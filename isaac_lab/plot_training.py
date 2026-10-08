"""
plot_training.py — Trainingsdiagramme eines Experiments aus den TensorBoard-Logs (rsl_rl).

Liest events.out.tfevents.* aller Seeds und schreibt nach <experiment>/diagramme/:
  lernkurve.svg    Train/mean_reward, Train/mean_episode_length
  belohnung.svg    Episode_Reward/* (Belohnung je Sekunde Episode, wie Isaac Lab sie loggt)
  abbrueche.svg    Episode_Termination/* (Anteil der Episoden je Abbruchgrund)
  ppo.svg          Value-/Surrogate-Loss, Entropie, Rausch-Std, Lernrate
  training.json    Endwerte je Seed (Mittel der letzten 10 Iterationen, ungeglättet)
  bedingungen.svg  mit --bedingungen <results.json>: Ergebnis je Bedingung (Objekt) — Aufgabenerfolg,
                   Finger am Objekt, Kippwinkel je Seed, dazu Mittel (und 95-%-KI beim Aufgabenerfolg)
  verlauf.svg      mit --verlauf-laeufe/--verlauf-bedingungen: Verlauf über die Episode je Objekt (Mittel über
                   Seeds und laufende Episoden): Objekthöhe ggü. Start, Kippwinkel, Finger am Objekt, Griffkraft
Seeds dünn (Farbe fest je Seed), Mittel über die Seeds kräftig; Eltern (Mittel, gestrichelt) nur
bei Abbrüchen und PPO — die Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar
(ADR-016). x-Achse: Simulationsschritte (Iteration × Umgebungen × Schritte je Umgebung).

Aufgerufen von experiments.py (report) über isaaclab.sh -p — braucht tensorboard + matplotlib
aus env_isaaclab, keine Simulation:
  ~/IsaacLab/isaaclab.sh -p isaac_lab/plot_training.py --exp-dir experiments/EXP-004_... \
      --runs <laufordner> ... [--eltern-runs <laufordner> ...] [--eltern-name EXP-000]
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
MAX_POINTS = 400     # Punkte je Linie in der SVG (nach dem Glätten)
TAIL = 10            # Iterationen für die Endwerte
# Farben (Kategorie-Palette der dataviz-Referenz, feste Reihenfolge): Farbe folgt dem Seed
SEED_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
STANDARD_SEEDS = [42, 43, 44, 45, 46]
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

FIGURES = {
    "lernkurve": ("Lernkurve", ["Train/mean_reward", "Train/mean_episode_length"], False),
    "belohnung": ("Belohnungsanteile (je Sekunde Episode)", "Episode_Reward/", False),
    "abbrueche": ("Abbrüche (Anteil der Episoden)", "Episode_Termination/", True),
    "ppo": ("PPO-Diagnose", ["Loss/value_function", "Loss/surrogate", "Loss/entropy",
                             "Policy/mean_noise_std", "Loss/learning_rate"], True),
}
LABELS = {"Train/mean_reward": "Belohnung je Episode", "Train/mean_episode_length": "Episodenlänge [Schritte]",
          "Loss/value_function": "Value-Loss", "Loss/surrogate": "Surrogate-Loss", "Loss/entropy": "Entropie",
          "Policy/mean_noise_std": "Rausch-Std (Aktion)", "Loss/learning_rate": "Lernrate"}


def load_run(run_dir: Path) -> dict:
    files = sorted(run_dir.glob("events.out.tfevents.*"))
    if not files:
        return {}
    params = yaml.safe_load((run_dir / "params" / "agent.yaml").read_text(encoding="utf-8"))
    env = yaml.load((run_dir / "params" / "env.yaml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    steps_per_iter = int(env["scene"]["num_envs"]) * int(params["num_steps_per_env"])
    scalars = {}
    for f in files:
        ea = EventAccumulator(str(f), size_guidance={"scalars": 0})
        ea.Reload()
        for tag in ea.Tags()["scalars"]:
            if tag.endswith("/time") or tag.startswith("Perf/"):
                continue
            ev = ea.Scalars(tag)
            scalars[tag] = (np.array([e.step for e in ev]), np.array([e.value for e in ev], dtype=float))
    return {"seed": params.get("seed"), "steps_per_iter": steps_per_iter, "scalars": scalars, "name": run_dir.name}


def smooth(y: np.ndarray) -> np.ndarray:
    """Exponentielles Mittel (wie TensorBoard, mit Bias-Korrektur), Spanne ~ n/50."""
    span = max(3, len(y) // 50)
    alpha = 2 / (span + 1)
    out, acc, w = np.empty_like(y), 0.0, 0.0
    for i, v in enumerate(y):
        acc = (1 - alpha) * acc + alpha * v
        w = (1 - alpha) * w + alpha
        out[i] = acc / w
    return out


def thin(x, y):
    if len(x) <= MAX_POINTS:
        return x, y
    idx = np.unique(np.linspace(0, len(x) - 1, MAX_POINTS).round().astype(int))
    return x[idx], y[idx]


def curve(run: dict, tag: str):
    if tag not in run["scalars"]:
        return None
    it, y = run["scalars"][tag]
    return (it + 1) * run["steps_per_iter"] / 1e6, smooth(y)


def mean_curve(runs: list[dict], tag: str):
    cs = [c for c in (curve(r, tag) for r in runs) if c is not None]
    if not cs:
        return None
    n = min(len(c[0]) for c in cs)
    return cs[0][0][:n], np.mean([c[1][:n] for c in cs], axis=0)


def seed_color(seed, seeds: list) -> str:
    if seed is None:                       # Lauf ohne Seed im Namen (EXP-000)
        return SEED_COLORS[0]
    if seed in STANDARD_SEEDS:
        return SEED_COLORS[STANDARD_SEEDS.index(seed)]
    extra = [s for s in seeds if s not in STANDARD_SEEDS]
    return SEED_COLORS[(len(STANDARD_SEEDS) + extra.index(seed)) % len(SEED_COLORS)]


def style_axis(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelcolor=INK2, labelsize=8)


def plot_figure(out: Path, title: str, tags: list[str], runs: list[dict], parent: list[dict], parent_name: str,
                percent: bool, exp_name: str):
    cols = 2 if len(tags) <= 4 else 3
    rows = int(np.ceil(len(tags) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.2 * cols, 2.6 * rows + 0.9), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    seeds = [r["seed"] for r in runs]
    handles = {}
    for ax, tag in zip(axes.flat, tags):
        style_axis(ax)
        scale = 100 if percent else 1
        for r in runs:
            c = curve(r, tag)
            if c is not None:
                x, y = thin(c[0], c[1] * scale)
                h, = ax.plot(x, y, color=seed_color(r["seed"], seeds), linewidth=1.2, alpha=0.9,
                             solid_capstyle="round", solid_joinstyle="round")
                handles.setdefault(f"Seed {r['seed']}", h)
        m = mean_curve(runs, tag)
        if m is not None and len(runs) > 1:
            x, y = thin(m[0], m[1] * scale)
            handles.setdefault(f"Mittel {exp_name}", ax.plot(x, y, color=INK, linewidth=2.2,
                                                             solid_capstyle="round")[0])
        pm = mean_curve(parent, tag) if parent else None
        if pm is not None:
            x, y = thin(pm[0], pm[1] * scale)
            handles.setdefault(f"Mittel {parent_name} (Eltern)", ax.plot(x, y, color=MUTED, linewidth=1.8,
                                                                          linestyle=(0, (4, 2)))[0])
        name = LABELS.get(tag, tag.split("/", 1)[1])
        ax.set_title(name + (" [%]" if percent else ""), fontsize=9.5, color=INK, loc="left")
        ax.set_xlabel("Simulationsschritte [Mio.]", fontsize=8, color=INK2)
        if tag == "Loss/learning_rate":
            ax.set_yscale("log")
    for ax in list(axes.flat)[len(tags):]:
        ax.set_visible(False)
    fig.suptitle(f"{exp_name}: {title}", x=0.01, ha="left", fontsize=11, color=INK)
    fig.legend(handles.values(), handles.keys(), loc="upper left", ncol=len(handles), fontsize=8,
               frameon=False, labelcolor=INK2, bbox_to_anchor=(0.0, 1 - 0.32 / fig.get_figheight()),
               handlelength=1.8, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.5 / fig.get_figheight()), pad=0.6)
    fig.savefig(out, format="svg", facecolor=SURFACE, metadata={"Date": None})
    plt.close(fig)


def plot_conditions(out: Path, results: dict, exp_name: str):
    """Ergebnis je Bedingung: Seeds als Punkte (links im Feld), Mittel als Strich + 95-%-KI (rechts)."""
    conds = (list(results["benchmark"].values()) if results.get("benchmark")
             else [results] + list((results.get("weitere_bedingungen") or {}).values()))
    seeds = sorted({s for c in conds for s in c.get("seed_ids") or [] if s is not None})
    panels = [("Aufgabenerfolg [%]", lambda c, i: 100 * c["aufgabenerfolg"]["je_seed"][i], (0, 100)),
              ("Finger am Objekt (Haltephase)",
               lambda c, i: ((c["je_seed"][i].get("fingernutzung") or {}).get("finger_mit_kontakt")), (0, 5)),
              ("Kippwinkel Median [°] (gehalten)",
               lambda c, i: c["je_seed"][i]["leitplanken"].get("kipp_median_deg"), (0, None))]
    fig, axes = plt.subplots(1, 3, figsize=(4.0 * 3, 3.6))
    fig.patch.set_facecolor(SURFACE)
    handles = {}
    offsets = np.linspace(-0.30, -0.06, max(len(seeds), 1))
    for ax, (title, value, ylim) in zip(axes, panels):
        style_axis(ax)
        for x, c in enumerate(conds):
            vals = []
            for i, s in enumerate(c.get("seed_ids") or []):
                v = value(c, i)
                if v is None:
                    continue
                vals.append(v)
                k = seeds.index(s) if s in seeds else 0
                h = ax.scatter(x + offsets[k], v, s=42, color=seed_color(s, seeds), edgecolors=SURFACE,
                               linewidths=1.5, zorder=3)
                handles.setdefault(f"Seed {s}", h)
            if not vals:
                continue
            m = c["aufgabenerfolg"]["mittel"] * 100 if title.startswith("Aufgabe") else float(np.mean(vals))
            h, = ax.plot([x + 0.06, x + 0.30], [m, m], color=INK, linewidth=2.4, solid_capstyle="round", zorder=4)
            handles.setdefault("Mittel", h)
            if title.startswith("Aufgabe"):
                lo, hi = (100 * v for v in c["aufgabenerfolg"]["ki95"])
                h, = ax.plot([x + 0.18, x + 0.18], [lo, hi], color=INK2, linewidth=1.2, zorder=2)
                handles.setdefault("95-%-KI (Bootstrap)", h)
                ax.annotate(f"{m:.0f} %", (x + 0.33, m), fontsize=8, color=INK, va="center")
        req = conds[0].get("anforderung_max_kipp_deg")
        if title.startswith("Kipp") and req is not None:
            ax.axhline(req, color=MUTED, linewidth=1.0, linestyle=(0, (3, 2)), zorder=1)
            ax.annotate(f"Anforderung ≤ {req}°", (len(conds) - 0.5, req), fontsize=7.5, color=INK2,
                        ha="right", va="bottom")
        ax.set_xticks(range(len(conds)))
        ax.set_xticklabels([f"{c['bedingung']}\n{c.get('objekt', '')}" for c in conds], fontsize=7.5, color=INK2)
        ax.set_xlim(-0.5, len(conds) - 0.5)
        ax.set_ylim(ylim[0], ylim[1] if ylim[1] is not None else None)
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
        ax.grid(False, axis="x")
    fig.suptitle(f"{exp_name}: Ergebnis je Bedingung (Punkte = Seeds)", x=0.01, ha="left", fontsize=11, color=INK)
    fig.legend(handles.values(), handles.keys(), loc="upper left", ncol=len(handles), fontsize=8,
               frameon=False, labelcolor=INK2, bbox_to_anchor=(0.0, 1 - 0.32 / fig.get_figheight()),
               handlelength=1.8, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.5 / fig.get_figheight()), pad=0.6)
    fig.savefig(out, format="svg", facecolor=SURFACE, metadata={"Date": None})
    plt.close(fig)


def plot_trace(out: Path, runs: list[str], conds: list[tuple[str, str]], exp_name: str):
    """Verlauf über die Episode: je Objekt eine Linie (Mittel über die Seeds), Absenken markiert."""
    panels = [("hoehe_mm", "Objekthöhe ggü. Start [mm]"), ("kipp_deg", "Kippwinkel [°]"),
              ("finger", "Finger am Objekt (> 1 N)"), ("kraft_n", "Griffkraft, Summe FSR [N]")]
    fig, axes = plt.subplots(2, 2, figsize=(4.2 * 2, 2.6 * 2 + 0.9), squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    handles, marks = {}, None
    for j, (stem, kurz) in enumerate(conds):
        data = [json.loads((REPO / r / f"{stem}.json").read_text()) for r in runs if (REPO / r / f"{stem}.json").exists()]
        if not data:
            continue
        n = min(len(v["t_s"]) for v in data)
        t = np.array(data[0]["t_s"][:n])
        marks = data[0]["absenken_s"]
        for ax, (key, title) in zip(axes.flat, panels):
            y = np.mean([v[key][:n] for v in data], axis=0)
            h, = ax.plot(t, y, color=SEED_COLORS[j], linewidth=2.0, solid_capstyle="round")
            handles.setdefault(f"{kurz} ({len(data)} Seeds)", h)
    for ax, (key, title) in zip(axes.flat, panels):
        style_axis(ax)
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
        ax.set_xlabel("Zeit [s]", fontsize=8, color=INK2)
        if marks:
            ax.axvspan(marks[0], marks[1], color=GRID, alpha=0.6, linewidth=0)
        if key == "hoehe_mm":
            ax.axhline(0, color=AXIS, linewidth=1.0)
    if marks:
        axes[0, 0].annotate("Tisch senkt sich", (marks[1], 0), xytext=(4, 6), textcoords="offset points",
                            fontsize=7.5, color=INK2)
    fig.suptitle(f"{exp_name}: Verlauf über die Episode (Mittel über Seeds und laufende Episoden)", x=0.01,
                 ha="left", fontsize=11, color=INK)
    fig.legend(handles.values(), handles.keys(), loc="upper left", ncol=max(len(handles), 1), fontsize=8,
               frameon=False, labelcolor=INK2, bbox_to_anchor=(0.0, 1 - 0.32 / fig.get_figheight()),
               handlelength=1.8, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.5 / fig.get_figheight()), pad=0.6)
    fig.savefig(out, format="svg", facecolor=SURFACE, metadata={"Date": None})
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exp-dir", required=True)
    ap.add_argument("--runs", nargs="*", default=[])
    ap.add_argument("--bedingungen", default=None, help="results.json → bedingungen.svg")
    ap.add_argument("--verlauf-laeufe", nargs="*", default=[])
    ap.add_argument("--verlauf-bedingungen", nargs="*", default=[], help="<dateistamm>=<Kurzname> je Objekt")
    ap.add_argument("--eltern-runs", nargs="*", default=[])
    ap.add_argument("--eltern-name", default="")
    a = ap.parse_args()
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "pib-hand-sim",
                         "font.family": "DejaVu Sans"})

    exp_dir = REPO / a.exp_dir
    exp_name = exp_dir.name.split("_")[0]
    (exp_dir / "diagramme").mkdir(exist_ok=True)
    if a.bedingungen:
        plot_conditions(exp_dir / "diagramme" / "bedingungen.svg", json.loads((REPO / a.bedingungen).read_text()), exp_name)
        print(f"Diagramm: {exp_dir / 'diagramme' / 'bedingungen.svg'}")
    if a.verlauf_laeufe and a.verlauf_bedingungen:
        conds = [tuple(s.split("=", 1)) for s in a.verlauf_bedingungen]
        plot_trace(exp_dir / "diagramme" / "verlauf.svg", a.verlauf_laeufe, conds, exp_name)
        print(f"Diagramm: {exp_dir / 'diagramme' / 'verlauf.svg'}")
    if not a.runs:
        return
    runs = [r for r in (load_run(REPO / p) for p in a.runs) if r]
    parent = [r for r in (load_run(REPO / p) for p in a.eltern_runs) if r]
    if not runs:
        raise SystemExit("keine TensorBoard-Logs gefunden")
    runs.sort(key=lambda r: (r["seed"] is None, r["seed"]))
    out_dir = exp_dir / "diagramme"
    out_dir.mkdir(exist_ok=True)

    all_tags = sorted({t for r in runs for t in r["scalars"]})
    for key, (title, sel, with_parent) in FIGURES.items():
        tags = [t for t in all_tags if t.startswith(sel)] if isinstance(sel, str) else [t for t in sel if t in all_tags]
        if tags:
            plot_figure(out_dir / f"{key}.svg", title, tags, runs, parent if with_parent else [],
                        a.eltern_name, key == "abbrueche", exp_name)

    summary = {"tail_iterationen": TAIL, "je_seed": [
        {"seed": r["seed"], "lauf": r["name"], "iterationen": int(max(len(v[0]) for v in r["scalars"].values())),
         "simulationsschritte_mio": round(max(len(v[0]) for v in r["scalars"].values()) * r["steps_per_iter"] / 1e6, 1),
         "endwerte": {t: float(np.mean(v[1][-TAIL:])) for t, v in sorted(r["scalars"].items())}}
        for r in runs]}
    (out_dir / "training.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Diagramme: {out_dir} ({len(runs)} Läufe, Eltern {len(parent)})")


if __name__ == "__main__":
    main()
