# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-08-11

### Zuletzt gearbeitet an

**Branch: `feature/ros2-control`** — ros2_control-Integration vollständig implementiert und end-to-end verifiziert.

#### Was heute erledigt wurde

1. **Onshape-URDF integriert:** `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` enthält jetzt den echten Onshape-Export (1353 Zeilen, 18 STL-Meshes in `meshes/`). `check_urdf` grün.

2. **`robot_state_publisher` in launch hinzugefügt:** Jazzy-Breaking-Change — `controller_manager` subscribed `/robot_description` Topic statt Parameter. Gelöst in `pib_sim.launch.py`.

3. **rclpy Python-Mismatch gelöst:** Isaac Sim nutzt Python 3.11, ROS2 Jazzy ist für 3.12 gebaut. `pib_bridge.py` löst das durch Voranstellen von Isaacs eigenem rclpy-Path (`~/isaacsim/exts/isaacsim.ros2.bridge/jazzy/rclpy`).

4. **`test_client.py` auf Pickup-Demo umgestellt:** Ersetzt die Wellbewegung durch die physikalisch verifizierte Dose-Greif-Sequenz (4 Waypoints über 6s, 25 Gelenke).

5. **`pib_bridge.py` Physics-View-Warnings gefixt (4 Iterationen):**
   - Grace-Period: 0,5s nach Play warten bevor `get_joint_positions()` aufgerufen wird
   - Lazy `initialize()`: nur nach Grace-Period, nie beim Laden des Skripts
   - Handle-Reset bei Stop: `sys.modules.pop("_bridge_robot_initialized")` wenn Sim stoppt → Re-Init beim nächsten Play
   - Resultat: Keine „Physics Simulation View is not created yet" Warnings mehr, auch nach Stop/Play-Zyklen

6. **Aufräumen:** `ros2_server.py`, `tools/send_test_trajectory.py`, `isaac_sim/inventory_output.txt` gelöscht.

7. **README komplett überarbeitet** mit vollständiger Onboarding-Anleitung für den ros2_control-Workflow (3-Terminal-Workflow, Fallstricke, Architektur).

#### End-to-End verifiziert

Der komplette Stack läuft: `test_client` → `FollowJointTrajectory` Action → `JointTrajectoryController` → `topic_based_ros2_control` → `/pib/hw/joint_commands` → `pib_bridge.py` → `robot_io` → Isaac PhysX.

Endzustand der Pickup-Demo (physikalisch korrekt):
- `elbow_right`: ~49° (Soll: 55°, DriveAPI-Lag erwartet)
- `thumb_right_rotator`: ~89° (Soll: 90°, reibungsbedingt fast exakt)
- Finger: ~14–34° (Soll: 33°, Kontakt mit Dose begrenzt Flexion)

---

### Offene Punkte

- **Fingertip-Kontaktkräfte implementieren (ADR-005):** `ArticulationView.get_net_contact_forces()` — gleicher Ansatz wie Isaac Lab's `ContactSensor`. Publish auf `/pib/fingertip_forces` (`sensor_msgs/JointState`, `effort` = Newton, 50 Hz). Erstes: `inventory.py` ausführen und Fingertip-Prim-Pfade + Indizes notieren.
- **`get_object_pose()` + Scene API:** `reset()` und `place_object(pose)` noch nicht implementiert.
- **Winkeleinheit mit IK-Team abstimmen:** `config/server_config.py` hat `ANGLE_UNIT = "deg"` als Platzhalter. ros2_control-Stack arbeitet bereits in rad — nur Legacy-Topics betrifft das noch.
- **Koordinatenrahmen dokumentieren:** pib-Basis als Ursprung, Achsenkonvention noch nicht mit Teams abgestimmt.
- **Branch mergen:** `feature/ros2-control` → `main` (Leon entscheidet).

---

### Nächste Schritte

1. `is_grasping()` in `robot_io.py` implementieren (Admittanz-Heuristik, Sprint 3)
2. `get_object_pose()` in `robot_io.py` hinzufügen
3. `reset()` + `place_object()` Scene API (robot_io + ggf. Stage-Zugriff)
4. Branch in `main` mergen wenn stabil

---

### Wichtige Kontextdetails

- **Isaac-Startbefehl:** `~/isaacsim/isaac-sim.sh` (nicht `isaacsim` — kein PATH-Eintrag)
- **ROS2 vor Isaac sourced:** `source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash && export ROS_DOMAIN_ID=0 && ~/isaacsim/isaac-sim.sh`
- **rclpy-Path:** Isaac legt Python 3.11 rclpy unter `~/isaacsim/exts/isaacsim.ros2.bridge/jazzy/rclpy/` ab — `pib_bridge.py` trägt das automatisch ein
- **Grace-Period:** 0,5s nach Play → dann `SingleArticulation.initialize()` → dann Physics-API nutzen
- **DriveAPI-Lag:** Body-Gelenke (Schulter, Ellbogen) antworten langsamer als Handgelenke wegen Spring-Damper. Endzustand nach 6s-Trajektorie ca. 6–10° unter Sollwert — erwartet, kein Bug.
- **Controller-Namespace:** Action auf `/joint_trajectory_controller/follow_joint_trajectory`
- **`pib_bridge.py` hot-reload:** Erneut im Script Editor ausführen stoppt vorherige Instanz und startet neu

---

### Architektur-Überblick (aktueller Stand)

```
[test_client.py / IK-Team]
  └── FollowJointTrajectory Action
        ↓
[ros2_control (externer Prozess)]
  ├── JointTrajectoryController
  ├── JointStateBroadcaster  → /joint_states (rad, 50 Hz)
  └── topic_based_ros2_control/TopicBasedSystem (HW Interface)
        ↕ /pib/hw/joint_states + /pib/hw/joint_commands (rad)
[Isaac Sim — Script Editor]
  └── pib_bridge.py
        ↕ robot_io.py (JOINT_SIGN hier, nirgendwo sonst)
  └── Physik-Simulation (PhysX)
```

#### Limit-Abweichungen: `pib_upperbody_isaac_import.urdf` vs. `setup_stage.py` (Task 2, Stichprobenvergleich)

Alle 44 revoluten Gelenke aus `isaac_sim/urdf/pib_upperbody_isaac_import.urdf` (Task 1,
Onshape→Isaac-transformierte Limits) gegen die bisher hardcodierten Isaac-Limits in
`setup_stage.py` (`_BODY_LIMITS_ISAAC` + Hand-Sonderfall `(-90°, 0°)`) geprüft, Toleranz 0.5°.

**42/44 stimmen überein**, 2 Abweichungen — beide Körpergelenke, deren bisheriger
hardcodierter Wert ein symmetrischer Schätzwert war, während die echte Onshape-Quelle
(verifiziert in `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf`) einseitig ist:

| Gelenk | alt (`_BODY_LIMITS_ISAAC`) | neu (URDF-transformiert) |
|---|---|---|
| `dof_shoulder_horizontal_right` | (-90.0°, 90.0°) | (-90.0°, 0.0°) |
| `dof_upper_arm_left` | (-90.0°, 90.0°) | (-90.0°, 0.0°) |

Beide Abweichungen gegen die Onshape-Quell-URDF gegengeprüft (Onshape-Limits jeweils
`[0°, 90°]`) — Transform korrekt, kein Bug in Task 1. Relevant für Task 6 (Limits im
Action Graph/`setup_stage.py` aktualisieren) und den vollständigen 44-DOF-Sweep in Task 8.
