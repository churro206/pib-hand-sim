# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-06-23

### Zuletzt gearbeitet an
1. **README Onboarding-Sektion** — neuer Abschnitt „Onboarding für Teamkollegen": Isaac Sim Install-Link, GPU-Anforderung, ROS2 Jazzy, Schritt-für-Schritt-Workflow mit konkreten Menüpfaden
2. **ROS2-vor-Isaac-Gotcha** — prominenter `> Wichtig:`-Block in Schritt 3: `source /opt/ros/jazzy/setup.bash` muss VOR `isaacsim` laufen, sonst findet Isaac `rclpy` nicht
3. **requirements.txt-Klarstellung** — Sektion „LSTM-Training (Phase 5)" macht explizit dass `requirements.txt` + Docker Training-only sind; Isaac Sim bringt Python 3.10 + numpy selbst mit
4. **current-sprint.md** — Onboarding-Task als `[x]` eingetragen unter ROS2-Bridge

### Offene Punkte
- Commit + Push steht aus (Leon macht das)
- `is_grasping()` nicht implementiert — ADR-005: Admittanz-Heuristik via `robot.get_measured_joint_efforts()`, Schwellwert als `GRASP_TORQUE_THRESHOLD` in `server_config.py`
- Scene API (`reset()`, `place_object()`) noch nicht begonnen
- Winkeleinheit `"deg"` vs. `"rad"` in `server_config.py` — muss mit IK-Team abgestimmt werden

### Nächste Schritte (in Reihenfolge)
1. Commit pushen (Leon)
2. `is_grasping()` in `robot_io.py`: `get_measured_joint_efforts(joint_indices=hand_indices)` → Torque-Schwellwert → bool; Schwellwert als `GRASP_TORQUE_THRESHOLD` in `server_config.py`; in `ros2_server.py` verdrahten statt Stub
3. Scene API: `reset()` → T-Pose + Objekt-Reset; `place_object(pose)` → Prim-Transform setzen
4. Winkeleinheit mit IK-Team abstimmen

### Wichtige Kontextdetails
- **ROS_DOMAIN_ID=0** — Projektstandard; Isaac Sim Default=0, Terminal muss explizit gesetzt werden
- **ROS2 muss vor Isaac Sim gesourced sein** — `source /opt/ros/jazzy/setup.bash && isaacsim`; fehlt das, crasht `ros2_server.py` beim Import von `rclpy`
- **requirements.txt ist Training-only** — für die Sim selbst nichts installieren; `ros-jazzy-desktop` deckt alle ROS2-Pakete ab (`rclpy`, `sensor_msgs`, `std_msgs`, `trajectory_msgs`)
- **isaacsim.ros2.bridge** — wird von `ros2_server.py` automatisch aktiviert, kein manuelles Extension-Enabling nötig
- **ros2_server.py stoppen:** nochmal ausführen im Script Editor (setzt Stop-Flag automatisch), beendet sich spätestens 1s danach
- **Headless/Docker für Isaac Sim** — bewusst zurückgestellt; sinnvoll erst wenn Server stabil und standalone (`_launch_helper.py ros2_server`) der primäre Workflow ist (Sprint 4+)
