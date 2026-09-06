# Architektur

**Branch `experiment/omnigraph-lightweight`.** Beschreibt den Stand dieses Branches. Der
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

---

## Layer 1 — Isaac-Setup

| Datei | Verantwortung |
|---|---|
| `config/pib_hand_config_v4.py` | DOF-Namen, Indizes, `ROBOT_PRIM_PATH`, Joint-Limits |
| `isaac_sim/setup_stage.py` | Physics Scene, Boden/Licht, Joint-Drives (Stiffness/Damping), Initialpose |
| `isaac_sim/start.py` | Bündelt `setup_stage`-Aufrufe, vor Play im Script Editor ausführen |
| `isaac_sim/autostart.py` | Vollautomatisch: USD laden → `start.py` → Play (`--exec`, kein Script Editor nötig) |

Läuft jede Session neu (PhysX cached Drive-Stiffness/Damping nicht zwischen Sessions).

### Physikalisch validiert
Pickup-/Putdown-Demo bewegen den Roboter korrekt, Kontakt und Reibung mit dem Zylinder
funktionieren (siehe `ros2_ws/src/pib_bringup/pib_bringup/test_client_pickup.py`).

---

## Robot-Prim (v4)
```
ROBOT_PRIM_PATH = /World/pib_upperbody_URDF/pib_upperbody_URDF   (aus config/pib_hand_config_v4.py)
DOFs: 14 Body + 15 linke Hand + 15 rechte Hand = 44 gesamt
```
v5-Prim-Pfad/DOF-Struktur noch offen — v5 hat dieselbe DOF-Aufteilung, aber andere
Gelenk-/Link-Namen (kein `dof_`-Präfix, Daumen-Mittelgelenk heißt `tip` statt `distal`),
siehe `docs/current-sprint.md`.

---

## Offen (aktuelles Ziel dieses Branches)

### Contact Sensors
Kontaktkräfte pro Fingertip, für Greif-Erkennung. Entschieden (ADR-008): nativer
`IsaacContactSensor`-Prim pro Fingertip-Link + `Isaac Read Contact Sensor Node` im Action
Graph, Ausgabe über einen generischen `ROS2 Publisher`-Node (`std_msgs/Float32`) auf
`/pib/fingertip_force/<finger>`. Verworfen: `ArticulationView.get_net_contact_forces()`
(Tensor-API) — hätte einen Script Node mit echtem Python-Code gebraucht, Bruch mit dem
"kein Custom-Python"-Prinzip dieses Branches.

**Bekannter Stolperstein**: Der Onshape-Importer legt Robotik-Meshes standardmäßig als
`instanceable` an (Performance-Feature für viele parallele Roboter-Instanzen, hier ohne
Nutzen). Ein `IsaacContactSensor`-Prim lässt sich nicht unter einem Instance-Proxy anlegen
(„authoring to an instance proxy is not allowed") — vorher `SetInstanceable(False)` auf
dem jeweiligen Fingertip-Link-Prim setzen.

Bisher nur `index_right` verkabelt und verifiziert. Restliche 9 Fingerspitzen offen, siehe
`docs/current-sprint.md`.

### Szenen-Erweiterung
Weitere Objekte/Umgebung in `isaac_sim/usd/pib_upperbody_v4.usd` — Details noch offen.

### v5-Hand-Integration
v5 läuft dauerhaft parallel zu v4 (nicht ablösend), Repo-Struktur bereits auf `_v4`/`_v5`
gezogen (USD, `config/`, roher Onshape-Export, ROS2-Package). Noch offen: `pib_hand_config_v5.py`
(DOF-Namen/Limits gegen die echte Stage verifizieren, nicht nur aus der URDF übernehmen),
`isaac_sim/usd/pib_upperbody_v5.usd` flatten + Action Graph/Contact Sensors aufbauen,
`ros2_ws/src/pib_description_v5/` (inkl. handgepflegter `<ros2_control>`-Tags, analog zu
`pib_description_v4`). v5-Gelenkachsen sind laut Import bereits korrekt orientiert —
`flip_joint_sign.py` (ADR-007) vermutlich nicht nötig, aber noch nicht gegengeprüft.

---

## Bewusst nicht Teil dieses Branches
Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface), LSTM-Gelenkdynamik,
AS5600-Sensordaten — voller Fahrplan dazu auf `feature/ros2-control`.
