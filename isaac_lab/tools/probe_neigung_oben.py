"""
probe_neigung_oben.py — Neigung der Hand für „von oben“, bei der alle fünf Fingerspitzen gleich hoch über dem Tisch stehen
(Leon, 2026-10-10: statt waagrechter Hand; Plan docs/plan-griff-von-oben.md).

Hand ohne Schwerkraft, Daumen-Rotator 90°, alle übrigen Gelenke 0 (offen). Je Fingerspitze die Punkte ihrer Meshes (Kollision
und Optik, aus der USD im Link-Rahmen, mit der simulierten Lage des Links) relativ zum Hand-Root. Gesucht: Drehung um x (Kippen
der Finger nach unten/oben) und um y (Rollen um die Fingerachse), bei der die tiefsten Punkte der fünf Spitzen am wenigsten
streuen (Raster 0,5°). Dazu: Lage der Spitzen in der Tischebene (Objektmitte) und wie viel Platz zwischen Spitzenebene und
Hand bleibt (tiefster Handpunkt außer den Spitzen über einer Kreisfläche um die Mitte) — das begrenzt die Objektgröße.
Bericht: isaac_sim/tools/_probe_neigung_oben.txt

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/probe_neigung_oben.py --headless
"""
import argparse
import math
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

p = argparse.ArgumentParser()
p.add_argument("--rotator", type=float, default=90.0, help="Daumen-Rotator [°]")
p.add_argument("--dump", type=str, default=None,
               help="nur Geometrie speichern: Mesh-Punkte der fünf Fingerspitzen (Hand-Root-Frame, ungedreht) je "
                    "Rotator 60/75/90° als .npz (für tools/suche_startpose_oben.py), dann Ende")
AppLauncher.add_app_launcher_args(p)
a = p.parse_args()
app = AppLauncher(a).app

import numpy as np  # noqa: E402
import torch  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import Articulation  # noqa: E402
from isaaclab.utils.math import quat_apply  # noqa: E402
from pxr import Usd, UsdGeom  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG  # noqa: E402
from pib_grasp.mdp import FINGERTIP_LINKS  # noqa: E402

NAMES = ["Daumen", "Zeige", "Mittel", "Ring", "Klein"]
sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1 / 120, device=a.device, gravity=(0.0, 0.0, 0.0)))
r = Articulation(PIB_HAND_LEFT_V5_CFG.replace(prim_path="/World/Hand", init_state=PIB_HAND_LEFT_V5_CFG.init_state.replace(
    pos=(0.0, 0.0, 0.0), rot=(1.0, 0.0, 0.0, 0.0))))
sim.reset()
t = torch.zeros_like(r.data.joint_pos)
t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(a.rotator)
for _ in range(360):
    r.set_joint_position_target(t)
    r.write_data_to_sim()
    sim.step()
    r.update(sim.get_physics_dt())

stage = sim_utils.get_current_stage()
time = Usd.TimeCode.Default()


def link_points(body: str) -> np.ndarray:
    """Alle Mesh-Punkte unter dem Link-Prim, im Rahmen des Hand-Root mit der simulierten Lage des Links."""
    link = stage.GetPrimAtPath(f"/World/Hand/{body}")
    inv = UsdGeom.Xformable(link).ComputeLocalToWorldTransform(time).GetInverse()
    pts = []
    for prim in Usd.PrimRange(link, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        rel = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time) * inv        # Mesh → Link (statisch)
        for q in UsdGeom.Mesh(prim).GetPointsAttr().Get(time) or []:
            v = rel.Transform(q)
            pts.append((v[0], v[1], v[2]))
    if not pts:
        return np.zeros((0, 3))
    i = r.body_names.index(body)
    P = torch.tensor(pts, dtype=torch.float32, device=r.device)
    q = r.data.body_link_quat_w[0, i].expand(len(P), 4)
    w = quat_apply(q, P) + r.data.body_link_pos_w[0, i] - r.data.root_pos_w[0]
    return w.cpu().numpy()


if a.dump:
    data = {}
    for rot_deg in (60, 75, 90):
        t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(rot_deg)
        for _ in range(240):
            r.set_joint_position_target(t)
            r.write_data_to_sim()
            sim.step()
            r.update(sim.get_physics_dt())
        for i, b in enumerate(FINGERTIP_LINKS):
            data[f"r{rot_deg}_tip{i}"] = link_points(b)
    np.savez(a.dump, **data)
    print(f"Geometrie gespeichert: {a.dump}", flush=True)
    os._exit(0)

tips = [link_points(b) for b in FINGERTIP_LINKS]
others = np.concatenate([link_points(b) for b in r.body_names if b not in FINGERTIP_LINKS and "elbow" not in b])
palm = link_points("urdf_palm_left")


def rot(ax_deg: float, ay_deg: float) -> np.ndarray:
    ax, ay = math.radians(ax_deg), math.radians(ay_deg)
    Rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    return Ry @ Rx


best = None
for ax in np.arange(-70, 70.01, 0.5):
    for ay in np.arange(-45, 45.01, 0.5):
        R = rot(ax, ay)
        low = [float((P @ R.T)[:, 2].min()) for P in tips]
        spread = max(low) - min(low)
        if best is None or spread < best[0]:
            best = (spread, ax, ay)
spread, ax, ay = best
R = rot(ax, ay)
lines = [f"== Daumen-Rotator {a.rotator:.0f}°, übrige Gelenke 0, Hand-Root im Ursprung (mm, Hand-Root-Frame nach der Drehung)",
         "", "Ohne Drehung (waagrecht), tiefster Punkt je Spitze z: "
         + "  ".join(f"{n} {1000 * P[:, 2].min():+.0f}" for n, P in zip(NAMES, tips)), ""]
lines.append(f"Beste Drehung: um x {ax:+.1f}° (Finger kippen), um y {ay:+.1f}° (Rollen)  →  Streuung der Spitzen {1000 * spread:.1f} mm")
quat_x = (math.cos(math.radians(ax) / 2), math.sin(math.radians(ax) / 2), 0.0, 0.0)
lines.append(f"  (Quaternion nur um x, w x y z: {tuple(round(v, 5) for v in quat_x)}; Gesamt R = Ry·Rx)")
low_pts = []
for n, P in zip(NAMES, tips):
    Q = P @ R.T
    k = int(Q[:, 2].argmin())
    low_pts.append(Q[k])
    lines.append(f"  {n:7s} tiefster Punkt x {1000 * Q[k, 0]:+5.0f}  y {1000 * Q[k, 1]:+5.0f}  z {1000 * Q[k, 2]:+5.0f}")
low_pts = np.array(low_pts)
plane = float(low_pts[:, 2].mean())
cxy = low_pts[:, :2].mean(0)
lines.append(f"Spitzenebene z {1000 * plane:+.0f} mm; Mitte der Spitzen (Objektmitte) x {1000 * cxy[0]:+.0f}  y {1000 * cxy[1]:+.0f}")
lines.append(f"Abstand Daumenspitze ↔ Mittelfingerspitze in der Ebene {1000 * np.linalg.norm(low_pts[0, :2] - low_pts[2, :2]):.0f} mm")
# Greifmitte: zwischen Daumenspitze und der Mitte der vier Fingerspitzen (dort steht das Objekt)
gxy = (low_pts[0, :2] + low_pts[1:, :2].mean(0)) / 2
lines.append(f"Greifmitte (zwischen Daumen und Fingern) x {1000 * gxy[0]:+.0f}  y {1000 * gxy[1]:+.0f}")
O = others @ R.T
Pm = palm @ R.T
for rad in (0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065):
    m = np.linalg.norm(O[:, :2] - gxy, axis=1) <= max(rad, 0.003)
    h = (O[m, 2].min() - plane) if m.any() else float("nan")
    lines.append(f"  Platz über der Spitzenebene, Kreis r = {1000 * rad:2.0f} mm um die Greifmitte: {1000 * h:4.0f} mm "
                 "(tiefster Handpunkt außer den Spitzen)")
lines.append(f"Handfläche tiefster Punkt {1000 * (Pm[:, 2].min() - plane):+.0f} mm über der Spitzenebene")
# Daumen beim Eindrehen: tiefster Punkt der Daumenspitze bei Rotator 0/30/60/90 (übrige Gelenke 0) relativ zur Spitzenebene
sweep = []
for rot_deg in (0.0, 30.0, 60.0, 90.0):
    t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(rot_deg)
    for _ in range(240):
        r.set_joint_position_target(t)
        r.write_data_to_sim()
        sim.step()
        r.update(sim.get_physics_dt())
    sweep.append(f"{rot_deg:.0f}° {1000 * ((link_points(FINGERTIP_LINKS[0]) @ R.T)[:, 2].min() - plane):+.0f}")
lines.append("Daumenspitze beim Eindrehen, tiefster Punkt ggü. Spitzenebene [mm]: " + "  ".join(sweep))
# Finger beim Schließen (Daumen auf Rotator 90°): tiefster Punkt aller Fingerglieder ggü. der Spitzenebene je MCP-Winkel
t[:, r.joint_names.index("thumb_left_rotator")] = math.radians(a.rotator)
curl = []
for deg in range(0, 91, 10):
    for f in ("index", "middle", "ring", "pinky"):
        t[:, r.joint_names.index(f"{f}_left_proximal")] = math.radians(deg)
    for _ in range(240):
        r.set_joint_position_target(t)
        r.write_data_to_sim()
        sim.step()
        r.update(sim.get_physics_dt())
    low = min(float((link_points(b) @ R.T)[:, 2].min()) for b in r.body_names if b.startswith("urdf_finger_"))
    curl.append(f"{deg}° {1000 * (low - plane):+.0f}")
lines.append("Finger beim Schließen (MCP, Kopplung 1:1), tiefster Fingerpunkt ggü. Spitzenebene [mm]: " + "  ".join(curl))
text = "\n".join(lines)
print(text, flush=True)
(Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / "_probe_neigung_oben.txt").write_text(text + "\n", encoding="utf-8")
os._exit(0)
