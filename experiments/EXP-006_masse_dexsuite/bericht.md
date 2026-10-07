# EXP-006: Objektmasse wie Dexsuite (0,04–0,4 kg)

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 45°), Protokoll eval-v1, 3 Seed(s); Eltern-Spalte unter derselben Bedingung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | Eltern (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 71.5 % | 27.2 % – 94.5 % | 82.4 % | 33.3 % | 77.3 % / 82.5 % |
| haltequote | 94.7 % | 93.8 % – 95.5 % | 94.7 % | 0.0 % | 90.1 % / 90.3 % |
| Kippwinkel Median [°] | 33.8 | | | | 26.6 |
| Unterarm Median [°] | 42.6 | | | | 25.8 |
| Griffkraft Mittel [N] | 85.3 | | | | 58.4 |
| Kraft > 15 N [Anteil] | 99.9 % | | | | 99.2 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 99.7 % |
| Absinken [mm] | 0.0343 | | | | 0.0255 |
| Unruhe | 0.35 | | | | 1.01 |

Fehlerarten: startfehler 0.5 %, gefallen 4.8 %, instabil 0.0 %, anforderung_verletzt 23.2 %

**Urteilsvorschlag: kein messbarer Unterschied**
Unterschied Aufgabenerfolg -6.2 Prozentpunkte (95-%-KI -28.6 … +7.0)
- Leitplanke: Kippwinkel Median [°]: 33.8 > 31.6
- Leitplanke: Unterarm Median [°]: 42.6 > 35.8
- Leitplanke: Griffkraft Mittel [N]: 85.3 > 70.1

Je Seed: 93.3 %, 26.9 %, 94.3 %

Fingernutzung (Haltephase): im Mittel 2.96 Finger an der Dose; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/95/100/95/0 · 100/0/94/0/100 · 97/99/4/3/0

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

## Konfiguration gegenüber EXP-004 (1 Unterschiede)

Geplante Änderung: Trainingsmasse der Dose 0,04–0,4 kg statt 0,05–0,2 kg (Dexsuite: 0,2 kg × 0,2–2; Task Pib-Grasp-Hand-Left-Heavy-v0).

- `env.events.object_mass.params.mass_distribution_params: (0.05, 0.2) → (0.04, 0.4)`
