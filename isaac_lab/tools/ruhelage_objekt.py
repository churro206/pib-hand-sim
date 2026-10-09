"""
ruhelage_objekt.py — Ruhelage („stable pose“) eines Katalogobjekts auf dem Tisch messen, damit es beim Reset genau so
gespawnt wird, wie es von selbst steht (kein Fallen/Setzen/Kippen bei t = 0).

Objekt wenige mm über dem Tisch, Hand ganz offen, Aktionen 0, 1,5 s (vor dem Absenken). Gemessen je Umgebung: Höhe des
Objektursprungs über der Tischplatte und Neigung im Körperrahmen (q_reset⁻¹ · q_end, unabhängig von der Gierdrehung),
dazu Restbewegung und Streuung. Ergebnis als Eintrag für env_cfg.OBJECTS[...]["ruhelage"].
Bericht: isaac_sim/tools/_ruhelage_<objekt>.txt

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/ruhelage_objekt.py --headless --objekt ycb_004_zucker
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--objekt", required=True)
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--fall_mm", type=float, default=3.0, help="Start über dem Tisch [mm]")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import GRASP_TIME_S, TABLE_TOP_Z, PibGraspEnvCfg, apply_object  # noqa: E402
from isaaclab.utils.math import quat_inv, quat_mul  # noqa: E402

cfg = apply_object(PibGraspEnvCfg(), args.objekt)
cfg.scene.num_envs = args.num_envs
cfg.seed = 1000
cfg.events.reset_hand.params["ranges_deg"] = {k: (0.0, 0.0) for k in cfg.events.reset_hand.params["ranges_deg"]}
cfg.events.place_objects.params["lift"] = args.fall_mm / 1000      # ohne gespeicherte Ruhelage, wenige mm Fall
cfg.events.place_objects.params["root_height"] = None
cfg.scene.object.init_state.rot = (1.0, 0.0, 0.0, 0.0)
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg)
u = env.unwrapped
obj = u.scene["object"]
org = u.scene.env_origins

u.reset(seed=1000)
q_reset = obj.data.root_quat_w.clone()
act = torch.zeros(u.num_envs, u.action_manager.total_action_dim, device=u.device)
steps = int(1.5 / u.step_dt)
with torch.inference_mode():
    for k in range(steps):
        u.step(act)
        if k == steps - 31:
            p_half = (obj.data.root_pos_w - org).clone()
assert steps * u.step_dt < GRASP_TIME_S
p_end = obj.data.root_pos_w - org
height = p_end[:, 2] - TABLE_TOP_Z
q_settle = quat_mul(quat_inv(q_reset), obj.data.root_quat_w)
q_settle = q_settle * torch.sign(q_settle[:, :1])                    # w ≥ 0 (gleiche Hemisphäre)
tilt = torch.rad2deg(mdp.object_tilt(u))
# typische Ruhelage = Umgebung mit dem Median der Neigung (Ausreißer — umgefallen/geschaukelt — nicht mitteln)
med = int(tilt.argsort()[len(tilt) // 2])
typical = (tilt - tilt[med]).abs() < 1.0
q_typ = q_settle[typical].mean(0)
q_typ = q_typ / q_typ.norm()
h_typ = height[typical].mean()
rest_motion = 1000 * (p_end - p_half).norm(dim=-1)                    # letzte 0,5 s

lines = [f"== {args.objekt} | {u.num_envs} Umgebungen, Start {args.fall_mm} mm über dem Tisch, Hand offen, 1,5 s",
         f"Ursprung über Tischplatte [mm]: Mittel {1000 * height.mean().item():.2f}, Streuung "
         f"{1000 * height.std().item():.2f}, min {1000 * height.min().item():.2f}, max {1000 * height.max().item():.2f}",
         f"Neigung [°]: Mittel {tilt.mean().item():.2f}, min {tilt.min().item():.2f}, max {tilt.max().item():.2f}",
         f"typische Ruhelage (Neigung {tilt[med].item():.2f}° ± 1°): {int(typical.sum())}/{u.num_envs} Umgebungen, "
         f"Ursprung {1000 * h_typ.item():.2f} mm über der Tischplatte",
         f"Restbewegung in den letzten 0,5 s: max {rest_motion.max().item():.2f} mm",
         "Neigung je Umgebung sortiert [°]: " + " ".join(f"{v:.1f}" for v in sorted(tilt.tolist())),
         "",
         f'Eintrag: "ruhelage": {{"hoehe": {h_typ.item():.5f}, "quat": ('
         + ", ".join(f"{v:.5f}" for v in q_typ.tolist()) + ")}"]
out = Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / f"_ruhelage_{args.objekt}.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines), flush=True)
os._exit(0)
