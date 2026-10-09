"""
eval_policy.py — Policy nach dem Bewertungsprotokoll eval-v2 bewerten (experiments/README.md, ADR-021).

eval-v2 (seit 2026-10-09) = eval-v1 mit Reset ohne Überlappung und Fall (Startpose fast offen, Platzierung nach
tatsächlicher Größe und Gierdrehung, YCB in Ruhelage — env_cfg/mdp); eval-v1-Dateien bleiben als Historie.

Exportierter Actor (TorchScript, deterministisch) in der Greifaufgabe; nur die Abbrüche
„Dose gefallen“ und „Physik instabil“ sind aktiv, der Kippwinkel wird gemessen. Je Episode:
Ende, größter Kippwinkel, Unterarmdrehung, Griffkraft/Kraft > 15 N in der Haltephase,
Stall-Anteil, Absinken, Unruhe. Ausgabe: <protokoll>.txt + <protokoll>.json (Metriken, Erfolg je
Episode für den Bootstrap in experiments.py) — je Protokollversion eine Datei, nichts wird
bei einer neuen Version überschrieben. Andere Bedingung (Objekt aus env_cfg.OBJECTS):
--objekt quader_7x7x20 --bedingung quader_seitlich → <protokoll>_<bedingung>.json/.txt
(Standardbedingung zylinder_seitlich bleibt <protokoll>.json).

  ~/IsaacLab/isaaclab.sh -p isaac_lab/eval_policy.py --policy <run>/exported/policy.pt --num_envs 16 --real_time
  ~/IsaacLab/isaaclab.sh -p isaac_lab/eval_policy.py --checkpoint <run>/model_299.pt --headless
Mit --checkpoint: lädt wie Isaac Labs play.py und exportiert nach <run>/exported/ (JIT + ONNX).
Mit --video N: zeichnet die ersten N Schritte auf (<out>/videos/), braucht Kameras.
Mit --verlauf: zusätzlich Verlauf über die Episode (je Zeitschritt, Mittel über laufende Episoden:
Objekthöhe ggü. Start, Kippwinkel, Finger am Objekt, Griffkraft, Anteil laufender Episoden) →
verlauf-v1[_<bedingung>].json. --nur-medien: keine Bewertungsdateien schreiben (Video/Verlauf allein,
überschreibt keine vorhandene Bewertung).
"""
import argparse
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

PROTOCOL = "eval-v2"                                        # experiments.PROTOKOLL

parser = argparse.ArgumentParser()
src = parser.add_mutually_exclusive_group(required=True)
src.add_argument("--policy", type=str, help="exported/policy.pt (TorchScript)")
src.add_argument("--checkpoint", type=str, help="model_<n>.pt eines Trainingslaufs (wird exportiert)")
src.add_argument("--regel", type=str, choices=["alle_schliessen", "bis_kontakt"],
                 help="regelbasierter Griff statt Policy (Baseline, EXP-014/015)")
parser.add_argument("--regel-param", dest="regel_param", type=str, default="",
                    help="Parameter der Regel, z. B. schliessen=0.4,nachdruck_deg=5,rotator_deg=90")
parser.add_argument("--num_envs", type=int, default=256)
parser.add_argument("--episodes", type=int, default=1000, help="Zahl der gewerteten Episoden")
parser.add_argument("--seed", type=int, default=1000, help="Bewertungs-Seed (≠ Trainings-Seeds)")
parser.add_argument("--max_kipp_deg", type=float, default=20.0, help="Anforderung; < 0 = keine")
parser.add_argument("--objekt", type=str, default="zylinder_d6", help="Objekt aus env_cfg.OBJECTS")
parser.add_argument("--bedingung", type=str, default="zylinder_seitlich", help="Name der Bedingung (Dateiname)")
parser.add_argument("--out", type=str, default=None, help="Ausgabeordner (<protokoll>.json/.txt); "
                    "Standard: Laufordner bzw. isaac_sim/tools/")
parser.add_argument("--video", type=int, default=0, help="Schritte Video am Anfang (0 = aus)")
parser.add_argument("--real_time", action="store_true", help="Auf Echtzeit bremsen (zum Zuschauen)")
parser.add_argument("--verlauf", action="store_true", help="Verlauf über die Episode messen")
parser.add_argument("--nur-medien", dest="nur_medien", action="store_true",
                    help="keine eval-Dateien schreiben (nur Video/Verlauf)")
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()
if args_cli.video:
    args_cli.enable_cameras = True
simulation_app = AppLauncher(args_cli).app

import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402

import gymnasium as gym  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pib_grasp  # noqa: E402,F401
from pib_grasp import mdp  # noqa: E402
from pib_grasp.env_cfg import DROP_DEPTH, DROP_SPEED, GRASP_TIME_S, PibGraspEnvCfg, apply_object  # noqa: E402
from pib_hand_left_v5_cfg import SERVO_JOINTS, WRIST_JOINT  # noqa: E402

HOLD_START_S = GRASP_TIME_S + DROP_DEPTH / DROP_SPEED     # Tisch unten → Haltephase
EARLY_S = 0.1                                              # Startfehler (Reset-Überlappung)
FORCE_LIMIT_N = 15.0
STALL_FRACTION = 0.9
REQ_DEG = args_cli.max_kipp_deg if args_cli.max_kipp_deg >= 0 else None

# ── Umgebung: wie im Training, nur Abbrüche „gefallen“ und „instabil“ ─────────────────────
cfg = apply_object(PibGraspEnvCfg(), args_cli.objekt)
cfg.scene.num_envs = args_cli.num_envs
cfg.seed = args_cli.seed
if getattr(cfg.terminations, "object_tilted", None) is not None:   # trainingsspezifisch (EXP-001/002)
    cfg.terminations.object_tilted = None
    cfg.rewards.early_termination = None      # verweist auf object_tilted; Belohnung hier unbenutzt
torch.manual_seed(args_cli.seed)
env = gym.make("Pib-Grasp-Hand-Left-v0", cfg=cfg, render_mode="rgb_array" if args_cli.video else None)
uenv = env.unwrapped

if args_cli.checkpoint:
    # wie ~/IsaacLab/scripts/reinforcement_learning/rsl_rl/play.py: laden, Actor exportieren
    from isaaclab_rl.rsl_rl import RslRlVecEnvWrapper, export_policy_as_jit, export_policy_as_onnx
    from rsl_rl.runners import OnPolicyRunner
    from pib_grasp.agents.rsl_rl_ppo_cfg import PibGraspPPORunnerCfg
    agent_cfg = PibGraspPPORunnerCfg()
    runner = OnPolicyRunner(RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions), agent_cfg.to_dict(),
                            log_dir=None, device=uenv.device)
    runner.load(args_cli.checkpoint)
    export_dir = os.path.join(os.path.dirname(args_cli.checkpoint), "exported")
    normalizer = getattr(runner.alg.policy, "actor_obs_normalizer", None)
    export_policy_as_jit(runner.alg.policy, normalizer=normalizer, path=export_dir, filename="policy.pt")
    export_policy_as_onnx(runner.alg.policy, normalizer=normalizer, path=export_dir, filename="policy.onnx")
    args_cli.policy = os.path.join(export_dir, "policy.pt")

if args_cli.regel:
    args_cli.policy = f"regel:{args_cli.regel}:{args_cli.regel_param}"
out_dir = Path(args_cli.out) if args_cli.out else (
    Path(args_cli.policy).resolve().parent.parent if "exported" in args_cli.policy
    else Path(__file__).resolve().parent.parent / "isaac_sim" / "tools")
out_dir.mkdir(parents=True, exist_ok=True)
STEM = PROTOCOL if args_cli.bedingung == "zylinder_seitlich" else f"{PROTOCOL}_{args_cli.bedingung}"
if args_cli.video:
    env = gym.wrappers.RecordVideo(env, video_folder=str(out_dir / ("videos" if STEM == PROTOCOL else f"videos_{args_cli.bedingung}")), step_trigger=lambda s: s == 0,
                                   video_length=args_cli.video, disable_logger=True)
class RuleGrasp(torch.nn.Module):
    """Regelbasierter Griff im selben Aktionsraum wie die Policy (relative Servo-Ziele, Skala wie ActionsCfg) und
    nur mit denselben Sensoren (Gelenkwinkel, FSR). Bis rot_s: Daumen-Rotator auf rotator_deg, sonst halten.
    Danach schließen Daumen und Finger mit 'schliessen' (Anteil des maximalen Schritts je 1/60 s).
    alle_schliessen: weiter schließen bis zum Anschlag (Heuristik wie Chen et al. 2022).
    bis_kontakt: je Finger ab FSR > kontakt_n nur noch um nachdruck_deg nachdrücken (Hsiao et al. 2010).
    Handgelenk und Unterarm halten ihre Startstellung."""

    def __init__(self, env, name: str, params: str):
        super().__init__()
        p = {"schliessen": 0.4, "rotator_deg": 90.0, "rot_s": 0.4, "nachdruck_deg": 5.0, "kontakt_n": 1.0}
        for kv in filter(None, params.split(",")):
            k, v = kv.split("=")
            p[k.strip()] = float(v)
        self.p, self.name, self.env = p, name, env
        self.robot = env.scene["robot"]
        self.ids = [self.robot.joint_names.index(n) for n in SERVO_JOINTS]
        term = env.action_manager.get_term("servos")
        s = term._scale                                      # (Umgebungen × Aktionen) oder Skalar
        self.scale = s[0].clone() if torch.is_tensor(s) else torch.full((len(self.ids),), float(s), device=env.device)
        self.hold = None
        self.contact = torch.zeros(env.num_envs, 5, dtype=torch.bool, device=env.device)

    def forward(self, obs):
        import math
        env, p = self.env, self.p
        q = self.robot.data.joint_pos[:, self.ids]
        t = mdp.episode_time(env)
        new = t <= env.step_dt + 1e-6
        if self.hold is None:
            self.hold = q.clone()
        self.hold[new] = q[new]
        self.contact[new] = False
        a = torch.zeros_like(q)
        a[:, :2] = ((self.hold[:, :2] - q[:, :2]) / self.scale[:2]).clamp(-1, 1)             # Unterarm, Handgelenk
        a[:, 2] = ((math.radians(p["rotator_deg"]) - q[:, 2]) / self.scale[2]).clamp(-1, 1)  # Daumen-Rotator
        closing = (t >= p["rot_s"]).float()[:, None]
        a[:, 3:] = p["schliessen"] * closing                                                 # Daumen + 4 Finger
        if self.name == "bis_kontakt":
            self.contact |= mdp.fingertip_forces(env) > p["kontakt_n"]                       # FSR: Daumen … klein
            squeeze = (math.radians(p["nachdruck_deg"]) / self.scale[3:]).clamp(-1, 1)
            a[:, 3:] = torch.where(self.contact, squeeze.expand_as(a[:, 3:]) * closing, a[:, 3:])
        return a


if args_cli.regel:
    policy = RuleGrasp(uenv, args_cli.regel, args_cli.regel_param)
else:
    policy = torch.jit.load(args_cli.policy, map_location=uenv.device).eval()
obs, _ = env.reset(seed=args_cli.seed)

robot = uenv.scene["robot"]
obj = uenv.scene["object"]
forearm = robot.joint_names.index("forearm_left")
stall_ids = [robot.joint_names.index(n) for n in SERVO_JOINTS if n != WRIST_JOINT]
stall_limit = robot.data.joint_effort_limits[:, stall_ids]
term_names = uenv.termination_manager.active_terms
dt = uenv.step_dt
early_steps = round(EARLY_S / dt)
N = uenv.num_envs
dev = uenv.device


def zeros():
    return torch.zeros(N, device=dev)


# laufende Größen je Umgebung (aktuelle Episode)
steps, max_tilt, early_tilt, max_forearm = zeros(), zeros(), zeros(), zeros()
hold_steps, hold_force, hold_over, stall, act_rate, sink = zeros(), zeros(), zeros(), zeros(), zeros(), zeros()
hold_touch = torch.zeros(N, 5, device=dev)       # Fingernutzung: Schritte mit Objektkontakt > 1 N je Finger
hold_fobj = torch.zeros(N, 5, device=dev)        # … und Objektkraft je Finger (Reihenfolge Daumen … klein)
forearm0 = robot.data.joint_pos[:, forearm].clone()
z0 = obj.data.root_pos_w[:, 2].clone()           # Dosenhöhe beim Episodenstart (Größe randomisiert)
episodes = []                                   # abgeschlossene Episoden
# Verlauf je Zeitschritt seit Episodenstart (Summen über laufende Episoden, nur abgeschlossene zählen)
T = int(uenv.max_episode_length) + 2
trace_keys = ("hoehe_mm", "kipp_deg", "finger", "kraft_n")
trace_sum = {k: torch.zeros(T, device=dev) for k in trace_keys}
trace_n = torch.zeros(T, device=dev)
ep_trace = {k: torch.zeros(N, T, device=dev) for k in trace_keys}   # laufende Episode je Umgebung


def finish(i, reason):
    if args_cli.verlauf:
        n_i = int(steps[i].item())
        trace_n[:n_i] += 1
        for k in trace_keys:
            trace_sum[k][:n_i] += ep_trace[k][i, :n_i]
    held = reason == "time_out"
    req_ok = REQ_DEG is None or math.degrees(max_tilt[i].item()) <= REQ_DEG
    n = max(steps[i].item(), 1.0)
    early = (not held and steps[i].item() <= early_steps) or (
        REQ_DEG is not None and math.degrees(early_tilt[i].item()) > REQ_DEG)
    episodes.append({
        "ende": reason, "gehalten": held, "erfolg": held and req_ok, "startfehler": early,
        "kipp_max_deg": math.degrees(max_tilt[i].item()),
        "unterarm_max_deg": math.degrees(max_forearm[i].item()),
        "kraft_mittel_n": hold_force[i].item() / hold_steps[i].item() if hold_steps[i] > 0 else None,
        "kraft_ueber_anteil": hold_over[i].item() / hold_steps[i].item() if hold_steps[i] > 0 else None,
        "stall_anteil": stall[i].item() / n,
        "absinken_mm": 1000 * sink[i].item(),
        "unruhe": act_rate[i].item() / n,
        "finger_kontakt": (hold_touch[i] / hold_steps[i]).tolist() if hold_steps[i] > 0 else None,
        "finger_kraft_n": (hold_fobj[i] / hold_steps[i]).tolist() if hold_steps[i] > 0 else None,
    })


t_start = time.time()
total_steps = 0
with torch.inference_mode():
    # mit Video mindestens bis zur vollen Videolänge (sonst fehlt z. B. das Absenken des Tischs)
    while (len(episodes) < args_cli.episodes or total_steps < args_cli.video) and simulation_app.is_running():
        t0 = time.time()
        total_steps += 1
        obs, _, terminated, truncated, _ = env.step(policy(obs["policy"]))
        done = terminated | truncated
        for i in done.nonzero().flatten().tolist():
            if len(episodes) < args_cli.episodes:
                finish(i, next((n for n in term_names if uenv.termination_manager.get_term(n)[i]), "?"))
        # neue Episoden zurücksetzen, laufende fortschreiben (Werte nach dem Schritt)
        for buf in (steps, max_tilt, early_tilt, max_forearm, hold_steps, hold_force, hold_over, stall, act_rate, sink,
                    hold_touch, hold_fobj):
            buf[done] = 0.0
        forearm0[done] = robot.data.joint_pos[done, forearm]
        z0[done] = obj.data.root_pos_w[done, 2]
        live = ~done
        steps[live] += 1
        tilt = mdp.object_tilt(uenv)
        max_tilt[live] = torch.maximum(max_tilt[live], tilt[live])
        early = live & (steps <= early_steps)
        early_tilt[early] = torch.maximum(early_tilt[early], tilt[early])
        max_forearm[live] = torch.maximum(max_forearm[live], (robot.data.joint_pos[live, forearm] - forearm0[live]).abs())
        in_hold = live & (steps * dt >= HOLD_START_S)
        f = mdp.fingertip_forces(uenv)
        hold_steps[in_hold] += 1
        hold_force[in_hold] += f[in_hold].sum(-1)
        hold_over[in_hold] += (f[in_hold] > FORCE_LIMIT_N).any(-1).float()
        fo = mdp.fingertip_object_forces(uenv)
        hold_touch[in_hold] += (fo[in_hold] > 1.0).float()
        hold_fobj[in_hold] += fo[in_hold]
        stall[live] += (robot.data.applied_torque[live][:, stall_ids].abs() >= STALL_FRACTION * stall_limit[live]).any(-1).float()
        am = uenv.action_manager
        act_rate[live] += ((am.action - am.prev_action) ** 2).sum(-1)[live]
        sink[live] = (z0 - obj.data.root_pos_w[:, 2]).clamp(min=0.0)[live]   # Hand fest → ggü. Startlage
        if args_cli.verlauf:
            idx = (steps - 1).long().clamp(0, T - 1)
            rows = live.nonzero().flatten()
            vals = {"hoehe_mm": 1000 * (obj.data.root_pos_w[:, 2] - z0), "kipp_deg": torch.rad2deg(tilt),
                    "finger": (fo > 1.0).float().sum(-1), "kraft_n": f.sum(-1)}
            for k in trace_keys:
                ep_trace[k][rows, idx[rows]] = vals[k][rows]
        if args_cli.real_time:
            time.sleep(max(0.0, dt - (time.time() - t0)))


def median(v):
    v = sorted(x for x in v if x is not None)
    return v[len(v) // 2] if v else None


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


E = len(episodes)
held = [e for e in episodes if e["gehalten"]]
rate = lambda key: sum(1 for e in episodes if e[key]) / max(E, 1)  # noqa: E731
summary = {
    "aufgabenerfolg": rate("erfolg"),
    "haltequote": rate("gehalten"),
    "fehler": {
        "startfehler": sum(1 for e in episodes if e["startfehler"]) / max(E, 1),
        "gefallen": sum(1 for e in episodes if e["ende"] == "object_dropped" and not e["startfehler"]) / max(E, 1),
        "instabil": sum(1 for e in episodes if e["ende"] == "abnormal_robot" and not e["startfehler"]) / max(E, 1),
        "anforderung_verletzt": sum(1 for e in episodes if e["gehalten"] and not e["erfolg"] and not e["startfehler"]) / max(E, 1),
    },
    "leitplanken": {
        "kipp_median_deg": median([e["kipp_max_deg"] for e in held]),
        "unterarm_median_deg": median([e["unterarm_max_deg"] for e in held]),
        "kraft_mittel_n": mean([e["kraft_mittel_n"] for e in held]),
        "kraft_ueber_15n_anteil": mean([e["kraft_ueber_anteil"] for e in held]),
        "stall_anteil": mean([e["stall_anteil"] for e in held]),
        "absinken_mm": mean([e["absinken_mm"] for e in held]),
        "unruhe": mean([e["unruhe"] for e in held]),
    },
    # beschreibend (keine Leitplanke): Kontaktanteil/Kraft je Finger in der Haltephase, gehaltene Episoden
    "fingernutzung": {
        "finger": ["daumen", "zeige", "mittel", "ring", "klein"],
        "kontakt_anteil": [mean([e["finger_kontakt"][k] for e in held if e["finger_kontakt"]]) for k in range(5)],
        "kraft_n": [mean([e["finger_kraft_n"][k] for e in held if e["finger_kraft_n"]]) for k in range(5)],
        "finger_mit_kontakt": mean([sum(e["finger_kontakt"]) for e in held if e["finger_kontakt"]]),
    },
}
result = {
    "protokoll": PROTOCOL, "bedingung": args_cli.bedingung, "objekt": args_cli.objekt,
    "policy": args_cli.policy if args_cli.regel else str(Path(args_cli.policy).resolve()), "seed": args_cli.seed,
    "episoden": E, "umgebungen": N, "anforderung": {"max_kipp_deg": REQ_DEG},
    "dauer_s": round(time.time() - t_start, 1), "zusammenfassung": summary,
    "netz": {"eingaenge": int(obs["policy"].shape[-1]), "ausgaenge": int(uenv.action_manager.total_action_dim),
             "actor_parameter": int(sum(p.numel() for p in policy.parameters()))},
    "erfolg_je_episode": [int(e["erfolg"]) for e in episodes],
    "gehalten_je_episode": [int(e["gehalten"]) for e in episodes],
    "kipp_je_episode": [round(e["kipp_max_deg"], 2) for e in episodes],
}


def pct(x):
    return "–" if x is None else f"{100 * x:5.1f} %"


def num(x, unit="", digits=1):
    return "–" if x is None else f"{x:.{digits}f}{unit}"


L = summary["leitplanken"]
lines = [
    f"Bewertung {PROTOCOL}, Bedingung {args_cli.bedingung} (Objekt {args_cli.objekt}): {args_cli.policy}",
    f"{E} Episoden, {N} Umgebungen, Seed {args_cli.seed}, Anforderung Kippwinkel ≤ {REQ_DEG}°",
    "",
    f"Aufgabenerfolg      {pct(summary['aufgabenerfolg'])}",
    f"Haltequote          {pct(summary['haltequote'])}",
    "Fehlerarten:  " + "  ".join(f"{k} {pct(v)}" for k, v in summary["fehler"].items()),
    "Leitplanken (gehaltene Episoden):",
    f"  Kippwinkel Median    {num(L['kipp_median_deg'], '°')}",
    f"  Unterarm Median      {num(L['unterarm_median_deg'], '°')}",
    f"  Griffkraft Mittel    {num(L['kraft_mittel_n'], ' N')}",
    f"  Kraft > 15 N         {pct(L['kraft_ueber_15n_anteil'])}",
    f"  Stall-Anteil         {pct(L['stall_anteil'])}",
    f"  Absinken             {num(L['absinken_mm'], ' mm')}",
    f"  Unruhe               {num(L['unruhe'], digits=3)}",
    "Fingernutzung (Haltephase, Kontakt > 1 N / Kraft an der Dose), Daumen … klein:",
    "  Kontakt  " + "  ".join(pct(x) for x in summary["fingernutzung"]["kontakt_anteil"]),
    "  Kraft    " + "  ".join(num(x, " N") for x in summary["fingernutzung"]["kraft_n"]),
    f"  Finger mit Kontakt im Mittel: {num(summary['fingernutzung']['finger_mit_kontakt'], digits=2)}",
]
if args_cli.video and getattr(env, "recording", False):
    env.stop_recording()                        # Video schreiben, auch wenn kürzer als --video
if args_cli.verlauf:
    n = trace_n.clamp(min=1)
    last = int((trace_n > 0).nonzero().max().item()) + 1 if (trace_n > 0).any() else 0
    verlauf = {"protokoll": PROTOCOL, "bedingung": args_cli.bedingung, "objekt": args_cli.objekt,
               "policy": args_cli.policy if args_cli.regel else str(Path(args_cli.policy).resolve()), "episoden": E, "dt_s": dt,
               "absenken_s": [GRASP_TIME_S, HOLD_START_S],
               "t_s": [round((k + 1) * dt, 4) for k in range(last)],
               "laufend_anteil": (trace_n[:last] / max(E, 1)).tolist(),
               **{k: (trace_sum[k][:last] / n[:last]).tolist() for k in trace_keys}}
    vstem = STEM.replace(PROTOCOL, "verlauf-v1", 1)
    (out_dir / f"{vstem}.json").write_text(json.dumps(verlauf), encoding="utf-8")
    print(f"Verlauf: {out_dir / (vstem + '.json')}", flush=True)
if not args_cli.nur_medien:
    (out_dir / f"{STEM}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    (out_dir / f"{STEM}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines), flush=True)
print(f"Bericht: {out_dir / (STEM + '.txt')}", flush=True)
os._exit(0)
