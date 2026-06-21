"""
isaac_sim/test_hand_poses.py — Ganzkörper-Posen-Test (alle 44 DOFs).

Läuft in beiden Umgebungen:
  SCRIPT EDITOR: setup_stage.py ausführen → Ctrl+S → Play → diese Datei ausführen.
  STANDALONE:    ~/isaacsim/python.sh isaac_sim/_launch_helper.py test_hand_poses

Sequenz: Winken → Doppelbizeps → Peace

Winkelkonvention: positiv = Onshape-Flexionsrichtung.
JOINT_SIGN=-1 in robot_io.py kompensiert die Isaac-Invertierung automatisch.
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
    sys.modules.pop(name, None)   # stale Cache entfernen
    importlib.invalidate_caches() # Isaac-Python neu-scannt Filesystem
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
    _log(f"[test] Robot initialisiert: {_io.ROBOT_PRIM_PATH}")

# ── Setup (Script Editor): Drives + Limits ────────────────────────────────────
if not _STANDALONE:
    try:
        import omni.usd  # type: ignore
        _ss  = _load_mod("_setup_fns", os.path.join(_root, "isaac_sim", "setup_stage.py"),
                         _SKIP_AUTO_SETUP=True)
        _stg = omni.usd.get_context().get_stage()
        _log(f"[test] Drives: {_ss.configure_drives(_stg)} Joints")
        # fix_joint_limits hier NICHT aufrufen — ist einmalige Setup-Funktion.
        # setup_stage.py ausführen → Ctrl+S → Play → dann diese Datei starten.
    except Exception as _e:
        _log(f"[test] Setup fehlgeschlagen (ignoriert): {_e}")

# ── Referenzen ────────────────────────────────────────────────────────────────
set_all_targets = _io.set_all_targets
HAND_DOFS       = _io.HAND_DOFS

# ── Hilfs-Lambdas ─────────────────────────────────────────────────────────────
def _open(side):
    return {n: 0.0 for n in HAND_DOFS[side]["names"]}

def _fist(side):
    s = side
    return {
        f"dof_thumb_{s}_rotator":   30.0,
        f"dof_thumb_{s}_proximal":  80.0, f"dof_thumb_{s}_distal":    80.0,
        f"dof_index_{s}_proximal":  85.0, f"dof_index_{s}_distal":    68.0, f"dof_index_{s}_tip":   51.0,
        f"dof_middle_{s}_proximal": 85.0, f"dof_middle_{s}_distal":   68.0, f"dof_middle_{s}_tip":  51.0,
        f"dof_ring_{s}_proximal":   85.0, f"dof_ring_{s}_distal":     68.0, f"dof_ring_{s}_tip":    51.0,
        f"dof_pinky_{s}_proximal":  85.0, f"dof_pinky_{s}_distal":    68.0, f"dof_pinky_{s}_tip":   51.0,
    }

# ── Posen ─────────────────────────────────────────────────────────────────────
# Winkelangaben in Grad, Onshape-Konvention (positiv = gewünschte Flexionsrichtung).
# Körpergelenk-Vorzeichen: visuell verifizieren, ggf. umdrehen.

# Geteilte Arm-Konfiguration für alle Wink-Posen.
# Ziel: Unterarm zeigt senkrecht nach oben.
#   → Schulter in T-Pose-Ebene (shoulder_vertical ≈ 0°, shoulder_horizontal leicht
#     nach vorne), Ellbogen auf 90° gebeugt → Unterarm zeigt nach oben.
# Winken: dof_elbow_right zwischen WINK_ELBOW_A und WINK_ELBOW_B hin und her.
WINK_ELBOW_A = 65.0   # Ellbogen etwas weniger gebeugt (Unterarm leicht gekippt)
WINK_ELBOW_B = 90.0   # Ellbogen voll gebeugt (Unterarm senkrecht oben)

_WINK_ARM = {
    "dof_head_horizontal":           25.0,  # Kopf leicht zum Gegenüber
    "dof_head_vertical":              0.0,
    "dof_shoulder_vertical_left":   -30.0,  # linker Arm leicht hängend
    "dof_shoulder_horizontal_left":   0.0,
    "dof_upper_arm_left":             0.0,
    "dof_elbow_left":                15.0,
    "dof_forearm_left":               0.0,
    "dof_wrist_left":                 0.0,
    "dof_shoulder_vertical_right":    0.0,  # Schulter T-Pose-Ebene
    "dof_shoulder_horizontal_right": 20.0,  # Arm leicht nach vorne
    "dof_upper_arm_right":            0.0,
    "dof_forearm_right":              0.0,
    "dof_wrist_right":                0.0,
}

POSES = {
    # ── Neutral — T-Pose ─────────────────────────────────────────────────────
    "neutral": {
        "dof_head_horizontal": 0.0, "dof_head_vertical": 0.0,
        "dof_shoulder_vertical_left": 0.0,   "dof_shoulder_horizontal_left": 0.0,
        "dof_upper_arm_left": 0.0,            "dof_elbow_left": 0.0,
        "dof_forearm_left": 0.0,              "dof_wrist_left": 0.0,
        "dof_shoulder_vertical_right": 0.0,  "dof_shoulder_horizontal_right": 0.0,
        "dof_upper_arm_right": 0.0,           "dof_elbow_right": 0.0,
        "dof_forearm_right": 0.0,             "dof_wrist_right": 0.0,
        **_open("left"), **_open("right"),
    },

    # ── Winken A/B — Ellbogen schwingt hin und her ───────────────────────────
    "wink_a": {**_WINK_ARM, "dof_elbow_right": WINK_ELBOW_A,
               **_open("left"), **_open("right")},
    "wink_b": {**_WINK_ARM, "dof_elbow_right": WINK_ELBOW_B,
               **_open("left"), **_open("right")},

    # ── Doppelbizeps — beide Arme T-Pose, Ellbogen 90°, Fäuste ──────────────
    "doppelbizeps": {
        "dof_head_horizontal":           0.0,  "dof_head_vertical":             0.0,
        "dof_shoulder_vertical_left":    0.0,  "dof_shoulder_horizontal_left":  0.0,
        "dof_upper_arm_left":            0.0,  "dof_elbow_left":               90.0,
        "dof_forearm_left":             90.0,  "dof_wrist_left":                0.0,
        "dof_shoulder_vertical_right":   0.0,  "dof_shoulder_horizontal_right": 0.0,
        "dof_upper_arm_right":           0.0,  "dof_elbow_right":              90.0,
        "dof_forearm_right":            90.0,  "dof_wrist_right":               0.0,
        "dof_wrist_left":               90.0,  "dof_wrist_right":              90.0,
        **_fist("left"), **_fist("right"),
    },

    # ── Peace — rechte Hand V-Zeichen ────────────────────────────────────────
    "peace": {
        "dof_head_horizontal":          -15.0,
        "dof_head_vertical":              0.0,
        "dof_shoulder_vertical_left":   -30.0,
        "dof_shoulder_horizontal_left":   0.0,
        "dof_upper_arm_left":             0.0,
        "dof_elbow_left":                20.0,
        "dof_forearm_left":               0.0,
        "dof_wrist_left":                 0.0,
        "dof_shoulder_vertical_right":   30.0,
        "dof_shoulder_horizontal_right": 25.0,
        "dof_upper_arm_right":            0.0,
        "dof_elbow_right":               40.0,
        "dof_forearm_right":              0.0,
        "dof_wrist_right":                0.0,
        **_open("left"),
        "dof_thumb_right_rotator":   30.0,
        "dof_thumb_right_proximal":  60.0,  "dof_thumb_right_distal":   60.0,
        "dof_index_right_proximal":   0.0,  "dof_index_right_distal":    0.0,  "dof_index_right_tip":   0.0,
        "dof_middle_right_proximal":  0.0,  "dof_middle_right_distal":   0.0,  "dof_middle_right_tip":  0.0,
        "dof_ring_right_proximal":   85.0,  "dof_ring_right_distal":    68.0,  "dof_ring_right_tip":   51.0,
        "dof_pinky_right_proximal":  85.0,  "dof_pinky_right_distal":   68.0,  "dof_pinky_right_tip":  51.0,
    },
}

# Sequenz: (pose_name, dauer_in_sekunden)
_SEQUENCE = [
    # Winken
    ("wink_a", 0.2),     ("wink_b", 0.2),
    ("wink_a", 0.2),     ("wink_b", 0.2),
    ("wink_a", 0.2),     ("wink_b", 0.2),
    ("wink_a", 0.2),     ("wink_b", 0.2),
    ("wink_a", 0.2),     ("wink_b", 0.2),
    # Doppelbizeps
    ("doppelbizeps", 2.0),
    # Peace
    ("peace",        2.0),
    ("neutral",      2.0),
]


# ── Test-Logik ────────────────────────────────────────────────────────────────

async def _run_editor() -> None:
    try:
        import omni.kit.app  # type: ignore
        app = omni.kit.app.get_app()
        _log("[test] Ganzkörper-Test mit Winken")
        for pose_name, duration in _SEQUENCE:
            _log(f"[test] ► {pose_name.upper()}  ({duration}s)")
            set_all_targets(POSES[pose_name])
            frames = max(1, int(duration * 60))
            for _ in range(frames):
                await app.next_update_async()
        _log("[test] Abgeschlossen.")
    except Exception as _exc:
        import traceback
        _log(f"[test] FEHLER: {_exc}")
        _log(traceback.format_exc())


def run() -> None:
    _log("[test] Ganzkörper-Test mit Winken  (Standalone)")
    for pose_name, duration in _SEQUENCE:
        _log(f"[test] ► {pose_name.upper()}  ({duration}s)")
        set_all_targets(POSES[pose_name])
        frames = max(1, int(duration * 60))
        for _ in range(frames):
            _lh.sim_app.update()
    _log("[test] Abgeschlossen.")


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    _log("[test] Starte Coroutine (Script Editor Modus)")
    asyncio.ensure_future(_run_editor())
