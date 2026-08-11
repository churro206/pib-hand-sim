# ros2_control Integration — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isaac Sim als ros2_control-Backend betreiben — Kollegen steuern den pib-Roboter über den `FollowJointTrajectory`-Standard, ohne Isaac Sim zu kennen.

**Architecture:** `pib_bridge.py` läuft inside Isaac Sim als dünner Topic-Bridge (liest/schreibt `robot_io`). `topic_based_ros2_control` stellt die Hardware-Interface-Verbindung über Topics her. Darüber laufen Standard-ros2_control-Controller (`JointTrajectoryController`, `JointStateBroadcaster`) als normaler Linux-Prozess außerhalb von Isaac.

**Tech Stack:** ROS2 Jazzy, ros2_control, topic_based_ros2_control (PickNik), sensor_msgs/JointState, control_msgs/FollowJointTrajectory, Python 3.10, Isaac Sim 5.1

---

## Global Constraints

- ROS_DOMAIN_ID=0 überall
- Winkel intern in Grad; über ROS2 in Radiant (ros2_control-Standard)
- JOINT_SIGN=-1 bleibt ausschließlich in `robot_io.py` — pib_bridge.py nur rad↔deg
- Onshape-Konvention: positiv = Flexion/Heben/Vorne
- Branch: `feature/ros2-control`
- Kein Testframework — Verifikation über `ros2 topic echo` / `ros2 control list_controllers`
- Workspace-Pfad: `ros2_ws/` im Repo-Root (neben `isaac_sim/`, `config/` etc.)
- Keine Änderungen an `robot_io.py`, `setup_stage.py`, `start.py`

---

## Dateistruktur

```
ros2_ws/                                   NEU — ROS2-Workspace
└── src/
    ├── pib_description/                   NEU — URDF + ros2_control-Tags
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   └── urdf/
    │       └── pib_upperbody.urdf         Onshape-Export + <ros2_control>-Block
    │
    ├── pib_bringup/                       NEU — Launch + Config + Test-Client
    │   ├── package.xml
    │   ├── CMakeLists.txt
    │   ├── config/
    │   │   └── controllers.yaml           Controller-Konfiguration (44 DOFs)
    │   ├── launch/
    │   │   └── pib_sim.launch.py          Startet alles mit einem Befehl
    │   └── pib_bringup/
    │       ├── __init__.py
    │       └── test_client.py             FollowJointTrajectory Demo-Client
    │
    └── topic_based_ros2_control/          EXTERN — via git clone (PickNik)

isaac_sim/pib_bridge.py                    NEU — ersetzt ros2_server.py in Isaac
isaac_sim/ros2_server.py                   BLEIBT — vorerst nicht gelöscht
docs/architecture.md                       UPDATE — ros2_control-Layer ergänzt
docs/current-sprint.md                     UPDATE — Sprint-Status
```

---

## Task 1: Workspace-Setup + topic_based_ros2_control

**Files:**
- Create: `ros2_ws/src/` (Verzeichnis)
- Clone: `ros2_ws/src/topic_based_ros2_control/`

**Interfaces:**
- Produces: `ros-jazzy-topic-based-ros2-control` verfügbar, `colcon` findet es

- [ ] **Schritt 1: Abhängigkeiten installieren**

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-ros2-control \
  ros-jazzy-ros2-controllers \
  ros-jazzy-joint-state-broadcaster \
  ros-jazzy-joint-trajectory-controller \
  python3-colcon-common-extensions
```

- [ ] **Schritt 2: topic_based_ros2_control klonen**

```bash
cd ~/repos/pib-hand-sim/ros2_ws/src
git clone https://github.com/PickNikRobotics/topic_based_ros2_control.git -b main
```

- [ ] **Schritt 3: Workspace-Gerüst anlegen**

```bash
mkdir -p ~/repos/pib-hand-sim/ros2_ws/src
cd ~/repos/pib-hand-sim/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select topic_based_ros2_control
```

Erwartetes Ergebnis: `Summary: 1 packages finished`

- [ ] **Schritt 4: Verifizieren**

```bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
ros2 pkg list | grep topic_based
```

Erwartetes Ergebnis: `topic_based_ros2_control` in der Ausgabe

- [ ] **Schritt 5: Commit**

```bash
cd ~/repos/pib-hand-sim
git add ros2_ws/src/topic_based_ros2_control
git commit -m "chore: add topic_based_ros2_control as subworkspace source"
```

---

## Task 2: pib_description — URDF mit ros2_control-Tags

**Files:**
- Create: `ros2_ws/src/pib_description/package.xml`
- Create: `ros2_ws/src/pib_description/CMakeLists.txt`
- Create: `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf`

**Interfaces:**
- Consumes: Onshape-URDF-Export (manuell platzieren)
- Produces: `robot_description` Parameter mit eingebetteten ros2_control-Tags; alle 44 Gelenknamen für controllers.yaml

- [ ] **Schritt 1: Package-Dateien anlegen**

```bash
mkdir -p ~/repos/pib-hand-sim/ros2_ws/src/pib_description/urdf
```

`ros2_ws/src/pib_description/package.xml`:
```xml
<?xml version="1.0"?>
<package format="3">
  <name>pib_description</name>
  <version>0.1.0</version>
  <description>pib Roboter URDF mit ros2_control Hardware-Interface</description>
  <maintainer email="leonkrampf206@gmail.com">Leon</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <exec_depend>urdf</exec_depend>
  <exec_depend>xacro</exec_depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

`ros2_ws/src/pib_description/CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.8)
project(pib_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
```

- [ ] **Schritt 2: Onshape-URDF exportieren und platzieren**

In Onshape: Exportieren → Format: URDF → Geometrie: STL → Herunterladen

Die heruntergeladene Datei (enthält URDF + STL-Ordner) entpacken.
Die `.urdf`-Datei nach `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` kopieren.
STL-Dateien nach `ros2_ws/src/pib_description/urdf/meshes/` kopieren (falls vorhanden).

- [ ] **Schritt 3: `<ros2_control>`-Block in URDF einfügen**

Am Ende der URDF-Datei direkt vor `</robot>` einfügen:

```xml
  <!-- ═══════════════════════════════════════════════════════════════
       ros2_control Hardware Interface
       topic_based_ros2_control liest /pib/hw/joint_states von Isaac
       und schreibt /pib/hw/joint_commands nach Isaac.
       Winkel in Radiant (ros2_control-Standard).
  ══════════════════════════════════════════════════════════════════ -->
  <ros2_control name="pib_hw" type="system">
    <hardware>
      <plugin>topic_based_ros2_control/TopicBasedSystem</plugin>
      <param name="joint_commands_topic">/pib/hw/joint_commands</param>
      <param name="joint_states_topic">/pib/hw/joint_states</param>
    </hardware>

    <!-- Körper (14 DOFs) -->
    <joint name="dof_head_horizontal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_head_vertical">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_shoulder_vertical_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_shoulder_horizontal_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_upper_arm_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_elbow_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_forearm_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_wrist_left">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_shoulder_vertical_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_shoulder_horizontal_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_upper_arm_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_elbow_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_forearm_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_wrist_right">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>

    <!-- Linke Hand (15 DOFs) -->
    <joint name="dof_thumb_left_rotator">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_thumb_left_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_thumb_left_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_left_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_left_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_left_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_left_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_left_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_left_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_left_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_left_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_left_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_left_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_left_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_left_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>

    <!-- Rechte Hand (15 DOFs) -->
    <joint name="dof_thumb_right_rotator">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_thumb_right_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_thumb_right_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_right_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_right_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_index_right_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_right_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_right_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_middle_right_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_right_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_right_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_ring_right_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_right_proximal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_right_distal">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>
    <joint name="dof_pinky_right_tip">
      <command_interface name="position"/>
      <state_interface name="position"/>
    </joint>

  </ros2_control>
```

- [ ] **Schritt 4: Paket bauen und URDF validieren**

```bash
cd ~/repos/pib-hand-sim/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select pib_description
source install/setup.bash
check_urdf $(ros2 pkg prefix pib_description)/share/pib_description/urdf/pib_upperbody.urdf
```

Erwartetes Ergebnis: `robot name is: pib_upperbody_URDF` (oder ähnlich), kein Fehler

- [ ] **Schritt 5: Commit**

```bash
cd ~/repos/pib-hand-sim
git add ros2_ws/src/pib_description
git commit -m "feat(pib_description): URDF mit ros2_control-Tags für alle 44 DOFs"
```

---

## Task 3: pib_bringup — Controller-Config + Launch

**Files:**
- Create: `ros2_ws/src/pib_bringup/package.xml`
- Create: `ros2_ws/src/pib_bringup/CMakeLists.txt`
- Create: `ros2_ws/src/pib_bringup/config/controllers.yaml`
- Create: `ros2_ws/src/pib_bringup/launch/pib_sim.launch.py`

**Interfaces:**
- Consumes: `pib_description` (robot_description Parameter), alle 44 DOF-Namen aus Task 2
- Produces: `ros2 launch pib_bringup pib_sim.launch.py` startet Controller Manager + Controller

- [ ] **Schritt 1: Package-Dateien anlegen**

```bash
mkdir -p ~/repos/pib-hand-sim/ros2_ws/src/pib_bringup/{config,launch,pib_bringup}
touch ~/repos/pib-hand-sim/ros2_ws/src/pib_bringup/pib_bringup/__init__.py
```

`ros2_ws/src/pib_bringup/package.xml`:
```xml
<?xml version="1.0"?>
<package format="3">
  <name>pib_bringup</name>
  <version>0.1.0</version>
  <description>pib Simulation — Start-Launch und Test-Client</description>
  <maintainer email="leonkrampf206@gmail.com">Leon</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake_python</buildtool_depend>
  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>rclpy</depend>
  <depend>pib_description</depend>
  <depend>ros2_control</depend>
  <depend>ros2_controllers</depend>
  <depend>joint_state_broadcaster</depend>
  <depend>joint_trajectory_controller</depend>
  <depend>control_msgs</depend>
  <depend>sensor_msgs</depend>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

`ros2_ws/src/pib_bringup/CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.8)
project(pib_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(pib_bringup)

install(DIRECTORY config launch
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  pib_bringup/test_client.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
```

- [ ] **Schritt 2: controllers.yaml schreiben**

`ros2_ws/src/pib_bringup/config/controllers.yaml`:
```yaml
controller_manager:
  ros__parameters:
    update_rate: 50  # Hz — Isaac Sim läuft bei 60 Hz, wir bleiben darunter

    joint_state_broadcaster:
      type: joint_state_broadcaster/JointStateBroadcaster

    joint_trajectory_controller:
      type: joint_trajectory_controller/JointTrajectoryController

joint_trajectory_controller:
  ros__parameters:
    joints:
      # Körper
      - dof_head_horizontal
      - dof_head_vertical
      - dof_shoulder_vertical_left
      - dof_shoulder_horizontal_left
      - dof_upper_arm_left
      - dof_elbow_left
      - dof_forearm_left
      - dof_wrist_left
      - dof_shoulder_vertical_right
      - dof_shoulder_horizontal_right
      - dof_upper_arm_right
      - dof_elbow_right
      - dof_forearm_right
      - dof_wrist_right
      # Linke Hand
      - dof_thumb_left_rotator
      - dof_thumb_left_proximal
      - dof_thumb_left_distal
      - dof_index_left_proximal
      - dof_index_left_distal
      - dof_index_left_tip
      - dof_middle_left_proximal
      - dof_middle_left_distal
      - dof_middle_left_tip
      - dof_ring_left_proximal
      - dof_ring_left_distal
      - dof_ring_left_tip
      - dof_pinky_left_proximal
      - dof_pinky_left_distal
      - dof_pinky_left_tip
      # Rechte Hand
      - dof_thumb_right_rotator
      - dof_thumb_right_proximal
      - dof_thumb_right_distal
      - dof_index_right_proximal
      - dof_index_right_distal
      - dof_index_right_tip
      - dof_middle_right_proximal
      - dof_middle_right_distal
      - dof_middle_right_tip
      - dof_ring_right_proximal
      - dof_ring_right_distal
      - dof_ring_right_tip
      - dof_pinky_right_proximal
      - dof_pinky_right_distal
      - dof_pinky_right_tip

    command_interfaces:
      - position
    state_interfaces:
      - position

    # Trajektorie interpolieren (ros2_control übernimmt Smoothing)
    allow_partial_joints_goal: true
    open_loop_control: false
    allow_integration_in_goal_trajectories: false
```

- [ ] **Schritt 3: Launch-Datei schreiben**

`ros2_ws/src/pib_bringup/launch/pib_sim.launch.py`:
```python
"""
pib_sim.launch.py — Startet den kompletten ros2_control-Stack für Isaac Sim.

Voraussetzung: Isaac Sim läuft mit start.py + pib_bridge.py (Script Editor).

Start:
  source /opt/ros/jazzy/setup.bash
  source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
  ros2 launch pib_bringup pib_sim.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


def generate_launch_description():
    # URDF einlesen
    urdf_path = os.path.join(
        get_package_share_directory("pib_description"),
        "urdf", "pib_upperbody.urdf"
    )
    with open(urdf_path, "r") as f:
        robot_description = f.read()

    # Controller-Konfiguration
    controllers_yaml = os.path.join(
        get_package_share_directory("pib_bringup"),
        "config", "controllers.yaml"
    )

    # Controller Manager
    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            {"robot_description": robot_description},
            controllers_yaml,
        ],
        output="screen",
    )

    # JointStateBroadcaster spawnen
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )

    # JointTrajectoryController spawnen — erst nach JointStateBroadcaster
    joint_trajectory_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_trajectory_controller"],
    )

    delay_jtc = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[joint_trajectory_controller_spawner],
        )
    )

    return LaunchDescription([
        controller_manager,
        joint_state_broadcaster_spawner,
        delay_jtc,
    ])
```

- [ ] **Schritt 4: Paket bauen**

```bash
cd ~/repos/pib-hand-sim/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select pib_bringup
```

Erwartetes Ergebnis: `Summary: 1 packages finished`

- [ ] **Schritt 5: Struktur verifizieren (ohne Isaac)**

```bash
source install/setup.bash
ros2 launch pib_bringup pib_sim.launch.py
# → Controller Manager startet, dann Fehler da Isaac nicht läuft — das ist ok
# Wichtig: kein Import-Fehler, kein URDF-Parse-Fehler
```

Strg+C abbrechen. Erwartetes Ergebnis: Keine Python- oder XML-Fehler.

- [ ] **Schritt 6: Commit**

```bash
cd ~/repos/pib-hand-sim
git add ros2_ws/src/pib_bringup
git commit -m "feat(pib_bringup): Controller-Config + Launch-Datei für 44 DOFs"
```

---

## Task 4: pib_bridge.py — Isaac-interner Topic-Bridge

**Files:**
- Create: `isaac_sim/pib_bridge.py`

**Interfaces:**
- Consumes: `robot_io.get_all_joint_states()` → `{dof_name: angle_deg}`, `robot_io.set_all_targets()` ← `{dof_name: angle_deg}`
- Produces:
  - Publiziert `/pib/hw/joint_states` (`sensor_msgs/JointState`, Radiant, 50 Hz)
  - Subscribed `/pib/hw/joint_commands` (`sensor_msgs/JointState`, Radiant)

**Winkel-Konvention in diesem File:**
- `robot_io` arbeitet in Grad (Onshape-Konvention)
- ROS2 / ros2_control arbeitet in Radiant
- Konvertierung: `rad = deg * π/180` und `deg = rad * 180/π`
- JOINT_SIGN wird **nicht** hier angewendet — das macht robot_io intern

- [ ] **Schritt 1: pib_bridge.py schreiben**

`isaac_sim/pib_bridge.py`:
```python
"""
isaac_sim/pib_bridge.py — Dünner ROS2-Bridge zwischen Isaac Sim und ros2_control.

Ersetzt ros2_server.py für den ros2_control-Workflow.

Workflow Script Editor:
  start.py → Play → pib_bridge.py ausführen
  Erneut ausführen: stoppt vorherige Instanz, startet neu.

Topics:
  Publish:   /pib/hw/joint_states   (sensor_msgs/JointState, rad, 50 Hz)
             → topic_based_ros2_control liest davon
  Subscribe: /pib/hw/joint_commands (sensor_msgs/JointState, rad)
             ← topic_based_ros2_control schreibt dorthin

Winkel: robot_io arbeitet in Grad; Bridge konvertiert ↔ Radiant.
JOINT_SIGN bleibt in robot_io — hier keine Vorzeichen-Logik.
"""
import sys
import os
import importlib
import importlib.util
import asyncio
import math
import time

# ── Umgebungs-Erkennung ───────────────────────────────────────────────────────
_lh = sys.modules.get("_launch_helper")
_STANDALONE = _lh is not None

try:
    import carb as _carb  # type: ignore
    _log = _carb.log_warn
except ImportError:
    _log = print


def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    if _STANDALONE:
        from pathlib import Path
        return str(Path(__file__).parent.parent)
    try:
        import omni.usd  # type: ignore
        from pathlib import Path
        f = Path(omni.usd.get_context().get_stage().GetRootLayer().realPath)
        for ancestor in [f.parent, f.parent.parent]:
            if (ancestor / "config" / "pib_hand_config.py").is_file():
                return str(ancestor)
    except Exception:
        pass
    for candidate in ["~/repos/pib-hand-sim", "~/pib-hand-sim"]:
        p = os.path.expanduser(candidate)
        if os.path.isfile(os.path.join(p, "config", "pib_hand_config.py")):
            return p
    raise FileNotFoundError("Projekt nicht gefunden. PIB_HAND_SIM_ROOT setzen.")


_root = _find_root()
if _root not in sys.path:
    sys.path.insert(0, _root)


def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


# ── robot_io laden ────────────────────────────────────────────────────────────
if _STANDALONE:
    import robot_io as _io  # type: ignore
else:
    _io = _load_mod("robot_io", os.path.join(_root, "isaac_sim", "robot_io.py"))
    if not sys.modules.get("_bridge_robot_initialized"):
        try:
            from isaacsim.core.prims import SingleArticulation as _ArtCls  # type: ignore
        except ImportError:
            from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore
        _robot = _ArtCls(prim_path=_io.ROBOT_PRIM_PATH)
        _robot.initialize()
        sys.modules["_bridge_robot_initialized"] = _robot
    _io._set_robot(sys.modules["_bridge_robot_initialized"])

# ── ROS2-Bridge aktivieren ────────────────────────────────────────────────────
try:
    import omni.kit.app as _omni_app  # type: ignore
    _ext = _omni_app.get_app().get_extension_manager()
    if not _ext.is_extension_enabled("isaacsim.ros2.bridge"):
        _ext.set_extension_enabled_immediate("isaacsim.ros2.bridge", True)
        _log("[pib_bridge] ROS2-Bridge aktiviert.")
except Exception as _e:
    _log(f"[pib_bridge] ROS2-Bridge-Aktivierung fehlgeschlagen: {_e}")

import rclpy  # type: ignore
from rclpy.node import Node  # type: ignore
from sensor_msgs.msg import JointState  # type: ignore

# ── Stop-Flag: erneutes Ausführen stoppt vorherige Instanz ───────────────────
_FLAG = "_pib_bridge_active"
if sys.modules.get(_FLAG):
    sys.modules[_FLAG]["stop"] = True
_stop = {"stop": False}
sys.modules[_FLAG] = _stop

# ── Publish-Rate ──────────────────────────────────────────────────────────────
_PUBLISH_HZ = 50.0
_PUBLISH_INTERVAL = 1.0 / _PUBLISH_HZ

# ── Letzter empfangener Befehl ────────────────────────────────────────────────
_pending_command: dict | None = None  # {dof_name: angle_deg}


async def _run_bridge() -> None:
    global _pending_command

    if not rclpy.ok():
        rclpy.init()

    node = Node("pib_bridge")

    def _on_joint_commands(msg: JointState) -> None:
        """Empfängt Positionsbefehle von ros2_control (in Radiant)."""
        global _pending_command
        if not msg.name or not msg.position:
            return
        # Radiant → Grad (Onshape-Konvention)
        _pending_command = {
            name: math.degrees(pos)
            for name, pos in zip(msg.name, msg.position)
        }

    node.create_subscription(
        JointState,
        "/pib/hw/joint_commands",
        _on_joint_commands,
        10,
    )

    pub_states = node.create_publisher(JointState, "/pib/hw/joint_states", 10)

    _log("[pib_bridge] Bereit.")
    _log("[pib_bridge]   pub: /pib/hw/joint_states (50 Hz, rad)")
    _log("[pib_bridge]   sub: /pib/hw/joint_commands (rad)")

    import omni.kit.app as _app_module  # type: ignore
    app = _app_module.get_app()

    _last_pub = 0.0

    while not _stop["stop"]:
        rclpy.spin_once(node, timeout_sec=0)

        # Befehl ausführen wenn vorhanden
        if _pending_command is not None:
            _io.set_all_targets(_pending_command)
            _pending_command = None

        # Joint-States publishen (Grad → Radiant)
        now = time.monotonic()
        if now - _last_pub >= _PUBLISH_INTERVAL:
            try:
                state_deg = _io.get_all_joint_states()
                msg = JointState()
                msg.header.stamp = node.get_clock().now().to_msg()
                msg.name = list(state_deg.keys())
                msg.position = [math.radians(v) for v in state_deg.values()]
                pub_states.publish(msg)
            except Exception as e:
                _log(f"[pib_bridge] publish fehlgeschlagen: {e}")
            _last_pub = now

        try:
            await asyncio.wait_for(app.next_update_async(), timeout=1.0)
        except asyncio.TimeoutError:
            pass

    _log("[pib_bridge] Gestoppt.")
    node.destroy_node()


# ── Einstieg ──────────────────────────────────────────────────────────────────
if not _STANDALONE:
    asyncio.ensure_future(_run_bridge())
```

- [ ] **Schritt 2: Verifizieren (nur Syntax, ohne Isaac)**

```bash
python3 -c "import ast; ast.parse(open('isaac_sim/pib_bridge.py').read()); print('Syntax OK')"
```

Erwartetes Ergebnis: `Syntax OK`

- [ ] **Schritt 3: Commit**

```bash
git add isaac_sim/pib_bridge.py
git commit -m "feat(isaac): pib_bridge.py — dünner ros2_control Topic-Bridge"
```

---

## Task 5: Test-Client + End-to-End-Verifikation

**Files:**
- Create: `ros2_ws/src/pib_bringup/pib_bringup/test_client.py`

**Interfaces:**
- Consumes: `FollowJointTrajectory` Action auf `/joint_trajectory_controller/follow_joint_trajectory`
- Produces: Wellbewegung der rechten Hand in Isaac Sim, Ausgabe der empfangenen joint_states

- [ ] **Schritt 1: Test-Client schreiben**

`ros2_ws/src/pib_bringup/pib_bringup/test_client.py`:
```python
#!/usr/bin/env python3
"""
test_client.py — Demo-Client für pib ros2_control-Stack.

Sendet eine Wellbewegung der rechten Hand als FollowJointTrajectory-Goal.
Gibt Feedback und Result aus. Empfängt joint_states und zeigt Endzustand.

Voraussetzung:
  1. Isaac Sim läuft (start.py + pib_bridge.py im Script Editor)
  2. ros2 launch pib_bringup pib_sim.launch.py

Start:
  ros2 run pib_bringup test_client
"""
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState


# Rechte Hand: Zeige-, Mittel-, Ring- und Kleinfinger wellen
WAVE_JOINTS = [
    "dof_index_right_proximal",
    "dof_index_right_distal",
    "dof_index_right_tip",
    "dof_middle_right_proximal",
    "dof_middle_right_distal",
    "dof_middle_right_tip",
    "dof_ring_right_proximal",
    "dof_ring_right_distal",
    "dof_ring_right_tip",
    "dof_pinky_right_proximal",
    "dof_pinky_right_distal",
    "dof_pinky_right_tip",
]

def _deg(d: float) -> float:
    """Grad → Radiant (ros2_control-Konvention)."""
    return math.radians(d)


def _make_wave_trajectory():
    """Erzeugt 4-Punkt-Wellbewegung: offen → geschlossen → offen → geschlossen."""
    n = len(WAVE_JOINTS)
    points = []

    # Punkt 0 — Startposition (offen, 0°), sofort
    points.append(JointTrajectoryPoint(
        positions=[_deg(0.0)] * n,
        time_from_start=Duration(sec=0, nanosec=0),
    ))
    # Punkt 1 — Geschlossen (90°) nach 1.0s
    points.append(JointTrajectoryPoint(
        positions=[_deg(90.0)] * n,
        time_from_start=Duration(sec=1, nanosec=0),
    ))
    # Punkt 2 — Offen nach 2.0s
    points.append(JointTrajectoryPoint(
        positions=[_deg(0.0)] * n,
        time_from_start=Duration(sec=2, nanosec=0),
    ))
    # Punkt 3 — Geschlossen nach 3.0s (Endpose)
    points.append(JointTrajectoryPoint(
        positions=[_deg(45.0)] * n,
        time_from_start=Duration(sec=3, nanosec=0),
    ))

    return points


class PibTestClient(Node):

    def __init__(self):
        super().__init__("pib_test_client")
        self._action_client = ActionClient(
            self,
            FollowJointTrajectory,
            "/joint_trajectory_controller/follow_joint_trajectory",
        )
        self._joint_states_sub = self.create_subscription(
            JointState,
            "/joint_states",
            self._on_joint_states,
            10,
        )
        self._last_joint_states = None
        self._done = False

    def _on_joint_states(self, msg: JointState):
        self._last_joint_states = msg

    def send_wave(self):
        self.get_logger().info("Warte auf Action-Server...")
        self._action_client.wait_for_server()
        self.get_logger().info("Action-Server bereit. Sende Wellbewegung.")

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = WAVE_JOINTS
        goal.trajectory.points = _make_wave_trajectory()

        future = self._action_client.send_goal_async(
            goal,
            feedback_callback=self._on_feedback,
        )
        future.add_done_callback(self._on_goal_response)

    def _on_goal_response(self, future):
        handle = future.result()
        if not handle.accepted:
            self.get_logger().error("Goal abgelehnt!")
            self._done = True
            return
        self.get_logger().info("Goal akzeptiert — Ausführung läuft...")
        result_future = handle.get_result_async()
        result_future.add_done_callback(self._on_result)

    def _on_feedback(self, feedback_msg):
        fb = feedback_msg.feedback
        # Zeige aktuellen Zeigefinger-Winkel als Fortschrittsindikator
        if fb.actual.positions:
            deg = math.degrees(fb.actual.positions[0])
            self.get_logger().info(f"  Fortschritt — index_proximal: {deg:.1f}°")

    def _on_result(self, future):
        result = future.result().result
        self.get_logger().info(f"Fertig! Error-Code: {result.error_code}")

        # Joint-States ausgeben
        if self._last_joint_states:
            self.get_logger().info("Aktueller Roboterzustand (Auswahl rechte Hand):")
            for name, pos in zip(
                self._last_joint_states.name,
                self._last_joint_states.position,
            ):
                if "right" in name:
                    self.get_logger().info(f"  {name}: {math.degrees(pos):.1f}°")

        self._done = True


def main(args=None):
    rclpy.init(args=args)
    client = PibTestClient()
    client.send_wave()

    while rclpy.ok() and not client._done:
        rclpy.spin_once(client, timeout_sec=0.1)

    client.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Schritt 2: Paket neu bauen**

```bash
cd ~/repos/pib-hand-sim/ros2_ws
colcon build --packages-select pib_bringup
source install/setup.bash
```

- [ ] **Schritt 3: End-to-End-Test**

Terminal 1 — Isaac Sim:
```
start.py ausführen → ▶ Play → pib_bridge.py ausführen
```

Terminal 2:
```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
ros2 launch pib_bringup pib_sim.launch.py
```

Erwartete Ausgabe: `Spawning joint_state_broadcaster` + `Spawning joint_trajectory_controller`

```bash
ros2 control list_controllers
```
Erwartetes Ergebnis:
```
joint_state_broadcaster[joint_state_broadcaster/JointStateBroadcaster] active
joint_trajectory_controller[joint_trajectory_controller/JointTrajectoryController] active
```

Terminal 3:
```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
ros2 run pib_bringup test_client
```

Erwartetes Ergebnis in Isaac Sim: rechte Hand macht Wellbewegung (offen → zu → offen → halb)
Erwartete Ausgabe im Terminal: Fortschritts-Logs + Endzustand der rechten Hand-DOFs

- [ ] **Schritt 4: joint_states verifizieren**

```bash
ros2 topic echo /joint_states --once
```

Erwartetes Ergebnis: 44 DOF-Namen mit Positionen in Radiant

- [ ] **Schritt 5: Commit**

```bash
cd ~/repos/pib-hand-sim
git add ros2_ws/src/pib_bringup/pib_bringup/test_client.py
git commit -m "feat(pib_bringup): Test-Client mit Wellbewegung (FollowJointTrajectory)"
```

---

## Task 6: Dokumentation aktualisieren

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/current-sprint.md`
- Modify: `docs/handoff.md`

- [ ] **Schritt 1: architecture.md — ros2_control-Layer ergänzen**

In `docs/architecture.md` den Abschnitt `## 4-Schichten-Modell` ersetzen:

```markdown
## 4-Schichten-Modell (Ziel)

```
Layer 5: Team-Integration          Sprint 4
         ROS2-Protokoll, Koordinatenrahmen, IK-Interface

Layer 4: ros2_control-Stack        Sprint 3b (feature/ros2-control) ←
         JointTrajectoryController, JointStateBroadcaster
         FollowJointTrajectory-Action (MoveIt2-kompatibel)
         topic_based_ros2_control als Hardware-Interface

Layer 3: Simulation Server         Sprint 3 (teilweise fertig)
         pib_bridge.py (ersetzt ros2_server.py)
         /pib/hw/joint_states + /pib/hw/joint_commands

Layer 2: Control-Architektur       fertig
         ControlMode ABC (direct | servo | nn), sequences, runner

Layer 1: Isaac IO-Schicht          fertig
         robot_io, setup_stage, Physik-Simulation
```
```

- [ ] **Schritt 2: current-sprint.md — Sprint ergänzen**

Unter `# Sprint 3` den Eintrag ergänzen:

```markdown
### ros2_control-Integration (feature/ros2-control)
- [x] pib_bridge.py — dünner Isaac-Bridge (ersetzt ros2_server.py)
- [x] pib_description — URDF + ros2_control-Tags (44 DOFs)
- [x] pib_bringup — Launch + Controller-Config + Test-Client
- [ ] End-to-End-Test mit Isaac Sim
- [ ] ForceTorqueSensorBroadcaster für Kontaktkräfte (Phase 2 dieser Branch)
```

- [ ] **Schritt 3: Alles committen**

```bash
cd ~/repos/pib-hand-sim
git add docs/architecture.md docs/current-sprint.md
git commit -m "docs: ros2_control-Layer in Architektur + Sprint dokumentiert"
```

---

## Bekannte Fallstricke

**topic_based_ros2_control Branch:** Beim Klonen auf kompatiblen Branch achten. Falls `main` nicht mit Jazzy kompatibel: `git checkout jazzy` versuchen.

**ROS2 vor Isaac sourced sein:** `source /opt/ros/jazzy/setup.bash` muss VOR `isaacsim` laufen — sonst findet Isaac kein `rclpy`. Reihenfolge:
```bash
source /opt/ros/jazzy/setup.bash
source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash
isaacsim
```

**Controller startet nicht:** Wenn `joint_trajectory_controller` nicht auf `active` wechselt, `ros2 control list_hardware_interfaces` prüfen — alle 44 DOFs müssen als `available` erscheinen. Fehlt ein DOF-Name, stimmt der Name in URDF nicht mit pib_hand_config.py überein.

**Winkel-Sanity-Check:** `ros2 topic echo /pib/hw/joint_states` → alle Werte sollten nahe 0.0 rad sein (T-Pose). Große Werte deuten auf Vorzeichen-Problem hin — dann in pib_bridge.py prüfen ob math.radians korrekt aufgerufen wird.
