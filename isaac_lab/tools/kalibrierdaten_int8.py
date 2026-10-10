"""
kalibrierdaten_int8.py — Beobachtungen aus Sim-Rollouts als Kalibrierdaten für die int8-Quantisierung (M2, conventions.md →
„ST Edge AI“: Kalibrierdaten aus Sim-Rollouts).

Rollout der Policy (TorchScript, deterministisch, Aktion wie im Training begrenzt/geglättet) in der Trainingsaufgabe (Objekte
und Zufall wie im Training), je Schritt der Beobachtungsvektor des Actors (105 Werte, vor der Normalisierung — die steckt im
Netz). Zufällig gezogen: Kalibrier- und Testmenge, gespeichert als .npz (calib, test).

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/kalibrierdaten_int8.py --headless --policy <run>/exported/policy.pt \
      --task Pib-Grasp-Hand-Left-HeavyMultiProgressClipXY-v0 --action_clip 1.0 --out logs/int8/<name>/daten.npz
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--policy", required=True)
parser.add_argument("--task", required=True)
parser.add_argument("--out", required=True)
parser.add_argument("--num_envs", type=int, default=256)
parser.add_argument("--schritte", type=int, default=540, help="Policy-Schritte (2 Episoden à 4,5 s)")
parser.add_argument("--action_clip", type=float, default=0.0)
parser.add_argument("--kalibrierung", type=int, default=2000)
parser.add_argument("--test", type=int, default=2000)
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402

cfg = parse_env_cfg(args.task, num_envs=args.num_envs)
cfg.seed = 3000                                              # weder Trainings- noch Bewertungs-Seed
env = gym.make(args.task, cfg=cfg)
policy = torch.jit.load(args.policy, map_location=env.unwrapped.device).eval()
obs, _ = env.reset(seed=3000)
rows = []
with torch.inference_mode():
    for _ in range(args.schritte):
        o = obs["policy"]
        rows.append(o.cpu().numpy())
        act = policy(o)
        if args.action_clip > 0:
            act = act.clamp(-args.action_clip, args.action_clip)
        obs, *_ = env.step(act)
data = np.concatenate(rows).astype(np.float32)
rng = np.random.default_rng(0)
idx = rng.permutation(len(data))
out = Path(args.out)
out.parent.mkdir(parents=True, exist_ok=True)
np.savez(out, calib=data[idx[:args.kalibrierung]], test=data[idx[args.kalibrierung:args.kalibrierung + args.test]])
print(f"Kalibrierdaten: {len(data)} Beobachtungen ({data.shape[1]} Werte) → {out} "
      f"(Kalibrierung {args.kalibrierung}, Test {args.test})", flush=True)
os._exit(0)
