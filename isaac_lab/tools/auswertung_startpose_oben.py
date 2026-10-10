"""
auswertung_startpose_oben.py — Startpose „von oben“ über alle Objekte auswählen (nach tools/suche_startpose_oben.py).

Je Objekt und Kombination (Kippung, Rollen, Rotator, Höhe, Versatz) über die Wiederholungen: gehalten, sauberer Start (kein
Kontakt Hand↔Objekt > 0,5 N in 0,1 s, kein Hand↔Tisch vor dem Schließen), Tischkontakt beim Schließen, Handfläche, Finger.
Eine Pose (Kippung, Rollen, Rotator, Versatz) gilt für alle Objekte, die Höhe darf je Objekt verschieden sein (Leon: Höhe je
Objekt): je Objekt die beste saubere Höhe; Rangfolge der Posen nach dem Mittel über die Benchmark-Objekte, dann dem
schwächsten Objekt. Ausgabe: docs/startpose-oben/ (ergebnis.md, Diagramme) — Empfehlung, umgestellt wird von Hand.

  conda activate env_isaaclab && python isaac_lab/tools/auswertung_startpose_oben.py
"""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "logs" / "startpose_oben"
OUT = REPO / "docs" / "startpose-oben"
# Objekt → (Kurzname, Höhe [mm], Benchmark?)  — Testobjekt YCB zählt nicht in die Auswahl
OBJ = {"kugel_d5": ("Kugel Ø 5", 50, True), "kugel_d7": ("Kugel Ø 7", 70, True), "kugel_d9": ("Kugel Ø 9", 90, True),
       "dose_d68x10": ("Dose 6,8×10", 100, True), "quader_9x6x4": ("Schachtel 9×6×4", 40, True),
       "ycb_005_suppe": ("YCB-Suppe (Test)", 102, False)}
KEYS = ["kipp_x", "roll_y", "rotator", "hoehe_m", "versatz_y_m"]


def load(name):
    with open(SRC / f"{name}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    combos = {}
    for r in rows:
        k = tuple(float(r[c]) for c in KEYS)
        combos.setdefault(k, []).append(r)
    out = {}
    for k, rs in combos.items():
        g = lambda c: np.array([float(r[c]) for r in rs])  # noqa: E731
        out[k] = {"gehalten": g("gehalten").mean(),
                  "sauber": bool(((g("startkontakt_n") <= 0.5) & (g("tisch_vor_schliessen_n") <= 1.0)).all()),
                  "tisch": ((g("tisch_daumen_n") > 1.0) | (g("tisch_finger_n") > 1.0)).mean(),
                  "handflaeche": g("handflaeche_anteil").mean(), "finger": g("finger_am_objekt").mean(),
                  "weg": g("objektweg_m").mean(), "n": len(rs)}
    return out


data = {n: load(n) for n in OBJ if (SRC / f"{n}.csv").exists()}
bench = [n for n in data if OBJ[n][2]]
poses = sorted({k[:3] + (k[4],) for n in data for k in data[n]})
heights = sorted({k[3] for n in data for k in data[n]})


def best_height(n, pose):
    """Beste saubere Höhe eines Objekts für eine Pose: gehalten, dann wenig Tischkontakt, dann niedrig."""
    cand = [(h, data[n].get(pose[:3] + (h, pose[3]))) for h in heights]
    cand = [(h, v) for h, v in cand if v and v["sauber"]]
    if not cand:
        return None, None
    h, v = max(cand, key=lambda hv: (hv[1]["gehalten"], -hv[1]["tisch"], -hv[0]))
    return h, v


score = []
for p in poses:
    per = [best_height(n, p) for n in bench]
    vals = [v["gehalten"] if v else 0.0 for _, v in per]
    score.append((float(np.mean(vals)), float(min(vals)), p, per))
score.sort(key=lambda s: (-s[0], -s[1]))
OUT.mkdir(parents=True, exist_ok=True)
pct = lambda x: f"{100 * x:.0f} %"  # noqa: E731
L = ["# Startpose „von oben“ — Suche (automatisch erzeugt)", "",
     "Erzeugt von `isaac_lab/tools/auswertung_startpose_oben.py` aus `logs/startpose_oben/*.csv` "
     "(`tools/suche_startpose_oben.py`: Regel „alle schließen“, Rotator hält seine Startstellung, Tisch senkt sich wie "
     "gewohnt; je Kombination mehrere Wiederholungen mit Zufallsgröße/-masse/-lage). Höhe = tiefste Fingerspitze (auch "
     "Daumen) über dem Tisch; Versatz = Objektmitte ggü. Greifmitte längs der Finger (− = Richtung Fingerspitzen). "
     "„Sauber“ = kein Startkontakt Hand↔Objekt, kein Hand↔Tisch vor dem Schließen.", "",
     f"Objekte: {', '.join(OBJ[n][0] for n in data)}; Auswahl über {', '.join(OBJ[n][0] for n in bench)}.", "",
     "## Beste Posen (eine Pose für alle Objekte, Höhe je Objekt)", "",
     "| Rang | Kippung | Rollen | Rotator | Versatz | Mittel gehalten | schwächstes | je Objekt: Höhe → gehalten / Tisch beim Schließen / Handfläche |",
     "|---|---|---|---|---|---|---|---|"]
for i, (m, lo, p, per) in enumerate(score[:12], 1):
    cells = "; ".join(f"{OBJ[n][0]} {('–' if h is None else f'{1000 * h:.0f} mm')} → "
                      + ("–" if v is None else f"{pct(v['gehalten'])}/{pct(v['tisch'])}/{pct(v['handflaeche'])}")
                      for n, (h, v) in zip(bench, per))
    L.append(f"| {i} | {p[0]:g}° | {p[1]:g}° | {p[2]:g}° | {1000 * p[3]:+.0f} mm | {pct(m)} | {pct(lo)} | {cells} |")

# Diagramme für die beste Pose: gehalten über Kippung × Höhe je Objekt (Rollen, Rotator, Versatz der besten Pose)
best = score[0][2]
kipps = sorted({k[0] for n in data for k in data[n]})
fig, axs = plt.subplots(1, len(data), figsize=(3.2 * len(data), 3.2), squeeze=False)
for ax, n in zip(axs[0], data):
    M = np.full((len(kipps), len(heights)), np.nan)
    for i, kx in enumerate(kipps):
        for j, h in enumerate(heights):
            v = data[n].get((kx, best[1], best[2], h, best[3]))
            if v:
                M[i, j] = v["gehalten"] if v["sauber"] else -0.2
    im = ax.imshow(M, origin="lower", vmin=-0.2, vmax=1.0, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(heights)), [f"{1000 * h:.0f}" for h in heights])
    ax.set_yticks(range(len(kipps)), [f"{k:g}" for k in kipps])
    ax.set_xlabel("Höhe [mm]")
    ax.set_title(OBJ[n][0], fontsize=9)
axs[0][0].set_ylabel("Kippung [°]")
fig.suptitle(f"gehalten (Startkontakt = dunkel) — Rollen {best[1]:g}°, Rotator {best[2]:g}°, Versatz {1000 * best[3]:+.0f} mm",
             fontsize=9)
fig.colorbar(im, ax=axs[0].tolist(), shrink=0.8)
fig.savefig(OUT / "gehalten_kippung_hoehe.svg")
plt.close(fig)

# Höhe je Objekt für die beste Pose → Regel „Höhe aus Objektgröße“
h_obj = [(OBJ[n][1], h) for n, (h, v) in zip(bench, score[0][3]) if h is not None]
L += ["", f"![gehalten über Kippung und Höhe](gehalten_kippung_hoehe.svg)", "",
      "## Höhe je Objekt für die beste Pose", "", "| Objekt | Objekthöhe | beste Höhe der tiefsten Spitze | gehalten | Tisch beim Schließen | Handfläche | Finger am Objekt | Objektweg |",
      "|---|---|---|---|---|---|---|---|"]
for n in data:
    h, v = best_height(n, best)
    L.append(f"| {OBJ[n][0]} | {OBJ[n][1]} mm | {('–' if h is None else f'{1000 * h:.0f} mm')} | "
             + ("– | – | – | – | –" if v is None else
                f"{pct(v['gehalten'])} | {pct(v['tisch'])} | {pct(v['handflaeche'])} | {v['finger']:.1f} | {1000 * v['weg']:.0f} mm")
             + " |")
if len(h_obj) >= 2:
    x, y = np.array(h_obj, float).T
    a, b = np.polyfit(x, 1000 * y, 1)
    L += ["", f"Lineare Näherung über die Benchmark-Objekte: Höhe ≈ {a:.2f} · Objekthöhe {b:+.0f} mm (nur Hinweis — das Raster "
          f"ist grob, Höhen {', '.join(f'{1000 * h:.0f}' for h in heights)} mm)."]
L += ["", "Gesamt je Objekt (alle Posen): " + "; ".join(
    f"{OBJ[n][0]} gehalten {pct(np.mean([v['gehalten'] for v in data[n].values()]))}, sauber "
    f"{pct(np.mean([v['sauber'] for v in data[n].values()]))}" for n in data)]
(OUT / "ergebnis.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L[:20]))
print(f"→ {OUT / 'ergebnis.md'}")
