"""
isaac_sim/test_hand_poses.py — Greifposen-Test (Phase 1, direkte Gelenksteuerung).

Läuft in beiden Umgebungen:

  SCRIPT EDITOR: Datei öffnen → Run (Ctrl+Enter). Simulation muss laufen (Play).

  STANDALONE:    ~/isaacsim/python.sh isaac_sim/_launch_helper.py test_hand_poses

Ablauf: open → closed_fist → pointing → open
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
_log(f"[test] Projekt-Root: {_root}")


def _load_mod(name: str, path: str, **pre_attrs):
    """Lädt Modul via importlib; pre_attrs werden VOR exec_module gesetzt."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


# ── hand_io laden und Robot-Handle setzen ─────────────────────────────────────
if _STANDALONE:
    import hand_io as _io  # type: ignore  — bereits von _launch_helper initialisiert
else:
    _io = _load_mod("hand_io", os.path.join(_root, "isaac_sim", "hand_io.py"))
    try:
        from isaacsim.core.prims import SingleArticulation as _ArtCls  # type: ignore
    except ImportError:
        from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore
    _robot = _ArtCls(prim_path=_io.ROBOT_PRIM_PATH)
    _robot.initialize()
    _io._set_robot(_robot)
    _log(f"[test] Robot initialisiert: {_io.ROBOT_PRIM_PATH}")

# ── phase1_direct laden ───────────────────────────────────────────────────────
if _STANDALONE:
    from phases.phase1_direct import compute_joint_targets  # type: ignore
else:
    _ph = _load_mod("phase1_direct", os.path.join(_root, "phases", "phase1_direct.py"))
    compute_joint_targets = _ph.compute_joint_targets

set_hand_targets = _io.set_hand_targets
print_hand_state = _io.print_hand_state
HAND_DOFS        = _io.HAND_DOFS

# ── Drives konfigurieren (Script Editor) ──────────────────────────────────────
# Nötig wenn setup_stage.py noch nicht mit den neuen Drive-Werten ausgeführt
# wurde (alter Stand hatte stiffness=0 für Handgelenke → keine Bewegung).
if not _STANDALONE:
    try:
        import omni.usd  # type: ignore
        _ss = _load_mod(
            "_setup_fns",
            os.path.join(_root, "isaac_sim", "setup_stage.py"),
            _SKIP_AUTO_SETUP=True,
        )
        _n = _ss.configure_drives(omni.usd.get_context().get_stage())
        _log(f"[test] Drives konfiguriert: {_n} Joints")
    except Exception as _e:
        _log(f"[test] configure_drives fehlgeschlagen (ignoriert): {_e}")

# ── Parameter ─────────────────────────────────────────────────────────────────
SIDE    = "right"   # "left" oder "right"
PAUSE_S = 3.0       # Wartezeit zwischen Posen in Sekunden
# ─────────────────────────────────────────────────────────────────────────────

_N = HAND_DOFS[SIDE]["names"]

DIRECT_POSES = {
    "open": {name: 0.0 for name in _N},

    "closed_fist": {
        "dof_thumb_right_rotator":   30.0,
        "dof_thumb_right_proximal":  80.0,
        "dof_thumb_right_distal":    80.0,
        "dof_index_right_proximal":  85.0,
        "dof_index_right_distal":    68.0,   # 85 × 0.8
        "dof_index_right_tip":       51.0,   # 85 × 0.6
        "dof_middle_right_proximal": 85.0,
        "dof_middle_right_distal":   68.0,
        "dof_middle_right_tip":      51.0,
        "dof_ring_right_proximal":   85.0,
        "dof_ring_right_distal":     68.0,
        "dof_ring_right_tip":        51.0,
        "dof_pinky_right_proximal":  85.0,
        "dof_pinky_right_distal":    68.0,
        "dof_pinky_right_tip":       51.0,
    },

    "pointing": {
        "dof_thumb_right_rotator":   30.0,
        "dof_thumb_right_proximal":  80.0,
        "dof_thumb_right_distal":    80.0,
        "dof_index_right_proximal":   0.0,
        "dof_index_right_distal":     0.0,
        "dof_index_right_tip":        0.0,
        "dof_middle_right_proximal": 85.0,
        "dof_middle_right_distal":   68.0,
        "dof_middle_right_tip":      51.0,
        "dof_ring_right_proximal":   85.0,
        "dof_ring_right_distal":     68.0,
        "dof_ring_right_tip":        51.0,
        "dof_pinky_right_proximal":  85.0,
        "dof_pinky_right_distal":    68.0,
        "dof_pinky_right_tip":       51.0,
    },
}


def _adapt_pose(pose: dict) -> dict:
    if SIDE == "right":
        return pose
    return {k.replace("_right_", f"_{SIDE}_"): v for k, v in pose.items()}


# ── Test-Logik ────────────────────────────────────────────────────────────────

_SEQUENCE = ["open", "closed_fist", "pointing", "open"]


async def _run_editor() -> None:
    """Script-Editor-Variante: wartet mit app.next_update_async()."""
    try:
        import omni.kit.app  # type: ignore
        app    = omni.kit.app.get_app()
        frames = max(1, int(PAUSE_S * 60))

        _log(f"[test] Hand-Pose-Test  Seite={SIDE}  Pause={PAUSE_S}s")

        for pose_name in _SEQUENCE:
            targets = compute_joint_targets(_adapt_pose(DIRECT_POSES[pose_name]), SIDE)

            _log(f"[test] ► {pose_name.upper()}")
            for name, deg in targets.items():
                _log(f"[test]   {name:<32s} {deg:5.1f}°")

            set_hand_targets(targets, SIDE)

            for _ in range(frames):
                await app.next_update_async()

        _log("[test] Abgeschlossen.")

    except Exception as _exc:
        import traceback
        _log(f"[test] FEHLER in _run_editor: {_exc}")
        _log(traceback.format_exc())


def run() -> None:
    """Standalone-Variante: wartet mit sim_app.update()."""
    frames = max(1, int(PAUSE_S * 60))

    _log(f"[test] Hand-Pose-Test  Seite={SIDE}  Pause={PAUSE_S}s  (Standalone)")
    for pose_name in _SEQUENCE:
        targets = compute_joint_targets(_adapt_pose(DIRECT_POSES[pose_name]), SIDE)
        set_hand_targets(targets, SIDE)
        _log(f"[test] ► {pose_name.upper()}")
        print_hand_state(SIDE)
        for _ in range(frames):
            _lh.sim_app.update()
    _log("[test] Abgeschlossen. Simulation läuft weiter (Fenster schließen zum Beenden).")


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    _log(f"[test] Starte Coroutine (Script Editor Modus)")
    asyncio.ensure_future(_run_editor())
# Standalone: run() wird von _launch_helper.py aufgerufen
