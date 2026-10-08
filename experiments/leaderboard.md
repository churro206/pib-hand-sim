# Leaderboard — Greif-Policies

Automatisch erzeugt (auswertung-v2). Benchmark: Protokoll eval-v1, Kippwinkel ≤ 45°, Ø 6 cm, Ø 8 cm, Quader. **Gesamt** = IQM des Aufgabenerfolgs über alle Seeds × Objekte (rliable, sortiert danach). **Leistung** = dasselbe nur über die erfolgreichen Seeds (Mittel über die Objekte ≥ 50 %), je Objekt als Median. **Zuverlässigkeit** = erfolgreiche Seeds. **P(1 > X)**: Wahrscheinlichkeit, dass ein Lauf von Platz 1 besser ist (gesichert, wenn die untere KI-Grenze > 0,5). Werte in %, KI 95 %. Vorschlag = Urteilsregel v2 gegenüber den Eltern (✓: Leon hat das Experiment bewertet, Urteil im Bericht). Quellen: Agarwal et al. 2021 (rliable), Chan et al. 2020 (Zuverlässigkeit).

| Rang | Experiment | Titel | Gesamt [KI] | Leistung [KI] | Ø 6 cm | Ø 8 cm | Quader | erfolgreiche Seeds | Unruhe | P(1 > X) | Vorschlag (v2) | beste Videos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [EXP-006](EXP-006_masse_dexsuite/bericht.md) | Objektmasse wie Dexsuite (0,04–0,4 kg) | **68** [53–78] | 75 [69–82] | 92 | 80 | 55 | 4/5 | 0.31 | – | kein Unterschied, Leitplanke verletzt ✓ | [▶](EXP-006_masse_dexsuite/beste_videos/zylinder_d6_s44.mp4) [▶](EXP-006_masse_dexsuite/beste_videos/zylinder_d8_s44.mp4) [▶](EXP-006_masse_dexsuite/beste_videos/quader_7x7x20_s44.mp4) |
| 2 | [EXP-005](EXP-005_fingerzahl/bericht.md) | Kontaktbelohnung nach Fingerzahl | **64** [50–75] | 71 [64–78] | 89 | 74 | 55 | 4/5 | 0.49 | 0.57 [0.35–0.77] | kein Unterschied, Leitplanke verletzt ✓ | [▶](EXP-005_fingerzahl/beste_videos/zylinder_d6_s42.mp4) [▶](EXP-005_fingerzahl/beste_videos/zylinder_d8_s42.mp4) [▶](EXP-005_fingerzahl/beste_videos/quader_7x7x20_s42.mp4) |
| 3 | [EXP-007](EXP-007_lang_1500/bericht.md) | EXP-004 mit 1500 Iterationen | **64** [43–76] | 73 [63–81] | 93 | 72 | 54 | 4/5 | 1.58 | 0.49 [0.28–0.72] | kein Unterschied, Leitplanke verletzt ✓ | [▶](EXP-007_lang_1500/beste_videos/zylinder_d6_s46.mp4) [▶](EXP-007_lang_1500/beste_videos/zylinder_d8_s46.mp4) [▶](EXP-007_lang_1500/beste_videos/quader_7x7x20_s46.mp4) |
| 4 | [EXP-011](EXP-011_masse_lang_1500/bericht.md) | EXP-006 mit 1500 Iterationen (längeres Training) | **57** [45–68] | 68 [62–78] | 91 | 61 | 45 | 3/5 | 1.20 | 0.64 [0.43–0.84] | schlechter, Leitplanke verletzt ✓ | [▶](EXP-011_masse_lang_1500/beste_videos/zylinder_d6_s42.mp4) [▶](EXP-011_masse_lang_1500/beste_videos/zylinder_d8_s42.mp4) [▶](EXP-011_masse_lang_1500/beste_videos/quader_7x7x20_s42.mp4) |
| 5 | [EXP-012](EXP-012_dexsuite_belohnung_voll/bericht.md) | Belohnung wie Dexsuite (Annäherung mit Handfläche, Position 3D zur Startposition) | **41** [9–68] | 73 [69–78] | 93 | 71 | 50 | 3/5 | 2.80 | 0.69 [0.47–0.88] | kein Unterschied, Leitplanke verletzt | [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/zylinder_d6_s42.mp4) [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/zylinder_d8_s42.mp4) [▶](EXP-012_dexsuite_belohnung_voll/beste_videos/quader_7x7x20_s42.mp4) |
| 6 | [EXP-004](EXP-004_dexsuite_belohnung/bericht.md) | Belohnungssatz wie Dexsuite (dicht + scharf, kontaktgekoppelt) | **28** [6–56] | 73 [70–76] | 88 | 76 | 43 | 2/5 | 0.86 | 0.83 [0.64–0.95] gesichert | kein Unterschied, Leitplanke verletzt ✓ | [▶](EXP-004_dexsuite_belohnung/beste_videos/zylinder_d6_s42.mp4) [▶](EXP-004_dexsuite_belohnung/beste_videos/zylinder_d8_s42.mp4) [▶](EXP-004_dexsuite_belohnung/beste_videos/quader_7x7x20_s42.mp4) |
| 7 | [EXP-000](EXP-000_probelauf/bericht.md) | Probelauf Dexsuite-Muster (Ausgangswert) | **2** [2–3] | – | – | – | – | 0/1 ⚠ | 0.24 | 1.00 [1.00–1.00] gesichert | Ausgangswert | – |
| 8 | [EXP-001](EXP-001_kippabbruch/bericht.md) | Kippabbruch + Aufrecht-Belohnung | **0** [0–0] | – | – | – | – | 0/3 ⚠ | – | 1.00 [1.00–1.00] gesichert | kein Unterschied | – |
| 9 | [EXP-002](EXP-002_lang/bericht.md) | Langer Lauf (Lift-Rezept: 1500 Iterationen) | **0** [0–0] | – | – | – | – | 0/3 ⚠ | – | 1.00 [1.00–1.00] gesichert | kein Unterschied | – |
| 10 | [EXP-003](EXP-003_kipp_belohnung/bericht.md) | Kippen über multiplikative Belohnung statt Abbruch (Dexsuite) | **0** [0–0] | – | – | – | – | 0/3 ⚠ | – | 1.00 [1.00–1.00] gesichert | kein Unterschied | – |

⚠ weniger als 5 Seeds (vorläufig).

<details>
<summary>Einsatz-Kandidaten (bester Seed je Policy — nach der Bewertung ausgewählt, daher optimistisch)</summary>

| Experiment | bester Seed | Ø 6 cm | Ø 8 cm | Quader | Actor-Parameter | Policy (ONNX) |
|---|---|---|---|---|---|---|
| EXP-006 | 44 | 94 | 88 | 58 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_13-21-47_EXP-006_s44/exported/policy.onnx` |
| EXP-005 | 42 | 93 | 80 | 62 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_12-19-15_EXP-005_s42/exported/policy.onnx` |
| EXP-007 | 46 | 97 | 86 | 60 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_00-14-07_EXP-007_s46/exported/policy.onnx` |
| EXP-011 | 42 | 88 | 83 | 45 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_01-20-00_EXP-011_s42/exported/policy.onnx` |
| EXP-012 | 42 | 93 | 82 | 52 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-08_16-17-35_EXP-012_s42/exported/policy.onnx` |
| EXP-004 | 42 | 88 | 74 | 46 | 68808 | `logs/rsl_rl/pib_grasp_hand_left/2026-10-07_11-06-59_EXP-004_s42/exported/policy.onnx` |

</details>
