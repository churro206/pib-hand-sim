# Konventionen

**Branch `experiment/omnigraph-lightweight`.** Beschreibt den Stand dieses Branches — kein
`robot_io.py`, kein `control/`, keine Sequenz-Pipeline. Voller Stand auf `feature/ros2-control`.

## Winkel und Vorzeichen

### Konvention (ROS2 und Isaac identisch, seit ADR-007)
- Positiv = Flexion (Finger schließt), Heben (Arm geht hoch), Vorne (Arm geht nach vorne)
- 0° = T-Pose / vollständig offen
- Gilt auf `/pib/hw/joint_commands`, `/pib/hw/joint_states` und direkt an den Gelenk-Prims —
  bis ADR-007 waren Onshape/URDF und die importierten USD-Gelenkachsen vorzeicheninvertiert,
  behoben durch `isaac_sim/tools/flip_joint_sign.py` (einmalig gegen die Prims ausgeführt,
  siehe `docs/decisions.md`)
- Gelenk-Limits nach `set_joint_limits()` (`setup_stage.py`): Hand [0°, 90°], Ellbogen [-45°, 90°], Handgelenk [0°, 90°]
- Kein Clip im Code — Gelenklimits kommen aus den USD-Joint-Limits selbst

### Verifizierte Vorzeichen-Referenzen
- `dof_shoulder_horizontal_right: +20` → Arm leicht nach vorne
- `dof_shoulder_vertical_left: -30` → Arm leicht hängend (unter T-Pose)
- `dof_elbow_right: +90` → Ellbogen voll gebeugt
- `dof_shoulder_horizontal_left: -90` → linker Arm nach vorne (gespiegelte Achse!)

## Namenskonventionen

### DOF-Namen
Schema: `dof_{teil}_{seite}_{position}`
- Beispiele: `dof_index_left_proximal`, `dof_shoulder_vertical_right`, `dof_thumb_left_rotator`
- Seite: `left` / `right`; Position: `proximal` / `distal` / `tip` / `rotator` / `vertical` / `horizontal`
- Nie erfinden — immer aus `config/pib_hand_config.py` oder der URDF (`ros2_ws/src/pib_description/urdf/`)

### Python-Dateien
- `isaac_sim/` — alles was Isaac Sim braucht (`start.py`, `setup_stage.py`, `autostart.py`)
- `config/` — reine Daten/Konfiguration, keine Isaac-Imports
- `ros2_ws/src/pib_bringup/pib_bringup/` — ROS2-Test-Clients (reines rclpy, kein Isaac-Import)
- Prefix `_` für interne Hilfsfunktionen: `_load_mod()`, `_find_root()`

## ROS2-Konventionen

### Domain ID
`ROS_DOMAIN_ID=0` — Projektstandard für alle Teams.

Isaac Sim wird ohne gesetztes `ROS_DOMAIN_ID` gestartet (Default = 0). Im Terminal vor jeder ROS2-Session setzen:
```bash
export ROS_DOMAIN_ID=0
```

### Topics (dieser Branch)
| Topic | Typ | Richtung |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | ← ros2_control (50 Hz, rad) |
| `/joint_trajectory_controller/follow_joint_trajectory` | Action `control_msgs/FollowJointTrajectory` | → ros2_control, MoveIt2-kompatibel |
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad), gelesen vom Action Graph |
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (rad), vom Action Graph publiziert |

Winkeleinheit durchgehend **Radiant** — kein separater `deg`/`rad`-Umschalter mehr (`config/server_config.py` existiert auf diesem Branch nicht).

### Workflow
```
USD laden (enthält Action Graph) → start.py → Play
  → Action Graph läuft automatisch mit
ros2 launch pib_bringup pib_sim.launch.py
ros2 run pib_bringup test_client_pickup     # oder test_client_putdown
```
`start.py` erneut ausführen = hot-reload für Drives/Limits (kein Isaac-Neustart nötig).
Der Action Graph selbst braucht kein erneutes Ausführen — er ist Teil der Stage und lebt
mit Play/Stop.

---

## Isaac Sim Patterns

### Modul laden (Script Editor)
```python
def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod
```
Genutzt von `start.py`, um `setup_stage.py` zu laden.

### Simulation-Loop
```python
# Script Editor:
await app.next_update_async()
```
(Kein Standalone-Modus mehr auf diesem Branch — `_launch_helper.py` wurde entfernt.)

## Commit-Konventionen
- Keine automatischen Commits — Leon schaut erst drüber
