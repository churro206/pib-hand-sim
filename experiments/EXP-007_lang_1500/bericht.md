# EXP-007: EXP-004 mit 1500 Iterationen

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 45°), Protokoll eval-v1, 3 Seed(s); Eltern-Spalte unter derselben Bedingung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | Eltern (Mittel / IQM) |
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

**Urteilsvorschlag: kein messbarer Unterschied**
Unterschied Aufgabenerfolg -8.3 Prozentpunkte (95-%-KI -33.6 … +6.7)
- Leitplanke: Unruhe: 1.86 > 1.21

Je Seed: 92.0 %, 21.7 %, 94.5 %

Fingernutzung (Haltephase): im Mittel 2.25 Finger an der Dose; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 97/100/0/0/2 · 100/75/0/0/100 · 100/0/100/0/0

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 1500 Iterationen

## Konfiguration gegenüber EXP-004 (1 Unterschiede)

Geplante Änderung: Trainingsdauer 1500 statt 300 Iterationen.

- `agent.max_iterations: 300 → 1500`
