# pib Hand Simulation

Simulationsserver für den RoboCup 2027 (@Home Liga).
pib-Oberkörper (v4 und v5, je 44 DOFs) in NVIDIA Isaac Sim 5.1 — steuerbar über ros2_control —
und RL-Greifen in NVIDIA Isaac Lab für die reale linke v5-Hand.

**Branch `feature/rl-grasping`** = digitaler Zwilling von `experiment/omnigraph-lightweight`
plus RL-Greifen (Proof of Concept, `isaac_lab/`, ADR-014–020):
- **Digitaler Zwilling:** Die Isaac-seitige ROS2-Anbindung läuft komplett über einen nativen
  Action Graph (OmniGraph) statt über eigenen Python-Bridge-Code. robot_io,
  ControlMode-Architektur, Sequenz-Executor und LSTM-Pipeline liegen auf `feature/ros2-control`.
- **RL-Greifen:** Greif-Policy für 8 Servos und 5 FSR, später int8 auf dem STM32N657. Isaac Lab
  läuft in einer eigenen conda-Umgebung — Befehle in `docs/conventions.md` → „Isaac Lab“;
  Experimente, Berichte und Rangliste in `experiments/` (`experiments/leaderboard.md`).

---

## Aktueller Stand

| Teil | v4 | v5 |
|---|---|---|
| USD-Stage mit Action Graph (ROS2 Subscribe/Publish Joint State + Articulation Controller) | ✓ läuft | ✓ läuft |
| ros2_control-Stack (JTC, JointStateBroadcaster, TopicBasedSystem) | ✓ end-to-end verifiziert | ✓ end-to-end verifiziert |
| Pickup-Demo (Dose greifen und heben) | ✓ physikalisch verifiziert | ✓ läuft |
| Putdown-Demo (Dose absetzen und loslassen — Umkehrung der Pickup-Demo) | ✓ | ✓ läuft (2026-10-04 mit Servo-Modell erneut bestanden) |
| Fingerkopplung PIP/DIP/IP folgen dem MCP (PhysX Mimic Joints, ADR-011) | — | ✓ |
| Servo-Aktuatormodell ST3215/ST3095 nach Datenblatt (ADR-012) | — | ✓ |
| Contact Sensors (Fingertip-Kontaktkraft) | nur `index_right` (Einzel-Topic) | ✓ alle 10, gebündelt auf `/pib/fingertip_forces` (ADR-013) |
| Handgelenk über Pleuel, Grenzen [−60°, 0°] (ADR-014) | — | ✓ |
| RL-Greifen in Isaac Lab, linke Hand (ADR-015–020) | — | Proof of Concept, Kraftgriff seitlich: beste Policy 80 % Aufgabenerfolg (EXP-017), Regel-Baseline 71 % (Stand 2026-10-09, `experiments/leaderboard.md`) |

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
  └── Action Graph (Teil der USD-Stage, kein externes Skript), Trigger pro Physikschritt
        ROS2SubscribeJointState → IsaacArticulationController
        Artikulation → ROS2PublishJointState
        (v5) 10 × IsaacReadContactSensor → ConstructArray → ToDouble → ROS2Publisher
             (sensor_msgs/JointState) → /pib/fingertip_forces
  └── PhysX-Physik-Simulation (v5: Mimic Joints für die Fingerkopplung, Servo-Grenzen)
```

### Der Action Graph im Detail

Liegt vollständig in der jeweiligen USD (Window → Graph Editors → Action Graph zum
Ansehen/Bearbeiten), `/Graph/ROS_JointStates`:

1. **`ROS2SubscribeJointState`** — `topicName = /pib/hw/joint_commands`
2. **`IsaacArticulationController`** — `targetPrim` = Artikulations-Root (v5: `root_joint`)
3. **`ROS2PublishJointState`** — `topicName = /pib/hw/joint_states`

Kein Script Node: Die Vorzeichen-Invertierung zwischen Onshape und Isaac ist seit ADR-007
direkt an den Gelenk-Prims korrigiert, `/pib/hw/joint_states` zeigt korrekte Werte. v5
zusätzlich: Trigger `OnPhysicsStep` statt `OnPlaybackTick`, und der Kontaktkraft-Zweig
(ADR-013). Die Fingerkopplung ist keine Graph-Logik, sondern eine PhysX-Zwangsbedingung
(Mimic Joints, gesetzt von `start.py`, ADR-011) — die ROS2-Werte für `distal`/`tip` sind
deshalb wirkungslos, gesteuert wird über `proximal`. Details: `docs/architecture.md`.

`velocityCommand`/`effortCommand` (an `ROS2SubscribeJointState`/`IsaacArticulationController`)
bleiben unverbunden — `controllers.yaml` konfiguriert nur `command_interfaces: [position]`.

---

## ROS2-Schnittstelle

| Topic | Typ | Richtung | Beschreibung |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | ← ros2_control | Ist-Positionen aller 44 DOFs, 50 Hz, rad |
| `/joint_trajectory_controller/follow_joint_trajectory` | Action `control_msgs/FollowJointTrajectory` | → ros2_control | Trajektorie mit Zeitpunkten, MoveIt2-kompatibel |
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad) | Von `topic_based_ros2_control`, gelesen vom Action Graph |
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (rad) | Vom Action Graph publiziert, gelesen von `topic_based_ros2_control` |
| `/pib/fingertip_forces` | `sensor_msgs/JointState` | ← Isaac (v5) | Kontaktkraft aller 10 Fingerspitzen in **N** in `effort`, Fingernamen in `name`, Simulationszeit in `header.stamp`, 60 Hz (Reihenfolge: `docs/conventions.md`) |

---

## Bekannte Fallstricke

| Problem | Lösung |
|---|---|
| `ModuleNotFoundError: rclpy._rclpy_pybind11` | ROS2 Jazzy nutzt Python 3.12, Isaac Sim 3.11. ROS2 **vor** Isaac Sim in derselben Shell sourcen — Isaacs eigene rclpy-Version greift dann automatisch. |
| `controller_manager` wartet ewig auf `/robot_description` | Jazzy-Breaking-Change: ros2_control subscribed Topic statt Parameter. Gelöst durch `robot_state_publisher` in `pib_sim.launch.py`. |
| `Package 'pib_bringup' not found` | `ros2_ws/install/setup.bash` wurde in dieser Shell nicht gesourced — `cd` ändert daran nichts, `AMENT_PREFIX_PATH` fehlt der Eintrag. |
| Hand schließt in falsche Richtung | Nach einem Onshape-Neuimport `isaac_sim/tools/flip_joint_sign.py` erneut ausführen (ADR-007). |
| `/pib/fingertip_forces` leer oder Graph-Änderung nach dem Neu-Öffnen weg | Per Skript gesetzte OmniGraph-Werte stehen nur im laufenden Graph — nach Graph-Skripten speichern **und neu öffnen**, Knoten nicht im Stage-Tree umbenennen (ADR-013, `docs/conventions.md`). |
| v5-Stage stürzt bei Play ab (Backtrace in `isaacsim.sensors.physics.plugin`) | Compound-Subgraph im Action Graph — entfernen, Kraft-Knoten flach neu bauen (ADR-013, Korrektur zu Fallstrick 3). |
| Isaac Lab installiert Pakete in die falsche Python | Immer in `conda activate env_isaaclab` arbeiten, Projekt-`.venv` vorher deaktivieren (ADR-015). |
| Isaac Sim startet aber ROS2 nicht gefunden | ROS2 muss **vor** Isaac Sim gesourced sein: `source /opt/ros/jazzy/setup.bash && ~/isaacsim/isaac-sim.sh` |

---

## Schlüsseldateien

```
config/
  pib_hand_config_v4.py   DOF-Namen, Indizes, ROBOT_PRIM_PATH, Joint-Limits (für start.py)
  pib_hand_config_v5.py   dasselbe für v5

isaac_sim/
  start.py                Session-Setup: Drives, Mimic Joints, Limits, T-Pose (vor Play ausführen)
  setup_stage.py           von start.py genutzt — v5: Servo-Aktuatortabelle, MIMIC_JOINTS
  autostart.py             vollautomatischer Start ohne Script Editor (--exec)
  usd/
    pib_upperbody_v4.usd   Roboter (v4) + Action Graph
    pib_upperbody_v5.usd   Roboter (v5) + Action Graph
    pib_hand_left_v5.usd   Hand + Unterarm (links) für Isaac Lab, Mimic/Limits/Antriebe eingebrannt
  tools/
    dump_pose.py           Nimmt Drive-Targets der aktuell posierten Gelenke als Waypoint
                            auf → isaac_sim/tools/_pose_dump.json (gitignored)
    audit_asset.py         Asset-Inspektion: Massen, Collider, Antriebe, ω_n·Δt/ζ (nur lesend)
    inspect_action_graph.py   Graph-Inventur aus der USD
    build_contact_sensors_v5.py, build_fingertip_force_graph_v5.py   Kontaktsensoren v5
    bake_hand_asset_v5.py  Mimic/Limits/Antriebe/Self-Collision in die Hand-USD einbrennen

pib_hand_left_urdf_v5/     onshape-to-robot-Export der linken Hand (Basis: elbow_lower)
pib_upperbody_urdf_v5/     onshape-to-robot-Export des v5-Oberkörpers (Quelle der DOF-Namen)

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
    pib_bringup/test_client_mimic_v5.py     Mimic-Kopplung ohne Last (nur MCP kommandiert)
    pib_bringup/test_client_mimic_load_v5.py  Finger gegen Tisch, mit Diagnose
  topic_based_ros2_control/   Hardware-Interface-Bridge (Drittanbieter-Paket)

isaac_lab/                 RL-Greifen (conda env_isaaclab, Befehle: docs/conventions.md → „Isaac Lab“)
  pib_hand_left_v5_cfg.py  Isaac-Lab-Asset der linken Hand (Aktuatoren aus config/pib_hand_config_v5.py)
  pib_grasp/               Greifaufgabe (env_cfg, mdp, PPO-Konfiguration), Trainingsvarianten als Task-IDs
  train.py, play.py        Isaac Labs rsl_rl-Skripte mit den pib-Tasks
  experiments.py           Experiment-Framework: new/run/eval/done, Leaderboard, Medien (ADR-016)
  eval_policy.py           Bewertungsprotokoll eval-v1 (auch Regel-Baselines)
  plot_training.py         Trainingsdiagramme für die Berichte
  backup_policies.py       Policies → privates Hugging-Face-Repo
  check_hand_asset.py, scripted_grasp_test.py   Asset-Prüfung, Machbarkeitstest ohne Policy
  tools/                   Diagnose: check_multi.py (Szenenprüfung), reward_diag.py (Belohnungsterme), …

experiments/               Experimente EXP-NNN_<kurzname>/ (Plan, Ergebnisse, Bericht, Diagramme, beste Videos),
                           index.md, leaderboard.md, README.md (Ablauf, Metriken)

scripts/
  start_isaac.sh, start_ros2.sh, launch.sh   Terminal-Automatisierung (v4)

docs/                      architecture, conventions, decisions (ADRs), current-sprint, handoff; archiv/
```

---

## Konventionen

### Winkel
- ros2_control-Stack arbeitet durchgehend in **Radiant**
- Überall dieselbe Konvention (seit ADR-007): 0° = T-Pose/offen, positiv = Flexion/Heben/Vorne
- Am USD-Gelenk-Prim: Drive-Stiffness in Nm/°, Damping in Nm·s/°, Geschwindigkeit in °/s

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
