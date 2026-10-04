import argparse
from isaaclab.app import AppLauncher
p = argparse.ArgumentParser(); AppLauncher.add_app_launcher_args(p); a = p.parse_args()
app = AppLauncher(a).app
import math, os, torch
import isaaclab.sim as sim_utils
from isaaclab.assets import Articulation
from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG
sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1/120, device=a.device, gravity=(0.0, 0.0, 0.0)))
r = Articulation(PIB_HAND_LEFT_V5_CFG.replace(prim_path="/World/Hand"))
sim.reset()
def settle(deg, thumb_rot=0.0):
    t = torch.zeros_like(r.data.joint_pos)
    for f in ["index","middle","ring","pinky","thumb"]:
        t[:, r.joint_names.index(f"{f}_left_proximal")] = math.radians(deg)
    t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(thumb_rot)
    for _ in range(240):
        r.set_joint_position_target(t); r.write_data_to_sim(); sim.step(); r.update(sim.get_physics_dt())
    return {n: r.data.body_link_pos_w[0, i].tolist() for i, n in enumerate(r.body_names)}
out = []
for label, deg, rot in [("offen", 0, 0), ("gebeugt60", 60, 0), ("daumen_rot90", 0, 90)]:
    pos = settle(deg, rot)
    out.append(f"== {label}")
    for n, v in pos.items():
        out.append(f"{n:26s} " + " ".join(f"{x:+.4f}" for x in v))
txt = "\n".join(out); print(txt)
open("/tmp/claude-1000/-home-leon-repos-pib-hand-sim/f504ffc7-a788-40a5-bc07-4d2746aa6048/scratchpad/geometry.txt","w").write(txt+"\n")
os._exit(0)
