# Leaderboard — Greif-Policies

Automatisch erzeugt (`experiments.py done` / `leaderboard`). Alle Policies (Experimente mit eigenem Training) unter denselben Benchmark-Bedingungen: Protokoll eval-v1, Kippwinkel ≤ 45°, Objekte Ø 6 cm (`zylinder_d6`), Ø 8 cm (`zylinder_d8`), Quader (`quader_7x7x20`). Sortiert nach dem **IQM des Aufgabenerfolgs über alle Objekte** (rliable: Erfolgsquoten aller Seeds × Objekte gepoolt, Mittel der mittleren 50 % — robust gegen einzelne gescheiterte Seeds); 95-%-KI per stratifiziertem Bootstrap. Je Objekt dasselbe über die Seeds. **P(1 > X)**: Wahrscheinlichkeit, dass ein Lauf von Platz 1 besser ist als einer dieser Policy (rliable „probability of improvement“, gemittelt über die Objekte); **gesichert**, wenn die untere KI-Grenze über 0,5 liegt — sonst kein belastbarer Abstand zu Platz 1. Quelle: Agarwal et al. 2021, *Deep RL at the Edge of the Statistical Precipice*. Werte in %.

## Rangliste

| Rang | Experiment | Titel | Seeds | It. × Umg. | IQM alle Objekte [KI] | IQM Ø 6 cm [KI] | IQM Ø 8 cm [KI] | IQM Quader [KI] | Fehlschlag-Seeds | P(1 > X) [KI] | Urteil |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [EXP-006](EXP-006_masse_dexsuite/bericht.md) | Objektmasse wie Dexsuite (0,04–0,4 kg) | 5 | 300 × 1024 | **67.8** [52.3–77.8] | 89.0 [44.5–93.8] | 74.1 [51.2–85.7] | 52.6 [16.2–59.3] | 1/5 | – | kein gesicherter Unterschied zu EXP-004 nach eval-v1, aber robuster (1/5 Fehlschlag-Seeds) und beste Übertragung — neue Baseline — bestätigt (Leon, 2026-10-08) |
| 2 | [EXP-005](EXP-005_fingerzahl/bericht.md) | Kontaktbelohnung nach Fingerzahl | 5 | 300 × 1024 | **64.4** [50.0–74.2] | 83.7 [32.4–92.2] | 69.1 [46.2–82.6] | 52.6 [23.7–59.3] | 1/5 | 0.57 [0.36–0.77] | kein messbarer Unterschied zu EXP-004 (mehr Finger, mehr Kraft) — bestätigt (Leon, 2026-10-08) |
| 3 | [EXP-007](EXP-007_lang_1500/bericht.md) | EXP-004 mit 1500 Iterationen | 5 | 1500 × 1024 | **63.7** [41.5–75.3] | 90.7 [41.9–95.9] | 65.0 [35.4–84.1] | 42.4 [15.6–60.0] | 1/5 | 0.49 [0.28–0.72] | kein messbarer Unterschied zu EXP-004 am Zylinder; robuster als EXP-004, aber unruhiger — bestätigt (Leon, 2026-10-08) |
| 4 | [EXP-011](EXP-011_masse_lang_1500/bericht.md) | EXP-006 mit 1500 Iterationen (längeres Training) | 5 | 1500 × 1024 | **57.1** [44.1–68.7] | 90.9 [45.9–93.5] | 57.9 [48.7–76.1] | 36.0 [14.1–47.7] | 2/5 | 0.64 [0.41–0.84] | Hypothese widerlegt (längeres Training hebt den Transfer nicht) — bestätigt (Leon, 2026-10-08) |
| 5 | [EXP-012](EXP-012_dexsuite_belohnung_voll/bericht.md) | Belohnung wie Dexsuite (Annäherung mit Handfläche, Position 3D zur Startposition) | 5 | 300 × 1024 | **41.3** [8.7–68.3] | 64.1 [0.0–94.1] | 48.5 [0.0–77.6] | 34.3 [0.0–51.1] | 2/5 | 0.69 [0.48–0.88] | – |
| 6 | [EXP-004](EXP-004_dexsuite_belohnung/bericht.md) | Belohnungssatz wie Dexsuite (dicht + scharf, kontaktgekoppelt) | 5 | 300 × 1024 | **27.6** [7.3–55.4] | 50.5 [2.0–88.1] | 29.8 [0.9–76.2] | 20.8 [0.8–43.1] | 3/5 | 0.83 [0.65–0.96] gesichert | besser als EXP-000, aber instabil (2/5 Seeds scheitern) — bestätigt (Leon, 2026-10-08) |
| 7 | [EXP-000](EXP-000_probelauf/bericht.md) | Probelauf Dexsuite-Muster (Ausgangswert) | 1 ⚠ | 300 × 1024 | **2.3** [1.7–2.9] | 2.0 [1.2–2.9] | 5.2 [3.9–6.6] | 0.6 [0.2–1.1] | 1/1 | 1.00 [1.00–1.00] gesichert | Ausgangswert |
| 8 | [EXP-001](EXP-001_kippabbruch/bericht.md) | Kippabbruch + Aufrecht-Belohnung | 3 ⚠ | 300 × 1024 | **0.0** [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 3/3 | 1.00 [1.00–1.00] gesichert | schlechter (Entwurf, von Leon zu bestätigen) |
| 9 | [EXP-002](EXP-002_lang/bericht.md) | Langer Lauf (Lift-Rezept: 1500 Iterationen) | 3 ⚠ | 1500 × 1024 | **0.0** [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 3/3 | 1.00 [1.00–1.00] gesichert | kein Unterschied (Entwurf, von Leon zu bestätigen) |
| 10 | [EXP-003](EXP-003_kipp_belohnung/bericht.md) | Kippen über multiplikative Belohnung statt Abbruch (Dexsuite) | 3 ⚠ | 300 × 1024 | **0.0** [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | 3/3 | 1.00 [1.00–1.00] gesichert | kein Unterschied (Entwurf, von Leon zu bestätigen) |

⚠ weniger als 5 Seeds (vorläufig).

## Verhalten (Ø 6 cm, gehaltene Episoden, Mittel über Seeds)

| Experiment | Haltequote | Kipp° | Unterarm° | Finger am Objekt | Griffkraft [N] | Kraft > 15 N | Stall | Unruhe |
|---|---|---|---|---|---|---|---|---|
| EXP-006 | 92.3 | 30 | 40 | 2.9 | 86 | 99.9 | 99.8 | 0.31 |
| EXP-005 | 90.0 | 34 | 44 | 2.9 | 93 | 99.8 | 99.9 | 0.49 |
| EXP-007 | 92.1 | 22 | 21 | 2.0 | 55 | 89.3 | 85.9 | 1.58 |
| EXP-011 | 94.3 | 28 | 38 | 2.9 | 92 | 99.7 | 100.0 | 1.20 |
| EXP-012 | 56.0 | 17 | 24 | 2.2 | 82 | 99.9 | 99.5 | 2.80 |
| EXP-004 | 73.1 | 34 | 36 | 2.0 | 60 | 99.3 | 99.6 | 0.86 |
| EXP-000 | 86.1 | 104 | 90 | – | 24 | 9.3 | 99.6 | 0.24 |
| EXP-001 | 0.0 | – | – | – | – | – | – | – |
| EXP-002 | 0.0 | – | – | – | – | – | – | – |
| EXP-003 | 0.0 | – | – | – | – | – | – | – |

## Einsatz-Kandidat je Policy

Bester Seed nach mittlerem Aufgabenerfolg über alle Benchmark-Objekte — Auswahl nach der Bewertung, daher optimistisch; für Vergleiche zählt die Rangliste.

| Experiment | bester Seed | Ø 6 cm | Ø 8 cm | Quader | Actor-Parameter | Policy (ONNX) |
|---|---|---|---|---|---|---|
| EXP-006 | 44 | 94.3 [▶](EXP-006_masse_dexsuite/beste_videos/zylinder_d6_s44.mp4) | 87.7 [▶](EXP-006_masse_dexsuite/beste_videos/zylinder_d8_s44.mp4) | 58.5 [▶](EXP-006_masse_dexsuite/beste_videos/quader_7x7x20_s44.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_13-21-47_EXP-006_s44/exported/policy.onnx` |
| EXP-005 | 42 | 93.2 [▶](EXP-005_fingerzahl/beste_videos/zylinder_d6_s42.mp4) | 79.7 [▶](EXP-005_fingerzahl/beste_videos/zylinder_d8_s42.mp4) | 61.9 [▶](EXP-005_fingerzahl/beste_videos/quader_7x7x20_s42.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_12-19-15_EXP-005_s42/exported/policy.onnx` |
| EXP-007 | 46 | 96.9 [▶](EXP-007_lang_1500/beste_videos/zylinder_d6_s46.mp4) | 85.7 [▶](EXP-007_lang_1500/beste_videos/zylinder_d8_s46.mp4) | 59.5 [▶](EXP-007_lang_1500/beste_videos/quader_7x7x20_s46.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_00-14-07_EXP-007_s46/exported/policy.onnx` |
| EXP-011 | 42 | 87.9 [▶](EXP-011_masse_lang_1500/beste_videos/zylinder_d6_s42.mp4) | 83.2 [▶](EXP-011_masse_lang_1500/beste_videos/zylinder_d8_s42.mp4) | 44.8 [▶](EXP-011_masse_lang_1500/beste_videos/quader_7x7x20_s42.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_01-20-00_EXP-011_s42/exported/policy.onnx` |
| EXP-012 | 42 | 93.1 [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/zylinder_d6_s42.mp4) | 81.7 [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/zylinder_d8_s42.mp4) | 51.9 [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/quader_7x7x20_s42.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_16-17-35_EXP-012_s42/exported/policy.onnx` |
| EXP-004 | 42 | 88.3 [▶](EXP-004_dexsuite_belohnung/beste_videos/zylinder_d6_s42.mp4) | 73.6 [▶](EXP-004_dexsuite_belohnung/beste_videos/zylinder_d8_s42.mp4) | 45.6 [▶](EXP-004_dexsuite_belohnung/beste_videos/quader_7x7x20_s42.mp4) | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_11-06-59_EXP-004_s42/exported/policy.onnx` |
