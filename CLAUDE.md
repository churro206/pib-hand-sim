# pib-Hand-Sim

Leon, RoboCup 2027 @Home: pib v4 Roboterhand-Simulation in NVIDIA Isaac Sim 5.1.

## Session-Start
**Lies zuerst `docs/handoff.md`** — enthält Stand und offene Punkte der letzten Session.

## Stack
- **Isaac Sim 5.1** — Script Editor + Standalone via `_launch_helper.py`
- **PyTorch 2.6 / ONNX** — LSTM-Training in Docker, Export für STM32 (Nucleo H723ZG)
- **Python 3.10+**, numpy, pyserial | kein Test-Framework

## JOINT_SIGN = -1 (kritisch, nie vergessen)
Onshape und Isaac sind vorzeicheninvertiert. Kompensation **ausschließlich** in `robot_io.py`.

| Funktion | Erwartet | Anwendung |
|---|---|---|
| `set_all_targets(d)` | Onshape-Konvention (positiv = Flexion/Heben/Vorne) | runner, sequences, direct, servo |
| `apply_full_pose(d)` | Isaac-Konvention (Physics Inspector Werte) | manuelle Inspector-Tests im Script Editor |

- Winkel intern immer in **Grad**; Isaac API in Radiant → `_to_isaac_rad()` in robot_io
- Hand-Clip: `[0°, 90°]` vor JOINT_SIGN; Body: kein Clip
- JOINT_SIGN **nie** außerhalb robot_io verwenden
- Vorzeichen-Referenz (verifiziert): `shoulder_horizontal_right: +20` = Arm vorne; `elbow_right: +90` = voll gebeugt

## Isaac Sim API-Regeln
- Kein `time.sleep()` → `await app.next_update_async()` (Editor) / `sim_app.update()` (Standalone)
- `_load_mod(name, path)` in jedem Skript → umgeht stale `.pyc`-Cache
- `configure_drives()` jede Session aufrufen (PhysX cached Stiffness/Damping nicht)
- `set_joint_limits()` verwenden — `fix_joint_limits` existiert nicht mehr
- DOF-Namen nie erfinden → erst `inventory.py` ausführen

## Team (alle nutzen ROS2)
- **IK-Team**: Inverse Kinematik → gibt Gelenkwinkel-Trajektorien aus
- **Greifpunkt-Team**: Greifpunkterkennung → gibt Greifpunkt im Roboterframe aus
- **Objekterkennung**: hinten angestellt

## Ziel-Architektur
```
Extern (ROS2) → ControlMode(direct|servo|nn) → robot_io.set_all_targets() → Isaac
```
4-Schichten-Modell (IO → Control → Server → Team): @docs/architecture.md

## Phasen
- **Phase 1** ✓ Direktsteuerung (`robot_io`, `setup_stage`, Pickup-Demo physikalisch verifiziert)
- **Phase 2** ✓ Control-Architektur (`ControlMode` ABC, `DirectMode`/`ServoMode`/`NNMode`, `sequences.py`, `runner.py`)
- **Phase 3** Simulation Server (Observation API, Scene API, ROS2-Bridge)
- **Phase 4** Team-Integration (IK, Greifpunkt, Koordinatenrahmen)
- **Phase 5** AS5600-Sensordaten, LSTM mit echten Daten trainieren

## Schlüsseldateien
```
config/pib_hand_config.py      DOF-Namen, Indizes, JOINT_SIGN, Servo-Faktoren
config/sequences.py            Pose-Sequenzen (Onshape-Konvention); _isaac() für Inspector-Werte
control/base.py                ControlMode ABC
control/direct.py              DirectMode — pass-through
control/servo.py               ServoMode — Sehnen-Mapping, partial expansion
control/nn.py                  NNMode — Stub (Phase 5)
isaac_sim/runner.py            Sequenz-Executor: SEQUENCE_NAME / MODE_NAME / SIDE oben anpassen
isaac_sim/robot_io.py          einzige Isaac-IO-Schicht (hier kein Refactor ohne Grund)
isaac_sim/setup_stage.py       Drives + Limits (einmalig pro Session vor Play)
isaac_sim/start.py             Startroutine: configure_physics + drives + limits + initial pose
isaac_sim/_launch_helper.py    Standalone-Launcher (legt robot + robot_io an)
```

→ Architektur: @docs/architecture.md | Konventionen: @docs/conventions.md
→ Entscheidungen: @docs/decisions.md | Sprint: @docs/current-sprint.md
