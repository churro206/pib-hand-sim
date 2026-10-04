# Architektur

**Branch `feature/rl-grasping`** (= `experiment/omnigraph-lightweight` + RL-Greifen in Isaac
Lab, Abschnitt „RL-Greifen“ unten). Die Simulations-/ROS2-Teile beschreiben den Stand von
`experiment/omnigraph-lightweight`. Der
vollständige Stand mit `robot_io.py`, ControlMode-Architektur (`direct`/`servo`/`nn`),
Sequenz-Executor und Sprint-3/4-Fahrplan liegt auf `feature/ros2-control` (eigene Version
dieser Datei dort).

## Team-Kontext
RoboCup 2027 @Home. Mehrere Gruppen:
- **pib-Sim** (Leon): Simulation, ros2_control-Stack, Schnittstellen
- **IK-Team**: Inverse Kinematik — gibt Gelenkwinkel-Trajektorien aus
- **Greifpunkt-Team**: Greifpunkterkennung — gibt Greifpunkt im Roboterframe aus
- **Objekterkennung**: hinten angestellt

Alle Teams nutzen **ROS2**. Auf diesem Branch noch nicht angegangen (siehe „Offen" unten).

**RL-Greifen**: Greif-Policy per Reinforcement Learning in Isaac Lab für die reale linke
v5-Hand (8 Servos, 5 FSR, STM32N657 mit NPU) — auf diesem Branch, siehe Abschnitt
„RL-Greifen“ und ADR-015.

**v4/v5**: Seit der v5-Hand-Baugruppe läuft alles Folgende doppelt, für v4 (verifiziert,
Referenz-Implementierung) und v5 (im Aufbau) parallel — nicht ablösend. Durchgängiges
Namensschema: `_v4`-Suffix bzw. `_v5`-Suffix auf jeder Ebene (USD, Config, ROS2-Package).
Wo unten nicht explizit unterschieden wird, ist v4 gemeint (aktuell einziger vollständig
verifizierter Stand); v5-Stand siehe `docs/current-sprint.md`.

---

## Schichtenmodell (dieser Branch)

```
Layer 3: ros2_control-Stack (fertig)
         JointTrajectoryController (FollowJointTrajectory, MoveIt2-kompatibel)
         JointStateBroadcaster → /joint_states
         topic_based_ros2_control als Hardware-Interface-Bridge

Layer 2: Action Graph (fertig)
         Teil der USD-Stage, kein externer Python-Prozess
         ROS2SubscribeJointState → IsaacArticulationController
         Artikulation → ROS2PublishJointState

Layer 1: Isaac-Setup (fertig, minimal, bisher nur v4)
         config/pib_hand_config_v4.py (DOF-Namen, Limits) + start.py/setup_stage.py
         (Drives, Limits, Initialpose — einmalig pro Session vor Play)
```

Kein Layer für Control-Architektur oder Simulation-Server-Abstraktion mehr — der Action
Graph spricht direkt mit `ros2_control` über die Topics, ohne Python-Vermittlungsschicht.

---

## Layer 2 — Action Graph im Detail

Liegt vollständig in `isaac_sim/usd/pib_upperbody_v4.usd` (Window → Graph Editors → Action
Graph zum Ansehen/Bearbeiten). Drei Nodes:

1. **`ROS2SubscribeJointState`** — `topicName = /pib/hw/joint_commands`
2. **`IsaacArticulationController`** — `targetPrim` = Artikulations-Root des Roboters,
   `positionCommand` direkt von `ROS2SubscribeJointState` verbunden
3. **`ROS2PublishJointState`** — `topicName = /pib/hw/joint_states`

Kein Script Node mehr nötig — die Vorzeichen-Konvention ist direkt an den Gelenk-Prims
korrigiert (`isaac_sim/tools/flip_joint_sign.py`, siehe ADR-007). `ROS2PublishJointState`
liest den Gelenkzustand weiterhin direkt aus dem Prim, zeigt jetzt aber korrekte
(nicht mehr gespiegelte) Werte, da die Prims selbst schon in Onshape-Konvention stehen.

`velocityCommand`/`effortCommand` bleiben unverbunden — `controllers.yaml` konfiguriert
nur `command_interfaces: [position]`.

### Warum kein Custom-Bridge-Code mehr
`ROS2SubscribeJointState`/`IsaacArticulationController`/`ROS2PublishJointState` sind
NVIDIA-gewartete OmniGraph-Nodes, die genau den Loop ersetzen, den `pib_bridge.py` vorher
per `rclpy` von Hand nachgebaut hat (inkl. Grace-Period/Lazy-Init-Handling für die
Physics-View-Bereitschaft — übernimmt der native Node selbst). Die Vorzeichen-Invertierung,
die anfangs noch einen Script Node brauchte, ist seit ADR-007 keine Laufzeit-Kompensation
mehr, sondern eine einmalige Korrektur direkt an den Gelenk-Prims — kein Custom-Code mehr
im Action Graph selbst.

### v5-Besonderheiten
Gilt **nur für `pib_upperbody_v5.usd`** — für v4 bleibt der obige Aufbau unverändert gültig.

- **Trigger `OnPhysicsStep`** (`isaacsim.core.nodes.OnPhysicsStep`) statt `OnPlaybackTick`
  für alle Nodes in `/Graph/ROS_JointStates` — Kommandos/Zustände laufen im Physiktakt,
  auch wenn die Simulation unter 60 FPS rendert. Funktioniert nur zusammen mit dem
  Graph-Prim auf `evaluationMode=Standalone` **und** `pipelineStage=pipelineStageOnDemand`
  (sonst Fehler „Physics OnSimulationStep node detected in a non on-demand Graph").
  Nebenwirkung: beim ersten Physikschritt nach Play meldet `ArticulationController` einmal
  `'NoneType' object has no attribute 'create_articulation_view'` (Physics-Sim-View noch nicht
  angelegt) und initialisiert sich im nächsten Schritt selbst — harmlos. Der Physics
  Inspector ist mit dieser Graph-Konfiguration unzuverlässig.
- **Kein Script Node.** Die Fingerkopplung (PIP/DIP/IP folgen dem MCP) ist keine
  Laufzeitlogik im Graph mehr, sondern eine PhysX-Zwangsbedingung direkt an den
  Gelenk-Prims (Mimic Joints, ADR-011). Der zwischenzeitliche `FingerCoupling`-Script-Node
  (ADR-009) und die explizite Kraft-Rückwirkung (ADR-010) sind ersetzt bzw. verworfen.
- **`targetPrim` = `root_joint`** (Articulation Root von v5 ist ein `PhysicsFixedJoint`,
  nicht der Wrapper-Xform wie bei v4).

---

## Layer 1 — Isaac-Setup

| Datei | Verantwortung |
|---|---|
| `config/pib_hand_config_v4.py` | DOF-Namen, Indizes, `ROBOT_PRIM_PATH`, Joint-Limits |
| `config/pib_hand_config_v5.py` | dasselbe für v5 (Namen ohne `dof_`-Präfix) |
| `isaac_sim/setup_stage.py` | Physics Scene, Boden/Licht, Joint-Drives (Stiffness/Damping/maxForce), Servo-Aktuatormodell (Armature, maxJointVelocity, ADR-012), Mimic Joints (`MIMIC_JOINTS`, ADR-011), Limits, Initialpose |
| `isaac_sim/start.py` | Bündelt `setup_stage`-Aufrufe, vor Play im Script Editor ausführen |
| `isaac_sim/autostart.py` | Vollautomatisch: USD laden → `start.py` → Play (`--exec`, kein Script Editor nötig) |

Läuft jede Session neu (PhysX cached Drive-Stiffness/Damping nicht zwischen Sessions).
Was dagegen dauerhaft in der USD steht (GUI-Änderungen, gespeichert): Action-Graph-Aufbau,
Self-Collision am Articulation Root, korrigierte Unterarm-Masse (v5).

### Servo-Aktuatormodell (v5, ADR-012)
Nach NVIDIAs Articulation Stability Guide / Tuning-Reihe: `maxForce` = Stall-Torque,
`maxJointVelocity` = Leerlaufdrehzahl (Datenblatt, 12 V), Stiffness = `maxForce` / 5°
(Robotiq-Rezept), Damping kritisch (ζ=1) mit Armature als Trägheit.

| Servo | Gelenke | maxForce | maxJointVelocity | Stand |
|---|---|---|---|---|
| ST3215 | MCP (`*_proximal`), `thumb_*_rotator`, `forearm_*` | 2,94 Nm | 270 °/s | umgesetzt |
| ST3215 über Pleuel | `wrist_*` (Übersetzung Bereichsmitte ≈ 2, ADR-014) | 5,87 Nm | 135 °/s | umgesetzt, Armature ×4 |
| ST3215 | `upper_arm_*`, `elbow_*`, `head_*` | 2,94 Nm | 270 °/s | umgesetzt |
| ST3095 | `shoulder_vertical_*`, `shoulder_horizontal_*` | 9,32 Nm | 186 °/s | umgesetzt |
| – | Mimic-Folgegelenke (`distal`/`tip`) | passiv | 500 °/s | Armature 5e-4 |

Konfiguriert in `config/pib_hand_config_v5.py` → `SERVOS` (Datenblattwerte) und
`V5_ACTUATORS` (Gelenkgruppe → Servo, Nenn-Trägheit aus dem Audit für die Dämpfung);
`servo_actuator()` liefert die Werte in Prim-Einheiten (Nm/°, von `setup_stage.py`
angewendet) und in rad (für Isaac Lab). v4 behält die
Referenzwerte von `0fdbc62` (`_v4_gains`, `maxForce=inf`).

Prüfen mit `isaac_sim/tools/audit_asset.py` (effektive Gelenkträgheit aus der Massenmatrix,
ω_n·Δt, ζ, Schwerkraftmoment). Armature 5e-3 kg·m² ist eine Annahme (Rotorträgheit und
Übersetzung des ST3215 nicht im Datenblatt).

### Physikalisch validiert
Pickup-/Putdown-Demo bewegen den Roboter korrekt, Kontakt und Reibung mit dem Zylinder
funktionieren (siehe `ros2_ws/src/pib_bringup/pib_bringup/test_client_pickup.py`). v5 mit
Mimic Joints: `test_client_mimic_v5` (Kopplung frei, Δ ≤ 0,2°) und
`test_client_mimic_load_v5` (Finger gegen Tisch: Kopplung ≤ 0,1°, kein Ausbrechen; mit
Servo-Arm gibt der Ellbogen nach, statt dass der Finger stallt). Pickup-Demo v5: Dose wird
gegriffen, der ausgestreckte Arm hält sie nur knapp (Servo-Grenzen) — Putdown nicht erneut
getestet.

---

## RL-Greifen (Isaac Lab, ADR-014/015)

```
Isaac Lab (conda env_isaaclab)                         reale Hand (Ziel)
  isaac_lab/pib_grasp/  Greifaufgabe (Dexsuite-Muster)   STM32N657 (NUCLEO-N657X0, NPU)
  isaac_lab/pib_hand_left_v5_cfg.py  Asset + Aktuatoren   ← Policy als int8-ONNX (ST Edge AI)
  isaac_sim/usd/pib_hand_left_v5.usd  Hand + Unterarm      8 Servos (ST3215), 5 FSR
  config/pib_hand_config_v5.py  Servo-/Pleuel-Modell (gemeinsame Quelle mit Isaac Sim)
```

- **Asset**: nur Unterarm + Hand (eigener `onshape-to-robot`-Export), Basis fest. Mimic
  Joints, Limits, Antriebe, Self-Collision und Filtered Pair Unterarm ↔ Daumen-Rotator
  eingebrannt (`isaac_sim/tools/bake_hand_asset_v5.py`). Kein Action Graph, keine
  `IsaacContactSensor`-Prims — Isaac Lab bringt eigene Kontaktsensoren mit.
- **Aktuatoren** (`pib_hand_left_v5_cfg.py`): 7 Servos implizit (PhysX-PD, Werte aus
  `servo_actuator()` in rad), Handgelenk explizit über `RemotizedPDActuatorCfg` (Pleuel,
  winkelabhängiges Moment), 9 Folgegelenke passiv.
- **Aufgabe** (`pib_grasp/env_cfg.py`, `mdp.py`): Hand seitlich, Dose auf kinematischem Tisch,
  ab 2 s sinkt der Tisch; Policy sieht 8 Gelenkwinkel + 5 FSR + letzte Aktion (Verlauf 5),
  Critic zusätzlich privilegierte Größen; PPO über Isaac Labs `rsl_rl`-Skripte
  (`isaac_lab/train.py`/`play.py` registrieren nur die Tasks und starten diese).
- **Werkzeuge**: `check_hand_asset.py` (Mimic, Sensoren, Antriebe), `scripted_grasp_test.py`
  (Machbarkeit ohne Policy), `_probe_geometry.py`/`_debug_scene.py` (Diagnose).
- Schnittstelle Policy ↔ Firmware: `docs/conventions.md` → „Isaac Lab“.

---

## Robot-Prim (v4)
```
ROBOT_PRIM_PATH = /World/pib_upperbody_URDF/pib_upperbody_URDF   (aus config/pib_hand_config_v4.py)
DOFs: 14 Body + 15 linke Hand + 15 rechte Hand = 44 gesamt
```
v5: Roboter-Wrapper `/World/pib_upperbody_urdf_v5`, Articulation Root
`/World/pib_upperbody_urdf_v5/root_joint`, dieselbe DOF-Aufteilung, andere Namen (kein
`dof_`-Präfix, Daumen-Mittelgelenk heißt `tip` statt `distal`). 18 der 44 DOFs (Finger-
`distal`/`tip`, `thumb_*_tip`) sind passive Mimic-Folgegelenke.

---

## Offen (aktuelles Ziel dieses Branches)

### Contact Sensors (v5 ✓, ADR-008 + ADR-013)
Kontaktkräfte pro Fingertip, für Greif-Erkennung. Nativer `IsaacContactSensor`-Prim an allen
10 Fingertip-Links (`<link>/Contact_Sensor`, radius −1 = ganzes Glied) + je ein
`ReadContact_<finger>`-Knoten; die 10 Kräfte werden über `ConstructArray` → `ToDouble`
gebündelt und mit Simulationszeit (`IsaacTimeSplitter`) als `sensor_msgs/JointState` auf
`/pib/fingertip_forces` publiziert (Reihenfolge/Format: `docs/conventions.md`). Aufbau per
`build_contact_sensors_v5.py` + `build_fingertip_force_graph_v5.py`. Verworfen:
`ArticulationView.get_net_contact_forces()` (Tensor-API, bräuchte Script Node) und ein
Script Node zum Bündeln (Leon: nur native Nodes).

**Bekannter Stolperstein**: Der Onshape-Importer legt Robotik-Meshes standardmäßig als
`instanceable` an (Performance-Feature für viele parallele Roboter-Instanzen, hier ohne
Nutzen). Ein `IsaacContactSensor`-Prim lässt sich nicht unter einem Instance-Proxy anlegen
(„authoring to an instance proxy is not allowed") — vorher `SetInstanceable(False)` auf
dem jeweiligen Fingertip-Link-Prim setzen.

v5: Die Link-Prims sind nicht instanceable, nur ihre `visuals`/`collisions`-Kinder — die
Sensor-Prims ließen sich direkt am Link anlegen. v4: nur `index_right` (Einzel-Topic, ADR-008).

### Szenen-Erweiterung
Weitere Objekte/Umgebung in `isaac_sim/usd/pib_upperbody_v4.usd` — Details noch offen.

### v5-Hand-Integration
v5 läuft dauerhaft parallel zu v4 (nicht ablösend), Repo-Struktur bereits auf `_v4`/`_v5`
gezogen (USD, `config/`, roher Onshape-Export, ROS2-Package). Action Graph, ros2_control-
Stack, Pickup-/Putdown-Demo, `config/pib_hand_config_v5.py` und Fingerkopplung (Mimic
Joints, ADR-011) und das Servo-Aktuatormodell (ADR-012) für v5 sind fertig. Noch offen:
Putdown-Regression, ADR zur
v5-Reimport-Entscheidung (bisher nur in `docs/current-sprint.md` nacherzählt).

---

## Bewusst nicht Teil dieses Branches
Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface), LSTM-Gelenkdynamik,
AS5600-Sensordaten — voller Fahrplan dazu auf `feature/ros2-control`.
