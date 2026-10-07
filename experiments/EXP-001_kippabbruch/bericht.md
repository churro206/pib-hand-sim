# EXP-001: Kippabbruch + Aufrecht-Belohnung

Bedingung `zylinder_seitlich`, Protokoll eval-v1, 6 Seed(s)

| Metrik | Wert | 95-%-KI | Eltern |
|---|---|---|---|
| aufgabenerfolg | 0.0 % | 0.0 % – 0.0 % | 0.0 % |
| haltequote | 0.0 % | 0.0 % – 0.0 % | 86.1 % |
| Kippwinkel Median [°] | – | | 104 |
| Unterarm Median [°] | – | | 90 |
| Griffkraft Mittel [N] | – | | 23.9 |
| Kraft > 15 N [Anteil] | – | | 9.3 % |
| Stall-Anteil [Anteil] | – | | 99.6 % |
| Absinken [mm] | – | | 0 |
| Unruhe | – | | 0.244 |

Fehlerarten: startfehler 1.8 %, gefallen 98.2 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)**
Unterschied Aufgabenerfolg +0.0 Prozentpunkte (95-%-KI +0.0 … +0.0)

Je Seed: 0.0 %, 0.0 %, 0.0 %, 0.0 %, 0.0 %, 0.0 %

## Netz und Training

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

## Konfiguration gegenüber EXP-000 (15 Unterschiede)

Geplante Änderung: Abbruch object_tilted (> 20°), Belohnung upright (Gewicht 2, ab dem Absenken), Objektorientierung im Critic

- `env.observations.critic.object_quat.clip: ∅ → None`
- `env.observations.critic.object_quat.flatten_history_dim: ∅ → True`
- `env.observations.critic.object_quat.func: ∅ → pib_grasp.mdp:object_quat_in_root`
- `env.observations.critic.object_quat.history_length: ∅ → 0`
- `env.observations.critic.object_quat.modifiers: ∅ → None`
- `env.observations.critic.object_quat.noise: ∅ → None`
- `env.observations.critic.object_quat.scale: ∅ → None`
- `env.rewards.early_termination.params.term_keys: ['object_dropped', 'abnormal_robot'] → ['object_dropped', 'object_tilted', 'abnormal_robot']`
- `env.rewards.upright.func: ∅ → pib_grasp.mdp:object_upright`
- `env.rewards.upright.params.drop_start_s: ∅ → 2.0`
- `env.rewards.upright.params.std: ∅ → 0.2`
- `env.rewards.upright.weight: ∅ → 2.0`
- `env.terminations.object_tilted.func: ∅ → pib_grasp.mdp:object_tilted`
- `env.terminations.object_tilted.params.max_tilt_deg: ∅ → 20.0`
- `env.terminations.object_tilted.time_out: ∅ → False`
