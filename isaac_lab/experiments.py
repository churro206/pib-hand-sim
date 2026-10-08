"""
experiments.py — Experimente planen, ausführen, bewerten, vergleichen (experiments/README.md).

Läuft mit System-Python (PyYAML, numpy), Isaac Lab nur als Unterprozess über isaaclab.sh —
die conda-Umgebung env_isaaclab muss aktiv sein (isaaclab.sh nimmt deren Python).

  /usr/bin/python3 isaac_lab/experiments.py new  --eltern EXP-001 --kurz name --titel "..."
  /usr/bin/python3 isaac_lab/experiments.py new  --eltern EXP-004 --kurz name --titel "..." --ohne-training
  /usr/bin/python3 isaac_lab/experiments.py bench --envs 2048 4096      # Durchsatz → umgebungen: auto
  /usr/bin/python3 isaac_lab/experiments.py run  EXP-001 [EXP-002 ...]  # Kurztest, Training, Bewertung, Bericht
  /usr/bin/python3 isaac_lab/experiments.py eval EXP-000 [--neu]        # fehlende (--neu: alle) Bewertungen + Bericht
  /usr/bin/python3 isaac_lab/experiments.py bericht EXP-000             # nur Bericht + Trainingsdiagramme neu
  /usr/bin/python3 isaac_lab/experiments.py done                        # index.md neu erzeugen
  /usr/bin/python3 isaac_lab/experiments.py medien [EXP-006] --videos --verlauf   # Videos + Episodenverlauf

run, eval und done enden mit der Sicherung nach Hugging Face (backup_policies.py --upload;
abschalten mit --kein-backup).

Isaac Labs train.py hängt nach dem Ende in simulation_app.close() — sobald der letzte
Checkpoint geschrieben ist, wird der Prozess nach 60 s beendet.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# conda env_isaaclab setzt PYTHONPATH auf Isaac Sims Pakete (cp311) — nur für diesen
# Steuerprozess (System-Python) ausblenden; Unterprozesse erben die Umgebung unverändert
sys.path[:] = [p for p in sys.path if "isaac" not in p.lower()]

import numpy as np  # noqa: E402
import yaml  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EXP_DIR = REPO / "experiments"
RUNS = REPO / "logs" / "rsl_rl" / "pib_grasp_hand_left"
LOGS = REPO / "logs" / "experiments"
ISAACLAB = Path.home() / "IsaacLab" / "isaaclab.sh"
BENCH = EXP_DIR / "_bench.json"
SMOKE = {"iterationen": 3, "umgebungen": 256, "seed": 0}
EVAL = {"umgebungen": 256, "episoden": 1000, "video_umgebungen": 16, "video_schritte": 300,
        "beste_video_schritte": 3 * 270}     # beste Videos: 3 Episoden (je 4,5 s × 60 Hz), ~14 s
BOOT = 2000
# Leitplanken: (Schlüssel, Bezeichnung, Toleranz, Art) — Art "abs" = Einheit der Größe, "rel" = Anteil
GUARDRAILS = [
    ("kipp_median_deg", "Kippwinkel Median [°]", 5.0, "abs"),
    ("unterarm_median_deg", "Unterarm Median [°]", 10.0, "abs"),
    ("kraft_mittel_n", "Griffkraft Mittel [N]", 0.20, "rel"),
    ("kraft_ueber_15n_anteil", "Kraft > 15 N [Anteil]", 0.05, "abs"),
    ("stall_anteil", "Stall-Anteil [Anteil]", 0.05, "abs"),
    ("absinken_mm", "Absinken [mm]", 5.0, "abs"),
    ("unruhe", "Unruhe", 0.20, "rel"),
]


class _ParamsLoader(yaml.SafeLoader):
    """SafeLoader, der zusätzlich Python-Tupel aus Isaac Labs env.yaml liest (sonst nichts Ausführbares)."""


_ParamsLoader.add_constructor("tag:yaml.org,2002:python/tuple", lambda l, n: tuple(l.construct_sequence(n)))


def _python_tag_as_text(loader, suffix, node):
    """Übrige Python-Tags (slice, Klassen, Funktionen) nur als Text — nichts wird ausgeführt."""
    if isinstance(node, yaml.SequenceNode):
        return f"{suffix}{tuple(loader.construct_sequence(node, deep=True))}"
    if isinstance(node, yaml.MappingNode):
        return f"{suffix}{loader.construct_mapping(node, deep=True)}"
    return f"{suffix}:{loader.construct_scalar(node)}"


_ParamsLoader.add_multi_constructor("tag:yaml.org,2002:python/", _python_tag_as_text)
# Schlüssel, die sich je Lauf ändern, ohne eine Änderung des Experiments zu sein
_DIFF_IGNORE = ("seed", "run_name", "log_dir", "load_run", "load_checkpoint", "resume")
# reine Optik (Kamera, Farben) — keine Änderung des Experiments
_DIFF_IGNORE_PARTS = ("viewer", "visual_material", "visual_material_path", "light", "sun")


def load_params(run_dir: Path) -> dict:
    out = {}
    for name in ("agent", "env"):
        p = run_dir / "params" / f"{name}.yaml"
        if p.exists():
            out[name] = yaml.load(p.read_text(encoding="utf-8"), Loader=_ParamsLoader)
    return out


def _flat(d, prefix=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from _flat(v, f"{prefix}{k}.")
    else:
        yield prefix.rstrip("."), d


def config_diff(child: dict, parent: dict) -> list[str]:
    """Alle Einstellungen, die sich zwischen zwei Läufen unterscheiden (agent.yaml + env.yaml)."""
    a, b = dict(_flat(child)), dict(_flat(parent))
    out = []
    for k in sorted(set(a) | set(b)):
        if k.split(".")[-1] in _DIFF_IGNORE or any(part in _DIFF_IGNORE_PARTS for part in k.split(".")):
            continue
        if a.get(k, "∅") != b.get(k, "∅"):
            out.append(f"{k}: {b.get(k, '∅')} → {a.get(k, '∅')}")
    return out


def net_profile(params: dict, ev: dict | None) -> dict:
    ag, env = params.get("agent", {}), params.get("env", {})
    pol, alg = ag.get("policy", {}), ag.get("algorithm", {})
    hist = (((env.get("observations") or {}).get("policy")) or {}).get("history_length")
    return {
        "actor": pol.get("actor_hidden_dims"), "critic": pol.get("critic_hidden_dims"),
        "aktivierung": pol.get("activation"), "verlauf": hist,
        "eingaenge": (ev or {}).get("netz", {}).get("eingaenge"),
        "actor_parameter": (ev or {}).get("netz", {}).get("actor_parameter"),
        "lernrate": alg.get("learning_rate"), "entropie": alg.get("entropy_coef"),
        "epochen": alg.get("num_learning_epochs"), "mini_batches": alg.get("num_mini_batches"),
        "schritte_je_umgebung": ag.get("num_steps_per_env"), "iterationen": ag.get("max_iterations"),
        "umgebungen": (env.get("scene") or {}).get("num_envs"),
    }


def log(msg):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "experiments.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sh(*cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO, **kw).stdout.strip()


# ── Experimente lesen/schreiben ───────────────────────────────────────────────

def exp_path(exp_id: str) -> Path:
    hits = sorted(EXP_DIR.glob(f"{exp_id}_*"))
    if not hits:
        sys.exit(f"{exp_id} nicht gefunden in {EXP_DIR}")
    return hits[0]


def load(exp_id: str) -> tuple[Path, dict]:
    d = exp_path(exp_id)
    return d, yaml.safe_load((d / "experiment.yaml").read_text(encoding="utf-8"))


def save_fields(d: Path, **fields):
    """Felder in experiment.yaml ersetzen, Kommentare/Reihenfolge erhalten (einfache Skalare/Listen)."""
    p = d / "experiment.yaml"
    text = p.read_text(encoding="utf-8")
    for key, value in fields.items():
        dumped = yaml.safe_dump({key: value}, allow_unicode=True, default_flow_style=False, sort_keys=False).rstrip()
        # Feld endet an der nächsten Zeile, die weder eingerückt noch Listeneintrag ist
        pattern = re.compile(rf"^{key}:.*?(?=^[^\s-]|\Z)", re.M | re.S)
        if pattern.search(text):
            text = pattern.sub(lambda _: dumped + "\n", text, count=1)
        else:
            text += dumped + "\n"
    p.write_text(text, encoding="utf-8")


# ── new ───────────────────────────────────────────────────────────────────────

def cmd_new(a):
    ids = [int(p.name[4:7]) for p in EXP_DIR.glob("EXP-[0-9][0-9][0-9]_*")]
    new_id = f"EXP-{max(ids, default=-1) + 1:03d}"
    parent_dir, parent = load(a.eltern)
    d = EXP_DIR / f"{new_id}_{a.kurz}"
    d.mkdir()
    text = (EXP_DIR / "_vorlage.yaml").read_text(encoding="utf-8")
    (d / "experiment.yaml").write_text(text, encoding="utf-8")
    if a.ohne_training:          # nur bewerten: Läufe der Eltern unter eigenen Bedingungen
        training, extra = None, {"laeufe_von": a.eltern, "fenstertest": True}
    else:
        training, extra = dict(parent["training"]), {}
        training["seeds"] = sorted(set(training.get("seeds") or []) | {42, 43, 44, 45, 46})   # README: 5 Seeds
    save_fields(d, id=new_id, titel=a.titel, datum=f"{dt.date.today()}", eltern=a.eltern,
                bedingungen=parent["bedingungen"], training=training, protokoll=parent["protokoll"], **extra)
    log(f"{new_id} angelegt: {d.relative_to(REPO)} (Eltern {a.eltern})")
    if parent.get("commit"):
        base = str(parent["commit"]).split("+")[0]
        print(f"\nCode-Unterschiede seit {a.eltern} ({base}) — es sollte genau eine Änderung sein:")
        print(sh("git", "diff", "--stat", base, "--", "isaac_lab", "config", "isaac_sim/usd") or "  (keine)")
    print(f"\nJetzt ausfüllen: {d.relative_to(REPO)}/experiment.yaml → hypothese, aenderung, fenstertest")


# ── Unterprozesse: Training mit Schutz gegen Hängen ──────────────────────────

def check_env():
    if os.environ.get("CONDA_DEFAULT_ENV") != "env_isaaclab":
        sys.exit("conda-Umgebung env_isaaclab ist nicht aktiv (deactivate; conda activate env_isaaclab)")


def train(run_name: str, task: str, envs: int, iters: int, seed: int, extra: list, log_file: Path) -> tuple[Path | None, dict]:
    before = set(RUNS.glob("*")) if RUNS.exists() else set()
    cmd = [str(ISAACLAB), "-p", "isaac_lab/train.py", "--task", task, "--headless", "--num_envs", str(envs),
           "--max_iterations", str(iters), "--seed", str(seed), "--run_name", run_name, *extra]
    log(f"  Training {run_name}: {envs} Umgebungen, {iters} Iterationen, Seed {seed}")
    start, vram, run_dir, done_at = time.time(), 0, None, None
    # Schutz gegen Hänger: 3× erwartete Dauer (~2,3 s/Iteration bei 1024 Umgebungen), mind. 30 min
    limit_s = max(1800.0, 3 * 2.3 * iters * envs / 1024 + 300)
    with open(log_file, "w", encoding="utf-8") as out:
        proc = subprocess.Popen(cmd, cwd=REPO, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        while proc.poll() is None:
            time.sleep(5)
            try:
                vram = max(vram, int(sh("nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits").split()[0]))
            except (ValueError, IndexError):
                pass
            if run_dir is None:
                new = [p for p in set(RUNS.glob(f"*_{run_name}")) - before if p.is_dir()]
                run_dir = max(new, default=None)
            if run_dir is not None and (run_dir / f"model_{iters - 1}.pt").exists():
                done_at = done_at or time.time()
                if time.time() - done_at > 60:
                    os.killpg(proc.pid, signal.SIGTERM)
                    time.sleep(5)
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
            if time.time() - start > limit_s:
                log(f"  Abbruch: über {limit_s / 3600:.1f} h (3× erwartete Dauer) — Training hängt?")
                os.killpg(proc.pid, signal.SIGKILL)
    text = log_file.read_text(encoding="utf-8", errors="ignore")
    sps = [int(x) for x in re.findall(r"Computation: (\d+) steps/s", text)]
    terms = {k: float(v) for k, v in re.findall(r"Episode_Termination/(\w+): ([\d.]+)", text)[-8:]}
    info = {"dauer_min": round((time.time() - start) / 60, 1), "schritte_pro_s": int(np.mean(sps[-5:])) if sps else 0,
            "vram_max_mib": vram, "nan": bool(re.search(r"Mean reward:\s+nan", text, re.I)),
            "fehler": bool(re.search(r"Traceback|CUDA out of memory|RuntimeError", text)),
            "abbrueche_letzte": terms}
    ok = run_dir is not None and (run_dir / f"model_{iters - 1}.pt").exists() and not info["nan"]
    return (run_dir if ok else None), info


def write_meta(run_dir: Path, exp_id: str, seed: int, train_info: dict, cmdline: str):
    versions = sh(str(ISAACLAB), "-p", "-c",
                  "import importlib.metadata as m, torch, json;"
                  "print(json.dumps({p: m.version(p) for p in ['isaaclab','isaaclab_tasks','isaaclab_rl','rsl-rl-lib']}"
                  " | {'torch': torch.__version__}))").splitlines()
    meta = {
        "experiment": exp_id, "seed": seed, "commit": sh("git", "rev-parse", "HEAD"),
        "branch": sh("git", "rev-parse", "--abbrev-ref", "HEAD"),
        "uncommitted": bool(sh("git", "status", "--porcelain", "--untracked-files=no")),
        "untracked": sh("git", "ls-files", "--others", "--exclude-standard").splitlines(),
        "isaacsim": (Path.home() / "isaacsim" / "VERSION").read_text().strip() if (Path.home() / "isaacsim" / "VERSION").exists() else None,
        "versions": json.loads(versions[-1]) if versions and versions[-1].startswith("{") else None,
        "gpu": sh("nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"),
        "befehl": cmdline, "training": train_info, "zeit": f"{dt.datetime.now():%Y-%m-%d %H:%M}",
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
    (run_dir / "pib_hand_sim.diff").write_text(sh("git", "diff", "HEAD"), encoding="utf-8")
    untracked = [f for f in meta["untracked"] if (REPO / f).is_file() and (REPO / f).stat().st_size < 1_000_000]
    if untracked:
        subprocess.run(["tar", "czf", str(run_dir / "pib_hand_sim_untracked.tar.gz"), *untracked], cwd=REPO)


DEFAULT_CONDITION = "zylinder_seitlich"      # Bewertung ohne Suffix (eval-v1.json), Objekt zylinder_d6
DEFAULT_OBJECT = "zylinder_d6"


def stem(exp: dict, cond: dict) -> str:
    """Dateiname der Bewertung je Bedingung (wie eval_policy.py)."""
    return exp["protokoll"] if cond["name"] == DEFAULT_CONDITION else f"{exp['protokoll']}_{cond['name']}"


def evaluate(run_dir: Path, exp: dict, video: bool, log_file: Path, neu: bool = False) -> bool:
    """Lauf unter allen Bedingungen bewerten. Vorhandene Bewertungen bleiben (neu=True: neu bewerten) —
    Experimente ohne Training teilen sich die Läufe mit ihrer Quelle, deren Zahlen sollen stehen bleiben."""
    ok = True
    with open(log_file, "a", encoding="utf-8") as out:
        for cond in exp["bedingungen"]:
            if neu or not (run_dir / f"{stem(exp, cond)}.json").exists():
                evaluate_condition(run_dir, exp, cond, video, out)
            ok &= (run_dir / f"{stem(exp, cond)}.json").exists()
    return ok


def rule_args(exp: dict) -> list[str]:
    r = exp["regel"]
    return ["--regel", r["name"], "--regel-param", r.get("param") or ""]


def evaluate_condition(run_dir: Path, exp: dict, cond: dict, video: bool, out):
    req = cond["anforderung"].get("max_kipp_deg")
    # Regel: immer der LETZTE Checkpoint, nie der beste nach Bewertung (sonst Auswahl-Verzerrung)
    ckpts = sorted(run_dir.glob("model_*.pt"), key=lambda p: int(p.stem.split("_")[1]))
    exported = run_dir / "exported" / "policy.pt"
    # Export aktueller als der letzte Checkpoint → Export nehmen (z. B. EXP-000: Critic-Eingang
    # hat sich seitdem geändert, der Checkpoint lädt nicht mehr, der Actor schon)
    if exp.get("regel"):
        src = rule_args(exp)
    elif exported.exists() and (not ckpts or exported.stat().st_mtime >= ckpts[-1].stat().st_mtime):
        src = ["--policy", str(exported)]
    else:
        src = ["--checkpoint", str(ckpts[-1])]
    base = [str(ISAACLAB), "-p", "isaac_lab/eval_policy.py", "--headless", "--max_kipp_deg", str(req if req is not None else -1),
            "--objekt", cond.get("objekt_id") or DEFAULT_OBJECT, "--bedingung", cond["name"]]
    log(f"    Bedingung {cond['name']}")
    subprocess.run(base + src + ["--num_envs", str(EVAL["umgebungen"]), "--episodes", str(EVAL["episoden"]),
                                 "--out", str(run_dir)], cwd=REPO, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
    if video:
        subprocess.run(base + (rule_args(exp) if exp.get("regel") else ["--policy", str(run_dir / "exported" / "policy.pt")]) + [
                               "--num_envs", str(EVAL["video_umgebungen"]), "--episodes", str(EVAL["video_umgebungen"]),
                               "--video", str(EVAL["video_schritte"]), "--out", str(run_dir / "video_eval")],
                       cwd=REPO, stdout=out, stderr=subprocess.STDOUT, timeout=1800)


# ── Statistik ─────────────────────────────────────────────────────────────────

def iqm(values) -> float:
    """Interquartilsmittel (Agarwal et al. 2021, rliable): Mittel der mittleren 50 % — untere und obere
    25 % verworfen, Randwerte anteilig gewichtet (wie scipy.stats.trim_mean mit 0,25)."""
    v = np.sort(np.asarray(values, float))
    n = len(v)
    lo, hi = 0.25 * n, 0.75 * n
    w = np.clip(np.minimum(np.arange(1, n + 1), hi) - np.maximum(np.arange(n), lo), 0, None)
    return float((v * w).sum() / w.sum())


FAIL_BELOW = 0.5        # Seed gilt als Fehlschlag unter 50 % Aufgabenerfolg


def boot_means(per_seed: list[np.ndarray], rng) -> np.ndarray:
    """Zweistufiger Bootstrap: Seeds ziehen, darin Episoden ziehen → BOOT Mittelwerte."""
    k = len(per_seed)
    out = np.empty(BOOT)
    for b in range(BOOT):
        seeds = rng.integers(0, k, k)
        out[b] = np.mean([rng.choice(per_seed[s], len(per_seed[s])).mean() for s in seeds])
    return out


def boot_iqm(per_seed: list[np.ndarray], rng) -> np.ndarray:
    """Zweistufiger Bootstrap des IQM über Seeds (wie rliable): Seeds ziehen, darin Episoden ziehen,
    IQM der Seed-Mittel → BOOT Werte."""
    k = len(per_seed)
    out = np.empty(BOOT)
    for b in range(BOOT):
        seeds = rng.integers(0, k, k)
        out[b] = iqm([rng.choice(per_seed[s], len(per_seed[s])).mean() for s in seeds])
    return out


def requirement(cond: dict):
    return cond["anforderung"].get("max_kipp_deg")


def find_condition(exp: dict, name: str) -> dict | None:
    return next((c for c in exp["bedingungen"] if c["name"] == name), None)


def aggregate(exp: dict, cond: dict, req="eigene") -> dict:
    """Ergebnisse aller Seeds unter einer Bedingung; Anforderung (max. Kippwinkel) wird hier angewandt —
    für den Vergleich mit den Eltern deren Rohdaten unter der Anforderung des Kindes (req=...)."""
    req = requirement(cond) if req == "eigene" else req
    evals, seed_ids = [], []
    for r in dict.fromkeys(exp.get("laeufe") or []):      # doppelte Einträge nur einmal zählen
        p = REPO / r / f"{stem(exp, cond)}.json"
        if p.exists():
            evals.append(json.loads(p.read_text()))
            m = re.search(r"_s(\d+)$", r)
            seed_ids.append(int(m.group(1)) if m else None)
    if not evals:
        return {}
    rng = np.random.default_rng(0)
    res = {"protokoll": evals[0]["protokoll"], "seeds": len(evals), "laeufe": exp.get("laeufe"),
           "bedingung": cond["name"], "objekt": cond.get("objekt_id") or DEFAULT_OBJECT,
           "seed_ids": seed_ids, "je_seed": [e["zusammenfassung"] for e in evals]}
    def success(e):
        held = np.array(e["gehalten_je_episode"], bool)
        if "kipp_je_episode" not in e:          # ältere Bewertung: Anforderung schon angewandt
            return np.array(e["erfolg_je_episode"], float)
        return (held & ((np.array(e["kipp_je_episode"]) <= req) if req is not None else True)).astype(float)

    res["anforderung_max_kipp_deg"] = req
    res["_erfolg_je_seed"] = [success(e) for e in evals]
    for key, per_seed in (("aufgabenerfolg", res["_erfolg_je_seed"]),
                          ("haltequote", [np.array(e["gehalten_je_episode"], float) for e in evals])):
        bm = boot_means(per_seed, rng)
        seed_rates = [float(s.mean()) for s in per_seed]
        bi = boot_iqm(per_seed, rng)
        res[key] = {"mittel": float(np.mean(seed_rates)), "iqm": iqm(seed_rates), "je_seed": seed_rates,
                    "iqm_ki95": [float(np.percentile(bi, 2.5)), float(np.percentile(bi, 97.5))],
                    "fehlschlag_seeds": float(np.mean([r < FAIL_BELOW for r in seed_rates])),
                    "ki95": [float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))], "_boot": bm}
    first = REPO / exp["laeufe"][0]
    res["netz"] = net_profile(load_params(first), evals[0])
    res["_params"] = load_params(first)
    fn = [e["zusammenfassung"].get("fingernutzung") for e in evals if e["zusammenfassung"].get("fingernutzung")]
    res["fingernutzung"] = {
        "je_seed_kontakt": [f["kontakt_anteil"] for f in fn],
        "finger_mit_kontakt": _mean([f["finger_mit_kontakt"] for f in fn]),
    } if fn else None
    res["leitplanken"] = {g[0]: _mean([e["zusammenfassung"]["leitplanken"].get(g[0]) for e in evals]) for g in GUARDRAILS}
    res["fehler"] = {k: _mean([e["zusammenfassung"]["fehler"][k] for e in evals]) for k in evals[0]["zusammenfassung"]["fehler"]}
    res["fehler"]["anforderung_verletzt"] = float(np.mean([
        np.mean(np.array(e["gehalten_je_episode"], bool) & ~success(e).astype(bool)) for e in evals]))
    return res


def _mean(v):
    v = [x for x in v if x is not None]
    return float(np.mean(v)) if v else None


def verdict(child: dict, parent: dict) -> dict:
    if not parent or parent.get("protokoll") != child.get("protokoll"):
        return {"urteil": "kein Vergleich (keine Eltern-Bewertung mit gleichem Protokoll)"}
    diff = child["aufgabenerfolg"]["_boot"] - parent["aufgabenerfolg"]["_boot"]
    ci = [float(np.percentile(diff, 2.5)), float(np.percentile(diff, 97.5))]
    violated = []
    for key, label, tol, kind in GUARDRAILS:
        c, p = child["leitplanken"].get(key), parent["leitplanken"].get(key)
        if c is None or p is None:
            continue
        limit = p + tol if kind == "abs" else p * (1 + tol)
        if c > limit:
            violated.append(f"{label}: {c:.3g} > {limit:.3g}")
    if ci[0] > 0:
        u = "Leitplanke verletzt" if violated else "besser"
    elif ci[1] < 0:
        u = "schlechter"
    else:
        u = "kein messbarer Unterschied"
    note = " (vorläufig: < 3 Seeds)" if min(child["seeds"], parent["seeds"]) < 3 else ""
    return {"urteil": u + note, "differenz_aufgabenerfolg": float(diff.mean()), "differenz_ki95": ci,
            "leitplanken_verletzt": violated}


def training_plots(d: Path, exp: dict, training: bool, conditions: bool) -> dict | None:
    """Diagramme (plot_training.py über isaaclab.sh) → <experiment>/diagramme/: Trainingsverlauf der eigenen
    Läufe und/oder Ergebnis je Bedingung (aus results.json); Fehler nur als Warnung."""
    runs = list(dict.fromkeys(exp.get("laeufe") or []))
    out = d / "diagramme" / "training.json"
    vstems = [(stem(exp, c).replace(exp["protokoll"], "verlauf-v1", 1), c["kurz"]) for c in BENCHMARK]
    trace = training and any((REPO / r / f"{s}.json").exists() for r in runs for s, _ in vstems)
    if not runs or not (training or conditions):
        return None
    if os.environ.get("CONDA_DEFAULT_ENV") != "env_isaaclab":
        log("  WARNUNG: Diagramme übersprungen — conda-Umgebung env_isaaclab nicht aktiv")
    else:
        cmd = [str(ISAACLAB), "-p", "isaac_lab/plot_training.py", "--exp-dir", str(d.relative_to(REPO))]
        if conditions:
            cmd += ["--bedingungen", str((d / "results.json").relative_to(REPO))]
        if training:
            cmd += ["--runs", *runs]
        if trace:
            cmd += ["--verlauf-laeufe", *runs, "--verlauf-bedingungen", *(f"{s}={k}" for s, k in vstems)]
        if training and exp.get("eltern"):
            _, pexp = load(exp["eltern"])
            cmd += ["--eltern-runs", *dict.fromkeys(pexp.get("laeufe") or []), "--eltern-name", exp["eltern"]]
        log_file = LOGS / f"{exp['id']}_diagramme.log"
        with open(log_file, "w", encoding="utf-8") as f:
            if subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT).returncode != 0:
                log(f"  WARNUNG: Diagramme fehlgeschlagen ({log_file})")
    return json.loads(out.read_text()) if training and out.exists() else None


def training_section(tr: dict) -> list[str]:
    figs = [("lernkurve", "Lernkurve"), ("belohnung", "Belohnungsanteile"), ("abbrueche", "Abbrüche"),
            ("ppo", "PPO-Diagnose")]
    seeds = tr["je_seed"]
    lines = ["", "## Trainingsverlauf", "",
             "Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen "
             "Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten "
             f"{tr['tail_iterationen']} Iterationen (Belohnungsanteile je Sekunde Episode).", "",
             "| Größe | " + " | ".join(f"Seed {s['seed']}" for s in seeds) + " | Mittel |",
             "|---|" + "---|" * (len(seeds) + 1)]
    tags = ["Train/mean_reward"] + sorted({t for s in seeds for t in s["endwerte"] if t.startswith("Episode_Reward/")}) \
        + ["Episode_Termination/object_dropped", "Policy/mean_noise_std"]
    for tag in tags:
        vals = [s["endwerte"].get(tag) for s in seeds]
        if all(v is None for v in vals):
            continue
        fmt = (lambda v: f"{100 * v:.1f} %") if tag.startswith("Episode_Termination/") else (lambda v: f"{v:.3g}")
        cells = ["–" if v is None else fmt(v) for v in vals]
        known = [v for v in vals if v is not None]
        lines.append(f"| {tag.split('/', 1)[1]} | " + " | ".join(cells) + f" | {fmt(float(np.mean(known)))} |")
    for name, title in figs:
        lines += ["", f"![{title}](diagramme/{name}.svg)"]
    return lines


def _clean(res: dict) -> dict:
    return {k: ({kk: vv for kk, vv in v.items() if kk != "_boot"} if isinstance(v, dict) else v)
            for k, v in res.items() if not k.startswith("_")}


def _pct(x):
    return "–" if x is None else f"{100 * x:.1f} %"


def condition_result(exp: dict, cond: dict, pexp: dict | None, first: dict | None) -> tuple[dict, dict, str]:
    """Ergebnis einer Bedingung + Vergleichspartner: die Eltern unter derselben Bedingung (eigene Läufe
    vorausgesetzt), sonst — bei Experimenten auf fremden Läufen — die Referenzbedingung (erste)."""
    res = aggregate(exp, cond)
    if not res:
        return {}, {}, ""
    ref, label = {}, ""
    same_runs = pexp is not None and set(pexp.get("laeufe") or []) == set(exp.get("laeufe") or [])
    if pexp is not None and not same_runs:          # Eltern-Läufe unter dieser Bedingung (falls bewertet)
        ref, label = aggregate(pexp, cond, req=requirement(cond)), exp["eltern"]
    if not ref and first is not None and first["name"] != cond["name"]:
        ref, label = aggregate(exp, first), f"Referenz {first['name']}"
    if ref:
        res["vergleich"] = verdict(res, ref)
    elif same_runs and first is not None and first["name"] == cond["name"]:
        res["vergleich"] = {"urteil": "Referenzbedingung"}
    else:
        ref, label = {}, ""
        res["vergleich"] = {"urteil": "kein Vergleich (keine Eltern-Bewertung mit gleichem Protokoll)"}
    res["vergleich"]["gegen"] = label or None
    return res, ref, label


def condition_lines(res: dict, ref: dict, label: str) -> list[str]:
    pct, v = _pct, res["vergleich"]
    col = label or "Eltern"
    lines = [f"Bedingung `{res['bedingung']}` (Objekt `{res['objekt']}`, Kippwinkel ≤ {res['anforderung_max_kipp_deg']}°), "
             f"Protokoll {res['protokoll']}, {res['seeds']} Seed(s); Spalte {col} unter derselben Anforderung", "",
             f"| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | {col} (Mittel / IQM) |",
             "|---|---|---|---|---|---|"]
    for key in ("aufgabenerfolg", "haltequote"):
        pv = f"{pct(ref[key]['mittel'])} / {pct(ref[key]['iqm'])}" if ref else "–"
        lines.append(f"| {key} | {pct(res[key]['mittel'])} | {pct(res[key]['ki95'][0])} – {pct(res[key]['ki95'][1])} | "
                     f"{pct(res[key]['iqm'])} | {pct(res[key]['fehlschlag_seeds'])} | {pv} |")
    for key, lab, _, kind in GUARDRAILS:
        c = res["leitplanken"].get(key)
        p = ref.get("leitplanken", {}).get(key) if ref else None
        f = (lambda x: "–" if x is None else (pct(x) if "anteil" in key else f"{x:.3g}"))
        lines.append(f"| {lab} | {f(c)} | | | | {f(p)} |")
    lines += ["", "Fehlerarten: " + ", ".join(f"{k} {pct(x)}" for k, x in res["fehler"].items()), "",
              f"**Urteilsvorschlag: {v['urteil']}**" + (f" (gegenüber {label})" if label else "")]
    if "differenz_ki95" in v:
        lines.append(f"Unterschied Aufgabenerfolg {100 * v['differenz_aufgabenerfolg']:+.1f} Prozentpunkte "
                     f"(95-%-KI {100 * v['differenz_ki95'][0]:+.1f} … {100 * v['differenz_ki95'][1]:+.1f})")
    for x in v.get("leitplanken_verletzt", []):
        lines.append(f"- Leitplanke: {x}")
    lines += ["", "Je Seed: " + ", ".join(f"{pct(s['aufgabenerfolg'])}" for s in res["je_seed"])]
    if res.get("fingernutzung"):
        fn = res["fingernutzung"]
        lines += ["", f"Fingernutzung (Haltephase): im Mittel {fn['finger_mit_kontakt']:.2f} Finger am Objekt; "
                  "Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): "
                  + " · ".join("/".join("–" if x is None else f"{100 * x:.0f}" for x in s) for s in fn["je_seed_kontakt"])]
    return lines


def _details(title: str, body: list[str]) -> list[str]:
    return ["", "<details>", f"<summary>{title}</summary>", ""] + body + ["", "</details>"]


def head_lines(d: Path, exp: dict, pexp: dict | None, rec: dict, prec: dict | None, res: dict,
               parent_main: dict, own_training: bool) -> tuple[list[str], dict]:
    """Kopf des Berichts (Auswertung v2): Leistung, Zuverlässigkeit, Leitplanken, Befund, Urteilsvorschlag."""
    pct = lambda x: "–" if x is None else f"{100 * x:.0f} %"  # noqa: E731
    ci = lambda v: f"[{100 * v[0]:.0f}–{100 * v[1]:.0f} %]"  # noqa: E731
    per_obj = " · ".join(f"{k} {pct(v)}" for k, v in zip(rec["kurz"], rec["leistung_je_objekt"]))
    rez = {k: v for k, v in rec.items() if not k.startswith("_")}
    src_dir = d if own_training else exp_path(exp.get("laeufe_von") or exp.get("eltern"))
    causes = failure_causes(src_dir, rec)
    lines = []
    if not own_training:
        ref = rec["leistung_je_objekt"][0]
        gaps = " · ".join(f"{k} {pct(v)}" + (f" ({100 * (v - ref):+.0f} PP)" if j and v is not None and ref is not None else "")
                          for j, (k, v) in enumerate(zip(rec["kurz"], rec["leistung_je_objekt"])))
        lines += [f"**Transfer** (Läufe von {exp.get('laeufe_von') or exp.get('eltern')}, erfolgreiche Seeds, Median): {gaps}",
                  f"**Zuverlässigkeit** {rec['k']}/{rec['n']} Seeds erfolgreich {ci(rec['zuverlaessigkeit_ki95'])}"
                  + (f" — ohne Erfolg: {', '.join(causes)}" if causes else "")]
        return lines, rez
    lei = rec["leistung"]
    cmp = compare_recipes(rec, prec) if prec else {}
    rez["vergleich"] = {"eltern": exp.get("eltern"), **cmp} if cmp else None
    l1 = (f"**Leistung** {pct(lei['iqm'])} {ci(lei['iqm_ki95'])} (erfolgreiche Seeds, IQM über die Objekte; "
          f"je Objekt {per_obj})" if lei else "**Leistung** – (kein erfolgreicher Seed)")
    if "leistung_p" in cmp:
        lo, hi = cmp["leistung_ki95"]
        word = "gesichert besser" if lo > 0.5 else ("gesichert schlechter" if hi < 0.5 else "kein Unterschied")
        l1 += f" — ggü. {exp['eltern']}: P(besser) = {cmp['leistung_p']:.2f} [{lo:.2f}–{hi:.2f}] → {word}"
    tests = test_performance(exp, rec)
    rez["testobjekte"] = dict(zip([c["name"] for c in TESTOBJEKTE], tests))
    if any(v is not None for v in tests):
        l1 += ("\n\n**Testobjekte** (nie trainiert, erfolgreiche Seeds, Median): "
               + " · ".join(f"{c['kurz'].replace(' (Test)', '')} {pct(v)}" for c, v in zip(TESTOBJEKTE, tests)))
    l2 = f"**Zuverlässigkeit** {rec['k']}/{rec['n']} Seeds erfolgreich {ci(rec['zuverlaessigkeit_ki95'])}"
    if cmp:
        word = ("gesichert schlechter" if cmp["zuverlaessigkeit_schlechter"] else
                "gesichert besser" if cmp["zuverlaessigkeit_besser"] else "nicht unterscheidbar")
        l2 += (f" — {exp['eltern']}: {prec['k']}/{prec['n']}, exakter Fisher-Test p = {cmp['fisher_p']:.2f} → {word}"
               + (" (für eine Aussage ≥ 10 Seeds je Experiment)" if word == "nicht unterscheidbar" else ""))
    violated = (res.get("vergleich") or {}).get("leitplanken_verletzt") or []
    l3 = "**Leitplanken** " + ("; ".join(violated) + " ✗" if violated else ("eingehalten" if cmp else "– (keine Eltern)"))
    finds = []
    if causes:
        finds.append("ohne Erfolg: " + ", ".join(causes))
    vals = [v for v in rec["leistung_je_objekt"] if v is not None]
    if len(vals) > 1:
        j = int(np.argmin([v if v is not None else 2 for v in rec["leistung_je_objekt"]]))
        finds.append(f"Engpass {rec['kurz'][j]} ({pct(rec['leistung_je_objekt'][j])})")
    if parent_main:
        lp, pp = res["leitplanken"], parent_main["leitplanken"]
        fc = (res.get("fingernutzung") or {}).get("finger_mit_kontakt")
        fp = (parent_main.get("fingernutzung") or {}).get("finger_mit_kontakt")
        for label, c, q, f in (("Kippwinkel", lp.get("kipp_median_deg"), pp.get("kipp_median_deg"), "{:.0f}°"),
                               ("Finger am Objekt", fc, fp, "{:.1f}"), ("Unruhe", lp.get("unruhe"), pp.get("unruhe"), "{:.2f}")):
            if c is not None and q and abs(c - q) / abs(q) >= 0.25:
                finds.append(f"{label} {f.format(c)} ({exp['eltern']}: {f.format(q)})")
    l4 = "**Befund** " + ("; ".join(finds) if finds else "–")
    u = (verdict_v2(cmp, violated) if cmp else
         "Ausgangswert" if not pexp else "kein Vergleich (Eltern ohne Benchmark-Bewertung)")
    rez["urteil"] = u
    l5 = f"**Urteilsvorschlag** ({AUSWERTUNG}): **{u}**"
    return [l1, "", l2, "", l3, "", l4, "", l5], rez


def report(exp_id: str):
    d, exp = load(exp_id)
    pexp = load(exp["eltern"])[1] if exp.get("eltern") else None
    conds = exp["bedingungen"]
    results = [condition_result(exp, c, pexp, conds[0] if len(conds) > 1 else None) for c in conds]
    results = [r for r in results if r[0]]
    if not results:
        log(f"{exp_id}: keine Bewertungen gefunden")
        return
    res, ref, _ = results[0]
    own_training = exp.get("training") is not None or bool(exp.get("regel"))
    parent_main = aggregate(pexp, pexp["bedingungen"][0]) if pexp and own_training else {}
    res["konfig_unterschiede"] = config_diff(res["_params"], parent_main["_params"]) if parent_main else []
    used = BENCHMARK if recipe(exp) else conds
    rec = recipe(exp, used)
    prec = recipe(pexp, used) if (pexp and own_training) else None
    out = _clean(res)
    if len(results) > 1:
        out["weitere_bedingungen"] = {r["bedingung"]: _clean(r) for r, _, _ in results[1:]}
    head, rez = head_lines(d, exp, pexp, rec, prec, res, parent_main, own_training) if rec else ([], None)
    if rec:
        out["rezept"] = rez
        out["benchmark"] = {r["bedingung"]: _clean(r) for r in rec["_res"]}
    (d / "results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    tr = training_plots(d, exp, training=exp.get("training") is not None,
                        conditions=bool(rec) and len(rec["bedingungen"]) > 1)

    lines = [f"# {exp_id}: {exp.get('titel', '')}", ""] + head
    src = exp.get("laeufe_von") or exp.get("eltern")
    if own_training:
        best, bv = best_videos(d, exp)
        if bv:
            lines += ["", f"**Beste Videos** (Seed {best}, 3 Episoden): " + " · ".join(bv)]
    if (d / "diagramme" / "bedingungen.svg").exists():
        lines += ["", "![Ergebnis je Bedingung — Punkte = Seeds](diagramme/bedingungen.svg)"]
    if (d / "diagramme" / "verlauf.svg").exists() and own_training:
        lines += ["", "![Verlauf über die Episode](diagramme/verlauf.svg)"]

    # ── Details (ausklappbar) ──
    body = []
    if len(results) > 1:
        for r, rf, label in results:
            body += ["", f"#### Bedingung `{r['bedingung']}`", ""] + condition_lines(r, rf, label)
    else:
        body += condition_lines(*results[0])
    lines += _details("Ergebnisse je Bedingung (eval-v1, Leitplanken, Fehlerarten, Fingernutzung)", body)
    if tr:
        lines += _details("Trainingsverlauf", training_section(tr)[2:])
    elif not own_training:
        sd = exp_path(src).name
        lines += ["", f"Trainingsverlauf: siehe Quelle [{src}](../{sd}/bericht.md) — "
                  + " · ".join(f"[{t}](../{sd}/diagramme/{n}.svg)" for n, t in (
                      ("lernkurve", "Lernkurve"), ("belohnung", "Belohnungsanteile"), ("abbrueche", "Abbrüche"),
                      ("ppo", "PPO-Diagnose")))]
    vids = sorted((d / "videos").glob("*.mp4")) if (d / "videos").exists() else []
    vsrc = d if vids else (exp_path(src) if not own_training else None)
    vids = vids or (sorted((vsrc / "videos").glob("*.mp4")) if vsrc and (vsrc / "videos").exists() else [])
    if vids:
        rel = "videos" if vsrc == d else f"../{vsrc.name}/videos"
        objs = list(dict.fromkeys(v.stem.rsplit("_s", 1)[0] for v in vids))
        seeds_v = sorted({v.stem.rsplit("_s", 1)[1] for v in vids}, key=int)
        vb = ["16 Umgebungen, eine Episode (nicht im Git, Hugging Face)." + (f" Quelle: {src}." if vsrc != d else ""), "",
              "| Objekt | " + " | ".join(f"Seed {s}" for s in seeds_v) + " |", "|---|" + "---|" * len(seeds_v)]
        for o in objs:
            vb.append(f"| `{o}` | " + " | ".join(
                f"[▶]({rel}/{o}_s{s}.mp4)" if (vsrc / "videos" / f"{o}_s{s}.mp4").exists() else "–" for s in seeds_v) + " |")
        lines += _details("Videos aller Seeds", vb)
    n = res["netz"]
    if exp.get("regel"):
        rg = exp["regel"]
        lines += _details("Regel und Parameterwahl", [
            f"Regel `{rg['name']}`, gewählt `{rg.get('param')}` aus dem Raster (Aufgabenerfolg mit Seed 2000, Mittel über "
            f"die Benchmark-Objekte): " + ", ".join(f"`{k}` {100 * v:.0f} %" for k, v in (exp.get("raster_ergebnis") or {}).items())])
        (d / "bericht.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        log(f"{exp_id}: Regel {rg['name']} ({rg.get('param')}) — Leistung "
            f"{_pct(rez['leistung']['iqm']) if rez and rez.get('leistung') else '–'}")
        return
    nb = [f"Actor {n['actor']} ({n['aktivierung']}), {n['actor_parameter']} Parameter, {n['eingaenge']} Eingänge "
          f"(Verlauf {n['verlauf']}) · Critic {n['critic']} · PPO: Lernrate {n['lernrate']}, Entropie {n['entropie']}, "
          f"{n['epochen']} Epochen × {n['mini_batches']} Mini-Batches, {n['schritte_je_umgebung']} Schritte/Umgebung · "
          f"{n['umgebungen']} Umgebungen × {n['iterationen']} Iterationen"]
    if parent_main:
        diffs = res["konfig_unterschiede"]
        nb += ["", f"Geplante Änderung: {exp.get('aenderung', '')}", "",
               f"Konfiguration gegenüber {exp['eltern']} ({len(diffs)} Unterschiede):", ""]
        nb += [f"- `{x}`" for x in diffs[:80]] or ["- keine"]
        if len(diffs) > 80:
            nb.append(f"- … {len(diffs) - 80} weitere (results.json)")
    lines += _details("Netz, Training und Konfiguration", nb)
    (d / "bericht.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if rez and rez.get("leistung"):
        log(f"{exp_id}: Leistung {_pct(rez['leistung']['iqm'])}, {rez['k']}/{rez['n']} Seeds erfolgreich"
            + (f" → {rez['urteil']}" if rez.get("urteil") else ""))
    else:
        log(f"{exp_id}: kein erfolgreicher Seed")


# ── bench / run / eval / done ─────────────────────────────────────────────────

def cmd_bench(a):
    check_env()
    results = {}
    for n in a.envs:
        run_dir, info = train(f"bench{n}", "Pib-Grasp-Hand-Left-v0", n, a.iter, 42, [], LOGS / f"bench_{n}.log")
        results[n] = info | {"ok": run_dir is not None}
        log(f"  {n} Umgebungen: {info['schritte_pro_s']} Schritte/s, VRAM max {info['vram_max_mib']} MiB, ok={run_dir is not None}")
        if run_dir:
            shutil.rmtree(run_dir)
    ok = {n: r for n, r in results.items() if r["ok"] and r["vram_max_mib"] < 7800}
    best = max(ok, key=lambda n: ok[n]["schritte_pro_s"], default=1024)
    BENCH.write_text(json.dumps({"datum": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "ergebnisse": results, "beste": best}, indent=1))
    log(f"Durchsatz: beste Umgebungszahl {best}")


def smoke(exp_id: str, t: dict) -> bool:
    run_dir, info = train(f"{exp_id}_smoke", t["task"], SMOKE["umgebungen"], SMOKE["iterationen"], SMOKE["seed"],
                          t.get("zusatz_args") or [], LOGS / f"{exp_id}_smoke.log")
    if run_dir:
        shutil.rmtree(run_dir)
    early = sum(v for k, v in info["abbrueche_letzte"].items() if k != "time_out")
    log(f"  Kurztest: ok={run_dir is not None}, NaN={info['nan']}, Fehler={info['fehler']}, "
        f"VRAM {info['vram_max_mib']} MiB, Abbrüche {info['abbrueche_letzte']}")
    if early > 0.99:
        log("  Warnung: fast alle Episoden enden vorzeitig")
    return run_dir is not None


def cmd_run(a):
    check_env()
    if sh("git", "status", "--porcelain", "--untracked-files=no", "--", "isaac_lab", "config", "isaac_sim"):
        log("WARNUNG: uncommittete Änderungen in isaac_lab/config/isaac_sim — der Lauf sichert den Diff, "
            "reproduzierbar ist aber nur ein committeter Stand (vorher committen)")
    for exp_id in a.ids:
        d, exp = load(exp_id)
        t = exp["training"]
        if exp.get("regel"):
            run_rule(d, exp)
            continue
        if t is None:
            run_without_training(d, exp)
            continue
        envs = t["umgebungen"]
        if envs == "auto":
            envs = json.loads(BENCH.read_text())["beste"] if BENCH.exists() else 1024
        # Seeds mit vorhandenem Lauf bleiben (Nachtrag weiterer Seeds, z. B. 3 → 5)
        runs = [r for r in dict.fromkeys(exp.get("laeufe") or []) if (REPO / r).exists()]
        done_seeds = {int(m.group(1)) for r in runs if (m := re.search(r"_s(\d+)$", r))}
        todo = [s for s in t["seeds"] if s not in done_seeds]
        if not todo:
            log(f"{exp_id}: alle Seeds trainiert — nichts zu tun (Bewertung: eval)")
            continue
        log(f"== {exp_id}: {exp.get('titel')} ({envs} Umgebungen, {t['iterationen']} Iterationen, Seeds {todo}"
            + (f", vorhanden {sorted(done_seeds)}" if done_seeds else "") + ")")
        # nur Code zählt (experiments/ ändert das Framework selbst während des Laufs)
        commit = sh("git", "rev-parse", "--short", "HEAD") + (
            "+lokal" if sh("git", "status", "--porcelain", "--", "isaac_lab", "config", "isaac_sim") else "")
        if runs:   # Nachtrag: Commit des Experiments bleibt, der neue steht in meta.json der Läufe
            save_fields(d, status="läuft", commit_nachtrag=commit)
        else:
            save_fields(d, status="läuft", commit=commit)
        if not smoke(exp_id, t):
            log(f"{exp_id}: Kurztest fehlgeschlagen — übersprungen ({LOGS / (exp_id + '_smoke.log')})")
            save_fields(d, status="fehlgeschlagen (Kurztest)")
            continue
        for i, seed in enumerate(todo):
            name = f"{exp_id}_s{seed}"
            run_dir, info = train(name, t["task"], envs, t["iterationen"], seed, t.get("zusatz_args") or [],
                                  LOGS / f"{name}.log")
            if run_dir is None:
                log(f"  {name} fehlgeschlagen ({LOGS / (name + '.log')})")
                continue
            write_meta(run_dir, exp_id, seed, info, f"train.py --task {t['task']} --num_envs {envs} "
                       f"--max_iterations {t['iterationen']} --seed {seed}")
            log(f"  {name} fertig nach {info['dauer_min']} min, {info['schritte_pro_s']} Schritte/s → Bewertung")
            runs.append(str(run_dir.relative_to(REPO)))
            save_fields(d, laeufe=runs)
            exp["laeufe"] = runs
            if not evaluate(run_dir, exp, video=(i == 0 and not done_seeds), log_file=LOGS / f"{name}_eval.log"):
                log(f"  Bewertung {name} fehlgeschlagen ({LOGS / (name + '_eval.log')})")
        save_fields(d, status="trainiert")
        report(exp_id)
    cmd_done(a)


def run_rule(d: Path, exp: dict):
    """Regel-Baseline (kein RL): Parameterraster mit eigenem Bewertungs-Seed (2000, 256 Episoden je Benchmark-
    Objekt) auswählen, dann die gewählte Einstellung nach eval-v1 (Seed 1000) bewerten — Auswahl und finale
    Bewertung getrennt (Patterson et al. 2024)."""
    r = exp["regel"]
    run_dir = REPO / "logs" / "regel" / exp["id"]
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"== {exp['id']}: {exp.get('titel')} (Regel {r['name']}, Raster {r.get('raster')})")
    save_fields(d, status="läuft", commit=sh("git", "rev-parse", "--short", "HEAD"))
    scores = {}
    tmp = LOGS / "_regel_tmp"
    for ps in r.get("raster") or [r.get("param") or ""]:
        vals = []
        for c in BENCHMARK:
            shutil.rmtree(tmp, ignore_errors=True)
            cmd = [str(ISAACLAB), "-p", "isaac_lab/eval_policy.py", "--headless", "--regel", r["name"], "--regel-param", ps,
                   "--objekt", c["objekt_id"], "--bedingung", c["name"], "--max_kipp_deg", str(c["anforderung"]["max_kipp_deg"]),
                   "--num_envs", "256", "--episodes", "256", "--seed", "2000", "--out", str(tmp)]
            with open(LOGS / f"{exp['id']}_raster.log", "a", encoding="utf-8") as f:
                subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT, timeout=1800)
            js = list(tmp.glob("eval-v1*.json"))
            vals.append(json.loads(js[0].read_text())["zusammenfassung"]["aufgabenerfolg"] if js else 0.0)
        scores[ps] = float(np.mean(vals))
        log(f"  Raster {ps or '(Standard)'}: Aufgabenerfolg {100 * scores[ps]:.1f} % (Seed 2000, Mittel über die Objekte)")
    shutil.rmtree(tmp, ignore_errors=True)
    best = max(scores, key=scores.get)
    r["param"] = best
    save_fields(d, regel=r, raster_ergebnis={k: round(v, 3) for k, v in scores.items()},
                laeufe=[str(run_dir.relative_to(REPO))])
    exp["laeufe"] = [str(run_dir.relative_to(REPO))]
    log(f"  gewählt: {best} → Bewertung eval-v1")
    evaluate(run_dir, exp, video=True, log_file=LOGS / f"{exp['id']}_eval.log")
    save_fields(d, status="bewertet")
    report(exp["id"])


def run_without_training(d: Path, exp: dict):
    """Experiment ohne eigenes Training (z. B. Transfer an andere Objekte): bewertet die Läufe von
    `laeufe_von` unter den eigenen Bedingungen; vorhandene Bewertungen der Quelle bleiben unverändert."""
    src_id = exp.get("laeufe_von") or exp.get("eltern")
    runs = list(dict.fromkeys(load(src_id)[1].get("laeufe") or []))
    log(f"== {exp['id']}: {exp.get('titel')} (ohne Training, {len(runs)} Läufe von {src_id}, "
        f"Bedingungen {[c['name'] for c in exp['bedingungen']]})")
    save_fields(d, status="läuft", commit=sh("git", "rev-parse", "--short", "HEAD"), laeufe=runs)
    exp["laeufe"] = runs
    for i, r in enumerate(runs):
        log(f"  Bewertung {Path(r).name}")
        if not evaluate(REPO / r, exp, video=(i == 0), log_file=LOGS / f"{exp['id']}_{Path(r).name}_eval.log"):
            log(f"  Bewertung {Path(r).name} unvollständig ({LOGS / (exp['id'] + '_' + Path(r).name + '_eval.log')})")
    save_fields(d, status="bewertet")
    report(exp["id"])


def cmd_eval(a):
    check_env()
    for exp_id in a.ids:
        d, exp = load(exp_id)
        for r in exp.get("laeufe") or []:
            log(f"  Bewertung {exp_id}: {r}")
            evaluate(REPO / r, exp, video=a.video, log_file=LOGS / f"{exp_id}_{Path(r).name}_eval.log", neu=a.neu)
        report(exp_id)
    cmd_done(a)


def cmd_bericht(a):
    for exp_id in a.ids:
        report(exp_id)
    cmd_done(a)


def cmd_done(a):
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}"  # noqa: E731
    rows = ["# Experimente — Übersicht", "", "Automatisch erzeugt (`experiments.py done`). Aufgabenerfolg/Haltequote "
            "in %, [95-%-KI]; Leitplanken Mittel über Seeds. Definitionen: README.md.", "",
            "| ID | Titel | Eltern | Bedingung | Seeds | Netz (Actor) | Param. | Iter. × Umg. | Aufgabenerfolg | IQM | Fehlschlag | Haltequote | Kipp° | Unterarm° | Stall | Finger | Vorschlag | Urteil (bestätigt) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    n_exp = 0
    for d in sorted(EXP_DIR.glob("EXP-[0-9][0-9][0-9]_*")):
        exp = yaml.safe_load((d / "experiment.yaml").read_text(encoding="utf-8"))
        main = json.loads((d / "results.json").read_text()) if (d / "results.json").exists() else {}
        n_exp += 1
        for k, cond in enumerate(exp["bedingungen"]):
            r = main if k == 0 else (main.get("weitere_bedingungen") or {}).get(cond["name"], {})
            rows.append(_index_row(d, exp, cond, r, first=k == 0))
    (EXP_DIR / "index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    log(f"index.md aktualisiert ({n_exp} Experimente)")
    write_leaderboard()
    if not a.kein_backup:
        backup()


def _index_row(d: Path, exp: dict, cond: dict, r: dict, first: bool) -> str:
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}"  # noqa: E731
    ae, hq, lp = r.get("aufgabenerfolg"), r.get("haltequote"), r.get("leitplanken", {})
    f = lambda m: f"{pct(m['mittel'])} [{pct(m['ki95'][0])}–{pct(m['ki95'][1])}]" if m else "–"  # noqa: E731
    g = lambda x: "–" if x is None else f"{x:.0f}"  # noqa: E731
    ident = f"[{exp['id']}]({d.name}/experiment.yaml)" if first else f"↳ {exp['id']}"
    head = (f"| {ident} | {exp.get('titel', '')} | {exp.get('eltern') or '–'} | " if first else f"| {ident} | | | ")
    vs = dict(r.get("vergleich", {}))
    if first and (r.get("rezept") or {}).get("urteil"):
        vs["urteil"] = r["rezept"]["urteil"] + f" ({AUSWERTUNG})"
    gegen = f" (ggü. {vs['gegen']})" if vs.get("gegen") and not first else ""
    return (head + f"{cond['name']} ≤{requirement(cond)}° | {r.get('seeds', '–')} | "
            f"{_net_cell(r.get('netz'))} | {(r.get('netz') or {}).get('actor_parameter') or '–'} | "
            f"{_budget_cell(r.get('netz'))} | {f(ae)} | {pct((ae or {}).get('iqm'))} | {pct((ae or {}).get('fehlschlag_seeds'))} | {f(hq)} | "
            f"{g(lp.get('kipp_median_deg'))} | {g(lp.get('unterarm_median_deg'))} | {pct(lp.get('stall_anteil'))} | "
            f"{_finger_cell(r.get('fingernutzung'))} | "
            f"{vs.get('urteil', '–')}{gegen} | "
            f"{(exp.get('urteil') or '–') if first else ''} |")


def backup():
    """Policies + experiments/ nach Hugging Face (backup_policies.py) — Fehler nur als Warnung."""
    commits = {json.loads(m.read_text()).get("commit") for m in RUNS.glob("*/meta.json")} - {None}
    unpushed = [c[:7] for c in sorted(commits) if not sh("git", "branch", "-r", "--contains", c)]
    if unpushed:
        log(f"WARNUNG: Trainings-Commit(s) {', '.join(unpushed)} nicht auf origin — Sicherung verweist auf "
            "einen nur lokal vorhandenen Code-Stand (git push)")
    if os.environ.get("CONDA_DEFAULT_ENV") != "env_isaaclab":
        log("WARNUNG: Sicherung übersprungen — conda-Umgebung env_isaaclab nicht aktiv")
        return
    log_file = LOGS / "backup.log"
    with open(log_file, "w", encoding="utf-8") as out:
        rc = subprocess.run([str(ISAACLAB), "-p", "isaac_lab/backup_policies.py", "--upload"], cwd=REPO,
                            stdout=out, stderr=subprocess.STDOUT).returncode
    if rc == 0:
        log("Sicherung auf Hugging Face fertig")
    else:
        log(f"WARNUNG: Sicherung fehlgeschlagen ({log_file}) — wird beim nächsten done nachgeholt")


# ── Leaderboard: alle Policies (Experimente mit eigenem Training) unter festen Benchmark-Bedingungen ──

BENCHMARK = [   # Reihenfolge = Spalten; die erste ist die Sortierbedingung
    {"name": "zylinder_seitlich", "objekt_id": "zylinder_d6", "kurz": "Ø 6 cm", "anforderung": {"max_kipp_deg": 45}},
    {"name": "zylinder_d8_seitlich", "objekt_id": "zylinder_d8", "kurz": "Ø 8 cm", "anforderung": {"max_kipp_deg": 45}},
    {"name": "quader_seitlich", "objekt_id": "quader_7x7x20", "kurz": "Quader", "anforderung": {"max_kipp_deg": 45}},
]


# Testobjekte: nie im Training (Generalisierung) — nicht in Gesamt/Leistung, eigene Spalten/Zeile
TESTOBJEKTE = [
    {"name": "flasche_seitlich", "objekt_id": "flasche_d7x25", "kurz": "Flasche (Test)", "anforderung": {"max_kipp_deg": 45}},
    {"name": "saftpackung_seitlich", "objekt_id": "saftpackung_9x6x19", "kurz": "Saftpackung (Test)",
     "anforderung": {"max_kipp_deg": 45}},
]


def test_performance(exp: dict, rec: dict | None) -> list:
    """Median des Aufgabenerfolgs der erfolgreichen Seeds (aus dem Benchmark) je Testobjekt, None wenn nicht bewertet."""
    out = []
    for c in TESTOBJEKTE:
        r = aggregate(exp, c)
        if not r or not rec or not rec["k"]:
            out.append(None)
            continue
        ok = dict(zip(rec["seed_ids"], rec["erfolgreich"]))
        vals = [v for s, v in zip(r["seed_ids"], r["aufgabenerfolg"]["je_seed"]) if ok.get(s)]
        out.append(float(np.median(vals)) if vals else None)
    return out


def trained_experiments() -> list[tuple[Path, dict]]:
    out = []
    for d in sorted(EXP_DIR.glob("EXP-[0-9][0-9][0-9]_*")):
        exp = yaml.safe_load((d / "experiment.yaml").read_text(encoding="utf-8"))
        if (exp.get("training") is not None or exp.get("regel")) and exp.get("laeufe"):
            out.append((d, exp))
    return out


def pooled_iqm(results: list[dict], rng) -> dict | None:
    """IQM über alle Objekte (rliable, Agarwal et al. 2021): Erfolgsquoten aller Seeds × Objekte poolen,
    IQM davon; 95-%-KI per stratifiziertem Bootstrap (je Objekt Seeds und Episoden ziehen)."""
    if not results or not all(results) or len({tuple(r["seed_ids"]) for r in results}) != 1:
        return None      # nur vollständig bewertete Policies (gleiche Seeds an allen Objekten)
    return pooled_iqm_lists([r["_erfolg_je_seed"] for r in results], rng)


def pooled_iqm_lists(per_obj: list[list[np.ndarray]], rng) -> dict | None:
    """Wie pooled_iqm, direkt auf Erfolg je Episode: per_obj[Objekt][Seed] = Array."""
    if not per_obj or not all(per_obj):
        return None
    point = iqm([s.mean() for obj in per_obj for s in obj])
    boot = np.empty(BOOT)
    for b in range(BOOT):
        pooled = []
        for obj in per_obj:
            for s in rng.integers(0, len(obj), len(obj)):
                pooled.append(rng.choice(obj[s], len(obj[s])).mean())
        boot[b] = iqm(pooled)
    return {"iqm": point, "iqm_ki95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}


def prob_improvement(x: list[list[float]], y: list[list[float]], rng) -> dict:
    """P(X > Y) nach rliable (Agarwal et al. 2021): je Objekt Anteil der Lauf-Paare mit x > y (Gleichstand
    zählt ½), gemittelt über die Objekte; 95-%-KI per stratifiziertem Bootstrap der Läufe je Objekt.
    Gesichert besser, wenn die untere KI-Grenze > 0,5."""
    def p(xs, ys):
        return float(np.mean([np.mean([(a > b) + 0.5 * (a == b) for a in xo for b in yo]) for xo, yo in zip(xs, ys)]))
    boot = np.empty(BOOT)
    for b in range(BOOT):
        boot[b] = p([np.asarray(xo)[rng.integers(0, len(xo), len(xo))] for xo in x],
                    [np.asarray(yo)[rng.integers(0, len(yo), len(yo))] for yo in y])
    return {"p": p(x, y), "ki95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}


# ── Auswertung v2: Leistung und Zuverlässigkeit getrennt (Chan et al. 2020, Agarwal et al. 2021) ──────

AUSWERTUNG = "auswertung-v2"


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> list[float]:
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return [lo, hi]


def recipe(exp: dict, conds: list[dict] | None = None) -> dict | None:
    """Kennzahlen eines Rezepts über Bedingungen (Standard: Benchmark): Leistung = IQM des Aufgabenerfolgs der
    erfolgreichen Seeds (Mittel über die Objekte ≥ 50 %, README) über Seeds × Objekte; Zuverlässigkeit =
    erfolgreiche Seeds k/n (Clopper-Pearson-KI); Gesamt = IQM aller Seeds × Objekte (rliable)."""
    conds = conds or BENCHMARK
    res = [aggregate(exp, c) for c in conds]
    if not all(res) or len({tuple(r["seed_ids"]) for r in res}) != 1:
        return None
    M = np.array([r["aufgabenerfolg"]["je_seed"] for r in res])            # Objekte × Seeds
    ok = M.mean(axis=0) >= FAIL_BELOW
    rng = np.random.default_rng(0)
    k, n = int(ok.sum()), len(ok)
    return {"auswertung": AUSWERTUNG, "bedingungen": [c["name"] for c in conds],
            "kurz": [c.get("kurz", c["name"]) for c in conds], "seed_ids": res[0]["seed_ids"],
            "je_seed": M.tolist(), "erfolgreich": ok.tolist(), "k": k, "n": n,
            "zuverlaessigkeit_ki95": clopper_pearson(k, n),
            "leistung": pooled_iqm_lists([[s for s, o in zip(r["_erfolg_je_seed"], ok) if o] for r in res], rng) if k else None,
            "leistung_je_objekt": [float(np.median(M[i, ok])) if k else None for i in range(len(conds))],
            "gesamt": pooled_iqm_lists([r["_erfolg_je_seed"] for r in res], rng), "_res": res, "_M": M, "_ok": ok}


def compare_recipes(child: dict, parent: dict) -> dict:
    """Leistung: P(Kind > Eltern) über die erfolgreichen Seeds (rliable); Zuverlässigkeit: exakter Fisher-Test."""
    from scipy.stats import fisher_exact
    out = {}
    if child["k"] and parent["k"] and child["bedingungen"] == parent["bedingungen"]:
        pi = prob_improvement([child["_M"][i, child["_ok"]].tolist() for i in range(len(child["bedingungen"]))],
                              [parent["_M"][i, parent["_ok"]].tolist() for i in range(len(parent["bedingungen"]))],
                              np.random.default_rng(0))
        out["leistung_p"], out["leistung_ki95"] = pi["p"], pi["ki95"]
    out["fisher_p"] = float(fisher_exact([[child["k"], child["n"] - child["k"]],
                                          [parent["k"], parent["n"] - parent["k"]]])[1])
    out["zuverlaessigkeit_schlechter"] = out["fisher_p"] < 0.05 and child["k"] / child["n"] < parent["k"] / parent["n"]
    out["zuverlaessigkeit_besser"] = out["fisher_p"] < 0.05 and child["k"] / child["n"] > parent["k"] / parent["n"]
    return out


def verdict_v2(cmp: dict, violated: list[str]) -> str:
    lo, hi = cmp.get("leistung_ki95", [0, 1])
    if "leistung_p" in cmp and lo > 0.5 and not cmp["zuverlaessigkeit_schlechter"] and not violated:
        return "besser"
    if ("leistung_p" in cmp and hi < 0.5) or cmp["zuverlaessigkeit_schlechter"]:
        u = "schlechter"
    else:
        u = "kein Unterschied"
    return u + (", Leitplanke verletzt" if violated else "")


def failure_causes(d: Path, rec: dict) -> list[str]:
    """Ursache je gescheitertem Seed: hält gekippt (Haltequote ≥ 50 %), lernt nicht zu greifen (Gegengriff im
    Training ≈ 0) oder greift, verliert das Objekt."""
    tj = d / "diagramme" / "training.json"
    train = {s["seed"]: s["endwerte"] for s in json.loads(tj.read_text())["je_seed"]} if tj.exists() else {}
    main = rec["_res"][0]
    out = []
    for i, (s, ok) in enumerate(zip(rec["seed_ids"], rec["erfolgreich"])):
        if ok:
            continue
        if main["je_seed"][i]["haltequote"] >= 0.5:
            why = "hält, aber gekippt"
        elif train.get(s, {}).get("Episode_Reward/good_contact", 1.0) < 0.05:
            why = "lernt nicht zu greifen"
        else:
            why = "greift, verliert das Objekt"
        out.append(f"Seed {s} ({why})")
    return out


def best_seed(res: dict):
    """Bester Seed nach mittlerem Aufgabenerfolg über alle Benchmark-Objekte (Einsatz-Kandidat) oder None."""
    if not all(res.get(c["name"]) for c in BENCHMARK):
        return None, {}
    per = {c["name"]: dict(zip(res[c["name"]]["seed_ids"], res[c["name"]]["aufgabenerfolg"]["je_seed"])) for c in BENCHMARK}
    ids = res[BENCHMARK[0]["name"]]["seed_ids"]
    best = max(ids, key=lambda s: np.mean([per[c["name"]].get(s, 0) for c in BENCHMARK]))
    if max(per[c["name"]].get(best, 0) for c in BENCHMARK) == 0:
        return None, per          # Policy greift nie — kein Kandidat
    return best, per


def best_videos(d: Path, exp: dict) -> tuple[object, list[str]]:
    """Links zu den Videos des besten Seeds je Benchmark-Objekt: lang (3 Episoden, beste_videos/, im Git,
    von `medien` aufgenommen), sonst die kurze Aufnahme aus videos/."""
    best, _ = best_seed({c["name"]: aggregate(exp, c) for c in BENCHMARK})
    if exp.get("regel"):
        best = 0
    if best is None:
        return None, []
    links = []
    for c in BENCHMARK:
        name = f"{c['objekt_id']}_s{best}.mp4"
        for sub in ("beste_videos", "videos"):
            if (d / sub / name).exists():
                links.append(f"[{c['kurz']}]({sub}/{name})")
                break
    return best, links


def cmd_leaderboard(a):
    if a.bewerten:
        check_env()
        for d, exp in trained_experiments():
            for r in dict.fromkeys(exp["laeufe"]):
                rec = recipe(exp)
                todo = BENCHMARK + (TESTOBJEKTE if rec and rec["k"] else [])
                missing = [c for c in todo if not (REPO / r / f"{stem(exp, c)}.json").exists()]
                if missing:
                    log(f"  Benchmark {exp['id']} {Path(r).name}: {[c['name'] for c in missing]}")
                    with open(LOGS / f"benchmark_{Path(r).name}.log", "a", encoding="utf-8") as out:
                        for c in missing:
                            evaluate_condition(REPO / r, exp, c, False, out)
    write_leaderboard()
    if not a.kein_backup:
        backup()


def cmd_medien(a):
    """Je Policy, Seed und Benchmark-Objekt: Verlauf über die Episode (verlauf-v1_*.json im Laufordner,
    256 Episoden) und Video mit der aktuellen Kamera → experiments/EXP-NNN/videos/<objekt>_s<seed>.mp4.
    Vorhandenes bleibt (--neu: neu erzeugen); Bewertungsdateien werden nie überschrieben (--nur-medien)."""
    check_env()
    exps = [(d, e) for d, e in trained_experiments() if not a.ids or e["id"] in a.ids]
    tmp = LOGS / "_medien_tmp"
    for d, exp in exps:
        if a.beste:                 # nur die langen Videos des besten Seeds (neu)
            record_best_videos(d, exp, tmp, neu=True)
            report(exp["id"])
            continue
        vdir = d / "videos"
        vdir.mkdir(exist_ok=True)
        for r in dict.fromkeys(exp["laeufe"]):
            run = REPO / r
            m = re.search(r"_s(\d+)$", r)
            seed = m.group(1) if m else "0"
            policy = run / "exported" / "policy.pt"
            src = rule_args(exp) if exp.get("regel") else ["--policy", str(policy)]
            for c in BENCHMARK:
                base = [str(ISAACLAB), "-p", "isaac_lab/eval_policy.py", "--headless", "--nur-medien", *src,
                        "--objekt", c["objekt_id"], "--bedingung", c["name"],
                        "--max_kipp_deg", str(c["anforderung"]["max_kipp_deg"])]
                vstem = stem(exp, c).replace(exp["protokoll"], "verlauf-v1", 1)
                log_file = LOGS / f"medien_{Path(r).name}.log"
                with open(log_file, "a", encoding="utf-8") as out:
                  try:
                    if a.verlauf and (a.neu or not (run / f"{vstem}.json").exists()):
                        log(f"  Verlauf {exp['id']} s{seed} {c['kurz']}")
                        subprocess.run(base + ["--verlauf", "--num_envs", "256", "--episodes", "256", "--out", str(run)],
                                       cwd=REPO, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
                    target = vdir / f"{c['objekt_id']}_s{seed}.mp4"
                    if a.videos and (a.neu or not target.exists()):
                        log(f"  Video {exp['id']} s{seed} {c['kurz']}")
                        shutil.rmtree(tmp, ignore_errors=True)
                        subprocess.run(base + ["--num_envs", str(EVAL["video_umgebungen"]), "--episodes",
                                               str(EVAL["video_umgebungen"]), "--video", str(EVAL["video_schritte"]),
                                               "--out", str(tmp)], cwd=REPO, stdout=out, stderr=subprocess.STDOUT,
                                       timeout=1800)
                        found = sorted(tmp.rglob("*.mp4"))
                        if found:
                            shutil.move(str(found[0]), target)
                        else:
                            log(f"  WARNUNG: kein Video ({log_file})")
                  except subprocess.TimeoutExpired:
                    log(f"  WARNUNG: Zeitüberschreitung {exp['id']} s{seed} {c['kurz']} ({log_file})")
        if a.videos:
            record_best_videos(d, exp, tmp, neu=a.neu)
        report(exp["id"])
    shutil.rmtree(tmp, ignore_errors=True)
    cmd_done(a)


def record_best_videos(d: Path, exp: dict, tmp: Path, neu: bool = False):
    """Lange Videos (3 Episoden) des besten Seeds je Benchmark-Objekt → <experiment>/beste_videos/ (im Git);
    Videos anderer Seeds dort werden entfernt."""
    best, _ = best_seed({c["name"]: aggregate(exp, c) for c in BENCHMARK})
    if exp.get("regel"):
        best = 0                                             # ein Lauf, Label s0
    out = d / "beste_videos"
    keep = {f"{c['objekt_id']}_s{best}.mp4" for c in BENCHMARK} if best is not None else set()
    for old in out.glob("*.mp4") if out.exists() else []:
        if old.name not in keep:
            old.unlink()
    if best is None:
        return
    run = exp["laeufe"][0] if exp.get("regel") else next((r for r in exp["laeufe"] if r.endswith(f"_s{best}")), None)
    if run is None:
        return
    out.mkdir(exist_ok=True)
    for c in BENCHMARK:
        target = out / f"{c['objekt_id']}_s{best}.mp4"
        if target.exists() and not neu:
            continue
        log(f"  Bestes Video {exp['id']} s{best} {c['kurz']} (3 Episoden)")
        shutil.rmtree(tmp, ignore_errors=True)
        src = rule_args(exp) if exp.get("regel") else ["--policy", str(REPO / run / "exported" / "policy.pt")]
        cmd = [str(ISAACLAB), "-p", "isaac_lab/eval_policy.py", "--headless", "--nur-medien", *src,
               "--objekt", c["objekt_id"], "--bedingung", c["name"],
               "--max_kipp_deg", str(c["anforderung"]["max_kipp_deg"]), "--num_envs", str(EVAL["video_umgebungen"]),
               "--episodes", str(EVAL["video_umgebungen"]), "--video", str(EVAL["beste_video_schritte"]), "--out", str(tmp)]
        try:
            with open(LOGS / f"medien_beste_{exp['id']}.log", "a", encoding="utf-8") as f:
                subprocess.run(cmd, cwd=REPO, stdout=f, stderr=subprocess.STDOUT, timeout=1800)
        except subprocess.TimeoutExpired:
            log(f"  WARNUNG: Zeitüberschreitung bestes Video {exp['id']} {c['kurz']}")
        found = sorted(tmp.rglob("*.mp4"))
        if found:
            shutil.move(str(found[0]), target)
    shutil.rmtree(tmp, ignore_errors=True)


def vorschlag(d: Path, exp: dict, rec: dict) -> str:
    """Kurzer Urteilsvorschlag (Auswertung v2) aus results.json; ✓, wenn Leon ein Urteil bestätigt hat."""
    r = json.loads((d / "results.json").read_text()) if (d / "results.json").exists() else {}
    u = (r.get("rezept") or {}).get("urteil") or "–"
    return u + (" ✓" if "bestätigt" in str(exp.get("urteil") or "") else "")


def write_leaderboard():
    """Rangliste aller Policies (Auswertung v2): sortiert nach **Leistung** (IQM der erfolgreichen Seeds über die
    Benchmark-Objekte) — Ziel ist eine brauchbare Policy je Greifart, die Zuverlässigkeit ist zweitrangig (Leon,
    2026-10-08). Daneben Gesamt (alle Seeds, rliable) und Zuverlässigkeit."""
    pct = lambda x: "–" if x is None else f"{100 * x:.0f}"  # noqa: E731
    ci = lambda m: f"[{pct(m['iqm_ki95'][0])}–{pct(m['iqm_ki95'][1])}]" if m else ""  # noqa: E731
    rows = []
    for d, exp in trained_experiments():
        rec = recipe(exp)
        rows.append((d, exp, rec))
    rows.sort(key=lambda r: -(r[2]["leistung"]["iqm"] if r[2] and r[2]["leistung"] else -1))
    lead = rows[0][2] if rows and rows[0][2] else None
    rng = np.random.default_rng(0)
    L = ["# Leaderboard — Greif-Policies", "",
         f"Automatisch erzeugt ({AUSWERTUNG}). Benchmark: Protokoll eval-v1, Kippwinkel ≤ 45°, "
         + ", ".join(c["kurz"] for c in BENCHMARK) + ". Sortiert nach **Leistung** = IQM des Aufgabenerfolgs der "
         "erfolgreichen Seeds (Mittel über die Objekte ≥ 50 %) über Seeds × Objekte — Ziel ist eine brauchbare Policy je "
         "Greifart; je Objekt als Median; Testobjekte (nie trainiert) ebenso, nicht in der Leistung. **Gesamt** = IQM über "
         "alle Seeds (rliable). **Zuverlässigkeit** = erfolgreiche Seeds. **P(1 > X)**: Wahrscheinlichkeit, "
         "dass ein erfolgreicher Lauf von Platz 1 besser ist (gesichert, wenn die untere KI-Grenze > 0,5). ⚠: unter 5 "
         "Seeds oder unter 3 erfolgreichen — Leistung vorläufig. Werte in %, KI 95 %. "
         "Vorschlag = Urteilsregel v2 gegenüber den Eltern (✓: Leon hat das Experiment bewertet, Urteil im Bericht). "
         "Quellen: Agarwal et al. 2021 (rliable), Chan et al. 2020 (Zuverlässigkeit).", "",
         "| Rang | Experiment | Titel | Leistung [KI] | Gesamt [KI] | " + " | ".join(c["kurz"] for c in BENCHMARK)
         + " | " + " | ".join(c["kurz"] for c in TESTOBJEKTE)
         + " | erfolgreiche Seeds | Unruhe | P(1 > X) | Vorschlag (v2) | beste Videos |",
         "|---|---|---|---|---|" + "---|" * (len(BENCHMARK) + len(TESTOBJEKTE)) + "---|---|---|---|---|"]
    for i, (d, exp, rec) in enumerate(rows, 1):
        if not rec:
            L.append(f"| {i} | [{exp['id']}]({d.name}/bericht.md) | {exp.get('titel', '')} | nicht vollständig bewertet |"
                     + " |" * (len(BENCHMARK) + len(TESTOBJEKTE) + 7))
            continue
        tie = "–"
        if i > 1 and lead and lead["k"] and rec["k"]:       # über die erfolgreichen Seeds, passend zur Sortierung
            pi = prob_improvement([lead["_M"][j, lead["_ok"]].tolist() for j in range(len(BENCHMARK))],
                                  [rec["_M"][j, rec["_ok"]].tolist() for j in range(len(BENCHMARK))], rng)
            tie = f"{pi['p']:.2f} [{pi['ki95'][0]:.2f}–{pi['ki95'][1]:.2f}]" + (" gesichert" if pi["ki95"][0] > 0.5 else "")
        best, _ = best_seed({c["name"]: r for c, r in zip(BENCHMARK, rec["_res"])})
        if exp.get("regel"):
            best = 0
        vids = " ".join(f"[▶]({d.name}/beste_videos/{c['objekt_id']}_s{best}.mp4)" for c in BENCHMARK
                        if best is not None and (d / "beste_videos" / f"{c['objekt_id']}_s{best}.mp4").exists()) or "–"
        unruhe = rec["_res"][0]["leitplanken"].get("unruhe")
        warn = "" if rec["n"] >= 5 and rec["k"] >= 3 else " ⚠"
        L.append(f"| {i} | [{exp['id']}]({d.name}/bericht.md) | {exp.get('titel', '')} | "
                 + (f"**{pct(rec['leistung']['iqm'])}** {ci(rec['leistung'])}" if rec["leistung"] else "–") + " | "
                 f"{pct(rec['gesamt']['iqm'])} {ci(rec['gesamt'])} | "
                 + " | ".join(pct(v) for v in rec["leistung_je_objekt"]) + " | "
                 + " | ".join(pct(v) for v in test_performance(exp, rec)) + f" | {rec['k']}/{rec['n']}{warn} | "
                 f"{'–' if unruhe is None else f'{unruhe:.2f}'} | {tie} | {vorschlag(d, exp, rec)} | {vids} |")
    eins = ["| Experiment | bester Seed | " + " | ".join(c["kurz"] for c in BENCHMARK) + " | Actor-Parameter | Policy (ONNX) |",
            "|---|---|" + "---|" * len(BENCHMARK) + "---|---|"]
    for d, exp, rec in rows:
        if not rec:
            continue
        best, per = best_seed({c["name"]: r for c, r in zip(BENCHMARK, rec["_res"])})
        if best is None:
            continue
        run = next((r for r in exp["laeufe"] if r.endswith(f"_s{best}")), exp["laeufe"][0])
        n = rec["_res"][0].get("netz") or {}
        eins.append(f"| {exp['id']} | {best} | " + " | ".join(pct(per[c["name"]].get(best)) for c in BENCHMARK)
                    + f" | {n.get('actor_parameter') or '–'} | `{run}/exported/policy.onnx` |")
    L += [""] + _details(
        "Einsatz-Kandidaten (bester Seed je Policy — nach der Bewertung ausgewählt, daher optimistisch)", eins)
    (EXP_DIR / "leaderboard.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"leaderboard.md aktualisiert ({len(rows)} Policies)")


def _net_cell(n):
    return f"{n['actor']} {n['aktivierung']}, V{n['verlauf']}" if n else "–"


def _finger_cell(f):
    return f"{f['finger_mit_kontakt']:.1f}" if f and f.get("finger_mit_kontakt") is not None else "–"


def _budget_cell(n):
    return f"{n['iterationen']} × {n['umgebungen']}" if n else "–"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--eltern", required=True)
    n.add_argument("--kurz", required=True, help="Kurzname für den Ordner")
    n.add_argument("--titel", required=True)
    n.add_argument("--ohne-training", action="store_true", help="nur bewerten (Läufe der Eltern, z. B. Transfer)")
    b = sub.add_parser("bench")
    b.add_argument("--envs", type=int, nargs="+", default=[2048, 4096])
    b.add_argument("--iter", type=int, default=20)
    r = sub.add_parser("run")
    r.add_argument("ids", nargs="+")
    e = sub.add_parser("eval")
    e.add_argument("ids", nargs="+")
    e.add_argument("--video", action="store_true")
    e.add_argument("--neu", action="store_true", help="vorhandene Bewertungen neu rechnen (sonst nur fehlende)")
    bt = sub.add_parser("bericht")
    bt.add_argument("ids", nargs="+")
    md = sub.add_parser("medien")
    md.add_argument("ids", nargs="*", help="Experimente (leer: alle Policies)")
    md.add_argument("--videos", action="store_true")
    md.add_argument("--verlauf", action="store_true")
    md.add_argument("--neu", action="store_true")
    md.add_argument("--beste", action="store_true", help="nur die langen Videos des besten Seeds (neu aufnehmen)")
    lb = sub.add_parser("leaderboard")
    lb.add_argument("--bewerten", action="store_true", help="fehlende Benchmark-Bewertungen nachholen")
    d = sub.add_parser("done")
    for s in (r, e, bt, md, lb, d):
        s.add_argument("--kein-backup", action="store_true", help="nicht nach Hugging Face sichern")
    a = p.parse_args()
    {"new": cmd_new, "bench": cmd_bench, "run": cmd_run, "eval": cmd_eval, "bericht": cmd_bericht, "leaderboard": cmd_leaderboard, "medien": cmd_medien, "done": cmd_done}[a.cmd](a)


if __name__ == "__main__":
    main()
