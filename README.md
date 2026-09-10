# pib Hand Simulation

Simulationsserver für den RoboCup 2027 (@Home Liga).
pib v4 Oberkörper (44 DOFs) in NVIDIA Isaac Sim 5.1 — steuerbar über ros2_control.

**Branch `experiment/omnigraph-lightweight`:** bewusst minimaler Zweig. Die Isaac-seitige
ROS2-Anbindung läuft komplett über einen nativen Action Graph (OmniGraph) statt über
eigenen Python-Bridge-Code. Alles, was für diesen Weg nicht gebraucht wird (robot_io,
ControlMode-Architektur, Sequenz-Executor, LSTM-Pipeline), wurde aus diesem Branch entfernt.
Der volle Stand liegt weiterhin auf `feature/ros2-control`.

---

## Aktueller Stand

| Teil | v4 | v5 |
|---|---|---|
| USD-Stage mit Action Graph (ROS2 Subscribe/Publish Joint State + Articulation Controller) | ✓ läuft | ✓ läuft |
| ros2_control-Stack (JTC, JointStateBroadcaster, TopicBasedSystem) | ✓ end-to-end verifiziert | ✓ end-to-end verifiziert |
| Pickup-Demo (Dose greifen und heben) | ✓ physikalisch verifiziert | ✓ läuft |
| Putdown-Demo (Dose absetzen und loslassen — Umkehrung der Pickup-Demo) | ✓ | ✓ läuft, Dose kippt gelegentlich um |
| Contact Sensors (Fingertip-Kontaktkraft) | nur `index_right` verkabelt | offen |

---

## Onboarding

### 1 — Voraussetzungen installieren

**NVIDIA GPU + Treiber**
Mindestens eine RTX-Klasse GPU, Treiber ≥ 550.

**Isaac Sim 5.1** (native auf Ubuntu 24.04)
NVIDIA-Dokumentation unter [docs.isaacsim.omniverse.nvidia.com](https://docs.isaacsim.omniverse.nvidia.com) → „Installation" → „Workstation" folgen.
Isaac Sim wird nach `~/isaacsim/` installiert (kein System-PATH-Eintrag).

**ROS2 Jazzy**
```bash
sudo apt install ros-jazzy-desktop ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
                 ros-jazzy-controller-manager ros-jazzy-robot-state-publisher
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2 — Repo klonen und ros2_ws bauen

```bash
git clone https://github.com/churro206/pib-hand-sim
cd pib-hand-sim
source /opt/ros/jazzy/setup.bash
cd ros2_ws && colcon build && cd ..
```

Die USD-Datei liegt im Repo — enthält Roboter **und** den Action Graph, kein separater
Export nötig. **v4 und v5 laufen dauerhaft parallel** (v5 löst v4 nicht ab), eigene USD,
eigenes ROS2-Package, eigene Launch-/Config-/Client-Dateien je Version:

| | v4 (verifizierte Referenz) | v5 (im Aufbau) |
|---|---|---|
| USD | `isaac_sim/usd/pib_upperbody_v4.usd` | `isaac_sim/usd/pib_upperbody_v5.usd` |
| ROS2-Description-Package | `pib_description_v4` | `pib_description_v5` |
| Launch-Datei | `pib_sim.launch.py` | `pib_sim_v5.launch.py` |
| Controller-Config | `controllers.yaml` | `controllers_v5.yaml` |
| Pickup-/Putdown-Client | `test_client_pickup`/`_putdown` | `test_client_pickup_v5`/`_putdown_v5` |
| DOF-Namensschema | `dof_*` (mit Präfix) | ohne Präfix, Daumen-Mittelgelenk `tip` statt `distal` |

> **Wichtig: v4- und v5-Stack niemals gleichzeitig laufen lassen** — beide nutzen dieselben
> `/pib/hw/joint_commands`/`/pib/hw/joint_states`-Topics und denselben Action-Namen. Ein
> zweiter `ros2 launch`-Aufruf neben einem schon laufenden kollidiert am
> `controller_manager`-Knotennamen (`A controller named '...' was already loaded`) — erst
> den einen sauber beenden (Strg+C), bevor der andere startet.

### 3 — Isaac Sim starten

> ROS2 **und** der ros2_ws müssen in derselben Shell gesourced sein, bevor Isaac Sim
> startet — der Action Graph nutzt Isaacs eigene rclpy-Version, die nur bei korrekt
> gesourcter Umgebung sauber gefunden wird.

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh
```

Dann in Isaac Sim:
```
1. File → Open → isaac_sim/usd/pib_upperbody_v4.usd  (oder _v5.usd) laden
2. Window → Script Editor öffnen
3. isaac_sim/start.py öffnen und ausführen (Strg+Enter)
   → Drives, Limits und T-Pose werden gesetzt (Version-unabhängig, dieselbe start.py)
4. Toolbar: Play drücken  ▶
```

Damit läuft alles — der Action Graph ist Teil der jeweiligen USD-Stage und aktiviert sich
automatisch mit Play. Kein weiteres Skript nötig.

**Schnellstart-Alternative** (ein Terminal, kein Script Editor, lädt immer v4):
```bash
source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh --exec ~/repos/pib-hand-sim/isaac_sim/autostart.py
```
Lädt v4-USD, führt `start.py` aus, drückt Play — vollautomatisch. Für v5: Schritt 3 oben
manuell durchgehen (`autostart.py` kennt bisher nur v4).

### 4 — ros2_control-Stack starten (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0

ros2 launch pib_bringup pib_sim.launch.py       # v4
ros2 launch pib_bringup pib_sim_v5.launch.py    # v5 — je nachdem, welche USD offen ist
```

Status prüfen:
```bash
ros2 control list_controllers          # beide müssen "active" sein
ros2 topic echo /joint_states --once   # plausible Werte, nicht leer/stale
```

### 5 — Pickup-/Putdown-Demo ausführen (Terminal 3)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0

ros2 run pib_bringup test_client_pickup        # v4 — Dose greifen und heben
ros2 run pib_bringup test_client_putdown       # v4 — danach: Dose absetzen und loslassen

ros2 run pib_bringup test_client_pickup_v5     # v5 — dieselbe Rolle wie oben
ros2 run pib_bringup test_client_putdown_v5    # v5
```

Beide Versionen folgen derselben 4-Waypoint-Choreografie, je 2s Abstand — nur die genauen
Winkel/die Anzahl gesendeter DOFs unterscheiden sich (v4 sendet eine Teilmenge von 25/44
DOFs mit fest im Skript kodierten Werten; v5 sendet alle 44 DOFs, 1:1 aus einer per
`isaac_sim/tools/dump_pose.py` in der laufenden Stage aufgenommenen Sequenz —
`isaac_sim/tools/_pose_dump.json`, gitignored, siehe Skript-Docstrings für die exakten
Werte):
- **t=0s** neutral — T-Pose
- **t=2s** approach — rechter Arm über die Dose, Daumen opponiert
- **t=4s** grasp — rechte Finger schließen
- **t=6s** lift — Ellbogen/Schulter hebt die Dose an

Putdown ist jeweils die exakte Umkehrung (lift → grasp → approach → neutral). Beide zeigen
per Feedback jede Sekunde Ist- vs. Soll-Position für Ellbogen, Daumen und Zeigefinger.

**Bekannt, noch offen (v5)**: Beim Absetzen kippt die Dose am Ende gelegentlich um —
Sequenz funktioniert grundsätzlich, Feinschliff der Absetz-Trajektorie steht noch aus.

---

## Architektur (dieser Branch)

```
[test_client_pickup / test_client_putdown]
  └── FollowJointTrajectory Action
        ↓
[ros2_control (externer Prozess)]
  ├── JointTrajectoryController
  ├── JointStateBroadcaster  → /joint_states (rad)
  └── topic_based_ros2_control
        ↕  /pib/hw/joint_states (rad) + /pib/hw/joint_commands (rad)
[Isaac Sim]
  └── Action Graph (Teil der USD-Stage, kein externes Skript)
        ROS2SubscribeJointState → Script Node (Vorzeichen-Invertierung)
          → IsaacArticulationController
        Artikulation → ROS2PublishJointState
  └── PhysX-Physik-Simulation
```

### Der Action Graph im Detail

Liegt vollständig in `isaac_sim/usd/pib_upperbody_v4.usd` (Window → Graph Editors
→ Action Graph zum Ansehen/Bearbeiten). Vier Nodes:

1. **`ROS2SubscribeJointState`** — `topicName = /pib/hw/joint_commands`
2. **Script Node** — invertiert `positionCommand` (Onshape-URDF und Isaacs importierte
   Gelenkachsen sind bei diesem Modell vorzeicheninvertiert; ohne diesen Schritt schließt
   sich die Hand in die falsche Richtung):
   ```python
   def compute(db: og.Database):
       db.outputs.jointNames = db.inputs.jointNames
       db.outputs.positionCommand = [-p for p in db.inputs.positionCommand]
   ```
3. **`IsaacArticulationController`** — `targetPrim` = Artikulations-Root des Roboters
4. **`ROS2PublishJointState`** — `topicName = /pib/hw/joint_states`

**Bekannter Kompromiss:** `ROS2PublishJointState` liest den Gelenkzustand direkt aus dem
Prim (Isaac-Konvention) — dort gibt es keinen Punkt, um die Vorzeichen-Invertierung
gegenzurechnen. Die Bewegung selbst ist korrekt, aber `/pib/hw/joint_states`,
`/joint_states` und die Action-Feedback-Werte (Konsolenausgabe von `test_client_pickup`) zeigen
gespiegelte Werte. `controllers.yaml` hat keine Toleranz-Constraints gesetzt, daher bricht
dadurch nichts ab — nur die Logausgabe ist verwirrend, nicht die tatsächliche Bewegung.

`velocityCommand`/`effortCommand` (an `ROS2SubscribeJointState`/`IsaacArticulationController`)
bleiben unverbunden — `controllers.yaml` konfiguriert nur `command_interfaces: [position]`.

---

## ROS2-Schnittstelle

| Topic | Typ | Richtung | Beschreibung |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | ← ros2_control | Ist-Positionen aller 44 DOFs, 50 Hz, rad (Isaac-Konvention, siehe Kompromiss oben) |
| `/joint_trajectory_controller/follow_joint_trajectory` | Action `control_msgs/FollowJointTrajectory` | → ros2_control | Trajektorie mit Zeitpunkten, MoveIt2-kompatibel |
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad) | Von `topic_based_ros2_control`, gelesen vom Action Graph |
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (rad) | Vom Action Graph publiziert, gelesen von `topic_based_ros2_control` |

---

## Bekannte Fallstricke

| Problem | Lösung |
|---|---|
| `ModuleNotFoundError: rclpy._rclpy_pybind11` | ROS2 Jazzy nutzt Python 3.12, Isaac Sim 3.11. ROS2 **vor** Isaac Sim in derselben Shell sourcen — Isaacs eigene rclpy-Version greift dann automatisch. |
| `controller_manager` wartet ewig auf `/robot_description` | Jazzy-Breaking-Change: ros2_control subscribed Topic statt Parameter. Gelöst durch `robot_state_publisher` in `pib_sim.launch.py`. |
| `Package 'pib_bringup' not found` | `ros2_ws/install/setup.bash` wurde in dieser Shell nicht gesourced — `cd` ändert daran nichts, `AMENT_PREFIX_PATH` fehlt der Eintrag. |
| Hand schließt in falsche Richtung / läuft in Limits | Vorzeichen-Script-Node zwischen `ROS2SubscribeJointState` und `IsaacArticulationController` fehlt oder ist falsch verkabelt (siehe oben). |
| `/joint_states`-Werte wirken gespiegelt/falsch | Bekannter Kompromiss (siehe oben) — Bewegung im Viewport prüfen, nicht nur die Konsole. |
| Isaac Sim startet aber ROS2 nicht gefunden | ROS2 muss **vor** Isaac Sim gesourced sein: `source /opt/ros/jazzy/setup.bash && ~/isaacsim/isaac-sim.sh` |

---

## Schlüsseldateien

```
config/
  pib_hand_config_v4.py   DOF-Namen, Indizes, ROBOT_PRIM_PATH, Joint-Limits (für start.py)

isaac_sim/
  start.py                Session-Setup: Drives, Limits, T-Pose (vor Play ausführen)
  setup_stage.py           von start.py genutzt
  autostart.py             vollautomatischer Start ohne Script Editor (--exec)
  usd/
    pib_upperbody_v4.usd   Roboter (v4) + Action Graph
    pib_upperbody_v5.usd   Roboter (v5) + Action Graph
  tools/
    dump_pose.py           Nimmt Drive-Targets der aktuell posierten Gelenke als Waypoint
                            auf → isaac_sim/tools/_pose_dump.json (gitignored)

ros2_ws/src/
  pib_description_v4/     URDF (44 DOFs + ros2_control-Tags) + STL-Meshes
  pib_description_v5/     dasselbe für v5 (kein dof_-Präfix in den Joint-Namen)
  pib_bringup/
    launch/pib_sim.launch.py           Startet ros2_control-Stack (v4)
    launch/pib_sim_v5.launch.py        dasselbe für v5
    config/controllers.yaml            JTC + JointStateBroadcaster, 50 Hz (v4)
    config/controllers_v5.yaml         dasselbe für v5
    pib_bringup/test_client_pickup.py       Pickup-Demo v4 via FollowJointTrajectory
    pib_bringup/test_client_putdown.py      Putdown-Demo v4 (Umkehrung)
    pib_bringup/test_client_pickup_v5.py    Pickup-Demo v5, aus dump_pose.py-Sequenz
    pib_bringup/test_client_putdown_v5.py   Putdown-Demo v5 (Umkehrung)
  topic_based_ros2_control/   Hardware-Interface-Bridge (Drittanbieter-Paket)

scripts/
  start_isaac.sh, start_ros2.sh, launch.sh   Terminal-Automatisierung
```

---

## Konventionen

### Winkel
- ros2_control-Stack arbeitet durchgehend in **Radiant**
- `/pib/hw/joint_commands` und Trajektorie-Ziele: "echte"/URDF-Konvention (0°–90° Flexion positiv)
- Innerhalb der Simulation (nach dem Vorzeichen-Script-Node): Isaac-Konvention, invertiert

### ROS2
- `ROS_DOMAIN_ID=0` — Projektstandard
- Isaac Sim mit gesourced ROS2 starten (nicht danach)

---

## Team

| Team | Aufgabe | Schnittstelle |
|---|---|---|
| pib-Sim (Leon) | Simulation, ros2_control-Stack | — |
| IK-Team | Gelenkwinkel-Trajektorien berechnen | `/joint_trajectory_controller/follow_joint_trajectory` (Action) |
| Greifpunkt-Team | Greifpunkterkennung im Roboterframe | → (Sprint 4) |
| Objekterkennung | Objekte im Kamerabild erkennen | hinten angestellt |
