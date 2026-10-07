# EXP-000: Probelauf Dexsuite-Muster (Ausgangswert)

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 20°), Protokoll eval-v1, 1 Seed(s); Eltern-Spalte unter derselben Bedingung

| Metrik | Wert | 95-%-KI | Eltern |
|---|---|---|---|
| aufgabenerfolg | 0.0 % | 0.0 % – 0.0 % | – |
| haltequote | 86.1 % | 84.1 % – 88.2 % | – |
| Kippwinkel Median [°] | 104 | | – |
| Unterarm Median [°] | 90 | | – |
| Griffkraft Mittel [N] | 23.9 | | – |
| Kraft > 15 N [Anteil] | 9.3 % | | – |
| Stall-Anteil [Anteil] | 99.6 % | | – |
| Absinken [mm] | 0 | | – |
| Unruhe | 0.244 | | – |

Fehlerarten: startfehler 1.9 %, gefallen 12.1 %, instabil 0.0 %, anforderung_verletzt 86.1 %

**Urteilsvorschlag: kein Vergleich (keine Eltern-Bewertung mit gleichem Protokoll)**

Je Seed: 0.0 %

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen
