# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-03

### Zuletzt gearbeitet an

1. **Sehnendynamik verworfen, Branch auf `0fdbc62` zurückgesetzt** — `1d0cd9c` (Script Node, ADR-009) lebt im Tag `backup/sehnendynamik-1d0cd9c` und auf `feature/rl-grasping`; Vorsession-Experimente (Kraft-Rückwirkung, Mimic-Vorprüfungen, `tendondrive/PROMPT_*.md`) liegen nur in `stash@{0}`.
2. **PhysX Mimic Joints** (ADR-011): `isaac_sim/setup_stage.py` → `MIMIC_JOINTS` + `configure_mimic_joints()`, von `start.py` jede Session gesetzt; 18 Folgegelenke passiv, gearing=-1.
3. **Servo-Aktuatormodell + Self-Collision** (ADR-012): MCP/Rotator/Handgelenk/Unterarm auf ST3215-Datenblatt (2,94 Nm, 270 °/s, 0,588 Nm/°, ζ=1, Armature 5e-3); Self-Collision am `root_joint` an → Tischtest stabil. Action Graph auf `OnPhysicsStep`.
4. **Werkzeuge**: `test_client_mimic_v5`, `test_client_mimic_load_v5` (Finger gegen Tisch, Diagnose), `isaac_sim/tools/audit_asset.py`; Unterarm-Masse 30 g → 0,229 kg (URDFs + USD). Commit `383c4ef`, Doku auf ADR-010/011/012 nachgezogen.

### Offene Punkte

- **Arm/Kopf noch nicht auf das Aktuatormodell umgestellt**: `shoulder_*` (ST3095), `upper_arm_*`/`elbow_*`/`head_*` (ST3215) stehen auf 3000–5000 Nm/°, `maxForce=inf` — Audit: ω_n·Δt 26–95.
- `setup_stage.py` hat sieben Experiment-Schalter (`SERVO_*_ENABLED`, `FOLLOWER_*`, `ARM_GAIN_SCALE`) aus der Fehlersuche — sollen durch eine Aktuator-Tabelle ersetzt werden.
- Pickup-/Putdown-Demo v5 mit Mimic Joints + Self-Collision nicht erneut getestet.
- Contact Sensors v5: alle 10 Fingerspitzen offen; `index_right`-Reader im Graph zeigt laut Inventur auf den Roboter-Wrapper, kein Sensor-Prim.
- Warum Self-Collision das Wegfliegen behoben hat, ist nicht erklärt (empirischer Befund).

### Nächste Schritte (in Reihenfolge)

1. Schritt 3/4 des NVIDIA-Plans: Aktuator-Tabelle in `setup_stage.py` (ST3095 `shoulder_*` 9,32 Nm/186 °/s; ST3215 Rest 2,94 Nm/270 °/s), Stiffness = maxForce/5°, Damping ζ=1 mit I_eff = M_ii + Armature aus `_asset_audit.txt`. Vorab durchgerechnet: Schulter vert. 1,864/0,062, horiz. 1,864/0,126, Oberarm 0,588/0,035, Ellbogen 0,588/0,044, Kopf 0,588/0,021 (Nm/° bzw. Nm·s/°).
2. Danach `audit_asset.py` (Play) + `test_client_mimic_load_v5 --reset` + `--finger fingers_left` als Regression.
3. Pickup-/Putdown-Demo v5 (`test_client_pickup_v5`/`_putdown_v5`) als Regression.
4. Contact Sensors für alle 10 v5-Fingerspitzen (ADR-008-Muster).

### Wichtige Kontextdetails

- **Einheiten**: Angular-Drive-Stiffness/Damping am Prim sind pro **Grad** (USD-Schema) — 500 Nm/° ≈ 28.650 Nm/rad; `maxJointVelocity` in °/s. PhysX-Massenmatrix enthält die Armature **nicht**.
- **Isaac Sim 5.1** hat keine Mimic-Compliance (`naturalFrequency`/`dampingRatio`) und kein `solveArticulationContactLast` — die NVIDIA-Tutorials dazu sind 6.0.
- Zeitschritt 60 → 240 Hz brachte nichts; Ursache waren die Gains (ω_n·Δt ≫ 1), nicht Δt.
- Warnung `'NoneType' object has no attribute 'create_articulation_view'` einmal pro Play ist harmlos (erster Physikschritt vor Sim-View-Erzeugung).
- Akzeptiert (Leon: "reale Gelenke auch nicht perfekt"): Handgelenk hängt in der Tisch-Testpose 2,7–5,4° durch, Daumen/Zeigefinger blockieren sich bei voller Beugung (~70°), übrige Finger stoppen ~88,5°.
- Onshape-Massen = Vollmaterial-PLA (1,30 g/cm³) ohne Servos/Infill — bewusst belassen.
- Robot-Collider stecken in instanzierten `collisions`-Kindern → Viewport-Collider-Anzeige zeigt sie erst mit Instanceable aus (die Links selbst sind nicht instanceable).
- Leon stellt einfache Stage-/Graph-Änderungen im GUI ein — dafür keine Skripte schreiben.
