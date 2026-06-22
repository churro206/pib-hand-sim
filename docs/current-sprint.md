# Sprint 2 — Codebase Streamlining & Control-Architektur

## Ziel
Parallele Strukturen bereinigen, einheitliche Control-Architektur einführen,
Startroutine implementieren. Phase-1-Demo (Dose greifen) ist abgeschlossen.

## Tasks (Priorität)

### P0 — Commit & Cleanup
- [ ] Commit der funktionierenden Demo: `pickup_keyframes.py`, `build_scene.py`, `demo_pickup.py`, `setup_stage.py`
- [ ] `poses_pickup.py` entfernen (durch `pickup_keyframes.py` ersetzt)
- [ ] `isaac_sim/_deprecated/` entfernen (`fix_joints.py`, `unfix_joints.py` — durch `setup_stage.set_joint_limits()` ersetzt)

### P1 — Startroutine
- [ ] `isaac_sim/start.py` schreiben: bündelt `configure_physics_scene`, `configure_drives`, `set_joint_limits`, `set_initial_pose`
- [ ] Sowohl Script Editor als auch `_launch_helper` nutzen dieses Modul
- [ ] `_launch_helper.py` refactoren um `start.py` zu verwenden

### P2 — Control-Architektur
- [ ] `control/base.py`: `ControlMode` ABC mit `to_joint_targets(command) -> dict`
- [ ] `control/direct.py`: Klasse `DirectMode(ControlMode)` — pass-through
- [ ] `control/servo.py`: Klasse `ServoMode(ControlMode)` — Sehnen-Mapping, Interface anpassen
- [ ] `control/nn.py`: `NNMode` Stub (Phase 5)
- [ ] Demo-Skript das Control-Mode als Argument nimmt

### P3 — Datenpipeline klären
- [ ] `isaac_sim/collect_data.py` vs. `data/collect_real.py` — Zuständigkeiten trennen und dokumentieren

## Nicht in diesem Sprint
- ROS2-Bridge (Sprint 3)
- AS5600-Sensoren anbinden (Phase 5)
- LSTM mit echten Daten trainieren (Phase 5)

---

# Sprint 3 — Simulation Server (geplant)

## Ziel
Die Sim wird vom Player zum Server: andere Teams können über ROS2 Befehle
schicken und Feedback empfangen, ohne Isaac-Kenntnisse.

## Tasks

### Observation API
- [ ] `get_robot_state()` → Gelenkpositionen aller 44 DOFs + Endeffektorpose (FK)
- [ ] `get_object_pose()` → Objektposition im Weltframe (Isaac kann das, noch nicht verdrahtet)
- [ ] Kontaktdetection: `is_grasping()` via PhysX Contact Reports

### Scene API
- [ ] `reset()` → Roboter zu T-Pose, Objekt zurück zur Ausgangsposition
- [ ] `place_object(pose)` → Objekt an beliebige Position setzen

### ROS2-Bridge
- [ ] Isaac Sim ROS2-Bridge aktivieren (`isaacsim.ros2.bridge`)
- [ ] Topics definieren (mit anderen Teams abstimmen):
  - Subscribe: `/pib/joint_command` ({dof_name: angle_deg})
  - Publish: `/pib/joint_states`, `/pib/grasp_state`
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
