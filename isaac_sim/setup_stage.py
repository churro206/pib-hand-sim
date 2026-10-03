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

# Experiment-Schalter: Faktor auf Stiffness/Damping aller Körpergelenke (Kopf, Schulter,
# Oberarm, Ellbogen, Unterarm, Handgelenk). 1.0 = unverändert. Stiffness ist in Nm/GRAD
# (5000 Nm/° ≈ 2.9e5 Nm/rad) — bei leichten Gliedern weit über dem, was ein
# 60-Hz-Physikschritt stabil auflösen kann (NVIDIA: Eigenfrequenz * Zeitschritt nicht >> 1).
# Zum Testen z.B. 0.1 oder 0.02; die Testpose weicht dann unter Schwerkraft etwas ab.
ARM_GAIN_SCALE = 1.0


def _classify_dof(name: str) -> tuple:
    """Gibt (stiffness, damping) für einen DOF-Namen zurück."""
    n = name.lower()
    if "head" in n:
        return 3000.0 * ARM_GAIN_SCALE, 150.0 * ARM_GAIN_SCALE
    if any(k in n for k in ("shoulder", "upper_arm", "elbow", "forearm")):
        return 5000.0 * ARM_GAIN_SCALE, 200.0 * ARM_GAIN_SCALE
    if "wrist" in n:
        return 2000.0 * ARM_GAIN_SCALE, 100.0 * ARM_GAIN_SCALE
    if "rotator" in n:                                  # dof_thumb_*_rotator
        return 1000.0, 50.0
    if any(k in n for k in ("proximal", "distal", "tip")):
        return 500.0, 20.0
    return 1000.0, 50.0                                 # Fallback


# ST3215-Servo (reale Hardware): 30 kg·cm Stall-Torque @ 12V.
# 1 kgf·cm = 0.0980665 Nm → 30 * 0.0980665 ≈ 2.94 Nm.
# Angenommen: Betriebsspannung 12V (Servo-Spannungsbereich 6~12.6V) — bei
# abweichender realer Versorgungsspannung anpassen, Stall-Torque skaliert mit
# dem Blockierstrom (kt=11 kg·cm/A * 2.7A Blockierstrom ≈ 30 kg·cm bei den
# Datenblatt-Bedingungen), nicht einfach linear mit der Spannung.
SERVO_STALL_TORQUE_NM = 30.0 * 0.0980665  # ≈ 2.94 Nm


def _classify_max_force(name: str) -> float:
    """
    Gibt maxForce (Nm) für einen DOF-Namen zurück.

    Nur auf die Gelenke beschränkt, die für RL-Fahrplan + aktuellen
    Demonstrator-Stand relevant sind und direkt von einem eigenen Servo
    angetrieben werden: Handgelenk, Unterarmdrehung (Pronation), Daumen-
    Rotator (CMC) und alle MCP-Gelenke (proximal) — Finger wie Daumen,
    beide Seiten. Bekommen den realen ST3215-Stall-Torque.

    Rest bleibt bei inf (unverändert, bewusst):
    - Kopf/Schulter/Oberarm/Ellbogen — nicht Teil dieser Abgrenzung (Leon:
      "der Rest bleibt erstmal so"), noch nicht angegangen.
    - PIP/DIP/IP (distal/tip) — mechanisch über das Viergelenkgetriebe an
      den jeweiligen MCP GEKOPPELT, kein eigener Servo. Laufen als passive
      Mimic Joints (siehe MIMIC_JOINTS unten): der MCP-Servo trägt die
      Last über die Zwangsbedingung, ein eigenes maxForce hätte hier keine
      physikalische Basis.
    """
    n = name.lower()
    if "wrist" in n:
        return SERVO_STALL_TORQUE_NM
    if "forearm" in n:
        return SERVO_STALL_TORQUE_NM
    if "rotator" in n:                                  # dof_thumb_*_rotator
        return SERVO_STALL_TORQUE_NM
    if "proximal" in n:                                 # alle MCP-Gelenke
        return SERVO_STALL_TORQUE_NM
    return float("inf")


# ── Servo-Dynamik der MCP-Gelenke (ST3215) ────────────────────────────────────
# Aus dem Datenblatt: Leerlaufdrehzahl 0.222 s/60° @12V (45 RPM) = 270°/s.
# Ohne Begrenzung beschleunigt der gesättigte 2.94-Nm-Antrieb den leichten Finger
# (Trägheit ~5e-5 kg·m², Annahme aus PROMPT_mimic_joints.md) auf viele hundert
# Grad pro Physikschritt und prallt dann auf den Tisch (Chattern, NaN) — siehe
# NVIDIA Articulation Stability Guide: Max-Force/Geschwindigkeit nach Aktuator-
# Spezifikation, Armature = Rotorträgheit * Übersetzung^2, Antriebs-Eigenfrequenz
# * Zeitschritt nicht >> 1.
#
# Einheiten (USD-Schema): Angular-Drive stiffness = Nm/GRAD, damping = Nm·s/GRAD,
# physxJoint:maxJointVelocity = °/s, physxJoint:armature = kg·m².
SERVO_NO_LOAD_SPEED_DEG_S = 60.0 / 0.222          # ≈ 270 °/s
# ANNAHME, nicht gemessen: reflektierte Rotorträgheit des geared Servos. Startwert
# 5e-3 kg·m² (Robotiq-Beispiel der NVIDIA-Doku; plausible Größenordnung für kleinen
# Motor mit Getriebe ~1:345). Bei Bedarf an realem Servo-Verhalten nachziehen.
SERVO_ARMATURE_KGM2 = 5.0e-3
# Stiffness so gewählt, dass maxForce (Stall-Torque) bei 5° Positionsfehler erreicht
# wird (NVIDIA-Rezept: stiffness = maxForce / Ziel-Fehler); Damping für kritische
# Dämpfung (ζ=1) mit der Armature als Trägheit.
SERVO_SATURATION_ERROR_DEG = 5.0
_RAD_PER_DEG = 0.017453292519943295

# Experiment-Schalter (je Lauf nur EINEN ändern, dann start.py → Stop → Play → Test):
#   Referenz "alt":  alle drei False  → Gains 500/20, keine Armature, kein Geschw.-Limit
SERVO_GAINS_ENABLED = True         # Stiffness/Damping aus Datenblatt-Rezept statt 500/20
SERVO_ARMATURE_ENABLED = True      # physxJoint:armature an den MCPs
SERVO_MAX_VELOCITY_ENABLED = True  # physxJoint:maxJointVelocity an den MCPs (270 °/s)
# Folgegelenke (PIP/DIP/IP): Limits [-2°, 95°] statt [0°, 90°] — Kontakt kann DIP unter 0°
# drücken, harte Grenze + Mimic + Kontakt widersprechen sich dann (PROMPT_mimic_joints.md,
# Abschnitt 3 Punkt 6).
FOLLOWER_LIMITS_WIDE = False
# Gleiche Servo-Behandlung auch für Handgelenk, Unterarmdrehung und Daumen-Rotator (alle
# ST3215, maxForce 2.94 Nm bei Stiffness 2000-5000 Nm/°): ein bei Winkelfehler ~0.001°
# gesättigter Antrieb wirkt wie ein Relais (±2.94 Nm) und kann vom Kontakt angeregt werden.
SERVO_ARM_JOINTS_ENABLED = True
# Passive Folgegelenke (PIP/DIP/IP): kleine Armature + Geschwindigkeitsgrenze. Ohne beides
# (Armature 0, maxJointVelocity 1e6 °/s) drehen sie bei Kontakt mehrfach durch, obwohl die
# Mimic-Zwangsbedingung sie an den MCP koppeln soll. ANNAHMEN, nicht gemessen:
#   Armature 5e-4 kg·m² (~10x geschätzte Fingerträgheit 5e-5, 1/10 der MCP-Armature),
#   maxJointVelocity 500 °/s (reale Kopplung: bis 1.67x MCP-Geschwindigkeit von 270 °/s ≈ 450 °/s).
FOLLOWER_STABILIZE_ENABLED = True
FOLLOWER_ARMATURE_KGM2 = 5.0e-4
FOLLOWER_MAX_VELOCITY_DEG_S = 500.0
_PHYSX_DEFAULT_MAX_JOINT_VELOCITY = 1.0e6   # Schema-Default, siehe generatedSchema.usda


def _classify_servo_dynamics(name: str):
    """
    ((stiffness Nm/°, damping Nm·s/°) oder None, armature kg·m², maxJointVelocity °/s)
    für servo-getriebene MCP-Gelenke (proximal, Finger + Daumen, beide Seiten), sonst
    None. Deaktivierte Experiment-Schalter liefern die neutralen Werte (gains=None,
    armature 0, Schema-Default-Geschwindigkeit), damit ein erneuter start.py-Lauf
    in derselben Session einen früheren Zustand wirklich zurücksetzt.
    """
    n = name.lower()
    is_mcp = "proximal" in n
    is_arm_servo = SERVO_ARM_JOINTS_ENABLED and any(k in n for k in ("wrist", "forearm", "rotator"))
    if not (is_mcp or is_arm_servo):
        return None
    k_deg = SERVO_STALL_TORQUE_NM / SERVO_SATURATION_ERROR_DEG
    k_rad = k_deg / _RAD_PER_DEG
    d_rad = 2.0 * (k_rad * SERVO_ARMATURE_KGM2) ** 0.5
    gains = (k_deg, d_rad * _RAD_PER_DEG) if SERVO_GAINS_ENABLED else None
    armature = SERVO_ARMATURE_KGM2 if SERVO_ARMATURE_ENABLED else 0.0
    max_vel = SERVO_NO_LOAD_SPEED_DEG_S if SERVO_MAX_VELOCITY_ENABLED else _PHYSX_DEFAULT_MAX_JOINT_VELOCITY
    return gains, armature, max_vel


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
    Setzt Stiffness, Damping und MaxForce für alle PhysicsRevoluteJoint-Prims.
    Funktioniert für v4 und v5 identisch (Namens-Substring-Klassifizierung,
    kein dof_-Präfix nötig, siehe _classify_dof).

    Klassifizierung nach DOF-Name (Stiffness / Damping):
      head      → stiffness=3000, damping=150
      shoulder/upper_arm/elbow/forearm → 5000 / 200
      wrist     → 2000 / 100
      rotator   → 1000 / 50   (Daumen CMC)
      proximal/distal/tip → 500 / 20  (alle Fingerglieder)

    MaxForce (physics:maxForce): für Handgelenk/Unterarmdrehung/Daumen-
    Rotator/alle MCP-Gelenke jetzt der reale ST3215-Stall-Torque
    (`_classify_max_force`, ≈2.94 Nm) statt inf — das sind die Gelenke, die
    direkt von einem eigenen Servo angetrieben werden und für RL +
    Demonstrator relevant sind. Rest (Kopf/Schulter/Oberarm/Ellbogen,
    PIP/DIP/IP) bleibt bei inf, siehe `_classify_max_force`-Docstring.
    Vorherige Session hatte hier pauschal inf gesetzt (Fix für einen
    falschen URDF-effort-Import bei v5, z.B. 10 Nm an der Schulter — siehe
    current-sprint.md), das bleibt für die unverändert gelassenen Gelenke
    weiterhin so.

    Returns: Anzahl konfigurierter Joints
    """
    count = 0
    limited = 0
    servo_count = 0
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        name = prim.GetPath().name
        stiffness, damping = _classify_dof(name)
        max_force = _classify_max_force(name)
        servo = _classify_servo_dynamics(name)
        if servo and servo[0]:
            stiffness, damping = servo[0]
        if name in MIMIC_JOINTS:
            # Mimic-Folgegelenke sind passiv — ein aktiver Antrieb würde gegen
            # die Zwangsbedingung arbeiten.
            stiffness, damping = 0.0, 0.0

        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")

        drive.GetStiffnessAttr().Set(stiffness)
        drive.GetDampingAttr().Set(damping)
        drive.GetMaxForceAttr().Set(max_force)
        if name in MIMIC_JOINTS:
            joint_api = PhysxSchema.PhysxJointAPI.Apply(prim)
            joint_api.CreateArmatureAttr().Set(FOLLOWER_ARMATURE_KGM2 if FOLLOWER_STABILIZE_ENABLED else 0.0)
            joint_api.CreateMaxJointVelocityAttr().Set(
                FOLLOWER_MAX_VELOCITY_DEG_S if FOLLOWER_STABILIZE_ENABLED else _PHYSX_DEFAULT_MAX_JOINT_VELOCITY)
        if servo:
            joint_api = PhysxSchema.PhysxJointAPI.Apply(prim)
            joint_api.CreateArmatureAttr().Set(servo[1])
            joint_api.CreateMaxJointVelocityAttr().Set(servo[2])
            servo_count += 1
        count += 1
        if max_force != float("inf"):
            limited += 1

    print(f"configure_drives: {count} Joints konfiguriert "
          f"({limited} mit realem Stall-Torque ≈{SERVO_STALL_TORQUE_NM:.2f} Nm, "
          f"Rest MaxForce=inf); {servo_count} Servo-Gelenke — Gains {'Datenblatt' if SERVO_GAINS_ENABLED else '500/20 (alt)'}, "
          f"Armature {SERVO_ARMATURE_KGM2 if SERVO_ARMATURE_ENABLED else 0:g} kg·m², "
          f"maxJointVelocity {SERVO_NO_LOAD_SPEED_DEG_S if SERVO_MAX_VELOCITY_ENABLED else 'Default'}; "
          f"SERVO_ARM_JOINTS={SERVO_ARM_JOINTS_ENABLED}, FOLLOWER_STABILIZE={FOLLOWER_STABILIZE_ENABLED}, ARM_GAIN_SCALE={ARM_GAIN_SCALE:g}, "
          f"FOLLOWER_LIMITS_WIDE={FOLLOWER_LIMITS_WIDE}")
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
    "wrist_left":                (-90.0,  30.0),
    "shoulder_vertical_right":   (-90.0,  90.0),
    "shoulder_horizontal_right": (  0.0,  90.0),
    "upper_arm_right":           (-90.0,  90.0),
    "elbow_right":               (-45.0,  90.0),
    "forearm_right":             (-90.0,  90.0),
    "wrist_right":               (-90.0,  30.0),
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
        if FOLLOWER_LIMITS_WIDE and name in MIMIC_JOINTS:
            lower_attr.Set(-2.0)
            upper_attr.Set(95.0)
            count += 1
        elif any(k in name for k in _HAND_KEYWORDS):
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
