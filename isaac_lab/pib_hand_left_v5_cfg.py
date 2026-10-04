"""
pib_hand_left_v5_cfg.py — Isaac-Lab-Asset der realen linken pib-v5-Hand (Unterarm + Hand).

USD: isaac_sim/usd/pib_hand_left_v5.usd (aus pib_hand_left_urdf_v5/, Mimic Joints, Limits
und Self-Collision per isaac_sim/tools/bake_hand_asset_v5.py eingebrannt). Basis
(urdf_elbow_lower) fest.

Aktuatoren aus config/pib_hand_config_v5.py (servo_actuator, Einheiten rad) — dieselbe
Quelle wie isaac_sim/setup_stage.py, kein Abschreiben. Die 9 Folgegelenke (PIP/DIP/IP)
sind passiv (Stiffness/Damping 0, ADR-011); ihre Stellung ergibt die PhysX-Mimic-
Zwangsbedingung aus der USD. Isaac Lab selbst kennt keine Mimic Joints.
"""
import importlib.util
from pathlib import Path

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg

REPO_ROOT = Path(__file__).resolve().parent.parent
USD_PATH = str(REPO_ROOT / "isaac_sim" / "usd" / "pib_hand_left_v5.usd")

_spec = importlib.util.spec_from_file_location(
    "pib_hand_config_v5", REPO_ROOT / "config" / "pib_hand_config_v5.py")
cfg_v5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfg_v5)

SERVO_JOINTS = cfg_v5.LEFT_HAND_SERVO_JOINTS
FOLLOWER_JOINTS_EXPR = [".*_left_distal", ".*_left_tip"]

_servo = {name: cfg_v5.servo_actuator(name) for name in SERVO_JOINTS}

PIB_HAND_LEFT_V5_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=USD_PATH,
        activate_contact_sensors=True,
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.5),
        joint_pos={".*": 0.0},
    ),
    actuators={
        "servos": ImplicitActuatorCfg(
            joint_names_expr=SERVO_JOINTS,
            stiffness={n: a["stiffness_rad"] for n, a in _servo.items()},
            damping={n: a["damping_rad"] for n, a in _servo.items()},
            effort_limit_sim={n: a["max_force"] for n, a in _servo.items()},
            velocity_limit_sim={n: a["max_velocity_rad"] for n, a in _servo.items()},
            armature={n: a["armature"] for n, a in _servo.items()},
        ),
        "followers": ImplicitActuatorCfg(
            joint_names_expr=FOLLOWER_JOINTS_EXPR,
            stiffness=0.0,
            damping=0.0,
            velocity_limit_sim=cfg_v5.FOLLOWER_MAX_VELOCITY_DEG_S * cfg_v5._RAD_PER_DEG,
            armature=cfg_v5.FOLLOWER_ARMATURE_KGM2,
        ),
    },
)
