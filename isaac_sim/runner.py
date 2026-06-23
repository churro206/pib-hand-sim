"""
isaac_sim/runner.py — Sequenz-Executor für pib (Library).

Wird von Sequenz-Skripten als Library geladen:
  _runner = _load_mod("runner", runner_path, _LIBRARY_MODE=True)
  _runner.execute(seq, mode="direct", side="right")

Re-Exports für Sequenz-Skripte: Sequence, Step, ALL

Workflow:
  start.py → Play → Sequenz-Skript ausführen
  Erneut ausführen nach Änderungen — kein Isaac-Neustart nötig.

Standalone:
  ~/isaacsim/python.sh isaac_sim/_launch_helper.py <sequenz_skript>
"""
import sys
import os
import importlib
import importlib.util
import asyncio
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

# ── Sequenzen + Control-Modes laden ──────────────────────────────────────────
_seq = _load_mod("pib_sequences", os.path.join(_root, "config", "sequences.py"))

_ctrl_dir = os.path.join(_root, "control")
sys.modules.pop("control", None)
_ctrl_pkg = _types.ModuleType("control")
_ctrl_pkg.__path__ = [_ctrl_dir]
sys.modules["control"] = _ctrl_pkg
_load_mod("control.base",   os.path.join(_ctrl_dir, "base.py"))
DirectMode = _load_mod("control.direct", os.path.join(_ctrl_dir, "direct.py")).DirectMode
ServoMode  = _load_mod("control.servo",  os.path.join(_ctrl_dir, "servo.py")).ServoMode
NNMode     = _load_mod("control.nn",     os.path.join(_ctrl_dir, "nn.py")).NNMode

# ── Re-Exports ────────────────────────────────────────────────────────────────
Sequence = _seq.Sequence
Step     = _seq.Step
ALL      = _seq.ALL


# ── Interpolation ─────────────────────────────────────────────────────────────
_SIM_HZ = 60.0


def _smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _interpolate(a: dict, b: dict, t: float) -> dict:
    s = _smoothstep(t)
    return {k: a.get(k, 0.0) * (1.0 - s) + b[k] * s for k in b}


def _build_frames(seq, mode_obj):
    """Generator: liefert (label, target_dict) pro Sim-Frame."""
    current: dict = {}
    for step in seq.steps:
        partial = mode_obj.to_joint_targets(step.target)
        target  = {**current, **partial}
        label   = step.name or "step"

        n_trans = max(1, int(step.transition_s * _SIM_HZ)) if step.transition_s > 0 else 0
        for k in range(n_trans):
            yield label, _interpolate(current, target, (k + 1) / n_trans)

        current = target
        for _ in range(max(1, int(step.hold_s * _SIM_HZ)) if step.hold_s > 0 else 1):
            yield label, current


def _make_mode_obj(mode_name: str, side: str):
    return {"direct": DirectMode(), "servo": ServoMode(side), "nn": NNMode()}[mode_name]


# ── Script Editor (async) ─────────────────────────────────────────────────────

async def _run_for(seq, mode_obj, mode_name: str) -> None:
    try:
        import omni.kit.app  # type: ignore
        app = omni.kit.app.get_app()
        _log(f"[runner] {seq.name} | mode={mode_name} | "
             f"{' → '.join(s.name for s in seq.steps)}")
        last = None
        for label, frame in _build_frames(seq, mode_obj):
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

def _run_standalone(seq, mode_obj, mode_name: str) -> None:
    _log(f"[runner] {seq.name} | mode={mode_name} (Standalone)")
    last = None
    for label, frame in _build_frames(seq, mode_obj):
        if label != last:
            _log(f"[runner] → {label}")
            last = label
        _io.set_all_targets(frame)
        _lh.sim_app.update()
    _log("[runner] Sequenz beendet — Endpose gehalten.")


# ── Öffentliche API ───────────────────────────────────────────────────────────

def execute(seq, mode: str = "direct", side: str = "right") -> None:
    """
    Sequenz abspielen.

    seq  : Sequence-Objekt
    mode : "direct" | "servo" | "nn"
    side : "left" | "right"  (nur für servo/nn)
    """
    mode_obj = _make_mode_obj(mode, side)
    if not _STANDALONE:
        asyncio.ensure_future(_run_for(seq, mode_obj, mode))
    else:
        _run_standalone(seq, mode_obj, mode)
