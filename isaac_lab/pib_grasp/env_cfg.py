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
Objektlage/-geschwindigkeit, Folgegelenke, Objekt-Kontaktkräfte und die Phase.
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

from . import mdp

# ── Geometrie (Hand-Root-Frame aus isaac_lab/_probe_geometry.py, 2026-10-04) ───
# Ohne Drehung zeigen die Finger nach −y, die Handfläche nach −z, der Daumen liegt auf
# −x. Drehung +90° um y: Handfläche → −x, Daumen → +z, Finger bleiben bei −y.
HAND_POS = (0.0, 0.0, 0.5)
HAND_ROT = (math.cos(math.pi / 4), 0.0, math.sin(math.pi / 4), 0.0)   # (w, x, y, z)

OBJECT_RADIUS = 0.03          # Dose Ø 6 cm
OBJECT_HEIGHT = 0.15
# Tischplatte 8,5 cm unter dem Hand-Root: die Spitze des kleinen Fingers liegt bei
# −6,3 cm (_debug_scene.py), bei −6 cm stieß sie an den Tisch
TABLE_TOP_Z = HAND_POS[2] - 0.085
# Dosenmitte: 6,5 cm vor der Handfläche (−x), auf Höhe der Grundglieder zwischen MCP
# (y ≈ −0,31) und PIP (y ≈ −0,35), steht auf dem Tisch. Bis 2026-10-04 y = −0,32: die
# Finger zogen die Dose Richtung Handgelenk, bis sie hinten vom Tisch rutschte.
OBJECT_POS = (HAND_POS[0] - 0.065, HAND_POS[1] - 0.34, TABLE_TOP_Z + OBJECT_HEIGHT / 2)
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
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.5, 0.5, 0.5)),
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=TABLE_POS),
    )

    # Ein Sensor für alle 5 Fingerspitzen; Filter aufs Objekt für die privilegierte Kraft
    fingertips = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Robot/(urdf_finger_tip.*|urdf_thumb_tip)",
        filter_prim_paths_expr=["{ENV_REGEX_NS}/Object"],
    )

    light = AssetBaseCfg(prim_path="/World/light", spawn=sim_utils.DomeLightCfg(intensity=2000.0))


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
    # Gewichte für Aktion/Kontakt aus Dexsuite
    action_l2 = RewTerm(func=base_mdp.action_l2, weight=-0.005)
    action_rate_l2 = RewTerm(func=base_mdp.action_rate_l2, weight=-0.005)
    fingertips_to_object = RewTerm(func=mdp.fingertips_to_object, weight=1.0, params={"std": 0.1})
    good_contact = RewTerm(func=mdp.thumb_opposition_contact, weight=0.5, params={"threshold": 1.0})
    # Erfolg: Dose bleibt nach dem Tisch-Absenken in der Hand (ersetzt Dexsuites Zielpose)
    held = RewTerm(func=mdp.object_held, weight=5.0, params={"drop_start_s": GRASP_TIME_S, "std": 0.02})
    excess_force = RewTerm(func=mdp.excess_fingertip_force, weight=-0.02, params={"limit": 15.0})
    early_termination = RewTerm(func=base_mdp.is_terminated_term, weight=-1.0,
                                params={"term_keys": ["object_dropped", "abnormal_robot"]})


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
        self.viewer.eye = (0.6, 0.0, 0.7)
        self.viewer.lookat = (0.0, -0.3, 0.5)


@configclass
class PibGraspEnvCfg_PLAY(PibGraspEnvCfg):
    def __post_init__(self):
        super().__post_init__()
        self.scene.num_envs = 16
