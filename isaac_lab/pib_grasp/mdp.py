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
from isaaclab.envs.mdp.actions import RelativeJointPositionActionCfg
from isaaclab.envs.mdp.actions.joint_actions import RelativeJointPositionAction
from isaaclab.managers import ManagerTermBase, SceneEntityCfg
from isaaclab.sensors import ContactSensor
from isaaclab.utils import configclass

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


# ── Aktion ────────────────────────────────────────────────────────────────────

class FilteredRelativeJointPositionAction(RelativeJointPositionAction):
    """Relative Gelenkposition wie Dexsuite, die Aktion vorher mit einem gleitenden Mittelwert geglättet (EXP-024):
    a_f ← α·a + (1 − α)·a_f, Sollwert = q + Skala·a_f. Vorbild Isaac Lab ShadowHand-OpenAI (act_moving_average = 0.3,
    DeXtreme-Linie) — dort auf den Gelenk-Sollwerten, hier auf der relativen Aktion, weil der Sollwert jeden Schritt aus
    der aktuellen Stellung neu entsteht. Die Firmware muss denselben Filter (gleiches α, 60 Hz) vor die Servos setzen.
    filtered_actions = das, was die Servos tatsächlich bekommen (Kennzahl „Unruhe wirksam“)."""

    cfg: FilteredRelativeJointPositionActionCfg

    def __init__(self, cfg: FilteredRelativeJointPositionActionCfg, env):
        super().__init__(cfg, env)
        self._filtered = torch.zeros_like(self._raw_actions)

    @property
    def filtered_actions(self) -> torch.Tensor:
        return self._filtered

    def process_actions(self, actions: torch.Tensor):
        self._raw_actions[:] = actions
        self._filtered[:] = self.cfg.alpha * actions + (1.0 - self.cfg.alpha) * self._filtered
        self._processed_actions = self._filtered * self._scale + self._offset
        if self.cfg.clip is not None:
            self._processed_actions = torch.clamp(self._processed_actions, min=self._clip[:, :, 0], max=self._clip[:, :, 1])

    def reset(self, env_ids=None) -> None:
        super().reset(env_ids)
        self._filtered[env_ids] = 0.0


@configclass
class FilteredRelativeJointPositionActionCfg(RelativeJointPositionActionCfg):
    class_type: type = FilteredRelativeJointPositionAction
    alpha: float = 0.3
    """Gewicht der neuen Aktion (1 = kein Filter)."""


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


def object_properties(env: ManagerBasedRLEnv, object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Privilegiert (nur Critic, EXP-021; wie HORA und Dexsuite, deren Critic Masse/Reibung/Form kennt): halbe Tiefe,
    halbe Breite, Höhe [m] (Bounding Box inkl. Zufallsgröße), Masse [kg], Haft- und Gleitreibung. Beim ersten Aufruf
    nach den Startup-Events gelesen (ändern sich danach nicht); davor Nullen (Formbestimmung des Observation-Managers)."""
    props = getattr(env, "_pib_object_props", None)
    if props is not None:
        return props
    footprint = getattr(env, "pib_object_footprint", None)
    if footprint is None:
        return torch.zeros(env.num_envs, 6, device=env.device)
    obj: RigidObject = env.scene[object_cfg.name]
    mass = obj.root_physx_view.get_masses().reshape(env.num_envs, -1).sum(-1).to(env.device)
    material = obj.root_physx_view.get_material_properties().reshape(env.num_envs, -1, 3)[:, 0, :2].to(env.device)
    env._pib_object_props = torch.cat([footprint[:, [0, 1, 3]], mass[:, None], material], dim=-1)
    return env._pib_object_props


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


def place_objects_by_size(env: ManagerBasedRLEnv, env_ids: torch.Tensor | None, hand_x: float, palm_gap: float,
                          table_top_z: float, lift: float = 0.0, root_height: float | None = None,
                          object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> None:
    """Startup: Startlage je Umgebung aus der Bounding Box des gespawnten Objekts (USD, inkl. zufälliger Größe) —
    Oberfläche palm_gap vor der Handfläche, Boden lift über der Tischplatte. root_height: gemessene Ruhelage
    (Höhe des Ursprungs über der Tischplatte, tools/ruhelage_objekt.py) statt Bounding Box + lift."""
    import re
    import isaaclab.sim as sim_utils
    from pxr import Usd, UsdGeom
    obj: RigidObject = env.scene[object_cfg.name]
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    stage = env.scene.stage
    # Grundriss je Umgebung für reset_object_gap_aware (halbe Tiefe/Breite, eckig 1 / rund 0) und Höhe [m]
    env.pib_object_footprint = torch.zeros(env.num_envs, 4, device=env.device)
    for path in sim_utils.find_matching_prim_paths(obj.cfg.prim_path):
        idx = int(re.search(r"env_(\d+)", path).group(1))
        prim = stage.GetPrimAtPath(path)
        size = cache.ComputeWorldBound(prim).ComputeAlignedRange().GetSize()
        round_ = any(p.GetTypeName() == "Cylinder" for p in Usd.PrimRange(prim))
        env.pib_object_footprint[idx] = torch.tensor([size[0] / 2, size[1] / 2, 0.0 if round_ else 1.0, size[2]])
        obj.data.default_root_state[idx, 0] = hand_x - palm_gap - size[0] / 2
        obj.data.default_root_state[idx, 2] = table_top_z + (root_height if root_height is not None
                                                             else lift + size[2] / 2)


def tip_height_for_object(kind: str, size: tuple[float, float, float], clearance: tuple[tuple[float, float], ...],
                          margin: float, min_tip_height: float) -> float:
    """Höhe der Fingerspitzenebene über dem Tisch [m] für ein Objekt unter der gekippten Hand „von oben“: so tief wie
    möglich, aber die Hand (außer den Spitzen) bleibt überall mindestens margin über der Objektoberfläche, und die Spitzen
    stehen mindestens min_tip_height über dem Tisch (wie ein Planer die Vorgreifhöhe je Objekt setzen würde).
    clearance: gemessener Platz unter der Hand über der Spitzenebene je Abstand r von der Greifmitte
    (tools/probe_neigung_oben.py); jenseits der Tabelle linear mit der letzten Steigung fortgesetzt.
    kind: kugel (Radius = size[2]/2), zylinder (Radius = size[0]/2) oder quader (halbe Diagonale des Grundrisses, weil
    die Gierdrehung beliebig sein kann); size = Bounding Box (x, y, z)."""
    import math
    rs, cs = [c[0] for c in clearance], [c[1] for c in clearance]

    def c_at(r: float) -> float:
        for i in range(1, len(rs)):
            if r <= rs[i]:
                w = (r - rs[i - 1]) / (rs[i] - rs[i - 1])
                return cs[i - 1] + w * (cs[i] - cs[i - 1])
        return cs[-1] + (r - rs[-1]) * (cs[-1] - cs[-2]) / (rs[-1] - rs[-2])

    if kind == "kugel":
        R = size[2] / 2
        surface = lambda r: R + math.sqrt(max(R * R - r * r, 0.0))  # noqa: E731
    else:
        R = size[0] / 2 if kind == "zylinder" else math.hypot(size[0], size[1]) / 2
        surface = lambda r: size[2]  # noqa: E731
    radii = sorted({*[r for r in rs if r <= R], R})
    need = max(surface(r) + margin - c_at(r) for r in radii)
    return max(min_tip_height, need)


def place_objects_from_above(env: ManagerBasedRLEnv, env_ids: torch.Tensor | None, center_xy: tuple[float, float],
                             tip_plane_z: float, clearance: tuple[tuple[float, float], ...], margin: float,
                             min_tip_height: float, table_thickness: float, lift: float = 0.0,
                             object_cfg: SceneEntityCfg = SceneEntityCfg("object"),
                             table_cfg: SceneEntityCfg = SceneEntityCfg("table")) -> None:
    """Startup, Greifart „von oben“ (env_cfg_oben, gekippte Hand): je Umgebung aus der Bounding Box des gespawnten Objekts
    (inkl. Zufallsgröße) und seiner Form die Höhe der Fingerspitzen über dem Tisch (tip_height_for_object), Objekt in der
    Greifmitte center_xy auf dem Tisch, Tisch tip_height unter der Spitzenebene tip_plane_z (− lift: YCB fällt kurz auf den
    Tisch statt im Collider zu starten). Die Hand ist fest — Objekt und Tisch werden gesetzt; lower_table und
    reset_scene_to_default nutzen die geänderte Standardlage. Höhe je Umgebung in env.pib_tip_height (Diagnose).
    Grundriss für reset_object_gap_aware ohne Eckkorrektur (eckig = 0): die Gierdrehung ist in der Höhe berücksichtigt."""
    import re
    import isaaclab.sim as sim_utils
    from pxr import Usd, UsdGeom
    obj: RigidObject = env.scene[object_cfg.name]
    table: RigidObject = env.scene[table_cfg.name]
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    stage = env.scene.stage
    env.pib_object_footprint = torch.zeros(env.num_envs, 4, device=env.device)
    env.pib_tip_height = torch.zeros(env.num_envs, device=env.device)
    for path in sim_utils.find_matching_prim_paths(obj.cfg.prim_path):
        idx = int(re.search(r"env_(\d+)", path).group(1))
        prim = stage.GetPrimAtPath(path)
        size = cache.ComputeWorldBound(prim).ComputeAlignedRange().GetSize()
        types = {p.GetTypeName() for p in Usd.PrimRange(prim)}
        kind = "kugel" if "Sphere" in types else ("zylinder" if "Cylinder" in types else "quader")
        h = tip_height_for_object(kind, (size[0], size[1], size[2]), clearance, margin, min_tip_height)
        env.pib_tip_height[idx] = h
        env.pib_object_footprint[idx] = torch.tensor([size[0] / 2, size[1] / 2, 0.0, size[2]])
        top = tip_plane_z - h                                         # Tischplatte
        obj.data.default_root_state[idx, 0] = center_xy[0]
        obj.data.default_root_state[idx, 1] = center_xy[1]
        obj.data.default_root_state[idx, 2] = top + lift + size[2] / 2  # Ursprung = Boxmitte (auch YCB)
        table.data.default_root_state[idx, 0] = center_xy[0]
        table.data.default_root_state[idx, 1] = center_xy[1]
        table.data.default_root_state[idx, 2] = top - table_thickness / 2


def reset_object_gap_aware(env: ManagerBasedRLEnv, env_ids: torch.Tensor, pose_range: dict[str, tuple[float, float]],
                           velocity_range: dict[str, tuple[float, float]],
                           asset_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> None:
    """Wie Isaac Labs reset_root_state_uniform, aber der Abstand zur Handfläche gilt nach der Gierdrehung: ein eckiges
    Objekt wird um a·|cos θ| + b·|sin θ| − a von der Hand weggerückt (a, b = halbe Tiefe/Breite), damit seine nächste
    Ecke so weit vor der Handfläche liegt wie die Vorderfläche ohne Drehung — wie ein Greifplaner die Vorgreifpose
    setzen würde. Runde Objekte unverändert. Ohne Grundriss (place_objects_by_size) wie das Original.
    Vorher berührte die Ecke eines um 10–15° gedrehten Quaders beim Reset die Finger (tools/analyse_reset.py)."""
    from isaaclab.utils import math as math_utils
    asset: RigidObject = env.scene[asset_cfg.name]
    root_states = asset.data.default_root_state[env_ids].clone()
    ranges = torch.tensor([pose_range.get(k, (0.0, 0.0)) for k in ("x", "y", "z", "roll", "pitch", "yaw")],
                          device=asset.device)
    rand = math_utils.sample_uniform(ranges[:, 0], ranges[:, 1], (len(env_ids), 6), device=asset.device)
    positions = root_states[:, 0:3] + env.scene.env_origins[env_ids] + rand[:, 0:3]
    footprint = getattr(env, "pib_object_footprint", None)
    if footprint is not None:
        a, b, square = footprint[env_ids, :3].unbind(-1)
        yaw = rand[:, 5]
        positions[:, 0] -= square * (a * yaw.cos().abs() + b * yaw.sin().abs() - a)   # Objekt liegt bei −x der Hand
    orientations = math_utils.quat_mul(root_states[:, 3:7],
                                       math_utils.quat_from_euler_xyz(rand[:, 3], rand[:, 4], rand[:, 5]))
    vranges = torch.tensor([velocity_range.get(k, (0.0, 0.0)) for k in ("x", "y", "z", "roll", "pitch", "yaw")],
                           device=asset.device)
    velocities = root_states[:, 7:13] + math_utils.sample_uniform(vranges[:, 0], vranges[:, 1], (len(env_ids), 6),
                                                                  device=asset.device)
    asset.write_root_pose_to_sim(torch.cat([positions, orientations], dim=-1), env_ids=env_ids)
    asset.write_root_velocity_to_sim(velocities, env_ids=env_ids)


class GraspDifficultyScheduler(ManagerTermBase):
    """Curriculum wie Dexsuites DifficultyScheduler (adr_curriculum.py), mit unserem Erfolgskriterium statt des
    Zielkommandos: je Umgebung Schwierigkeit +1 nach einer erfolgreichen Episode (bis zum Zeitende gehalten,
    Kippwinkel ≤ max_kipp_deg), sonst −1; difficulty_frac = Mittel / max_difficulty steuert über
    initial_final_interpolate_fn Schwerkraft und Beobachtungsrauschen (EXP-017)."""

    def __init__(self, cfg, env):
        super().__init__(cfg, env)
        self.current = torch.ones(env.num_envs, device=env.device) * self.cfg.params.get("init_difficulty", 0)
        self.difficulty_frac = torch.zeros((), device=env.device)

    def __call__(self, env: ManagerBasedRLEnv, env_ids, max_kipp_deg: float = 45.0, init_difficulty: int = 0,
                 min_difficulty: int = 0, max_difficulty: int = 10):
        import math
        ok = env.termination_manager.time_outs[env_ids] & (object_tilt(env)[env_ids] <= math.radians(max_kipp_deg))
        self.current[env_ids] = torch.where(ok, self.current[env_ids] + 1, self.current[env_ids] - 1).clamp(
            min=min_difficulty, max=max_difficulty)
        # Tensor wie bei Dexsuite: initial_final_interpolate_fn ruft .item() auf den interpolierten Werten auf
        self.difficulty_frac = self.current.mean() / max(max_difficulty, 1)
        return self.difficulty_frac


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


class FingertipProgress(ManagerTermBase):
    """Annäherung wie NVIDIA AllegroKuka/DexPBT (IsaacGymEnvs allegro_kuka_base.py; Petrenko et al. 2023): je
    Fingerspitze nur der Fortschritt zur Objektmitte, Σ max(kleinster bisheriger Abstand − aktueller, 0) — bloßes
    Nahesein bringt nichts (nicht ausnutzbar), dass die Spitzen die Mitte hoher Objekte nie erreichen, stört nicht.
    Nur in der Greifphase (vor dem Absenken; AllegroKuka: bis das Objekt angehoben ist). EXP-019, ersetzt
    fingertips_to_object (maß alle Handkörper, für 3–4 cm Fingerweg ohnehin zu flach — ADR-022)."""

    def __init__(self, cfg, env: ManagerBasedRLEnv):
        super().__init__(cfg, env)
        self.robot: Articulation = env.scene["robot"]
        self.obj: RigidObject = env.scene["object"]
        self.tip_ids = [self.robot.body_names.index(n) for n in FINGERTIP_LINKS]
        self.closest = torch.full((env.num_envs, len(self.tip_ids)), -1.0, device=env.device)   # −1: neu setzen

    def reset(self, env_ids=None):
        self.closest[slice(None) if env_ids is None else env_ids] = -1.0

    def __call__(self, env: ManagerBasedRLEnv, drop_start_s: float, max_delta: float = 0.05) -> torch.Tensor:
        d = torch.norm(self.robot.data.body_pos_w[:, self.tip_ids] - self.obj.data.root_pos_w[:, None, :], dim=-1)
        self.closest = torch.where(self.closest < 0, d, self.closest)
        delta = (self.closest - d).clamp(0.0, max_delta)          # AllegroKuka: clip(…, 0, 10)
        self.closest = torch.minimum(self.closest, d)
        return delta.sum(dim=-1) * (episode_time(env) < drop_start_s).float()


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


def object_xy_displacement(env: ManagerBasedRLEnv, ref_s: float, max_dist: float = 0.2,
                           object_cfg: SceneEntityCfg = SceneEntityCfg("object")) -> torch.Tensor:
    """Verschiebung [m] der Objektmitte in der Tischebene ggü. der Startlage (bis ref_s mitgeführt, dann
    eingefroren), gekappt bei max_dist. Als Strafe über die ganze Episode wie Cross-Embodiment Dexterous Grasping
    (Yuan et al. 2024: r = −0,3·‖xy − xy_Start‖); z bleibt beim Halteterm. EXP-023: die Policies zogen das Objekt
    ~13 cm Richtung Unterarm (tools/diag_objektweg.py), nichts in der Belohnung hielt die Lage in der Tischebene."""
    obj: RigidObject = env.scene[object_cfg.name]
    xy = obj.data.root_pos_w[:, :2]
    if getattr(env, "_pib_start_xy", None) is None or env._pib_start_xy.shape != xy.shape:
        env._pib_start_xy = xy.clone()
    before = episode_time(env) < ref_s
    env._pib_start_xy[before] = xy[before]
    return torch.norm(xy - env._pib_start_xy, dim=-1).clamp(max=max_dist)


def servo_torque_l2(env: ManagerBasedRLEnv, asset_cfg: SceneEntityCfg) -> torch.Tensor:
    """Σ (Moment / Stall-Moment)² der Servos in asset_cfg (EXP-025): 0 = kraftlos, ≈ Zahl der Servos bei Dauer-Stall.
    Wie die Moment-Strafe von HORA (Qi et al. 2022) und Isaac Labs joint_torques_l2, aber je Gelenk auf das Stall-Moment
    normiert (Servos verschieden stark). applied_torque = PD-Moment nach Begrenzung — dieselbe Größe wie die Leitplanke
    Stall-Anteil (eval_policy). Gelenke nur über params (SceneEntityCfg wird nur dort aufgelöst, ADR-017)."""
    robot: Articulation = env.scene[asset_cfg.name]
    tau = robot.data.applied_torque[:, asset_cfg.joint_ids] / robot.data.joint_effort_limits[:, asset_cfg.joint_ids]
    return torch.sum(torch.square(tau), dim=1)


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
