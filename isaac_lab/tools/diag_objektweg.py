"""
diag_objektweg.py — Wohin bewegen Policies das Objekt? (2026-10-10: „Objekt wandert Richtung Unterarm“)

Basisaufgabe, deterministisch, 64 Umgebungen, Seed 1000; je Policy und Objekt die mittlere Verschiebung des Objekts ggü.
t = 0,1 s in Weltkoordinaten (+x = Richtung Handfläche, +y = Richtung Unterarm/Handgelenk, z = Höhe), die Änderung des
Abstands zum Unterarmansatz (urdf_elbow_lower — das maß der fehlerhafte Annäherungsterm bis EXP-018) und die
Unterarmdrehung; nur Episoden, in denen das Objekt bis zum Ende gehalten wurde. Kontrolle ohne Belohnung: Regel
„alle schließen“ (wie EXP-014). Bericht: isaac_sim/tools/_diag_objektweg_<objekt>.txt

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/diag_objektweg.py --headless \
      --policy EXP-018=<run>/exported/policy.pt EXP-022=<run>/exported/policy.pt:1.0 ...   (:1.0 = action_clip)
"""
import argparse
import math
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--policy", nargs="+", required=True, help="Name=Pfad[:clip]")
parser.add_argument("--objekt", default="zylinder_d6", help="ein Objekt je Lauf (Isaac Lab: eine Umgebung je Prozess)")
parser.add_argument("--num_envs", type=int, default=64)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp  # noqa: E402,F401
from pib_grasp.env_cfg import PibGraspEnvCfg, apply_object  # noqa: E402
from pib_hand_left_v5_cfg import SERVO_JOINTS  # noqa: E402
from isaaclab.sensors import ContactSensorCfg  # noqa: E402

BODIES = ["urdf_elbow_lower", "urdf_forearm_left", "urdf_palm_left", "urdf_thumb_rotator_left", "urdf_thumb_proximal",
          "urdf_thumb_tip"] + [f"urdf_finger_{seg}{sfx}" for sfx in ("", "_2", "_3", "_4") for seg in ("proximal", "distal", "tip")]
SHORT = {"urdf_elbow_lower": "Ellbogen", "urdf_forearm_left": "Unterarm", "urdf_palm_left": "Handfläche",
         "urdf_thumb_rotator_left": "D-Rot", "urdf_thumb_proximal": "D-Grund", "urdf_thumb_tip": "D-Spitze"}
for _sfx, _f in (("", "Z"), ("_2", "M"), ("_3", "R"), ("_4", "K")):
    for _seg, _n in (("proximal", "Grund"), ("distal", "Mitte"), ("tip", "Spitze")):
        SHORT[f"urdf_finger_{_seg}{_sfx}"] = f"{_f}-{_n}"

MARKS = [0.1, 1.0, 2.0, 2.5, 4.3]          # s: Start, Greifen, vor dem Absenken, Tisch unten, Ende


def rule_policy(u):
    """Regel „alle schließen“ wie EXP-014 (schliessen 0,2, Rotator 90° bis 0,4 s, Unterarm/Handgelenk halten)."""
    robot = u.scene["robot"]
    ids = [robot.joint_names.index(n) for n in SERVO_JOINTS]
    scale = torch.tensor([0.03, 0.03] + [0.1] * 6, device=u.device)
    hold = {}

    def act(obs):
        q = robot.data.joint_pos[:, ids]
        t = u.episode_length_buf * u.step_dt
        new = t <= u.step_dt + 1e-6
        if "q" not in hold:
            hold["q"] = q.clone()
        hold["q"][new] = q[new]
        a = torch.zeros_like(q)
        a[:, :2] = ((hold["q"][:, :2] - q[:, :2]) / scale[:2]).clamp(-1, 1)
        a[:, 2] = ((math.radians(90) - q[:, 2]) / scale[2]).clamp(-1, 1)
        a[:, 3:] = 0.2 * (t >= 0.4).float()[:, None]
        return a
    return act


objekt = args.objekt
lines = [f"== Objektweg ggü. t = 0,1 s (gehaltene Episoden, Mittel; +x Richtung Handfläche, +y Richtung Unterarm) "
         f"| {args.num_envs} Umgebungen, Seed 1000", ""]
if True:
    cfg = apply_object(PibGraspEnvCfg(), objekt)
    cfg.scene.num_envs = args.num_envs
    cfg.seed = 1000
    cfg.scene.object.spawn.activate_contact_sensors = True
    cfg.scene.object_contact = ContactSensorCfg(
        prim_path="{ENV_REGEX_NS}/Object", history_length=cfg.decimation,
        filter_prim_paths_expr=[f"{{ENV_REGEX_NS}}/Robot/{b}" for b in BODIES] + ["{ENV_REGEX_NS}/Table"])
    env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg)
    u = env.unwrapped
    robot, obj = u.scene["robot"], u.scene["object"]
    elbow = robot.body_names.index("urdf_elbow_lower")
    forearm = robot.joint_names.index("forearm_left")
    steps = {round(m / u.step_dt): m for m in MARKS}
    lines.append(f"-- {objekt}")
    lines.append(f"{'Policy':10s} {'gehalten':>8s}   " + "   ".join(f"t={m:.1f}s Δx/Δy/Δz [mm] ΔElle" for m in MARKS[1:])
                 + "   Unterarm Ende [°]")
    for spec in [("Regel", None, 0.0)] + [(s.split("=", 1)[0], *(s.split("=", 1)[1].rsplit(":", 1) + ["0"])[:2])
                                          for s in args.policy]:
        name, path, clip = spec[0], spec[1], float(spec[2] or 0)
        policy = rule_policy(u) if path is None else torch.jit.load(path, map_location=u.device).eval()
        rec = {}
        with torch.inference_mode():                 # auch reset: Tensoren aus inference_mode nicht außerhalb ändern
            obs, _ = env.reset(seed=1000)
            alive = torch.ones(u.num_envs, dtype=torch.bool, device=u.device)
            for k in range(1, int(u.max_episode_length)):
                a = policy(obs["policy"])
                if clip > 0:
                    a = a.clamp(-clip, clip)
                obs, _, term, trunc, _ = env.step(a)
                alive &= ~term                       # gefallen/instabil; Zeitende am Schluss zählt als gehalten
                if k in steps:
                    p = obj.data.root_pos_w - u.scene.env_origins
                    d_elbow = (obj.data.root_pos_w - robot.data.body_pos_w[:, elbow]).norm(dim=-1)
                    rec[steps[k]] = (p.clone(), d_elbow.clone(), robot.data.joint_pos[:, forearm].clone())
        p0, e0, f0 = rec[MARKS[0]]
        m = alive
        cells = []
        for t in MARKS[1:]:
            p, e, _ = rec[t]
            dp = 1000 * (p - p0)[m].mean(0) if m.any() else torch.zeros(3)
            de = 1000 * (e - e0)[m].mean() if m.any() else torch.tensor(0.0)
            cells.append(f"{dp[0]:+6.1f}/{dp[1]:+6.1f}/{dp[2]:+6.1f} {de:+6.1f}")
        sens = u.scene["object_contact"]
        force = sens.data.force_matrix_w_history[:, :, 0].norm(dim=-1).amax(dim=1)[:, :len(BODIES)]   # (N, Körper)
        share = ((force > 1.0)[m].float().mean(0) if m.any() else torch.zeros(len(BODIES)))
        mean_f = (force[m].mean(0) if m.any() else torch.zeros(len(BODIES)))
        top = sorted(range(len(BODIES)), key=lambda b: -mean_f[b].item())[:6]
        contacts = ", ".join(f"{SHORT[BODIES[b]]} {mean_f[b]:.0f} N ({100 * share[b]:.0f} %)" for b in top if mean_f[b] > 0.5)
        fe = math.degrees((rec[MARKS[-1]][2] - f0)[m].abs().mean().item()) if m.any() else float("nan")
        lines.append(f"{name:10s} {int(m.sum()):4d}/{u.num_envs:<3d}   " + "   ".join(cells) + f"   {fe:6.1f}")
        lines.append(f"{'':10s} Kontakte am Ende (Kraft, Anteil Umgebungen > 1 N): {contacts or '–'}")
        print(lines[-1], flush=True)
    lines.append("")
out = Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / f"_diag_objektweg_{objekt}.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines), flush=True)
os._exit(0)
