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
6. **Contact Sensors v5 fertig** (ADR-013): 10 `Contact_Sensor`-Prims + Reader, gebündelt als `sensor_msgs/JointState` mit Zeitstempel auf `/pib/fingertip_forces` (`build_contact_sensors_v5.py`, `build_fingertip_force_graph_v5.py`); an der Dose verifiziert, überlebt Neu-Öffnen. Kaputter Zwischenstand liegt lokal als `pib_upperbody_v5.usd.bak-2026-10-03` (gitignored).

### Offene Punkte

- Nach der Arm-Umstellung bestanden: `audit_asset.py` (keine Warnung), `test_client_mimic_v5 --finger all`; nur Putdown-Demo v5 nicht erneut getestet.
- Arm/Handgelenk hängen unter Last sichtbar durch (Handgelenk −5,6° in der Tisch-Testpose) — akzeptiert; Stellschraube `SERVO_SATURATION_ERROR_DEG`.
- Compound für die Contact-Knoten nicht gebildet (hatte zusammen mit Stage-Tree-Umbenennen einen Absturz-Stand erzeugt, ADR-013).
- Warum Self-Collision das Wegfliegen behoben hat, ist nicht erklärt (empirischer Befund).

### Nächste Schritte (in Reihenfolge)

1. Aktuator-Tabelle (`SERVOS`/`V5_ACTUATORS`) nach `config/pib_hand_config_v5.py` verschieben — eine Quelle für `setup_stage.py` und später Isaac Lab (Einheiten Nm/° ↔ Nm/rad an einer Stelle).
2. `forward_position_controller` in `ros2_ws/src/pib_bringup/config/controllers_v5.yaml` (Streaming-Sollwerte für Policy-Inferenz über ROS).
3. Putdown-Demo v5 als letzte Regression (`test_client_putdown_v5`).
4. Optional: `SERVO_SATURATION_ERROR_DEG` kleiner, falls das Durchhängen stört (danach Audit).

### Wichtige Kontextdetails

- **Einheiten**: Angular-Drive-Stiffness/Damping am Prim sind pro **Grad** (USD-Schema) — 500 Nm/° ≈ 28.650 Nm/rad; `maxJointVelocity` in °/s. PhysX-Massenmatrix enthält die Armature **nicht**.
- **Isaac Sim 5.1** hat keine Mimic-Compliance (`naturalFrequency`/`dampingRatio`) und kein `solveArticulationContactLast` — die NVIDIA-Tutorials dazu sind 6.0.
- Zeitschritt 60 → 240 Hz brachte nichts; Ursache waren die Gains (ω_n·Δt ≫ 1), nicht Δt.
- Warnung `'NoneType' object has no attribute 'create_articulation_view'` einmal pro Play ist harmlos (erster Physikschritt vor Sim-View-Erzeugung).
- Akzeptiert (Leon: "reale Gelenke auch nicht perfekt"): Handgelenk hängt in der Tisch-Testpose 2,7–5,4° durch, Daumen/Zeigefinger blockieren sich bei voller Beugung (~70°), übrige Finger stoppen ~88,5°.
- Onshape-Massen = Vollmaterial-PLA (1,30 g/cm³) ohne Servos/Infill — bewusst belassen.
- Robot-Collider stecken in instanzierten `collisions`-Kindern → Viewport-Collider-Anzeige zeigt sie erst mit Instanceable aus (die Links selbst sind nicht instanceable).
- Leon stellt einfache Stage-/Graph-Änderungen im GUI ein — dafür keine Skripte schreiben.
- **OmniGraph per Skript**: `og.Controller`-Änderungen stehen nur im laufenden Graph; Persistentes direkt in die USD schreiben, danach speichern + neu öffnen; Knoten nicht im Stage-Tree umbenennen (ADR-013). Script Editor lädt geänderte Dateien nicht neu — immer frisch von der Platte öffnen.
- RL-Plan nach NVIDIA-Abgleich (Sim-to-Real-Leitfaden): Delta-Gelenkaktionen, kein Rauschen auf Propriozeption, Gains an realer Sprungantwort kalibrieren + Gelenkreibung, Export mit `--export_io_descriptors`, Inferenz-Leiter Lab-Play → Isaac-Sim-Runner → ROS-Weg → echte Hand (Details im Chat-Verlauf, noch nicht im RL-Branch).
