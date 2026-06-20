"""
setup_stage.py — Stage-Setup für pib in Isaac Sim.

Im Script Editor ausführen um:
  1. Physics Scene, Boden und Licht einzurichten
  2. Joint-Drives für alle Gelenke zu konfigurieren (Stiffness/Damping)
  3. Initiale Pose (Hände offen, Körper neutral) als Drive-Target zu setzen

Danach Stage speichern (Ctrl+S), dann Play drücken.

Importierbar von _launch_helper.py — _SKIP_AUTO_SETUP = True (vor exec_module
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
        if (ancestor / "config" / "pib_hand_config.py").is_file():
            return str(ancestor)
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config.py").is_file():
            return str(candidate)
    raise FileNotFoundError("pib-hand-sim nicht gefunden. PIB_HAND_SIM_ROOT setzen.")

_root = _find_project_root()
_spec = importlib.util.spec_from_file_location("pib_hand_config", f"{_root}/config/pib_hand_config.py")
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
    Setzt Stiffness und Damping für alle PhysicsRevoluteJoint-Prims.

    Klassifizierung nach DOF-Name:
      head      → stiffness=3000, damping=150
      shoulder/upper_arm/elbow/forearm → 5000 / 200
      wrist     → 2000 / 100
      rotator   → 1000 / 50   (Daumen CMC)
      proximal/distal/tip → 500 / 20  (alle Fingerglieder)

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
        count += 1

    print(f"configure_drives: {count} Joints konfiguriert")
    return count


def fix_joint_limits(stg) -> int:
    """
    Invertiert die Limits aller PhysicsRevoluteJoints: new_lower=-old_upper, new_upper=-old_lower.

    Systematischer Fehler beim Onshape-Import: Isaac interpretiert die Drehachse
    aller Gelenke entgegengesetzt zu Onshape. Die Limits aus Onshape gelten in
    Onshape-Konvention — nach der Invertierung stimmen sie mit den tatsächlichen
    Isaac-Targets überein.

    Beispiel: Onshape [0°, 90°]   →  Isaac [-90°, 0°]
              Onshape [-45°, 90°]  →  Isaac [-90°, 45°]
              Onshape [-90°, 90°]  →  Isaac [-90°, 90°]  (symmetrisch → unverändert)

    Idempotenz: Custom-Data-Flag "pib_limits_inverted" wird pro Prim gesetzt und
    beim nächsten Aufruf geprüft. Bleibt nach Ctrl+S im USD erhalten.
    Wert-basierte Guards versagen bei asymmetrischen Limits (z.B. [-90°, 45°]).
    """
    _FLAG = "pib_limits_inverted"
    count = 0
    for prim in stg.Traverse():
        if prim.GetTypeName() != "PhysicsRevoluteJoint":
            continue
        cd = prim.GetCustomData()
        if cd and cd.get(_FLAG):
            continue  # Bereits invertiert (Flag gesetzt)
        lower_attr = prim.GetAttribute("physics:lowerLimit")
        upper_attr = prim.GetAttribute("physics:upperLimit")
        if not (lower_attr and upper_attr):
            continue
        old_lower = lower_attr.Get()
        old_upper = upper_attr.Get()
        lower_attr.Set(-old_upper)
        upper_attr.Set(-old_lower)
        new_cd = dict(cd) if cd else {}
        new_cd[_FLAG] = True
        prim.SetCustomData(new_cd)
        count += 1
    print(f"fix_joint_limits: {count} Gelenke invertiert")
    return count


def set_initial_pose(stg) -> None:
    """
    Setzt initiale Drive-Targets (in Grad, USD-Konvention ohne JOINT_SIGN):
      - Hände offen: alle Finger 0°
      - Ellbogen leicht angewinkelt: 30° (visuell verifizieren — je nach
        USD-Achse kann positiv = strecken oder beugen bedeuten; ggf. auf -30°
        ändern)
      - Alles andere: 0° (T-Pose / neutral)
    """
    initial_targets: dict = {
        "dof_elbow_left":  30.0,
        "dof_elbow_right": 30.0,
    }
    count = 0
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        name   = prim.GetPath().name
        target = initial_targets.get(name, 0.0)

        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if drive:
            drive.GetTargetPositionAttr().Set(target)
            count += 1

    print(f"set_initial_pose: {count} Drive-Targets gesetzt (Ellbogen je 30°, Rest 0°)")


def setup_all(stg) -> None:
    configure_physics_scene(stg)
    configure_ground(stg)
    configure_lights(stg)
    configure_drives(stg)
    fix_joint_limits(stg)
    set_initial_pose(stg)


# ── Script-Editor-Block ───────────────────────────────────────────────────────
# Wird übersprungen wenn _launch_helper.py dieses Modul importiert
# (setzt _SKIP_AUTO_SETUP = True vor exec_module).
if not globals().get("_SKIP_AUTO_SETUP"):
    setup_all(stage)
    print("\nSetup abgeschlossen. Stage speichern (Ctrl+S), dann Play drücken.")
