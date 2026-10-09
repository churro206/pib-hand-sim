import argparse, sys, os
from pathlib import Path
from isaaclab.app import AppLauncher
p = argparse.ArgumentParser(); AppLauncher.add_app_launcher_args(p); a = p.parse_args()
app = AppLauncher(a).app
import gymnasium as gym, torch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp
from pib_grasp.env_cfg import PibGraspEnvCfg
cfg = PibGraspEnvCfg(); cfg.scene.num_envs = 1
cfg.events.object_scale = None
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg); u = env.unwrapped; env.reset()
r, o, t, s = u.scene["robot"], u.scene["object"], u.scene["table"], u.scene["fsr_index"]
org = u.scene.env_origins[0]
def dump(tag):
    print(f"== {tag}")
    print("object", [round(v,3) for v in (o.data.root_pos_w[0]-org).tolist()], "table", [round(v,3) for v in (t.data.root_pos_w[0]-org).tolist()])
    for i, n in enumerate(r.body_names):
        print(f"  {n:26s}", [round(v,3) for v in (r.data.body_pos_w[0,i]-org).tolist()])
    print("  sensor bodies", s.body_names, "force_matrix", tuple(s.data.force_matrix_w.shape) if s.data.force_matrix_w is not None else None)
    print("  net", [round(v,1) for v in s.data.net_forces_w[0].norm(dim=-1).tolist()])
    if s.data.force_matrix_w is not None: print("  obj", [round(v,1) for v in s.data.force_matrix_w[0,:,0].norm(dim=-1).tolist()])
dump("start")
act = torch.zeros(1, 8, device=u.device); act[:, 3:] = 1.0
for _ in range(30): env.step(act)
dump("nach 0.5 s schliessen")
sys.stdout.flush(); os._exit(0)
