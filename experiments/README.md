# Experimente — RL-Greifen (Isaac Lab)

Ziel: jede Änderung an Aufgabe, Belohnung, Randomisierung oder Netz als **Experiment** mit
Hypothese, genau einer Änderung, festem Bewertungsprotokoll und dokumentiertem Schluss —
vergleichbar, nachvollziehbar, reproduzierbar (ADR-016).

Grundlagen: Henderson et al. 2018 „Deep RL that Matters“ (Seeds, Varianz), Agarwal et al.
2021 „Deep RL at the Edge of the Statistical Precipice“ (Bootstrap-Konfidenzintervalle, rliable),
NeurIPS-Reproduzierbarkeits-Checkliste, YCB-Protokolle (Erfolgsquote je Objekt/Startlage),
Dexsuite (Lift/Reorient unterscheiden sich nur im Erfolgskriterium).

## Ablage

```
experiments/
  README.md                 dieses Dokument (Ablauf, Metriken, Entscheidungsregel)
  _vorlage.yaml             Vorlage für experiment.yaml
  index.md                  automatisch: Vergleichstabelle aller Experimente
  EXP-NNN_<kurzname>/
    experiment.yaml         Plan (vor dem Start) + Schluss (nach der Auswertung), von Hand
    results.json            automatisch: Metriken je Seed + Zusammenfassung + Urteilsvorschlag
    bericht.md              automatisch: lesbarer Bericht des Laufs
logs/rsl_rl/pib_grasp_hand_left/<zeit>_EXP-NNN_s<seed>/   (gitignored)
    params/env.yaml, agent.yaml   Isaac Lab: vollständige Konfiguration
    meta.json                     Commit, Versionen, GPU, Befehl, Zeiten
    pib_hand_sim.diff             nicht committete Änderungen zum Zeitpunkt des Starts
    model_*.pt, exported/         Checkpoints, Export (JIT + ONNX)
    eval-v1.json, eval-v1.txt     Bewertung je Protokollversion (nichts wird überschrieben)
    video_eval/videos/            Video der ersten Episoden (erster Seed)
```

`experiments/` ist im Git (nur Text), Checkpoints/Logs nicht. **Sicherung der Policies** nach jedem
Experiment in das private Hugging-Face-Repo [`churro206/pib-grasp-policies`](https://huggingface.co/churro206/pib-grasp-policies)
(je Lauf letzter Checkpoint, Export, Konfiguration, Metadaten, Bewertung, Log, Video; ~5 MB/Lauf;
unveränderte Dateien werden nicht erneut hochgeladen):
```bash
~/IsaacLab/isaaclab.sh -p isaac_lab/backup_policies.py            # Probelauf
~/IsaacLab/isaaclab.sh -p isaac_lab/backup_policies.py --upload   # hochladen
```
Anmeldung einmalig `hf auth login` (fine-grained Token „pib-hand-sim backup“: Repos lesen, Repos
anlegen/nur selbst angelegte beschreiben). Meilenstein-Policies zusätzlich als GitHub Release mit
Tag am Trainings-Commit.

## Ablauf (7 Schritte)

| # | Schritt | Wer | Werkzeug |
|---|---|---|---|
| 1 | **Planen**: Hypothese, genau eine Änderung zu den Eltern, Bedingungen | Leon (Claude entwirft) | `experiments.py new` |
| 2 | **Prüfen**: Kurztest headless (Absturz, NaN, Abbruchquoten, VRAM); Fenstertest nur bei geänderter Szene/Belohnung/Abbruch | automatisch + Leon | `experiments.py run` |
| 3 | **Trainieren**: alle Seeds, Metadaten werden gesichert | automatisch | `experiments.py run` |
| 4 | **Evaluieren**: festes Protokoll (unten), letzter Checkpoint | automatisch | `experiments.py run` → `eval_policy.py` |
| 5 | **Sichten**: Video, Auffälligkeiten | automatisch aufgenommen, Leon schaut | `videos/` im Laufordner |
| 6 | **Bewerten**: Vergleich mit den Eltern, Urteilsvorschlag nach Regel | automatisch, Leon bestätigt | `results.json`, `bericht.md` |
| 7 | **Dokumentieren & Entscheiden**: Schluss, nächstes Experiment; Policies sichern | Leon (Claude schlägt vor) | `experiments.py done`, `backup_policies.py --upload` |

Befehle (conda-Umgebung `env_isaaclab` aktiv, Orchestrierung mit System-Python):
```bash
/usr/bin/python3 isaac_lab/experiments.py new  --eltern EXP-001 --kurz name --titel "..."
/usr/bin/python3 isaac_lab/experiments.py run  EXP-002 [EXP-003 ...]     # 2–6, unbeaufsichtigt
/usr/bin/python3 isaac_lab/experiments.py done EXP-002                   # 7: index.md
```

Regeln:
- **Eine Änderung** pro Experiment gegenüber den Eltern (`new` listet die Code-Unterschiede).
- Hypothese, Bedingungen und Entscheidungsregel **vor** dem Lauf festlegen, nicht danach anpassen.
- **5 Seeds** (42–46) für Entscheidungen (seit 2026-10-07; vorher 3 — ein einzelner schlechter Seed
  bestimmte das Urteil, EXP-004–007: Seed 43 jedes Mal 14–56 %). Henderson et al. 2018: ≥ 5;
  Colas et al. 2018: für kleine Effekte per Power-Analyse eher 10–20.
- **Vor dem Lauf committen** (`run` warnt sonst) — nur ein committeter Stand ist reproduzierbar.
- Bewertet wird immer der **letzte Checkpoint**, nie der beste nach Bewertung (Auswahl-Verzerrung).
- Ändert ein Experiment das Trainingsbudget (Iterationen, Umgebungen), ist das **eine** Änderung
  je Größe; Lernkurven dann über Simulationsschritte vergleichen, nicht über Iterationen.
- Änderungen an Assets (USD) zeigt der Diff nur als „binär geändert“ → immer eigenes,
  committetes Experiment.
- Auch Misserfolge dokumentieren.
- Test-Objekte (ab Stufe 4) nie zum Abstimmen benutzen.
- PhysX (GPU) ist nicht bitgenau reproduzierbar — reproduzierbar heißt: gleicher Commit,
  gleiche Konfiguration, gleiche Seeds → statistisch gleiches Ergebnis.

## Bewertungsprotokoll `eval-v1`

- Je Lauf **1000 Episoden**, 256 Umgebungen, Bewertungs-Seed **1000** (≠ Trainings-Seeds),
  Policy **deterministisch** (exportierter Actor, Mittelwert ohne Rauschen).
- Umgebung wie im Training (gleiche Randomisierung), **aber nur zwei Abbrüche**: Dose gefallen,
  Physik instabil. Trainingsspezifische Abbrüche (z. B. Kippen) sind in der Bewertung aus,
  der Kippwinkel wird gemessen — so bleiben Experimente mit unterschiedlichen
  Trainingsabbrüchen vergleichbar.
- **Bedingung** = Objekt × Startpose × Anforderung (in `experiment.yaml`). Ergebnisse
  immer je Bedingung, nie über Bedingungen gemittelt.

### Metriken

**Hauptmetrik — Aufgabenerfolg**: Anteil der Episoden, die bis zum Ende laufen (Dose nach dem
Absenken gehalten) **und** die Anforderung der Bedingung erfüllen (z. B. größter Kippwinkel
der ganzen Episode ≤ `max_kipp_deg`).

**Haltequote**: Anteil der Episoden bis zum Ende ohne Herunterfallen, unabhängig von der
Anforderung (über Bedingungen vergleichbar).

**Fehlerarten** (Anteile): gefallen · Physik instabil · Startfehler (Abbruch oder Kippen über
die Anforderung in den ersten 0,1 s — Reset-Überlappung) · Anforderung verletzt (gehalten,
aber gekippt).

**Leitplanken** (je Bedingung, über die gehaltenen Episoden):

| Leitplanke | Definition | Toleranz ggü. Eltern |
|---|---|---|
| Kippwinkel | Median des größten Kippwinkels je Episode [°] | +5° |
| Unterarmdrehung | Median der größten Abweichung von der Startstellung [°] | +10° |
| Griffkraft | Mittel der FSR-Summe in der Haltephase [N] | +20 % |
| Kraft > 15 N | Anteil der Schritte der Haltephase mit einer Fingerspitze > 15 N | +5 Prozentpunkte |
| Stall-Anteil | Anteil der Schritte mit einem Servo (außer Handgelenk) ≥ 90 % des Maximalmoments | +5 Prozentpunkte |
| Absinken | Absinken der Dose gegenüber der Hand bis Episodenende [mm] | +5 mm |
| Unruhe | Mittel von ‖a_t − a_{t−1}‖² | +20 % |

**Fingernutzung** (beschreibend, keine Leitplanke; seit 2026-10-07): Kontaktanteil (> 1 N an der
Dose) und Kraft je Finger in der Haltephase, mittlere Zahl der Finger mit Kontakt. Anlass: EXP-004
hielt mit nur zwei Fingern (Pinzettengriff) — in den übrigen Metriken unsichtbar.

**Lerneffizienz** (aus TensorBoard, stochastische Policy): `Episode_Termination/time_out` über
die Schritte; Kennzahl: Umgebungsschritte bis 50 % bzw. 80 %.

Später: Robustheitsraster Masse × Reibung × Durchmesser (Stufe 3), Test-Objekte (Stufe 4),
int8 − float (M2).

### Grenzen und Ausblick

- **Bewertungssätze**: eval-v1 bewertet in der Trainingsverteilung. Ab Stufe 3/4 getrennte Sätze:
  nominal, breit (über die Trainingsbereiche hinaus), Test-Objekte (nie zum Abstimmen).
- **Aussagekraft**: 1000 Episoden → je Seed etwa ±2–3 Prozentpunkte; die Streuung zwischen Seeds
  ist meist größer. Effekte unter ~5 Prozentpunkten sind mit 3 Seeds kaum nachweisbar → 5 Seeds.
- **Sim-to-Real**: alle Metriken gelten für die Simulation (bekannte Lücken: lineare Kopplung,
  Fingerkraft ~2× zu hoch, idealisierte FSR, keine Latenz — ADR-015). Echte Hand später mit
  denselben Metriken und festen Versuchsreihen je Objekt/Startlage (YCB-Muster).
- **Rechenaufwand**: Dauer je Lauf steht in `meta.json` (GPU-Stunden je Experiment).

### Statistik und Entscheidungsregel

- Je Seed die Quote; zusammengefasst Mittel über die Seeds mit **95-%-Konfidenzintervall**
  per zweistufigem Bootstrap (Seeds, darin Episoden ziehen; 2000 Wiederholungen).
- Unterschied Kind − Eltern ebenso per Bootstrap.
- Zusätzlich je Experiment: **IQM** der Seed-Quoten (Interquartilsmittel, Agarwal et al. 2021 —
  robust gegen Ausreißer-Seeds, ab ~5 Seeds sinnvoll) und **Fehlschlagquote** (Anteil der Seeds
  unter 50 % Aufgabenerfolg = Zuverlässigkeit des Trainings). Mittelwert = was ein einzelner
  Trainingslauf im Schnitt bringt; IQM = wie gut die Variante typischerweise wird.
- **Urteilsvorschlag**:
  - *besser*: Intervall des Unterschieds im Aufgabenerfolg komplett > 0 und keine Leitplanke
    über der Toleranz
  - *schlechter*: Intervall komplett < 0
  - *kein messbarer Unterschied*: sonst — dann gewinnt die einfachere Variante
  - *Leitplanke verletzt*: besser im Aufgabenerfolg, aber eine Leitplanke über der Toleranz
- Das Urteil ist ein Vorschlag; Leon bestätigt es in `experiment.yaml` → `schluss`.

### Versionen

Ändert sich eine Definition (Protokoll, Metrik, Anforderung), bekommt das Protokoll eine neue
Version (`eval-v2` …) und die zu vergleichenden Policies werden neu bewertet. Ergebnisse
verschiedener Protokollversionen werden nicht verglichen.
