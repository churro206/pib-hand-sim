# pib Hand Simulation

Simulationsserver für den RoboCup 2027 (@Home Liga).
Ziel: pib v4 Oberköper (44 DOFs) in NVIDIA Isaac Sim 5.1 — steuerbar über ROS2, Greifkraft-Erkennung, später LSTM-Gelenkdynamik.

---

## Aktueller Stand

| Phase | Status |
|---|---|
| Isaac IO-Schicht (robot_io, setup_stage) | ✓ fertig |
| Control-Architektur (DirectMode, ServoMode, NNMode) | ✓ fertig |
| Sequenz-Executor (runner.py, Smoothstep) | ✓ fertig |
| ROS2-Bridge (Jazzy, JointTrajectory → Isaac) | ✓ end-to-end verifiziert |
| is_grasping() via Admittanz | in Arbeit |
| Scene API (reset, place_object) | geplant |
| AS5600-Sensordaten + LSTM-Training | Phase 5 |

---

## Schnellstart

### Voraussetzungen
- NVIDIA Isaac Sim 5.1
- ROS2 Jazzy (`/opt/ros/jazzy`)
- Python 3.10+, numpy, `ROS_DOMAIN_ID=0`

### Isaac Sim starten
```
1. USD laden
2. start.py im Script Editor ausführen    ← Drives + Limits + T-Pose
3. Play drücken
4a. runner.py ausführen                   → Sequenz abspielen
4b. ros2_server.py ausführen              → ROS2-Bridge starten
```

### ROS2-Bridge testen
```bash
export ROS_DOMAIN_ID=0
source /opt/ros/jazzy/setup.bash

ros2 topic list                           # Topics prüfen
python3 tools/send_test_trajectory.py    # Testsequenz schicken
ros2 topic echo /pib/joint_states --once # Feedback lesen
```

---

## Architektur (4 Schichten)

```
Layer 4: Team-Integration (Sprint 4)
         ROS2-Protokoll, Koordinatenrahmen, IK-Interface

Layer 3: Simulation Server (Sprint 3)  ←
         ros2_server.py — Observation API, Scene API, ROS2-Bridge

Layer 2: Control-Architektur (fertig)
         DirectMode | ServoMode | NNMode → sequences.py → runner.py

Layer 1: Isaac IO-Schicht (fertig)
         robot_io.py — JOINT_SIGN, Grad↔Rad, DriveAPI, 44 DOFs
```

---

## ROS2-Schnittstelle

| Topic | Typ | Richtung | Beschreibung |
|---|---|---|---|
| `/pib/joint_trajectory` | `trajectory_msgs/JointTrajectory` | → Isaac | Gelenkwinkel-Trajektorie (IK-Team) |
| `/pib/set_mode` | `std_msgs/String` | → Isaac | Control-Mode wechseln (`direct`/`servo`/`nn`) |
| `/pib/joint_states` | `sensor_msgs/JointState` | ← Isaac | Ist-Positionen aller 44 DOFs, 30 Hz |
| `/pib/grasp_state` | `std_msgs/Bool` | ← Isaac | Greif-Status |

**Winkeleinheit:** aktuell Grad (Platzhalter) — in `config/server_config.py` auf `"rad"` umstellen wenn mit IK-Team abgestimmt.

---

## Schlüsseldateien

```
config/
  pib_hand_config.py     DOF-Namen, Indizes, JOINT_SIGN, Servo-Faktoren
  sequences.py           Pose-Sequenzen (Onshape-Konvention)
  server_config.py       ROS2-Konfiguration: Mode, Topics, Winkeleinheit

control/
  base.py                ControlMode ABC
  direct.py              DirectMode — pass-through
  servo.py               ServoMode — Sehnen-Mapping
  nn.py                  NNMode — Stub (Phase 5)

isaac_sim/
  robot_io.py                   Einzige Isaac-IO-Schicht: set/get, JOINT_SIGN
  setup_stage.py                Drives + Limits (einmalig pro Session)
  start.py                      Startroutine (configure_physics + drives + limits + pose)
  runner.py                     Sequenz-Executor (Library): execute(seq, mode, side)
  ros2_server.py                ROS2-Bridge: JointTrajectory → Isaac, joint_states publizieren
  sequences/
    template.py                 Vorlage für neue Sequenzen (kopieren + anpassen)
    test_hand_poses.py          Winken → Doppelbizeps → Peace
    test_tendon.py              Sehnenmechanik-Test (ServoMode)
    demo_pickup.py              Pickup-Demo (physikalisch verifiziert)

tools/
  send_test_trajectory.py       ROS2-Testskript: Trajectory senden + Feedback lesen
```

---

## Konventionen

### Winkel
- Intern immer **Grad**, Onshape-Konvention (positiv = Flexion/Heben/Vorne)
- `JOINT_SIGN = -1` kompensiert Onshape↔Isaac — **nur in robot_io**, nie außerhalb
- Hand-Clip: `[0°, 90°]`; Body: kein Clip

### Isaac Sim
- Kein `time.sleep()` → `await app.next_update_async()` (Editor) / `sim_app.update()` (Standalone)
- `_load_mod(name, path)` in jedem Skript → umgeht stale `.pyc`-Cache
- `configure_drives()` jede Session aufrufen (PhysX cached Stiffness/Damping nicht)

### ROS2
- `ROS_DOMAIN_ID=0` — Projektstandard
- Isaac Sim wird ohne gesetztes Domain-ID gestartet (Default = 0)

---

## Sequenzen abspielen

Jede Sequenz ist ein eigenes Script in `isaac_sim/sequences/` — direkt im Script Editor öffnen und ausführen:

| Script | Mode | Beschreibung |
|---|---|---|
| `sequences/test_hand_poses.py` | direct | Winken → Doppelbizeps → Peace |
| `sequences/test_tendon.py` | servo | Sehnenmechanik: Hand 3× schließen/öffnen |
| `sequences/demo_pickup.py` | direct | Dose greifen und heben |

**Neue Sequenz erstellen:** `sequences/template.py` kopieren, Steps anpassen, ausführen.

---

## Greif-Erkennung (in Arbeit)

**Admittanz-Heuristik** (Sprint 3): `robot.get_measured_joint_efforts()` gibt Torque pro Gelenk.
Hoher Torque bei geschlossenem Target → Objekt blockiert Finger → Greifkontakt.

**Contact Reports** (Phase 5): PhysX-Kontaktkräfte an Fingertip-Prims als virtuelle Drucksensoren —
gleiche Modalität wie echte FSR-Sensoren, besser für LSTM-Training.

---

## Phase 5 — LSTM-Gelenkdynamik (geplant)

Das Netz lernt `(Sollwinkel_t, Istwinkel_{t-1}) → Istwinkel_t` — modelliert Trägheit,
Reibung und Hysterese der Sehnenmechanik.

```
Isaac Sim (synthetisch) ──┐
                           ├── training/train.py → hand_lstm_*.pt
AS5600-Sensordaten (real) ─┘
         ↓
   export_onnx.py → *.onnx → STM32 (Nucleo H723ZG)
   export_weights.py → *_weights.npz → NNMode in Isaac
```

Architektur: 2-Layer LSTM, hidden_size=128, Input: 22 Features (11 cmd + 11 pos_prev).

---

## Lokale Umgebung

```bash
git clone https://github.com/churro206/pib-hand-sim
cd pib-hand-sim
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Docker (Training)
```bash
docker compose build
docker compose run --rm train
docker compose run --rm export
```

---

## Team

| Team | Aufgabe | Schnittstelle |
|---|---|---|
| pib-Sim (Leon) | Simulation, Control, ROS2-Server | — |
| IK-Team | Gelenkwinkel-Trajektorien berechnen | → `/pib/joint_trajectory` |
| Greifpunkt-Team | Greifpunkterkennung im Roboterframe | → (Sprint 4) |
| Objekterkennung | Objekte im Kamerabild erkennen | hinten angestellt |
