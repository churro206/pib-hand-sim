"""
_diag_anheben.py — Diagnose: Warum heben die Policies das Objekt vor dem Absenken an? (2026-10-08)

Hypothese: Der Annäherungsterm (fingertips_to_object = Dexsuite object_ee_distance, größter Abstand
Fingerspitze ↔ Objektmitte) belohnt bei fester Hand, die Objektmitte zwischen Daumen (oben) und kleinen
Finger zu schieben → Anheben. Die Policy läuft bis kurz vor dem Absenken; dann wird für die tatsächlichen
Fingerspitzen der Term über einer gedachten Höhenverschiebung der Objektmitte ausgewertet (rein
geometrisch, keine Physik) und das Optimum mit der tatsächlichen Höhe verglichen.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/_diag_anheben.py --headless --policy <run>/exported/policy.pt
Bericht: isaac_sim/tools/_diag_anheben.txt (angehängt je Aufruf)
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--policy", required=True)
parser.add_argument("--objekt", default="zylinder_d6")
parser.add_argument("--num_envs", type=int, default=256)
parser.add_argument("--t", type=float, default=1.9, help="Zeitpunkt der Auswertung [s] (vor dem Absenken)")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import PibGraspEnvCfg, apply_object  # noqa: E402

cfg = apply_object(PibGraspEnvCfg(), args.objekt)
cfg.scene.num_envs = args.num_envs
cfg.seed = 1000
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg)
u = env.unwrapped
policy = torch.jit.load(args.policy, map_location=u.device).eval()
robot, obj = u.scene["robot"], u.scene["object"]
tip_ids = [robot.body_names.index(n) for n in mdp.FINGERTIP_LINKS]
STD, W = 0.4, 1.0                     # wie RewardsCfg.fingertips_to_object

obs, _ = env.reset(seed=1000)
z0 = obj.data.root_pos_w[:, 2].clone()
alive = torch.ones(u.num_envs, dtype=torch.bool, device=u.device)
steps = round(args.t / u.step_dt)
with torch.inference_mode():
    for _ in range(steps):
        obs, _, term, trunc, _ = env.step(policy(obs["policy"]))
        alive &= ~(term | trunc)
    tips = robot.data.body_pos_w[:, tip_ids]                       # (N, 5, 3)
    c = obj.data.root_pos_w                                         # (N, 3)
    lift = (c[:, 2] - z0)                                           # tatsächliche Höhe ggü. Start [m]
    dz = torch.linspace(-0.10, 0.10, 401, device=u.device)         # gedachte Verschiebung der Mitte
    shifted = c[:, None, :].repeat(1, len(dz), 1)
    shifted[:, :, 2] += dz[None, :]
    dist = torch.norm(tips[:, None, :, :] - shifted[:, :, None, :], dim=-1).max(dim=-1).values   # (N, D)
    r = W * (1 - torch.tanh(dist / STD))
    best = dz[r.argmax(dim=1)]                                      # Verschiebung zum Optimum
    i0 = (dz.abs()).argmin()
    r_now = r[:, i0]
    # Wert, wenn die Mitte auf Starthöhe stünde (Objekt auf dem Tisch)
    on_table = torch.stack([r[k, (dz - (-lift[k])).abs().argmin()] for k in range(u.num_envs)])
    far = (tips[:, :, 2] - c[:, None, 2])                           # Höhe der Fingerspitzen relativ zur Mitte
    a = alive
    lines = [
        f"== {args.policy} | Objekt {args.objekt} | t = {args.t} s | {int(a.sum())}/{u.num_envs} Episoden laufen",
        f"tatsächliche Höhe ggü. Start:         Median {1000 * lift[a].median():6.1f} mm  (Mittel {1000 * lift[a].mean():6.1f})",
        f"Optimum des Annäherungsterms bei:     Median {1000 * (lift + best)[a].median():6.1f} mm ggü. Start",
        f"  → von der jetzigen Höhe aus noch:   Median {1000 * best[a].median():6.1f} mm",
        f"Annäherungsterm jetzt / auf dem Tisch: {r_now[a].mean():.3f} / {on_table[a].mean():.3f} je s "
        f"(Gewinn durch Anheben {100 * (r_now[a].mean() / on_table[a].mean() - 1):+.1f} %)",
        "Fingerspitzen relativ zur Objektmitte (z, Median) Daumen…klein [mm]: "
        + " ".join(f"{1000 * far[a, k].median():+.0f}" for k in range(5)),
        "Weiteste Fingerspitze (Anteil): " + " ".join(
            f"{n}={100 * ((torch.norm(tips - c[:, None, :], dim=-1).argmax(dim=1) == k)[a].float().mean()):.0f}%"
            for k, n in enumerate(["Daumen", "Zeige", "Mittel", "Ring", "klein"])),
    ]
    # Hypothese 2: Anheben als Vorbereitung — Nachrutschen nach dem Absenken je Episode gegen die Höhe davor
    z_pre = c[:, 2].clone()
    sag = torch.zeros(u.num_envs, device=u.device)
    alive2 = alive.clone()
    for _ in range(round((3.5 - args.t) / u.step_dt)):
        obs, _, term, trunc, _ = env.step(policy(obs["policy"]))
        alive2 &= ~(term | trunc)
        z = obj.data.root_pos_w[:, 2]
        sag = torch.where(alive2, torch.maximum(sag, z_pre - z), sag)
    held = alive2 & alive
    lines.append(f"Nachrutschen nach dem Absenken (max. Absinken ggü. Höhe bei {args.t} s, bis 3,5 s, gehaltene Episoden):")
    for lo, hi in ((-1, 0.005), (0.005, 0.02), (0.02, 0.04), (0.04, 1)):
        m = alive & (lift > lo) & (lift <= hi)
        if m.sum() == 0:
            continue
        h = m & held
        s = sag[h]
        lines.append(f"  Höhe vor dem Absenken {1000 * max(lo, 0):3.0f}–{min(1000 * hi, 999):3.0f} mm: {int(m.sum()):3d} Ep., "
                     f"gehalten {100 * h.sum() / m.sum():5.1f} %, Nachrutschen Median {1000 * s.median() if len(s) else float('nan'):5.1f} mm, "
                     f"Halte-Term (std 2 cm) ≈ {(1 - torch.tanh(s / 0.02)).mean() if len(s) else float('nan'):.2f}")
    lines.append("")
print("\n".join(lines), flush=True)
out = Path(__file__).resolve().parent.parent / "isaac_sim" / "tools" / "_diag_anheben.txt"
with open(out, "a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
os._exit(0)
