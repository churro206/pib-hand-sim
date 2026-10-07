# Experimente — Übersicht

Automatisch erzeugt (`experiments.py done`). Aufgabenerfolg/Haltequote in %, [95-%-KI]; Leitplanken Mittel über Seeds. Definitionen: README.md.

| ID | Titel | Eltern | Bedingung | Seeds | Netz (Actor) | Param. | Iter. × Umg. | Aufgabenerfolg | Haltequote | Kipp° | Unterarm° | Stall | Vorschlag | Urteil (bestätigt) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [EXP-000](EXP-000_probelauf/experiment.yaml) | Probelauf Dexsuite-Muster (Ausgangswert) | – | zylinder_seitlich | 1 | [256, 128, 64] elu, V5 | 68808 | 300 × 1024 | 0.0 [0.0–0.0] | 86.1 [84.1–88.2] | 104 | 90 | 99.6 | kein Vergleich (keine Eltern-Bewertung mit gleichem Protokoll) | Ausgangswert |
| [EXP-001](EXP-001_kippabbruch/experiment.yaml) | Kippabbruch + Aufrecht-Belohnung | EXP-000 | zylinder_seitlich | 6 | [256, 128, 64] elu, V5 | 68808 | 300 × 1024 | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | – | – | – | kein messbarer Unterschied (vorläufig: < 3 Seeds) | – |
| [EXP-002](EXP-002_lang/experiment.yaml) | Langer Lauf (Lift-Rezept: 1500 Iterationen) | EXP-001 | zylinder_seitlich | 6 | [256, 128, 64] elu, V5 | 68808 | 1500 × 1024 | 0.0 [0.0–0.0] | 0.0 [0.0–0.0] | – | – | – | kein messbarer Unterschied | – |
