# pib Hand Simulation

Simulationsserver für den RoboCup 2027 (@Home Liga).
Ziel: pib v4 Oberköper (44 DOFs) in NVIDIA Isaac Sim 5.1 — steuerbar über ros2_control, Greifkraft-Erkennung, später LSTM-Gelenkdynamik.

---

## Aktueller Stand

| Phase | Status |
|---|---|
| Isaac IO-Schicht (robot_io, setup_stage) | ✓ fertig |
| Control-Architektur (DirectMode, ServoMode, NNMode) | ✓ fertig |
| Sequenz-Executor (runner.py, Smoothstep) | ✓ fertig |
| ros2_control-Stack (JTC, JointStateBroadcaster, TopicBasedSystem) | ✓ end-to-end verifiziert |
| pib_bridge.py (Isaac ↔ ros2_control) | ✓ fertig |
| is_grasping() via Admittanz | geplant (Sprint 3) |
| Scene API (reset, place_object) | geplant (Sprint 3) |
| AS5600-Sensordaten + LSTM-Training | Phase 5 |

---

## Onboarding für Teamkollegen

Dieser Abschnitt führt von Null bis zur laufenden Simulation.

### 1 — Voraussetzungen installieren

**NVIDIA GPU + Treiber**
Mindestens eine RTX-Klasse GPU, Treiber ≥ 550. Ohne GPU läuft Isaac Sim nicht.

**Isaac Sim 5.1** (native auf Ubuntu 24.04, einmalig ~20 GB)
NVIDIA-Dokumentation unter [docs.isaacsim.omniverse.nvidia.com](https://docs.isaacsim.omniverse.nvidia.com) → „Installation" → „Workstation" folgen.
Isaac Sim wird nach `~/isaacsim/` installiert (kein System-PATH-Eintrag).

**ROS2 Jazzy**
```bash
sudo apt install ros-jazzy-desktop ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
                 ros-jazzy-controller-manager ros-jazzy-robot-state-publisher
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### 2 — Repo klonen und bauen

```bash
git clone https://github.com/churro206/pib-hand-sim
cd pib-hand-sim
```

ROS2-Workspace bauen (einmalig):
```bash
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build
cd ..
```

> **Hinweis:** Falls du eine `.venv` im Repo-Root nutzt, muss `catkin_pkg` installiert sein:
> `pip install catkin_pkg`

Die USD-Dateien sind im Repo (`isaac_sim/usd/`) — kein extra Download nötig.

### 3 — Isaac Sim starten

> **Wichtig:** ROS2 **und** der ros2_ws müssen in derselben Shell gesourced sein, bevor Isaac Sim
> startet — sonst findet `pib_bridge.py` die richtige rclpy-Version nicht.

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh
```

Dann in Isaac Sim:
```
1. File → Open → isaac_sim/usd/pib_upperbody_7_flattened.usd laden
2. Window → Script Editor öffnen
3. isaac_sim/start.py öffnen und ausführen (Strg+Enter)
   → Drives, Limits und T-Pose werden gesetzt
4. Toolbar: Play drücken  ▶
5. isaac_sim/pib_bridge.py öffnen und ausführen
   → „[pib_bridge] Play erkannt..." im Log, nach 0,5 s „Physics View bereit"
```

### 4 — ros2_control-Stack starten (Terminal 2)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch pib_bringup pib_sim.launch.py
```

Erwartete Ausgabe:
```
[ros2_control_node]: Loaded robot description
[spawner-joint_state_broadcaster]: Configured and activated joint_state_broadcaster
[spawner-joint_trajectory_controller]: Configured and activated joint_trajectory_controller
```

Status prüfen:
```bash
ros2 control list_controllers   # beide müssen "active" sein
```

### 5 — Pickup-Demo ausführen (Terminal 3)

```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 run pib_bringup test_client
```

Der Roboter führt die physikalisch verifizierte Dose-Greif-Sequenz aus:
- **t=0s** T-Pose
- **t=2s** Approach — rechter Arm positioniert, Daumen opponiert
- **t=4s** Grasp — alle Finger auf 33°
- **t=6s** Lift — Ellbogen hebt die Dose an

Feedback zeigt jede Sekunde Ist- vs. Soll-Position für Ellbogen, Daumen und Zeigefinger.

---

## Schnellstart (Kurzfassung)

```
# Shell 1 (Isaac starten)
source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
~/isaacsim/isaac-sim.sh
# → USD laden → start.py → Play ▶ → pib_bridge.py

# Shell 2 (ros2_control)
source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 launch pib_bringup pib_sim.launch.py

# Shell 3 (Demo)
source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=0
ros2 run pib_bringup test_client
```

---

## 4a — Sequenzen ohne ros2_control (direkt im Script Editor)

Für lokale Tests ohne den ros2_control-Stack: Sequenz aus `isaac_sim/sequences/` im Script Editor öffnen und ausführen.

| Script | Mode | Beschreibung |
|---|---|---|
| `sequences/test_hand_poses.py` | direct | Winken → Doppelbizeps → Peace |
| `sequences/test_tendon.py` | servo | Sehnenmechanik: Hand 3× schließen/öffnen |
| `sequences/demo_pickup.py` | direct | Dose greifen und heben |

**Neue Sequenz erstellen:** `sequences/template.py` kopieren, Steps anpassen, im Script Editor ausführen. Kein Isaac-Neustart nötig.

---

## Architektur

```
Layer 4: Team-Integration (Sprint 4)
         ROS2-Protokoll, Koordinatenrahmen, IK-Interface

Layer 3: ros2_control-Stack (fertig)          ←
         JointTrajectoryController (FollowJointTrajectory, MoveIt2-kompatibel)
         JointStateBroadcaster → /joint_states
         topic_based_ros2_control (Hardware-Interface-Bridge)

Layer 2: Control-Architektur (fertig)
         DirectMode | ServoMode | NNMode → sequences.py → runner.py

Layer 1: Isaac IO-Schicht (fertig)
         robot_io.py — JOINT_SIGN, Grad↔Rad, DriveAPI, 44 DOFs
```

### Datenfluss (ros2_control-Workflow)

```
[test_client / IK-Team]
  └── FollowJointTrajectory Action
        ↓
[ros2_control (externer Prozess)]
  ├── JointTrajectoryController
  ├── JointStateBroadcaster  → /joint_states (rad)
  └── topic_based_ros2_control
        ↕  /pib/hw/joint_states (rad) + /pib/hw/joint_commands (rad)
[Isaac Sim (Script Editor)]
  └── pib_bridge.py
        ↕  robot_io.py (JOINT_SIGN = -1 hier, nirgendwo sonst)
  └── PhysX-Physik-Simulation
```

---

## ROS2-Schnittstelle

### Externe Topics (für IK-Team und andere)

| Topic | Typ | Richtung | Beschreibung |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | ← ros2_control | Ist-Positionen aller 44 DOFs, 50 Hz, **rad** |
| `/joint_trajectory_controller/follow_joint_trajectory` | Action `control_msgs/FollowJointTrajectory` | → ros2_control | Trajektorie mit Zeitpunkten, MoveIt2-kompatibel |

### Interne Bridge-Topics (pib_bridge.py ↔ ros2_control)

| Topic | Typ | Richtung |
|---|---|---|
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (50 Hz, rad) |
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad) |

**Winkeleinheit:** ros2_control-Stack arbeitet in **Radiant**. `pib_bridge.py` konvertiert intern nach Grad für `robot_io`.

---

## Bekannte Fallstricke

| Problem | Lösung |
|---|---|
| `ModuleNotFoundError: rclpy._rclpy_pybind11` | ROS2 Jazzy nutzt Python 3.12, Isaac Sim 3.11. `pib_bridge.py` löst das automatisch durch Isaac-eigenen rclpy-Path. |
| `controller_manager` wartet ewig auf `/robot_description` | Jazzy-Breaking-Change: ros2_control subscribed Topic statt Parameter. Gelöst durch `robot_state_publisher` in `pib_sim.launch.py`. |
| „Physics Simulation View is not created yet" | Gibt es nicht mehr. `pib_bridge.py` wartet 0,5s Grace-Period nach Play bevor es Physics API aufruft. |
| Warnings nach Stop + erneutem Play | Gelöst: `pib_bridge.py` invalidiert das Robot-Handle beim Stop und re-initialisiert es nach dem nächsten Play. |
| Isaac Sim startet aber ROS2 nicht gefunden | ROS2 muss **vor** Isaac Sim gesourced sein: `source /opt/ros/jazzy/setup.bash && ~/isaacsim/isaac-sim.sh` |

---

## Schlüsseldateien

```
config/
  pib_hand_config.py     DOF-Namen, Indizes, JOINT_SIGN, Servo-Faktoren
  sequences.py           Pose-Sequenzen (Onshape-Konvention)
  server_config.py       Winkeleinheit, Thresholds

control/
  base.py                ControlMode ABC
  direct.py              DirectMode — pass-through
  servo.py               ServoMode — Sehnen-Mapping
  nn.py                  NNMode — Stub (Phase 5)

isaac_sim/
  robot_io.py            Einzige Isaac-IO-Schicht: set/get, JOINT_SIGN
  setup_stage.py         Drives + Limits (einmalig pro Session)
  start.py               Startroutine (configure_physics + drives + limits + pose)
  runner.py              Sequenz-Executor (Library): execute(seq, mode, side)
  pib_bridge.py          ROS2-Bridge: /pib/hw/* ↔ robot_io (50 Hz)
  sequences/
    template.py          Vorlage für neue Sequenzen (kopieren + anpassen)
    test_hand_poses.py   Winken → Doppelbizeps → Peace
    test_tendon.py       Sehnenmechanik-Test (ServoMode)
    demo_pickup.py       Dose greifen und heben (physikalisch verifiziert)

ros2_ws/src/
  pib_description/       URDF (44 DOFs + ros2_control-Tags) + STL-Meshes
  pib_bringup/
    launch/pib_sim.launch.py      Startet gesamten ros2_control-Stack
    config/controllers.yaml       JTC + JointStateBroadcaster, 50 Hz
    pib_bringup/test_client.py    Pickup-Demo via FollowJointTrajectory
```

---

## Konventionen

### Winkel
- Intern immer **Grad**, Onshape-Konvention (positiv = Flexion/Heben/Vorne)
- `JOINT_SIGN = -1` kompensiert Onshape↔Isaac — **nur in robot_io**, nie außerhalb
- ros2_control-Stack arbeitet in **Radiant** — `pib_bridge.py` konvertiert
- Hand-Clip: `[0°, 90°]` vor JOINT_SIGN; Body: kein Clip

### Isaac Sim
- Kein `time.sleep()` → `await app.next_update_async()` (Editor) / `sim_app.update()` (Standalone)
- `_load_mod(name, path)` in jedem Skript → umgeht stale `.pyc`-Cache
- `configure_drives()` jede Session aufrufen (PhysX cached Stiffness/Damping nicht)
- `pib_bridge.py` erneut ausführen = hot-reload (stoppt vorherige Instanz)

### ROS2
- `ROS_DOMAIN_ID=0` — Projektstandard für alle Teams
- Isaac Sim mit gesourced ROS2 starten (nicht danach)

---

## Fingertip-Kontaktkräfte (geplant, Sprint 3)

`ArticulationView.get_net_contact_forces()` aus `isaacsim.core.prims` — dieselbe API wie Isaac Lab's `ContactSensor`, ohne Isaac-Lab-Install. Gibt die summierte Kontaktkraft (Newton) pro Fingertip-Link zurück.

Veröffentlicht auf `/pib/fingertip_forces` (`sensor_msgs/JointState`, 50 Hz):
- `name`: `["thumb_right", "index_right", "middle_right", "ring_right", "pinky_right"]`
- `effort`: Kraft pro Fingertip in Newton

Direkt LSTM-fähig — gleiche Modalität wie echte FSR-Sensoren (Gesamtkraft, kein Torque-Umweg).
Voraussetzung: Fingertip-Prim-Pfade mit `inventory.py` bestimmen.

---

## Phase 5 — LSTM-Gelenkdynamik (geplant)

Das Netz lernt `(Sollwinkel_t, Istwinkel_{t-1}) → Istwinkel_t` — modelliert Trägheit,
Reibung und Hysterese der Sehnenmechanik.

```
Isaac Sim (synthetisch) ──┐
                           ├── training/train.py → hand_lstm_*.pt
AS5600-Sensordaten (real) ─┘
         ↓
   export_onnx.py → *.onnx → STM32 (Nucleo H723ZG)
   export_weights.py → *_weights.npz → NNMode in Isaac
```

`requirements.txt` und Docker sind **nur für das LSTM-Training** — nicht für die Simulation selbst.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose build && docker compose run --rm train
```

---

## Team

| Team | Aufgabe | Schnittstelle |
|---|---|---|
| pib-Sim (Leon) | Simulation, Control, ros2_control-Stack | — |
| IK-Team | Gelenkwinkel-Trajektorien berechnen | `/joint_trajectory_controller/follow_joint_trajectory` (Action) |
| Greifpunkt-Team | Greifpunkterkennung im Roboterframe | → (Sprint 4) |
| Objekterkennung | Objekte im Kamerabild erkennen | hinten angestellt |
