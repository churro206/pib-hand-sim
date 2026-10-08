# EXP-006: Objektmasse wie Dexsuite (0,04–0,4 kg)

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-004 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-004 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 77.5 % | 52.0 % – 93.4 % | 89.0 % | 20.0 % | 47.6 % / 50.5 % |
| haltequote | 92.3 % | 87.8 % – 95.0 % | 94.3 % | 0.0 % | 73.1 % / 90.2 % |
| Kippwinkel Median [°] | 30 | | | | 34 |
| Unterarm Median [°] | 40 | | | | 35.7 |
| Griffkraft Mittel [N] | 85.7 | | | | 59.6 |
| Kraft > 15 N [Anteil] | 99.9 % | | | | 99.3 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 99.6 % |
| Absinken [mm] | 0.0206 | | | | 0.0191 |
| Unruhe | 0.312 | | | | 0.863 |

Fehlerarten: startfehler 0.5 %, gefallen 7.2 %, instabil 0.0 %, anforderung_verletzt 14.8 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-004)
Unterschied Aufgabenerfolg +30.1 Prozentpunkte (95-%-KI -8.0 … +68.4)
- Leitplanke: Griffkraft Mittel [N]: 85.7 > 71.6

Je Seed: 93.3 %, 26.9 %, 94.3 %, 81.9 %, 91.2 %

Fingernutzung (Haltephase): im Mittel 2.93 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/95/100/95/0 · 100/0/94/0/100 · 97/99/4/3/0 · 99/0/0/100/0 · 98/90/0/100/92

## Trainingsverlauf

Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten 10 Iterationen (Belohnungsanteile je Sekunde Episode).

| Größe | Seed 42 | Seed 43 | Seed 44 | Seed 45 | Seed 46 | Mittel |
|---|---|---|---|---|---|---|
| mean_reward | 29.4 | 28.3 | 27.6 | 18.8 | 28.4 | 26.5 |
| action_l2 | -0.0915 | -0.0873 | -0.0632 | -0.114 | -0.107 | -0.0926 |
| action_rate_l2 | -0.0762 | -0.0535 | -0.047 | -0.0927 | -0.0545 | -0.0648 |
| early_termination | -4.34e-06 | -5.58e-05 | 0 | 0 | 0 | -1.2e-05 |
| fingertips_to_object | 0.361 | 0.37 | 0.323 | 0.389 | 0.442 | 0.377 |
| good_contact | 0.433 | 0.42 | 0.412 | 0.353 | 0.398 | 0.403 |
| held | 0.919 | 0.883 | 0.888 | 0.719 | 0.869 | 0.856 |
| success | 3.19 | 2.98 | 3.04 | 1.65 | 3.15 | 2.8 |
| upright | 1.77 | 1.71 | 1.62 | 1.31 | 1.61 | 1.6 |
| object_dropped | 11.1 % | 10.6 % | 11.7 % | 25.6 % | 14.9 % | 14.8 % |
| mean_noise_std | 0.846 | 0.712 | 0.687 | 0.974 | 0.769 | 0.798 |

![Lernkurve](diagramme/lernkurve.svg)

![Belohnungsanteile](diagramme/belohnung.svg)

![Abbrüche](diagramme/abbrueche.svg)

![PPO-Diagnose](diagramme/ppo.svg)

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

## Konfiguration gegenüber EXP-004 (1 Unterschiede)

Geplante Änderung: Trainingsmasse der Dose 0,04–0,4 kg statt 0,05–0,2 kg (Dexsuite: 0,2 kg × 0,2–2; Task Pib-Grasp-Hand-Left-Heavy-v0).

- `env.events.object_mass.params.mass_distribution_params: (0.05, 0.2) → (0.04, 0.4)`
