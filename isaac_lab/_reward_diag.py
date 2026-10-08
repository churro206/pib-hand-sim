"""
_reward_diag.py — Größenordnung der Belohnungsterme vor einem Lauf prüfen (ADR-017-Arbeitsregel).

Lässt eine Policy in einer Task-Variante laufen und mittelt je Term den Beitrag je Sekunde
(Gewicht × Term, aus dem Reward-Manager) über laufende Umgebungen — vor dem Absenken (0–2 s) und in
der Haltephase (ab 2,5 s). Ausgabe angehängt an isaac_sim/tools/_reward_diag.txt.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/_reward_diag.py --headless --task Pib-Grasp-Hand-Left-HeavyDexsuite-v0 \
      --policy <run>/exported/policy.pt
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--task", required=True)
parser.add_argument("--policy", required=True)
parser.add_argument("--num_envs", type=int, default=256)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pib_grasp  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from pib_grasp.env_cfg import DROP_DEPTH, DROP_SPEED, GRASP_TIME_S  # noqa: E402

cfg = parse_env_cfg(args.task, num_envs=args.num_envs)
cfg.seed = 1000
env = gym.make(args.task, cfg=cfg)
u = env.unwrapped
policy = torch.jit.load(args.policy, map_location=u.device).eval()
rm = u.reward_manager
names = rm.active_terms
hold_s = GRASP_TIME_S + DROP_DEPTH / DROP_SPEED
sums = {k: torch.zeros(len(names), device=u.device) for k in ("vor", "halten")}
counts = {k: 0.0 for k in sums}
held_end = 0
obs, _ = env.reset(seed=1000)
alive = torch.ones(u.num_envs, dtype=torch.bool, device=u.device)
with torch.inference_mode():
    for step in range(int(u.max_episode_length) - 1):
        obs, _, term, trunc, _ = env.step(policy(obs["policy"]))
        alive &= ~(term | trunc)
        t = (step + 1) * u.step_dt
        key = "vor" if t < GRASP_TIME_S else ("halten" if t >= hold_s else None)
        if key and alive.any():
            sums[key] += rm._step_reward[alive].sum(dim=0)
            counts[key] += float(alive.sum())
held_end = int(alive.sum())
lines = [f"== {args.task} | {args.policy}",
         f"noch gehalten am Ende: {held_end}/{u.num_envs}",
         f"{'Term':24s} {'vor Absenken [1/s]':>20s} {'Haltephase [1/s]':>18s}"]
for i, n in enumerate(names):
    lines.append(f"{n:24s} {sums['vor'][i] / max(counts['vor'], 1):20.3f} {sums['halten'][i] / max(counts['halten'], 1):18.3f}")
lines.append("")
print("\n".join(lines), flush=True)
with open(Path(__file__).resolve().parent.parent / "isaac_sim" / "tools" / "_reward_diag.txt", "a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
os._exit(0)
