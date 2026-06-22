# Konventionen

## Winkel und Vorzeichen

### Onshape-Konvention (Code-Standard)
- Positiv = Flexion (Finger schließt), Heben (Arm geht hoch), Vorne (Arm geht nach vorne)
- 0° = T-Pose / vollständig offen
- Bereich Hand: [0°, 90°]; Body: asymmetrisch, kein Clip

### Isaac-Konvention (Physics Inspector)
- Entgegengesetzt zu Onshape (JOINT_SIGN = -1)
- Gelenk-Limits nach `set_joint_limits()`: Hand [-90°, 0°], Ellbogen [-90°, 45°], Handgelenk [-90°, 0°]
- Nur in `pickup_keyframes.py` und beim direkten Inspector-Ablesen

### Konvertierung
```python
# Onshape → Isaac (robot_io intern):
isaac_rad = JOINT_SIGN * clip(onshape_deg, 0, 90) * pi/180   # Hand
isaac_deg = JOINT_SIGN * onshape_deg                           # Body (DriveAPI)

# Isaac → Onshape (apply_full_pose):
onshape = -isaac_deg    # für alle Gelenke
```

### Verifizierte Vorzeichen-Referenzen
Aus `test_hand_poses.py` (stabil, getestet):
- `dof_shoulder_horizontal_right: +20` → Arm leicht nach vorne
- `dof_shoulder_vertical_left: -30` → Arm leicht hängend (unter T-Pose)
- `dof_elbow_right: +90` → Ellbogen voll gebeugt
- `dof_shoulder_horizontal_left: -90` → linker Arm nach vorne (gespiegelte Achse!)

## Namenskonventionen

### DOF-Namen
Schema: `dof_{teil}_{seite}_{position}`
- Beispiele: `dof_index_left_proximal`, `dof_shoulder_vertical_right`, `dof_thumb_left_rotator`
- Seite: `left` / `right`; Position: `proximal` / `distal` / `tip` / `rotator` / `vertical` / `horizontal`
- Nie erfinden — immer aus `inventory.py` oder `pib_hand_config.py`

### Python-Dateien
- `isaac_sim/` — alles was Isaac Sim braucht (Script Editor oder Standalone)
- `config/` — reine Daten/Konfiguration, keine Isaac-Imports
- `control/` — Isaac-unabhängige Kontroll-Logik
- Prefix `_` für interne Hilfsfunktionen: `_to_isaac_rad()`, `_load_mod()`

### Pose-Dicts
- Schlüssel: exakter DOF-Name aus pib_hand_config
- Wert: Grad (float), in der Konvention der jeweiligen Datei
- Vollständige Dicts (alle 44 DOFs) für Keyframes; Teilmengen für Updates

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

### Simulation-Loop
```python
# Script Editor:
await app.next_update_async()

# Standalone:
sim_app.update()
```

### Script Editor vs. Standalone
```python
_lh = sys.modules.get("_launch_helper")
_STANDALONE = _lh is not None
```

## Commit-Konventionen
- Keine automatischen Commits — Leon schaut erst drüber
- Uncommitted: `config/pickup_keyframes.py`, `isaac_sim/build_scene.py`, `isaac_sim/demo_pickup.py` (seit Umbau)
