"""
Test-Skript: Alle Greifposen der pib-Hand nacheinander abfahren.

Ausführen im Isaac Script Editor (Window → Script Editor → Run).
Voraussetzung: Simulation läuft (Play gedrückt), USD-Modell ist geladen.

Anpassbare Parameter:
  SIDE      — welche Hand getestet wird ("left" oder "right")
  PAUSE_S   — Wartezeit zwischen Posen in Sekunden
  STIFFNESS — Drive-Steifigkeit (höher = steifer Halt)
  DAMPING   — Drive-Dämpfung (verhindert Schwingen)
"""
import asyncio
import os
import importlib.util

import omni.kit.app   # type: ignore
import omni.usd       # type: ignore
from pxr import UsdPhysics  # type: ignore

# ── Parameter ─────────────────────────────────────────────────────────────────
SIDE      = "right"
PAUSE_S   = 2.0
STIFFNESS = 200.0
DAMPING   = 20.0
# ─────────────────────────────────────────────────────────────────────────────

def _find_project_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    for candidate in [
        os.path.expanduser("~/repos/pib-hand-sim"),
        os.path.expanduser("~/pib-hand-sim"),
        os.path.expanduser("~/projects/pib-hand-sim"),
    ]:
        if os.path.isfile(os.path.join(candidate, "config", "pib_hand_config.py")):
            return candidate
    raise FileNotFoundError(
        "pib-hand-sim Projektverzeichnis nicht gefunden. "
        "Env-Variable PIB_HAND_SIM_ROOT=<Pfad> setzen."
    )

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_root = _find_project_root()
_cfg  = _load("pib_hand_config",     os.path.join(_root, "config",    "pib_hand_config.py"))
_ctrl = _load("manual_control_hand", os.path.join(_root, "isaac_sim", "manual_control_hand.py"))

GRASP_POSES          = _cfg.GRASP_POSES
HAND_DOFS            = _cfg.HAND_DOFS
ROBOT_PRIM_PATH      = _cfg.ROBOT_PRIM_PATH
JOINT_SIGN           = _cfg.JOINT_SIGN
servo_pose_to_joints = _cfg.servo_pose_to_joints

get_robot         = _ctrl.get_robot
move_to_pose      = _ctrl.move_to_pose
print_joint_state = _ctrl.print_joint_state


# ── Drive-Funktionen direkt hier (keine Abhängigkeit von _ctrl nötig) ─────────

def setup_drives(side: str, stiffness: float, damping: float) -> None:
    """Setzt Steifigkeit und Dämpfung aller Handgelenke über USD DriveAPI."""
    stage = omni.usd.get_context().get_stage()
    for name in HAND_DOFS[side]["names"]:
        prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
        if not prim.IsValid():
            print(f"[WARN] Prim nicht gefunden: {name}")
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        drive.GetStiffnessAttr().Set(stiffness)
        drive.GetDampingAttr().Set(damping)


def set_drive_targets(joint_dict: dict, side: str) -> None:
    """Übergibt Sollwinkel an USD Drives — Gelenk hält Position physikbasiert."""
    stage = omni.usd.get_context().get_stage()
    names = HAND_DOFS[side]["names"]
    for name, angle_deg in joint_dict.items():
        if name not in names:
            continue
        prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
        if not prim.IsValid():
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            continue
        # USD DriveAPI nimmt Grad, mit JOINT_SIGN-Kompensation
        drive.GetTargetPositionAttr().Set(JOINT_SIGN * float(max(0.0, min(90.0, angle_deg))))


# ── Test ──────────────────────────────────────────────────────────────────────

async def _wait(seconds: float) -> None:
    app    = omni.kit.app.get_app()
    frames = max(1, int(seconds * 60))
    for _ in range(frames):
        await app.next_update_async()


async def run_test() -> None:
    print(f"\n{'='*60}")
    print(f"pib Hand-Pose-Test — Seite: {SIDE.upper()}")
    print(f"Posen: {list(GRASP_POSES.keys())}")
    print(f"Pause: {PAUSE_S}s  |  stiffness={STIFFNESS}  damping={DAMPING}")
    print(f"{'='*60}\n")

    robot = get_robot()

    # Drives einmal konfigurieren — Gelenke halten danach Position gegen Kräfte
    setup_drives(SIDE, STIFFNESS, DAMPING)
    print("Drives konfiguriert.\n")

    pose_sequence = ["open"] + [p for p in GRASP_POSES if p != "open"]

    for pose_name in pose_sequence:
        print(f"── Pose: {pose_name} ──────────────────────────────────────────")
        servo_dict = GRASP_POSES[pose_name]
        joint_dict = servo_pose_to_joints(servo_dict, SIDE)
        print(f"   Servo-Werte: {servo_dict}")

        await move_to_pose(joint_dict, duration_s=1.0, side=SIDE, robot=robot)
        set_drive_targets(joint_dict, side=SIDE)

        print_joint_state(side=SIDE, robot=robot)
        await _wait(PAUSE_S)

    # Zurück zu Open
    print("── Zurück zur Open-Pose ──────────────────────────────────────────")
    open_joints = servo_pose_to_joints(GRASP_POSES["open"], SIDE)
    await move_to_pose(open_joints, duration_s=1.0, side=SIDE, robot=robot)
    set_drive_targets(open_joints, side=SIDE)
    print_joint_state(side=SIDE, robot=robot)

    print(f"\n{'='*60}")
    print("Test abgeschlossen.")
    print("Falls Gelenke in falsche Richtung: JOINT_SIGN in pib_hand_config.py prüfen")
    print("Falls Gelenke sich nicht bewegen:  unfix_joints.py ausführen")
    print(f"{'='*60}\n")


asyncio.ensure_future(run_test())
