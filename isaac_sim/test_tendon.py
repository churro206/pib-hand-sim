"""
isaac_sim/test_tendon.py — Virtueller Servo Test.

Rechten Arm nach vorne strecken, dann rechte Hand 3× langsam schließen und
öffnen. Drive-Targets werden interpoliert — ohne Ramp würde der Drive sofort
einrasten statt sich langsam zu bewegen.

Anpassbare Parameter:
  RAMP_SEC   — Sekunden pro Richtung (Schließen oder Öffnen)
  RAMP_STEPS — Interpolationsschritte (mehr = gleichmäßiger)

Läuft in beiden Umgebungen:
  SCRIPT EDITOR: setup_stage.py ausführen → Ctrl+S → Play → diese Datei ausführen.
  STANDALONE:    ~/isaacsim/python.sh isaac_sim/_launch_helper.py test_tendon
"""
import sys
import os
import importlib.util
import asyncio

# ── Umgebungs-Erkennung ───────────────────────────────────────────────────────
_lh = sys.modules.get("_launch_helper")
_STANDALONE = _lh is not None

# ── Logging ───────────────────────────────────────────────────────────────────
try:
    import carb as _carb  # type: ignore
    _log = _carb.log_warn
except ImportError:
    _log = print

# ── Projekt-Root ermitteln ────────────────────────────────────────────────────
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
_log(f"[tendon] Projekt-Root: {_root}")


def _load_mod(name, path, **pre_attrs):
    """Isaac-Sim-safe Modul-Loader — umgeht stale .pyc-Bytecode-Cache."""
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
    try:
        from isaacsim.core.prims import SingleArticulation as _ArtCls  # type: ignore
    except ImportError:
        from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore
    _robot = _ArtCls(prim_path=_io.ROBOT_PRIM_PATH)
    _robot.initialize()
    _io._set_robot(_robot)

# ── Drives konfigurieren (Script Editor) ─────────────────────────────────────
if not _STANDALONE:
    try:
        import omni.usd  # type: ignore
        _ss  = _load_mod("_setup_fns", os.path.join(_root, "isaac_sim", "setup_stage.py"),
                         _SKIP_AUTO_SETUP=True)
        _stg = omni.usd.get_context().get_stage()
        _log(f"[tendon] Drives: {_ss.configure_drives(_stg)} Joints")
    except Exception as _e:
        _log(f"[tendon] Setup fehlgeschlagen (ignoriert): {_e}")

# ── Referenzen ────────────────────────────────────────────────────────────────
set_all_targets = _io.set_all_targets
HAND_DOFS       = _io.HAND_DOFS

# ── Config laden ──────────────────────────────────────────────────────────────
_cfg                 = _load_mod("pib_hand_config", os.path.join(_root, "config", "pib_hand_config.py"))
servo_pose_to_joints = _cfg.servo_pose_to_joints
GRASP_POSES          = _cfg.GRASP_POSES

_log(f"[tendon] SERVO_FACTORS index: {_cfg._SERVO_FACTORS['index']}")

# ── Arm-Pose: rechter Arm nach vorne gestreckt ────────────────────────────────
_ARM_FORWARD = {
    "dof_head_horizontal":            0.0,
    "dof_head_vertical":              0.0,
    "dof_shoulder_vertical_left":   -30.0,
    "dof_shoulder_horizontal_left":   0.0,
    "dof_upper_arm_left":             0.0,
    "dof_elbow_left":                15.0,
    "dof_forearm_left":               0.0,
    "dof_wrist_left":                 0.0,
    "dof_shoulder_vertical_right":    0.0,
    "dof_shoulder_horizontal_right": 75.0,  # Arm nach vorne
    "dof_upper_arm_right":            0.0,
    "dof_elbow_right":                0.0,
    "dof_forearm_right":              0.0,
    "dof_wrist_right":                0.0,
}

# ── Servo-Posen ───────────────────────────────────────────────────────────────
_OPEN  = GRASP_POSES["open"]
_CLOSE = GRASP_POSES["closed_fist"]

# ── Interpolationsparameter ───────────────────────────────────────────────────
RAMP_SEC   = 5.0   # Sekunden pro Richtung
RAMP_STEPS = 90    # Schritte → dt ≈ 0.056 s pro Schritt


def _ramp(from_servo: dict, to_servo: dict) -> list:
    """
    Generiert RAMP_STEPS interpolierte (pose, dt)-Tupel für eine Richtung.
    Linke Hand bleibt offen. Arm-Pose bleibt konstant.
    """
    dt        = RAMP_SEC / RAMP_STEPS
    left_open = {n: 0.0 for n in HAND_DOFS["left"]["names"]}
    steps     = []
    for i in range(1, RAMP_STEPS + 1):
        alpha  = i / RAMP_STEPS
        interp = {k: from_servo.get(k, 0.0) + alpha * (to_servo.get(k, 0.0) - from_servo.get(k, 0.0))
                  for k in to_servo}
        pose = dict(_ARM_FORWARD)
        pose.update(servo_pose_to_joints(interp, "right"))
        pose.update(left_open)
        steps.append((pose, dt))
    return steps


# ── Sequenz ───────────────────────────────────────────────────────────────────
_pose_start = dict(_ARM_FORWARD)
_pose_start.update(servo_pose_to_joints(_OPEN, "right"))
_pose_start.update(servo_pose_to_joints(_OPEN, "left"))

_SEQUENCE = (
    [(_pose_start, 2.0)]        # Arm positionieren, Hand öffnen
    + _ramp(_OPEN,  _CLOSE)     # Schließen ─┐
    + _ramp(_CLOSE, _OPEN)      # Öffnen    ─┘ Zyklus 1
    + _ramp(_OPEN,  _CLOSE)     #              Zyklus 2
    + _ramp(_CLOSE, _OPEN)
    + _ramp(_OPEN,  _CLOSE)     #              Zyklus 3
    + _ramp(_CLOSE, _OPEN)
)

_log(f"[tendon] Sequenz: {len(_SEQUENCE)} Schritte, ~{2 + 6 * RAMP_SEC:.0f}s gesamt")


# ── Test-Logik ────────────────────────────────────────────────────────────────

async def _run_editor() -> None:
    try:
        import omni.kit.app  # type: ignore
        app = omni.kit.app.get_app()
        _log("[tendon] Virtueller-Servo-Test gestartet")
        for pose, duration in _SEQUENCE:
            set_all_targets(pose)
            for _ in range(max(1, int(duration * 60))):
                await app.next_update_async()
        _log("[tendon] Abgeschlossen.")
    except Exception as _exc:
        import traceback
        _log(f"[tendon] FEHLER: {_exc}")
        _log(traceback.format_exc())


def run() -> None:
    _log("[tendon] Virtueller-Servo-Test gestartet (Standalone)")
    for pose, duration in _SEQUENCE:
        set_all_targets(pose)
        for _ in range(max(1, int(duration * 60))):
            _lh.sim_app.update()
    _log("[tendon] Abgeschlossen.")


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    _log("[tendon] Starte Coroutine (Script Editor Modus)")
    asyncio.ensure_future(_run_editor())
