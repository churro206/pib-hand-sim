# Architektur

## Team-Kontext
RoboCup 2027 @Home. Mehrere Gruppen:
- **pib-Sim** (Leon): Simulation, Control-Architektur, Schnittstellen
- **IK-Team**: Inverse Kinematik — gibt Gelenkwinkel-Trajektorien aus
- **Greifpunkt-Team**: Greifpunkterkennung — gibt Greifpunkt im Roboterframe aus
- **Objekterkennung**: hinten angestellt

Alle Teams nutzen **ROS2**.

---

## 4-Schichten-Modell (Ziel)

```
Layer 4: Team-Integration          Sprint 4
         ROS2-Protokoll, Koordinatenrahmen, IK-Interface

Layer 3: Simulation Server         Sprint 3 ←
         Observation API, Scene API, ROS2-Bridge

Layer 2: Control-Architektur       fertig
         ControlMode ABC (direct | servo | nn), sequences, runner

Layer 1: Isaac IO-Schicht          fertig
         robot_io, setup_stage, Physik-Simulation
```

---

## Layer 1 — Isaac IO-Schicht (fertig)

### Modul-Verantwortlichkeiten

| Modul | Verantwortung |
|---|---|
| `config/pib_hand_config.py` | Einzige Quelle für DOF-Namen, Indizes, JOINT_SIGN, Servo-Faktoren |
| `config/sequences.py` | Pose-Sequenzen in Onshape-Konvention; `_isaac()` konvertiert Inspector-Werte einmalig beim Laden |
| `control/base.py` | `ControlMode` ABC |
| `control/direct.py` | `DirectMode` — pass-through |
| `control/servo.py` | `ServoMode` — Sehnen-Mapping, partial expansion |
| `control/nn.py` | `NNMode` — Stub (Phase 5) |
| `isaac_sim/runner.py` | Sequenz-Executor: lädt Sequenz + ControlMode, Smoothstep-Interpolation, `set_all_targets` |
| `isaac_sim/robot_io.py` | **Einzige Isaac-IO-Schicht.** Kapselt JOINT_SIGN, Grad→Rad, DriveAPI vs. Articulation API |
| `isaac_sim/setup_stage.py` | Einmalig-Setup: PhysicsScene, Drives, Limits, Initialpose |
| `isaac_sim/start.py` | Startroutine: bündelt configure_physics + drives + limits + initial pose |
| `isaac_sim/_launch_helper.py` | Standalone-Launcher: SimApp starten, USD laden, robot_io initialisieren |

### Datenfluss (aktuell)
```
sequences.py (Onshape-Konvention)
  → runner._build_frames()   Smoothstep-Interpolation, persistenter State
  → ControlMode.to_joint_targets()
      ├─ DirectMode:   pass-through
      └─ ServoMode:    Servo-Namen → DOF-Winkel (Sehnen-Mapping)
  → robot_io.set_all_targets()   Dispatcher
      ├─ set_hand_targets()  clip [0°,90°] → ×JOINT_SIGN → ×π/180 → ArticulationController
      └─ set_body_targets()  ×JOINT_SIGN → DriveAPI
```

### Physikalisch validiert
Die Pickup-Demo hat den Zylinder physikalisch angehoben — Kontakt und Reibung
funktionieren. Kollisionsgeometrie und Materialien sind korrekt.

---

## Layer 2 — Control-Architektur (fertig)

### ControlMode-Interface
```python
# control/base.py
from abc import ABC, abstractmethod

class ControlMode(ABC):
    @abstractmethod
    def to_joint_targets(self, command: dict) -> dict:
        """command → {dof_name: winkel_deg} (Onshape-Konvention)"""

# DirectMode:  command = {dof_name: deg}     → pass-through
# ServoMode:   command = {finger: servo_deg} → Sehnen-Mapping (partial)
# NNMode:      command = {finger: servo_deg} → LSTM-Inference (Phase 5, Stub)
```

### runner.py — Workflow
```
SEQUENCE_NAME / MODE_NAME / SIDE oben in runner.py setzen
  → start.py ausführen (vor Play)
  → Play drücken
  → runner.py im Script Editor ausführen
  → erneut ausführen nach Änderungen (kein Isaac-Neustart nötig, _load_mod cacht nicht)
```

---

## Layer 3 — Simulation Server (Sprint 3, geplant)

### Observation API
```python
get_robot_state() → {
    "joint_positions": {dof_name: angle_deg},   # alle 44 DOFs
    "end_effector_pose": (position, rotation),   # FK, Weltframe
}
get_object_pose()  → (position, rotation)        # Objektposition im Weltframe
is_grasping()      → bool                        # PhysX Contact Reports
```

### Scene API
```python
reset()              # Roboter T-Pose, Objekt Ausgangsposition
place_object(pose)   # Objekt an beliebige Position setzen
```

### ROS2-Bridge (dünner Wrapper)
```
Subscribe: /pib/joint_command   → ControlMode → robot_io
Publish:   /pib/joint_states    ← get_robot_state()
Publish:   /pib/grasp_state     ← is_grasping()
```

---

## Layer 4 — Team-Integration (Sprint 4, geplant)

### Offene Fragen (blockiert alles)
- Koordinatenrahmen: pib-Basis als Ursprung? Welche Achsenkonvention?
- ROS2-Distro der anderen Teams?
- Welche Message-Typen nutzen IK-Team und Greifpunkt-Team?

### Informationsfluss (Vollbild)
```
[Greifpunkt-Team]       [IK-Team]                  [pib-Sim]
  Greifpunkt             nimmt Greifpunkt
  im Roboterframe        → berechnet Trajektorie
  → /pib/grasp_point →   → /pib/joint_command  →   ROS2-Bridge
                                                    → ControlMode
                                                    → robot_io
                                                    → Isaac Sim
                                                    ← /pib/joint_states
                                                    ← /pib/grasp_state
```

---

## Robot-Prim
```
ROBOT_PRIM_PATH = /World/pib_upperbody_7_flattened/pib_upperbody_URDF
DOFs: 14 Body + 15 linke Hand + 15 rechte Hand = 44 gesamt
```
