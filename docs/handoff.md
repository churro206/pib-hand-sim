# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-09-27

### Zuletzt gearbeitet an

1. **Sehnendynamik-Kopplung implementiert und verifiziert** (ADR-009): neuer `FingerCoupling`-Script-Node im v5-Action-Graph (`isaac_sim/tools/build_finger_coupling_graph.py`) berechnet PIP/DIP bzw. Daumen-IP jeden Tick aus dem gemessenen MCP-/PIP-Ist-Winkel (Viergelenkgetriebe-Formel aus `tendondrive/`). Digitaler Zwilling der realen linken Hand (8 Servos, PIP/DIP mechanisch nicht unabhängig aktuierbar).
2. **Zwei Bugs gefunden und gefixt**: `NameError: name 'np' is not defined` (Script-Node-Sandbox execut mit getrennten globals/locals, Fix: Closures in `setup(db)` statt Modulebene) und falscher Gelenkname `thumb_left_distal` statt `thumb_left_tip` (v5-Namensschema-Abweichung übersehen).
3. **End-to-end über echten `ros2_control`-Stack getestet**: `FollowJointTrajectory`-Goals gegen einzelne Finger, Daumen, Kontrolltest (`wrist_left`), alle 10 Finger-/Daumen-MCPs beider Hände gleichzeitig auf 90° (exakter Referenzpunkt der Kopplungskurve) — alles bestätigt korrekt.
4. **Docs durchgängig aktualisiert** (CLAUDE.md, architecture.md, conventions.md, current-sprint.md, decisions.md/ADR-009) und neuer Branch `feature/rl-grasping` angelegt (RL-Feingreifen in Isaac Lab, aufbauend auf diesem digitalen Zwilling — eigenes CLAUDE.md dort).

### Offene Punkte

- Restliche 9 Fingerspitzen-Kontaktsensoren (v4 **und** v5) noch nicht verkabelt — bei der Inspektion diese Session gefunden, dass `index_right` in v5 (entgegen der bisherigen Doku) bereits verkabelt war.
- Regressionscheck Pickup-/Putdown-Demo v5 gegen die neue Kopplung **noch nicht gemacht** — die aufgezeichnete Sequenz schickt eigene distal/tip-Werte, die jetzt ignoriert werden, sollte aber trotzdem funktionieren (nicht verifiziert).
- `config/pib_hand_config_v5.py` weiterhin nicht geschrieben.
- ADR-010 (v5-Reimport-Entscheidung, Backlog-Punkt aus einer früheren Session, nur umnummeriert von ADR-009) weiterhin nicht geschrieben.
- Kopplungsgeometrie nur für linke Seite an echter Hardware verifizierbar — rechte Hand existiert nicht physisch, Annahme "gespiegelt identisch" bleibt ungeprüft.
- Isaac Lab ist auf dieser Maschine nicht installiert — erster Blocker für `feature/rl-grasping`.

### Nächste Schritte (in Reihenfolge)

1. Restliche 9 Fingerspitzen-Kontaktsensoren verkabeln (ADR-008-Muster, v4 und v5).
2. Regressionscheck Pickup-/Putdown-Demo v5.
3. `config/pib_hand_config_v5.py` schreiben (Limits/`ROBOT_PRIM_PATH` gegen laufende Stage verifizieren).
4. Auf `feature/rl-grasping`: Isaac Lab installieren, dann `ArticulationCfg` gegen die echte v5-USD verifizieren — Aktionsraum **muss** die 8 realen Servo-DOFs sein, PIP/DIP/IP intern über dieselbe `FourBar`-Formel (nicht lernbar), sonst lernt die Policy real unerreichbare Posen.

### Wichtige Kontextdetails

- **Reale Hand**: nur die linke Hand + Unterarm existiert physisch (Prototyp), 8 Servos über STM32 Nucleo gesteuert (Handgelenk, Unterarmdrehung, Daumen-Rotator, 5× Finger-/Daumen-MCP). PIP/DIP/IP sind rein mechanisch über Kopplungsstangen gekoppelt, nicht individuell aktuiert — das ist der Grund für die gesamte Sehnendynamik-Arbeit, nicht nur ein Kinematik-Nice-to-have.
- **Script-Node-Sandbox-Gotcha gilt für JEDEN künftigen Script Node**, nicht nur `FingerCoupling`: Klassen/Instanzen nie auf Modulebene, immer als Closure in `setup(db)` + `db.per_instance_state`. Siehe `docs/conventions.md` → „Script Node (Action Graph)".
- **`IsaacArticulationController` scheint bei einem ungültigen Gelenknamen im Array den kompletten `positionCommand`-Batch zu verwerfen**, nicht nur den einen Eintrag — beim `thumb_left_distal`-Bug bewegte sich deshalb auch das unbeteiligte `wrist_left` nicht, was die Fehlersuche erst in eine falsche Richtung (generelles Physics-/Grace-Period-Problem) gelenkt hat. Nicht abschließend im Isaac-Sim-Quellcode verifiziert, nur empirisch beobachtet.
- `isaac_sim/tools/inspect_action_graph.py` schreibt die Ausgabe zusätzlich nach `isaac_sim/tools/_action_graph_inventory.txt` (gitignored) — Konsolenausgabe im Script Editor lässt sich schlecht kopieren, `__file__` ist dort außerdem nicht definiert (Pfad wird stattdessen über die offene Stage aufgelöst, wie in `setup_stage.py`).
- **`ros2 launch` läuft im Vordergrund** — Ctrl-C killt den kompletten Stack (`robot_state_publisher`, `controller_manager`, alle Controller), nicht nur die Spawner-Prozesse (die sich ohnehin normal selbst beenden). Zwei Terminals nötig: eins zum Laufenlassen, eins für Testbefehle.
- Geprüfte, aber verworfene Alternative zur Sehnendynamik: natives PhysX-Fixed-Tendon-Schema (`PhysxTendonAxisAPI`) — Gearing ist linear, reale Kopplung ist nichtlinear (Übersetzung 0,6–1,667 über 0–90°), damit nicht exakt abbildbar.
- **Neuer Branch `feature/rl-grasping`** von diesem Stand abgezweigt (nach Doku-Update), eigenes `CLAUDE.md` — erbt den kompletten digitalen Zwilling (USD, Sehnendynamik, Kontaktsensoren), nicht neu aufbauen.
