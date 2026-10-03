# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-03

### Zuletzt gearbeitet an

1. **Sehnendynamik verworfen, Branch auf `0fdbc62` zurückgesetzt** — `1d0cd9c` (Script Node, ADR-009) lebt im Tag `backup/sehnendynamik-1d0cd9c` und auf `feature/rl-grasping`; Vorsession-Experimente (Kraft-Rückwirkung, Mimic-Vorprüfungen, `tendondrive/PROMPT_*.md`) liegen nur in `stash@{0}`.
2. **PhysX Mimic Joints** (ADR-011): `isaac_sim/setup_stage.py` → `MIMIC_JOINTS` + `configure_mimic_joints()`, von `start.py` jede Session gesetzt; 18 Folgegelenke passiv, gearing=-1.
3. **Servo-Aktuatormodell + Self-Collision** (ADR-012): MCP/Rotator/Handgelenk/Unterarm auf ST3215-Datenblatt (2,94 Nm, 270 °/s, 0,588 Nm/°, ζ=1, Armature 5e-3); Self-Collision am `root_joint` an → Tischtest stabil. Action Graph auf `OnPhysicsStep`.
4. **Werkzeuge**: `test_client_mimic_v5`, `test_client_mimic_load_v5` (Finger gegen Tisch, Diagnose), `isaac_sim/tools/audit_asset.py`; Unterarm-Masse 30 g → 0,229 kg (URDFs + USD). Commit `383c4ef`, Doku `f2c4e67`, origin per Force-Push auf diesen Stand gebracht.
5. **Schritt 3/4 abgeschlossen**: `setup_stage.py` → `SERVOS` + `V5_ACTUATORS` für alle v5-Servo-Gelenke (Schultern ST3095 9,32 Nm/186 °/s, Rest ST3215), Experiment-Schalter entfernt, v4 zurück auf `0fdbc62`-Werte. Pickup: Arm hält die Dose nur knapp, Tischtest: Ellbogen gibt nach — beides realistisch (Leon).

### Offene Punkte

- Nach der Arm-Umstellung bestanden: `audit_asset.py` (keine Warnung), `test_client_mimic_v5 --finger all`; nur Putdown-Demo v5 nicht erneut getestet.
- Arm/Handgelenk hängen unter Last sichtbar durch (Handgelenk −5,6° in der Tisch-Testpose) — akzeptiert; Stellschraube `SERVO_SATURATION_ERROR_DEG`.
- Contact Sensors v5: alle 10 Fingerspitzen offen; `index_right`-Reader im Graph zeigt laut Inventur auf den Roboter-Wrapper, kein Sensor-Prim.
- Warum Self-Collision das Wegfliegen behoben hat, ist nicht erklärt (empirischer Befund).

### Nächste Schritte (in Reihenfolge)

1. Contact Sensors für alle 10 v5-Fingerspitzen (ADR-008-Muster), vorher den halb verkabelten `index_right`-Reader im v5-Graph prüfen.
2. Putdown-Demo v5 als letzte Regression (`test_client_putdown_v5`).
3. Optional: `SERVO_SATURATION_ERROR_DEG` kleiner, falls das Durchhängen stört (danach Audit).

### Wichtige Kontextdetails

- **Einheiten**: Angular-Drive-Stiffness/Damping am Prim sind pro **Grad** (USD-Schema) — 500 Nm/° ≈ 28.650 Nm/rad; `maxJointVelocity` in °/s. PhysX-Massenmatrix enthält die Armature **nicht**.
- **Isaac Sim 5.1** hat keine Mimic-Compliance (`naturalFrequency`/`dampingRatio`) und kein `solveArticulationContactLast` — die NVIDIA-Tutorials dazu sind 6.0.
- Zeitschritt 60 → 240 Hz brachte nichts; Ursache waren die Gains (ω_n·Δt ≫ 1), nicht Δt.
- Warnung `'NoneType' object has no attribute 'create_articulation_view'` einmal pro Play ist harmlos (erster Physikschritt vor Sim-View-Erzeugung).
- Akzeptiert (Leon: "reale Gelenke auch nicht perfekt"): Handgelenk hängt in der Tisch-Testpose 2,7–5,4° durch, Daumen/Zeigefinger blockieren sich bei voller Beugung (~70°), übrige Finger stoppen ~88,5°.
- Onshape-Massen = Vollmaterial-PLA (1,30 g/cm³) ohne Servos/Infill — bewusst belassen.
- Robot-Collider stecken in instanzierten `collisions`-Kindern → Viewport-Collider-Anzeige zeigt sie erst mit Instanceable aus (die Links selbst sind nicht instanceable).
- Leon stellt einfache Stage-/Graph-Änderungen im GUI ein — dafür keine Skripte schreiben.
