"""
scripted_grasp_test.py — Szene der Greifaufgabe ohne Policy prüfen.

Fester Griff: erst fährt der Daumen-Rotator 0,4 s auf --thumb_rot (Grad, je Episode
ein Wert), dann schließen alle Finger-/Daumen-MCPs mit voller Schrittweite. Misst zusätzlich
den größten Kippwinkel der Dose (Kippabbruch wie in eval-v1 aus) — ist „aufrecht halten“ mit
dieser Hand überhaupt erreichbar? Handgelenk
und Unterarm bleiben. Nur Machbarkeitstest der Szene — die Policy soll die Opposition
selbst lernen. Zeigt, ob die Szene stimmt (Startkontakte, Tisch
senkt sich, Sensoren) und ob ein stumpfer Griff die Dose überhaupt hält.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/scripted_grasp_test.py --headless --num_envs 16
Mit Fenster zum Zuschauen (Echtzeit, Fenster bleibt am Ende offen):
  ~/IsaacLab/isaaclab.sh -p isaac_lab/scripted_grasp_test.py --num_envs 16 --real_time --thumb_rot 0,45,90
Bericht zusätzlich in isaac_sim/tools/_scripted_grasp_test.txt.
"""
import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--num_envs", type=int, default=16)
parser.add_argument("--thumb_rot", type=str, default="0", help="Rotator-Ziel [°] je Episode, z.B. 0,45,90")
parser.add_argument("--real_time", action="store_true", help="Auf Echtzeit bremsen (zum Zuschauen)")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
simulation_app = AppLauncher(args_cli).app

import math  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import GRASP_TIME_S, TABLE_POS, TABLE_SIZE, PibGraspEnvCfg  # noqa: E402

REPORT = Path(__file__).resolve().parent.parent / "isaac_sim" / "tools" / "_scripted_grasp_test.txt"
lines = []


def log(msg=""):
    print(msg, flush=True)
    lines.append(msg)


cfg = PibGraspEnvCfg()
cfg.scene.num_envs = args_cli.num_envs
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg)
uenv = env.unwrapped
obs, _ = env.reset()
log(f"Beobachtung policy {tuple(obs['policy'].shape)}, critic {tuple(obs['critic'].shape)}")
log(f"Aktionen {uenv.action_manager.total_action_dim}: {uenv.action_manager.get_term('servos')._joint_names}")

term = uenv.action_manager.get_term("servos")
names = term._joint_names
close = torch.tensor([1.0 if n.endswith("_proximal") else 0.0 for n in names], device=uenv.device)
rot_i = names.index("thumb_left_rotator")
rot_joint = None   # gesetzt nach robot = ...
ROTATE_S = 0.4


def scripted_action(t: float, rot_target_rad: float) -> torch.Tensor:
    a = torch.zeros(uenv.num_envs, len(names), device=uenv.device)
    q = robot.data.joint_pos[:, rot_joint]
    a[:, rot_i] = ((rot_target_rad - q) / term._scale[:, rot_i]).clamp(-1.0, 1.0)
    if t > ROTATE_S:
        a += close
    return a


robot = uenv.scene["robot"]
rot_joint = robot.joint_names.index("thumb_left_rotator")
obj = uenv.scene["object"]
steps = int(cfg.episode_length_s / uenv.step_dt)
table_edge_x = TABLE_POS[0] + TABLE_SIZE[0] / 2      # Tischkante zur Hand hin (Env-Frame)

rot_targets = [float(v) for v in args_cli.thumb_rot.split(",")]
for episode, rot_deg in enumerate(rot_targets):
    if episode > 0:
        env.reset()
    log()
    log(f"══ Episode {episode + 1}: Daumen-Rotator {rot_deg:.0f}°")
    start = obj.data.root_pos_w.clone() - uenv.scene.env_origins
    prev = start.clone()
    total_reward = torch.zeros(uenv.num_envs, device=uenv.device)
    dropped_at = torch.full((uenv.num_envs,), -1.0, device=uenv.device)
    max_tilt = torch.zeros(uenv.num_envs, device=uenv.device)
    drop_pos = torch.zeros_like(start)
    for k in range(steps):
        t0 = time.time()
        t = (k + 1) * uenv.step_dt
        if k == 0:
            f0 = mdp.fingertip_forces(uenv)
            log(f"Start: FSR [N] (Daumen, Zeige, Mittel, Ring, klein) Env0 = {[round(v, 2) for v in f0[0].tolist()]}")
        obs, rew, terminated, trunc, _ = env.step(scripted_action(t, math.radians(rot_deg)))
        total_reward += rew
        newly = terminated & (dropped_at < 0)
        dropped_at[newly] = t
        drop_pos[newly] = prev[newly]          # letzte Lage vor dem automatischen Reset
        prev = obj.data.root_pos_w.clone() - uenv.scene.env_origins
        alive = dropped_at < 0
        max_tilt[alive] = torch.maximum(max_tilt[alive], mdp.object_tilt(uenv)[alive])
        if abs(t - (GRASP_TIME_S - 0.05)) < uenv.step_dt / 2 or abs(t - 4.4) < uenv.step_dt / 2 or k == 30:
            q = torch.rad2deg(robot.data.joint_pos[0])
            mcp = {n.split("_")[0]: round(q[robot.joint_names.index(n)].item(), 1) for n in names if n.endswith("proximal")}
            f = mdp.fingertip_forces(uenv)[0]
            fo = mdp.fingertip_object_forces(uenv)[0]
            tz = uenv.scene["table"].data.root_pos_w[0, 2].item()
            log(f"t={t:4.2f}s  MCP {mcp}  Rotator {q[rot_joint].item():.1f}°  Handgelenk {q[robot.joint_names.index('wrist_left')].item():+.1f}°")
            log(f"          FSR {[round(v, 1) for v in f.tolist()]}  davon Objekt {[round(v, 1) for v in fo.tolist()]}")
            log(f"          Dose Env0 Δ(x,y,z) [mm] {[round(1000 * v, 1) for v in (prev[0] - start[0]).tolist()]}, Tisch z {tz:.3f}")
        if args_cli.real_time:
            time.sleep(max(0.0, uenv.step_dt - (time.time() - t0)))

    log()
    held = dropped_at < 0
    log(f"Dose gehalten bis Episodenende: {int(held.sum())}/{uenv.num_envs}   Return (Mittel): {total_reward.mean().item():.2f}")
    tilt_deg = torch.rad2deg(max_tilt)
    upright = held & (tilt_deg <= 20.0)
    log(f"davon aufrecht (größter Kippwinkel ≤ 20°): {int(upright.sum())}/{uenv.num_envs}   "
        f"Kippwinkel gehaltener Dosen [°]: {sorted(round(v, 1) for v in tilt_deg[held].tolist())}")
    for i in (~held).nonzero().flatten().tolist():
        d = 1000 * (drop_pos[i] - start[i])
        over_edge = drop_pos[i, 0] + cfg.scene.object.spawn.radius > table_edge_x
        log(f"  Env {i:2d}: gefallen bei t={dropped_at[i].item():.2f}s, vorher Δ(x,y,z) = "
            f"({d[0].item():+.0f}, {d[1].item():+.0f}, {d[2].item():+.0f}) mm"
            f"{'  — Dose ragt über die Tischkante' if over_edge else ''}")

REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Bericht: {REPORT}", flush=True)
if not args_cli.headless:
    print("Fenster bleibt offen — zum Beenden schließen.", flush=True)
    while simulation_app.is_running():
        simulation_app.update()
os._exit(0)
