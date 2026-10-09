# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-09

### Zuletzt gearbeitet an

1. **Experiment-Framework** (`isaac_lab/experiments.py`, `plot_training.py`, `eval_policy.py`): automatische HF-Sicherung in `done`, Trainings-/Bedingungs-/Verlaufsdiagramme (SVG), mehrere Bedingungen je Experiment, Objektkatalog (`env_cfg.OBJECTS`), Experimente ohne Training, **Auswertung v2** (Leistung = IQM erfolgreicher Seeds, Zuverlässigkeit k/n; ADR-019), **Leaderboard nach Leistung** (`experiments/leaderboard.md`), Testobjekte, Videos je Seed + beste Videos (3 Episoden, im Git), Regel-Experimente (ADR-020).
2. **Experimente EXP-008–017**: Transfer (008–011), Belohnung wie Dexsuite (012), Objektvielfalt 18 Formen (013, `HeavyMulti-v0`), Regel-Baselines (014/015), Randomisierung (016), **Curriculum wie Dexsuite (017, Platz 1: Leistung 80 %, aber 2/5 Seeds, Unruhe 2,55)**; EXP-004–007 auf 5 Seeds.
3. **Fehler gefunden**: Annäherungsterm maß alle Handkörper (Standardargument-`SceneEntityCfg` nicht aufgelöst, ADR-017-Korrektur); Startbeugung Finger/Handgelenk überlappte bei breiten Formen (`tools/check_multi.py`); Curriculum-Schwierigkeit muss Tensor sein (EXP-017 erster Lauf abgestürzt).
4. Doku: ADR-018 (Spezialist je Greifart), ADR-019 (Benchmark/Leaderboard/Auswertung v2), ADR-020 (Regel-Baselines), Sprint „Plan ab 2026-10-09“.

### Offene Punkte

- Urteile EXP-012–017 nicht von Leon bestätigt (Ergebnis + Schluss als Entwurf in den `EXP-NNN_experiment.yaml`).
- Quader ist bei RL und Regel der Engpass (52–64 %) — Ursache unklar (Hand/Geometrie, nicht Training).
- Seeds, die gar nicht greifen lernen (EXP-004/012/013/017); beim Curriculum bleiben 3/5 bei Schwerkraft 0 hängen.
- Unruhe der besten Policies hoch (EXP-017 2,55, EXP-012 2,8; Regel 0,01) — Hardware-Risiko.
- YCB-Masse: Entscheidung Leon offen (Vorschlag: echte Masse 0,4–0,6 kg).

### Nächste Schritte (in Reihenfolge)

1. **Prio 1 YCB-Testobjekte**: 003 Cracker, 004 Zucker, 006 Senf (Isaac Sim 5.1 hat nur diese + 005 mit Physik unter `Props/YCB/Axis_Aligned_Physics/`) in `OBJECTS`/`TESTOBJEKTE` (UsdFileCfg, Lage per Bounding Box, Ausrichtung je Objekt), Szenenprüfung mit Bildern, Nachbewertung (`leaderboard --bewerten`).
2. **Prio 2 EXP-018 Strafen-Curriculum wie Isaac Lab Lift** (Eltern EXP-017; Aktionsstrafen −0,005 bis ~It. 400, dann ~−0,05; Endwert per `tools/reward_diag.py`); danach **EXP-019 Aktionsfilter** (EMA wie DeXtreme, α ≈ 0,5).
3. Leon die Urteile EXP-012–017 bestätigen lassen; Videos (`experiments/EXP-0xx_*/beste_videos/`) sichten.
4. Später: Servo-Systemidentifikation (LeRobot Feetech), Greif-Ablauf (Romano 2011, Ablegen), Lehrer–Schüler (HORA/RMA), int8 im Sim-Loop, „von oben“ mit dem besten Rezept.

### Wichtige Kontextdetails

- **Leon (2026-10-08): Leistung vor Zuverlässigkeit** — eine brauchbare Policy je Greifart genügt; Leaderboard danach sortiert.
- **Eltern für Neues: EXP-017** (Unruhe-Experimente) bzw. **EXP-013** (Objektvielfalt-Setup); Varianten als Task-IDs (`HeavyMulti`, `HeavyMultiADR`, `HeavyMultiRand`, `HeavyDexsuite`), bewertet immer in der Basisaufgabe.
- **Dexsuite hat kein Strafen-Curriculum** (nur Isaac Lab Lift: `modify_reward_weight`); Dexsuite-Curriculum = Schwerkraft + Rauschen, bei uns via `mdp.GraspDifficultyScheduler` + Dexsuite-`initial_final_interpolate_fn`.
- Kurztests müssen alle Codepfade treffen (Curriculum-Interpolation erst ab Schwierigkeit 0,1 → Test mit `env.curriculum.adr.params.init_difficulty=6`).
- `pkill -f` mit einem Muster aus der eigenen Befehlszeile beendet die eigene Shell (zweimal passiert) — Testläufe nicht über pkill aufräumen.
- Aktion ist auf 0,1 rad (5,7°) je Schritt begrenzt (Regel-Raster entsprechend); YCB nicht ins Training (Bewertungsdatensatz), Massen aus YCB fürs Training übernehmen, falls nötig.
- Kamera/Licht für Videos: schräg, schwarzer Hintergrund, Hauptlicht (`env_cfg` `viewer`/`sun`), zählt nicht als Konfigurationsunterschied. Videos aller Seeds nur auf HF, beste im Git.
- Leon bisweilen remote: Fenstertests dann durch Szenenprüfung mit Bildern ersetzen; vor Pushs fragen (Ausnahme: er bittet ausdrücklich).
