"""
experiments.py — Experimente planen, ausführen, bewerten, vergleichen (experiments/README.md).

Läuft mit System-Python (PyYAML, numpy), Isaac Lab nur als Unterprozess über isaaclab.sh —
die conda-Umgebung env_isaaclab muss aktiv sein (isaaclab.sh nimmt deren Python).

  /usr/bin/python3 isaac_lab/experiments.py new  --eltern EXP-001 --kurz name --titel "..."
  /usr/bin/python3 isaac_lab/experiments.py bench --envs 2048 4096      # Durchsatz → umgebungen: auto
  /usr/bin/python3 isaac_lab/experiments.py run  EXP-001 [EXP-002 ...]  # Kurztest, Training, Bewertung, Bericht
  /usr/bin/python3 isaac_lab/experiments.py eval EXP-000                # nur (neu) bewerten + Bericht
  /usr/bin/python3 isaac_lab/experiments.py done                        # index.md neu erzeugen

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
EVAL = {"umgebungen": 256, "episoden": 1000, "video_umgebungen": 16, "video_schritte": 300}
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
        if k.split(".")[-1] in _DIFF_IGNORE:
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
        pattern = re.compile(rf"^{key}:.*?(?=^\S|\Z)", re.M | re.S)
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
    save_fields(d, id=new_id, titel=a.titel, datum=f"{dt.date.today()}", eltern=a.eltern,
                bedingungen=parent["bedingungen"], training=parent["training"], protokoll=parent["protokoll"])
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
            if time.time() - start > 8 * 3600:
                log("  Abbruch: über 8 h")
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


def evaluate(run_dir: Path, exp: dict, video: bool, log_file: Path) -> dict | None:
    req = exp["bedingungen"][0]["anforderung"].get("max_kipp_deg")
    # Regel: immer der LETZTE Checkpoint, nie der beste nach Bewertung (sonst Auswahl-Verzerrung)
    ckpts = sorted(run_dir.glob("model_*.pt"), key=lambda p: int(p.stem.split("_")[1]))
    exported = run_dir / "exported" / "policy.pt"
    # Export aktueller als der letzte Checkpoint → Export nehmen (z. B. EXP-000: Critic-Eingang
    # hat sich seitdem geändert, der Checkpoint lädt nicht mehr, der Actor schon)
    if exported.exists() and (not ckpts or exported.stat().st_mtime >= ckpts[-1].stat().st_mtime):
        src = ["--policy", str(exported)]
    else:
        src = ["--checkpoint", str(ckpts[-1])]
    base = [str(ISAACLAB), "-p", "isaac_lab/eval_policy.py", "--headless", "--max_kipp_deg", str(req if req is not None else -1)]
    with open(log_file, "w", encoding="utf-8") as out:
        subprocess.run(base + src + ["--num_envs", str(EVAL["umgebungen"]), "--episodes", str(EVAL["episoden"]),
                                     "--out", str(run_dir)], cwd=REPO, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
        if video:
            subprocess.run(base + ["--policy", str(run_dir / "exported" / "policy.pt"),
                                   "--num_envs", str(EVAL["video_umgebungen"]), "--episodes", str(EVAL["video_umgebungen"]),
                                   "--video", str(EVAL["video_schritte"]), "--out", str(run_dir / "video_eval")],
                           cwd=REPO, stdout=out, stderr=subprocess.STDOUT, timeout=1800)
    p = run_dir / f"{exp['protokoll']}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ── Statistik ─────────────────────────────────────────────────────────────────

def boot_means(per_seed: list[np.ndarray], rng) -> np.ndarray:
    """Zweistufiger Bootstrap: Seeds ziehen, darin Episoden ziehen → BOOT Mittelwerte."""
    k = len(per_seed)
    out = np.empty(BOOT)
    for b in range(BOOT):
        seeds = rng.integers(0, k, k)
        out[b] = np.mean([rng.choice(per_seed[s], len(per_seed[s])).mean() for s in seeds])
    return out


def aggregate(exp_dir: Path, exp: dict) -> dict:
    evals = []
    for r in exp.get("laeufe") or []:
        p = REPO / r / f"{exp['protokoll']}.json"
        if p.exists():
            evals.append(json.loads(p.read_text()))
    if not evals:
        return {}
    rng = np.random.default_rng(0)
    res = {"protokoll": evals[0]["protokoll"], "seeds": len(evals), "laeufe": exp.get("laeufe"),
           "bedingung": exp["bedingungen"][0]["name"], "je_seed": [e["zusammenfassung"] for e in evals]}
    for key, field in (("aufgabenerfolg", "erfolg_je_episode"), ("haltequote", "gehalten_je_episode")):
        per_seed = [np.array(e[field], float) for e in evals]
        bm = boot_means(per_seed, rng)
        res[key] = {"mittel": float(np.mean([s.mean() for s in per_seed])),
                    "ki95": [float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))], "_boot": bm}
    first = REPO / exp["laeufe"][0]
    res["netz"] = net_profile(load_params(first), evals[0])
    res["_params"] = load_params(first)
    res["leitplanken"] = {g[0]: _mean([e["zusammenfassung"]["leitplanken"].get(g[0]) for e in evals]) for g in GUARDRAILS}
    res["fehler"] = {k: _mean([e["zusammenfassung"]["fehler"][k] for e in evals]) for k in evals[0]["zusammenfassung"]["fehler"]}
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


def report(exp_id: str):
    d, exp = load(exp_id)
    res = aggregate(d, exp)
    if not res:
        log(f"{exp_id}: keine Bewertungen gefunden")
        return
    parent_res = {}
    if exp.get("eltern"):
        pd, pexp = load(exp["eltern"])
        parent_res = aggregate(pd, pexp)
    res["vergleich"] = verdict(res, parent_res)
    res["konfig_unterschiede"] = config_diff(res["_params"], parent_res["_params"]) if parent_res else []
    clean = {k: ({kk: vv for kk, vv in v.items() if kk != "_boot"} if isinstance(v, dict) else v)
             for k, v in res.items() if k != "_params"}
    (d / "results.json").write_text(json.dumps(clean, indent=1, ensure_ascii=False), encoding="utf-8")
    pct = lambda x: "–" if x is None else f"{100 * x:.1f} %"  # noqa: E731
    v = res["vergleich"]
    lines = [f"# {exp_id}: {exp.get('titel', '')}", "",
             f"Bedingung `{res['bedingung']}`, Protokoll {res['protokoll']}, {res['seeds']} Seed(s)", "",
             "| Metrik | Wert | 95-%-KI | Eltern |", "|---|---|---|---|"]
    for key in ("aufgabenerfolg", "haltequote"):
        pv = pct(parent_res[key]["mittel"]) if parent_res else "–"
        lines.append(f"| {key} | {pct(res[key]['mittel'])} | {pct(res[key]['ki95'][0])} – {pct(res[key]['ki95'][1])} | {pv} |")
    for key, label, _, kind in GUARDRAILS:
        c = res["leitplanken"].get(key)
        p = parent_res.get("leitplanken", {}).get(key) if parent_res else None
        f = (lambda x: "–" if x is None else (pct(x) if "anteil" in key else f"{x:.3g}"))
        lines.append(f"| {label} | {f(c)} | | {f(p)} |")
    lines += ["", "Fehlerarten: " + ", ".join(f"{k} {pct(x)}" for k, x in res["fehler"].items()), "",
              f"**Urteilsvorschlag: {v['urteil']}**"]
    if "differenz_ki95" in v:
        lines.append(f"Unterschied Aufgabenerfolg {100 * v['differenz_aufgabenerfolg']:+.1f} Prozentpunkte "
                     f"(95-%-KI {100 * v['differenz_ki95'][0]:+.1f} … {100 * v['differenz_ki95'][1]:+.1f})")
    for x in v.get("leitplanken_verletzt", []):
        lines.append(f"- Leitplanke: {x}")
    lines += ["", "Je Seed: " + ", ".join(f"{pct(s['aufgabenerfolg'])}" for s in res["je_seed"])]
    n = res["netz"]
    lines += ["", "## Netz und Training", "",
              f"Actor {n['actor']} ({n['aktivierung']}), {n['actor_parameter']} Parameter, {n['eingaenge']} Eingänge "
              f"(Verlauf {n['verlauf']}) · Critic {n['critic']} · PPO: Lernrate {n['lernrate']}, Entropie {n['entropie']}, "
              f"{n['epochen']} Epochen × {n['mini_batches']} Mini-Batches, {n['schritte_je_umgebung']} Schritte/Umgebung · "
              f"{n['umgebungen']} Umgebungen × {n['iterationen']} Iterationen"]
    if parent_res:
        diffs = res["konfig_unterschiede"]
        lines += ["", f"## Konfiguration gegenüber {exp['eltern']} ({len(diffs)} Unterschiede)", "",
                  f"Geplante Änderung: {exp.get('aenderung', '')}", ""]
        lines += [f"- `{x}`" for x in diffs[:80]] or ["- keine"]
        if len(diffs) > 80:
            lines.append(f"- … {len(diffs) - 80} weitere (results.json)")
    (d / "bericht.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"{exp_id}: Aufgabenerfolg {pct(res['aufgabenerfolg']['mittel'])}, Haltequote "
        f"{pct(res['haltequote']['mittel'])} → {v['urteil']}")


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
        envs = t["umgebungen"]
        if envs == "auto":
            envs = json.loads(BENCH.read_text())["beste"] if BENCH.exists() else 1024
        log(f"== {exp_id}: {exp.get('titel')} ({envs} Umgebungen, {t['iterationen']} Iterationen, Seeds {t['seeds']})")
        commit = sh("git", "rev-parse", "--short", "HEAD") + ("+lokal" if sh("git", "status", "--porcelain") else "")
        save_fields(d, status="läuft", commit=commit)
        if not smoke(exp_id, t):
            log(f"{exp_id}: Kurztest fehlgeschlagen — übersprungen ({LOGS / (exp_id + '_smoke.log')})")
            save_fields(d, status="fehlgeschlagen (Kurztest)")
            continue
        runs = []
        for i, seed in enumerate(t["seeds"]):
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
            if evaluate(run_dir, exp, video=(i == 0), log_file=LOGS / f"{name}_eval.log") is None:
                log(f"  Bewertung {name} fehlgeschlagen ({LOGS / (name + '_eval.log')})")
        save_fields(d, status="trainiert")
        report(exp_id)
    cmd_done(a)


def cmd_eval(a):
    check_env()
    for exp_id in a.ids:
        d, exp = load(exp_id)
        for r in exp.get("laeufe") or []:
            log(f"  Bewertung {exp_id}: {r}")
            evaluate(REPO / r, exp, video=a.video, log_file=LOGS / f"{exp_id}_{Path(r).name}_eval.log")
        report(exp_id)
    cmd_done(a)


def cmd_done(a):
    pct = lambda x: "–" if x is None else f"{100 * x:.1f}"  # noqa: E731
    rows = ["# Experimente — Übersicht", "", "Automatisch erzeugt (`experiments.py done`). Aufgabenerfolg/Haltequote "
            "in %, [95-%-KI]; Leitplanken Mittel über Seeds. Definitionen: README.md.", "",
            "| ID | Titel | Eltern | Bedingung | Seeds | Netz (Actor) | Param. | Iter. × Umg. | Aufgabenerfolg | Haltequote | Kipp° | Unterarm° | Stall | Vorschlag | Urteil (bestätigt) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in sorted(EXP_DIR.glob("EXP-[0-9][0-9][0-9]_*")):
        exp = yaml.safe_load((d / "experiment.yaml").read_text(encoding="utf-8"))
        r = json.loads((d / "results.json").read_text()) if (d / "results.json").exists() else {}
        ae, hq, lp = r.get("aufgabenerfolg"), r.get("haltequote"), r.get("leitplanken", {})
        f = lambda m: f"{pct(m['mittel'])} [{pct(m['ki95'][0])}–{pct(m['ki95'][1])}]" if m else "–"  # noqa: E731
        g = lambda x: "–" if x is None else f"{x:.0f}"  # noqa: E731
        rows.append(f"| [{exp['id']}]({d.name}/experiment.yaml) | {exp.get('titel', '')} | {exp.get('eltern') or '–'} | "
                    f"{exp['bedingungen'][0]['name']} | {r.get('seeds', '–')} | "
                    f"{_net_cell(r.get('netz'))} | {(r.get('netz') or {}).get('actor_parameter') or '–'} | "
                    f"{_budget_cell(r.get('netz'))} | {f(ae)} | {f(hq)} | "
                    f"{g(lp.get('kipp_median_deg'))} | {g(lp.get('unterarm_median_deg'))} | {pct(lp.get('stall_anteil'))} | "
                    f"{r.get('vergleich', {}).get('urteil', '–')} | {exp.get('urteil') or '–'} |")
    (EXP_DIR / "index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    log(f"index.md aktualisiert ({len(rows) - 6} Experimente)")


def _net_cell(n):
    return f"{n['actor']} {n['aktivierung']}, V{n['verlauf']}" if n else "–"


def _budget_cell(n):
    return f"{n['iterationen']} × {n['umgebungen']}" if n else "–"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--eltern", required=True)
    n.add_argument("--kurz", required=True, help="Kurzname für den Ordner")
    n.add_argument("--titel", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--envs", type=int, nargs="+", default=[2048, 4096])
    b.add_argument("--iter", type=int, default=20)
    r = sub.add_parser("run")
    r.add_argument("ids", nargs="+")
    e = sub.add_parser("eval")
    e.add_argument("ids", nargs="+")
    e.add_argument("--video", action="store_true")
    sub.add_parser("done")
    a = p.parse_args()
    {"new": cmd_new, "bench": cmd_bench, "run": cmd_run, "eval": cmd_eval, "done": cmd_done}[a.cmd](a)


if __name__ == "__main__":
    main()
