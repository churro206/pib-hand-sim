"""
analyse_reset.py — Was passiert in den ersten 0,1 s nach dem Reset? (Reset-Überlappung, Sprint 2026-10-09)

Basisaufgabe (eval-v1) mit einem Katalogobjekt, Aktionen 0. Ein Kontaktsensor am Objekt mit Filter auf jeden
Handkörper und den Tisch zeigt je Umgebung, welcher Körper das Objekt im ersten Physikschritt bzw. in den ersten
0,1 s berührt und mit welcher Kraft — eine Überlappung beim Reset (Hand wird teleportiert) erscheint als große
Kontaktkraft schon im ersten Schritt. Dazu: Verschiebung/Drehung des Objekts, Drift der Hand (Servo-Gelenke,
Fingerspitzen) und die Startwinkel. Bericht: isaac_sim/tools/_analyse_reset_<objekt>[_offen].txt

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/analyse_reset.py --headless --objekt zylinder_d6 --num_envs 64
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
parser.add_argument("--objekt", required=True, help="Objekt aus env_cfg.OBJECTS oder multi (Trainingsszene HeavyMulti)")
parser.add_argument("--greifart", choices=["seitlich", "oben"], default="seitlich",
                    help="oben: Objekte aus env_cfg_oben.OBJECTS_OBEN, multi = Trainingsszene ObenMulti")
parser.add_argument("--num_envs", type=int, default=64)
parser.add_argument("--dauer", type=float, default=0.1, help="Beobachtungsdauer [s] (≤ 2 s: vor dem Absenken)")
parser.add_argument("--offen", action="store_true", help="Reset mit ganz geöffneter Hand (Gegenprobe)")
parser.add_argument("--startpose", choices=["standard", "eval_v1"], default="standard",
                    help="standard = Reset der Basisaufgabe; eval_v1 = Reset bis eval-v1 zum Vergleich (Finger 0–15°, "
                         "Handgelenk −10–0°, Startlage aus der Nenngröße)")
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # isaac_lab/
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import PibGraspEnvCfg, PibGraspEnvCfg_HeavyMulti, apply_object  # noqa: E402
from isaaclab.sensors import ContactSensorCfg  # noqa: E402

BODIES = ["urdf_elbow_lower", "urdf_forearm_left", "urdf_palm_left", "urdf_thumb_rotator_left", "urdf_thumb_proximal",
          "urdf_thumb_tip"] + [f"urdf_finger_{seg}{sfx}" for sfx in ("", "_2", "_3", "_4")
                               for seg in ("proximal", "distal", "tip")]
LABEL = {"urdf_elbow_lower": "Ellbogen", "urdf_forearm_left": "Unterarm", "urdf_palm_left": "Handfläche",
         "urdf_thumb_rotator_left": "Daumen-Rot.", "urdf_thumb_proximal": "Daumen-Grund", "urdf_thumb_tip": "Daumen-Spitze"}
for sfx, f in (("", "Zeige"), ("_2", "Mittel"), ("_3", "Ring"), ("_4", "Klein")):
    for seg, s in (("proximal", "Grund"), ("distal", "Mittel"), ("tip", "Spitze")):
        LABEL[f"urdf_finger_{seg}{sfx}"] = f"{f}-{s}"
FILTERS = BODIES + ["Tisch"]

if args.greifart == "oben":
    from pib_grasp.env_cfg_oben import PibGraspEnvCfg_Oben, PibGraspEnvCfg_ObenMulti, apply_object_oben
    TASK = "Pib-Grasp-Hand-Left-ObenMulti-v0" if args.objekt == "multi" else "Pib-Grasp-Hand-Left-Oben-v0"
    cfg = PibGraspEnvCfg_ObenMulti() if args.objekt == "multi" else apply_object_oben(PibGraspEnvCfg_Oben(), args.objekt)
else:
    TASK = "Pib-Grasp-Hand-Left-HeavyMulti-v0" if args.objekt == "multi" else "Pib-Grasp-Hand-Left-v0"
    cfg = PibGraspEnvCfg_HeavyMulti() if args.objekt == "multi" else apply_object(PibGraspEnvCfg(), args.objekt)
cfg.scene.num_envs = args.num_envs
cfg.seed = 1000
stem = (f"_analyse_reset_{'oben_' if args.greifart == 'oben' else ''}{args.objekt}"
        + (f"_{args.dauer:g}s" if args.dauer != 0.1 else ""))
if args.startpose == "eval_v1":
    r = cfg.events.reset_hand.params["ranges_deg"]
    r.update({j: (0.0, 15.0) for j in ("index_left_proximal", "middle_left_proximal", "ring_left_proximal",
                                       "pinky_left_proximal")}, wrist_left=(-10.0, 0.0))
    if cfg.events.place_objects.params["lift"] == 0.0:       # YCB behält die Platzierung (feste Größe, Abstand)
        cfg.events.place_objects = None
    stem += "_eval_v1"
ranges = cfg.events.reset_hand.params["ranges_deg"]
if args.offen:
    cfg.events.reset_hand.params["ranges_deg"] = {k: (0.0, 0.0) for k in ranges}
    stem += "_offen"
cfg.scene.object.spawn.activate_contact_sensors = True
cfg.scene.object_contact = ContactSensorCfg(
    prim_path="{ENV_REGEX_NS}/Object",
    filter_prim_paths_expr=[f"{{ENV_REGEX_NS}}/Robot/{b}" for b in BODIES] + ["{ENV_REGEX_NS}/Table"],
    history_length=cfg.decimation)          # alle Physik-Unterschritte eines Policy-Schritts, nicht nur den letzten
env = gym.make(TASK, cfg=cfg)
u = env.unwrapped
obj, robot, sensor = u.scene["object"], u.scene["robot"], u.scene["object_contact"]
org = u.scene.env_origins
SERVO = ["forearm_left", "wrist_left", "thumb_left_rotator", "thumb_left_proximal", "index_left_proximal",
         "middle_left_proximal", "ring_left_proximal", "pinky_left_proximal"]
sidx = [robot.joint_names.index(j) for j in SERVO]
tips = [robot.body_names.index(b) for b in ("urdf_thumb_tip", "urdf_finger_tip", "urdf_finger_tip_2",
                                            "urdf_finger_tip_3", "urdf_finger_tip_4")]

import re  # noqa: E402
import isaaclab.sim as sim_utils  # noqa: E402
scale = torch.ones(u.num_envs)                               # zufällige Objektgröße (object_scale, prestartup)
for path in sim_utils.find_matching_prim_paths(obj.cfg.prim_path):
    a = u.scene.stage.GetPrimAtPath(path).GetAttribute("xformOp:scale")
    if a and a.Get() is not None:
        scale[int(re.search(r"env_(\d+)", path).group(1))] = float(a.Get()[2])

u.reset(seed=1000)
p0 = (obj.data.root_pos_w - org).clone()
q0 = obj.data.root_quat_w.clone()
w, x, y, z = q0.unbind(-1)
yaw0 = torch.rad2deg(torch.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
j0 = robot.data.joint_pos[:, sidx].clone()
t0 = robot.data.body_pos_w[:, tips].clone()
steps = round(args.dauer / u.step_dt)
first = None
peak = torch.zeros(u.num_envs, len(FILTERS), device=u.device)
act = torch.zeros(u.num_envs, u.action_manager.total_action_dim, device=u.device)
with torch.inference_mode():
    for k in range(steps):
        u.step(act)
        f = sensor.data.force_matrix_w_history[:, :, 0].norm(dim=-1).amax(dim=1)   # (N, Filter), max über Unterschritte
        if k == 0:
            first = f.clone()
        peak = torch.maximum(peak, f)
dpos = 1000 * ((obj.data.root_pos_w - org) - p0)
drot = torch.rad2deg(2 * torch.acos((obj.data.root_quat_w * q0).sum(-1).abs().clamp(max=1.0)))
djoint = torch.rad2deg((robot.data.joint_pos[:, sidx] - j0).abs())
dtip = 1000 * (robot.data.body_pos_w[:, tips] - t0).norm(dim=-1)
start = torch.rad2deg(j0)

TH = 0.5                                                     # N — Kontakt
hand = slice(0, len(BODIES))
touch0 = first[:, hand] > TH
touch = peak[:, hand] > TH
lines = [f"== {args.objekt} | Reset {args.startpose}{' (Hand offen)' if args.offen else ''} | {u.num_envs} Umgebungen, Seed 1000, "
         f"Aktionen 0, {steps} Schritte ({args.dauer:g} s)", ""]
n = u.num_envs
lines += [f"Hand berührt das Objekt im 1. Schritt: {int(touch0.any(1).sum())}/{n}, in 0,1 s: {int(touch.any(1).sum())}/{n}",
          f"(„in 0,1 s“ = im Beobachtungszeitraum {args.dauer:g} s)",
          f"Objekt verschoben > 5 mm: {int((dpos.norm(dim=-1) > 5).sum())}/{n}, > 10 mm: {int((dpos.norm(dim=-1) > 10).sum())}/{n}; "
          f"gedreht > 5°: {int((drot > 5).sum())}/{n}",
          f"  ohne Handkontakt in 0,1 s: verschoben > 5 mm {int(((dpos.norm(dim=-1) > 5) & ~touch.any(1)).sum())}"
          f"/{int((~touch.any(1)).sum())}, Δ Mittel x/y/z [mm] "
          + "/".join(f"{v:.1f}" for v in (dpos[~touch.any(1)].mean(0).tolist() if (~touch.any(1)).any() else [0, 0, 0])),
          f"  mit Handkontakt: verschoben > 5 mm {int(((dpos.norm(dim=-1) > 5) & touch.any(1)).sum())}/{int(touch.any(1).sum())}",
          f"Tischkontakt 1. Schritt: Kraft Median {first[:, -1].median().item():.1f} N, max {first[:, -1].max().item():.1f} N "
          f"(Gewicht {9.81 * obj.root_physx_view.get_masses().reshape(n, -1).sum(1).mean().item():.1f} N)",
          f"Objektgröße s {scale.min().item():.3f}–{scale.max().item():.3f}; Δz gegen (s − 1)·h/2 (Start zu hoch/tief): "
          f"Korrelation {torch.corrcoef(torch.stack([dpos[:, 2].cpu(), scale - 1]))[0, 1].item():.2f}",
          f"Hand-Drift in 0,1 s: Servo-Gelenk max {djoint.max().item():.2f}° (Umgebung {int(djoint.max(1).values.argmax())}, "
          f"{SERVO[int(djoint.max(0).values.argmax())]}; Median der Maxima {djoint.max(1).values.median().item():.2f}°), "
          f"Fingerspitze max {dtip.max().item():.1f} mm", "",
          "Handkörper mit Kontakt (Anteil Umgebungen 1. Schritt / 0,1 s, Spitzenkraft):"]
for b in range(len(BODIES)):
    if touch[:, b].any():
        lines.append(f"  {LABEL[BODIES[b]]:14s} {int(touch0[:, b].sum()):3d} / {int(touch[:, b].sum()):3d}   "
                     f"max {peak[:, b].max().item():7.1f} N")
lines += ["", "Startwinkel [°] mit/ohne Handkontakt (Mittel), je Servo:"]
for i, j in enumerate(SERVO):
    a = start[touch.any(1), i].mean().item() if touch.any(1).any() else float("nan")
    b = start[~touch.any(1), i].mean().item() if (~touch.any(1)).any() else float("nan")
    lines.append(f"  {j:22s} {a:6.1f} / {b:6.1f}   Bereich {ranges.get(j, (0, 0)) if not args.offen else (0, 0)}")
lines += ["", f"{'Env':>4} {'s':>6s} {'Gier':>5s} {'Δ x/y/z [mm]':22s} {'Dreh [°]':>8s} {'Kontakt (Spitzenkraft N)':55s} Start Daumen-Rot/-MCP, Z/M/R/K-MCP, Handgel."]
for i in range(n):
    c = ", ".join(f"{LABEL[BODIES[b]]} {peak[i, b].item():.0f}" for b in range(len(BODIES)) if touch[i, b])
    c += f" [Hand max {peak[i, hand].max().item():.2f} N]"
    lines.append(f"{i:4d} {scale[i].item():6.3f} {yaw0[i].item():5.0f} {'/'.join(f'{v:.1f}' for v in dpos[i].tolist()):22s} {drot[i].item():8.1f} {c:55s} "
                 + " / ".join(f"{start[i, k].item():.0f}" for k in (2, 3, 4, 5, 6, 7, 1)))
out = Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / f"{stem}.txt"
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:30]), flush=True)
print(f"Bericht: {out}")
os._exit(0)
