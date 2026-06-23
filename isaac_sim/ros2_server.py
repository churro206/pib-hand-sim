"""
isaac_sim/ros2_server.py — ROS2-Bridge: empfängt Trajektorien, publiziert Zustand.

Workflow Script Editor:
  start.py → Play → ros2_server.py ausführen
  Erneut ausführen: stoppt vorherigen Server, startet neuen (hot-reload).

Topics:
  Subscribe: /pib/joint_trajectory  (trajectory_msgs/JointTrajectory)
  Subscribe: /pib/set_mode          (std_msgs/String)
  Publish:   /pib/joint_states      (sensor_msgs/JointState)
  Publish:   /pib/grasp_state       (std_msgs/Bool)
"""
import sys
import os
import importlib
import importlib.util
import asyncio
import time
import math
import types as _types

# ── Umgebungs-Erkennung ───────────────────────────────────────────────────────
_lh = sys.modules.get("_launch_helper")
_STANDALONE = _lh is not None

try:
    import carb as _carb  # type: ignore
    _log = _carb.log_warn
except ImportError:
    _log = print


def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    if _STANDALONE:
        from pathlib import Path
        return str(Path(__file__).parent.parent)
    try:
        import omni.usd  # type: ignore
        from pathlib import Path
        f = Path(omni.usd.get_context().get_stage().GetRootLayer().realPath)
        for ancestor in [f.parent, f.parent.parent]:
            if (ancestor / "config" / "pib_hand_config.py").is_file():
                return str(ancestor)
    except Exception:
        pass
    for candidate in ["~/repos/pib-hand-sim", "~/pib-hand-sim"]:
        p = os.path.expanduser(candidate)
        if os.path.isfile(os.path.join(p, "config", "pib_hand_config.py")):
            return p
    raise FileNotFoundError("Projekt nicht gefunden. PIB_HAND_SIM_ROOT setzen.")


_root = _find_root()
if _root not in sys.path:
    sys.path.insert(0, _root)


def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


# ── robot_io laden ────────────────────────────────────────────────────────────
if _STANDALONE:
    import robot_io as _io  # type: ignore
else:
    _io = _load_mod("robot_io", os.path.join(_root, "isaac_sim", "robot_io.py"))
    if not sys.modules.get("_runner_robot_initialized"):
        try:
            from isaacsim.core.prims import SingleArticulation as _ArtCls  # type: ignore
        except ImportError:
            from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore
        _robot = _ArtCls(prim_path=_io.ROBOT_PRIM_PATH)
        _robot.initialize()
        sys.modules["_runner_robot_initialized"] = _robot
    _io._set_robot(sys.modules["_runner_robot_initialized"])

# ── ControlModes laden ────────────────────────────────────────────────────────
_ctrl_dir = os.path.join(_root, "control")
sys.modules.pop("control", None)
_ctrl_pkg = _types.ModuleType("control")
_ctrl_pkg.__path__ = [_ctrl_dir]
sys.modules["control"] = _ctrl_pkg
_load_mod("control.base",   os.path.join(_ctrl_dir, "base.py"))
DirectMode = _load_mod("control.direct", os.path.join(_ctrl_dir, "direct.py")).DirectMode
ServoMode  = _load_mod("control.servo",  os.path.join(_ctrl_dir, "servo.py")).ServoMode
NNMode     = _load_mod("control.nn",     os.path.join(_ctrl_dir, "nn.py")).NNMode

# ── server_config laden ───────────────────────────────────────────────────────
_cfg = _load_mod("server_config", os.path.join(_root, "config", "server_config.py"))


def _make_mode(mode_name: str):
    return {"direct": DirectMode(), "servo": ServoMode(_cfg.SIDE), "nn": NNMode()}[mode_name]


# ── ROS2-Bridge aktivieren ────────────────────────────────────────────────────
try:
    import omni.kit.app as _omni_app  # type: ignore
    _ext = _omni_app.get_app().get_extension_manager()
    if not _ext.is_extension_enabled("isaacsim.ros2.bridge"):
        _ext.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
        _log("[ros2_server] ROS2-Bridge aktiviert.")
except Exception as _e:
    _log(f"[ros2_server] ROS2-Bridge-Aktivierung fehlgeschlagen: {_e}")

import rclpy  # type: ignore
from rclpy.node import Node  # type: ignore
from sensor_msgs.msg import JointState  # type: ignore
from trajectory_msgs.msg import JointTrajectory  # type: ignore
from std_msgs.msg import Bool, String  # type: ignore

# ── Shutdown-Flag: erneutes Ausführen stoppt vorherigen Server ────────────────
_FLAG = "_ros2_server_active"
if sys.modules.get(_FLAG):
    sys.modules[_FLAG]["stop"] = True
_stop = {"stop": False}
sys.modules[_FLAG] = _stop

# ── Server-Zustand ────────────────────────────────────────────────────────────
_active_traj = None
_traj_t0     = 0.0
_mode        = _make_mode(_cfg.CONTROL_MODE)


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _duration_to_sec(d) -> float:
    return float(d.sec) + float(d.nanosec) * 1e-9


def _to_deg(value: float, unit: str) -> float:
    """Eingehenden Winkel in interne Grad-Konvention umrechnen."""
    return math.degrees(value) if unit == "rad" else float(value)


def _from_deg(angle_deg: float, unit: str) -> float:
    """Interne Grad-Konvention in Ausgabe-Einheit umrechnen."""
    return math.radians(angle_deg) if unit == "rad" else angle_deg


def _interpolate_traj(traj, elapsed: float) -> dict:
    """Gibt {dof_name: angle_deg} für den aktuellen Zeitpunkt zurück."""
    names  = list(traj.joint_names)
    points = traj.points
    times  = [_duration_to_sec(p.time_from_start) for p in points]
    unit   = _cfg.ANGLE_UNIT

    # Letzten Punkt halten wenn Trajektorie abgelaufen
    if elapsed >= times[-1]:
        return {n: _to_deg(points[-1].positions[j], unit) for j, n in enumerate(names)}

    for i in range(len(points) - 1):
        if elapsed <= times[i + 1]:
            t0, t1 = times[i], times[i + 1]
            alpha  = (elapsed - t0) / (t1 - t0) if t1 > t0 else 1.0
            p0, p1 = points[i].positions, points[i + 1].positions
            return {n: _to_deg(p0[j] * (1.0 - alpha) + p1[j] * alpha, unit)
                    for j, n in enumerate(names)}

    return {n: _to_deg(points[-1].positions[j], unit) for j, n in enumerate(names)}


def _publish_joint_states(node, pub) -> None:
    try:
        state = _io.get_all_joint_states()
        unit  = _cfg.ANGLE_UNIT
        msg = JointState()
        msg.header.stamp = node.get_clock().now().to_msg()
        msg.name     = list(state.keys())
        msg.position = [_from_deg(v, unit) for v in state.values()]
        pub.publish(msg)
    except Exception as e:
        _log(f"[ros2_server] joint_states publish fehlgeschlagen: {e}")


def _publish_grasp_state(pub) -> None:
    try:
        msg = Bool()
        msg.data = False  # TODO Sprint 3: PhysX Contact Reports
        pub.publish(msg)
    except Exception as e:
        _log(f"[ros2_server] grasp_state publish fehlgeschlagen: {e}")


# ── Server-Loop ───────────────────────────────────────────────────────────────
async def _run_server() -> None:
    global _active_traj, _traj_t0, _mode

    if not rclpy.ok():
        rclpy.init()

    node = Node("pib_sim")

    def _on_joint_trajectory(msg):
        global _active_traj, _traj_t0
        if not msg.points:
            return
        _active_traj = msg
        _traj_t0     = time.monotonic()
        duration     = _duration_to_sec(msg.points[-1].time_from_start)
        _log(f"[ros2_server] Trajectory: {len(msg.points)} Punkte, {duration:.2f}s")

    def _on_set_mode(msg):
        global _mode
        name = msg.data.strip()
        if name not in ("direct", "servo", "nn"):
            _log(f"[ros2_server] Unbekannter Mode: {name!r} — ignoriert")
            return
        _mode = _make_mode(name)
        _log(f"[ros2_server] Mode → {name}")

    node.create_subscription(JointTrajectory, _cfg.TOPIC_JOINT_TRAJECTORY, _on_joint_trajectory, 10)
    node.create_subscription(String,          _cfg.TOPIC_SET_MODE,         _on_set_mode,         10)

    pub_states = node.create_publisher(JointState, _cfg.TOPIC_JOINT_STATES, 10)
    pub_grasp  = node.create_publisher(Bool,       _cfg.TOPIC_GRASP_STATE,  10)

    _log(f"[ros2_server] Bereit | mode={_cfg.CONTROL_MODE} | unit={_cfg.ANGLE_UNIT}")
    _log(f"[ros2_server]   sub: {_cfg.TOPIC_JOINT_TRAJECTORY}, {_cfg.TOPIC_SET_MODE}")
    _log(f"[ros2_server]   pub: {_cfg.TOPIC_JOINT_STATES}, {_cfg.TOPIC_GRASP_STATE}")

    import omni.kit.app as _app_module  # type: ignore
    app = _app_module.get_app()

    _pub_interval = 1.0 / _cfg.PUBLISH_HZ
    _last_pub     = 0.0

    while not _stop["stop"]:
        rclpy.spin_once(node, timeout_sec=0)

        # Aktive Trajektorie ausführen
        if _active_traj is not None:
            elapsed = time.monotonic() - _traj_t0
            cmd     = _interpolate_traj(_active_traj, elapsed)
            targets = _mode.to_joint_targets(cmd)
            _io.set_all_targets(targets)

            last_t = _duration_to_sec(_active_traj.points[-1].time_from_start)
            if elapsed >= last_t:
                _log("[ros2_server] Trajectory abgeschlossen — Endpose gehalten.")
                _active_traj = None

        # Zustand publishen
        now = time.monotonic()
        if now - _last_pub >= _pub_interval:
            _publish_joint_states(node, pub_states)
            _publish_grasp_state(pub_grasp)
            _last_pub = now

        try:
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
        except asyncio.TimeoutError:
            pass  # Sim pausiert oder gestoppt — Stop-Flag beim nächsten Tick prüfen

    _log("[ros2_server] Gestoppt.")
    node.destroy_node()


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    asyncio.ensure_future(_run_server())
