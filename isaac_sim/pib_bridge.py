"""
isaac_sim/pib_bridge.py — Dünner ROS2-Bridge zwischen Isaac Sim und ros2_control.

Ersetzt ros2_server.py für den ros2_control-Workflow.

Workflow Script Editor:
  start.py → Play → pib_bridge.py ausführen
  Erneut ausführen: stoppt vorherige Instanz, startet neu.

Topics:
  Publish:   /pib/hw/joint_states   (sensor_msgs/JointState, rad, 50 Hz)
             → topic_based_ros2_control liest davon
  Subscribe: /pib/hw/joint_commands (sensor_msgs/JointState, rad)
             ← topic_based_ros2_control schreibt dorthin

Winkel: robot_io arbeitet in Grad; Bridge konvertiert ↔ Radiant.
JOINT_SIGN bleibt in robot_io — hier keine Vorzeichen-Logik.
"""
import sys
import os
import importlib
import importlib.util
import asyncio
import math
import time

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
    mod = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


# ── robot_io laden ────────────────────────────────────────────────────────────
if _STANDALONE:
    import robot_io as _io  # type: ignore
else:
    _io = _load_mod("robot_io", os.path.join(_root, "isaac_sim", "robot_io.py"))
    # Robot-Initialisierung lazy: initialize() erst wenn Sim läuft, da
    # SingleArticulation.initialize() intern get_joint_positions() aufruft
    # und Isaac's C++ "Physics Simulation View is not created yet" loggt.
    if sys.modules.get("_bridge_robot_initialized"):
        _io._set_robot(sys.modules["_bridge_robot_initialized"])
    # Sonst: _ensure_robot_initialized() im Loop nach is_playing()-Check

# ── ROS2-Bridge aktivieren ────────────────────────────────────────────────────
try:
    import omni.kit.app as _omni_app  # type: ignore
    _ext = _omni_app.get_app().get_extension_manager()
    if not _ext.is_extension_enabled("isaacsim.ros2.bridge"):
        _ext.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
        _log("[pib_bridge] ROS2-Bridge aktiviert.")
except Exception as _e:
    _log(f"[pib_bridge] ROS2-Bridge-Aktivierung fehlgeschlagen: {_e}")

# Isaac Sim bündelt rclpy für Python 3.11 in der Bridge-Extension.
# System-ROS2 (Jazzy) ist für Python 3.12 gebaut → C-Extension inkompatibel.
# Korrekt: jazzy/ (Parent des rclpy-Packages) eintragen, nicht jazzy/rclpy/.
# Gecachte rclpy-Module aus sys.modules entfernen (falls System-rclpy bereits
# importiert wurde, z.B. durch ROS2-Sourcing im Start-Terminal).
import os as _os
_isaac_ros2_path = _os.path.expanduser(
    "~/isaacsim/exts/isaacsim.ros2.bridge/jazzy"
)
if _os.path.isdir(_isaac_ros2_path):
    for _k in [k for k in sys.modules if k.startswith("rclpy")]:
        del sys.modules[_k]
    if _isaac_ros2_path not in sys.path:
        sys.path.insert(0, _isaac_ros2_path)
    _log(f"[pib_bridge] Isaac ROS2-Path eingetragen: {_isaac_ros2_path}")

import rclpy  # type: ignore
from rclpy.node import Node  # type: ignore
from sensor_msgs.msg import JointState  # type: ignore

# ── Stop-Flag: erneutes Ausführen stoppt vorherige Instanz ───────────────────
_FLAG = "_pib_bridge_active"
if sys.modules.get(_FLAG):
    sys.modules[_FLAG]["stop"] = True
_stop = {"stop": False}
sys.modules[_FLAG] = _stop

# ── Publish-Rate ──────────────────────────────────────────────────────────────
_PUBLISH_HZ = 50.0
_PUBLISH_INTERVAL = 1.0 / _PUBLISH_HZ

# ── Letzter empfangener Befehl ────────────────────────────────────────────────
_pending_command: dict | None = None  # {dof_name: angle_deg}


async def _run_bridge() -> None:
    global _pending_command

    if not rclpy.ok():
        rclpy.init()

    node = Node("pib_bridge")

    def _on_joint_commands(msg: JointState) -> None:
        """Empfängt Positionsbefehle von ros2_control (in Radiant)."""
        global _pending_command
        if not msg.name or not msg.position:
            return
        # Radiant → Grad (Onshape-Konvention)
        _pending_command = {
            name: math.degrees(pos)
            for name, pos in zip(msg.name, msg.position)
        }

    node.create_subscription(
        JointState,
        "/pib/hw/joint_commands",
        _on_joint_commands,
        10,
    )

    pub_states = node.create_publisher(JointState, "/pib/hw/joint_states", 10)

    _log("[pib_bridge] Bereit.")
    _log("[pib_bridge]   pub: /pib/hw/joint_states (50 Hz, rad)")
    _log("[pib_bridge]   sub: /pib/hw/joint_commands (rad)")

    import omni.kit.app as _app_module  # type: ignore
    app = _app_module.get_app()

    _last_pub   = 0.0
    _physics_ready = False
    _play_since = None          # Zeitstempel des letzten Play-Starts
    _GRACE_S    = 0.5           # Warte nach Play bevor get_joint_positions

    import omni.timeline as _timeline_mod  # type: ignore
    _timeline = _timeline_mod.get_timeline_interface()

    def _init_robot() -> bool:
        """Initialisiert SingleArticulation (nur wenn noch nicht gecacht)."""
        if sys.modules.get("_bridge_robot_initialized"):
            _io._set_robot(sys.modules["_bridge_robot_initialized"])
            return True
        try:
            from isaacsim.core.prims import SingleArticulation as _AC  # type: ignore
        except ImportError:
            from omni.isaac.core.articulations import Articulation as _AC  # type: ignore
        try:
            robot = _AC(prim_path=_io.ROBOT_PRIM_PATH)
            robot.initialize()
            sys.modules["_bridge_robot_initialized"] = robot
            _io._set_robot(robot)
            return True
        except Exception:
            return False

    _was_playing = False

    while not _stop["stop"]:
        rclpy.spin_once(node, timeout_sec=0)

        now        = time.monotonic()
        is_playing = _timeline.is_playing()

        # Sim gestoppt: Handle invalidieren damit nächstes Play re-initialisiert
        if not is_playing:
            if _was_playing:
                _was_playing   = False
                _physics_ready = False
                _play_since    = None
                sys.modules.pop("_bridge_robot_initialized", None)
                _log("[pib_bridge] Sim gestoppt — warte auf Play.")
            if _pending_command is not None:
                _pending_command = None
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
            continue

        # Sim started: Grace-Period abwarten bevor Physics View genutzt wird
        if not _was_playing:
            _was_playing = True
            _play_since  = now
            _log("[pib_bridge] Play erkannt — warte auf Physics View...")

        if now - _play_since < _GRACE_S:
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
            continue

        # Grace-Period abgelaufen: Robot initialisieren (einmalig pro Session)
        if not _init_robot():
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
            continue

        # Befehl ausführen
        if _pending_command is not None:
            _io.set_all_targets(_pending_command)
            _pending_command = None

        # Joint-States publishen (50 Hz)
        if now - _last_pub >= _PUBLISH_INTERVAL:
            _last_pub = now
            try:
                state_deg = _io.get_all_joint_states()
                if not _physics_ready:
                    _physics_ready = True
                    _log("[pib_bridge] Physics View bereit — publishe joint_states.")
                msg = JointState()
                msg.header.stamp = node.get_clock().now().to_msg()
                msg.name     = list(state_deg.keys())
                msg.position = [math.radians(v) for v in state_deg.values()]
                pub_states.publish(msg)
            except Exception as e:
                if _physics_ready:
                    _physics_ready = False
                    _log(f"[pib_bridge] publish fehlgeschlagen: {e}")

        try:
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
        except asyncio.TimeoutError:
            pass

    _log("[pib_bridge] Gestoppt.")
    node.destroy_node()


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    asyncio.ensure_future(_run_bridge())
