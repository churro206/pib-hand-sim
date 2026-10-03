# pib-Hand-Sim

Leon, RoboCup 2027 @Home: pib v4 Roboterhand-Simulation in NVIDIA Isaac Sim 5.1.

## Branch `experiment/omnigraph-lightweight`
Bewusst minimaler Zweig: Isaac-seitige ROS2-Anbindung läuft über einen nativen Action
Graph (OmniGraph, Teil der USD-Stage) statt über eigenen Python-Bridge-Code. Diese Datei
beschreibt den Stand **dieses Branches**. Der vollständige Stand mit `robot_io.py`,
ControlMode-Architektur und Sprint-Fahrplan liegt auf `feature/ros2-control` (eigenes,
dort gültiges CLAUDE.md). Feinmotorisches Greifen per Reinforcement Learning (Isaac Lab,
aufbauend auf dem hier entstandenen digitalen Zwilling) liegt auf `feature/rl-grasping`
(ebenfalls eigenes CLAUDE.md) — abgezweigt vom inzwischen ersetzten Sehnendynamik-Stand
(`1d0cd9c`, ADR-009), nicht vom aktuellen Mimic-Joint-Stand (ADR-011).

## Session-Start
**Lies zuerst `docs/handoff.md`** — enthält Stand und offene Punkte der letzten Session.

## Stack
- **Isaac Sim 5.1** — Script Editor (`start.py`) + Action Graph (Teil der USD-Stage) + `ros2_control`
- **Python 3.10+**, numpy | kein Test-Framework
- Keine LSTM/Training-Pipeline auf diesem Branch (LSTM: siehe `feature/ros2-control`, RL-Grasping: siehe `feature/rl-grasping`)

## Vorzeichen-Konvention (behoben, ADR-007)
Onshape und Isaacs importierte Gelenkachsen waren vorzeicheninvertiert — physikalische
Eigenschaft des Modells, kein Doku-Detail. Behoben direkt am Prim in
`isaac_sim/tools/flip_joint_sign.py` (einmalig gegen `isaac_sim/usd/pib_upperbody_v4.usd`
ausgeführt, Ergebnis gespeichert) — kein Script Node, kein `JOINT_SIGN` mehr nötig, siehe
ADR-007. Bei einem künftigen Neuimport aus Onshape muss das Skript erneut laufen.

- Vorzeichen-Referenz (verifiziert): `shoulder_horizontal_right: +20` = Arm vorne; `elbow_right: +90` = voll gebeugt

## Isaac Sim API-Regeln
- Kein `time.sleep()` → `await app.next_update_async()` (Editor) / `sim_app.update()` (Standalone)
- `_load_mod(name, path)` in `start.py`/`setup_stage.py` → umgeht stale `.pyc`-Cache
- `start.py` jede Session vor Play ausführen — setzt Drives, Servo-Aktuatormodell, Mimic Joints,
  Limits, Initialpose (PhysX cached Stiffness/Damping nicht); danach Stop → Play
- `set_joint_limits()` verwenden — `fix_joint_limits` existiert nicht mehr
- DOF-Namen nie erfinden → aus `config/pib_hand_config_v4.py`/`_v5.py` oder der jeweiligen URDF (`ros2_ws/src/pib_description_v4/urdf/`, `pib_upperbody_urdf_v5/robot.urdf`)
- **Einheiten am Prim** (USD-Schema, nicht raten): Angular-Drive `stiffness` = Nm/**°**,
  `damping` = Nm·s/**°**, `physxJoint:maxJointVelocity` = °/s, `physxJoint:armature` = kg·m².
  Für ω_n/ζ-Rechnungen ×180/π auf rad umrechnen
- **Mimic-Folgegelenke** (v5: `distal`/`tip` der Finger, `thumb_*_tip`) haben bewusst
  Stiffness/Damping 0 — nie einen aktiven Antrieb darauf setzen (arbeitet gegen die
  Zwangsbedingung, ADR-011). Gearing/Offset nur in `setup_stage.py` → `MIMIC_JOINTS`
- Isaac Sim 5.1 (omni.physx 107.3) hat **keine** Mimic-Compliance (`naturalFrequency`/
  `dampingRatio`) und kein `solveArticulationContactLast` — beides nur in 6.0-Docs
- OmniGraph-Live-Werte nur über `og.Controller.get()` lesbar, nicht über `pxr.Usd`
  (Graph läuft `fabricCacheBacking=StageWithoutHistory`) — umgekehrt landen per
  `og.Controller` gesetzte Werte/Verbindungen nicht zuverlässig in der USD: Persistentes
  (z.B. dynamische `ROS2Publisher`-Eingänge) direkt in der USD authoren, nach Graph-Skripten
  speichern **und neu öffnen**; Graph-Knoten nicht im Stage-Tree umbenennen (ADR-013)
- Script Node (Action Graph), falls je wieder nötig: Klassen/Instanzen **nie** auf Modulebene des Skript-Texts anlegen, nur innerhalb `setup(db)` als Closures + `db.per_instance_state` — sonst `NameError` beim Methodenaufruf trotz sichtbarem `import` darüber (getrennte globals/locals im Sandbox-Exec, siehe ADR-009, `docs/conventions.md`)
- Einfache, einmalige Stage-/Graph-Änderungen macht Leon im GUI — Skripte nur für viele
  gleichartige Wiederholungen oder Diagnose; Diagnose-Skripte schreiben zusätzlich nach
  `isaac_sim/tools/_*.txt` (Script-Editor-Konsole nicht kopierbar)

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
- **v5-Hand-Integration** ✓ Action Graph, ros2_control-Stack, Pickup-/Putdown-Demo für v5,
  `config/pib_hand_config_v5.py`; Regressionscheck der Demo mit Mimic Joints noch offen
- **Fingerkopplung** ✓ PhysX Mimic Joints (ADR-011, linear, gearing=-1) — ersetzt den
  Sehnendynamik-Script-Node (ADR-009) und die verworfene Kraft-Rückwirkung (ADR-010)
- **Physik-Tuning nach NVIDIA** ✓ weitgehend (ADR-012, Plan in `docs/current-sprint.md`):
  Servo-Aktuatormodell (ST3215/ST3095) für alle v5-Servo-Gelenke, Self-Collision an,
  Tischtest stabil; Restvalidierung (Mimic-Freitest, Audit, Putdown) offen
- **Contact Sensors** ✓ (v5) — alle 10 Fingerspitzen, gebündelt als `sensor_msgs/JointState`
  mit Zeitstempel auf `/pib/fingertip_forces` (ADR-008 + ADR-013)
- **Szenen-Erweiterung** — weitere Objekte/Umgebung in der USD-Stage

Alte Phasen/Sprints (Simulation Server, Team-Integration, LSTM-Training) sind für diesen
Branch verworfen — voller Fahrplan dazu auf `feature/ros2-control`. Feinmotorisches Greifen
per RL ist ebenfalls nicht Teil dieses Branches — siehe `feature/rl-grasping`.

## Schlüsseldateien
```
config/pib_hand_config_v4.py   DOF-Namen, Indizes, ROBOT_PRIM_PATH, Joint-Limits (v4, verifiziert)
config/pib_hand_config_v5.py   dasselbe für v5 (gegen URDF und Stage verifiziert)
isaac_sim/start.py             Startroutine: Drives + Mimic + Limits + Initialpose (vor Play ausführen)
isaac_sim/setup_stage.py       von start.py genutzt — v5: SERVOS/V5_ACTUATORS (Servo-
                               Aktuatormodell, ADR-012), MIMIC_JOINTS (ADR-011); v4: _v4_gains
isaac_sim/autostart.py         vollautomatischer Start ohne Script Editor (--exec), lädt v4
isaac_sim/usd/pib_upperbody_v4.usd   Roboter (v4) + Action Graph — verifizierter Arbeitsstand
isaac_sim/usd/pib_upperbody_v5.usd   Roboter (v5) + Action Graph (OnPhysicsStep), Self-Collision an
isaac_sim/tools/audit_asset.py       Asset-Inspektion: Massen USD/PhysX/URDF, Collider, Antriebe,
                                     effektive Gelenkträgheit, ω_n·Δt/ζ nach NVIDIA (nur lesend)
isaac_sim/tools/inspect_action_graph.py        Graph-Inventur aus der USD (Knoten, Verbindungen, Sensoren)
isaac_sim/tools/build_contact_sensors_v5.py    10 Fingertip-Kontaktsensor-Prims anlegen (ADR-013)
isaac_sim/tools/build_fingertip_force_graph_v5.py  Kraft-Bündel-Graph → /pib/fingertip_forces
ros2_ws/src/pib_description_v4/               URDF (44 DOFs + ros2_control-Tags) + Meshes
ros2_ws/src/pib_bringup/config/controllers.yaml   JTC + JointStateBroadcaster, 50 Hz
ros2_ws/src/pib_bringup/launch/pib_sim.launch.py  startet gesamten ros2_control-Stack (v4)
ros2_ws/src/pib_bringup/pib_bringup/test_client_pickup.py      Pickup-Demo (FollowJointTrajectory)
ros2_ws/src/pib_bringup/pib_bringup/test_client_putdown.py     Putdown-Demo (Umkehrung)
ros2_ws/src/pib_bringup/pib_bringup/test_client_mimic_v5.py    Mimic-Kopplung ohne Last
ros2_ws/src/pib_bringup/pib_bringup/test_client_mimic_load_v5.py  Finger gegen Tisch + Diagnose
```

v4 und v5 laufen bewusst redundant/parallel nebeneinander (nicht: v5 löst v4 ab) — überall
im Repo gilt das `_v4`/`_v5`-Namensschema, siehe `docs/current-sprint.md` für den Stand.

→ Architektur: @docs/architecture.md | Konventionen: @docs/conventions.md
→ Entscheidungen: @docs/decisions.md (ADR-011–013) | Sprint: @docs/current-sprint.md
