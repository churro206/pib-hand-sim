# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-06-22

### Zuletzt gearbeitet an
1. **Limit-Fix**: `fix_joint_limits` (Toggle, unzuverlässig wegen USD Custom-Data) → `set_joint_limits` (direkte Zielwerte, idempotent) in `setup_stage.py`
2. **Vorzeichen-Fix** in `poses_pickup.py`: `dof_head_vertical` (neg→pos), `dof_shoulder_horizontal_left` (pos→neg, gespiegelte Achse)
3. **Neue Demo-Architektur**: `config/pickup_keyframes.py` (Isaac-Konvention, 4 Keyframes vom User validiert), `robot_io.apply_full_pose()`, `demo_pickup.py` neugeschrieben
4. **✅ Demo erfolgreich**: Roboter hat die Dose vom Tisch ausgehoben — Pickup-Sequenz funktioniert
5. **Context-Management-System**: CLAUDE.md (54 Zeilen), docs/ (5 Dateien), .claude/commands/ (3 Slash-Commands)
6. **Timing-Anpassung**: `pickup_keyframes.py` — lift-Step `transition_s` von 2.0 → 0.5 (vom User direkt bearbeitet)

### Offene Punkte
- Uncommitted: `config/pickup_keyframes.py`, `isaac_sim/build_scene.py`, `isaac_sim/demo_pickup.py`, `isaac_sim/setup_stage.py`
- `poses_pickup.py` veraltet — durch `pickup_keyframes.py` ersetzt, noch nicht gelöscht
- Keine Startroutine vorhanden (Sprint-2-Task)
- `isaac_sim/_deprecated/` noch nicht aufgeräumt

### Nächste Schritte (in Reihenfolge)
1. Commit der funktionierenden Demo (`pickup_keyframes.py`, `build_scene.py`, `demo_pickup.py`, `setup_stage.py`)
2. `poses_pickup.py` entfernen + `isaac_sim/_deprecated/` aufräumen
3. `isaac_sim/start.py` schreiben — bündelt `configure_physics_scene`, `configure_drives`, `set_joint_limits`, `set_initial_pose`
4. Control-Architektur: `control/base.py` ABC, `control/direct.py` pass-through, `control/servo.py` Interface anpassen

### Wichtige Kontextdetails
- Keyframes in `pickup_keyframes.py`: **Isaac-Konvention** — `apply_full_pose()` negiert intern vor `set_all_targets()`
- `set_all_targets()` erwartet **Onshape-Konvention** (positiv = Flexion/Heben/Vorne), wie `test_hand_poses.py`
- Linke Schulter horizontal: **negativ = nach vorne** (gespiegelte Achse zur rechten Seite — verifiziert)
- Greifwinkel der Demo: `_G = -33.3°` Isaac-Konvention für alle Finger → funktioniert für Dose
- LSTM in `models/` hat nur synthetische Daten — nicht produktionsreif, Phase 3
