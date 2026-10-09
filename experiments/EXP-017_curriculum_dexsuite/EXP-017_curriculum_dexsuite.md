# EXP-017: Curriculum wie Dexsuite (Schwerkraft und Beobachtungsrauschen nach Erfolg), 1500 Iterationen

**Leistung** 80 % [78–81 %] (erfolgreiche Seeds, IQM über die Objekte; je Objekt Ø 6 cm 90 % · Ø 8 cm 81 % · Quader 64 %) — ggü. EXP-013: P(besser) = 0.72 [0.50–0.94] → kein Unterschied

**Testobjekte** (nie trainiert, erfolgreiche Seeds, Median): Flasche 83 % · Saftpackung 70 %

**Zuverlässigkeit** 2/5 Seeds erfolgreich [5–85 %] — EXP-013: 3/5, exakter Fisher-Test p = 1.00 → nicht unterscheidbar (für eine Aussage ≥ 10 Seeds je Experiment)

**Leitplanken** Griffkraft Mittel [N]: 119 > 112; Unruhe: 2.55 > 0.846 ✗

**Befund** ohne Erfolg: Seed 42 (lernt nicht zu greifen), Seed 44 (lernt nicht zu greifen), Seed 46 (lernt nicht zu greifen); Engpass Quader (64 %); Unruhe 2.55 (EXP-013: 0.70)

**Urteilsvorschlag** (auswertung-v2): **kein Unterschied, Leitplanke verletzt**

**Beste Videos** (Seed 45, 3 Episoden): [Ø 6 cm](beste_videos/EXP-017_zylinder_d6_s45.mp4) · [Ø 8 cm](beste_videos/EXP-017_zylinder_d8_s45.mp4) · [Quader](beste_videos/EXP-017_quader_7x7x20_s45.mp4)

![Ergebnis je Bedingung — Punkte = Seeds](diagramme/EXP-017_bedingungen.svg)

![Verlauf über die Episode](diagramme/EXP-017_verlauf.svg)

<details>
<summary>Ergebnisse je Bedingung (eval-v1, Leitplanken, Fehlerarten, Fingernutzung)</summary>


#### Bedingung `zylinder_seitlich`

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 35.9 % | 0.0 % – 72.5 % | 26.3 % | 60.0 % | 50.3 % / 56.6 % |
| haltequote | 37.5 % | 0.0 % – 75.3 % | 28.1 % | 60.0 % | 55.6 % / 64.1 % |
| Kippwinkel Median [°] | 23.6 | | | | 27.1 |
| Unterarm Median [°] | 24.8 | | | | 32 |
| Griffkraft Mittel [N] | 119 | | | | 93.5 |
| Kraft > 15 N [Anteil] | 99.9 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 100.0 % |
| Absinken [mm] | 0.00684 | | | | 0.000794 |
| Unruhe | 2.55 | | | | 0.705 |

Fehlerarten: startfehler 0.7 %, gefallen 61.8 %, instabil 0.0 %, anforderung_verletzt 1.6 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -15.5 Prozentpunkte (95-%-KI -67.9 … +38.3)
- Leitplanke: Griffkraft Mittel [N]: 119 > 112
- Leitplanke: Unruhe: 2.55 > 0.846

Je Seed: 0.0 %, 87.7 %, 0.0 %, 91.9 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.44 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 99/74/99/81/46 · –/–/–/–/– · 99/0/91/99/0 · –/–/–/–/–

#### Bedingung `zylinder_d8_seitlich`

Bedingung `zylinder_d8_seitlich` (Objekt `zylinder_d8`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 32.5 % | 0.0 % – 65.4 % | 24.0 % | 60.0 % | 49.4 % / 55.6 % |
| haltequote | 33.0 % | 0.0 % – 66.6 % | 24.3 % | 60.0 % | 51.1 % / 57.7 % |
| Kippwinkel Median [°] | 10.1 | | | | 21.6 |
| Unterarm Median [°] | 7.21 | | | | 30.6 |
| Griffkraft Mittel [N] | 110 | | | | 90 |
| Kraft > 15 N [Anteil] | 99.7 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 100.0 % |
| Absinken [mm] | 0.0599 | | | | 0 |
| Unruhe | 1.23 | | | | 0.845 |

Fehlerarten: startfehler 0.6 %, gefallen 66.3 %, instabil 0.0 %, anforderung_verletzt 0.5 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -18.0 Prozentpunkte (95-%-KI -68.3 … +33.8)
- Leitplanke: Griffkraft Mittel [N]: 110 > 108
- Leitplanke: Unruhe: 1.23 > 1.01

Je Seed: 0.0 %, 80.1 %, 0.0 %, 82.4 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.43 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/95/98/94/3 · –/–/–/–/– · 100/0/100/97/0 · –/–/–/–/–

#### Bedingung `quader_seitlich`

Bedingung `quader_seitlich` (Objekt `quader_7x7x20`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 25.5 % | 0.0 % – 51.6 % | 18.9 % | 60.0 % | 33.6 % / 37.0 % |
| haltequote | 25.7 % | 0.0 % – 51.8 % | 19.1 % | 60.0 % | 36.4 % / 41.5 % |
| Kippwinkel Median [°] | 10.1 | | | | 22.6 |
| Unterarm Median [°] | 8.2 | | | | 31.5 |
| Griffkraft Mittel [N] | 102 | | | | 80.9 |
| Kraft > 15 N [Anteil] | 99.3 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 100.0 % |
| Absinken [mm] | 1.11 | | | | 0.00647 |
| Unruhe | 2.05 | | | | 0.931 |

Fehlerarten: startfehler 6.7 %, gefallen 67.7 %, instabil 0.0 %, anforderung_verletzt 0.1 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -8.9 Prozentpunkte (95-%-KI -45.4 … +28.6)
- Leitplanke: Griffkraft Mittel [N]: 102 > 97.1
- Leitplanke: Unruhe: 2.05 > 1.12

Je Seed: 0.0 %, 63.0 %, 0.0 %, 64.6 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.24 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/95/96/78/2 · –/–/–/–/– · 98/0/98/82/0 · –/–/–/–/–

#### Bedingung `flasche_seitlich`

Bedingung `flasche_seitlich` (Objekt `flasche_d7x25`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 33.4 % | 0.0 % – 67.4 % | 24.5 % | 60.0 % | 49.1 % / 55.4 % |
| haltequote | 35.1 % | 0.0 % – 70.5 % | 26.2 % | 60.0 % | 51.7 % / 59.1 % |
| Kippwinkel Median [°] | 16.8 | | | | 23.7 |
| Unterarm Median [°] | 9.25 | | | | 30.1 |
| Griffkraft Mittel [N] | 114 | | | | 91.9 |
| Kraft > 15 N [Anteil] | 99.7 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 100.0 % |
| Absinken [mm] | 0.0312 | | | | 0.0287 |
| Unruhe | 1.52 | | | | 0.802 |

Fehlerarten: startfehler 0.5 %, gefallen 64.4 %, instabil 0.0 %, anforderung_verletzt 1.8 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -16.9 Prozentpunkte (95-%-KI -68.2 … +36.0)
- Leitplanke: Griffkraft Mittel [N]: 114 > 110
- Leitplanke: Unruhe: 1.52 > 0.962

Je Seed: 0.0 %, 85.0 %, 0.0 %, 81.8 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.37 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/93/98/84/3 · –/–/–/–/– · 100/0/98/98/0 · –/–/–/–/–

#### Bedingung `saftpackung_seitlich`

Bedingung `saftpackung_seitlich` (Objekt `saftpackung_9x6x19`, Kippwinkel ≤ 45°), Protokoll eval-v1, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 27.9 % | 0.0 % – 56.3 % | 20.9 % | 60.0 % | 39.6 % / 45.4 % |
| haltequote | 28.3 % | 0.0 % – 56.9 % | 21.2 % | 60.0 % | 41.7 % / 47.5 % |
| Kippwinkel Median [°] | 14.7 | | | | 23.2 |
| Unterarm Median [°] | 12.9 | | | | 33.9 |
| Griffkraft Mittel [N] | 95.1 | | | | 81.7 |
| Kraft > 15 N [Anteil] | 99.3 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 100.0 % | | | | 100.0 % |
| Absinken [mm] | 1.68 | | | | 0 |
| Unruhe | 2.52 | | | | 0.83 |

Fehlerarten: startfehler 4.8 %, gefallen 67.0 %, instabil 0.0 %, anforderung_verletzt 0.4 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -12.6 Prozentpunkte (95-%-KI -52.6 … +29.4)
- Leitplanke: Unruhe: 2.52 > 0.995

Je Seed: 0.0 %, 69.7 %, 0.0 %, 69.9 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.21 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/99/99/60/10 · –/–/–/–/– · 97/0/99/78/0 · –/–/–/–/–

</details>

<details>
<summary>Trainingsverlauf</summary>


Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten 10 Iterationen (Belohnungsanteile je Sekunde Episode).

| Größe | Seed 42 | Seed 43 | Seed 44 | Seed 45 | Seed 46 | Mittel |
|---|---|---|---|---|---|---|
| mean_reward | 2.37 | 29.5 | 2.37 | 28.3 | 2.34 | 13 |
| action_l2 | -0.00351 | -0.295 | -0.00334 | -0.354 | -0.00499 | -0.132 |
| action_rate_l2 | -0.00402 | -0.179 | -0.00462 | -0.203 | -0.00703 | -0.0796 |
| early_termination | 0 | -7.23e-06 | 0 | 0 | 0 | -1.45e-06 |
| fingertips_to_object | 0.155 | 0.329 | 0.155 | 0.424 | 0.155 | 0.244 |
| good_contact | 0 | 0.407 | 1.45e-06 | 0.406 | 0 | 0.163 |
| held | 0 | 0.894 | 0 | 0.892 | 0 | 0.357 |
| success | 0.381 | 3.66 | 0.382 | 3.35 | 0.378 | 1.63 |
| upright | 0 | 1.76 | 0 | 1.74 | 0 | 0.7 |
| object_dropped | 100.0 % | 15.6 % | 100.0 % | 13.7 % | 100.0 % | 65.9 % |
| mean_noise_std | 0.298 | 1.4 | 0.325 | 1.49 | 0.388 | 0.78 |

![Lernkurve](diagramme/EXP-017_lernkurve.svg)

![Belohnungsanteile](diagramme/EXP-017_belohnung.svg)

![Abbrüche](diagramme/EXP-017_abbrueche.svg)

![PPO-Diagnose](diagramme/EXP-017_ppo.svg)

</details>

<details>
<summary>Videos aller Seeds</summary>

16 Umgebungen, eine Episode (nicht im Git, Hugging Face).

| Objekt | Seed 42 | Seed 43 | Seed 44 | Seed 45 | Seed 46 |
|---|---|---|---|---|---|
| `quader_7x7x20` | [▶](videos/EXP-017_quader_7x7x20_s42.mp4) | [▶](videos/EXP-017_quader_7x7x20_s43.mp4) | [▶](videos/EXP-017_quader_7x7x20_s44.mp4) | [▶](videos/EXP-017_quader_7x7x20_s45.mp4) | [▶](videos/EXP-017_quader_7x7x20_s46.mp4) |
| `zylinder_d6` | [▶](videos/EXP-017_zylinder_d6_s42.mp4) | [▶](videos/EXP-017_zylinder_d6_s43.mp4) | [▶](videos/EXP-017_zylinder_d6_s44.mp4) | [▶](videos/EXP-017_zylinder_d6_s45.mp4) | [▶](videos/EXP-017_zylinder_d6_s46.mp4) |
| `zylinder_d8` | [▶](videos/EXP-017_zylinder_d8_s42.mp4) | [▶](videos/EXP-017_zylinder_d8_s43.mp4) | [▶](videos/EXP-017_zylinder_d8_s44.mp4) | [▶](videos/EXP-017_zylinder_d8_s45.mp4) | [▶](videos/EXP-017_zylinder_d8_s46.mp4) |

</details>

<details>
<summary>Netz, Training und Konfiguration</summary>

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 1500 Iterationen

Geplante Änderung: Curriculum wie Dexsuite (Task HeavyMultiADR-v0, adr_curriculum.py): Schwierigkeit 0–10 je Umgebung nach Erfolg (gehalten, Kipp ≤ 45°), Schwerkraft 0 → 9,81 m/s², Rauschen der Gelenkwinkel 0 → ±0,1 rad; FSR ohne Rauschen. Dazu 1500 statt 300 Iterationen, weil das Curriculum Zeit braucht (EXP-011: 1500 It. allein ohne Wirkung). Bewertung ohne Curriculum (volle Schwerkraft, kein Rauschen).

Konfiguration gegenüber EXP-013 (38 Unterschiede):

- `agent.max_iterations: 300 → 1500`
- `env.curriculum: None → ∅`
- `env.curriculum.adr.func: ∅ → pib_grasp.mdp:GraspDifficultyScheduler`
- `env.curriculum.adr.params.init_difficulty: ∅ → 0`
- `env.curriculum.adr.params.max_difficulty: ∅ → 10`
- `env.curriculum.adr.params.max_kipp_deg: ∅ → 45.0`
- `env.curriculum.adr.params.min_difficulty: ∅ → 0`
- `env.curriculum.gravity_adr.func: ∅ → isaaclab.envs.mdp.curriculums:modify_term_cfg`
- `env.curriculum.gravity_adr.params.address: ∅ → events.variable_gravity.params.gravity_distribution_params`
- `env.curriculum.gravity_adr.params.modify_fn: ∅ → isaaclab_tasks.manager_based.manipulation.dexsuite.mdp.curriculums:initial_final_interpolate_fn`
- `env.curriculum.gravity_adr.params.modify_params.difficulty_term_str: ∅ → adr`
- `env.curriculum.gravity_adr.params.modify_params.final_value: ∅ → ([0.0, 0.0, -9.81], [0.0, 0.0, -9.81])`
- `env.curriculum.gravity_adr.params.modify_params.initial_value: ∅ → ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])`
- `env.curriculum.joint_pos_noise_max_adr.func: ∅ → isaaclab.envs.mdp.curriculums:modify_term_cfg`
- `env.curriculum.joint_pos_noise_max_adr.params.address: ∅ → observations.policy.joint_pos.noise.n_max`
- `env.curriculum.joint_pos_noise_max_adr.params.modify_fn: ∅ → isaaclab_tasks.manager_based.manipulation.dexsuite.mdp.curriculums:initial_final_interpolate_fn`
- `env.curriculum.joint_pos_noise_max_adr.params.modify_params.difficulty_term_str: ∅ → adr`
- `env.curriculum.joint_pos_noise_max_adr.params.modify_params.final_value: ∅ → 0.1`
- `env.curriculum.joint_pos_noise_max_adr.params.modify_params.initial_value: ∅ → 0.0`
- `env.curriculum.joint_pos_noise_min_adr.func: ∅ → isaaclab.envs.mdp.curriculums:modify_term_cfg`
- `env.curriculum.joint_pos_noise_min_adr.params.address: ∅ → observations.policy.joint_pos.noise.n_min`
- `env.curriculum.joint_pos_noise_min_adr.params.modify_fn: ∅ → isaaclab_tasks.manager_based.manipulation.dexsuite.mdp.curriculums:initial_final_interpolate_fn`
- `env.curriculum.joint_pos_noise_min_adr.params.modify_params.difficulty_term_str: ∅ → adr`
- `env.curriculum.joint_pos_noise_min_adr.params.modify_params.final_value: ∅ → -0.1`
- `env.curriculum.joint_pos_noise_min_adr.params.modify_params.initial_value: ∅ → 0.0`
- `env.events.variable_gravity.func: ∅ → isaaclab.envs.mdp.events:randomize_physics_scene_gravity`
- `env.events.variable_gravity.interval_range_s: ∅ → None`
- `env.events.variable_gravity.is_global_time: ∅ → False`
- `env.events.variable_gravity.min_step_count_between_reset: ∅ → 0`
- `env.events.variable_gravity.mode: ∅ → reset`
- `env.events.variable_gravity.params.gravity_distribution_params: ∅ → ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])`
- `env.events.variable_gravity.params.operation: ∅ → abs`
- `env.observations.policy.enable_corruption: False → True`
- `env.observations.policy.joint_pos.noise: None → ∅`
- `env.observations.policy.joint_pos.noise.func: ∅ → isaaclab.utils.noise.noise_model:uniform_noise`
- `env.observations.policy.joint_pos.noise.n_max: ∅ → 0.0`
- `env.observations.policy.joint_pos.noise.n_min: ∅ → 0.0`
- `env.observations.policy.joint_pos.noise.operation: ∅ → add`

</details>
