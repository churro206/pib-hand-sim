# EXP-003: Kippen über multiplikative Belohnung statt Abbruch (Dexsuite)

Bedingung `zylinder_seitlich` (Kippwinkel ≤ 45°), Protokoll eval-v1, 3 Seed(s); Eltern-Spalte unter derselben Bedingung

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

Fehlerarten: startfehler 0.5 %, gefallen 99.5 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied**
Unterschied Aufgabenerfolg +0.0 Prozentpunkte (95-%-KI +0.0 … +0.0)

Je Seed: 0.0 %, 0.0 %, 0.0 %

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

## Konfiguration gegenüber EXP-001 (10 Unterschiede)

Geplante Änderung: Kippabbruch entfernt; Halte-Belohnung multiplikativ mit Aufrecht-Faktor (rot_std 0,5 rad wie Dexsuite success_reward) statt additiver Aufrecht-Belohnung. Bedingung: Anforderung ≤ 45° (Leon 2026-10-07, verschlossene Packung) — wird bei der Auswertung angewandt, Eltern unter derselben Bedingung.

- `env.rewards.early_termination.params.term_keys: ['object_dropped', 'object_tilted', 'abnormal_robot'] → ['object_dropped', 'abnormal_robot']`
- `env.rewards.held.func: pib_grasp.mdp:object_held → pib_grasp.mdp:object_held_upright`
- `env.rewards.held.params.rot_std: ∅ → 0.5`
- `env.rewards.upright.func: pib_grasp.mdp:object_upright → ∅`
- `env.rewards.upright.params.drop_start_s: 2.0 → ∅`
- `env.rewards.upright.params.std: 0.2 → ∅`
- `env.rewards.upright.weight: 2.0 → ∅`
- `env.terminations.object_tilted.func: pib_grasp.mdp:object_tilted → ∅`
- `env.terminations.object_tilted.params.max_tilt_deg: 20.0 → ∅`
- `env.terminations.object_tilted.time_out: False → ∅`
