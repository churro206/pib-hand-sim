# Sprint — `feature/rl-grasping`

Seit 2026-10-04 Arbeitsbranch: `feature/rl-grasping` = Stand von
`experiment/omnigraph-lightweight` (digitaler Zwilling v5) plus RL-Greifen in Isaac Lab
(Abschnitt „RL-Greifen“ unten, ADR-015). Die übrigen Abschnitte sind die Historie des
Omnigraph-Sprints. Alte Sprints/Ziele (Simulation Server, Team-Integration, LSTM-Training)
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

## Contact Sensors ✓ (v5)

**Ziel**: Kontaktkräfte pro Fingertip, für Greif-Erkennung nutzbar.

- [x] Entscheidung: nativer `IsaacContactSensor`-Node (nicht `ArticulationView`-Tensor-API),
      siehe ADR-008
- [x] `index_right` verkabelt und verifiziert (v4): `IsaacContactSensor`-Prim + `Isaac Read
      Contact Sensor Node` + generischer `ROS2 Publisher`-Node (`std_msgs/Float32`) auf
      `/pib/fingertip_force/index_right` — Kraftwerte kommen korrekt an (~1-2 N beim
      Greifen der Testdose)
- [x] v5: alle 10 Fingerspitzen — Sensor-Prims (`build_contact_sensors_v5.py`), 10 Reader,
      gebündelt als `sensor_msgs/JointState` mit Zeitstempel auf `/pib/fingertip_forces`
      (`build_fingertip_force_graph_v5.py`, ADR-013); verifiziert an der Dose (Daumen ≈42 N,
      Zeige ≈25 N, Mittel ≈16 N, Ring ≈2 N)
- [x] Absturz bei Play behoben (2026-10-04): ein Compound-Subgraph mit allen Reader-Knoten
      steckte doch in der committeten USD — entfernt, Knoten flach neu gebaut (ADR-013,
      Korrektur zu Fallstrick 3); jetzt wirklich stabil nach Speichern + Neu-Öffnen
- [x] ~~Contact-Knoten als Compound zusammenfassen~~ — verworfen: Compound löst den Absturz
      aus (ADR-013, Fallstrick 3)
- [ ] v4: restliche 9 Fingerspitzen — v4 vorerst nicht weiterverfolgt

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
- [x] `config/pib_hand_config_v5.py` — gegen die v5-URDF verifiziert; dabei v5-Limits-Bug in
      `setup_stage.py` gefunden (`_BODY_LIMITS` war nur mit v4-Werten befüllt:
      `upper_arm_left` [0°,90°] statt [-90°,90°], `wrist_*` [0°,90°] statt [-90°,30°]);
      Limits in der Stage per `audit_asset.py` bestätigt
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
- [x] Pickup-/Putdown-Demo für v5 als Regressionscheck — am 2026-09-10 end-to-end
      verifiziert. **Erneuter Regressionscheck nötig**: Mit Mimic Joints (ADR-011) sind die
      aufgezeichneten `distal`/`tip`-Werte wirkungslos, mit Self-Collision und weichen
      Servo-Gains (ADR-012) kann die Greifpose anders ausfallen
- [ ] ADR schreiben zur v5-Reimport-Entscheidung (`_v4`/`_v5`-Namensschema, maxForce-Fix,
      Erkenntnis dass dieser Import-Weg über `onshape-to-robot`+URDF lief statt über den
      direkten Onshape-Importer wie beim v4-Aufbau) — nächste freie Nummer ist ADR-016

## Fingerkopplung ✓ (ADR-009 → ADR-010 → ADR-011)

**Ziel**: Digitaler Zwilling der realen linken Hand (8 Servos) — PIP/DIP bzw. Daumen-IP folgen
dem MCP, und der MCP-Servo trägt die Last der ganzen Kette.

- [x] ADR-009: Script Node `FingerCoupling` (analytische Viergelenk-Kopplung der Soll-Winkel)
      — **ersetzt**, Branch auf `0fdbc62` zurückgesetzt (Commit `1d0cd9c` auf
      `feature/rl-grasping` und im Tag `backup/sehnendynamik-1d0cd9c`)
- [x] ADR-010: explizite Kraft-Rückwirkung PIP/DIP → MCP — instabil, **verworfen**
- [x] ADR-011: PhysX Mimic Joints, linear (gearing=-1, offset=0), 18 Gelenke beider Hände,
      Folgegelenke passiv; Konfiguration in `setup_stage.py` → `MIMIC_JOINTS`, gesetzt von
      `start.py` — `test_client_mimic_v5`: alle 10 MCPs Δ ≤ 0,2°
- [ ] Stufe 2 (adaptiv, Gearing/Offset aus der Viergelenk-Formel pro Schritt) — offen, erst
      prüfen ob Isaac Laufzeitänderungen von Gearing an PhysX weitergibt
- [ ] Geometrie nur für links an echter Hardware validierbar (rechte Hand existiert nicht
      physisch) — Annahme "gespiegelt identisch" bleibt unverifiziert

## Physik-Tuning nach NVIDIA ← aktuell (ADR-012)

**Ziel**: Stabile, realistische Simulation unter Kontakt, so nah wie möglich an NVIDIAs
Tuning-Reihe (Inspire Hand) und bewährten Projekten. Plan (Reihenfolge nach NVIDIA):

- [x] **1. Asset inspizieren** — `isaac_sim/tools/audit_asset.py`: Massen USD = PhysX = URDF für
      alle 47 Links; Onshape-Massen sind Vollmaterial-PLA ohne Servos (bewusst belassen),
      Unterarm-Override 30 g → 0,229 kg korrigiert (URDF + USD); effektive Gelenkträgheiten
      gemessen (PhysX zählt Armature nicht in die Massenmatrix)
- [x] **2. Collider-Paare** — Self-Collision am `root_joint` an (damit Tischtest stabil);
      Collision Groups vorerst nicht nötig, nur bei konkretem Problem einzelne Filtered Pairs
- [x] **3. Antriebsgrenzen** + **4. Gains** — Servo-Aktuatormodell für alle v5-Servo-Gelenke
      (ST3215 2,94 Nm/270 °/s, ST3095 `shoulder_*` 9,32 Nm/186 °/s; Stiffness = maxForce/5°,
      ζ=1 mit Nenn-Trägheit aus dem Audit) in `setup_stage.py` → `SERVOS`/`V5_ACTUATORS`;
      Experiment-Schalter entfernt, v4 zurück auf Referenzwerte. ω_n·Δt 0,44–1,36
- [ ] **5. Stabilität unter Kontakt** — nur falls nötig, einzeln: Armature,
      `maxDepenetrationVelocity`, Solver-Iterationen (Mimic-Compliance und
      `solveArticulationContactLast` gibt es in 5.1 nicht)
- [x] **6. Validierung** — Tischtest bestanden (Ellbogen gibt nach statt Finger-Stall),
      Pickup v5: Dose gegriffen, Arm hält sie nur knapp (realistisch laut Leon),
      `test_client_mimic_v5` unverändert bestanden (Δ ≤ 0,2°; Daumen/Zeigefinger blockieren
      sich bei ~70°, übrige Finger ~88,5° — Self-Collision), `audit_asset.py` ohne Warnung.
      Putdown v5 am 2026-10-04 erneut bestanden (mit Handgelenk-Pleuel und Filtered Pairs)
- [x] Action-Graph-Trigger auf `OnPhysicsStep` (v5)
- [x] Tischtest bestanden: `index_left` stabiler Stall, vier Finger → Handgelenk gibt
      realistisch nach; Durchhängen/Blockaden bewusst akzeptiert (siehe ADR-012)

---

## RL-Greifen (Isaac Lab, linke v5-Hand) ← aktuell (ADR-014, ADR-015)

**Ziel (Proof of Concept, ~1 Woche ab 2026-10-04)**: Greif-Policy in der Simulation, die nur
reale Sensoren nutzt (8 Servo-Winkel, 5 FSR) — später auf dem STM32N657 (NPU) der echten
linken Hand. Meilensteine: M1 Policy greift in der Sim, M2 läuft quantisiert auf dem Chip
(`stedgeai validate`), M3 echte Hand (optional).

- [x] Servo-Aktuatormodell nach `config/pib_hand_config_v5.py` (eine Quelle, Nm/° und Nm/rad)
- [x] Isaac Lab 2.3.2 in eigener conda-Umgebung `env_isaaclab` (Miniconda, NVIDIA-Doku);
      Hardware-Test RTX 3060 Ti: 1024 Umgebungen ≈ 16.000 Schritte/s
- [x] Hand-only-Asset: `pib_hand_left_urdf_v5/` → `pib_hand_left_v5.usd`, eingebrannt per
      `bake_hand_asset_v5.py`; Isaac Lab übernimmt die Mimic-Kopplung (GPU, Δ ≤ 0,01°)
- [x] Handgelenk-Pleuel: Grenzen [−60°, 0°], Aktuator `RemotizedPDActuatorCfg` (ADR-014)
- [x] Filtered Pair Unterarm ↔ Daumen-Rotator (Hand-USD und Vollroboter)
- [x] Aufgabe `isaac_lab/pib_grasp/` nach Dexsuite (Tisch senkt sich, Asymmetric
      Actor-Critic, ein Kontaktsensor je Fingerspitze, Zufallsstart der Gelenke)
- [x] Machbarkeitstest: Daumen-Rotator 90° → 14–15/16 gehalten, 0° → 0/16
- [x] Probelauf 300 Iterationen: Dose fällt 100 % → 19 %, Gegengriff 0 → 0,38; ONNX-Export
- [x] Policy im Fenster bewertet (`play.py`, Video `videos/isaac_lab_pib_hand_inference_test.webm`):
      hält viele Dosen — dreht dafür aber den Unterarm, bis die Dose auf der Handfläche liegt
- [ ] Unterarmdrehung unterbinden (Unterarm aus dem Aktionsraum oder Strafe auf Neigung der
      Dose/Abweichung des Unterarms), dann längeres Training
- [ ] Dose beim Reset aus der Hand geschleudert (~6 %, vermutlich Daumen in Opposition +
      gebeugt überlappt die Dose) — beobachten, ggf. Daumen-MCP-Startbereich verkleinern
- [ ] M2: ONNX → int8 (QDQ) → in der Sim gegen float bewerten → ST Edge AI →
      `stedgeai validate` auf dem NUCLEO-N657X0
- [ ] Sim-to-Real (für M3): Servo-Sprungantwort messen und Gains/Armature kalibrieren,
      Aktionsverzögerung randomisieren (Spot-Muster), FSR-Modell, ggf. adaptive Kopplung

---

## Nicht in diesem Sprint
- Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface) — siehe `feature/ros2-control`
- AS5600-Sensoren, LSTM-Training — siehe `feature/ros2-control`
- Vision/VLA-Greifen auf dem künftigen Jetson Thor (GraspGen, FoundationPose, cuMotion,
  GR00T N1.6, Teacher-Student nach DextrAH) — nur skizziert, siehe Handoff 2026-10-04
