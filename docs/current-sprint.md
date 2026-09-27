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
- [x] `index_right` verkabelt und verifiziert (v4): `IsaacContactSensor`-Prim + `Isaac Read
      Contact Sensor Node` + generischer `ROS2 Publisher`-Node (`std_msgs/Float32`) auf
      `/pib/fingertip_force/index_right` — Kraftwerte kommen korrekt an (~1-2 N beim
      Greifen der Testdose)
- [x] **v5 hat `index_right` ebenfalls schon verkabelt** — bei der Action-Graph-Inspektion
      diese Session gefunden (`isaac_sim/tools/inspect_action_graph.py`), war in dieser
      Datei zuvor nicht als erledigt vermerkt (Doku war hier hinter der Realität)
- [ ] Restliche 9 Fingerspitzen (v4 und v5) nach demselben Muster verkabeln (siehe ADR-008
      für die Schritte: `SetInstanceable(False)` je Link-Prim, Sensor-Prim, zwei Action-
      Graph-Nodes) — **nächster konkreter Schritt** (Leon: "FSR an den anderen Fingern")
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
      nicht aus der URDF übernommen (gleiches Prinzip wie bei v4) — weiterhin offen
- [x] `ros2_ws/src/pib_description_v5/` — neues Package, `<ros2_control>`-Block von Hand
      ergänzt (44 Joints, `topic_based_ros2_control`, gleiche `/pib/hw/*`-Topics wie v4 —
      unproblematisch, da nie beide Stacks gleichzeitig gegen dieselbe Isaac-Instanz laufen)
- [x] `ros2_ws/src/pib_bringup/config/controllers_v5.yaml` + `launch/pib_sim_v5.launch.py`
      — v5-Pendants zu `controllers.yaml`/`pib_sim.launch.py`, v5-Joint-Namen
- [x] `test_client_pickup_v5.py`/`test_client_putdown_v5.py` — aus der per `dump_pose.py`
      aufgenommenen Sequenz (`isaac_sim/tools/_pose_dump.json`: neutral/approach/grasp/lift,
      je 2s) gebaut, alle 44 DOFs (nicht nur Teilmenge wie bei v4), Joint-Namen gegen JSON/
      YAML/URDF kreuzgeprüft (alle 44 identisch)
- [x] **`colcon build` erfolgreich** — `ros2_ws/install/` enthält `pib_description_v5`/
      `pib_bringup` aktuell (verifiziert diese Session, war zuvor als ungetestet vermerkt)
- [x] **Action Graph für v5 fertig verkabelt** (war hier fälschlich noch als Blocker
      vermerkt — laut `docs/handoff.md` vom 2026-09-10 bereits erledigt, diese Session per
      `inspect_action_graph.py` gegen die echte Stage verifiziert: `targetPrim` zeigt
      korrekt auf `root_joint`)
- [x] Pickup-/Putdown-Demo für v5 als Regressionscheck — laut `docs/handoff.md` vom
      2026-09-10 bereits end-to-end verifiziert. **Erneuter Regressionscheck nötig**, da
      die Sehnendynamik-Kopplung (siehe unten) jetzt `distal`/`tip` der aufgezeichneten
      Sequenz überschreibt — noch nicht erneut gegen die Demo getestet
- [ ] ADR-010 schreiben (v5-Reimport-Entscheidung, `_v4`/`_v5`-Namensschema, maxForce-Fix,
      Self-Collision-Fund, Erkenntnis dass dieser Import-Weg über `onshape-to-robot`+URDF lief
      statt über den direkten Onshape-Importer wie beim v4-Aufbau) — Nummer verschoben von
      ADR-009 auf ADR-010, da ADR-009 jetzt die Sehnendynamik-Entscheidung ist (siehe unten)

## Sehnendynamik ✓ (neu, diese Session)

**Ziel**: Digitaler Zwilling der realen linken Hand (Unterarm + Hand, 8 Servos) — PIP/DIP
bzw. Daumen-IP folgen dem jeweiligen MCP über dieselbe Viergelenk-Kopplung wie die echte
Hardware, statt unabhängig positionsgesteuert zu sein. Vorarbeit (Geometrie/Formel
hergeleitet und validiert) kam aus einer separaten Session, lag als Prompt + Referenz-
Skripte in `tendondrive/`.

- [x] Entscheidung: Script Node im bestehenden Action Graph, geschlossener Regelkreis über
      gemessene Ist-Winkel, kein Sehnenkraft-/Effort-Modell (siehe ADR-009)
- [x] Action Graph erweitert (`isaac_sim/tools/build_finger_coupling_graph.py`):
      `MeasuredJointState` (`IsaacArticulationState`) + `FingerCoupling` (Script Node) neu,
      `ArticulationController` liest `jointNames`/`positionCommand` jetzt von
      `FingerCoupling` statt direkt von `SubscriberJointState`
- [x] Zwei Bugs gefunden und gefixt (Script-Node-Sandbox-`NameError`, falscher Daumen-
      Gelenkname `distal` statt `tip`) — Details siehe ADR-009
- [x] End-to-end über echten `ros2_control`-Stack verifiziert: einzelne Finger, Daumen,
      Kontrolltest mit unbeteiligtem Gelenk (`wrist_left`), alle 10 Finger-/Daumen-MCPs
      beider Hände gleichzeitig auf 90°
- [ ] Restliche 9 Fingerspitzen-Kontaktsensoren (siehe „Contact Sensors" oben) — als
      nächstes geplant, dann volle Sensorabdeckung für den digitalen Zwilling
- [ ] Regressionscheck Pickup-/Putdown-Demo v5 (s.o.)
- [ ] Geometrie nur für linke Seite an echter Hardware validierbar (rechte Hand existiert
      nicht physisch) — Annahme "gespiegelt identisch" bleibt unverifiziert

---

## RL-Grasping (Isaac Lab) — ausgelagert auf `feature/rl-grasping`

Feinmotorisches Greifen (Force Closure) per RL, aufbauend auf dem digitalen Zwilling dieses
Branches (Sehnendynamik, USD, Kontaktsensoren). Eigener Branch, eigenes `CLAUDE.md` — siehe
dort für Ziele/Stand. Nicht Teil dieses Sprints.

---

## Nicht in diesem Sprint
- Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface) — siehe `feature/ros2-control`
- AS5600-Sensoren, LSTM-Training — siehe `feature/ros2-control`
- RL-Grasping-Training — siehe `feature/rl-grasping`
