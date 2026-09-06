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

| Teil | Status |
|---|---|
| USD-Stage mit Action Graph (ROS2 Subscribe/Publish Joint State + Articulation Controller) | ✓ läuft |
| ros2_control-Stack (JTC, JointStateBroadcaster, TopicBasedSystem) | ✓ end-to-end verifiziert |
| Pickup-Demo (Dose greifen und heben) | ✓ physikalisch verifiziert |
| Putdown-Demo (Dose absetzen und loslassen — Umkehrung der Pickup-Demo) | ✓ |

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

Die USD-Datei liegt im Repo (`isaac_sim/usd/pib_upperbody_v4.usd`) — enthält Roboter
**und** den Action Graph, kein separater Export nötig.

### 3 — Isaac Sim starten

> **Wichtig:** ROS2 **und** der ros2_ws müssen in derselben Shell gesourced sein, bevor Isaac
> Sim startet — der Action Graph nutzt Isaacs eigene rclpy-Version, die nur bei korrekt
> gesourcter Umgebung sauber gefunden wird.

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh
```

Dann in Isaac Sim:
```
1. File → Open → isaac_sim/usd/pib_upperbody_v4.usd laden
2. Window → Script Editor öffnen
3. isaac_sim/start.py öffnen und ausführen (Strg+Enter)
   → Drives, Limits und T-Pose werden gesetzt
4. Toolbar: Play drücken  ▶
```

Damit läuft alles — der Action Graph ist Teil der USD-Stage und aktiviert sich automatisch
mit Play. Kein weiteres Skript nötig.

**Schnellstart-Alternative** (ein Terminal, kein Script Editor):
```bash
source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh --exec ~/repos/pib-hand-sim/isaac_sim/autostart.py
```
Lädt USD, führt `start.py` aus, drückt Play — vollautomatisch.

### 4 — ros2_control-Stack starten (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch pib_bringup pib_sim.launch.py
```

Status prüfen:
```bash
ros2 control list_controllers   # beide müssen "active" sein
```

### 5 — Pickup-/Putdown-Demo ausführen (Terminal 3)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0

ros2 run pib_bringup test_client_pickup     # Dose greifen und heben
ros2 run pib_bringup test_client_putdown    # danach: Dose absetzen und loslassen
```

`test_client_pickup`:
- **t=0s** T-Pose
- **t=2s** Approach — rechter Arm positioniert, Daumen opponiert
- **t=4s** Grasp — alle Finger auf 33°
- **t=6s** Lift — Ellbogen hebt die Dose an

`test_client_putdown` (genau umgekehrt, im Anschluss an `test_client_pickup` ausführen):
- **t=0s** Lift-Zustand (Startpunkt)
- **t=2s** Grasp — Ellbogen senkt die Dose ab
- **t=4s** Approach — Finger öffnen, Dose losgelassen
- **t=6s** Neutral — Arm zurück in T-Pose

Beide zeigen per Feedback jede Sekunde Ist- vs. Soll-Position für Ellbogen, Daumen und
Zeigefinger.

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
    pib_upperbody_v4.usd   Roboter + Action Graph

ros2_ws/src/
  pib_description_v4/     URDF (44 DOFs + ros2_control-Tags) + STL-Meshes
  pib_bringup/
    launch/pib_sim.launch.py        Startet gesamten ros2_control-Stack
    config/controllers.yaml         JTC + JointStateBroadcaster, 50 Hz
    pib_bringup/test_client_pickup.py     Pickup-Demo via FollowJointTrajectory
    pib_bringup/test_client_putdown.py   Putdown-Demo (Umkehrung von test_client_pickup)
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
