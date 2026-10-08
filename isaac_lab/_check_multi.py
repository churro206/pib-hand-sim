"""
_check_multi.py — Szenenprüfung Objektvielfalt (EXP-013) statt Fenstertest (Leon remote, 2026-10-08).

Baut Pib-Grasp-Hand-Left-HeavyMulti-v0, lässt eine Policy laufen und prüft je Form: Startlage aus der
Bounding Box (Abstand zur Handfläche, Boden auf dem Tisch), Bewegung in den ersten 0,1 s (Startfehler =
Überlappung/Fall), gehalten nach dem Absenken. Speichert Einzelbilder nach isaac_sim/tools/_check_multi_*.png
und den Bericht nach isaac_sim/tools/_check_multi.txt.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/_check_multi.py --headless --enable_cameras --policy <run>/exported/policy.pt
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--policy", required=True)
parser.add_argument("--num_envs", type=int, default=36)
parser.add_argument("--null", action="store_true", help="Aktionen 0 (Finger bleiben in der Reset-Stellung)")
parser.add_argument("--offen", action="store_true", help="Reset mit ganz geöffneter Hand (Gegenprobe Überlappung)")
parser.add_argument("--nur", type=str, default="", help="mit --offen: dieses Gelenk behält seinen Zufallsbereich")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import imageio.v2 as iio  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pib_grasp  # noqa: E402,F401
from isaaclab_tasks.utils import parse_env_cfg  # noqa: E402
from pib_grasp.env_cfg import HAND_POS, TABLE_TOP_Z  # noqa: E402

TASK = "Pib-Grasp-Hand-Left-HeavyMulti-v0"
OUT = Path(__file__).resolve().parent.parent / "isaac_sim" / "tools"
cfg = parse_env_cfg(TASK, num_envs=args.num_envs)
cfg.seed = 1000
if args.offen:
    cfg.events.reset_hand.params["ranges_deg"] = {k: (v if k == args.nur else (0.0, 0.0))
                                                  for k, v in cfg.events.reset_hand.params["ranges_deg"].items()}
env = gym.make(TASK, cfg=cfg, render_mode="rgb_array")
u = env.unwrapped
policy = torch.jit.load(args.policy, map_location=u.device).eval()
obj = u.scene["object"]
org = u.scene.env_origins

from pxr import Usd, UsdGeom  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
import re  # noqa: E402
cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
info = {}
for path in sim_utils.find_matching_prim_paths(obj.cfg.prim_path):
    i = int(re.search(r"env_(\d+)", path).group(1))
    prim = u.scene.stage.GetPrimAtPath(path)
    kind = "Zylinder" if any(c.GetTypeName() == "Cylinder" for c in Usd.PrimRange(prim)) else "Quader"
    size = cache.ComputeWorldBound(prim).ComputeAlignedRange().GetSize()
    info[i] = (kind, [round(100 * s, 1) for s in size])

obs, _ = env.reset(seed=1000)
p0 = (obj.data.root_pos_w - org).clone()
alive = torch.ones(u.num_envs, dtype=torch.bool, device=u.device)
frames = {}
moved = None
with torch.inference_mode():
    for step in range(int(u.max_episode_length) - 1):
        act = policy(obs["policy"])
        obs, _, term, trunc, _ = env.step(torch.zeros_like(act) if args.null else act)
        alive &= ~(term | trunc)
        if step == 5:
            moved = ((obj.data.root_pos_w - org) - p0).norm(dim=-1)
        if step in (1, 60, 200):
            frames[step] = env.render()
for s, f in frames.items():
    iio.imwrite(OUT / f"_check_multi_t{s}.png", f)

d = p0.cpu()
lines = [f"== {TASK} | {'Aktionen 0' if args.null else args.policy} | {u.num_envs} Umgebungen",
         f"{'Env':>4} {'Form':9s} {'Maße x/y/z [cm]':18s} {'Oberfl.→Handfl. [cm]':>20s} {'Boden−Tisch [mm]':>16s} "
         f"{'Bewegung 0,1 s [mm]':>19s} {'gehalten':>9s}"]
bad = 0
for i in range(u.num_envs):
    kind, size = info[i]
    gap = 100 * (HAND_POS[0] - (d[i, 0].item() + size[0] / 200))       # Handfläche bei x = HAND_POS[0]
    bottom = 1000 * (d[i, 2].item() - size[2] / 200 - TABLE_TOP_Z)
    mv = 1000 * moved[i].item()
    bad += mv > 5
    lines.append(f"{i:4d} {kind:9s} {'/'.join(f'{s:.1f}' for s in size):18s} {gap:20.1f} {bottom:16.1f} {mv:19.1f} "
                 f"{'ja' if alive[i] else 'nein':>9s}")
lines += [f"Startfehler (Bewegung > 5 mm in 0,1 s): {bad}/{u.num_envs}; gehalten am Ende: {int(alive.sum())}/{u.num_envs}",
          f"Bilder: {', '.join(f'_check_multi_t{s}.png' for s in frames)}", ""]
print("\n".join(lines), flush=True)
(OUT / "_check_multi.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
os._exit(0)
