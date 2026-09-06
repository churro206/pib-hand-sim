"""
setup_stage.py — Stage-Setup für pib in Isaac Sim.

Im Script Editor ausführen um:
  1. Physics Scene, Boden und Licht einzurichten
  2. Joint-Drives für alle Gelenke zu konfigurieren (Stiffness/Damping/MaxForce)
  3. Initiale Pose (T-Pose, alle Targets 0°) als Drive-Target zu setzen

Danach Stage speichern (Ctrl+S), dann Play drücken.

Importierbar von start.py — _SKIP_AUTO_SETUP = True (vor exec_module
setzen) verhindert automatische Ausführung beim Import.
"""
import os
import importlib.util
from pathlib import Path

import omni.usd  # type: ignore
from pxr import UsdGeom, UsdLux, UsdPhysics, PhysxSchema, Gf  # type: ignore

stage = omni.usd.get_context().get_stage()

# ── Config laden ──────────────────────────────────────────────────────────────
def _find_project_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    stage_file = Path(stage.GetRootLayer().realPath)
    for ancestor in [stage_file.parent, stage_file.parent.parent]:
        if (ancestor / "config" / "pib_hand_config_v4.py").is_file():
            return str(ancestor)
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config_v4.py").is_file():
            return str(candidate)
    raise FileNotFoundError("pib-hand-sim nicht gefunden. PIB_HAND_SIM_ROOT setzen.")

_root = _find_project_root()
_spec = importlib.util.spec_from_file_location("pib_hand_config_v4", f"{_root}/config/pib_hand_config_v4.py")
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)
ROBOT_PRIM_PATH = _cfg.ROBOT_PRIM_PATH


# ── Drive-Klassifizierung ─────────────────────────────────────────────────────

def _classify_dof(name: str) -> tuple:
    """Gibt (stiffness, damping) für einen DOF-Namen zurück."""
    n = name.lower()
    if "head" in n:
        return 3000.0, 150.0
    if any(k in n for k in ("shoulder", "upper_arm", "elbow", "forearm")):
        return 5000.0, 200.0
    if "wrist" in n:
        return 2000.0, 100.0
    if "rotator" in n:                                  # dof_thumb_*_rotator
        return 1000.0, 50.0
    if any(k in n for k in ("proximal", "distal", "tip")):
        return 500.0, 20.0
    return 1000.0, 50.0                                 # Fallback


# ── Setup-Funktionen ──────────────────────────────────────────────────────────

def configure_physics_scene(stg) -> None:
    path = "/World/PhysicsScene"
    if not stg.GetPrimAtPath(path):
        scene = UsdPhysics.Scene.Define(stg, path)
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
        scene.CreateGravityMagnitudeAttr(9.81)
        PhysxSchema.PhysxSceneAPI.Apply(stg.GetPrimAtPath(path))
        print("Physics Scene erstellt")
    else:
        print("Physics Scene bereits vorhanden")


def configure_ground(stg) -> None:
    path = "/World/GroundPlane"
    if not stg.GetPrimAtPath(path):
        ground = UsdGeom.Mesh.Define(stg, path)
        ground.CreatePointsAttr([(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0)])
        ground.CreateFaceVertexCountsAttr([4])
        ground.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        ground.CreateNormalsAttr([(0, 0, 1)] * 4)
        UsdPhysics.CollisionAPI.Apply(stg.GetPrimAtPath(path))
        print("Boden erstellt")
    else:
        print("Boden bereits vorhanden")


def configure_lights(stg) -> None:
    dome = "/World/DomeLight"
    if not stg.GetPrimAtPath(dome):
        d = UsdLux.DomeLight.Define(stg, dome)
        d.CreateIntensityAttr(500.0)
        print("Dome Light erstellt")
    else:
        print("Dome Light bereits vorhanden")

    sun = "/World/DistantLight"
    if not stg.GetPrimAtPath(sun):
        s = UsdLux.DistantLight.Define(stg, sun)
        s.CreateIntensityAttr(1000.0)
        s.CreateAngleAttr(0.53)
        UsdGeom.XformCommonAPI(s).SetRotate(Gf.Vec3f(315.0, 0.0, 45.0))
        print("Distant Light erstellt")
    else:
        print("Distant Light bereits vorhanden")


def configure_drives(stg) -> int:
    """
    Setzt Stiffness, Damping und MaxForce für alle PhysicsRevoluteJoint-Prims.
    Funktioniert für v4 und v5 identisch (Namens-Substring-Klassifizierung,
    kein dof_-Präfix nötig, siehe _classify_dof).

    Klassifizierung nach DOF-Name (Stiffness / Damping):
      head      → stiffness=3000, damping=150
      shoulder/upper_arm/elbow/forearm → 5000 / 200
      wrist     → 2000 / 100
      rotator   → 1000 / 50   (Daumen CMC)
      proximal/distal/tip → 500 / 20  (alle Fingerglieder)

    MaxForce (physics:maxForce) wird auf unbegrenzt (inf) gesetzt — das ist
    der USD-Physics-Schema-Default und das Verhalten, das v4 schon immer
    hatte (dort wurde nie explizit ein maxForce gesetzt). Der Isaac-URDF-
    Importer übernimmt für v5 offenbar den effort-Wert aus der URDF direkt
    als Kappung (z.B. 10 Nm an der Schulter — reichte nicht, um die Trägheit
    des Arms zu überwinden). Bewusst kein "realistischer" Nm-Wert geraten —
    stellt nur wieder den unbegrenzten v4-Zustand her, siehe current-sprint.md.

    Returns: Anzahl konfigurierter Joints
    """
    count = 0
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        name = prim.GetPath().name
        stiffness, damping = _classify_dof(name)

        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")

        drive.GetStiffnessAttr().Set(stiffness)
        drive.GetDampingAttr().Set(damping)
        drive.GetMaxForceAttr().Set(float("inf"))
        count += 1

    print(f"configure_drives: {count} Joints konfiguriert (Stiffness/Damping/MaxForce=inf)")
    return count


# ── Gelenk-Limits ─────────────────────────────────────────────────────────────
# Seit isaac_sim/tools/flip_joint_sign.py (einmalig in der USD ausgeführt)
# stimmen Onshape- und Isaac-Konvention überein — keine Spiegelung mehr nötig,
# das sind direkt die Onshape-Limits (positiv = Flexion/Heben/Vorne).
#
# dof_upper_arm_left/dof_shoulder_horizontal_right korrigiert gegenüber dem
# alten (gespiegelten) Stand: die vorherige Tabelle hatte hier symmetrisch
# [-90°,90°] geschätzt, die echte Onshape-Quelle ist einseitig [0°,90°]
# (verifiziert gegen ros2_ws/src/pib_description_v4/urdf/pib_upperbody.urdf).

_HAND_KEYWORDS = ("proximal", "distal", "tip", "rotator")

_BODY_LIMITS = {
    "dof_head_horizontal":           (-90.0,  90.0),
    "dof_head_vertical":             (-45.0,  70.0),
    "dof_shoulder_vertical_left":    (-90.0,  90.0),
    "dof_shoulder_horizontal_left":  (-90.0,  90.0),
    "dof_upper_arm_left":            (  0.0,  90.0),
    "dof_elbow_left":                (-45.0,  90.0),
    "dof_forearm_left":              (-90.0,  90.0),
    "dof_wrist_left":                (  0.0,  90.0),
    "dof_shoulder_vertical_right":   (-90.0,  90.0),
    "dof_shoulder_horizontal_right": (  0.0,  90.0),
    "dof_upper_arm_right":           (-90.0,  90.0),
    "dof_elbow_right":               (-45.0,  90.0),
    "dof_forearm_right":             (-90.0,  90.0),
    "dof_wrist_right":               (  0.0,  90.0),
}


def set_joint_limits(stg) -> int:
    """
    Setzt Gelenk-Limits (Onshape-Konvention, seit flip_joint_sign.py identisch
    mit der Isaac-Konvention). Idempotent: setzt immer denselben Zielwert,
    kein Toggle, kein Flag.

    Hand/Fingergelenke (proximal/distal/tip/rotator): [0°, 90°]
    Körpergelenke: aus _BODY_LIMITS
    """
    count = 0
    for prim in stg.Traverse():
        if prim.GetTypeName() != "PhysicsRevoluteJoint":
            continue
        name = prim.GetPath().name
        lower_attr = prim.GetAttribute("physics:lowerLimit")
        upper_attr = prim.GetAttribute("physics:upperLimit")
        if not (lower_attr and upper_attr):
            continue
        if any(k in name for k in _HAND_KEYWORDS):
            lower_attr.Set(0.0)
            upper_attr.Set(90.0)
            count += 1
        elif name in _BODY_LIMITS:
            lower, upper = _BODY_LIMITS[name]
            lower_attr.Set(lower)
            upper_attr.Set(upper)
            count += 1
    print(f"set_joint_limits: {count} Gelenke konfiguriert")
    return count


def set_initial_pose(stg) -> None:
    """
    Setzt alle Drive-Targets auf 0° (T-Pose, volle Streckung) — Onshape-
    Konvention seit flip_joint_sign.py, positiv = Flexion. Kein Sonderfall
    mehr für den Ellbogen (war vorher 30°, das war nie begründet). Traversiert
    generisch über alle PhysicsRevoluteJoint-Prims, kein Namensabgleich nötig
    — funktioniert für v4 und v5 identisch.
    """
    count = 0
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if drive:
            drive.GetTargetPositionAttr().Set(0.0)
            count += 1

    print(f"set_initial_pose: {count} Drive-Targets auf 0° gesetzt (T-Pose)")


def setup_all(stg) -> None:
    configure_physics_scene(stg)
    configure_ground(stg)
    configure_lights(stg)
    configure_drives(stg)
    set_joint_limits(stg)
    set_initial_pose(stg)


# ── Script-Editor-Block ───────────────────────────────────────────────────────
# Wird übersprungen wenn start.py dieses Modul importiert
# (setzt _SKIP_AUTO_SETUP = True vor exec_module).
if not globals().get("_SKIP_AUTO_SETUP"):
    setup_all(stage)
    print("\nSetup abgeschlossen. Stage speichern (Ctrl+S), dann Play drücken.")
