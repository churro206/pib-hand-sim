# Design: JOINT_SIGN-Fix — Joint-Frames direkt in der USD umdrehen

**Branch**: `experiment/omnigraph-lightweight`
**Datum**: 2026-08-22
**Status**: Design approved (Weg 1), Implementierung ausstehend

## Pivot: Weg 2 verworfen

Der ursprünglich gewählte Weg 2 (Joint-Frames direkt in der bereits gebackenen USD umdrehen,
ohne Reimport) wurde beim Ausformulieren des Implementierungsplans verworfen: Ein
`PhysicsRevoluteJoint` hält seine Rotationsachse über die Weltausrichtung von
`localRot0`/`localRot1` fest. Die Vorzeichen-Konvention umzudrehen bedeutet zwangsläufig, die
Weltrichtung der Gelenkachse selbst umzudrehen — das ist nicht "kostenlos" möglich: entweder
schnappt PhysX beim nächsten Play die komplette nachgeordnete Kinematik-Kette in die neue
Achsrichtung (Geometrie verspringt), oder die Umkehrung müsste rekursiv für jedes
nachgeordnete Glied neu hergeleitet werden — was am Ende genauso viel Aufwand ist wie Weg 1,
nur ohne dessen Sicherheit. Es gibt keinen risikoarmen Weg, die Konvention direkt im
gebackenen Prim umzudrehen; irgendwo in der Kette muss weiterhin negiert werden.

**Neue Entscheidung: Weg 1 — URDF editieren + Isaac-Reimport.** Der Rest dieses Dokuments
(Abschnitt "Warum nicht URDF editieren + neu importieren" unten) beschreibt die ursprüngliche
Gegenüberstellung; sie gilt jetzt umgekehrt als Begründung *für* Weg 1. Wichtige Ergänzung:
Die kanonische `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` bleibt unangetastet
(weiterhin Onshape-Konvention für ros2_control/IK-Team/RViz) — eine deterministisch daraus
abgeleitete Kopie (`isaac_sim/urdf/pib_upperbody_isaac_import.urdf`, Achsen negiert, Limits
vertauscht+negiert) dient ausschließlich als Isaac-Importquelle. Bei jedem Onshape-Re-Export:
Transform-Skript erneut laufen lassen, dann Isaac-Reimport wiederholen.

## Kontext

Onshape/URDF und Isaacs importierte Gelenkachsen sind vorzeicheninvertiert (physikalische
Eigenschaft des importierten Modells, für alle 44 DOFs). Der aktuelle Fix (`JOINT_SIGN = -1`
in `config/pib_hand_config.py`) kompensiert das an drei Stellen: einem Script Node im Action
Graph (Kommando-Pfad), gespiegelten Limits in `isaac_sim/setup_stage.py`, und den
Initialpose-Werten dort. Das funktioniert (Pickup-/Putdown-Demo verifiziert), hat aber zwei
Probleme:

1. **Verstreute Kompensation** an mehreren Stellen statt einer Quelle der Wahrheit.
2. **Bekannter Kompromiss (ADR-006)**: `ROS2PublishJointState` liest den Gelenkzustand direkt
   aus dem Prim, ohne Interceptions-Punkt für die Rückrichtung — `/pib/hw/joint_states`,
   `/joint_states` und Action-Feedback zeigen daher vorzeichen-gespiegelte Ist-Werte. Bewegung
   ist korrekt, nur die Anzeige irreführend.

## Ziel

Isaacs importierte Gelenke sollen nativ Onshape-Konvention haben (positiv = Flexion, Heben,
Vorne), sodass **kein** Vorzeichen-Handling mehr nötig ist — weder Script Node, noch
`JOINT_SIGN`, noch Limit-Spiegelung, noch Initialpose-Vorzeichen. Behebt den ADR-006-Kompromiss
als Nebeneffekt, da die Rückrichtung dann ohnehin schon Onshape-Konvention liest.

**Nicht Teil dieses Fixes**: Contact Sensors, Szenen-Erweiterung (bleiben die nächsten
Sprint-Punkte danach). Die URDF-Datei (`ros2_ws/src/pib_description/urdf/pib_upperbody.urdf`)
bleibt unangetastet.

## Warum nicht URDF editieren + neu importieren

`isaac_sim/usd/pib_upperbody.usd` referenziert keine externe URDF-Quelle — der Roboter ist
vollständig geflattened in die eine Datei eingebacken (kein `references`/`payload`/
`assetPath` im USD). Ein URDF-Fix (Achsen/Limits spiegeln) würde einen Reimport erfordern,
bei dem der bestehende, verifizierte Action Graph und die Szene auf den neuen Roboter-Prim-Baum
umgehängt und neu verifiziert werden müssten — großer Blast-Radius. Stattdessen: die bereits
gebackenen Joint-Prims direkt in der USD umdrehen, ohne URDF anzufassen.

## Technischer Ansatz

Die "positive Richtung" eines `PhysicsRevoluteJoint`-Prims wird nicht über einen Vektor
definiert, sondern über die relative Orientierung seiner beiden lokalen Gelenk-Frames
(`localRot0`/`localRot1`). Ein Gelenk lässt sich umdrehen, indem eines der beiden Frames um
180° um eine zur Gelenkachse senkrechte Achse gedreht wird — reine Prim-Bearbeitung, kein
Reimport.

### Schritt 1 — Spike an einem Gelenk

Gelenk: `dof_elbow_right` (Vorzeichen bereits verifiziert: +90° = voll gebeugt, siehe
`docs/conventions.md`).

Script-Editor-Skript:
1. Liest den `PhysicsRevoluteJoint`-Prim.
2. Rotiert `localRot0` oder `localRot1` um 180° um eine zur Gelenkachse senkrechte Achse.
3. Negiert/tauscht `lowerLimit`/`upperLimit` passend.
4. Verifikation in Isaac Sim: ein positiver Zielwert **direkt auf dem Prim, ohne jede weitere
   Negierung** muss zu Beugung führen — und der aus dem Prim ausgelesene Ist-Wert muss
   denselben positiven Wert zeigen.

**Go/No-Go-Punkt**: Klappt der Spike nicht sauber (z.B. weil PhysX `lowerLimit`/`upperLimit`
weiterhin relativ zum ursprünglichen Frame interpretiert), fällt die Entscheidung zurück auf
den URDF+Reimport-Weg — der wird dann als eigener, separater Punkt neu aufgesetzt, nicht in
diesen Fix hineingezogen.

### Schritt 2 — Generalisierung

Aus dem verifizierten Einzelfall eine Funktion bauen, die pro Gelenk automatisch die passende
senkrechte Achse aus dem jeweiligen `physics:axis`-Wert des Prims ableitet (nicht blind
kopieren — die 44 Gelenke haben unterschiedliche Achsorientierungen, u.a. gespiegelte Achsen
zwischen linker/rechter Körperhälfte, siehe `docs/conventions.md`). Anwenden auf alle 44
`PhysicsRevoluteJoint`-Prims (14 Body + 15 linke Hand + 15 rechte Hand).

### Schritt 3 — Einmalig ausführen, USD speichern

Kein Re-Apply pro Session nötig (im Gegensatz zu `configure_drives()`/`set_joint_limits()`,
die PhysX weiterhin bei jedem Sessionstart braucht, da Stiffness/Damping nicht gecached wird).
Das Skript bleibt trotzdem im Repo (z.B. `isaac_sim/tools/flip_joint_axes.py`) — einmalig
ausgeführt, nicht Teil des `start.py`-Ablaufs — falls die USD je neu aus einer URDF importiert
werden muss.

## Migrationsschritte nach erfolgreichem Rollout

Reihenfolge, jeweils in Isaac Sim verifiziert bevor committed wird:

1. **Action Graph**: Script Node entfernen, `ROS2SubscribeJointState.positionCommand` direkt
   an `IsaacArticulationController.positionCommand` verkabeln.
2. **`config/pib_hand_config.py`**: `JOINT_SIGN = -1` entfernen (und jede Referenz darauf).
3. **`isaac_sim/setup_stage.py`**: `_BODY_LIMITS_ISAAC` und die Hand-Limit-Sonderbehandlung
   durch die reinen Onshape-Limits ersetzen (kein Spiegeln mehr); Initialpose-Werte (z.B.
   `dof_elbow_right: -30.0`) auf positives Vorzeichen drehen; JOINT_SIGN-Kommentare entfernen.
4. **44-DOF-Sweep-Verifikation**: kleines Test-Skript (via `test_client_pickup.py`-Pattern
   oder direkt Script Editor), das jedes der 44 Gelenke einzeln durch seinen Bereich fährt —
   Leon bestätigt visuell pro Gelenk, dass positiv weiterhin die dokumentierte
   Onshape-Bedeutung hat (Referenzwerte aus `docs/conventions.md`). Pflicht, kein
   Nice-to-have — die Gelenke sind nicht alle gleich orientiert.
5. **Pickup-/Putdown-Demo** erneut end-to-end laufen lassen (Regressionscheck fürs bereits
   Verifizierte).
6. **Docs**: `CLAUDE.md`, `architecture.md`, `conventions.md` — JOINT_SIGN-Abschnitte raus;
   `decisions.md` — neues ADR (z.B. ADR-007), das ADR-006s "Bekannter Kompromiss" als behoben
   markiert und auf ADR-001/006 verweist statt sie zu löschen (historischer Kontext bleibt
   nachvollziehbar).

## Risiken & offene Punkte

- **Größtes Risiko**: Die Quaternion-Frame-Flip-Mechanik ist nicht mit Sicherheit aus der
  Doku bekannt — der Spike an `dof_elbow_right` ist der Go/No-Go-Punkt (siehe oben).
- **44 Gelenke sind nicht alle gleich orientiert** — die generalisierte Funktion muss das pro
  Gelenk korrekt ableiten. Sweep-Check (Migrationsschritt 4) ist deshalb Pflicht.
- **Kein direkter Isaac-Sim-Zugriff** bei der Entwicklung dieses Fixes — Spike und alle
  Verifikationsschritte laufen im Script Editor bei Leon; Code wird geliefert, Ausführung und
  visuelle Bestätigung liegen bei ihm.
- Falls der Spike zeigt, dass die 180°-Frame-Rotation Limits/Drive-Konfiguration unerwartet
  durcheinanderbringt, müsste zusätzlich `configure_drives()`/`set_joint_limits()` angepasst
  werden — als Fallback im Spike mit einplanen.
