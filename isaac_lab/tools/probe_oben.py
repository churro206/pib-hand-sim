"""
probe_oben.py — Geometrie der Hand in der Pose „von oben“ (Handfläche unten, Unterarm waagrecht; Plan: docs/plan-griff-
von-oben.md, Schritt 1). Ohne Schwerkraft, ohne Objekt: Hand-Root wie in env_cfg_oben (Drehung keine, Höhe HAND_POS),
alle vier Finger-MCPs gemeinsam 0–90°, Daumen bei Rotator 0/45/90° und Daumen-MCP 0–90°. Je Stellung die Lage der
Fingerspitzen-Links (Gelenkrahmen, nicht die Oberfläche) relativ zum Hand-Root: tiefster Punkt (z) und wo er liegt
(x quer, y längs) — daraus Vorgreifabstand und Objektlage für den Machbarkeitstest. Bericht: isaac_sim/tools/_probe_oben.txt

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/probe_oben.py --headless
"""
import argparse
import math
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
app = AppLauncher(a).app

import torch  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import Articulation  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG  # noqa: E402
from pib_grasp.mdp import FINGERTIP_LINKS  # noqa: E402

HAND_POS, HAND_ROT = (0.0, 0.0, 0.5), (1.0, 0.0, 0.0, 0.0)       # wie env_cfg_oben (HAND_POS, HAND_ROT_OBEN)
LINKS = ["urdf_palm_left", "urdf_thumb_rotator_left", "urdf_thumb_proximal"] + FINGERTIP_LINKS
NAMES = ["Handfläche", "D-Rotator", "D-Grund", "D-Spitze", "Zeige", "Mittel", "Ring", "Klein"]

sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1 / 120, device=a.device, gravity=(0.0, 0.0, 0.0)))
r = Articulation(PIB_HAND_LEFT_V5_CFG.replace(prim_path="/World/Hand",
                                               init_state=PIB_HAND_LEFT_V5_CFG.init_state.replace(pos=HAND_POS, rot=HAND_ROT)))
sim.reset()
ids = [r.body_names.index(n) for n in LINKS]


def settle(finger_deg: float, thumb_deg: float, rot_deg: float) -> torch.Tensor:
    t = torch.zeros_like(r.data.joint_pos)
    for f in ("index", "middle", "ring", "pinky"):
        t[:, r.joint_names.index(f"{f}_left_proximal")] = math.radians(finger_deg)
    t[:, r.joint_names.index("thumb_left_proximal")] = math.radians(thumb_deg)
    t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(rot_deg)
    for _ in range(240):                                  # 2 s: Servos (270 °/s) erreichen jede Stellung
        r.set_joint_position_target(t)
        r.write_data_to_sim()
        sim.step()
        r.update(sim.get_physics_dt())
    return r.data.body_link_pos_w[0, ids] - torch.tensor(HAND_POS, device=r.device)


def row(label: str, pos: torch.Tensor) -> str:
    return f"{label:18s} " + "  ".join(f"{n}({1000 * v[0]:+5.0f} {1000 * v[1]:+5.0f} {1000 * v[2]:+5.0f})"
                                       for n, v in zip(NAMES, pos.tolist()))


lines = ["Lage relativ zum Hand-Root [mm] (x quer: −Daumen/+kleiner Finger, y längs: − Richtung Fingerspitzen, "
         "z: − nach unten); Handfläche nach unten, keine Schwerkraft", "", "== Finger (Daumen offen, Rotator 0°)"]
for deg in range(0, 91, 10):
    pos = settle(deg, 0.0, 0.0)
    tips = pos[4:]
    k = int(tips[:, 2].argmin())
    lines.append(row(f"MCP {deg:2d}°", pos) + f"   tiefste Fingerspitze {NAMES[4 + k]} z = {1000 * tips[k, 2]:+.0f}")
for rot in (0.0, 45.0, 90.0):
    lines += ["", f"== Daumen (Rotator {rot:.0f}°, Finger offen)"]
    for deg in range(0, 91, 15):
        lines.append(row(f"D-MCP {deg:2d}°", settle(0.0, deg, rot)))
text = "\n".join(lines)
print(text, flush=True)
(Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / "_probe_oben.txt").write_text(text + "\n", encoding="utf-8")
os._exit(0)
