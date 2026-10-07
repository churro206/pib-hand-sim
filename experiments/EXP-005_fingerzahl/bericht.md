# EXP-005: Kontaktbelohnung nach Fingerzahl

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 45°), Protokoll eval-v1, 3 Seed(s); Eltern-Spalte unter derselben Bedingung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | Eltern (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 65.1 % | 14.6 % – 92.9 % | 76.4 % | 33.3 % | 77.3 % / 82.5 % |
| haltequote | 90.1 % | 83.6 % – 94.4 % | 91.9 % | 0.0 % | 90.1 % / 90.3 % |
| Kippwinkel Median [°] | 37.8 | | | | 26.6 |
| Unterarm Median [°] | 46.5 | | | | 25.8 |
| Griffkraft Mittel [N] | 80.9 | | | | 58.4 |
| Kraft > 15 N [Anteil] | 99.8 % | | | | 99.2 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 99.7 % |
| Absinken [mm] | 0.0284 | | | | 0.0255 |
| Unruhe | 0.481 | | | | 1.01 |

Fehlerarten: startfehler 0.6 %, gefallen 9.3 %, instabil 0.0 %, anforderung_verletzt 25.0 %

**Urteilsvorschlag: kein messbarer Unterschied**
Unterschied Aufgabenerfolg -12.7 Prozentpunkte (95-%-KI -41.1 … +4.6)
- Leitplanke: Kippwinkel Median [°]: 37.8 > 31.6
- Leitplanke: Unterarm Median [°]: 46.5 > 35.8
- Leitplanke: Griffkraft Mittel [N]: 80.9 > 70.1

Je Seed: 93.2 %, 14.4 %, 87.7 %

Fingernutzung (Haltephase): im Mittel 2.63 Finger an der Dose; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/94/99/4/0 · 100/0/0/99/95 · 99/100/0/0/0

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

## Konfiguration gegenüber EXP-004 (3 Unterschiede)

Geplante Änderung: Zusätzlicher Belohnungsterm finger_count = 1 · (Finger mit Objektkontakt > 1 N)/4 · 𝟙[Daumen in Kontakt], ganze Episode (Task Pib-Grasp-Hand-Left-FingerCount-v0).

- `env.rewards.finger_count.func: ∅ → pib_grasp.mdp:fingers_in_contact`
- `env.rewards.finger_count.params.threshold: ∅ → 1.0`
- `env.rewards.finger_count.weight: ∅ → 1.0`
