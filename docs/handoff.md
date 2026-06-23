# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-06-23

### Zuletzt gearbeitet an
1. **`runner.py` Bug fixes** — `MODE_NAME = "servo"` für `tendon`-Sequenz (war `"direct"` → unbekannte DOF-Keys); Robot-Re-Initialisierungs-Bug: `_robot.initialize()` wurde bei jedem Script-Editor-Run aufgerufen → Fix via `sys.modules["_runner_robot_initialized"]`-Flag, läuft jetzt nur beim ersten Run
2. **Hot-Reload bestätigt** — nach dem Fix lädt runner.py `sequences.py` bei jedem Re-Run frisch (kein Isaac-Neustart nötig); `_load_mod` + sys.modules-Flag ermöglicht das
3. **`manual_control_hand.py` gelöscht** — kein Importeur, vollständig durch robot_io + control/ + runner ersetzt
4. **Alle Docs aktualisiert** — `CLAUDE.md` Schlüsseldateien + Phasen, `architecture.md` Layer-Status + Datenfluss + Modul-Tabelle, `decisions.md` ADR-003 neu geschrieben (Einweg-Modell), `conventions.md` pickup_keyframes-Referenzen entfernt, `current-sprint.md` Sprint 2 als ✓ abgeschlossen

### Offene Punkte
- Commit steht noch aus — alle Änderungen (control/, sequences.py, runner.py, start.py, gelöschte Dateien, Docs) sind uncommitted
- Pickup-Lift-Step noch nicht visuell in Isaac verifiziert: `dof_elbow_right: 55.4` (Isaac-Inspector war `-55.4` → nach `_isaac()`-Negierung = `+55.4` Onshape)
- P3 (collect_data.py vs. data/collect_real.py Zuständigkeiten) noch offen, kein Blocker für Sprint 3

### Nächste Schritte (in Reihenfolge)
1. Commit: `git add config/sequences.py control/ isaac_sim/runner.py isaac_sim/start.py` + deletions + docs, dann pushen
2. Pickup-Sequenz in Isaac abspielen, Lift-Step visuell prüfen (`SEQUENCE_NAME = "pickup"`, `MODE_NAME = "direct"`)
3. Sprint 3 beginnen: `get_robot_state()` in robot_io, dann Observation API

### Wichtige Kontextdetails
- **Hot-Reload-Pattern:** `sys.modules["_runner_robot_initialized"]` überlebt zwischen Script-Editor-Runs innerhalb einer Isaac-Session — wird als einmaliger Init-Flag verwendet. Bei Isaac-Neustart wird er automatisch geleert.
- **Sequenz-Kompatibilität:** `hand_poses` → `direct`; `tendon` → `servo` + `SIDE="right"`; `pickup` → `direct`. Falsche Kombination gibt DOF-Fehler.
- **`_load_mod` + control/ als synthetisches Paket:** `sys.modules["control"]` wird in runner.py als `types.ModuleType` angelegt, damit `from control.base import ControlMode` in servo.py etc. funktioniert — nicht über normales `import control` erreichbar in Isaac.
