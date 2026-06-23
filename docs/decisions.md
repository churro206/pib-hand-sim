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

## ADR-003: Einheitlicher Einweg nach set_all_targets via _isaac()-Helper

**Problem**: Früher zwei Eingabewege nach robot_io (`apply_full_pose` für Inspector-Werte, `set_all_targets` für Onshape-Werte). Erhöhte kognitive Last; `pickup_keyframes.py` war nur für `apply_full_pose` zugänglich.

**Entscheidung**: `pickup_keyframes.py` gelöscht. Inspector-Werte werden einmalig beim Laden mit `_isaac(d)` negiert und in `config/sequences.py` als Onshape-Konvention gespeichert. Alle Sequenzen laufen über `set_all_targets()`. `apply_full_pose()` bleibt in robot_io als Hilfsfunktion für manuelle Script-Editor-Tests.

**Begründung**: Ein einziger Weg nach Isaac ist wartbarer. `_load_mod` in runner.py lädt sequences.py bei jedem Run neu — Sequenzänderungen ohne Isaac-Neustart möglich.

**Konsequenzen**: Neue Sequenzen immer in Onshape-Konvention schreiben. Inspector-Werte beim Einfügen mit `_isaac({...})` wrappen.

---

## ADR-004: _launch_helper.py als Standalone-Pattern

**Problem**: Isaac Sim erfordert SimulationApp als erste Initialisierung, danach erst andere Imports.

**Entscheidung**: `_launch_helper.py` kapselt App-Init, USD-Laden, robot_io-Init. Zielmodule werden via `run()` aufgerufen. `lh.sim_app` und `lh.robot` sind globale Handles.

**Konsequenzen**: Jedes neue Standalone-Skript braucht nur `run()` implementieren. Script-Editor-Skripte müssen selbst robot initialisieren (kein _launch_helper).

---

## ADR-005: Greif-Erkennung — Admittanz-Heuristik jetzt, Contact Reports Phase 5

**Problem**: `is_grasping()` muss erkennen ob der Roboter ein Objekt hält. Zwei physikalisch motivierte Ansätze: (1) Admittanzregelung via Gelenk-Torques, (2) Drucksensoren via PhysX Contact Reports.

**Entscheidung**: Stufen-Ansatz:
- **Sprint 3**: Admittanz-Heuristik — `robot.get_measured_joint_efforts()` gibt Torque pro Gelenk; überschreitet ein Finger-Torque einen Schwellwert während das Drive-Target hoch ist → Kontakt erkannt.
- **Phase 5**: Contact Report API als virtuelle Drucksensoren — wenn AS5600-Sensordaten kommen, soll die Sim dieselbe Sensor-Modalität liefern (Kraft pro Fingertip-Mesh statt Torque pro Gelenk).

**Begründung**: Admittanz ist mit `get_measured_joint_efforts()` sofort verfügbar, kein USD-Schema nötig. Contact Reports sind für LSTM-Training besser (gleiche Modalität wie echte FSR-Sensoren), aber erfordern `PhysicsContactReport`-Schema auf jedem Fingertip-Prim — sinnvoll erst wenn Sensor-Hardware feststeht.

**Konsequenzen**: `is_grasping()` in robot_io, Schwellwert in server_config.py. Bei Phase 5 Contact-Force-Publisher parallel ergänzen.

---

## Template für neue Entscheidungen

**Problem**: [Was ist das konkrete Problem oder der Trade-off?]

**Entscheidung**: [Was wurde entschieden?]

**Begründung**: [Warum diese Option?]

**Konsequenzen**: [Was ändert sich, was muss beachtet werden?]
