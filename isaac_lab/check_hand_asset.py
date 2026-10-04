"""
check_hand_asset.py — Prüft die Hand-USD in Isaac Lab, bevor darauf trainiert wird.

  1. USD auf der Platte: Mimic Joints eingebrannt? Gelenk-Frames gleich wie im v5-
     Vollroboter (dann gilt dessen verifizierte Vorzeichen-Konvention auch hier)?
  2. Isaac Lab (GPU): Folgen PIP/DIP/IP dem MCP (PhysX Mimic aus der USD)?
     Liefern die Kontaktsensoren an den 5 Fingerspitzen Werte?

Aufruf (ohne aktive Projekt-.venv):
  ~/IsaacLab/isaaclab.sh -p isaac_lab/check_hand_asset.py --headless
Bericht zusätzlich in isaac_sim/tools/_check_hand_asset_lab.txt.
"""
import argparse

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Hand-USD in Isaac Lab prüfen.")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
simulation_app = AppLauncher(args_cli).app

import math  # noqa: E402

import torch  # noqa: E402
from pxr import Usd, UsdPhysics  # noqa: E402

import isaaclab.sim as sim_utils  # noqa: E402
from isaaclab.assets import Articulation  # noqa: E402
from isaaclab.sensors import ContactSensor, ContactSensorCfg  # noqa: E402

from pib_hand_left_v5_cfg import PIB_HAND_LEFT_V5_CFG, REPO_ROOT, SERVO_JOINTS, USD_PATH  # noqa: E402

V5_USD = str(REPO_ROOT / "isaac_sim" / "usd" / "pib_upperbody_v5.usd")
REPORT = REPO_ROOT / "isaac_sim" / "tools" / "_check_hand_asset_lab.txt"
MIMIC_TOL_DEG = 1.0
_lines = []


def log(msg: str = "") -> None:
    print(msg)
    _lines.append(msg)


def _revolute_joints(stage) -> dict:
    return {p.GetPath().name: p for p in stage.Traverse()
            if p.GetTypeName() == "PhysicsRevoluteJoint" or p.HasAPI(UsdPhysics.RevoluteJoint)}


# ── 1. USD auf der Platte ─────────────────────────────────────────────────────
log("── 1. USD auf der Platte ──")
hand = Usd.Stage.Open(USD_PATH)
v5 = Usd.Stage.Open(V5_USD)
hand_joints, v5_joints = _revolute_joints(hand), _revolute_joints(v5)

mimic = [n for n, p in hand_joints.items()
         if any(s.startswith("PhysxMimicJointAPI") for s in p.GetAppliedSchemas())]
log(f"Mimic-Gelenke in der Datei: {len(mimic)} (erwartet 9)")

frame_diff = []
for name, prim in sorted(hand_joints.items()):
    other = v5_joints.get(name)
    if other is None:
        frame_diff.append(f"{name}: fehlt in v5")
        continue
    for attr in ("physics:axis", "physics:localRot1"):
        a, b = prim.GetAttribute(attr).Get(), other.GetAttribute(attr).Get()
        if attr == "physics:axis":
            same = a == b
        else:   # Quaternion: q und -q sind dieselbe Rotation
            dot = abs(sum(x * y for x, y in zip((a.GetReal(), *a.GetImaginary()),
                                                 (b.GetReal(), *b.GetImaginary()))))
            same = dot > 0.9999
        if not same:
            frame_diff.append(f"{name}: {attr} hand={a} v5={b}")
log("Gelenk-Frames (Achse, Kind-Seite) gleich wie v5: "
    + ("ja" if not frame_diff else "NEIN"))
for line in frame_diff:
    log(f"  {line}")

default_prim = hand.GetDefaultPrim().GetPath()
tip_paths = [p.GetPath() for p in hand.Traverse()
             if p.HasAPI(UsdPhysics.RigidBodyAPI) and p.GetName() in
             ("urdf_finger_tip", "urdf_finger_tip_2", "urdf_finger_tip_3", "urdf_finger_tip_4", "urdf_thumb_tip")]
tip_rel = sorted({str(p.MakeRelativePath(default_prim)) for p in tip_paths})
log(f"Fingerspitzen-Links: {tip_rel}")

# ── 2. Isaac Lab ──────────────────────────────────────────────────────────────
log()
log("── 2. Isaac Lab ──")
sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1 / 120, device=args_cli.device))
robot = Articulation(PIB_HAND_LEFT_V5_CFG.replace(prim_path="/World/Hand"))
contact = None
if tip_rel and len({p.count("/") for p in tip_rel}) == 1:
    names = "|".join(p.rsplit("/", 1)[-1] for p in tip_rel)
    parent = tip_rel[0].rsplit("/", 1)[0] if "/" in tip_rel[0] else ""
    expr = f"/World/Hand/{parent + '/' if parent else ''}({names})"
    contact = ContactSensor(ContactSensorCfg(prim_path=expr, update_period=0.0))
sim.reset()

log(f"Gelenke ({robot.num_joints}): {robot.joint_names}")
log(f"Device: {sim.device}")

def jidx(name):
    return robot.joint_names.index(name)

FINGERS = ["index", "middle", "ring", "pinky"]
problems = []


def run_phase(label: str, mcp_deg: float, seconds: float = 1.5) -> None:
    target = torch.zeros_like(robot.data.joint_pos)
    for f in FINGERS:
        target[:, jidx(f"{f}_left_proximal")] = math.radians(mcp_deg)
    target[:, jidx("thumb_left_proximal")] = math.radians(mcp_deg)
    for _ in range(int(seconds * 120)):
        robot.set_joint_position_target(target)
        robot.write_data_to_sim()
        sim.step()
        robot.update(sim.get_physics_dt())
        if contact is not None:
            contact.update(sim.get_physics_dt())

    q = torch.rad2deg(robot.data.joint_pos[0]).tolist()
    log()
    log(f"[{label}] MCP-Soll {mcp_deg:.0f}°   Handgelenk {q[jidx('wrist_left')]:+.1f}°  "
        f"Unterarm {q[jidx('forearm_left')]:+.1f}°")
    log(f"  {'Finger':7s} {'MCP':>7s} {'PIP':>7s} {'DIP':>7s}  Kopplung")
    for f in FINGERS:
        mcp, pip, dip = (q[jidx(f"{f}_left_{s}")] for s in ("proximal", "distal", "tip"))
        d = max(abs(pip - mcp), abs(dip - pip))
        log(f"  {f:7s} {mcp:7.1f} {pip:7.1f} {dip:7.1f}  Δ {d:.2f}°")
        if d > MIMIC_TOL_DEG:
            problems.append(f"{label}/{f}: Kopplung Δ {d:.2f}°")
    mcp, ip = q[jidx("thumb_left_proximal")], q[jidx("thumb_left_tip")]
    log(f"  {'thumb':7s} {mcp:7.1f} {ip:7.1f} {'':7s}  Δ {abs(ip - mcp):.2f}°")
    if abs(ip - mcp) > MIMIC_TOL_DEG:
        problems.append(f"{label}/thumb: Kopplung Δ {abs(ip - mcp):.2f}°")
    if contact is not None:
        forces = contact.data.net_forces_w[0].norm(dim=-1).tolist()
        log("  Kontaktkraft Fingerspitzen [N]: "
            + ", ".join(f"{n}={v:.2f}" for n, v in zip(contact.body_names, forces)))


run_phase("Ruhe", 0.0)
run_phase("halb", 45.0)
run_phase("fast zu", 80.0)
run_phase("zurück", 0.0)

log()
if len(mimic) != 9:
    problems.append(f"{len(mimic)} Mimic-Gelenke in der Datei statt 9 — Bake gespeichert?")
if frame_diff:
    problems.append("Gelenk-Frames weichen von v5 ab — Vorzeichen prüfen")
if contact is None:
    problems.append("Kontaktsensor nicht angelegt (Fingerspitzen-Links nicht gefunden)")
log("PROBLEME:\n  - " + "\n  - ".join(problems) if problems else "OK")

REPORT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
print(f"\nBericht: {REPORT}", flush=True)
# simulation_app.close() blieb headless minutenlang hängen (2026-10-04) — Bericht ist
# geschrieben, Prozess hart beenden.
import os  # noqa: E402
os._exit(0)
