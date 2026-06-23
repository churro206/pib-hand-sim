# Sprint 2 — Codebase Streamlining & Control-Architektur ✓

## Ergebnis
- [x] P0: `test_hand_poses.py`, `test_tendon.py`, `demo_pickup.py`, `pickup_keyframes.py`, `run_sequence.py` gelöscht
- [x] P1: `isaac_sim/start.py` — Startroutine (configure_physics + drives + limits + initial pose)
- [x] P2: `control/base.py`, `direct.py`, `servo.py`, `nn.py` — ControlMode-Architektur fertig
- [x] P2: `config/sequences.py` — alle Posen migriert (HAND_POSES, TENDON, PICKUP)
- [x] P2: `isaac_sim/runner.py` — Sequenz-Executor mit Smoothstep, hot-reload ohne Isaac-Neustart
- [ ] P3: `isaac_sim/collect_data.py` vs. `data/collect_real.py` — offen (kein Blocker für Sprint 3)

## Offenes vor Sprint 3
- [ ] Commit ausstehender Änderungen (sequences.py, runner.py, control/, start.py, gelöschte Dateien)
- [ ] Pickup-Lift-Step visuell verifizieren: `dof_elbow_right: 55.4` (war Isaac `-55.4`)

## Nicht in diesem Sprint
- ROS2-Bridge (Sprint 3)
- AS5600-Sensoren anbinden (Phase 5)
- LSTM mit echten Daten trainieren (Phase 5)

---

# Sprint 3 — Simulation Server ←

## Ziel
Die Sim wird vom Player zum Server: andere Teams können über ROS2 Befehle
schicken und Feedback empfangen, ohne Isaac-Kenntnisse.

## Tasks

### Observation API
- [x] `get_all_joint_states()` → alle 44 DOFs, in `robot_io.py` + über `/pib/joint_states` publiziert
- [ ] `get_object_pose()` → Objektposition im Weltframe
- [ ] `is_grasping()` → Admittanz-Heuristik via `get_measured_joint_efforts()` (ADR-005)

### Scene API
- [ ] `reset()` → Roboter zu T-Pose, Objekt zurück zur Ausgangsposition
- [ ] `place_object(pose)` → Objekt an beliebige Position setzen

### ROS2-Bridge
- [x] Isaac Sim ROS2-Bridge aktivieren (`isaacsim.ros2.bridge`) — automatisch in `ros2_server.py`
- [x] Topics implementiert und end-to-end verifiziert (Hand bewegt sich, 44 DOFs zurück):
  - Subscribe: `/pib/joint_trajectory` (`trajectory_msgs/JointTrajectory`)
  - Subscribe: `/pib/set_mode` (`std_msgs/String`)
  - Publish: `/pib/joint_states` (`sensor_msgs/JointState`, 30 Hz)
  - Publish: `/pib/grasp_state` (`std_msgs/Bool`, Stub)
- [x] `ROS_DOMAIN_ID=0` als Projektstandard dokumentiert (`docs/conventions.md`)
- [ ] Winkeleinheit mit IK-Team abstimmen (`"deg"` vs. `"rad"` in `server_config.py`)
- [ ] Koordinatenrahmen dokumentieren (pib-Basis als Ursprung)

---

# Sprint 4 — Team-Integration (geplant)

## Ziel
IK-Team und Greifpunkt-Team können direkt mit der Sim arbeiten.
Koordinatenrahmen ist mit allen Teams abgestimmt.

## Voraussetzung (blockiert alles)
- Welcher Koordinatenrahmen? (pib-Basis? Weltframe in Isaac?)
- Welche ROS2-Message-Typen nutzen die anderen Teams?
- Welche ROS2-Distro läuft auf den anderen Systemen?

## Tasks
- [ ] Koordinatenrahmen-Spec schreiben und mit Teams teilen
- [ ] IK-Team-Interface: empfange Gelenkwinkel-Trajektorien, führe aus
- [ ] Greifpunkt-Interface: empfange Greifpunkt im Roboterframe, wähle passenden ControlMode
- [ ] Objekterkennung: hinten angestellt — kommt wenn IK + Greifpunkt sitzen
