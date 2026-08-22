# Sprint — `experiment/omnigraph-lightweight`

Alte Sprints/Ziele (Simulation Server, Team-Integration, LSTM-Training) für diesen Branch
verworfen — voller Fahrplan dazu auf `feature/ros2-control`.

## OmniGraph-Migration ✓

- [x] `pib_bridge.py` durch Action Graph ersetzt (`ROS2SubscribeJointState` → Script Node
      [JOINT_SIGN] → `IsaacArticulationController`, Rückweg über `ROS2PublishJointState`)
- [x] `robot_io.py`, `runner.py`, `_launch_helper.py`, `control/`, Sequenz-Pipeline,
      LSTM-Pipeline, 11 alte USD-Dateivarianten entfernt (ADR-006)
- [x] `test_client_pickup.py` — Pickup-Demo, verifiziert über `FollowJointTrajectory`
- [x] `test_client_putdown.py` — exakte Umkehrung, verifiziert
- [x] `start.py`/`setup_stage.py` behalten (Drive/Limit-Setup läuft weiterhin pro Session)
- [x] Docs (`CLAUDE.md`, `architecture.md`, `conventions.md`, `decisions.md`) an diesen
      Branch angepasst

## Vorzeichen-Fix ✓

- [x] Ursache identifiziert: Onshape und Isaacs importierte Gelenkachsen vorzeicheninvertiert
- [x] Behoben direkt an den Gelenk-Prims (`isaac_sim/tools/flip_joint_sign.py`, ADR-007) —
      kein Script Node/`JOINT_SIGN` mehr, Ist-Werte-Kompromiss aus ADR-006 miterledigt
- [x] `config/pib_hand_config.py`/`isaac_sim/setup_stage.py` angepasst
- [x] Pickup-/Putdown-Demo als Regressionscheck verifiziert

## Contact Sensors ← aktuell

**Ziel**: Kontaktkräfte pro Fingertip, für Greif-Erkennung nutzbar.

- [ ] Entscheidung: nativer `IsaacContactSensor`-Node vs. `ArticulationView`-Tensor-API
      in einem Script Node (Abwägung in `docs/architecture.md` → „Offen")
- [ ] Fingertip-Prim-Pfade in der USD identifizieren (kein `inventory.py` mehr auf diesem
      Branch — Stage-Baum direkt durchsuchen, oder `feature/ros2-control` als Referenz)
- [ ] Sensor(en) hinzufügen, in Action Graph verkabeln
- [ ] Auf ROS2-Topic veröffentlichen (Name/Format noch offen)

## Szenen-Erweiterung ← aktuell

**Ziel**: Weitere Objekte/Umgebung in `isaac_sim/usd/pib_upperbody.usd`.

- [ ] Details noch offen — welche Objekte, welche Anordnung, Kollisions-/Material-Setup

---

## Nicht in diesem Sprint
- Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface)
- AS5600-Sensoren, LSTM-Training
