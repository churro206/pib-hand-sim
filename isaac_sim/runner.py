"""
isaac_sim/runner.py — Ebene-3-Executor: spielt eine Sequenz über einen ControlMode.

Datenfluss pro Step:
  Step.target (nur Änderungen)
    → MODE.to_joint_targets()      servo→dof expandieren, Rest durchreichen
    → in current-State mergen      (persistenter Zustand)
    → Smoothstep current→neu       über transition_s
    → robot_io.set_all_targets()   → Isaac

Konfiguration: SEQUENCE_NAME / MODE_NAME / SIDE unten anpassen.

Workflow Script Editor:
  start.py → Play → runner.py ausführen

Workflow Standalone:
  ~/isaacsim/python.sh isaac_sim/_launch_helper.py runner
"""
import sys
import os
import importlib
import importlib.util
import asyncio

# ══ KONFIGURATION ═════════════════════════════════════════════════════════════
SEQUENCE_NAME = "tendon"   # hand_poses | tendon | pickup
MODE_NAME     = "servo"        # direct | servo | nn
SIDE          = "right"        # nur für servo / nn
# ══════════════════════════════════════════════════════════════════════════════

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
    """Isaac-Sim-safe Modul-Loader — umgeht stale .pyc-Cache."""
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
    import robot_io as _io  # type: ignore  (_launch_helper hat es registriert)
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

# ── Sequenzen + Control-Modes via _load_mod laden ────────────────────────────
# Bewusst KEIN "from config import ..." / "from control import ...":
# Isaac hat cv2/ auf sys.path mit eigenem config.py → Namensk­ollision.
# _load_mod lädt per Dateipfad und umgeht das (+ stale .pyc).
import types as _types

_seq = _load_mod("pib_sequences", os.path.join(_root, "config", "sequences.py"))

# control/ als synthetisches Paket registrieren, damit die internen
# "from control.base import ControlMode" der Submodule auflösen.
_ctrl_dir = os.path.join(_root, "control")
sys.modules.pop("control", None)
_ctrl_pkg = _types.ModuleType("control")
_ctrl_pkg.__path__ = [_ctrl_dir]
sys.modules["control"] = _ctrl_pkg
_load_mod("control.base", os.path.join(_ctrl_dir, "base.py"))
DirectMode = _load_mod("control.direct", os.path.join(_ctrl_dir, "direct.py")).DirectMode
ServoMode  = _load_mod("control.servo",  os.path.join(_ctrl_dir, "servo.py")).ServoMode
NNMode     = _load_mod("control.nn",     os.path.join(_ctrl_dir, "nn.py")).NNMode

SEQUENCE = _seq.ALL[SEQUENCE_NAME]
MODE     = {"direct": DirectMode(), "servo": ServoMode(SIDE), "nn": NNMode()}[MODE_NAME]


# ── Interpolation ─────────────────────────────────────────────────────────────
_SIM_HZ = 60.0


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _interpolate(a: dict, b: dict, t: float) -> dict:
    s = _smoothstep(t)
    return {k: a.get(k, 0.0) * (1.0 - s) + b[k] * s for k in b}


def _build_frames():
    """
    Generator: liefert (label, target_dict) pro Sim-Frame.
    Pflegt den persistenten current-State und expandiert via MODE.
    """
    current: dict = {}
    for step in SEQUENCE.steps:
        partial = MODE.to_joint_targets(step.target)
        target  = {**current, **partial}
        label   = step.name or "step"

        n_trans = max(1, int(step.transition_s * _SIM_HZ)) if step.transition_s > 0 else 0
        for k in range(n_trans):
            yield label, _interpolate(current, target, (k + 1) / n_trans)

        current = target
        for _ in range(max(1, int(step.hold_s * _SIM_HZ)) if step.hold_s > 0 else 1):
            yield label, current


# ── Script Editor (async) ─────────────────────────────────────────────────────
async def _run_editor() -> None:
    try:
        import omni.kit.app  # type: ignore
        app = omni.kit.app.get_app()
        _log(f"[runner] {SEQUENCE.name} | mode={MODE_NAME} | "
             f"{' → '.join(s.name for s in SEQUENCE.steps)}")
        last = None
        for label, frame in _build_frames():
            if label != last:
                _log(f"[runner] → {label}")
                last = label
            _io.set_all_targets(frame)
            await app.next_update_async()
        _log("[runner] Sequenz beendet — Drive-Targets bleiben aktiv.")
    except Exception as exc:
        import traceback
        _log(f"[runner] FEHLER: {exc}")
        _log(traceback.format_exc())


# ── Standalone ────────────────────────────────────────────────────────────────
def run() -> None:
    _log(f"[runner] {SEQUENCE.name} | mode={MODE_NAME} (Standalone)")
    last = None
    for label, frame in _build_frames():
        if label != last:
            _log(f"[runner] → {label}")
            last = label
        _io.set_all_targets(frame)
        _lh.sim_app.update()
    _log("[runner] Sequenz beendet — Endpose gehalten (Drive-Targets aktiv).")


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    asyncio.ensure_future(_run_editor())
