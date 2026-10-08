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
# Ein ContactSensor je Fingerspitze (wie Dexsuite): Isaac Labs Objekt-Filter funktioniert
# nur, wenn ein Sensor genau einen Prim abdeckt (ContactSensorCfg.filter_prim_paths_expr).
FINGERTIP_SENSORS = ["fsr_thumb", "fsr_index", "fsr_middle", "fsr_ring", "fsr_pinky"]


def _sensors(env: ManagerBasedRLEnv) -> list[ContactSensor]:
    return [env.scene.sensors[name] for name in FINGERTIP_SENSORS]


def episode_time(env: ManagerBasedRLEnv) -> torch.Tensor:
    return env.episode_length_buf * env.step_dt


# ── Beobachtungen ─────────────────────────────────────────────────────────────

def fingertip_forces(env: ManagerBasedRLEnv) -> torch.Tensor:
    """Betrag der Gesamtkontaktkraft je Fingerspitze [N], FSR-Reihenfolge. Alle Kontakte
    (auch Finger-Finger), wie ein echter FSR. Clip über ObsTerm(clip=...)."""
    return torch.stack([s.data.net_forces_w[:, 0].norm(dim=-1) for s in _sensors(env)], dim=-1)


def fingertip_object_forces(env: ManagerBasedRLEnv) -> torch.Tensor:
    """Kontaktkraft je Fingerspitze nur mit dem Objekt [N] (privilegiert, Critic/Reward)."""
    # force_matrix_w: (N, Körper=1, Filter=1, 3)
    return torch.stack([s.data.force_matrix_w[:, 0, 0].norm(dim=-1) for s in _sensors(env)], dim=-1)


def object_pos_in_root(env: ManagerBasedRLEnv, robot_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
                       object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    from isaaclab.utils.math import quat_apply_inverse
    robot: Articulation = env.scene[robot_cfg.name]
    obj: RigidObject = env.scene[object_cfg.name]
    return quat_apply_inverse(robot.data.root_quat_w, obj.data.root_pos_w - robot.data.root_pos_w)


def object_quat_in_root(env: ManagerBasedRLEnv, robot_cfg: SceneEntityCfg = SceneEntityCfg("robot"),
                        object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Objektorientierung (w, x, y, z) im Hand-Root-Frame (Dexsuite: object_quat_b), privilegiert."""
    from isaaclab.utils.math import quat_inv, quat_mul
    robot: Articulation = env.scene[robot_cfg.name]
    obj: RigidObject = env.scene[object_cfg.name]
    return quat_mul(quat_inv(robot.data.root_quat_w), obj.data.root_quat_w)


def object_tilt(env: ManagerBasedRLEnv, object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Kippwinkel [rad] zwischen Objekt-z-Achse (Zylinderachse) und Welt-z."""
    from isaaclab.utils.math import quat_apply
    obj: RigidObject = env.scene[object_cfg.name]
    z = torch.zeros_like(obj.data.root_pos_w)
    z[:, 2] = 1.0
    return torch.acos(quat_apply(obj.data.root_quat_w, z)[:, 2].clamp(-1.0, 1.0))


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


# Mimic-Kopplung der linken Hand (ADR-011, isaac_sim/setup_stage.py → MIMIC_JOINTS):
# Folgegelenk -> Referenz, gearing -1 = gleicher Winkel. Reihenfolge: PIP vor DIP.
MIMIC_LEFT = [(f"{f}_left_distal", f"{f}_left_proximal") for f in ("index", "middle", "ring", "pinky")] + \
             [(f"{f}_left_tip", f"{f}_left_distal") for f in ("index", "middle", "ring", "pinky")] + \
             [("thumb_left_tip", "thumb_left_proximal")]


def reset_hand_joints(env: ManagerBasedRLEnv, env_ids: torch.Tensor, ranges_deg: dict[str, tuple[float, float]],
                      asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> None:
    """Servo-Gelenke beim Reset gleichverteilt in ranges_deg setzen (Dexsuite: reset_joints_by_offset),
    Folgegelenke passend zur Mimic-Kopplung — sonst startet die Zwangsbedingung mit einem Sprung.
    Sollwerte = Startstellung, damit die Antriebe nicht zurückziehen."""
    import math
    robot: Articulation = env.scene[asset_cfg.name]
    q = robot.data.default_joint_pos[env_ids].clone()
    for name, (lo, hi) in ranges_deg.items():
        u = torch.rand(len(env_ids), device=q.device)
        q[:, robot.joint_names.index(name)] = math.radians(lo) + u * math.radians(hi - lo)
    for follower, reference in MIMIC_LEFT:
        q[:, robot.joint_names.index(follower)] = q[:, robot.joint_names.index(reference)]
    robot.write_joint_state_to_sim(q, torch.zeros_like(q), env_ids=env_ids)
    robot.set_joint_position_target(q, env_ids=env_ids)


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


def thumb_opposition_contact(env: ManagerBasedRLEnv, threshold: float) -> torch.Tensor:
    """1, wenn Daumen und mindestens ein Finger das Objekt berühren (Dexsuite: contacts)."""
    f = fingertip_object_forces(env)
    return ((f[:, 0] > threshold) & (f[:, 1:] > threshold).any(dim=-1)).float()


def object_sink(env: ManagerBasedRLEnv, drop_start_s: float,
                object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Absinken [m] gegenüber der Höhe beim Beginn des Absenkens (bis dahin mitgeführt, danach
    eingefroren). Nicht gegen die Standardhöhe: mit ±10 % Größe steht die Dose bis 7,5 mm tiefer."""
    obj: RigidObject = env.scene[object_cfg.name]
    z = obj.data.root_pos_w[:, 2]
    if getattr(env, "_pib_z_ref", None) is None or env._pib_z_ref.shape != z.shape:
        env._pib_z_ref = z.clone()
    before = episode_time(env) < drop_start_s
    env._pib_z_ref[before] = z[before]
    return (env._pib_z_ref - z).clamp(min=0.0)


def fingers_in_contact(env: ManagerBasedRLEnv, threshold: float) -> torch.Tensor:
    """Anteil der vier Finger mit Objektkontakt, nur bei Daumenkontakt: (Finger > threshold) / 4 ·
    𝟙[Daumen > threshold] ∈ [0, 1]. Belohnt Kraftgriff statt Pinzettengriff (EXP-005)."""
    f = fingertip_object_forces(env)
    return (f[:, 1:] > threshold).float().mean(dim=-1) * (f[:, 0] > threshold).float()


def object_held(env: ManagerBasedRLEnv, drop_start_s: float, std: float,
                object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Ab dem Tisch-Absenken: 1 − tanh(Absinken des Objekts / std). Vorher 0 — solange das
    Objekt auf dem Tisch steht, gibt es nichts zu verdienen."""
    active = (episode_time(env) >= drop_start_s).float()
    return active * (1.0 - torch.tanh(object_sink(env, drop_start_s, object_cfg) / std))


def held_in_grasp(env: ManagerBasedRLEnv, drop_start_s: float, std: float, threshold: float) -> torch.Tensor:
    """Dicht, ab dem Absenken: Halten × Gegengriff (Dexsuite position_command_error_tanh, × contacts)."""
    return object_held(env, drop_start_s, std) * thumb_opposition_contact(env, threshold)


def upright_in_grasp(env: ManagerBasedRLEnv, drop_start_s: float, rot_std: float, threshold: float) -> torch.Tensor:
    """Dicht, ab dem Absenken: (1 − tanh(Kippwinkel/rot_std)) × Gegengriff (Dexsuite
    orientation_command_error_tanh, × contacts). Erst ab dem Absenken — auf dem Tisch steht die
    Dose von selbst aufrecht, sonst gäbe es die Belohnung fürs bloße Antippen."""
    active = (episode_time(env) >= drop_start_s).float()
    return active * (1.0 - torch.tanh(object_tilt(env) / rot_std)) * thumb_opposition_contact(env, threshold)


def object_held_upright(env: ManagerBasedRLEnv, drop_start_s: float, std: float, rot_std: float,
                        object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Halten × aufrecht (Dexsuite success_reward: (1 − tanh(Fehler/pos_std))·(1 − tanh(Winkel/rot_std))).
    Gekippt halten bringt fast nichts, ohne die Episode abzubrechen — das Greifen bleibt erkundbar."""
    return object_held(env, drop_start_s, std, object_cfg) * (1.0 - torch.tanh(object_tilt(env, object_cfg) / rot_std))


def object_upright(env: ManagerBasedRLEnv, drop_start_s: float, std: float) -> torch.Tensor:
    """Ab dem Tisch-Absenken: 1 − tanh(Kippwinkel / std). Vorher 0 — auf dem Tisch steht die
    Dose ohnehin aufrecht, die Belohnung gäbe es dort ohne Zutun."""
    active = (episode_time(env) >= drop_start_s).float()
    return active * (1.0 - torch.tanh(object_tilt(env) / std))


# ── Positionsterme wie Dexsuite (EXP-012): Ziel = Startposition des Objekts ────────────────

def object_start_distance(env: ManagerBasedRLEnv, ref_s: float,
                          object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """3D-Abstand [m] des Objekts zu seiner Startposition (bis ref_s mitgeführt, dann eingefroren: Objekt
    abgesetzt, Größe eingeschwungen). Gegenstück zu Dexsuites Zielposition (Kommando relativ zur
    Roboterbasis): die Hand ist fest, das Objekt soll bleiben, wo der Arm es gegriffen hat."""
    obj: RigidObject = env.scene[object_cfg.name]
    pos = obj.data.root_pos_w
    if getattr(env, "_pib_start_pos", None) is None or env._pib_start_pos.shape != pos.shape:
        env._pib_start_pos = pos.clone()
    before = episode_time(env) < ref_s
    env._pib_start_pos[before] = pos[before]
    return torch.norm(pos - env._pib_start_pos, dim=-1)


def position_tracking_start(env: ManagerBasedRLEnv, drop_start_s: float, std: float, threshold: float,
                            ref_s: float) -> torch.Tensor:
    """Dexsuite position_command_error_tanh: (1 − tanh(‖p − p_Ziel‖/std)) × Gegengriff, ab dem Absenken."""
    active = (episode_time(env) >= drop_start_s).float()
    return active * (1.0 - torch.tanh(object_start_distance(env, ref_s) / std)) * thumb_opposition_contact(env, threshold)


def success_start(env: ManagerBasedRLEnv, drop_start_s: float, pos_std: float, rot_std: float,
                  ref_s: float) -> torch.Tensor:
    """Dexsuite success_reward: (1 − tanh(‖p − p_Ziel‖/pos_std)) · (1 − tanh(Kippwinkel/rot_std)), ab dem
    Absenken. Orientierung als Kippwinkel (Anforderung aufrecht, kein Gierziel)."""
    active = (episode_time(env) >= drop_start_s).float()
    return (active * (1.0 - torch.tanh(object_start_distance(env, ref_s) / pos_std))
            * (1.0 - torch.tanh(object_tilt(env) / rot_std)))


def excess_fingertip_force(env: ManagerBasedRLEnv, limit: float) -> torch.Tensor:
    """Summe der Kraft über `limit` [N] an allen Fingerspitzen (gegen Zerquetschen und
    unrealistisch hohe Kräfte, ADR-011: lineare Kopplung überschätzt die Spitzenkraft)."""
    return (fingertip_forces(env) - limit).clamp(min=0.0).sum(dim=-1)


# ── Abbruch ───────────────────────────────────────────────────────────────────

def object_dropped(env: ManagerBasedRLEnv, max_sink: float,
                   object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    obj: RigidObject = env.scene[object_cfg.name]
    z0 = obj.data.default_root_state[:, 2] + env.scene.env_origins[:, 2]
    return (z0 - obj.data.root_pos_w[:, 2]) > max_sink


def object_tilted(env: ManagerBasedRLEnv, max_tilt_deg: float) -> torch.Tensor:
    """Abbruch, wenn das Objekt mehr als max_tilt_deg kippt (Muster: Isaac Lab
    deploy/gear_assembly, reset_when_gear_orientation_exceeds_threshold)."""
    import math
    return object_tilt(env) > math.radians(max_tilt_deg)


def abnormal_robot_state(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg = SceneEntityCfg("robot")) -> torch.Tensor:
    """Gelenkgeschwindigkeit > 2× Limit — instabile Physik (Dexsuite: abnormal_robot_state)."""
    robot: Articulation = env.scene[asset_cfg.name]
    return (robot.data.joint_vel.abs() > (robot.data.joint_vel_limits * 2)).any(dim=1)
