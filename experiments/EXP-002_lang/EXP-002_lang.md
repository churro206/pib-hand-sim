# EXP-002: Langer Lauf (Lift-Rezept: 1500 Iterationen)

> **Nachtrag 2026-10-09 (ADR-021/022):** Bewertet unter eval-v1: beim Reset steckte die Hand in bis zu 81 % der Starts im Objekt (ADR-021) — besonders Quader-Werte und der Abstand zu den Regel-Baselines sind verzerrt.

> **Nachtrag 2026-10-09 (ADR-021/022):** Der Annäherungsterm maß bis EXP-018 alle Handkörper (Unterarmansatz) statt der Fingerspitzen und wäre auch korrigiert für 3–4 cm Fingerweg zu flach: ein Signal fürs Zugreifen fehlte, Seeds scheiterten deshalb am Entdecken des Griffs (ADR-022).

> **Nachtrag 2026-10-09 (ADR-021/022):** Der Schluss „länger trainieren macht unruhiger“ ist nicht belastbar: mit unbegrenzten Aktionen wachsen im langen Training Rauschen und Überziehen, die die Unruhe-Metrik misst — nach EXP-020/022 neu prüfen.

**Leistung** – (kein erfolgreicher Seed)

**Zuverlässigkeit** 0/3 Seeds erfolgreich [0–71 %] — EXP-001: 0/3, exakter Fisher-Test p = 1.00 → nicht unterscheidbar (für eine Aussage ≥ 10 Seeds je Experiment)

**Leitplanken** eingehalten

**Befund** ohne Erfolg: Seed 42 (lernt nicht zu greifen), Seed 43 (lernt nicht zu greifen), Seed 44 (lernt nicht zu greifen)

**Urteilsvorschlag** (auswertung-v2): **kein Unterschied**

![Ergebnis je Bedingung — Punkte = Seeds](diagramme/EXP-002_bedingungen.svg)

![Verlauf über die Episode](diagramme/EXP-002_verlauf.svg)

<details>
<summary>Ergebnisse je Bedingung (eval-v1, Leitplanken, Fehlerarten, Fingernutzung)</summary>

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 20°), Protokoll eval-v1, 3 Seed(s); Spalte EXP-001 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-001 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 0.0 % | 0.0 % – 0.0 % | 0.0 % | 100.0 % | 0.0 % / 0.0 % |
| haltequote | 0.0 % | 0.0 % – 0.0 % | 0.0 % | 100.0 % | 0.0 % / 0.0 % |
| Kippwinkel Median [°] | – | | | | – |
| Unterarm Median [°] | – | | | | – |
| Griffkraft Mittel [N] | – | | | | – |
| Kraft > 15 N [Anteil] | – | | | | – |
| Stall-Anteil [Anteil] | – | | | | – |
| Absinken [mm] | – | | | | – |
| Unruhe | – | | | | – |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 2.1 %, gefallen 97.9 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-001)
Unterschied Aufgabenerfolg +0.0 Prozentpunkte (95-%-KI +0.0 … +0.0)

Je Seed: 0.0 %, 0.0 %, 0.0 %

</details>

<details>
<summary>Trainingsverlauf</summary>


Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten 10 Iterationen (Belohnungsanteile je Sekunde Episode).

| Größe | Seed 42 | Seed 43 | Seed 44 | Mittel |
|---|---|---|---|---|
| mean_reward | 0.909 | 0.94 | 0.931 | 0.927 |
| action_l2 | -0.0043 | -0.00374 | -0.00311 | -0.00372 |
| action_rate_l2 | -0.00551 | -0.00437 | -0.00434 | -0.00474 |
| early_termination | -0.0037 | -0.0037 | -0.0037 | -0.0037 |
| excess_force | -8.52e-06 | -2.6e-05 | -7.41e-05 | -3.62e-05 |
| fingertips_to_object | 0.00101 | 0.00103 | 0.00102 | 0.00102 |
| good_contact | 0 | 0 | 0 | 0 |
| held | 0.1 | 0.104 | 0.103 | 0.102 |
| upright | 0.114 | 0.116 | 0.114 | 0.115 |
| object_dropped | 95.5 % | 95.4 % | 94.9 % | 95.3 % |
| mean_noise_std | 0.346 | 0.302 | 0.317 | 0.321 |

![Lernkurve](diagramme/EXP-002_lernkurve.svg)

![Belohnungsanteile](diagramme/EXP-002_belohnung.svg)

![Abbrüche](diagramme/EXP-002_abbrueche.svg)

![PPO-Diagnose](diagramme/EXP-002_ppo.svg)

</details>

<details>
<summary>Videos aller Seeds</summary>

16 Umgebungen, eine Episode (nicht im Git, Hugging Face).

| Objekt | Seed 42 | Seed 43 | Seed 44 |
|---|---|---|---|
| `quader_7x7x20` | [▶](videos/EXP-002_quader_7x7x20_s42.mp4) | [▶](videos/EXP-002_quader_7x7x20_s43.mp4) | [▶](videos/EXP-002_quader_7x7x20_s44.mp4) |
| `zylinder_d6` | [▶](videos/EXP-002_zylinder_d6_s42.mp4) | [▶](videos/EXP-002_zylinder_d6_s43.mp4) | [▶](videos/EXP-002_zylinder_d6_s44.mp4) |
| `zylinder_d8` | [▶](videos/EXP-002_zylinder_d8_s42.mp4) | [▶](videos/EXP-002_zylinder_d8_s43.mp4) | [▶](videos/EXP-002_zylinder_d8_s44.mp4) |

</details>

<details>
<summary>Netz, Training und Konfiguration</summary>

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 1500 Iterationen

Geplante Änderung: Trainingsdauer 1500 statt 300 Iterationen (Umgebungen unverändert 1024)

Konfiguration gegenüber EXP-001 (1 Unterschiede):

- `agent.max_iterations: 300 → 1500`

</details>
