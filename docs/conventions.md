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
- Gelenk-Limits nach `set_joint_limits()` (`setup_stage.py`): Hand [0°, 90°], Ellbogen [-45°, 90°],
  Handgelenk v4 [0°, 90°] / v5 [-90°, 30°] (v5-Werte aus der v5-URDF, siehe `_BODY_LIMITS`)

### Einheiten am Gelenk-Prim (USD/PhysX-Schema)
- Angular-Drive `stiffness` in **Nm/°**, `damping` in **Nm·s/°**, `targetPosition` in **°**
- `physxJoint:maxJointVelocity` in **°/s**, `physxJoint:armature` in **kg·m²**
- ROS2-Topics dagegen durchgehend **rad** bzw. rad/s
- Für Eigenfrequenz/Dämpfung (ω_n = √(k/I), ζ = d/(2√(k·I))) Stiffness/Damping ×180/π
  auf rad umrechnen; I = Diagonale der Massenmatrix **plus** Armature (PhysX zählt die
  Armature nicht in die Massenmatrix)
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
| `/pib/fingertip_forces` | `sensor_msgs/JointState` | ← Isaac, 60 Hz, alle 10 Fingerspitzen in einer Nachricht (v5, ADR-013): `name` = `thumb_left, index_left, middle_left, ring_left, pinky_left, thumb_right, index_right, middle_right, ring_right, pinky_right`, `effort` = Kontaktkraft in **Newton** (gleiche Reihenfolge), `header.stamp` = Simulationszeit, `position`/`velocity` leer. Ersetzt die früheren Einzel-Topics `/pib/fingertip_force/<finger>` (ADR-008). |

**Intern — Hardware-Interface-Bridge (ros2_control ↔ Isaac), nicht für andere Teams gedacht:**
| Topic | Typ | Richtung |
|---|---|---|
| `/pib/hw/joint_commands` | `sensor_msgs/JointState` | → Isaac (rad), gelesen vom Action Graph |
| `/pib/hw/joint_states` | `sensor_msgs/JointState` | ← Isaac (rad), vom Action Graph publiziert — Rohwert auf Hardware-Interface-Ebene, entspricht inhaltlich `/joint_states`, aber ohne den ros2_control-Layer davor |

**v5 only (ADR-011)**: `{index,middle,ring,pinky}_{left,right}_distal`/`_tip` und
`thumb_{left,right}_tip` (18 von 44 Gelenken) sind passive Mimic-Folgegelenke ohne eigenen
Antrieb (Stiffness/Damping 0) — ihre Werte in `/pib/hw/joint_commands` laufen zwar weiter
durch den Graph, haben aber **keine Wirkung**. Ihre Stellung ergibt sich aus der
PhysX-Zwangsbedingung (`θ_folge = θ_referenz`, PIP←MCP, DIP←PIP, Daumen-IP←MCP), wie auf
der realen Hand (ein Servo pro Finger am MCP, PIP/DIP über Koppelstangen). Steuern also
nur über `proximal`. `/pib/hw/joint_states` liefert für die Folgegelenke die echten
(gekoppelten) Ist-Werte.

Winkeleinheit durchgehend **Radiant** — kein separater `deg`/`rad`-Umschalter mehr (`config/server_config.py` existiert auf diesem Branch nicht).

### Workflow
```
USD laden (enthält Action Graph) → start.py → Play
  → Action Graph läuft automatisch mit
ros2 launch pib_bringup pib_sim.launch.py          # v5: pib_sim_v5.launch.py
ros2 run pib_bringup test_client_pickup     # oder test_client_putdown (v5: *_v5)

# v5 Mimic-/Lasttests (nach colcon build --packages-select pib_bringup):
ros2 run pib_bringup test_client_mimic_v5 --finger all        # Kopplung ohne Last
ros2 run pib_bringup test_client_mimic_load_v5 --reset        # Finger gegen Tisch
ros2 run pib_bringup test_client_mimic_load_v5 --finger fingers_left --reset
```
`start.py` erneut ausführen = hot-reload für Drives/Limits/Mimic (kein Isaac-Neustart
nötig), danach Stop → Play, damit PhysX die Änderungen übernimmt.

Asset-Diagnose: `isaac_sim/tools/audit_asset.py` im Script Editor (nach `start.py`, auf
Play) → `isaac_sim/tools/_asset_audit.txt`.
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

### Action Graph per Skript ändern — USD vs. laufender Graph (ADR-013)
- Über `og.Controller` (`edit`, `connect`, `attribute(...).set`) gesetzte Werte und
  Verbindungen landen im **laufenden** Graph, nicht zuverlässig in der USD. Was beim nächsten
  Öffnen gelten muss — vor allem dynamische Eingänge des `ROS2Publisher` — direkt in der USD
  anlegen (`prim.CreateAttribute(..., custom=True)`, `attr.SetConnections([...])`).
- Nach jedem Graph-Skript: **speichern und Stage neu öffnen**, erst dann testen.
- Graph-Knoten nicht im Stage-Tree umbenennen/verschieben und keinen Compound bilden, solange
  der laufende Graph vom USD-Stand abweichen kann.
- `DELETE_NODES` mit Knoten-Objekten (`og.Controller.node(path)`), nicht mit Pfad-Strings.
- Werkzeug zum Prüfen: `isaac_sim/tools/inspect_action_graph.py` (liest die USD).

### Script Node (Action Graph) — Modulebene vs. setup()/compute()
Derzeit ist **kein** Script Node im Graph (die Sehnendynamik-Kopplung aus ADR-009 ist durch
Mimic Joints ersetzt, ADR-011). Die Regel bleibt für jeden künftigen Script Node gültig:

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
Referenzimplementierung (nicht mehr im Baum, Git-Historie): `isaac_sim/tools/finger_coupling_script_node.py`
in Commit `1d0cd9c` (auch auf `feature/rl-grasping`).

## Commit-Konventionen
- Keine automatischen Commits — Leon schaut erst drüber
