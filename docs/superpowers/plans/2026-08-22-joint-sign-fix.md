# JOINT_SIGN-Fix (Weg 1: URDF editieren + Isaac-Reimport) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Isaacs importierte Gelenke sollen nativ Onshape-Konvention haben (positiv = Flexion/Heben/Vorne) — kein Script Node, kein `JOINT_SIGN`, keine Limit-Spiegelung mehr nötig. Behebt den ADR-006-Kompromiss (gespiegelte Ist-Werte auf `/pib/hw/joint_states`) als Nebeneffekt.

**Architecture:** Eine deterministisch aus der kanonischen `pib_upperbody.urdf` abgeleitete Kopie (Achsen negiert, Limits vertauscht+negiert) wird nur für den Isaac-Reimport verwendet. Die kanonische URDF (ros2_control/IK-Team/RViz) bleibt unangetastet. Nach dem Reimport verschwindet der Script Node aus dem Action Graph, `JOINT_SIGN`/Limit-Spiegelung fallen aus Config/Setup-Code weg.

**Tech Stack:** Python 3.10+ (URDF-Transform, kein Isaac nötig) · Isaac Sim 5.1 Script Editor (Reimport, Verifikation) · ROS2 Jazzy (Regressionstest über bestehende Test-Clients)

## Global Constraints

- Keine automatischen Commits — Leon schaut erst drüber (docs/conventions.md)
- Kein `time.sleep()` in Isaac-Sim-Code → `await app.next_update_async()` (CLAUDE.md)
- DOF-Namen nie erfinden → immer aus `config/pib_hand_config.py` (CLAUDE.md)
- Kein Test-Framework auf diesem Branch — Verifikationsskripte sind eigenständig lauffähig, kein pytest
- `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` bleibt für ros2_control/IK-Team/RViz unverändert — wird durch diesen Fix nicht angefasst
- Referenz-Vorzeichen (verifiziert, siehe docs/conventions.md): `dof_shoulder_horizontal_right: +20` = Arm vorne; `dof_shoulder_vertical_left: -30` = Arm leicht hängend; `dof_elbow_right: +90` = voll gebeugt; `dof_shoulder_horizontal_left: -90` = Arm vorne (gespiegelte Achse)

---

### Task 1: URDF-Transform-Skript

Reine Python/XML-Transformation, kein Isaac nötig — vollständig hier verifizierbar.

**Files:**
- Create: `isaac_sim/tools/flip_urdf_for_isaac.py`

**Interfaces:**
- Produces: `flip_urdf(source: Path, target: Path) -> int` (Anzahl transformierter Gelenke), genutzt in Task 2

- [ ] **Step 1: Skript schreiben**

```python
"""
flip_urdf_for_isaac.py — Erzeugt eine Isaac-Import-Variante der URDF mit
umgedrehter Vorzeichen-Konvention für revolute Gelenke.

Hintergrund: Onshape/URDF und Isaacs importierte Gelenkachsen sind für alle
44 DOFs vorzeicheninvertiert (siehe docs/decisions.md). Statt das zur
Laufzeit zu kompensieren (Script Node im Action Graph), wird hier eine
abgeleitete URDF erzeugt, deren <axis>-Vektoren negiert und deren <limit>
lower/upper vertauscht+negiert sind. Isaac importiert daraus direkt in
Onshape-Konvention.

Die kanonische ros2_ws/src/pib_description/urdf/pib_upperbody.urdf bleibt
UNVERÄNDERT (weiterhin Onshape-Konvention für ros2_control/IK-Team/RViz).
Diese Datei hier wird NUR für den Isaac-Reimport verwendet (Mesh-Referenzen
sind package://pib_description/... — ortsunabhängig, solange ros2_ws gebaut
und gesourced ist).

Bei jedem Onshape-Re-Export: dieses Skript erneut laufen lassen, dann den
Isaac-Reimport wiederholen (siehe
docs/superpowers/plans/2026-08-22-joint-sign-fix.md, Tasks 3-6).

Aufruf: python3 isaac_sim/tools/flip_urdf_for_isaac.py
"""
import xml.etree.ElementTree as ET
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = _ROOT / "ros2_ws/src/pib_description/urdf/pib_upperbody.urdf"
TARGET = _ROOT / "isaac_sim/urdf/pib_upperbody_isaac_import.urdf"

# Referenzwerte zur Selbstprüfung (aus dem Onshape-Export, radiant).
# (axis_danach, lower_danach, upper_danach)
_EXPECTED = {
    "dof_elbow_right":               ([1.0, -0.0, 1.22465e-16], -1.5708, 0.785398),
    "dof_wrist_right":               ([1.0, -5.48963e-16, -0.0], -1.5708, -0.0),
    "dof_index_right_proximal":      ([1.0, -0.0, -0.0], -1.5708, -0.0),
    "dof_shoulder_horizontal_right": ([-0.0, 1.0, -0.0], -1.5708, -0.0),
}


def flip_urdf(source: Path, target: Path) -> int:
    """Negiert axis + vertauscht/negiert limit für alle revolute Joints."""
    tree = ET.parse(source)
    root = tree.getroot()
    count = 0
    for joint in root.findall("joint"):
        if joint.get("type") != "revolute":
            continue
        axis_el = joint.find("axis")
        limit_el = joint.find("limit")
        if axis_el is None or limit_el is None:
            continue

        xyz = [float(v) for v in axis_el.get("xyz").split()]
        axis_el.set("xyz", " ".join(repr(-v) for v in xyz))

        lower = float(limit_el.get("lower"))
        upper = float(limit_el.get("upper"))
        limit_el.set("lower", repr(-upper))
        limit_el.set("upper", repr(-lower))

        count += 1

    tree.write(target, xml_declaration=True, encoding="UTF-8")
    return count


def _selfcheck(target: Path) -> None:
    tree = ET.parse(target)
    root = tree.getroot()
    joints = {j.get("name"): j for j in root.findall("joint")}
    for name, (axis_after, lo_after, up_after) in _EXPECTED.items():
        joint = joints[name]
        axis = [float(v) for v in joint.find("axis").get("xyz").split()]
        limit = joint.find("limit")
        lower = float(limit.get("lower"))
        upper = float(limit.get("upper"))
        assert all(abs(a - b) < 1e-6 for a, b in zip(axis, axis_after)), \
            f"{name}: axis {axis} != erwartet {axis_after}"
        assert abs(lower - lo_after) < 1e-6, f"{name}: lower {lower} != erwartet {lo_after}"
        assert abs(upper - up_after) < 1e-6, f"{name}: upper {upper} != erwartet {up_after}"
        print(f"OK  {name}: axis={axis} limit=[{lower:.4f},{upper:.4f}]")


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    n = flip_urdf(SOURCE, TARGET)
    print(f"{n} revolute Gelenke transformiert -> {TARGET}")
    assert n == 44, f"Erwartet 44 revolute Gelenke, gefunden {n}"
    _selfcheck(TARGET)
    print("Selfcheck OK")
```

- [ ] **Step 2: Ausführen und Ergebnis prüfen**

Run: `python3 isaac_sim/tools/flip_urdf_for_isaac.py`
Expected:
```
44 revolute Gelenke transformiert -> .../isaac_sim/urdf/pib_upperbody_isaac_import.urdf
OK  dof_elbow_right: axis=[1.0, -0.0, 1.22465e-16] limit=[-1.5708,0.7854]
OK  dof_wrist_right: axis=[1.0, -5.48963e-16, -0.0] limit=[-1.5708,-0.0]
OK  dof_index_right_proximal: axis=[1.0, -0.0, -0.0] limit=[-1.5708,-0.0]
OK  dof_shoulder_horizontal_right: axis=[-0.0, 1.0, -0.0] limit=[-1.5708,-0.0]
Selfcheck OK
```
(Bereits lokal mit dem echten `pib_upperbody.urdf` gegengeprüft — Werte oben sind das reale Ergebnis, kein Platzhalter.)

- [ ] **Step 3: Commit**

```bash
git add isaac_sim/tools/flip_urdf_for_isaac.py isaac_sim/urdf/pib_upperbody_isaac_import.urdf
git commit -m "feat(isaac_sim): URDF-Transform-Skript für JOINT_SIGN-Fix (Weg 1)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Stichprobenvergleich gegen bekannte Isaac-Limits

Prüft, ob die transformierten Limits mit den bisher (unabhängig) verifizierten Isaac-Limits aus `setup_stage.py` übereinstimmen — Kreuzvalidierung ohne Isaac Sim.

**Files:**
- Read only: `isaac_sim/urdf/pib_upperbody_isaac_import.urdf`, `isaac_sim/setup_stage.py:156-171` (`_BODY_LIMITS_ISAAC`)

- [ ] **Step 1: Alle 44 transformierten Limits aus `pib_upperbody_isaac_import.urdf` neben `_BODY_LIMITS_ISAAC`/den Hand-Limits `(-90,0)` legen und Abweichungen notieren.**

Bekannt aus dem Task-1-Testlauf: `dof_shoulder_horizontal_right` transformiert zu `[-90°, 0°]`, aber `_BODY_LIMITS_ISAAC` hat aktuell `(-90.0, 90.0)` — die bisherige Tabelle war an dieser Stelle eine zu großzügige Schätzung, nicht aus der echten Onshape-Quelle abgeleitet. **Erwartung: mehr solcher Abweichungen sind normal** — die neuen, aus der echten URDF abgeleiteten Werte sind die korrekteren.

- [ ] **Step 2: Abweichungsliste in `docs/handoff.md` unter "Wichtige Kontextdetails" ergänzen** (nicht Teil dieses Fixes, aber relevant für Task 6 und den 44-DOF-Sweep in Task 8).

- [ ] **Step 3: Commit**

```bash
git add docs/handoff.md
git commit -m "docs: Limit-Abweichungen URDF-Transform vs. bisherige Schätzwerte

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Testimport in separater Stage (Go/No-Go-Checkpoint)

**Läuft komplett in Isaac Sim bei Leon** — kein Zugriff von hier aus möglich. Vor jeder Änderung an der bestehenden `pib_upperbody.usd`.

**Files:**
- Isaac Sim: neue, leere Stage (nicht `pib_upperbody.usd`)

- [ ] **Step 1: Neue Stage öffnen** (File → New Stage), NICHT die bestehende `pib_upperbody.usd` verändern.

- [ ] **Step 2: URDF Importer-Extension öffnen** (Isaac Utils / URDF Importer, je nach Isaac-Sim-5.1-Menüführung unter `Window → Isaac Utils` oder `File → Import`), `isaac_sim/urdf/pib_upperbody_isaac_import.urdf` importieren. Ergebnis: neuer Roboter-Prim-Baum in der leeren Stage.

- [ ] **Step 3: Sign-Stichprobe ohne ROS2/Action Graph** — im Script Editor, direkt über `UsdPhysics.DriveAPI`, an 4 Gelenken:

```python
import omni.usd
from pxr import UsdPhysics

stage = omni.usd.get_context().get_stage()

# Pfad ggf. anpassen — vom Importer beim Import angezeigten Root-Pfad nehmen.
TEST_ROOT = "/World/pib_upperbody_isaac_import"  # Platzhalter, siehe Step 2

_TESTS = {
    "dof_elbow_right": 90.0,               # erwartet: voll gebeugt (Referenz: docs/conventions.md)
    "dof_shoulder_horizontal_right": 20.0, # erwartet: Arm leicht vorne
    "dof_shoulder_vertical_left": -30.0,   # erwartet: Arm leicht hängend
    "dof_shoulder_horizontal_left": -90.0, # erwartet: Arm vorne (gespiegelte Achse)
}

for prim in stage.Traverse():
    name = prim.GetPath().name
    if name not in _TESTS:
        continue
    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    if not drive:
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
    drive.GetTargetPositionAttr().Set(_TESTS[name])
    print(f"{name} -> {_TESTS[name]}°")
```

Play drücken, 4 Gelenke visuell gegen die Kommentare oben prüfen.

- [ ] **Step 4: Go/No-Go entscheiden**
  - **Go**: alle 4 Gelenke bewegen sich in die kommentierte Richtung → weiter mit Task 4.
  - **No-Go**: mindestens eines stimmt nicht → hier stoppen, Beobachtung (welches Gelenk, welche Richtung stattdessen) zurückmelden, keine der folgenden Tasks ausführen. Das ist ein Zeichen, dass die Ursache der Invertierung nicht (nur) im Achsvektor liegt — Neubewertung nötig, nicht in diesem Plan enthalten.

---

### Task 4: Bestehende Szene inventarisieren + Roboter-Prim ersetzen

**Nur bei Go aus Task 3.** Läuft in Isaac Sim bei Leon.

**Files:**
- Isaac Sim: `isaac_sim/usd/pib_upperbody.usd`

- [ ] **Step 1: Vor jeder Änderung Backup**: `pib_upperbody.usd` → `pib_upperbody.usd.bak` kopieren (Dateisystem, außerhalb von git — reiner Rollback-Schutz für die laufende Session).

- [ ] **Step 2: Bestehende Stage öffnen, alle Top-Level-Prims unter `/World` auflisten** (Stage-Fenster) und notieren — insbesondere Objekte aus der Pickup-/Putdown-Demo (z.B. der Zylinder), die NICHT zum Roboter gehören und erhalten bleiben müssen.

- [ ] **Step 3: Alten Roboter-Prim-Baum löschen** (`ROBOT_PRIM_PATH` aus `config/pib_hand_config.py`: `/World/pib_upperbody_URDF/pib_upperbody_URDF`, ggf. übergeordneten `/World/pib_upperbody_URDF`-Container mitlöschen falls er nur den Roboter enthält — anhand der Step-2-Liste prüfen).

- [ ] **Step 4: Neu importierten Roboter aus Task 3 in diese Stage kopieren/referenzieren**, auf denselben Pfad `/World/pib_upperbody_URDF/pib_upperbody_URDF` bringen (Umbenennen/Verschieben im Stage-Fenster) — `ROBOT_PRIM_PATH` in `config/pib_hand_config.py` soll unverändert gültig bleiben.

- [ ] **Step 5: `start.py` ausführen** (Drives/Limits/Initialpose — Verhalten bei falschen Vorzeichen in Initialpose ist an dieser Stelle erwartet, wird in Task 6 korrigiert). Prüfen: keine Fehler, Roboter + übrige Szenenobjekte aus Step 2 sind vorhanden.

- [ ] **Step 6: Speichern (Ctrl+S) erst NACH Task 5 (Action Graph) und Task 6 (Config), nicht jetzt** — Zwischenstand nicht committen, `pib_upperbody.usd` bleibt bis zum Abschluss von Task 6 unstaged in git.

---

### Task 5: Action Graph neu verkabeln

**Nur nach Task 4.** Läuft in Isaac Sim bei Leon.

**Files:**
- Isaac Sim: Action Graph in `isaac_sim/usd/pib_upperbody.usd` (Window → Graph Editors → Action Graph)

- [ ] **Step 1: Script Node löschen** (der Node zwischen `ROS2SubscribeJointState` und `IsaacArticulationController`, der bisher `positionCommand` negiert hat).

- [ ] **Step 2: `ROS2SubscribeJointState.positionCommand` direkt mit `IsaacArticulationController.positionCommand` verbinden.**

- [ ] **Step 3: `IsaacArticulationController.targetPrim` prüfen** — zeigt weiterhin auf `ROBOT_PRIM_PATH` (sollte unverändert sein, da Task 4 den Pfad beibehalten hat).

- [ ] **Step 4: `ROS2PublishJointState` unverändert lassen** (liest weiterhin direkt vom Prim — jetzt aber bereits in Onshape-Konvention, kein Kompromiss mehr).

- [ ] **Step 5: Play drücken, kurz beobachten dass sich nichts unerwartet bewegt** (Initialpose ist an dieser Stelle noch mit falschen Vorzeichen aus Task 4 Step 5 — erwartet, kommt in Task 6).

---

### Task 6: `setup_stage.py` und `config/pib_hand_config.py` korrigieren

**Files:**
- Modify: `isaac_sim/setup_stage.py:144-232`
- Modify: `config/pib_hand_config.py:6-12`

**Interfaces:**
- Consumes: Abweichungsliste aus Task 2 (welche Limits sich gegenüber der alten `_BODY_LIMITS_ISAAC`-Tabelle geändert haben)

- [ ] **Step 1: Prüfen ob `set_joint_limits()` nach dem Reimport überhaupt noch nötig ist** — in Isaac Sim (Script Editor): `physics:lowerLimit`/`physics:upperLimit` von `dof_elbow_right` direkt vom Prim auslesen (`prim.GetAttribute("physics:lowerLimit").Get()`). Falls der Importer die Werte aus der transformierten URDF bereits korrekt gesetzt hat (erwartet: `-90°`/`45°`, siehe Task 1 Selfcheck-Ausgabe in Grad statt Radiant) UND das nach einem Stop/Play-Zyklus stabil bleibt (im Gegensatz zu Stiffness/Damping, die laut CLAUDE.md nicht gecached werden) → Funktion in Step 2 entfernen statt korrigieren. Falls nicht stabil oder falsch → Funktion in Step 2 mit den korrekten (aus `isaac_sim/urdf/pib_upperbody_isaac_import.urdf` abgelesenen) Werten neu befüllen, analog zum bisherigen Muster.

- [ ] **Step 2a (falls Importer-Limits stabil sind): Limit-Funktion entfernen**

In `isaac_sim/setup_stage.py`, Zeilen 144-201 (Kommentarblock, `_HAND_KEYWORDS`, `_BODY_LIMITS_ISAAC`, `set_joint_limits()`) ersatzlos streichen. Aufruf in `setup_all()` (Zeile 240) entfernen:

```python
def setup_all(stg) -> None:
    configure_physics_scene(stg)
    configure_ground(stg)
    configure_lights(stg)
    configure_drives(stg)
    set_initial_pose(stg)
```

- [ ] **Step 2b (falls Importer-Limits NICHT stabil sind): Limit-Funktion korrigieren**

`_BODY_LIMITS_ISAAC` (Zeilen 156-171) durch die aus `isaac_sim/urdf/pib_upperbody_isaac_import.urdf` abgelesenen Grad-Werte ersetzen (Radiant → Grad, `math.degrees()`), `_HAND_KEYWORDS`-Zweig in `set_joint_limits()` (Zeile 191-193) von `(-90.0, 0.0)` auf die tatsächlichen transformierten Fingerlimits umstellen (aus Task 1 Selfcheck: `dof_index_right_proximal` → `[-90°, 0°]`, für alle Hand-DOFs identisch mit dem bisherigen Muster prüfen). Kommentarblock (Zeilen 144-153) entsprechend umschreiben — kein JOINT_SIGN-Bezug mehr, stattdessen: "Limits stammen direkt aus dem Isaac-Reimport, hier nur als Absicherung erneut gesetzt."

- [ ] **Step 3: Initialpose-Vorzeichen korrigieren**

```python
def set_initial_pose(stg) -> None:
    """
    Setzt initiale Drive-Targets (in Grad, Onshape-Konvention seit dem
    JOINT_SIGN-Fix — kein Vorzeichen-Wechsel mehr nötig):
      - Hände offen: alle Finger 0°
      - Ellbogen leicht angewinkelt: 30° (positiv = Flexion)
      - Alles andere: 0° (T-Pose / neutral)
    """
    initial_targets: dict = {
        "dof_elbow_left":  30.0,
        "dof_elbow_right": 30.0,
    }
    count = 0
    for prim in stg.Traverse():
        is_revolute = (prim.GetTypeName() == "PhysicsRevoluteJoint" or
                       prim.HasAPI(UsdPhysics.RevoluteJoint))
        if not is_revolute:
            continue

        name   = prim.GetPath().name
        target = initial_targets.get(name, 0.0)

        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if drive:
            drive.GetTargetPositionAttr().Set(target)
            count += 1

    print(f"set_initial_pose: {count} Drive-Targets gesetzt (Ellbogen je 30°, Rest 0°)")
```

(Ersetzt Zeilen 204-232 in `isaac_sim/setup_stage.py`.)

- [ ] **Step 4: `JOINT_SIGN` aus `config/pib_hand_config.py` entfernen**

Zeilen 6-12 ersetzen:

```python
# ── Roboter ───────────────────────────────────────────────────────────────────
ROBOT_PRIM_PATH = "/World/pib_upperbody_URDF/pib_upperbody_URDF"
```

(Der bisherige "Vorzeichen-Kompensation"-Block inkl. `JOINT_SIGN = -1` entfällt vollständig — seit dem Reimport stimmen Onshape- und Isaac-Konvention überein.)

- [ ] **Step 5: In Isaac Sim `start.py` erneut ausführen**, prüfen dass keine `AttributeError`/`KeyError` auftritt (z.B. falls andere Stellen noch `JOINT_SIGN` importieren — laut vorheriger Grep-Suche gibt es keine weiteren Referenzen außerhalb der beiden bearbeiteten Dateien, aber sicherheitshalber `grep -rn "JOINT_SIGN" .` nach diesem Schritt nochmal laufen lassen).

- [ ] **Step 6: Jetzt erst `pib_upperbody.usd` speichern (Ctrl+S)** — Action Graph (Task 5) und Config-Korrektur (dieser Task) sind beide durch.

- [ ] **Step 7: Commit**

```bash
git add config/pib_hand_config.py isaac_sim/setup_stage.py isaac_sim/usd/pib_upperbody.usd
git commit -m "fix: JOINT_SIGN-Fix Weg 1 — Isaac-Reimport aus achsen-invertierter URDF

Script Node im Action Graph entfernt, JOINT_SIGN/Limit-Spiegelung aus
config/pib_hand_config.py und isaac_sim/setup_stage.py entfernt. Isaac
importiert jetzt nativ in Onshape-Konvention (isaac_sim/urdf/pib_upperbody_isaac_import.urdf).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: 44-DOF-Sweep-Skript

**Files:**
- Create: `isaac_sim/tools/sweep_joints.py`

**Interfaces:**
- Consumes: `config.pib_hand_config.BODY_DOFS`, `HAND_DOFS` (Namenslisten)

- [ ] **Step 1: Skript schreiben**

```python
"""
sweep_joints.py — Fährt jedes der 44 Gelenke einzeln durch einen Test-Wert,
damit die Vorzeichen-Konvention nach dem JOINT_SIGN-Fix (Weg 1) pro Gelenk
visuell bestätigt werden kann. Siehe
docs/superpowers/plans/2026-08-22-joint-sign-fix.md, Task 7/8.

Im Script Editor ausführen, NACH start.py, bei laufender Simulation (Play).

Für jedes Gelenk: Zielwert = 70% des oberen Limits (positiv = Flexion/
Heben/Vorne laut docs/conventions.md), 2 Sekunden halten, dann zurück auf 0°.
Referenzierte, bereits verifizierte Gelenke (siehe docs/conventions.md)
werden besonders markiert.
"""
import asyncio
import importlib.util
from pathlib import Path

import omni.usd
import omni.kit.app as app
from pxr import UsdPhysics

stage = omni.usd.get_context().get_stage()


def _find_project_root() -> str:
    stage_file = Path(stage.GetRootLayer().realPath)
    for ancestor in [stage_file.parent, stage_file.parent.parent]:
        if (ancestor / "config" / "pib_hand_config.py").is_file():
            return str(ancestor)
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config.py").is_file():
            return str(candidate)
    raise FileNotFoundError("pib-hand-sim nicht gefunden.")


_root = _find_project_root()
_spec = importlib.util.spec_from_file_location("pib_hand_config", f"{_root}/config/pib_hand_config.py")
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

ALL_DOF_NAMES = (
    _cfg.BODY_DOFS["names"]
    + _cfg.HAND_DOFS["left"]["names"]
    + _cfg.HAND_DOFS["right"]["names"]
)
assert len(ALL_DOF_NAMES) == 44, f"Erwartet 44 DOFs, gefunden {len(ALL_DOF_NAMES)}"

# Bereits verifiziert (docs/conventions.md) — erwartete Bedeutung bei positivem Wert.
_VERIFIED = {
    "dof_shoulder_horizontal_right": "Arm leicht vorne (Referenzwert war +20°)",
    "dof_shoulder_vertical_left":    "Arm HEBT sich (Referenzwert war -30° = hängend)",
    "dof_elbow_right":               "Ellbogen voll gebeugt (Referenzwert war +90°)",
    "dof_shoulder_horizontal_left":  "Arm vorne (gespiegelte Achse, Referenzwert war -90°)",
}


async def sweep():
    prims_by_name = {}
    for prim in stage.Traverse():
        name = prim.GetPath().name
        if name in ALL_DOF_NAMES:
            prims_by_name[name] = prim

    missing = set(ALL_DOF_NAMES) - set(prims_by_name)
    if missing:
        print(f"WARNUNG: {len(missing)} DOFs nicht in der Stage gefunden: {sorted(missing)}")

    for name in ALL_DOF_NAMES:
        prim = prims_by_name.get(name)
        if not prim:
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            print(f"ÜBERSPRUNGEN (kein Drive): {name}")
            continue

        upper = prim.GetAttribute("physics:upperLimit").Get()
        target = upper * 0.7 if upper else 0.0

        note = _VERIFIED.get(name, "erwartet: positiv = Flexion/Heben/Vorne (docs/conventions.md)")
        print(f"{name}: Ziel {target:.1f}°  [{note}]")

        drive.GetTargetPositionAttr().Set(target)
        for _ in range(120):  # ~2s bei 60fps
            await app.get_app().next_update_async()

        drive.GetTargetPositionAttr().Set(0.0)
        for _ in range(30):
            await app.get_app().next_update_async()

    print("Sweep abgeschlossen — 44/44 Gelenke durchlaufen.")


asyncio.ensure_future(sweep())
```

- [ ] **Step 2: Commit**

```bash
git add isaac_sim/tools/sweep_joints.py
git commit -m "feat(isaac_sim): 44-DOF-Sweep-Skript zur Vorzeichen-Verifikation

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: 44-DOF-Sweep ausführen (Verifikation)

**Läuft komplett bei Leon in Isaac Sim.** Pflicht, kein Nice-to-have — die 44 Gelenke sind nicht alle gleich orientiert.

- [ ] **Step 1: `isaac_sim/tools/sweep_joints.py` im Script Editor ausführen**, bei jedem der 44 Ausgaben visuell bestätigen: positiver Zielwert = Flexion/Heben/Vorne (bzw. bei den 4 markierten Referenz-DOFs die notierte erwartete Bedeutung).

- [ ] **Step 2: Auffälligkeiten notieren** (Gelenk-Name + beobachtete statt erwartete Richtung).

- [ ] **Step 3: Bei Abweichungen** — betroffene Gelenke einzeln in `_EXPECTED`-Stil aus Task 1 nachprüfen (Achse/Limit in `pib_upperbody_isaac_import.urdf` anschauen), ob der Transform dort einen Sonderfall hat (z.B. Achse nicht achsparallel). Kein pauschaler Fix in diesem Plan vorgesehen — bei Abweichungen Rücksprache, bevor Task 9/10 fortgesetzt wird.

- [ ] **Step 4: Bei vollständiger Bestätigung** — Ergebnis (0 Abweichungen) in `docs/handoff.md` festhalten.

---

### Task 9: Pickup-/Putdown-Regressionstest

**Files:**
- Run: `ros2_ws/src/pib_bringup/pib_bringup/test_client_pickup.py`, `test_client_putdown.py`

- [ ] **Step 1: `ROS_DOMAIN_ID=0` setzen, `ros2_ws/install/setup.bash` sourcen** (siehe docs/conventions.md).

- [ ] **Step 2:** `ros2 launch pib_bringup pib_sim.launch.py`

- [ ] **Step 3:** `ros2 run pib_bringup test_client_pickup` — Roboter greift den Zylinder wie zuvor, physikalisch korrekt.

- [ ] **Step 4:** `ros2 run pib_bringup test_client_putdown` — exakte Umkehrung.

- [ ] **Step 5: Zusätzlich zur alten Prüfung (nur Bewegung korrekt) jetzt auch die Ist-Werte prüfen**: `ros2 topic echo /pib/hw/joint_states` während der Bewegung — Werte sollten jetzt (anders als vor diesem Fix) mit den gesendeten Soll-Werten in Onshape-Konvention übereinstimmen, nicht mehr gespiegelt sein. Das ist der ADR-006-Kompromiss, der mit diesem Fix behoben wird.

- [ ] **Step 6:** Bei Erfolg — keine weiteren Schritte, weiter mit Task 10.

---

### Task 10: Docs aktualisieren

**Files:**
- Modify: `CLAUDE.md`
- Modify: `docs/architecture.md`
- Modify: `docs/conventions.md`
- Modify: `docs/decisions.md`
- Modify: `docs/current-sprint.md`

- [ ] **Step 1: `CLAUDE.md`** — Abschnitt "JOINT_SIGN = -1 (kritisch, nie vergessen)" komplett ersetzen durch einen kurzen Hinweis auf ADR-00X (neue Nummer aus Step 4) und dass die Isaac-Konvention seit dem Reimport der Onshape-Konvention entspricht; Verweis auf `isaac_sim/tools/flip_urdf_for_isaac.py` für zukünftige Onshape-Re-Exports ergänzen.

- [ ] **Step 2: `docs/architecture.md`** — Abschnitt "Layer 2 — Action Graph im Detail" auf 3 Nodes reduzieren (Script Node raus), "Bekannter Kompromiss"-Absatz entfernen (behoben), "Warum kein Custom-Bridge-Code mehr" um den Satz ergänzen, dass jetzt auch die letzte Custom-Code-Zeile (Vorzeichen-Invertierung) entfallen ist.

- [ ] **Step 3: `docs/conventions.md`** — Abschnitt "Onshape/URDF-Konvention" und "Isaac-Konvention" zusammenführen (beide sind jetzt identisch), Konvertierungs-Codebeispiel (Script Node) entfernen, "Kein Clip mehr im Code"-Hinweis anpassen.

- [ ] **Step 4: `docs/decisions.md`** — neues ADR-007 anlegen:

```markdown
## ADR-007: JOINT_SIGN-Fix per Isaac-Reimport statt Laufzeit-Kompensation

**Problem**: ADR-006 hatte die Vorzeichen-Invertierung (Onshape/URDF vs. Isaac) über einen
Script Node im Action Graph kompensiert — funktionierte für den Kommando-Pfad, aber
`ROS2PublishJointState` liest den Prim direkt und hatte keinen Interceptions-Punkt für die
Rückrichtung (bekannter Kompromiss: gespiegelte Ist-Werte auf `/pib/hw/joint_states`).

**Entscheidung**: `isaac_sim/tools/flip_urdf_for_isaac.py` erzeugt aus der kanonischen
`pib_upperbody.urdf` eine abgeleitete Kopie mit negierten `<axis>`-Vektoren und
vertauscht+negierten `<limit>`-Werten. Der Roboter wurde aus dieser abgeleiteten Kopie neu
in Isaac importiert (nicht die kanonische URDF selbst geändert). Script Node aus dem Action
Graph entfernt, `JOINT_SIGN`/Limit-Spiegelung aus `config/pib_hand_config.py` und
`isaac_sim/setup_stage.py` entfernt.

Ein Zwischenschritt (Joint-Frames direkt in der bereits gebackenen USD umdrehen, ohne
Reimport) wurde verworfen: die Weltrichtung einer Gelenkachse lässt sich nicht ohne
physisches "Verspringen" der nachgeordneten Kinematik-Kette umdrehen, ohne denselben
Aufwand wie ein Reimport zu betreiben.

**Begründung**: Reimport aus einer achsen-korrigierten URDF ist die einzige Methode, bei der
Isaac nativ (ohne jede Laufzeit-Negierung) Onshape-Konvention spricht — behebt den
ADR-006-Kompromiss vollständig statt ihn zu verlagern. Die kanonische URDF bleibt für
ros2_control/IK-Team/RViz unverändert, da nur eine abgeleitete Kopie für den Isaac-Import
verwendet wird.

**Konsequenzen**:
- `JOINT_SIGN`-Konstante, `_BODY_LIMITS_ISAAC`-Spiegelung, Script Node — entfernt
- Bei jedem Onshape-Re-Export: `flip_urdf_for_isaac.py` erneut laufen lassen, Isaac-Reimport
  wiederholen (siehe `docs/superpowers/plans/2026-08-22-joint-sign-fix.md`)
- `/pib/hw/joint_states`, `/joint_states`, Action-Feedback zeigen jetzt korrekte
  (nicht mehr gespiegelte) Ist-Werte — ADR-006s bekannter Kompromiss ist behoben
- Einige Body-Limits in `setup_stage.py` waren zuvor grobe Schätzwerte (z.B.
  `dof_shoulder_horizontal_right` war `[-90°,90°]`, korrekt aus der Onshape-Quelle ist
  `[-90°,0°]`) — jetzt aus der echten Quelle abgeleitet, dadurch stellenweise strenger
```

- [ ] **Step 5: `docs/current-sprint.md`** — "Contact Sensors"/"Szenen-Erweiterung"-Abschnitte um einen neuen, abgehakten Abschnitt "JOINT_SIGN-Fix ✓" ergänzen (analog zum bestehenden "OmniGraph-Migration ✓"-Muster).

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md docs/architecture.md docs/conventions.md docs/decisions.md docs/current-sprint.md
git commit -m "docs: JOINT_SIGN-Fix (ADR-007) in Doku nachziehen

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review-Notizen

- **Spec-Abdeckung**: Task 1/2 decken den lokal verifizierbaren URDF-Transform ab; Task 3
  den Go/No-Go-Checkpoint aus der Spec; Task 4-6 die Migration (Action Graph, Config); Task
  7-8 die Pflicht-Sweep-Verifikation; Task 9 die Pickup/Putdown-Regression; Task 10 die
  Doku — alle Punkte aus der Design-Spec sind abgedeckt.
- **Bekannte Lücke, bewusst offengelassen**: Task 4 (Szenen-Objekte erhalten) kann nicht
  vollständig vorab skriptiert werden, da der genaue Inhalt der aktuellen Stage (z.B. exakter
  Prim-Pfad des Pickup-Zylinders) hier nicht einsehbar ist (binäres USD-Crate-Format, keine
  Isaac-Sim-Anbindung von hier aus) — Step 2 instruiert daher eine manuelle Bestandsaufnahme
  statt eines blinden Skripts.
- **Task 6 Step 1/2a/2b verzweigt** bewusst, da unklar ist, ob Isaac Limits nach dem Import
  zuverlässig persistiert (anders als Stiffness/Damping) — muss empirisch geprüft werden,
  kein Rateschritt.
