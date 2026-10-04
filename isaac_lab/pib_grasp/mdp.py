"""
mdp.py — Eigene MDP-Terme der pib-Greifaufgabe (zusätzlich zu isaaclab.envs.mdp).

Aufbau nach Isaac Labs Dexsuite (manipulation/dexsuite/mdp), angepasst an die pib-Hand:
Fingerspitzen-Kräfte in fester Reihenfolge (wie die echten FSR), "Tisch absenken" als
Erfolgstest statt Zielpose-Kommando.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.assets import Articulation, RigidObject
from isaaclab.managers import SceneEntityCfg
from isaaclab.sensors import ContactSensor

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv

# Feste FSR-Reihenfolge (auch für die Firmware): Daumen, Zeige, Mittel, Ring, klein.
# Link-Namen aus pib_hand_left_urdf_v5/robot.urdf (finger_tip = Zeige, _2 = Mittel,
# _3 = Ring, _4 = klein). Der ContactSensor liefert sie in anderer Reihenfolge.
FINGERTIP_LINKS = ["urdf_thumb_tip", "urdf_finger_tip", "urdf_finger_tip_2", "urdf_finger_tip_3", "urdf_finger_tip_4"]


def _tip_order(sensor: ContactSensor) -> list[int]:
    return [sensor.body_names.index(name) for name in FINGERTIP_LINKS]


def episode_time(env: ManagerBasedRLEnv) -> torch.Tensor:
    return env.episode_length_buf * env.step_dt


# ── Beobachtungen ─────────────────────────────────────────────────────────────

def fingertip_forces(env: ManagerBasedRLEnv, sensor_name: str = "fingertips") -> torch.Tensor:
    """Betrag der Gesamtkontaktkraft je Fingerspitze [N], FSR-Reihenfolge. Alle Kontakte
    (auch Finger-Finger), wie ein echter FSR. Clip über ObsTerm(clip=...)."""
    sensor: ContactSensor = env.scene.sensors[sensor_name]
    return sensor.data.net_forces_w[:, _tip_order(sensor)].norm(dim=-1)


def fingertip_object_forces(env: ManagerBasedRLEnv, sensor_name: str = "fingertips") -> torch.Tensor:
    """Kontaktkraft je Fingerspitze nur mit dem Objekt [N] (privilegiert, Critic/Reward)."""
    sensor: ContactSensor = env.scene.sensors[sensor_name]
    # force_matrix_w: (N, Körper, Filter, 3) — ein Filter (das Objekt)
    return sensor.data.force_matrix_w[:, _tip_order(sensor), 0].norm(dim=-1)


def object_pos_in_root(env: ManagerBasedRLEnv, robot_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
                       object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    from isaaclab.utils.math import quat_apply_inverse
    robot: Articulation = env.scene[robot_cfg.name]
    obj: RigidObject = env.scene[object_cfg.name]
    return quat_apply_inverse(robot.data.root_quat_w, obj.data.root_pos_w - robot.data.root_pos_w)


def object_lin_vel(env: ManagerBasedRLEnv, object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    obj: RigidObject = env.scene[object_cfg.name]
    return obj.data.root_lin_vel_w


def phase(env: ManagerBasedRLEnv, drop_start_s: float) -> torch.Tensor:
    """Episodenzeit relativ zum Tisch-Absenken (privilegiert, nur Critic)."""
    return (episode_time(env) - drop_start_s).unsqueeze(-1)


# ── Events ────────────────────────────────────────────────────────────────────

def lower_table(env: ManagerBasedRLEnv, env_ids: torch.Tensor, drop_start_s: float, drop_speed: float,
                drop_depth: float, table_cfg: SceneEntityCfg = SceneEntityCfg("table")) -> None:
    """Kinematischen Tisch ab drop_start_s mit drop_speed [m/s] um drop_depth [m] absenken.
    Physikalisch gleichwertig zum Anheben der Hand (später: der Arm hebt), ohne die
    feste Basis der Artikulation zu bewegen."""
    table: RigidObject = env.scene[table_cfg.name]
    t = episode_time(env)[env_ids]
    dz = ((t - drop_start_s) * drop_speed).clamp(0.0, drop_depth)
    pose = table.data.default_root_state[env_ids, :7].clone()
    pose[:, :3] += env.scene.env_origins[env_ids]
    pose[:, 2] -= dz
    table.write_root_pose_to_sim(pose, env_ids=env_ids)


# ── Belohnungen ───────────────────────────────────────────────────────────────

def fingertips_to_object(env: ManagerBasedRLEnv, std: float,
                         robot_cfg: SceneEntityCfg = SceneEntityCfg("robot", body_names=FINGERTIP_LINKS),
                         object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Annäherung: 1 − tanh(größter Abstand Fingerspitze↔Objekt / std) (Dexsuite: object_ee_distance)."""
    robot: Articulation = env.scene[robot_cfg.name]
    obj: RigidObject = env.scene[object_cfg.name]
    tips = robot.data.body_pos_w[:, robot_cfg.body_ids]
    dist = torch.norm(tips - obj.data.root_pos_w[:, None, :], dim=-1).max(dim=-1).values
    return 1.0 - torch.tanh(dist / std)


def thumb_opposition_contact(env: ManagerBasedRLEnv, threshold: float, sensor_name: str = "fingertips") -> torch.Tensor:
    """1, wenn Daumen und mindestens ein Finger das Objekt berühren (Dexsuite: contacts)."""
    f = fingertip_object_forces(env, sensor_name)
    return ((f[:, 0] > threshold) & (f[:, 1:] > threshold).any(dim=-1)).float()


def object_held(env: ManagerBasedRLEnv, drop_start_s: float, std: float,
                object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Ab dem Tisch-Absenken: 1 − tanh(Absinken des Objekts / std). Vorher 0 — solange das
    Objekt auf dem Tisch steht, gibt es nichts zu verdienen."""
    obj: RigidObject = env.scene[object_cfg.name]
    z0 = obj.data.default_root_state[:, 2] + env.scene.env_origins[:, 2]
    sink = (z0 - obj.data.root_pos_w[:, 2]).clamp(min=0.0)
    active = (episode_time(env) >= drop_start_s).float()
    return active * (1.0 - torch.tanh(sink / std))


def excess_fingertip_force(env: ManagerBasedRLEnv, limit: float, sensor_name: str = "fingertips") -> torch.Tensor:
    """Summe der Kraft über `limit` [N] an allen Fingerspitzen (gegen Zerquetschen und
    unrealistisch hohe Kräfte, ADR-011: lineare Kopplung überschätzt die Spitzenkraft)."""
    return (fingertip_forces(env, sensor_name) - limit).clamp(min=0.0).sum(dim=-1)


# ── Abbruch ───────────────────────────────────────────────────────────────────

def object_dropped(env: ManagerBasedRLEnv, max_sink: float,
                   object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    obj: RigidObject = env.scene[object_cfg.name]
    z0 = obj.data.default_root_state[:, 2] + env.scene.env_origins[:, 2]
    return (z0 - obj.data.root_pos_w[:, 2]) > max_sink


def abnormal_robot_state(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Gelenkgeschwindigkeit > 2× Limit — instabile Physik (Dexsuite: abnormal_robot_state)."""
    robot: Articulation = env.scene[asset_cfg.name]
    return (robot.data.joint_vel.abs() > (robot.data.joint_vel_limits * 2)).any(dim=1)
