"""
isaac_sim/demo_pickup.py — Pickup-Demo Sequenz abspielen.

Spielt PICKUP_SEQUENCE aus config/pickup_keyframes.py mit Smoothstep-Interpolation.
Keine time.sleep — alle Wartezeiten über sim_app.update() / next_update_async().

Workflow Script Editor:
  setup_stage.py → build_scene.py → Ctrl+S → Play → demo_pickup.py

Workflow Standalone:
  ~/isaacsim/python.sh isaac_sim/_launch_helper.py demo_pickup
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


def _load_mod(name, path, **pre_attrs):
    """Isaac-Sim-safe Modul-Loader — umgeht stale .pyc-Cache."""
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


# ── robot_io laden und Robot initialisieren ───────────────────────────────────
if _STANDALONE:
    import robot_io as _io  # type: ignore  (_launch_helper hat es registriert)
else:
    _io = _load_mod("robot_io", os.path.join(_root, "isaac_sim", "robot_io.py"))
    try:
        from isaacsim.core.prims import SingleArticulation as _ArtCls  # type: ignore
    except ImportError:
        from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore
    _robot = _ArtCls(prim_path=_io.ROBOT_PRIM_PATH)
    _robot.initialize()
    _io._set_robot(_robot)

# ── Drives + Limits konfigurieren (Script Editor) ────────────────────────────
if not _STANDALONE:
    try:
        import omni.usd  # type: ignore
        _ss  = _load_mod("_setup_fns", os.path.join(_root, "isaac_sim", "setup_stage.py"),
                         _SKIP_AUTO_SETUP=True)
        _stg = omni.usd.get_context().get_stage()
        _ss.configure_drives(_stg)
        _ss.set_joint_limits(_stg)
        _log("[demo] Drives und Limits konfiguriert")
    except Exception as _e:
        _log(f"[demo] Drive/Limit-Setup fehlgeschlagen (ignoriert): {_e}")

# ── Sequenz laden ─────────────────────────────────────────────────────────────
_kf = _load_mod("pickup_keyframes", os.path.join(_root, "config", "pickup_keyframes.py"))
SEQUENCE = _kf.PICKUP_SEQUENCE
_log(f"[demo] Sequenz: {' → '.join(s.name for s in SEQUENCE)}")


# ── Interpolation ─────────────────────────────────────────────────────────────

_SIM_HZ = 60.0


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _interpolate(a: dict, b: dict, t: float) -> dict:
    s = _smoothstep(t)
    return {name: a.get(name, 0.0) * (1.0 - s) + b[name] * s for name in b}


# ── Script Editor (async) ─────────────────────────────────────────────────────

async def _run_editor() -> None:
    try:
        import omni.kit.app  # type: ignore
        app = omni.kit.app.get_app()

        _log("[demo] Pickup-Demo gestartet")
        current = dict(SEQUENCE[0].keyframe)
        _io.apply_full_pose(current)
        await app.next_update_async()

        for step in SEQUENCE:
            _log(f"[demo] → {step.name}  (trans={step.transition_s}s  hold={step.hold_s}s)")

            n_trans = max(1, int(step.transition_s * _SIM_HZ)) if step.transition_s > 0 else 0
            for k in range(n_trans):
                _io.apply_full_pose(_interpolate(current, step.keyframe, (k + 1) / n_trans))
                await app.next_update_async()

            _io.apply_full_pose(step.keyframe)
            await app.next_update_async()
            current = dict(step.keyframe)

            n_hold = int(step.hold_s * _SIM_HZ)
            for _ in range(n_hold):
                await app.next_update_async()

        _log("[demo] Sequenz beendet — Drive-Targets bleiben aktiv.")

    except Exception as _exc:
        import traceback
        _log(f"[demo] FEHLER: {_exc}")
        _log(traceback.format_exc())


# ── Standalone ────────────────────────────────────────────────────────────────

def run() -> None:
    _log("[demo] Pickup-Demo gestartet (Standalone)")
    current = dict(SEQUENCE[0].keyframe)
    _io.apply_full_pose(current)
    _lh.sim_app.update()

    for step in SEQUENCE:
        _log(f"[demo] → {step.name}  (trans={step.transition_s}s  hold={step.hold_s}s)")

        n_trans = max(1, int(step.transition_s * _SIM_HZ)) if step.transition_s > 0 else 0
        for k in range(n_trans):
            _io.apply_full_pose(_interpolate(current, step.keyframe, (k + 1) / n_trans))
            _lh.sim_app.update()

        _io.apply_full_pose(step.keyframe)
        _lh.sim_app.update()
        current = dict(step.keyframe)

        n_hold = int(step.hold_s * _SIM_HZ)
        for _ in range(n_hold):
            _lh.sim_app.update()

    _log("[demo] Sequenz beendet. Halte Endpose.")
    while _lh.sim_app.is_running():
        _io.apply_full_pose(current)
        _lh.sim_app.update()


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    _log("[demo] Starte Coroutine (Script Editor Modus)")
    asyncio.ensure_future(_run_editor())
