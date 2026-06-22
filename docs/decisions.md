# Architektur-Entscheidungen

Format: Problem → Entscheidung → Begründung → Konsequenzen

---

## ADR-001: JOINT_SIGN statt Onshape-Achsen-Fix

**Problem**: Onshape und Isaac Sim haben invertierte Drehachsen für alle Gelenke.

**Entscheidung**: Konstante `JOINT_SIGN = -1` in `pib_hand_config.py`, Kompensation ausschließlich in `robot_io.py`.

**Begründung**: Onshape-Modell nicht anfassen (3D-Druck-Workflow bricht). Eine zentrale Stelle ist besser wartbar als verteilte Negierungen.

**Konsequenzen**: Alle Steuer-Skripte schreiben in Onshape-Konvention. Nur `apply_full_pose` (für Physics-Inspector-Werte) negiert explizit.

---

## ADR-002: set_joint_limits statt fix_joint_limits

**Problem**: `fix_joint_limits` invertierte Limits per Toggle (old_lower ↔ -old_upper). USD Custom-Data-Flag wurde nicht zuverlässig persistiert → Doppel-Inversion bei jedem Session-Start möglich.

**Entscheidung**: Ersetzt durch `set_joint_limits()` das Zielwerte direkt setzt (Hand: [-90°, 0°], Ellbogen: [-90°, 45°], etc.).

**Begründung**: Direktes Setzen ist idempotent ohne Flag-Mechanismus. Mehrfaches Aufrufen ist harmlos.

**Konsequenzen**: Werte in `_BODY_LIMITS_ISAAC` dict hardcoded. Bei neuen Gelenken dort eintragen.

---

## ADR-003: Zwei Pose-Konventionen (pickup_keyframes vs. set_all_targets)

**Problem**: Physics-Inspector-Werte (Isaac-Konvention) vs. Code-Konvention (Onshape). Keyframes kommen direkt aus dem Inspector.

**Entscheidung**: `pickup_keyframes.py` speichert Isaac-Konvention. `apply_full_pose()` negiert intern bevor es `set_all_targets()` aufruft.

**Begründung**: Validierte Inspector-Werte nicht umrechnen müssen. Kein Risiko von Tippfehlern bei der manuellen Negierung.

**Konsequenzen**: Zwei "Eingabe-Wege" nach robot_io. Neue Posen in pickup_keyframes: Inspector-Werte direkt. Neue Posen via Code: Onshape-Konvention für set_all_targets.

---

## ADR-004: _launch_helper.py als Standalone-Pattern

**Problem**: Isaac Sim erfordert SimulationApp als erste Initialisierung, danach erst andere Imports.

**Entscheidung**: `_launch_helper.py` kapselt App-Init, USD-Laden, robot_io-Init. Zielmodule werden via `run()` aufgerufen. `lh.sim_app` und `lh.robot` sind globale Handles.

**Konsequenzen**: Jedes neue Standalone-Skript braucht nur `run()` implementieren. Script-Editor-Skripte müssen selbst robot initialisieren (kein _launch_helper).

---

## Template für neue Entscheidungen

**Problem**: [Was ist das konkrete Problem oder der Trade-off?]

**Entscheidung**: [Was wurde entschieden?]

**Begründung**: [Warum diese Option?]

**Konsequenzen**: [Was ändert sich, was muss beachtet werden?]
