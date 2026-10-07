# pib-Hand-Sim

Leon, RoboCup 2027 @Home: pib v4 Roboterhand-Simulation in NVIDIA Isaac Sim 5.1.

## Branch `feature/rl-grasping`
Seit 2026-10-04 Arbeitsbranch: der digitale Zwilling von `experiment/omnigraph-lightweight`
(v5-USD, Action Graph, Mimic Joints, Servo-Modell, Kontaktsensoren — alles weiter gültig) plus
**RL-Greifen in Isaac Lab** für die reale linke v5-Hand (Proof of Concept, ADR-014/015).
Der alte Branch-Stand (Sehnendynamik-Script-Node, ADR-009) liegt im Tag
`backup/rl-grasping-c0b3f6d`. Team-Integration/LSTM: `feature/ros2-control`.

## Session-Start
**Lies zuerst `docs/handoff.md`** — enthält Stand und offene Punkte der letzten Session.

## Stack
- **Isaac Sim 5.1** — Script Editor (`start.py`) + Action Graph (Teil der USD-Stage) + `ros2_control`
- **Isaac Lab 2.3.2** (`~/IsaacLab`, `rsl_rl` PPO) in conda-Umgebung `env_isaaclab` (Miniconda)
- **Python 3.10+**, numpy | kein Test-Framework (Prüfskripte in `isaac_lab/`)
- Ziel-Hardware der Policy: STM32N657 (NUCLEO-N657X0, Neural-ART-NPU, int8) — später Jetson Thor

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

## Isaac Lab Regeln (ADR-015)
- **Nie** in Isaac Sims eigenes Python installieren — nur in `conda activate env_isaaclab`,
  Projekt-`.venv` vorher deaktivieren (`isaaclab.sh` nimmt die gerade aktive Python)
- Starten über `~/IsaacLab/isaaclab.sh -p isaac_lab/<skript>.py` — Befehle in
  `docs/conventions.md` → „Isaac Lab“
- Tests/Vorführungen **mit Fenster** (Leon schaut zu), headless nur fürs Training; nur ein
  Isaac-Fenster gleichzeitig (8 GB VRAM)
- Isaac-Lab-API nie raten — gegen `~/IsaacLab/source` prüfen; Vorbild ist Dexsuite
  (`isaaclab_tasks/manager_based/manipulation/dexsuite`)
- Hand-USD: Mimic/Limits/Antriebe sind eingebrannt (`bake_hand_asset_v5.py`) — nach
  Änderungen an `setup_stage.py`/Config erneut ausführen und speichern
- Kontaktsensor mit Objekt-Filter: **ein** `ContactSensorCfg` pro Fingerspitze
- Skripte enden mit Bericht-Datei + `os._exit(0)` (`simulation_app.close()` hängt)
- Training/Bewertung als **Experiment** über `isaac_lab/experiments.py` (ADR-016, `experiments/README.md`): Hypothese + genau eine Änderung vorher, ≥ 3 Seeds, Bewertung nach eval-v1 — nicht über die Trainings-Belohnung vergleichen

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
- **Digitaler Zwilling v5** ✓ (geerbt): Action Graph, ros2_control, Pickup/Putdown v5,
  Mimic Joints (ADR-011), Servo-Modell (ADR-012), Kontaktsensoren (ADR-013),
  Handgelenk-Pleuel [−60°, 0°] (ADR-014)
- **RL-Greifen, Proof of Concept** ← aktuell (ADR-015, Plan in `docs/current-sprint.md`):
  - M1 Policy greift in der Sim — EXP-004: 77 % aufrecht gehalten (≤ 45°), offen: Fingernutzung, Kraft
  - M2 Policy int8-quantisiert auf dem STM32N657 (`stedgeai validate`)
  - M3 echte Hand (optional, Sim-to-Real-Kalibrierung nötig)
- Policy sieht nur reale Sensoren (8 Servo-Winkel, 5 FSR); Aktionsraum = 8 Servos

## Schlüsseldateien
```
config/pib_hand_config_v4.py   DOF-Namen, Indizes, ROBOT_PRIM_PATH, Joint-Limits (v4, verifiziert)
config/pib_hand_config_v5.py   dasselbe für v5 (gegen URDF und Stage verifiziert), dazu
                               Servo-Aktuatormodell SERVOS/V5_ACTUATORS/servo_actuator()
                               (ADR-012, Nm/° und Nm/rad), Handgelenk-Pleuel WRIST_LINKAGE
                               (ADR-014) und LEFT_HAND_SERVO_JOINTS
isaac_sim/start.py             Startroutine: Drives + Mimic + Limits + Initialpose (vor Play ausführen)
isaac_sim/setup_stage.py       von start.py genutzt — v5: wendet das Aktuatormodell aus der
                               Config an, MIMIC_JOINTS (ADR-011); v4: _v4_gains
isaac_sim/autostart.py         vollautomatischer Start ohne Script Editor (--exec), lädt v4
isaac_sim/usd/pib_upperbody_v4.usd   Roboter (v4) + Action Graph — verifizierter Arbeitsstand
isaac_sim/usd/pib_upperbody_v5.usd   Roboter (v5) + Action Graph (OnPhysicsStep), Self-Collision an
isaac_sim/tools/audit_asset.py       Asset-Inspektion: Massen USD/PhysX/URDF, Collider, Antriebe,
                                     effektive Gelenkträgheit, ω_n·Δt/ζ nach NVIDIA (nur lesend)
isaac_sim/tools/inspect_action_graph.py        Graph-Inventur aus der USD (Knoten, Verbindungen, Sensoren)
isaac_sim/tools/build_contact_sensors_v5.py    10 Fingertip-Kontaktsensor-Prims anlegen (ADR-013)
isaac_sim/tools/build_fingertip_force_graph_v5.py  Kraft-Bündel-Graph → /pib/fingertip_forces
isaac_sim/tools/bake_hand_asset_v5.py   Mimic/Limits/Antriebe/Self-Collision in die Hand-USD
isaac_sim/usd/pib_hand_left_v5.usd       Hand + Unterarm (links) für Isaac Lab
pib_hand_left_urdf_v5/                   onshape-to-robot-Export der Hand (Basis: elbow_lower)
isaac_lab/pib_hand_left_v5_cfg.py        Isaac-Lab-Asset: Aktuatoren aus der v5-Config, Handgelenk Remotized
isaac_lab/pib_grasp/                     Greifaufgabe (env_cfg, mdp, agents/rsl_rl_ppo_cfg)
isaac_lab/train.py, play.py              Isaac Labs rsl_rl-Skripte mit den pib-Tasks
isaac_lab/check_hand_asset.py            Prüfung Hand-USD in Isaac Lab (Mimic, Sensoren)
isaac_lab/scripted_grasp_test.py         Machbarkeitstest ohne Policy (Fenster, Echtzeit)
isaac_lab/experiments.py                 Experiment-Framework: new/bench/run/eval/done (ADR-016)
isaac_lab/eval_policy.py                 Bewertungsprotokoll eval-v1 (Aufgabenerfolg, Leitplanken)
experiments/                             Experimente (experiment.yaml, Berichte), index.md, README
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
→ Entscheidungen: @docs/decisions.md (ADR-011–017) | Sprint: @docs/current-sprint.md
→ RL-Ursprungs-Prompt/Bewertung: `docs/rl-grasping-notes.md`
