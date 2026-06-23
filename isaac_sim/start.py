"""
isaac_sim/start.py — Session-Startroutine für pib in Isaac Sim.

Vor dem ersten Play ausführen. Konfiguriert Drives, Limits und Initialpose —
PhysX cached diese Werte nicht, sie müssen nach jedem Session-Start gesetzt werden.

Workflow Script Editor:
  build_scene.py → Ctrl+S → start.py → Play → runner.py

Workflow Standalone:
  _launch_helper.py ruft start.run() automatisch auf — manuell nicht nötig.
"""
import os
import sys
import importlib
import importlib.util
from pathlib import Path


def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    try:
        import omni.usd  # type: ignore
        f = Path(omni.usd.get_context().get_stage().GetRootLayer().realPath)
        for ancestor in [f.parent, f.parent.parent]:
            if (ancestor / "config" / "pib_hand_config.py").is_file():
                return str(ancestor)
    except Exception:
        pass
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config.py").is_file():
            return str(candidate)
    raise FileNotFoundError("pib-hand-sim nicht gefunden. PIB_HAND_SIM_ROOT setzen.")


_root = _find_root()


def _load_setup_stage():
    sys.modules.pop("_setup_stage_start", None)
    importlib.invalidate_caches()
    path = os.path.join(_root, "isaac_sim", "setup_stage.py")
    spec = importlib.util.spec_from_file_location("_setup_stage_start", path)
    mod  = importlib.util.module_from_spec(spec)
    mod._SKIP_AUTO_SETUP = True
    spec.loader.exec_module(mod)
    return mod


def run(stg=None) -> None:
    """
    Session-Startroutine: configure_drives → set_joint_limits → set_initial_pose.

    stg: USD Stage. Wenn None wird via omni.usd.get_context() ermittelt (Script Editor).
    """
    if stg is None:
        import omni.usd  # type: ignore
        stg = omni.usd.get_context().get_stage()

    _ss = _load_setup_stage()
    _ss.configure_drives(stg)
    _ss.set_joint_limits(stg)
    _ss.set_initial_pose(stg)
    print("[start] Session-Setup abgeschlossen — Drives, Limits, Initialpose gesetzt.")


# ── Script-Editor-Block ───────────────────────────────────────────────────────
if not globals().get("_SKIP_AUTO_SETUP"):
    run()
