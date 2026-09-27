# Architektur-Entscheidungen

Format: Problem → Entscheidung → Begründung → Konsequenzen

**Branch `experiment/omnigraph-lightweight`:** ADR-001/003/004 beziehen sich auf
`robot_io.py`/`_launch_helper.py` — auf diesem Branch entfernt, siehe ADR-006. Als
historischer Kontext (warum diese Entscheidungen ursprünglich getroffen wurden) stehen
gelassen, gelten aber nicht mehr für den aktuellen Code hier. Voller Stand auf
`feature/ros2-control`.

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

## ADR-005: Fingertip-Kontaktkräfte via ArticulationView (PhysX Tensor API)

> **Überholt durch ADR-008:** Der `ArticulationView`-Ansatz wurde nie umgesetzt (Zielkonflikt
> mit der "kein Custom-Python"-Linie dieses Branches). Stattdessen native OmniGraph-Nodes,
> siehe ADR-008. Als historischer Kontext stehen gelassen.

**Problem**: Die Sim soll Fingertip-Kontaktkräfte liefern — für Greif-Erkennung und später als LSTM-Trainingsdaten (gleiche Modalität wie echte FSR-Sensoren).

**Entscheidung**: `ArticulationView.get_net_contact_forces()` aus `isaacsim.core.prims` — derselbe Ansatz wie Isaac Lab's `ContactSensor`, nur ohne den Isaac-Lab-Wrapper. Kein `is_grasping()` Bool, stattdessen Kraft-Veröffentlichung als ROS2-Topic.

Konkret:
- `ArticulationView` statt `SingleArticulation` für den Roboter → gibt Joint-Control + Kontaktkräfte in einem Objekt
- `get_net_contact_forces(indices=[fingertip_indices])` → `(5, 3)` Numpy-Array, Newton
- Betrag pro Fingertip → 5 Skalare für rechte Hand
- Publish auf `/pib/fingertip_forces` als `sensor_msgs/JointState` (`name` = Fingernamen, `effort` = Kraft in Newton), 50 Hz

**Begründung**: Admittanz-Heuristik (`get_measured_joint_efforts()`) verworfen — gibt Torque pro Gelenk, nicht Kraft pro Fingertip; schlechte Modalitäts-Übereinstimmung mit echten FSR-Sensoren. `ArticulationView` ist in Isaac Sim 5.1 eingebaut (kein Isaac-Lab-Install nötig) und liefert direkt die physikalisch korrekte Kontaktkraft.

**Konsequenzen**:
- `pib_bridge.py`: `ArticulationView` initialisieren nach Grace-Period (ersetzt oder ergänzt `SingleArticulation`)
- Fingertip-Link-Indizes vorab mit `inventory.py` bestimmen (Prim-Pfade der `*_tip`-Links)
- `sensor_msgs/JointState` auf `/pib/fingertip_forces` — kein Custom-Message-Package nötig
- Offen: exakte Prim-Pfade der Fingertip-Links noch nicht verifiziert → `inventory.py` zuerst ausführen

---

## ADR-006: Action Graph (OmniGraph) statt eigenem ROS2-Bridge-Prozess

> **Überholt durch ADR-007:** Der hier beschriebene Script-Node-Ansatz und sein bekannter
> Kompromiss (gespiegelte Ist-Werte) wurden ersetzt. Als historischer Kontext stehen
> gelassen.

**Problem**: `pib_bridge.py` bildete den ROS2↔Isaac-Übergang komplett in Python nach:
eigener `rclpy`-Node mit manuellem Spin-Loop, Grace-Period/Lazy-Init-Zustandsmaschine
für die Physics-View-Bereitschaft, Python-3.11/3.12-rclpy-Pfad-Workaround. Für den reinen
Joint-State-Pub/Sub-Anteil existieren dafür fertige, NVIDIA-gewartete OmniGraph-Nodes.

**Entscheidung**: `pib_bridge.py` ersetzt durch einen Action Graph, Teil der USD-Stage
(`isaac_sim/usd/pib_upperbody.usd`): `ROS2SubscribeJointState` → Script Node (JOINT_SIGN-
Invertierung) → `IsaacArticulationController`, Rückrichtung über `ROS2PublishJointState`.
Topic-Namen/-Typen bleiben identisch zu vorher (`/pib/hw/joint_commands`,
`/pib/hw/joint_states`, `sensor_msgs/JointState`, rad) — `ros2_control`-Seite unverändert.

**Begründung**: Die nativen Nodes übernehmen Physics-View-Lifecycle-Handling selbst (kein
Grace-Period-Code mehr nötig) und sind robuster gegen Isaac-Sim-Updates als selbst
gepflegter `rclpy`-Code. Reduziert auf den Teil, der wirklich Custom-Logik ist: die
Vorzeicheninvertierung, für die es keinen fertigen Node gibt.

**Konsequenzen**:
- `robot_io.py`, `pib_bridge.py`, `runner.py`, `_launch_helper.py`, ControlMode-Architektur
  (`control/`), Sequenz-Pipeline (`config/sequences.py`, `isaac_sim/sequences/`) entfernt —
  wurden nur vom bisherigen Bridge-/Control-Weg gebraucht
- **Bekannter Kompromiss:** `ROS2PublishJointState` liest den Gelenkzustand direkt aus dem
  Prim (Isaac-Konvention) — kein Interceptions-Punkt für die Vorzeichenkorrektur der
  Rückrichtung. `/pib/hw/joint_states`, `/joint_states` und Action-Feedback zeigen daher
  gespiegelte Werte. Bewegung selbst korrekt (Befehlsrichtung ist korrigiert); nur die
  Ist-Wert-Anzeige irreführend. `controllers.yaml` hat keine Toleranz-Constraints, daher
  kein Abbruch. Sauberer Fix wäre eine Vorzeichen-Korrektur direkt in den URDF-Achsen
  (nicht umgesetzt — betrifft auch die Body-Gelenke, nicht nur die Hand, und bräuchte
  Re-Verifikation über alle 44 DOFs)
- `start.py`/`setup_stage.py` bleiben unverändert nötig — Action Graph ersetzt nur die
  Laufzeit-Bridge, nicht die einmalige Physik-Konfiguration pro Session
- `velocityCommand`/`effortCommand` an den Nodes bewusst unverbunden gelassen —
  `controllers.yaml` konfiguriert nur `command_interfaces: [position]`

---

## ADR-007: Vorzeichen-Fix direkt an den Gelenk-Prims statt Script Node

**Problem**: ADR-006 kompensierte die Vorzeichen-Invertierung (Onshape vs. Isaac) über
einen Script Node im Action Graph — funktionierte für den Kommando-Pfad, aber
`ROS2PublishJointState` liest den Prim direkt und hatte keinen Interceptions-Punkt für die
Rückrichtung (bekannter Kompromiss: gespiegelte Ist-Werte auf `/pib/hw/joint_states`).

**Entscheidung**: `isaac_sim/tools/flip_joint_sign.py`, einmalig im Script Editor gegen die
offene Stage ausgeführt, danach gespeichert. Für jedes `PhysicsRevoluteJoint`: `localRot0`
UND `localRot1` werden symmetrisch um dieselbe 180°-Rotation um eine zur Gelenkachse
senkrechte Achse gedreht — die Weltausrichtung der Achse bleibt dadurch exakt gleich (kein
Verspringen der Kette), aber der gemessene Winkel kehrt sein Vorzeichen um
(Rotationskonjugation `F·M·F`: gleicher Winkel, gespiegelte Achse ≡ gespiegelter Winkel,
gleiche Achse). Limits werden passend vertauscht+negiert. Danach: Script Node aus dem
Action Graph entfernt, `JOINT_SIGN`/Limit-Spiegelung aus `config/pib_hand_config.py` und
`isaac_sim/setup_stage.py` entfernt.

Zwei Alternativen verworfen:
- **URDF editieren + Reimport**: Prämisse war falsch — die USD wird nicht aus der URDF
  importiert, sondern per Onshape-Importer direkt aus Onshape gebaut. Eine Korrektur der
  URDF hätte die tatsächliche Build-Pipeline nicht beeinflusst.
- **Nur eine Seite des Gelenk-Frames drehen** (`localRot1` allein): mathematisch nicht
  äquivalent — die Weltausrichtung der Achse würde sich ändern, PhysX würde die
  nachgeordnete Kinematik-Kette beim nächsten Play in die neue Achsrichtung verspringen
  lassen. Erst die symmetrische Drehung beider Seiten vermeidet das.

**Begründung**: Der Fix sitzt an der Ursache (dem Prim selbst), unabhängig vom Importweg
(Onshape-Importer statt URDF), und ist eine einmalige, persistente Korrektur (in der USD
gespeichert) statt einer Laufzeit-Kompensation — kein Script Node, kein `JOINT_SIGN` mehr
nötig. Behebt den ADR-006-Kompromiss automatisch, da `ROS2PublishJointState` jetzt direkt
korrekte Werte vom Prim liest.

**Konsequenzen**:
- `JOINT_SIGN`-Konstante, `_BODY_LIMITS_ISAAC`-Spiegelung, Script Node — entfernt
- `/pib/hw/joint_states`, `/joint_states`, Action-Feedback zeigen jetzt korrekte
  (nicht mehr gespiegelte) Ist-Werte
- Bei jedem künftigen Onshape-Reimport: `flip_joint_sign.py` erneut gegen die neue Stage
  ausführen
- Einige Body-Limits in `setup_stage.py` waren zuvor grobe Schätzwerte (z.B.
  `dof_shoulder_horizontal_right`/`dof_upper_arm_left` waren `[-90°,90°]` geschätzt, korrekt
  aus der Onshape-Quelle ist `[0°,90°]`) — jetzt korrigiert
- `isaac_sim/tools/flip_urdf_for_isaac.py` und `isaac_sim/urdf/pib_upperbody_isaac_import.urdf`
  (Artefakte des verworfenen URDF-Reimport-Ansatzes) entfernt

---

## ADR-008: Fingertip-Kontaktkräfte via native OmniGraph-Nodes statt ArticulationView

**Problem**: ADR-005 sah `ArticulationView.get_net_contact_forces()` in einem Script Node
vor — bräuchte echten Python-Code im Action Graph, Zielkonflikt mit der "so viel NVIDIA
wie möglich"-Linie dieses Branches (siehe `docs/architecture.md` → „Offen"). Alternative
(nativer `IsaacContactSensor`-Node) war dort als Option genannt, aber nicht verifiziert.

**Entscheidung**: Nativer `IsaacContactSensor`-Prim pro Fingertip-Link + `Isaac Read
Contact Sensor Node` im Action Graph, Ausgabe (`outputs:value`, Kraft in Newton) über
einen generischen `ROS2 Publisher`-Node (`messagePackage=std_msgs`, `messageSubfolder=msg`,
`messageName=Float32`) auf `/pib/fingertip_force/<finger>` publiziert — ein Topic pro
Fingertip, kein gebündeltes `sensor_msgs/JointState`-Array wie in ADR-005 skizziert.
Für `index_right` verifiziert: Kraftwerte in Isaac (~1-2 N beim Greifen der Testdose)
kommen unverändert auf `ros2 topic echo /pib/fingertip_force/index_right` an.

**Begründung**: Kein Script Node, kein Custom-Python nötig — passt zur Linie dieses
Branches (vgl. ADR-006/007). Ein Topic pro Fingertip ist für den aktuellen Stand (1 von
10 Fingerspitzen verkabelt) einfacher als ein Array-Aufbau über `ConstructArray` +
`ROS2PublishJointState`; letzteres bleibt eine Option, falls später alle Fingerspitzen
gebündelt in einer Nachricht laufen sollen.

**Konsequenzen**:
- Fingertip-Link-Prims mussten einzeln `SetInstanceable(False)` gesetzt werden, bevor der
  `IsaacContactSensor`-Prim angelegt werden konnte — Onshape-Importer legt Robotik-Meshes
  standardmäßig als instanceable an (Performance-Feature für viele parallele
  Roboter-Instanzen, hier ohne Nutzen), Instance Proxies erlauben kein Authoring
  (Fehler „authoring to an instance proxy is not allowed"). Für jede weitere Fingerspitze
  wiederholen.
- Bisher nur `index_right` verkabelt. Restliche 9 Fingerspitzen (siehe
  `config/pib_hand_config_v4.py` → `HAND_DOFS` für Namensschema) offen — gleiches Muster:
  Instanceable aus, `IsaacContactSensor`-Prim anlegen, `Isaac Read Contact Sensor Node` +
  `ROS2 Publisher`-Node im bestehenden Action Graph ergänzen.
- Debugging-Fallstrick (nicht Node-spezifisch, aber hat die Verifikation verzögert):
  `ROS_DOMAIN_ID` ist pro Terminal gesetzt, nicht global — eine Shell mit abweichender
  Domain (z.B. geerbt aus einer anderen Session) sieht *gar keine* ROS2-Topics, auch nicht
  die längst bestehenden. Vor jeder ROS2-Diagnose `echo $ROS_DOMAIN_ID` prüfen (Soll: `0`,
  siehe `docs/conventions.md`).
- `docs/conventions.md` Topic-Tabelle um `/pib/fingertip_force/<finger>` ergänzt.

---

## ADR-009: Sehnendynamik-Kopplung via Script Node (bewusste Ausnahme von ADR-006/007/008)

**Problem**: Die reale linke Hand (Prototyp, Unterarm + Hand) hat nur **8 Servos**
(Handgelenk, Unterarmdrehung, Daumen-Rotator, sowie je ein Servo pro Finger/Daumen-MCP) —
gesteuert über einen STM32 Nucleo. PIP/DIP (bzw. Daumen-IP) sind **nicht** unabhängig
aktuiert, sondern folgen dem MCP rein mechanisch über zwei Kopplungsstangen (Viergelenk-
getriebe pro Stufe). Die Simulation bildete bisher jedes Fingerglied als unabhängig
positionsgesteuertes Gelenk ab (`servo_pose_to_joints()` in `config/pib_hand_config_v4.py`:
lineare 1:1-Näherung) — kinematisch falsch und unbrauchbar als digitaler Zwilling für
späteres Sim-to-Real-RL-Training (siehe `feature/rl-grasping`).

**Entscheidung**: Ein Script Node (`FingerCoupling`) im bestehenden Action Graph
(`/Graph/ROS_JointStates` in `pib_upperbody_v5.usd`) berechnet PIP/DIP/IP-Zielwinkel jeden
Tick aus dem **gemessenen** Ist-Winkel des jeweils vorgelagerten Gelenks — geschlossener
Regelkreis, kein Verlass auf den befehligten Soll-Wert. Formel: analytische Viergelenk-
Kopplung (geschlossene Lösung, keine LUT, keine Nullstellensuche im Regelkreis), hergeleitet
und validiert in `tendondrive/finger_analytisch.py` (Finger, r=7mm) und
`tendondrive/daumen_analytisch.py` (Daumen, r=7,4mm) — siehe dort für die geometrische
Herleitung der Schließbedingung. Ein neuer `IsaacArticulationState`-Node liefert die Ist-
Winkel (`MeasuredJointState`, 18 Gelenke: `{finger}_{side}_proximal`/`_distal` +
`thumb_{side}_proximal`). MCP selbst bleibt normale ROS2-Positions-Drive wie bisher, keine
Sehnenkraft/Effort-Steuerung — reine kinematische Umleitung der Positions-Commands für 18
von 44 Gelenken (4 Finger × 2-stufig + Daumen × 1-stufig, je beide Seiten).

Geprüfte Alternative: natives PhysX Fixed-Tendon-Schema (`PhysxTendonAxisAPI`/
`PhysxTendonAxisRootAPI`, in Isaac Sim 5.1 vorhanden) — verworfen, weil dessen Gearing ein
**linearer** Koeffizient pro Achse ist. Die reale Kopplung ist stark nichtlinear
(Übersetzung dPIP/dMCP läuft von 0,6 bis 1,667 über den Bewegungsbereich 0°–90°) und lässt
sich damit nicht exakt abbilden, nur linear annähern.

**Begründung**: Bewusste, begründete Ausnahme von der ADR-006/007/008-Linie ("kein Custom-
Python im Action Graph") — das eigentliche Kriterium dahinter (Action Graph bleibt Teil der
Stage, kein externer Prozess, kein Skript-Editor-Lauf pro Session nötig) ist weiterhin
erfüllt. Für eine echte Sehnenkraft-Berechnung gäbe es ohnehin keinen nativen Node; die
Alternative (Fixed Tendon) kann die nichtlineare Geometrie nicht exakt genug abbilden.

**Konsequenzen**:
- Neue Tools: `isaac_sim/tools/build_finger_coupling_graph.py` (einmaliger Graph-Aufbau,
  fügt `MeasuredJointState`+`FingerCoupling` hinzu, hängt `ArticulationController.inputs:
  jointNames`/`positionCommand` von `SubscriberJointState` auf `FingerCoupling` um),
  `isaac_sim/tools/patch_finger_coupling_script.py` (gezielter Patch nur des Skript-Texts,
  ohne Knoten neu anzulegen), `isaac_sim/tools/inspect_action_graph.py` (Diagnose: listet
  Action-Graph-Knoten inkl. tatsächlicher Attribut-Verbindungen, schreibt nach
  `isaac_sim/tools/_action_graph_inventory.txt`, gitignored).
- `/pib/hw/joint_commands` liefert weiterhin Werte für alle 44 DOFs, aber `distal`/`tip`
  (Daumen: `tip`) der 4 Finger + Daumen, beide Seiten (18 Gelenke), werden vom Script Node
  **überschrieben** — eingehende ROS2-Werte für diese Gelenke werden ignoriert. `docs/
  conventions.md` Topic-Tabelle entsprechend ergänzt.
- **Zwei Bugs beim Erstaufbau gefunden, beide gefixt:**
  1. `NameError: name 'np' is not defined` beim Aufruf der `FourBar`-Methoden, obwohl
     `import numpy as np` direkt über der Klassendefinition auf Modulebene stand. Ursache:
     Isaac Sims Script-Node-Sandbox execut den Skript-Text offenbar mit getrennten
     globals-/locals-Dicts — der `import` landet nur im locals-Dict, aber Methoden einer
     auf Modulebene definierten Klasse bekommen als `__globals__` das (numpy-lose)
     globals-Dict. Klassischer Python-Fallstrick bei `exec()` mit getrennten globals/
     locals. **Fix**: Klasse und Instanzen als Closures innerhalb von `setup(db)` anlegen,
     Instanzen in `db.per_instance_state` ablegen — schließt korrekt über `setup()`s
     eigenen Laufzeit-Namensraum, unabhängig vom Sandbox-Mechanismus. Gilt für **jeden**
     künftigen Script Node auf diesem Branch — siehe neue Regel in `CLAUDE.md`.
  2. Ziel-Gelenkname `thumb_{side}_distal` war falsch — v5-Namensschema nennt das
     Daumenmittelgelenk `tip`, nicht `distal` (dokumentierte Abweichung, siehe
     `docs/conventions.md`, war beim Schreiben übersehen worden). Führte zu einer
     `ArticulationController`-Warnung (`OmniGraph Warning: 'thumb_left_distal'`), die
     augenscheinlich den **kompletten** `positionCommand`-Batch blockierte — auch
     unbeteiligte Gelenke wie `wrist_left` bewegten sich währenddessen nicht, was die
     Fehlersuche zunächst in eine falsche Richtung lenkte (sah wie ein grundsätzliches
     Verkabelungs-/Physics-Problem aus, war aber ein einzelner falscher Name).
- End-to-end über den echten `ros2_control`-Stack verifiziert (`FollowJointTrajectory`-
  Goals gegen `index_left_proximal`, `thumb_left_proximal`, `wrist_left` als Kontrolltest,
  sowie alle 10 Finger-/Daumen-MCPs beider Hände gleichzeitig auf 90° — der einzige exakte
  Punkt der Kopplungskurve, leicht auf einen Blick prüfbar).
- Geometrie wird für **beide** Hände als identisch/gespiegelt angenommen (Kopplung läuft
  für `left` und `right` symmetrisch) — nicht separat verifiziert, da real aktuell nur die
  **linke** Hand als Hardware-Prototyp existiert.
- Kontaktsensor-Erweiterung (restliche 9 Fingerspitzen, ADR-008-Muster) und
  `config/pib_hand_config_v5.py` bleiben offen, siehe `docs/current-sprint.md`.
- RL-Grasping-Vorhaben (Isaac Lab) auf neuem Branch `feature/rl-grasping` — Aktionsraum
  dort **muss** die 8 realen Servo-DOFs sein, PIP/DIP/IP intern über dieselbe `FourBar`-
  Formel berechnet (nicht lernbar), sonst lernt die Policy real unerreichbare Posen.

---

## Template für neue Entscheidungen

**Problem**: [Was ist das konkrete Problem oder der Trade-off?]

**Entscheidung**: [Was wurde entschieden?]

**Begründung**: [Warum diese Option?]

**Konsequenzen**: [Was ändert sich, was muss beachtet werden?]
