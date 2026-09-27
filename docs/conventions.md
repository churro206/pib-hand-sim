# Konventionen

**Branch `experiment/omnigraph-lightweight`.** Beschreibt den Stand dieses Branches — kein
`robot_io.py`, kein `control/`, keine Sequenz-Pipeline. Voller Stand auf `feature/ros2-control`.

> **Geerbt auf `feature/rl-grasping`** (Branch-Abzweigung 2026-09-27): weiterhin gültig für
> die Simulationsseite, die dieser Branch nutzt (nicht hier gepflegt). Siehe `CLAUDE.md` /
> `docs/rl-grasping-notes.md` für RL-spezifisches.

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
**v4** — Schema: `dof_{teil}_{seite}_{position}`
- Beispiele: `dof_index_left_proximal`, `dof_shoulder_vertical_right`, `dof_thumb_left_rotator`
- Seite: `left` / `right`; Position: `proximal` / `distal` / `tip` / `rotator` / `vertical` / `horizontal`
- Nie erfinden — immer aus `config/pib_hand_config_v4.py` oder der URDF (`ros2_ws/src/pib_description_v4/urdf/`)

**v5** — Schema: `{teil}_{seite}_{position}` (**kein** `dof_`-Präfix — bewusst so aus Onshape
exportiert, nicht angleichen). Sonst identisch, mit einer Abweichung: Daumen-Mittelgelenk
heißt `tip` statt `distal` (`thumb_right_tip` statt `dof_thumb_right_distal` in v4).
- Nie erfinden — immer aus `config/pib_hand_config_v5.py` oder `pib_upperbody_urdf_v5/robot.urdf`

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

**Öffentliches Interface — für IK-Team/Greifpunkt-Team/Objekterkennung:**
| Topic | Typ | Richtung |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | ← ros2_control (50 Hz, rad), vom `JointStateBroadcaster` — Standard, MoveIt2-kompatibel |
| `/joint_trajectory_controller/follow_joint_trajectory` | Action `control_msgs/FollowJointTrajectory` | → ros2_control, MoveIt2-kompatibel — so werden Gelenkwinkel-Trajektorien (z.B. vom IK-Team) eingespielt |
| `/pib/fingertip_force/<finger>` | `std_msgs/Float32` | ← Isaac (Newton), ein Topic pro Fingertip, vom Action Graph publiziert (ADR-008). Bisher nur `index_right` verkabelt, Rest offen — Format kann sich noch ändern (Bündelung zu einem Topic als `sensor_msgs/JointState`, siehe ADR-008). |

**Intern — Hardware-Interface-Bridge (ros2_control ↔ Isaac), nicht für andere Teams gedacht:**
| Topic | Typ | Richtung |
|---|---|---|
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad), gelesen vom Action Graph |
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (rad), vom Action Graph publiziert — Rohwert auf Hardware-Interface-Ebene, entspricht inhaltlich `/joint_states`, aber ohne den ros2_control-Layer davor |

**v5 only (ADR-009)**: Werte in `/pib/hw/joint_commands` für `{index,middle,ring,pinky}_
{left,right}_distal`/`_tip` und `thumb_{left,right}_tip` (18 von 44 Gelenken) werden vom
`FingerCoupling`-Script-Node im Action Graph **ignoriert** und durch die analytisch
gekoppelten Werte aus dem jeweils gemessenen MCP-/PIP-Ist-Winkel ersetzt — diese Gelenke
sind auf der realen Hand nicht unabhängig aktuierbar (Sehnenkopplung, nicht 3 Motoren pro
Finger). `proximal` (MCP) bleibt normale ROS2-Positions-Drive.

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

### Script Node (Action Graph) — Modulebene vs. setup()/compute()
**Nie** Klassen/Instanzen mit echten Berechnungen auf Modulebene eines Script-Node-Skripts
anlegen (z.B. `import numpy as np` gefolgt von `MEIN_OBJEKT = MeineKlasse(...)` direkt
danach). Beobachteter Fehler (ADR-009): `NameError: name 'np' is not defined` beim Aufruf
einer Methode, obwohl der `import` sichtbar direkt darüber steht. Ursache: Isaac Sims
Script-Node-Sandbox execut Top-Level-Code offenbar mit getrennten globals-/locals-Dicts —
der `import` landet nur im locals-Dict, Methoden einer auf Modulebene definierten Klasse
bekommen aber das (numpy-lose) globals-Dict als `__globals__`. Klassischer Python-
Fallstrick bei `exec()` mit getrennten globals/locals.

**Fix**: Klasse(n) und Instanzen als Closures innerhalb von `setup(db)` definieren,
Instanzen in `db.per_instance_state` ablegen, `compute(db)` greift nur noch darauf zu:
```python
def setup(db):
    import numpy as np

    class Foo:
        def bar(self):
            return np.array(...)  # funktioniert -- echte Closure ueber setup()s Frame

    db.per_instance_state.foo = Foo()

def compute(db):
    result = db.per_instance_state.foo.bar()
```
Referenzimplementierung: `isaac_sim/tools/finger_coupling_script_node.py`.

## Commit-Konventionen
- Keine automatischen Commits — Leon schaut erst drüber
