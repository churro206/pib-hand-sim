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
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.utils import configclass

from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG, SERVO_JOINTS

from isaaclab_tasks.manager_based.manipulation.dexsuite.mdp import rewards as dexsuite_rewards

from . import mdp

# ── Geometrie (Hand-Root-Frame aus isaac_lab/_probe_geometry.py, 2026-10-04) ───
# Ohne Drehung zeigen die Finger nach −y, die Handfläche nach −z, der Daumen liegt auf
# −x. Drehung +90° um y: Handfläche → −x, Daumen → +z, Finger bleiben bei −y.
HAND_POS = (0.0, 0.0, 0.5)
HAND_ROT = (math.cos(math.pi / 4), 0.0, math.sin(math.pi / 4), 0.0)   # (w, x, y, z)

OBJECT_RADIUS = 0.03          # Dose Ø 6 cm
OBJECT_HEIGHT = 0.15
PALM_GAP = 0.035              # Handfläche ↔ Objektoberfläche (Vorgreifpose, für alle Objekte gleich)
# Tischplatte 8,5 cm unter dem Hand-Root: die Spitze des kleinen Fingers liegt bei
# −6,3 cm (_debug_scene.py), bei −6 cm stieß sie an den Tisch
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
# Tischplatte (kleiner Finger … Daumen, _debug_scene.py, 2026-10-07); tiefer geht die Hand
# nicht, sonst stößt der kleine Finger an den Tisch.
# form, Maße [m] (Zylinder: Radius, Höhe; Quader: x, y, z), Drehung beim Reset [rad]
OBJECTS = {
    "zylinder_d6": {"form": "zylinder", "masse": (0.03, 0.15), "gier": (-math.pi, math.pi)},      # Dose (Training)
    "zylinder_d8": {"form": "zylinder", "masse": (0.04, 0.15), "gier": (-math.pi, math.pi)},      # dicke Dose/Becher
    # Milchpackung: eine Fläche zur Hand ±15° (so würde ein Greifplaner anfahren)
    "quader_7x7x20": {"form": "quader", "masse": (0.07, 0.07, 0.20), "gier": (-math.radians(15), math.radians(15))},
}
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
            "thumb_left_proximal": (0.0, 15.0),
            "index_left_proximal": (0.0, 15.0),
            "middle_left_proximal": (0.0, 15.0),
            "ring_left_proximal": (0.0, 15.0),
            "pinky_left_proximal": (0.0, 15.0),
            "wrist_left": (-10.0, 0.0),
        }},
    )
    reset_object = EventTerm(
        func=base_mdp.reset_root_state_uniform,
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
    steht auf dem Tisch) und Drehung beim Reset. Physik, Masse, Material bleiben wie konfiguriert."""
    spec = OBJECTS[key]
    old = cfg.scene.object.spawn
    common = {k: getattr(old, k) for k in ("rigid_props", "collision_props", "mass_props", "physics_material",
                                           "visual_material")}
    if spec["form"] == "zylinder":
        radius, height = spec["masse"]
        cfg.scene.object.spawn = sim_utils.CylinderCfg(radius=radius, height=height, **common)
        depth = radius
    else:
        size = spec["masse"]
        cfg.scene.object.spawn = sim_utils.CuboidCfg(size=size, **common)
        depth, height = size[0] / 2, size[2]
    cfg.scene.object.init_state.pos = (HAND_POS[0] - PALM_GAP - depth, OBJECT_POS[1], TABLE_TOP_Z + height / 2)
    cfg.events.reset_object.params["pose_range"]["yaw"] = spec["gier"]
    return cfg


@configclass
class PibGraspEnvCfg_PLAY(PibGraspEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 16
