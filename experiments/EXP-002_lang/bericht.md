# EXP-002: Langer Lauf (Lift-Rezept: 1500 Iterationen)

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 20°), Protokoll eval-v1, 3 Seed(s); Eltern-Spalte unter derselben Bedingung

| Metrik | Wert | 95-%-KI | Eltern |
|---|---|---|---|
| aufgabenerfolg | 0.0 % | 0.0 % – 0.0 % | 0.0 % |
| haltequote | 0.0 % | 0.0 % – 0.0 % | 0.0 % |
| Kippwinkel Median [°] | – | | – |
| Unterarm Median [°] | – | | – |
| Griffkraft Mittel [N] | – | | – |
| Kraft > 15 N [Anteil] | – | | – |
| Stall-Anteil [Anteil] | – | | – |
| Absinken [mm] | – | | – |
| Unruhe | – | | – |

Fehlerarten: startfehler 2.1 %, gefallen 97.9 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied**
Unterschied Aufgabenerfolg +0.0 Prozentpunkte (95-%-KI +0.0 … +0.0)

Je Seed: 0.0 %, 0.0 %, 0.0 %

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 1500 Iterationen

## Konfiguration gegenüber EXP-001 (1 Unterschiede)

Geplante Änderung: Trainingsdauer 1500 statt 300 Iterationen (Umgebungen unverändert 1024)

- `agent.max_iterations: 300 → 1500`
