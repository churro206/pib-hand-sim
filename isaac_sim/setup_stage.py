"""
setup_stage.py — Stage-Setup für pib in Isaac Sim.

Im Script Editor ausführen um:
  1. Physics Scene, Boden und Licht einzurichten
  2. Joint-Drives zu konfigurieren — v5: Servo-Aktuatormodell aus Datenblättern
     (ADR-012), passive Mimic-Folgegelenke (ADR-011); v4: Referenzwerte von 0fdbc62
  3. Mimic Joints (v5), Gelenk-Limits und Initialpose (T-Pose, alle Targets 0°) zu setzen

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


# ── v4: Referenz-Drives (unverändert seit 0fdbc62) ────────────────────────────
# v4 bleibt der verifizierte Referenzstand: diese Gains, maxForce=inf, keine Armature/
# Geschwindigkeitsgrenze. Das Servo-Aktuatormodell (unten) gilt nur für v5 — v4-Namen
# haben das Präfix "dof_".

def _v4_gains(name: str) -> tuple:
    """(stiffness Nm/°, damping Nm·s/°) für v4-Gelenke."""
    n = name.lower()
    if "head" in n:
        return 3000.0, 150.0
    if any(k in n for k in ("shoulder", "upper_arm", "elbow", "forearm")):
        return 5000.0, 200.0
    if "wrist" in n:
        return 2000.0, 100.0
    if "rotator" in n:
        return 1000.0, 50.0
    if any(k in n for k in ("proximal", "distal", "tip")):
        return 500.0, 20.0
    return 1000.0, 50.0                                 # Fallback


# ── v5: Servo-Aktuatormodell (ADR-012) ────────────────────────────────────────
# Datenblattwerte, Gelenkgruppen und Rezept stehen in config/pib_hand_config_v5.py
# (SERVOS, V5_ACTUATORS, servo_actuator) — eine Quelle für Isaac Sim und Isaac Lab.
# Hier werden nur die Prim-Einheiten (Nm/°, Nm·s/°, °/s) verwendet.
_spec5 = importlib.util.spec_from_file_location("pib_hand_config_v5", f"{_root}/config/pib_hand_config_v5.py")
_cfg5  = importlib.util.module_from_spec(_spec5)
_spec5.loader.exec_module(_cfg5)
FOLLOWER_ARMATURE_KGM2 = _cfg5.FOLLOWER_ARMATURE_KGM2
FOLLOWER_MAX_VELOCITY_DEG_S = _cfg5.FOLLOWER_MAX_VELOCITY_DEG_S


def _v5_actuator(name: str):
    """
    Parameter eines servo-getriebenen v5-Gelenks in Prim-Einheiten als dict (servo,
    stiffness, damping, max_force, armature, max_velocity), sonst None.
    """
    act = _cfg5.servo_actuator(name)
    if act is None:
        return None
    return {"servo": act["servo"], "stiffness": act["stiffness_deg"],
            "damping": act["damping_deg"], "max_force": act["max_force"],
            "armature": act["armature"], "max_velocity": act["max_velocity_deg"]}


# ── Mimic Joints (Stufe 1: linear, nur v5) ────────────────────────────────────
# Folgegelenk -> (Referenzgelenk, gearing, offset). PhysX-Formel (aus
# generatedSchema.usda): q_folge + gearing * q_referenz + offset = 0.
# gearing=-1, offset=0  =>  theta_folge = theta_referenz. Exakt bei 0° und 90°,
# in der Mitte weicht die reale Viergelenk-Kopplung bis ~10° (PIP) / ~22° (DIP)
# ab (tendondrive/finger_analytisch.py). Einziger Ort für Gearing/Offset —
# eine spätere adaptive Stufe 2 ändert nur diese Werte.
# v4-Gelenke (dof_-Präfix) sind bewusst nicht enthalten.
MIMIC_GEARING = -1.0
MIMIC_OFFSET = 0.0


def _build_mimic_joints() -> dict:
    joints = {}
    for side in ("left", "right"):
        for finger in ("index", "middle", "ring", "pinky"):
            joints[f"{finger}_{side}_distal"] = (f"{finger}_{side}_proximal", MIMIC_GEARING, MIMIC_OFFSET)  # PIP <- MCP
            joints[f"{finger}_{side}_tip"] = (f"{finger}_{side}_distal", MIMIC_GEARING, MIMIC_OFFSET)       # DIP <- PIP
        joints[f"thumb_{side}_tip"] = (f"thumb_{side}_proximal", MIMIC_GEARING, MIMIC_OFFSET)               # IP  <- MCP
    return joints


MIMIC_JOINTS = _build_mimic_joints()

# Mimic-Instanzname je physics:axis des Gelenk-Prims (Mehrfach-Apply-Schema)
_MIMIC_AXIS = {"X": "rotX", "Y": "rotY", "Z": "rotZ"}


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
    Setzt die Antriebe aller PhysicsRevoluteJoint-Prims:
      v4 (Präfix "dof_")       → _v4_gains, maxForce=inf (Referenzstand, unverändert)
      v5 Mimic-Folgegelenke    → passiv: Stiffness/Damping 0, Armature/Geschwindigkeit
                                 aus FOLLOWER_* (ADR-011)
      v5 Servo-Gelenke         → Servo-Aktuatormodell aus V5_ACTUATORS (ADR-012)

    Returns: Anzahl konfigurierter Joints
    """
    count = 0
    groups = {}            # Ausgabe: (servo, stiffness, damping) -> Gelenkanzahl
    unknown = []
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        name = prim.GetPath().name
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")

        if name.startswith("dof_"):
            stiffness, damping = _v4_gains(name)
            drive.GetStiffnessAttr().Set(stiffness)
            drive.GetDampingAttr().Set(damping)
            drive.GetMaxForceAttr().Set(float("inf"))
            groups[("v4", stiffness, damping)] = groups.get(("v4", stiffness, damping), 0) + 1
            count += 1
            continue

        joint_api = PhysxSchema.PhysxJointAPI.Apply(prim)
        if name in MIMIC_JOINTS:
            # Passiv — ein aktiver Antrieb würde gegen die Zwangsbedingung arbeiten.
            drive.GetStiffnessAttr().Set(0.0)
            drive.GetDampingAttr().Set(0.0)
            drive.GetMaxForceAttr().Set(float("inf"))
            joint_api.CreateArmatureAttr().Set(FOLLOWER_ARMATURE_KGM2)
            joint_api.CreateMaxJointVelocityAttr().Set(FOLLOWER_MAX_VELOCITY_DEG_S)
            groups[("Mimic passiv", 0.0, 0.0)] = groups.get(("Mimic passiv", 0.0, 0.0), 0) + 1
            count += 1
            continue

        act = _v5_actuator(name)
        if act is None:
            unknown.append(name)
            continue
        drive.GetStiffnessAttr().Set(act["stiffness"])
        drive.GetDampingAttr().Set(act["damping"])
        drive.GetMaxForceAttr().Set(act["max_force"])
        joint_api.CreateArmatureAttr().Set(act["armature"])
        joint_api.CreateMaxJointVelocityAttr().Set(act["max_velocity"])
        key = (act["servo"], round(act["stiffness"], 4), round(act["damping"], 4))
        groups[key] = groups.get(key, 0) + 1
        count += 1

    print(f"configure_drives: {count} Joints konfiguriert")
    for (label, k, d), n in sorted(groups.items(), key=lambda item: str(item[0])):
        print(f"  {n:2d}x {label:<13} stiffness {k:g} Nm/°, damping {d:g} Nm·s/°")
    if unknown:
        print(f"  WARNUNG: keine Aktuator-Zuordnung für {unknown} — Antrieb unverändert")
    return count


def configure_mimic_joints(stg) -> int:
    """
    Legt PhysxMimicJointAPI an allen Folgegelenken aus MIMIC_JOINTS an
    (PIP<-MCP, DIP<-PIP, Daumen-IP<-MCP, beide Seiten = 18 Gelenke). Idempotent.
    Auf einer Stage ohne diese Gelenke (v4) passiert nichts.

    Instanzname = Achse des Folgegelenks (aus physics:axis gelesen, nicht
    angenommen). Antriebe der Folgegelenke setzt configure_drives auf 0 —
    vorher aufrufen, danach Stop -> Play, damit PhysX die Zwangsbedingung lädt.

    Returns: Anzahl konfigurierter Mimic-Gelenke
    """
    joints = {}
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if is_revolute and prim.GetPath().name in MIMIC_JOINTS:
            joints[prim.GetPath().name] = prim

    def _axis(prim) -> str:
        raw = prim.GetAttribute("physics:axis").Get()
        if raw not in _MIMIC_AXIS:
            raise RuntimeError(f"{prim.GetPath()}: physics:axis = {raw!r}, erwartet X/Y/Z")
        return _MIMIC_AXIS[raw]

    count = 0
    for follower, (reference, gearing, offset) in MIMIC_JOINTS.items():
        follower_prim = joints.get(follower)
        if follower_prim is None:
            continue
        reference_prim = next((p for p in stg.Traverse()
                               if p.GetPath().name == reference and p.GetTypeName() == "PhysicsRevoluteJoint"), None)
        if reference_prim is None:
            print(f"configure_mimic_joints: Referenzgelenk {reference} für {follower} nicht gefunden — übersprungen")
            continue

        mimic = PhysxSchema.PhysxMimicJointAPI.Apply(follower_prim, _axis(follower_prim))
        mimic.CreateGearingAttr().Set(gearing)
        mimic.CreateOffsetAttr().Set(offset)
        mimic.CreateReferenceJointAxisAttr().Set(_axis(reference_prim))
        mimic.GetReferenceJointRel().SetTargets([reference_prim.GetPath()])
        count += 1

    print(f"configure_mimic_joints: {count} Mimic-Gelenke konfiguriert (gearing={MIMIC_GEARING:g}, offset={MIMIC_OFFSET:g})")
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
# Das galt ausdrücklich nur für v4 -- siehe v5-Block unten, dort weicht
# upper_arm_left wieder ab (v5 IST dort symmetrisch).
#
# v5-Einträge (kein "dof_"-Präfix, siehe config/pib_hand_config_v5.py für die
# Herleitung) seit dieser Session ergänzt: _BODY_LIMITS wurde zuvor nur mit den
# v4-Werten befüllt, aber für v4 UND v5 gemeinsam verwendet (set_joint_limits()
# arbeitet namensbasiert über stg.Traverse(), keine Versionsunterscheidung). Dadurch
# bekam v5 fälschlich v4-Limits aufgezwungen, wo die echte v5-URDF abweicht:
# upper_arm_left war fälschlich auf [0°,90°] eingeschränkt (echtes v5-Limit:
# [-90°,90°], symmetrisch zu upper_arm_right), wrist_left/wrist_right standen auf
# [0°,90°] statt dem echten v5-Limit [-90°,30°] (beide Seiten gleichermaßen
# betroffen, kein Links/Rechts-Unterschied). shoulder_horizontal_right [0°,90°] ist
# dagegen in BEIDEN Versionen (v4 UND v5 URDF) identisch und keine Abweichung --
# keine Korrektur nötig, siehe config/pib_hand_config_v5.py.
#
# wrist_left/wrist_right v5 (2026-10-04): [-60°, 0°], in Onshape korrigiert. Das
# Handgelenk wird über ein Pleuel angetrieben, das mechanisch nur 60° Schwenk zulässt
# (config/pib_hand_config_v5.py → WRIST_LINKAGE). Vorzeichen-Ausnahme: -60° = voll
# nach innen gebeugt, 0° = gestreckt (docs/conventions.md).

_HAND_KEYWORDS = ("proximal", "distal", "tip", "rotator")

_BODY_LIMITS = {
    # v4 (dof_-Präfix, Quelle: pib_description_v4/urdf/pib_upperbody.urdf)
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
    # v5 (kein Präfix, Quelle: pib_upperbody_urdf_v5/robot.urdf, siehe
    # config/pib_hand_config_v5.py)
    "head_horizontal":           (-90.0,  90.0),
    "head_vertical":             (-45.0,  70.0),
    "shoulder_vertical_left":    (-90.0,  90.0),
    "shoulder_horizontal_left":  (-90.0,  90.0),
    "upper_arm_left":            (-90.0,  90.0),
    "elbow_left":                (-45.0,  90.0),
    "forearm_left":              (-90.0,  90.0),
    "wrist_left":                (-60.0,   0.0),
    "shoulder_vertical_right":   (-90.0,  90.0),
    "shoulder_horizontal_right": (  0.0,  90.0),
    "upper_arm_right":           (-90.0,  90.0),
    "elbow_right":               (-45.0,  90.0),
    "forearm_right":             (-90.0,  90.0),
    "wrist_right":               (-60.0,   0.0),
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
    configure_mimic_joints(stg)
    set_joint_limits(stg)
    set_initial_pose(stg)


# ── Script-Editor-Block ───────────────────────────────────────────────────────
# Wird übersprungen wenn start.py dieses Modul importiert
# (setzt _SKIP_AUTO_SETUP = True vor exec_module).
if not globals().get("_SKIP_AUTO_SETUP"):
    setup_all(stage)
    print("\nSetup abgeschlossen. Stage speichern (Ctrl+S), dann Play drücken.")
