"""
check_objekt.py — Szenenprüfung eines Katalogobjekts (env_cfg.OBJECTS) in der Basisaufgabe, wie bewertet wird.

Je Umgebung: Maße (Bounding Box in der Welt), Abstand Oberfläche ↔ Handfläche, Boden ↔ Tischplatte, Bewegung in
den ersten 0,1 s (Startfehler/Überlappung), Kippwinkel kurz vor dem Absenken (steht das Objekt?), Masse laut PhysX,
gehalten am Ende. Ohne --policy Aktionen 0 (Hand bleibt in der Reset-Stellung). Bilder (t = 1, 60, 200 Schritte) und
Bericht nach isaac_sim/tools/_check_objekt_<objekt>*.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/check_objekt.py --headless --enable_cameras --objekt ycb_003_cracker
  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/check_objekt.py --headless --enable_cameras --objekt ycb_006_senf \
      --policy <run>/exported/policy.pt
"""
import argparse
import os
import re
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--objekt", required=True)
parser.add_argument("--policy", default="")
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--offen", action="store_true", help="Reset mit ganz geöffneter Hand (Gegenprobe Überlappung)")
parser.add_argument("--nur", type=str, default="", help="mit --offen: dieses Gelenk behält seinen Zufallsbereich")
parser.add_argument("--gier_deg", type=float, default=-1, help="Drehung beim Reset ±Grad statt aus dem Katalog")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import imageio.v2 as iio  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import GRASP_TIME_S, HAND_POS, TABLE_TOP_Z, PibGraspEnvCfg, apply_object  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "isaac_sim" / "tools"
STEM = f"_check_objekt_{args.objekt}"
cfg = apply_object(PibGraspEnvCfg(), args.objekt)
cfg.scene.num_envs = args.num_envs
if args.offen:
    cfg.events.reset_hand.params["ranges_deg"] = {k: (v if k == args.nur else (0.0, 0.0))
                                                  for k, v in cfg.events.reset_hand.params["ranges_deg"].items()}
    STEM += "_offen" + (f"_{args.nur}" if args.nur else "")
if args.gier_deg >= 0:
    import math
    cfg.events.reset_object.params["pose_range"]["yaw"] = (-math.radians(args.gier_deg), math.radians(args.gier_deg))
    STEM += f"_gier{args.gier_deg:g}"
cfg.seed = 1000
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg, render_mode="rgb_array")
u = env.unwrapped
policy = torch.jit.load(args.policy, map_location=u.device).eval() if args.policy else None
obj = u.scene["object"]
org = u.scene.env_origins

import isaaclab.sim as sim_utils  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402
cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
size = {}
for path in sim_utils.find_matching_prim_paths(obj.cfg.prim_path):
    size[int(re.search(r"env_(\d+)", path).group(1))] = \
        list(cache.ComputeWorldBound(u.scene.stage.GetPrimAtPath(path)).ComputeAlignedRange().GetSize())
masses = obj.root_physx_view.get_masses().reshape(u.num_envs, -1).sum(dim=1).cpu()

obs, _ = env.reset(seed=1000)
p0 = (obj.data.root_pos_w - org).clone()
robot = u.scene["robot"]
start_deg = {n: torch.rad2deg(robot.data.joint_pos[:, robot.joint_names.index(n)]).cpu()
             for n in ("thumb_left_rotator", "thumb_left_proximal", "index_left_proximal", "wrist_left")}
alive = torch.ones(u.num_envs, dtype=torch.bool, device=u.device)
frames, moved, tilt_table = {}, None, None
before_drop = int(GRASP_TIME_S / u.step_dt) - 2
with torch.inference_mode():
    for step in range(int(u.max_episode_length) - 1):
        act = policy(obs["policy"]) if policy else torch.zeros(u.num_envs, u.action_manager.total_action_dim,
                                                                 device=u.device)
        obs, _, term, trunc, _ = env.step(act)
        alive &= ~(term | trunc)
        if step == 5:
            delta = (obj.data.root_pos_w - org) - p0
            moved = delta.norm(dim=-1)
        if step == before_drop:
            tilt_table = torch.rad2deg(mdp.object_tilt(u))
        if step in (1, 60, 200):
            frames[step] = env.render()
for s, f in frames.items():
    iio.imwrite(OUT / f"{STEM}_t{s}.png", f)

d = p0.cpu()
lines = [f"== {args.objekt} | {args.policy or 'Aktionen 0'} | {u.num_envs} Umgebungen",
         f"{'Env':>4} {'Maße x/y/z [cm]':18s} {'Oberfl.→Handfl. [cm]':>20s} {'Boden−Tisch [mm]':>16s} "
         f"{'Bewegung 0,1 s [mm]':>19s} {'Kipp vor Absenken [°]':>21s} {'Masse [g]':>9s} {'gehalten':>9s}"]
bad = 0
for i in range(u.num_envs):
    sz = size[i]
    gap = 100 * (HAND_POS[0] - (d[i, 0].item() + sz[0] / 2))       # Handfläche bei x = HAND_POS[0]
    bottom = 1000 * (d[i, 2].item() - sz[2] / 2 - TABLE_TOP_Z)
    mv = 1000 * moved[i].item()
    bad += mv > 5
    lines.append(f"{i:4d} {'/'.join(f'{100 * s:.1f}' for s in sz):18s} {gap:20.1f} {bottom:16.1f} {mv:19.1f} "
                 f"{tilt_table[i].item():21.1f} {1000 * masses[i].item():9.0f} {'ja' if alive[i] else 'nein':>9s}  Δ x/y/z [mm] "
                 + "/".join(f"{1000 * v:.1f}" for v in delta[i].tolist()) + "  "
                 + " / ".join(f"{v[i].item():.0f}" for v in start_deg.values()))
big = int((moved > 0.01).sum())
lines += [f"Startfehler (Bewegung > 5 mm in 0,1 s): {bad}/{u.num_envs}, davon > 10 mm: {big}; Kippwinkel vor dem Absenken max "
          f"{tilt_table.max().item():.1f}°; gehalten am Ende: {int(alive.sum())}/{u.num_envs}",
          f"Bilder: {', '.join(f'{STEM}_t{s}.png' for s in frames)}", ""]
print("\n".join(lines), flush=True)
(OUT / f"{STEM}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
os._exit(0)
