# EXP-007: EXP-004 mit 1500 Iterationen

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v1, 3 Seed(s); Spalte EXP-004 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-004 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 69.4 % | 21.9 % – 94.4 % | 80.7 % | 33.3 % | 77.3 % / 82.5 % |
| haltequote | 92.8 % | 91.0 % – 94.6 % | 92.7 % | 0.0 % | 90.1 % / 90.3 % |
| Kippwinkel Median [°] | 26 | | | | 26.6 |
| Unterarm Median [°] | 25.6 | | | | 25.8 |
| Griffkraft Mittel [N] | 64.9 | | | | 58.4 |
| Kraft > 15 N [Anteil] | 99.2 % | | | | 99.2 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 99.7 % |
| Absinken [mm] | 0.774 | | | | 0.0255 |
| Unruhe | 1.86 | | | | 1.01 |

Fehlerarten: startfehler 0.3 %, gefallen 6.9 %, instabil 0.0 %, anforderung_verletzt 23.4 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-004)
Unterschied Aufgabenerfolg -8.3 Prozentpunkte (95-%-KI -33.6 … +6.7)
- Leitplanke: Unruhe: 1.86 > 1.21

Je Seed: 92.0 %, 21.7 %, 94.5 %

Fingernutzung (Haltephase): im Mittel 2.25 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 97/100/0/0/2 · 100/75/0/0/100 · 100/0/100/0/0

## Trainingsverlauf

Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten 10 Iterationen (Belohnungsanteile je Sekunde Episode).

| Größe | Seed 42 | Seed 43 | Seed 44 | Mittel |
|---|---|---|---|---|
| mean_reward | 29.7 | 36.3 | 39.1 | 35 |
| action_l2 | -0.222 | -0.136 | -0.107 | -0.155 |
| action_rate_l2 | -0.123 | -0.0627 | -0.0801 | -0.0887 |
| early_termination | 0 | 0 | 0 | 0 |
| fingertips_to_object | 0.325 | 0.424 | 0.343 | 0.364 |
| good_contact | 0.433 | 0.41 | 0.449 | 0.431 |
| held | 0.948 | 0.973 | 1.06 | 0.993 |
| success | 3.42 | 4.47 | 4.99 | 4.29 |
| upright | 1.76 | 1.94 | 2.09 | 1.93 |
| object_dropped | 8.5 % | 9.7 % | 4.3 % | 7.5 % |
| mean_noise_std | 1.18 | 0.701 | 0.793 | 0.892 |

![Lernkurve](diagramme/lernkurve.svg)

![Belohnungsanteile](diagramme/belohnung.svg)

![Abbrüche](diagramme/abbrueche.svg)

![PPO-Diagnose](diagramme/ppo.svg)

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 1500 Iterationen

## Konfiguration gegenüber EXP-004 (1 Unterschiede)

Geplante Änderung: Trainingsdauer 1500 statt 300 Iterationen.

- `agent.max_iterations: 300 → 1500`
