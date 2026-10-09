"""
env_cfg.py — Greifaufgabe der realen linken pib-v5-Hand (Proof of Concept).

Vorlage: Isaac Lab Dexsuite (manipulation/dexsuite, Kuka-Allegro-Lift) — Aufbau,
Belohnungsgewichte, Clip der Kontaktkraft (20 N), Aktionsart (relative Gelenkposition)
und Randomisierung von dort übernommen, aufs Nötige reduziert.

Ablauf einer Episode (4,5 s, Policy 60 Hz):
  0,0–2,0 s  Dose steht auf dem Tisch vor der Handfläche, die Policy greift
  2,0–2,5 s  Tisch senkt sich um 10 cm (≙ der Arm hebt die Hand an)
  2,5–4,5 s  Dose muss in der Hand bleiben
Hand fest (Unterarm-Basis), seitlich: Handfläche zur Dose, Daumen oben.

Asymmetric Actor-Critic: Die Policy sieht nur, was die echte Hand misst (8 Servo-
Gelenkwinkel, 5 FSR, letzte Aktion; 5 Schritte Verlauf). Der Critic sieht zusätzlich
Objektlage/-orientierung/-geschwindigkeit, Folgegelenke, Objekt-Kontaktkräfte und die Phase.
"""
import math
from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg, AssetBaseCfg, RigidObjectCfg
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.envs import mdp as base_mdp
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.managers import CurriculumTermCfg as CurrTerm
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG, SERVO_JOINTS

from isaaclab_tasks.manager_based.manipulation.dexsuite.mdp import rewards as dexsuite_rewards
from isaaclab_tasks.manager_based.manipulation.dexsuite.mdp import curriculums as dexsuite_curriculums

from . import mdp

# ── Geometrie (Hand-Root-Frame aus isaac_lab/tools/probe_geometry.py, 2026-10-04) ───
# Ohne Drehung zeigen die Finger nach −y, die Handfläche nach −z, der Daumen liegt auf
# −x. Drehung +90° um y: Handfläche → −x, Daumen → +z, Finger bleiben bei −y.
HAND_POS = (0.0, 0.0, 0.5)
HAND_ROT = (math.cos(math.pi / 4), 0.0, math.sin(math.pi / 4), 0.0)   # (w, x, y, z)

OBJECT_RADIUS = 0.03          # Dose Ø 6 cm
OBJECT_HEIGHT = 0.15
PALM_GAP = 0.035              # Handfläche ↔ Objektoberfläche (Vorgreifpose, für alle Objekte gleich)
# Tischplatte 8,5 cm unter dem Hand-Root: die Spitze des kleinen Fingers liegt bei
# −6,3 cm (tools/debug_scene.py), bei −6 cm stieß sie an den Tisch
TABLE_TOP_Z = HAND_POS[2] - 0.085
# Dosenmitte: 6,5 cm vor der Handfläche (−x), auf Höhe der Grundglieder zwischen MCP
# (y ≈ −0,31) und PIP (y ≈ −0,35), steht auf dem Tisch. Bis 2026-10-04 y = −0,32: die
# Finger zogen die Dose Richtung Handgelenk, bis sie hinten vom Tisch rutschte.
OBJECT_POS = (HAND_POS[0] - PALM_GAP - OBJECT_RADIUS, HAND_POS[1] - 0.34, TABLE_TOP_Z + OBJECT_HEIGHT / 2)
OBJECT_POS_RANGE = {"x": (-0.01, 0.01), "y": (-0.02, 0.02)}
# Tisch: endet 4 cm vor dem Hand-Root (x), damit die Hand ihn nie berührt; in y von
# 16 cm vor bis 29 cm hinter der Dose, damit eine verrutschte Dose nicht sofort fällt
TABLE_SIZE = (0.20, 0.45, 0.04)
TABLE_POS = (HAND_POS[0] - 0.04 - TABLE_SIZE[0] / 2, OBJECT_POS[1] + 0.065, TABLE_TOP_Z - TABLE_SIZE[2] / 2)

GRASP_TIME_S = 2.0
DROP_SPEED = 0.2              # m/s
DROP_DEPTH = 0.10             # m
EPISODE_S = 4.5

FSR_CLIP_N = 20.0             # Dexsuite: "contact force in finger tips is under 20N normally"
# Dose soll aufrecht bleiben (Probelauf 2026-10-04: Unterarm kippte sie auf die Handfläche).
# Seit EXP-003 nur über die Belohnung (Dexsuite: Orientierung belohnt, nicht abgebrochen);
# rot_std 0,5 rad wie Dexsuites success_reward. EXP-001/002: Abbruch bei 20° → Policy griff
# gar nicht mehr zu (experiments/).
UPRIGHT_ROT_STD = 0.5
HOLD_STD_M = 0.02            # Absinken [m] für 1 − tanh(s/std)
CONTACT_N = 1.0              # Kontaktschwelle Gegengriff (Dexsuite: threshold 1.0)


# ── Objektkatalog (Bedingungen, experiments/README.md) ───────────────────────────────────
# Seitlich greifen braucht ≥ ~15 cm Höhe: die Fingerspitzen liegen 2,5–16,5 cm über der
# Tischplatte (kleiner Finger … Daumen, tools/debug_scene.py, 2026-10-07); tiefer geht die Hand
# nicht, sonst stößt der kleine Finger an den Tisch.
# form, Maße [m] (Zylinder: Radius, Höhe; Quader: x, y, z), Drehung beim Reset [rad]
OBJECTS = {
    "zylinder_d6": {"form": "zylinder", "masse": (0.03, 0.15), "gier": (-math.pi, math.pi)},      # Dose (Training)
    "zylinder_d8": {"form": "zylinder", "masse": (0.04, 0.15), "gier": (-math.pi, math.pi)},      # dicke Dose/Becher
    # Milchpackung: eine Fläche zur Hand ±15° (so würde ein Greifplaner anfahren)
    "quader_7x7x20": {"form": "quader", "masse": (0.07, 0.07, 0.20), "gier": (-math.radians(15), math.radians(15))},
    # Testobjekte (nie im Training, EXP-013 ff.): Flasche — Ø wie im Training, aber 25 cm hoch; Saftpackung —
    # schmale Seite (6 cm) zur Hand, im Training liegt immer die breite oder eine quadratische Seite vorn
    "flasche_d7x25": {"form": "zylinder", "masse": (0.035, 0.25), "gier": (-math.pi, math.pi)},
    "saftpackung_9x6x19": {"form": "quader", "masse": (0.09, 0.06, 0.19), "gier": (-math.radians(15), math.radians(15))},
    # YCB-Testobjekte (Isaac Sim 5.1 Props/YCB/Axis_Aligned_Physics, tools/inspect_ycb.py, 2026-10-09): echte Masse und
    # Größe aus dem Asset (Zufallsmasse/-größe aus); die Assets liegen (Höhe entlang y) → aufrecht über eine Wrapper-USD,
    # die nur das Mesh dreht (drehung = rotateXYZ [°]), der Starrkörper bleibt z-oben wie bei allen Objekten (Kippwinkel,
    # Gier). masse = Bounding Box aufrecht (Tiefe zur Hand, Breite, Höhe); Reibung wie alle Objekte (Zufall 0,5–1,0).
    # Oberseite des Assets zeigt nach −y → −90° um x (+90° stellte sie auf den Kopf, Fenstertest 2026-10-09).
    # ruhelage = gemessene Ruhelage auf dem Tisch (tools/ruhelage_objekt.py, typische von 64 Umgebungen): Höhe des
    # Ursprungs über der Tischplatte [m], Neigung (Körperrahmen, w x y z) — die gescannten Unterseiten sind uneben,
    # die Collider ragen unter die sichtbare Box; so steht das Objekt bei t = 0 still, statt zu fallen/kippen.
    "ycb_003_cracker": {"form": "usd", "ycb": "003_cracker_box", "drehung": (-90, 0, 0),          # 411 g, schmale
                        "masse": (0.164, 0.072, 0.213), "gier": (-math.radians(15), math.radians(15)),   # Seite zur Hand
                        "ruhelage": {"hoehe": 0.10635, "quat": (0.99965, 0.02641, -0.00166, 0.00023)}},  # 3,1°
    "ycb_004_zucker": {"form": "usd", "ycb": "004_sugar_box", "drehung": (-90, 0, 0),             # 514 g, schmale
                       "masse": (0.093, 0.045, 0.176), "gier": (-math.radians(15), math.radians(15)),    # Seite zur Hand
                       "ruhelage": {"hoehe": 0.08735, "quat": (0.99979, 0.01307, -0.01552, 0.00069)}},   # 2,3°
    "ycb_006_senf": {"form": "usd", "ycb": "006_mustard_bottle", "drehung": (-90, 0, 0),           # 603 g, schmale
                     "masse": (0.096, 0.058, 0.191), "gier": (-math.radians(15), math.radians(15)),      # Seite zur Hand
                     "ruhelage": {"hoehe": 0.09736, "quat": (1.0, 0.0, 0.0, 0.0)}},                      # (Leon), gerade
}
# Startstellung der Hand beim Reset fast offen (seit 2026-10-09 Standard, eval-v2): Fingerbeugung 0–15° und Handgelenk
# −10–0° (bis eval-v1) ließen die Hand beim Reset im Objekt stecken (tools/analyse_reset.py: Zylinder Ø6 34 %, Ø8 44 %,
# Quader 81 %, YCB-Cracker 63 % der Starts, v. a. Mittelglieder/Spitzen und Handgelenkbeugung); so 0 %. Daumen unkritisch,
# behält 0–90° Rotator / 0–15° Beugung. Die Hand kommt wie in der Vorgreifpose fast offen an.
FINGER_START_MAX_DEG = 4.0
WRIST_START_MAX_DEG = 1.0


# Collider der gescannten YCB-Meshes (Konvex-Zerlegung) ragen bis ~2 mm unter die sichtbare Bounding Box → bündig
# gespawnt startet das Objekt im Tisch und wird herausgestoßen (Senf: +2 mm, bis 1 cm seitlich, tools/check_objekt.py);
# 3 mm höher fällt es stattdessen kurz auf den Tisch.
YCB_SPAWN_LIFT = 0.003
YCB_WRAPPER_DIR = Path(__file__).resolve().parents[2] / "logs" / "ycb_aufrecht"     # erzeugt, gitignored


def ycb_upright_usd(name: str, rot_deg: tuple[float, float, float]) -> str:
    """Wrapper-USD für ein YCB-Asset: referenziert es und dreht nur das Mesh-Kind (rotateXYZ, Skalierung bleibt);
    Starrkörper, Masse und Collider kommen unverändert aus dem Asset."""
    src = f"{ISAAC_NUCLEUS_DIR}/Props/YCB/Axis_Aligned_Physics/{name}.usd"
    child = "_" + name[1:]                                     # 003_cracker_box → _03_cracker_box (Prim im Asset)
    YCB_WRAPPER_DIR.mkdir(parents=True, exist_ok=True)
    path = YCB_WRAPPER_DIR / f"{name}_aufrecht.usda"
    path.write_text(f"""#usda 1.0
(
    defaultPrim = "Object"
    metersPerUnit = 1
    upAxis = "Z"
)

def Xform "Object" (
    prepend references = @{src}@
)
{{
    over "{child}"
    {{
        float3 xformOp:rotateXYZ = ({rot_deg[0]}, {rot_deg[1]}, {rot_deg[2]})
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ", "xformOp:scale"]
    }}
}}
""", encoding="utf-8")
    return str(path)
DEFAULT_OBJECT = "zylinder_d6"


@configclass
class SceneCfg(InteractiveSceneCfg):
    robot: ArticulationCfg = PIB_HAND_LEFT_V5_CFG.replace(
        prim_path="{ENV_REGEX_NS}/Robot",
        init_state=PIB_HAND_LEFT_V5_CFG.init_state.replace(pos=HAND_POS, rot=HAND_ROT),
    )

    object: RigidObjectCfg = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Object",
        spawn=sim_utils.CylinderCfg(
            radius=OBJECT_RADIUS,
            height=OBJECT_HEIGHT,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                solver_position_iteration_count=16,
                solver_velocity_iteration_count=0,
            ),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
            physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=0.8, dynamic_friction=0.8),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.8, 0.2, 0.2)),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=OBJECT_POS),
    )

    table: RigidObjectCfg = RigidObjectCfg(
        prim_path="{ENV_REGEX_NS}/Table",
        spawn=sim_utils.CuboidCfg(
            size=TABLE_SIZE,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.18, 0.18, 0.2)),   # dunkel: Hand hebt sich ab
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=TABLE_POS),
    )

    # Ein Sensor je Fingerspitze (= je FSR), wie Dexsuite: der Objekt-Filter (privilegierte
    # Kraft) funktioniert in Isaac Lab nur, wenn ein Sensor genau einen Prim abdeckt.
    # Link-Namen: mdp.FINGERTIP_LINKS (Daumen, Zeige, Mittel, Ring, klein).
    fsr_thumb = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/urdf_thumb_tip",
                                 filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"])
    fsr_index = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/urdf_finger_tip",
                                 filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"])
    fsr_middle = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/urdf_finger_tip_2",
                                  filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"])
    fsr_ring = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/urdf_finger_tip_3",
                                filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"])
    fsr_pinky = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/urdf_finger_tip_4",
                                 filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"])

    # Nur Optik (Leon, 2026-10-08): Kuppel schwach als Aufhelllicht und unsichtbar (schwarzer Hintergrund),
    # gerichtetes Hauptlicht schräg von oben auf der Kameraseite → Schatten und Kontrast an Fingern/Objekt
    light = AssetBaseCfg(prim_path="/World/light",
                         spawn=sim_utils.DomeLightCfg(intensity=350.0, visible_in_primary_ray=False))
    sun = AssetBaseCfg(prim_path="/World/sun", spawn=sim_utils.DistantLightCfg(intensity=1600.0, angle=1.0),
                       init_state=AssetBaseCfg.InitialStateCfg(rot=(0.9666, 0.1573, 0.2022, 0.0)))


@configclass
class ActionsCfg:
    # Dexsuite: relative Gelenkposition, scale 0,1 rad je Schritt. Handgelenk/Unterarm
    # kleiner (Ursprungs-Prompt: kein "Peitschen" des Arms). 0,1 rad ≈ 5,7° ≥ Servo-
    # Sättigungsfehler (5°) — volles Stall-Moment ist erreichbar.
    servos = base_mdp.RelativeJointPositionActionCfg(
        asset_name="robot",
        joint_names=SERVO_JOINTS,
        preserve_order=True,
        scale={"forearm_left": 0.03, "wrist_left": 0.03, ".*_left_(proximal|rotator)": 0.1},
    )


@configclass
class ObservationsCfg:
    @configclass
    class PolicyCfg(ObsGroup):
        """Nur, was die echte Hand misst — Reihenfolge = Schnittstelle zur Firmware."""
        joint_pos = ObsTerm(
            func=base_mdp.joint_pos,
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=SERVO_JOINTS, preserve_order=True)},
        )
        fsr = ObsTerm(func=mdp.fingertip_forces, clip=(0.0, FSR_CLIP_N))
        last_action = ObsTerm(func=base_mdp.last_action)

        def __post_init__(self):
            self.enable_corruption = False
            self.concatenate_terms = True
            self.history_length = 5

    @configclass
    class CriticCfg(ObsGroup):
        """Privilegiert (nur Simulation)."""
        all_joint_pos = ObsTerm(func=base_mdp.joint_pos)
        all_joint_vel = ObsTerm(func=base_mdp.joint_vel)
        object_pos = ObsTerm(func=mdp.object_pos_in_root)
        object_quat = ObsTerm(func=mdp.object_quat_in_root)
        object_vel = ObsTerm(func=mdp.object_lin_vel)
        object_forces = ObsTerm(func=mdp.fingertip_object_forces, clip=(0.0, 50.0))
        phase = ObsTerm(func=mdp.phase, params={"drop_start_s": GRASP_TIME_S})

        def __post_init__(self):
            self.enable_corruption = False
            self.concatenate_terms = True

    policy: PolicyCfg = PolicyCfg()
    critic: CriticCfg = CriticCfg()


@configclass
class EventCfg:
    # -- startup (Dexsuite-Muster, Bereiche für den PoC enger)
    object_scale = EventTerm(
        func=base_mdp.randomize_rigid_body_scale,
        mode="prestartup",
        params={"scale_range": (0.9, 1.1), "asset_cfg": SceneEntityCfg("object")},
    )
    robot_material = EventTerm(
        func=base_mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", body_names=".*"),
            "static_friction_range": (0.5, 1.0),
            "dynamic_friction_range": (0.5, 1.0),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 250,
        },
    )
    object_material = EventTerm(
        func=base_mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("object"),
            "static_friction_range": (0.5, 1.0),
            "dynamic_friction_range": (0.5, 1.0),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 250,
        },
    )
    object_mass = EventTerm(
        func=base_mdp.randomize_rigid_body_mass,
        mode="startup",
        params={"asset_cfg": SceneEntityCfg("object"), "mass_distribution_params": (0.05, 0.2), "operation": "abs"},
    )
    # Startlage je Umgebung aus der Bounding Box des gespawnten Objekts inkl. Zufallsgröße (seit 2026-10-09 Standard,
    # eval-v2; bis eval-v1 nur EXP-013 ff.): Oberfläche PALM_GAP vor der Handfläche, Boden auf der Tischplatte (+ lift).
    # Vorher aus der Nenngröße → bei ±10 % fiel das Objekt bis 7,5 mm oder startete im Tisch (tools/analyse_reset.py).
    place_objects = EventTerm(
        func=mdp.place_objects_by_size, mode="startup",
        params={"hand_x": HAND_POS[0], "palm_gap": PALM_GAP, "table_top_z": TABLE_TOP_Z, "lift": 0.0,
                "root_height": None})
    servo_gains = EventTerm(
        func=base_mdp.randomize_actuator_gains,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot", joint_names=SERVO_JOINTS),
            "stiffness_distribution_params": (0.8, 1.25),
            "damping_distribution_params": (0.8, 1.25),
            "operation": "scale",
        },
    )

    # -- reset
    reset_robot = EventTerm(func=base_mdp.reset_scene_to_default, mode="reset",
                            params={"reset_joint_targets": True})
    # Zufällige Startstellung der Servo-Gelenke (Dexsuite: reset_joints_by_offset ±0,5 rad;
    # hier enger, Gelenke nur 0–90°). Rotator über den ganzen Bereich, damit die Policy auch
    # Starts mit Daumen in Opposition erlebt (Machbarkeitstest: Rotator 90° → 14–15/16 gehalten).
    reset_hand = EventTerm(
        func=mdp.reset_hand_joints,
        mode="reset",
        params={"ranges_deg": {
            "thumb_left_rotator": (0.0, 90.0),
            "thumb_left_proximal": (0.0, FINGER_START_MAX_DEG),
            "index_left_proximal": (0.0, FINGER_START_MAX_DEG),
            "middle_left_proximal": (0.0, FINGER_START_MAX_DEG),
            "ring_left_proximal": (0.0, FINGER_START_MAX_DEG),
            "pinky_left_proximal": (0.0, FINGER_START_MAX_DEG),
            "wrist_left": (-WRIST_START_MAX_DEG, 0.0),
        }},
    )
    reset_object = EventTerm(
        func=mdp.reset_object_gap_aware,            # Abstand zur Handfläche nach der Gierdrehung (eval-v2)
        mode="reset",
        params={
            "pose_range": {**OBJECT_POS_RANGE, "yaw": (-math.pi, math.pi)},
            "velocity_range": {},
            "asset_cfg": SceneEntityCfg("object"),
        },
    )

    # -- jeder Schritt: Tisch absenken
    lower_table = EventTerm(
        func=mdp.lower_table,
        mode="interval",
        interval_range_s=(0.0, 0.0),
        params={"drop_start_s": GRASP_TIME_S, "drop_speed": DROP_SPEED, "drop_depth": DROP_DEPTH},
    )


@configclass
class RewardsCfg:
    """Belohnungssatz wie Isaac Lab Dexsuite (dexsuite_env_cfg.RewardsCfg + KukaAllegroReorientRewardCfg),
    Zielpose ersetzt durch „nach dem Absenken auf Starthöhe gehalten, aufrecht“ (EXP-004).
    Alle Terme begrenzt; Beitrag je Sekunde = Gewicht × Term (Isaac Lab multipliziert mit dt)."""
    # Aktion: Dexsuite-Funktionen direkt (gekappt bei 1000 als Schutz gegen Ausreißer)
    action_l2 = RewTerm(func=dexsuite_rewards.action_l2_clamped, weight=-0.005)
    action_rate_l2 = RewTerm(func=dexsuite_rewards.action_rate_l2_clamped, weight=-0.005)
    # Annäherung (Dexsuite object_ee_distance, std 0,4) und Gegengriff (Dexsuite contacts, 0,5)
    fingertips_to_object = RewTerm(func=mdp.fingertips_to_object, weight=1.0, params={"std": 0.4})
    good_contact = RewTerm(func=mdp.thumb_opposition_contact, weight=0.5, params={"threshold": CONTACT_N})
    # Dicht, ab dem Absenken, nur bei Gegengriff (Dexsuite position/orientation_command_error_tanh)
    held = RewTerm(func=mdp.held_in_grasp, weight=2.0,
                   params={"drop_start_s": GRASP_TIME_S, "std": HOLD_STD_M, "threshold": CONTACT_N})
    upright = RewTerm(func=mdp.upright_in_grasp, weight=4.0,
                      params={"drop_start_s": GRASP_TIME_S, "rot_std": 1.5, "threshold": CONTACT_N})
    # Scharf: Halten × aufrecht (Dexsuite success_reward, pos_std/rot_std → Absinken/Kippwinkel)
    success = RewTerm(func=mdp.object_held_upright, weight=10.0,
                      params={"drop_start_s": GRASP_TIME_S, "std": HOLD_STD_M, "rot_std": UPRIGHT_ROT_STD})
    early_termination = RewTerm(func=base_mdp.is_terminated_term, weight=-1.0,
                                params={"term_keys": ["abnormal_robot"]})


@configclass
class TerminationsCfg:
    time_out = DoneTerm(func=base_mdp.time_out, time_out=True)
    object_dropped = DoneTerm(func=mdp.object_dropped, params={"max_sink": 0.05})
    abnormal_robot = DoneTerm(func=mdp.abnormal_robot_state)


@configclass
class PibGraspEnvCfg(ManagerBasedRLEnvCfg):
    scene: SceneCfg = SceneCfg(num_envs=1024, env_spacing=0.6, replicate_physics=False)
    observations: ObservationsCfg = ObservationsCfg()
    actions: ActionsCfg = ActionsCfg()
    events: EventCfg = EventCfg()
    rewards: RewardsCfg = RewardsCfg()
    terminations: TerminationsCfg = TerminationsCfg()

    def __post_init__(self):
        self.decimation = 2               # Physik 120 Hz, Policy 60 Hz (wie Dexsuite)
        self.episode_length_s = EPISODE_S
        self.is_finite_horizon = True
        self.sim.dt = 1 / 120
        self.sim.render_interval = self.decimation
        self.sim.physx.bounce_threshold_velocity = 0.01
        # Schräg von Handrücken/Fingerspitzen, ~28° von oben, 2,8 m (Leon, 2026-10-08): alle 16 Hände
        # und die Finger am Objekt sichtbar
        self.viewer.eye = (1.9, -2.25, 1.76)
        self.viewer.lookat = (0.15, -0.5, 0.45)


# ── Varianten für Experimente (eigene Task-IDs, gleiche Bewertungsumgebung) ───────────────

@configclass
class RewardsFingerCountCfg(RewardsCfg):
    # EXP-005: Belohnung steigt mit der Zahl der Finger an der Dose (EXP-004: nur Daumen + 1 Finger)
    finger_count = RewTerm(func=mdp.fingers_in_contact, weight=1.0, params={"threshold": CONTACT_N})


@configclass
class PibGraspEnvCfg_FingerCount(PibGraspEnvCfg):
    rewards: RewardsFingerCountCfg = RewardsFingerCountCfg()


@configclass
class PibGraspEnvCfg_Heavy(PibGraspEnvCfg):
    """EXP-006: Objektmasse wie Dexsuite (0,2 kg × 0,2–2 = 0,04–0,4 kg) statt 0,05–0,2 kg."""

    def __post_init__(self):
        super().__post_init__()
        self.events.object_mass.params["mass_distribution_params"] = (0.04, 0.4)


def apply_object(cfg: PibGraspEnvCfg, key: str) -> PibGraspEnvCfg:
    """Objekt aus OBJECTS einsetzen: Form/Maße, Startlage (Oberfläche PALM_GAP vor der Handfläche,
    steht auf dem Tisch) und Drehung beim Reset. Physik, Masse, Material bleiben wie konfiguriert — außer bei
    YCB (form usd): echte Masse und Größe aus dem Asset, keine Zufallsmasse/-größe. Die Startlage setzt danach
    das Startup-Event place_objects aus der tatsächlichen Bounding Box (init_state ist nur der Ausgangswert)."""
    spec = OBJECTS[key]
    old = cfg.scene.object.spawn
    common = {k: getattr(old, k) for k in ("rigid_props", "collision_props", "mass_props", "physics_material",
                                           "visual_material")}
    if spec["form"] == "zylinder":
        radius, height = spec["masse"]
        cfg.scene.object.spawn = sim_utils.CylinderCfg(radius=radius, height=height, **common)
        depth = radius
    elif spec["form"] == "usd":                 # YCB: Masse/Größe echt aus dem Asset, Aussehen aus dem Asset
        cfg.scene.object.spawn = sim_utils.UsdFileCfg(usd_path=ycb_upright_usd(spec["ycb"], spec["drehung"]),
                                                      rigid_props=old.rigid_props, collision_props=old.collision_props)
        cfg.events.object_mass = None
        cfg.events.object_scale = None
        if "ruhelage" in spec:                  # gemessene Ruhelage: steht bei t = 0 so, wie es von selbst steht
            cfg.events.place_objects.params["root_height"] = spec["ruhelage"]["hoehe"]
            cfg.scene.object.init_state.rot = spec["ruhelage"]["quat"]
        else:
            cfg.events.place_objects.params["lift"] = YCB_SPAWN_LIFT
        depth, height = spec["masse"][0] / 2, spec["masse"][2] + 2 * YCB_SPAWN_LIFT
    else:
        size = spec["masse"]
        cfg.scene.object.spawn = sim_utils.CuboidCfg(size=size, **common)
        depth, height = size[0] / 2, size[2]
    cfg.scene.object.init_state.pos = (HAND_POS[0] - PALM_GAP - depth, OBJECT_POS[1], TABLE_TOP_Z + height / 2)
    cfg.events.reset_object.params["pose_range"]["yaw"] = spec["gier"]
    return cfg


# ── Objektvielfalt (EXP-013): prozedurale Formen wie Dexsuite (16 Grundformen, MultiAssetSpawnerCfg), aber nur
# innerhalb der Kategorie „seitlich greifen“ (aufrecht, ≥ 15 cm hoch). Maße [m]: Zylinder (Radius, Höhe),
# Quader (Tiefe zur Hand, Breite, Höhe). Startlage je Umgebung aus der Bounding Box (mdp.place_objects_by_size).
TRAIN_CYLINDERS = [(r, h) for r in (0.025, 0.03, 0.035, 0.04, 0.045) for h in (0.15, 0.20)]
TRAIN_CUBOIDS = [(x, y, z) for x, y in ((0.06, 0.06), (0.07, 0.07), (0.08, 0.08), (0.06, 0.09)) for z in (0.16, 0.20)]


@configclass
class PibGraspEnvCfg_HeavyMulti(PibGraspEnvCfg_Heavy):
    """EXP-013: wie EXP-006 (Masse 0,04–0,4 kg), aber je Umgebung eine von 18 Formen der Kategorie (10 Zylinder
    Ø 5–9 cm × 15/20 cm, 8 Quader 6–8 cm × 16/20 cm) statt immer des Ø-6-cm-Zylinders; Drehung beim Reset
    ±15° für alle (bei Zylindern ohne Wirkung). Bewertung unverändert je Objekt (eval_policy, Basisaufgabe)."""

    def __post_init__(self):
        super().__post_init__()
        old = self.scene.object.spawn
        common = {k: getattr(old, k) for k in ("rigid_props", "collision_props", "mass_props")}
        mat = {k: getattr(old, k) for k in ("physics_material", "visual_material")}    # je Form, wie Dexsuite
        shapes = [sim_utils.CylinderCfg(radius=r, height=h, **mat) for r, h in TRAIN_CYLINDERS] + \
                 [sim_utils.CuboidCfg(size=s, **mat) for s in TRAIN_CUBOIDS]
        self.scene.object.spawn = sim_utils.MultiAssetSpawnerCfg(assets_cfg=shapes, random_choice=False, **common)
        self.events.reset_object.params["pose_range"]["yaw"] = (-math.radians(15), math.radians(15))



@configclass
class PibGraspEnvCfg_HeavyMultiRand(PibGraspEnvCfg_HeavyMulti):
    """EXP-016: wie EXP-013, Randomisierung der Hand wie Dexsuite: Servo-Gains 0,5–2 (statt 0,8–1,25) und
    Gelenkreibung × 0–5 (neu, dexsuite_env_cfg.EventCfg.joint_friction). Größe bleibt ±10 % (Dexsuite 0,75–1,5
    würde Objekte unter 15 cm Höhe erzeugen — außerhalb der Kategorie seitlich)."""

    def __post_init__(self):
        super().__post_init__()
        self.events.servo_gains.params["stiffness_distribution_params"] = (0.5, 2.0)
        self.events.servo_gains.params["damping_distribution_params"] = (0.5, 2.0)
        self.events.joint_friction = EventTerm(
            func=base_mdp.randomize_joint_parameters, mode="startup",
            params={"asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
                    "friction_distribution_params": (0.0, 5.0), "operation": "scale"})


@configclass
class CurriculumADRCfg:
    """Wie Dexsuite (adr_curriculum.CurriculumCfg): Schwierigkeit 0–10 je Umgebung nach Erfolg; Schwerkraft
    0 → 9,81 m/s² und Rauschen der Gelenkwinkel-Beobachtung 0 → ±0,1 rad (Dexsuite-Endwerte). FSR ohne
    Rauschen (Dexsuite hat keine Kraftsensoren)."""
    adr = CurrTerm(func=mdp.GraspDifficultyScheduler,
                   params={"max_kipp_deg": 45.0, "init_difficulty": 0, "min_difficulty": 0, "max_difficulty": 10})
    gravity_adr = CurrTerm(func=base_mdp.modify_term_cfg, params={
        "address": "events.variable_gravity.params.gravity_distribution_params",
        "modify_fn": dexsuite_curriculums.initial_final_interpolate_fn,
        "modify_params": {"initial_value": ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
                          "final_value": ((0.0, 0.0, -9.81), (0.0, 0.0, -9.81)), "difficulty_term_str": "adr"}})
    joint_pos_noise_min_adr = CurrTerm(func=base_mdp.modify_term_cfg, params={
        "address": "observations.policy.joint_pos.noise.n_min",
        "modify_fn": dexsuite_curriculums.initial_final_interpolate_fn,
        "modify_params": {"initial_value": 0.0, "final_value": -0.1, "difficulty_term_str": "adr"}})
    joint_pos_noise_max_adr = CurrTerm(func=base_mdp.modify_term_cfg, params={
        "address": "observations.policy.joint_pos.noise.n_max",
        "modify_fn": dexsuite_curriculums.initial_final_interpolate_fn,
        "modify_params": {"initial_value": 0.0, "final_value": 0.1, "difficulty_term_str": "adr"}})


@configclass
class PibGraspEnvCfg_HeavyMultiADR(PibGraspEnvCfg_HeavyMulti):
    """EXP-017: wie EXP-013, plus Curriculum wie Dexsuite (Schwerkraft und Beobachtungsrauschen wachsen mit dem
    Erfolg). Dexsuite: 'deliberate trick … starting with no gravity (easy) … the agent learns more smoothly'."""
    curriculum: CurriculumADRCfg = CurriculumADRCfg()

    def __post_init__(self):
        super().__post_init__()
        self.events.variable_gravity = EventTerm(func=base_mdp.randomize_physics_scene_gravity, mode="reset",
                                                 params={"gravity_distribution_params": ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]),
                                                         "operation": "abs"})
        self.observations.policy.joint_pos.noise = Unoise(n_min=0.0, n_max=0.0)
        self.observations.policy.enable_corruption = True
START_REF_S = 0.1     # Startposition = Objektlage bei 0,1 s (abgesetzt, Größe eingeschwungen)


@configclass
class RewardsDexsuiteCfg(RewardsCfg):
    """EXP-012: Eigenbau, der nicht durch die Aufgabe nötig ist, zurück auf Dexsuite
    (dexsuite_env_cfg.RewardsCfg, Kuka-Allegro-Konfiguration):
    - Annäherung: Dexsuite object_ee_distance über Handfläche + Fingerspitzen (statt nur Spitzen)
    - Positionsverfolgung (held): 3D-Abstand zur Zielposition, std 0,2 (statt Absinken in z, einseitig, 0,02)
    - Erfolg: 3D-Abstand pos_std 0,1 × Kippwinkel rot_std 0,5 (statt Absinken 0,02 × Kipp 0,5)
    Ziel = Startposition des Objekts (Dexsuite: kommandierte Pose). Bleibt bewusst eigen: Gegengriff mit
    kleinem Finger, Orientierung als Kippwinkel, Halten/Aufrecht/Erfolg erst ab dem Absenken (ADR-017)."""
    fingertips_to_object = RewTerm(func=dexsuite_rewards.object_ee_distance, weight=1.0, params={
        "std": 0.4, "asset_cfg": SceneEntityCfg("robot", body_names=["urdf_palm_left", *mdp.FINGERTIP_LINKS])})
    held = RewTerm(func=mdp.position_tracking_start, weight=2.0, params={
        "drop_start_s": GRASP_TIME_S, "std": 0.2, "threshold": CONTACT_N, "ref_s": START_REF_S})
    success = RewTerm(func=mdp.success_start, weight=10.0, params={
        "drop_start_s": GRASP_TIME_S, "pos_std": 0.1, "rot_std": UPRIGHT_ROT_STD, "ref_s": START_REF_S})


@configclass
class PibGraspEnvCfg_HeavyDexsuite(PibGraspEnvCfg_Heavy):
    """EXP-012: wie EXP-006 (Masse 0,04–0,4 kg), Belohnung so nah an Dexsuite wie die Aufgabe erlaubt."""
    rewards: RewardsDexsuiteCfg = RewardsDexsuiteCfg()


@configclass
class PibGraspEnvCfg_PLAY(PibGraspEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 16
