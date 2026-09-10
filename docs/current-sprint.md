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
- [x] `config/pib_hand_config_v4.py`/`isaac_sim/setup_stage.py` angepasst
- [x] Pickup-/Putdown-Demo als Regressionscheck verifiziert

## Contact Sensors ← aktuell

**Ziel**: Kontaktkräfte pro Fingertip, für Greif-Erkennung nutzbar.

- [x] Entscheidung: nativer `IsaacContactSensor`-Node (nicht `ArticulationView`-Tensor-API),
      siehe ADR-008
- [x] `index_right` verkabelt und verifiziert: `IsaacContactSensor`-Prim + `Isaac Read
      Contact Sensor Node` + generischer `ROS2 Publisher`-Node (`std_msgs/Float32`) auf
      `/pib/fingertip_force/index_right` — Kraftwerte kommen korrekt an (~1-2 N beim
      Greifen der Testdose)
- [ ] Restliche 9 Fingerspitzen nach demselben Muster verkabeln (siehe ADR-008 für die
      Schritte: `SetInstanceable(False)` je Link-Prim, Sensor-Prim, zwei Action-Graph-Nodes)
- [ ] Ggf. auf gebündeltes Topic/Array umstellen, falls Einzel-Topics pro Finger auf Dauer
      unhandlich werden (`ConstructArray` + `ROS2PublishJointState`, siehe ADR-008)

## Szenen-Erweiterung ← aktuell

**Ziel**: Weitere Objekte/Umgebung in `isaac_sim/usd/pib_upperbody_v4.usd`.

- [x] Tisch (fixierter Collider, `RigidBodyAPI` entfernt), Korb (mit Griffen), Tasse als
      Greif-Testobjekte ergänzt (Commit `d11e9b9`)
- [ ] Objekt-Austausch (Korb/Teller) — VariantSet-Ansatz war fertig implementiert
      (`isaac_sim/tools/make_object_variant.py`), aber verworfen; offen ob später doch
      umgesetzt oder Objekte manuell in der Stage getauscht werden

## v5-Hand-Integration ← neu

**Ziel**: v5-Hand (neue Onshape-Baugruppe, per `onshape-to-robot` als URDF exportiert und in
Isaac importiert) läuft **dauerhaft parallel** zu v4, nicht als Ablösung. v5-Gelenknamen
bleiben unverändert (kein `dof_`-Präfix, kein Onshape-Re-Export nur für den Namensabgleich).

**Repo-Struktur** (`_v4`/`_v5`-Schema durchgängig gezogen, dieser Session):
- [x] `isaac_sim/usd/pib_upperbody.usd` → `pib_upperbody_v4.usd` — dabei aufgefallen: die
      Datei war seit `737ac2e` (ADR-007) nicht mehr aktuell; der tatsächlich aktuelle Stand
      (Contact-Sensor-Rebuild + Tisch/Korb/Tasse aus `d11e9b9`) lag in
      `pib_upperbody_contact_sensors_assets.usd` — das ist jetzt `pib_upperbody_v4.usd`.
      Die beiden veralteten Dateien (`pib_upperbody.usd`, `pib_upperbody_contact_sensors.usd`)
      sind aus dem Baum entfernt (Git-Historie behält sie)
- [x] `config/pib_hand_config.py` → `pib_hand_config_v4.py`, alle Loader-Referenzen
      (`start.py`, `setup_stage.py`, `autostart.py`, `isaac_sim/tools/*.py`) nachgezogen
- [x] `pib_upperbody_urdf/` → `pib_upperbody_urdf_v4/`; `pib_upperbody_urdf_v5/` eingecheckt
      (roher `onshape-to-robot`-Export)
- [x] `ros2_ws/src/pib_description/` → `pib_description_v4/` (Package-Name in
      `package.xml`/`CMakeLists.txt`, `package://`-Mesh-Pfade in der URDF, sowie
      `pib_bringup`s `exec_depend`/Launch-Referenz mitgezogen)

**v5 in die Szene eingepflegt** (Kopie von `pib_upperbody_v4.usd`, alter Roboter-Prim
gelöscht, v5-URDF importiert, `targetPrim` des Action Graphs zeigt weiter — siehe Ablauf
weiter oben in dieser Session):
- [x] `isaac_sim/usd/pib_upperbody_v5.usd` — v5-Roboter + Tisch/Korb/Tasse aus v4 übernommen,
      Convex Hull/Static Base/Instanceable-aus beim Import gesetzt (ADR-008-Stolperstein damit
      von vornherein vermieden, nicht nachträglich pro Fingerspitze gefixt)
- [x] Drive-Bug gefunden und gefixt (`isaac_sim/setup_stage.py`): Isaac-URDF-Importer hatte
      `physics:maxForce` aus dem URDF-`effort`-Wert übernommen (10 Nm an der Schulter — real
      gebraucht werden dort deutlich mehr), v4 hatte nie ein maxForce gesetzt (Schema-Default
      `inf`). `configure_drives()` setzt jetzt explizit `maxForce=inf` auf allen Drives —
      stellt für v4 und v5 einheitlich den unbegrenzten Zustand her, kein geratener Nm-Wert
- [x] `set_initial_pose()`: alle Targets auf 0° (T-Pose), Ellbogen-Sonderfall (30°) entfernt
      — war nie begründet, jetzt einheitlich für v4/v5
- [x] Schwingen an manchen v5-Gelenken nach dem maxForce-Fix aufgetreten — Ursache gefunden:
      **Self-Collision**, nicht Damping/Solver. Articulation Root sitzt bei v5 auf `root_joint`
      (PhysicsFixedJoint, nicht auf dem Wrapper-Xform wie bei v4 — anderes, aber gültiges
      Importer-Muster). Self-Collisions dort deaktiviert, behoben. **Wichtig für später**:
      `IsaacArticulationController`s `targetPrim` muss beim Action-Graph-Verkabeln auf
      `root_joint` zeigen, nicht auf den Wrapper-Prim
- [ ] `config/pib_hand_config_v5.py` — DOF-Namen liegen aus der URDF vor, aber Limits/
      `ROBOT_PRIM_PATH`/Drive-Werte müssen gegen die echte Isaac-Stage verifiziert werden,
      nicht aus der URDF übernommen (gleiches Prinzip wie bei v4)
- [x] `ros2_ws/src/pib_description_v5/` — neues Package, `<ros2_control>`-Block von Hand
      ergänzt (44 Joints, `topic_based_ros2_control`, gleiche `/pib/hw/*`-Topics wie v4 —
      unproblematisch, da nie beide Stacks gleichzeitig gegen dieselbe Isaac-Instanz laufen)
- [x] `ros2_ws/src/pib_bringup/config/controllers_v5.yaml` + `launch/pib_sim_v5.launch.py`
      — v5-Pendants zu `controllers.yaml`/`pib_sim.launch.py`, v5-Joint-Namen
- [x] `test_client_pickup_v5.py`/`test_client_putdown_v5.py` — aus der per `dump_pose.py`
      aufgenommenen Sequenz (`isaac_sim/tools/_pose_dump.json`: neutral/approach/grasp/lift,
      je 2s) gebaut, alle 44 DOFs (nicht nur Teilmenge wie bei v4), Joint-Namen gegen JSON/
      YAML/URDF kreuzgeprüft (alle 44 identisch)
- [ ] **Noch ungetestet** — `colcon build` für die neuen Packages lief in dieser Session
      nicht (kein ROS2-Sourcing hier verfügbar), erste Ausführung steht noch aus
- [ ] Contact Sensors für v5 verkabeln (`index_right`-Muster, ADR-008)
- [ ] **Action Graph für v5 fehlt noch — Blocker für die Test-Clients**: Ohne
      `ROS2SubscribeJointState`/`IsaacArticulationController`(`targetPrim`→`root_joint`)/
      `ROS2PublishJointState` in `pib_upperbody_v5.usd` bewegt sich der Roboter trotz
      laufendem ros2_control-Stack nicht — die Clients senden ins Leere. Einfachster Weg:
      die drei Nodes aus `pib_upperbody_v4.usd`s Action Graph kopieren, `targetPrim` auf
      `root_joint` der v5-Stage umbiegen
- [ ] Pickup-/Putdown-Demo für v5 als Regressionscheck (sobald Action Graph steht)
- [ ] ADR-009 schreiben (v5-Reimport-Entscheidung, `_v4`/`_v5`-Namensschema, maxForce-Fix,
      Self-Collision-Fund, Erkenntnis dass dieser Import-Weg über `onshape-to-robot`+URDF lief
      statt über den direkten Onshape-Importer wie beim v4-Aufbau)

---

## Nicht in diesem Sprint
- Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface)
- AS5600-Sensoren, LSTM-Training
