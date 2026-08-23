# pib-Hand-Sim

Leon, RoboCup 2027 @Home: pib v4 Roboterhand-Simulation in NVIDIA Isaac Sim 5.1.

## Branch `experiment/omnigraph-lightweight`
Bewusst minimaler Zweig: Isaac-seitige ROS2-Anbindung läuft über einen nativen Action
Graph (OmniGraph, Teil der USD-Stage) statt über eigenen Python-Bridge-Code. Diese Datei
beschreibt den Stand **dieses Branches**. Der vollständige Stand mit `robot_io.py`,
ControlMode-Architektur und Sprint-Fahrplan liegt auf `feature/ros2-control` (eigenes,
dort gültiges CLAUDE.md).

## Session-Start
**Lies zuerst `docs/handoff.md`** — enthält Stand und offene Punkte der letzten Session.

## Stack
- **Isaac Sim 5.1** — Script Editor (`start.py`) + Action Graph (Teil der USD-Stage) + `ros2_control`
- **Python 3.10+**, numpy | kein Test-Framework
- Keine LSTM/Training-Pipeline auf diesem Branch (siehe `feature/ros2-control`)

## Vorzeichen-Konvention (behoben, ADR-007)
Onshape und Isaacs importierte Gelenkachsen waren vorzeicheninvertiert — physikalische
Eigenschaft des Modells, kein Doku-Detail. Behoben direkt am Prim in
`isaac_sim/tools/flip_joint_sign.py` (einmalig gegen `isaac_sim/usd/pib_upperbody.usd`
ausgeführt, Ergebnis gespeichert) — kein Script Node, kein `JOINT_SIGN` mehr nötig, siehe
ADR-007. Bei einem künftigen Neuimport aus Onshape muss das Skript erneut laufen.

- Vorzeichen-Referenz (verifiziert): `shoulder_horizontal_right: +20` = Arm vorne; `elbow_right: +90` = voll gebeugt

## Isaac Sim API-Regeln
- Kein `time.sleep()` → `await app.next_update_async()` (Editor) / `sim_app.update()` (Standalone)
- `_load_mod(name, path)` in `start.py`/`setup_stage.py` → umgeht stale `.pyc`-Cache
- `configure_drives()` jede Session aufrufen (PhysX cached Stiffness/Damping nicht) — `start.py` vor Play ausführen
- `set_joint_limits()` verwenden — `fix_joint_limits` existiert nicht mehr
- DOF-Namen nie erfinden → aus `config/pib_hand_config.py` oder der URDF (`ros2_ws/src/pib_description/urdf/`)

## Team (alle nutzen ROS2)
- **IK-Team**: Inverse Kinematik → gibt Gelenkwinkel-Trajektorien aus
- **Greifpunkt-Team**: Greifpunkterkennung → gibt Greifpunkt im Roboterframe aus
- **Objekterkennung**: hinten angestellt

## Ziel-Architektur
```
Extern (ROS2, ros2_control) → Action Graph (ROS2SubscribeJointState → IsaacArticulationController) → Isaac
```
Details: @docs/architecture.md (Abschnitt "Action Graph")

## Ziele (dieser Branch)
- **OmniGraph-Migration** ✓ Action Graph ersetzt `pib_bridge.py`, Pickup-/Putdown-Demo verifiziert
- **Vorzeichen-Fix** ✓ Gelenke direkt am Prim korrigiert (ADR-007), kein Script Node/JOINT_SIGN mehr
- **Contact Sensors** ← aktuelles Ziel — Ansatz entschieden (nativer `IsaacContactSensor`-
  Node, ADR-008), `index_right` verkabelt+verifiziert, restliche 9 Fingerspitzen offen
- **Szenen-Erweiterung** ← aktuelles Ziel — weitere Objekte/Umgebung in der USD-Stage

Alte Phasen/Sprints (Simulation Server, Team-Integration, LSTM-Training) sind für diesen
Branch verworfen — voller Fahrplan dazu auf `feature/ros2-control`.

## Schlüsseldateien
```
config/pib_hand_config.py      DOF-Namen, Indizes, ROBOT_PRIM_PATH, Joint-Limits
isaac_sim/start.py             Startroutine: Drives + Limits + Initialpose (vor Play ausführen)
isaac_sim/setup_stage.py       von start.py genutzt
isaac_sim/autostart.py         vollautomatischer Start ohne Script Editor (--exec)
isaac_sim/usd/pib_upperbody.usd   Roboter + Action Graph (einzige USD-Datei im Repo)
ros2_ws/src/pib_description/                  URDF (44 DOFs + ros2_control-Tags) + Meshes
ros2_ws/src/pib_bringup/config/controllers.yaml   JTC + JointStateBroadcaster, 50 Hz
ros2_ws/src/pib_bringup/launch/pib_sim.launch.py  startet gesamten ros2_control-Stack
ros2_ws/src/pib_bringup/pib_bringup/test_client_pickup.py    Pickup-Demo (FollowJointTrajectory)
ros2_ws/src/pib_bringup/pib_bringup/test_client_putdown.py   Putdown-Demo (Umkehrung)
```

→ Architektur: @docs/architecture.md | Konventionen: @docs/conventions.md
→ Entscheidungen: @docs/decisions.md (ADR-007) | Sprint: @docs/current-sprint.md
