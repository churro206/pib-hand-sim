# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-08-11

### Zuletzt gearbeitet an

**Branch: `feature/ros2-control`** — ros2_control-Integration vollständig implementiert (alle 6 Tasks):

1. **ros2_ws Workspace** — `topic_based_ros2_control` (PickNik) geklont und gebaut; `.venv`/`catkin_pkg`-Workaround in README dokumentiert
2. **`pib_description` Paket** — URDF-Platzhalter mit vollständigem `<ros2_control>`-Block (alle 44 DOFs, Plugin `topic_based_ros2_control/TopicBasedSystem`)
3. **`pib_bringup` Paket** — `controllers.yaml` (50 Hz, alle 44 DOFs) + `pib_sim.launch.py` (startet Controller Manager + beide Controller)
4. **`isaac_sim/pib_bridge.py`** — ersetzt `ros2_server.py` für den ros2_control-Workflow; publiziert `/pib/hw/joint_states` (50 Hz, rad), subscribed `/pib/hw/joint_commands` (rad)
5. **`pib_bringup/test_client.py`** — Demo-Client: sendet Wellbewegung der rechten Hand als `FollowJointTrajectory`-Goal, zeigt Feedback + Endzustand

### Offene Punkte

- **Onshape-URDF einsetzen (WICHTIG):** `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` ist ein Platzhalter. Onshape-Export (Format: URDF, Geometrie: STL) herunterladen und den `<robot>`-Inhalt in die Datei einfügen — den `<ros2_control>`-Block am Ende erhalten. Danach `check_urdf` muss grün sein.
- **End-to-End-Test:** `ros2 run pib_bringup test_client` mit laufendem Isaac Sim (start.py + pib_bridge.py im Script Editor) verifizieren — Hand soll Wellbewegung ausführen
- **Winkeleinheit mit IK-Team abstimmen:** `server_config.py` hat noch `ANGLE_UNIT = "deg"` — ros2_control-Stack arbeitet in rad (Standard)
- **`main` Branch:** Commit + Push auf `main` ausstehend (Leon entscheidet über Merge)

### Nächste Schritte (in Reihenfolge)

1. Onshape-URDF exportieren → in Platzhalter einsetzen → `check_urdf` prüfen → `colcon build`
2. Isaac Sim starten: `source /opt/ros/jazzy/setup.bash && isaacsim`
3. Script Editor: `start.py` → ▶ Play → `pib_bridge.py` ausführen
4. Terminal: `ros2 launch pib_bringup pib_sim.launch.py`
5. Terminal: `ros2 run pib_bringup test_client` → Hand soll wellen
6. `ros2 control list_controllers` → beide Controller müssen `active` sein

### Wichtige Kontextdetails

- **ros2_control-Stack:** läuft außerhalb Isaac als normaler Linux-Prozess; Isaac ist nur Backend via `/pib/hw/*`-Topics
- **`pib_bridge.py` vs. `ros2_server.py`:** Beide existieren. `pib_bridge.py` ist für ros2_control-Workflow; `ros2_server.py` bleibt für alten Topic-Workflow erhalten
- **ROS2 vor Isaac sourced sein:** `source /opt/ros/jazzy/setup.bash && source ~/repos/pib-hand-sim/ros2_ws/install/setup.bash` vor `isaacsim`
- **catkin_pkg:** Falls `.venv` im Repo-Root → `pip install catkin_pkg` nötig für `colcon build`
- **Controller-Namespace:** `FollowJointTrajectory` Action auf `/joint_trajectory_controller/follow_joint_trajectory`
- **ROS_DOMAIN_ID=0** überall

### Architektur-Überblick (aktueller Stand)

```
[test_client.py / IK-Team]
  └── FollowJointTrajectory Action
        ↓
[ros2_control (außerhalb Isaac)]
  ├── JointTrajectoryController
  ├── JointStateBroadcaster  → /joint_states
  └── topic_based_ros2_control/TopicBasedSystem (HW Interface)
        ↕ /pib/hw/joint_states + /pib/hw/joint_commands
[Isaac Sim]
  └── pib_bridge.py
        ↕ robot_io.py (JOINT_SIGN hier, nicht im Bridge)
  └── Physik-Simulation (PhysX)
```
