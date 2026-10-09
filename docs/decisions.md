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

> **Ergänzt durch ADR-013** (v5): Ausgabe gebündelt als ein `sensor_msgs/JointState`-Topic
> statt ein `Float32`-Topic pro Fingerspitze. Sensor- und Reader-Ansatz bleiben wie hier.

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

> **Ersetzt durch ADR-011:** Der Script Node koppelte nur die Soll-Winkel; PIP/DIP blieben
> eigene Antriebe mit `maxForce=inf`, ihre Last floss nicht zum MCP. Branch auf den Stand
> davor zurückgesetzt, Kopplung jetzt über PhysX Mimic Joints. Der Commit (`1d0cd9c`) lebt
> auf `feature/rl-grasping` und im Tag `backup/sehnendynamik-1d0cd9c` weiter. Als
> historischer Kontext stehen gelassen — die Script-Node-Regel (Closures in `setup(db)`)
> gilt weiterhin.

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

## ADR-010: Explizite Kraft-Rückwirkung PIP/DIP → MCP (verworfen)

> **Verworfen, ersetzt durch ADR-011.** Nie committet; Code und Herleitung liegen nur lokal
> (`git stash` vom 2026-10-03: `isaac_sim/tools/build_coupling_reflection_graph.py`,
> `tendondrive/PROMPT_kopplung_rueckwirkung.md`, `tendondrive/PROMPT_rueckwirkung_instabilitaet.md`).

**Problem**: In ADR-009 waren PIP/DIP eigene PD-Antriebe mit `maxForce=inf` — eine Kraft an
der Fingerspitze belastete den MCP-Servo nicht. Geschätzt war die Fingerspitze dadurch bei
90° um Faktor ~6,9 zu stark (183,6 N statt ~26,7 N real).

**Entscheidung (Versuch)**: Der Script Node berechnet zusätzlich das Moment der PIP/DIP-
Antriebe und gibt es über die Kopplungs-Jacobian (`-J·τ`) als `effortCommand` an einen
zweiten `IsaacArticulationController` auf dem MCP. Vorab verifiziert: `maxForce` begrenzt
nur die PD-Kraft, nicht einen separat vorgegebenen Effort; zwei Controller auf demselben
Gelenk koexistieren.

**Ergebnis**: Beim Tischtest bis zu −2025 Nm Effort am MCP, PIP knickte auf −87,8° durch,
MCP bewegte sich trotzdem nicht messbar anders als ohne Rückwirkung (82,7°). Eigene
Stabilitätsrechnung: Die Rückführung wirkt am MCP wie eine explizite Feder mit
J₁²·k ≈ 1050 Nm/rad; bei ~5·10⁻⁵ kg·m² Fingerträgheit ist eine explizite Feder nur bis
≈0,4 Nm/rad (Δt = 1/60 s) stabil — strukturell instabil, nicht durch Abstimmen zu retten.

**Konsequenzen**: Verworfen zugunsten einer impliziten Kopplung im Solver (ADR-011).

---

## ADR-011: Fingerkopplung über PhysX Mimic Joints (ersetzt ADR-009/010)

**Problem**: PIP/DIP (Finger) bzw. IP (Daumen) haben am realen Prototyp keinen Motor — sie
folgen dem MCP über Viergelenk-Koppelstangen, und der eine MCP-Servo (ST3215, 2,94 Nm)
trägt die Last aller Glieder. ADR-009 bildete nur die Winkel nach, nicht den Lastfluss;
ADR-010 (explizite Rückwirkung) war instabil.

**Entscheidung**: `PhysxMimicJointAPI` am Folgegelenk — eine Zwangsbedingung im PhysX-
Solver, Kopplungskraft wird implizit im selben Schritt berechnet und an den MCP
weitergegeben. Stufe 1, linear:

| Folgegelenk | Referenz | gearing | offset |
|---|---|---|---|
| `{index,middle,ring,pinky}_{side}_distal` (PIP) | `…_proximal` (MCP) | −1 | 0 |
| `{index,middle,ring,pinky}_{side}_tip` (DIP) | `…_distal` (PIP, Kette) | −1 | 0 |
| `thumb_{side}_tip` (IP) | `thumb_{side}_proximal` | −1 | 0 |

PhysX-Formel (aus `generatedSchema.usda`, nicht geraten): `q_folge + gearing·q_ref + offset = 0`
→ `gearing = −1` heißt `q_folge = q_ref`. Instanzname = Achse des Gelenks (`rotZ`, aus
`physics:axis` gelesen). Hart (nicht nachgiebig) — Isaac Sim 5.1 hat ohnehin keine
Mimic-Compliance. Folgegelenke passiv (Stiffness/Damping 0), mit Armature 5·10⁻⁴ kg·m² und
`maxJointVelocity` 500 °/s (reale Kopplung bis 1,67× MCP-Geschwindigkeit). Gesetzt jede
Session von `start.py` → `setup_stage.configure_mimic_joints()`; Gearing/Offset stehen nur in
`setup_stage.py` → `MIMIC_JOINTS` (Vorbereitung für eine adaptive Stufe 2).

Fixed Tendons waren in ADR-009 wegen ihres linearen Gearings verworfen worden — Mimic
Joints sind in Stufe 1 genauso linear. Für sie spricht: NVIDIAs Referenzweg für
linkage-getriebene Hände, und laut PhysX-Doku lassen sich Gearing/Offset zwischen
Simulationsschritten ändern (Voraussetzung für eine adaptive Stufe 2). Verworfen: Script
Node (ADR-009) und explizite Rückwirkung (ADR-010).

**Begründung**: Implizite Kopplung ist stabil gegen harten Kontakt, gibt die Last physikalisch
an den MCP weiter und braucht keinen Custom-Python im Action Graph (zurück auf der Linie von
ADR-006/007/008). NVIDIA nutzt denselben Ansatz für linkage-getriebene Hände (Inspire Hand,
Isaac-Sim-Tuning-Tutorials).

**Konsequenzen**:
- Branch auf `0fdbc62` zurückgesetzt (vor ADR-009), `FingerCoupling`/`MeasuredJointState`
  sind nicht mehr im Graph.
- ROS2-Werte für die 18 Folgegelenke in `/pib/hw/joint_commands` sind wirkungslos (siehe
  `docs/conventions.md`); gesteuert wird nur über `proximal`.
- Bekannter Preis der Linearisierung: Winkelfehler in der Bewegungsmitte gegenüber der realen
  Viergelenk-Kurve bis ~10° (PIP), ~22° (DIP über die Kette), ~8° (Daumen-IP); exakt bei 0° und
  90°. Kraftgrenze an der Fingerspitze bei 90° etwa doppelt so hoch wie real (Schätzung).
- Stufe 2 (adaptiv: Gearing/Offset jeden Schritt aus der Viergelenk-Formel linearisieren)
  offen; ob Isaac eine Laufzeitänderung an PhysX weitergibt, ist nicht getestet. Die
  Viergelenk-Herleitung (`tendondrive/`) liegt in `1d0cd9c`.
- Verifiziert: alle 10 MCPs frei 0°→45°→90°→0° mit Δ ≤ 0,2° (`test_client_mimic_v5`);
  Finger gegen den Tisch mit Kopplung ≤ 0,1° unter Last (`test_client_mimic_load_v5`, nach
  ADR-012).
- `feature/rl-grasping` basiert noch auf ADR-009: Aktionsraum dort bleibt die 8 Servo-DOFs;
  ob Isaac Lab die Mimic Joints aus der USD übernimmt, ist ungeprüft.

---

## ADR-012: Physik-Tuning nach NVIDIA — Servo-Aktuatormodell, Self-Collision, OnPhysicsStep

**Problem**: Mit Mimic Joints (ADR-011) chatterte der Finger beim Tischkontakt (±10°), später
brach der ganze linke Arm aus (Gelenke drehten sich mehrere tausend Grad, Limits wirkungslos,
NaN in `/pib/hw/joint_states`). Ursachen laut Analyse (Schema, Audit):
- Antriebe standen auf 500–5000 Nm/**°** (Einheit pro Grad, laut USD-Schema) — an MCP,
  Handgelenk, Unterarm mit `maxForce` 2,94 Nm kombiniert: Sättigung schon bei ~0,006°
  Fehler, der Antrieb wirkte wie ein Relais (±2,94 Nm). Eigenfrequenz × Zeitschritt
  (NVIDIA-Kriterium, soll nicht ≫ 1 sein) lag bei ~25–400.
- Keine realistischen Geschwindigkeitsgrenzen (Importer: 10 rad/s = 573 °/s aus der URDF).
- Self-Collision am Articulation Root aus.

**Entscheidung**: Vorgehen nach NVIDIAs Tuning-Reihe (Inspire Hand: Asset inspizieren →
Collider-Paare → Antriebsgrenzen → Gains) und Articulation Stability Guide:

1. **Servo-Aktuatormodell aus Datenblättern** (12 V): ST3215 (alle Servo-Gelenke außer
   Schultern) 2,94 Nm Stall, 270 °/s Leerlauf; ST3095-C002 (`shoulder_*`) 9,32 Nm, 186 °/s.
   `maxForce` = Stall-Torque, `maxJointVelocity` = Leerlaufdrehzahl, Stiffness =
   `maxForce`/5° (Robotiq-Rezept, 0,087 rad), Damping kritisch (ζ = 1) mit der effektiven
   Gelenkträgheit, Armature 5·10⁻³ kg·m² (Annahme — Rotorträgheit/Übersetzung nicht im
   Datenblatt). Für **alle** v5-Servo-Gelenke umgesetzt (`setup_stage.py` → `SERVOS`,
   `V5_ACTUATORS`); die Nenn-Trägheit pro Gelenkgruppe für die Dämpfung stammt aus dem Audit
   (Massenmatrix-Diagonale in der T-Pose). ω_n·Δt danach 0,44–1,36, ζ = 1. v4 bleibt bewusst
   auf den Referenzwerten von `0fdbc62` (500–5000 Nm/°, `maxForce=inf`).
2. **Self-Collision an** am `root_joint` — empirisch der entscheidende Schritt: danach kein
   Wegfliegen und kein Schwingen mehr beim Tischtest. Den Mechanismus erklären die Daten nicht.
   Collision Groups vorerst nicht nötig (direkt verbundene Glieder filtert PhysX selbst; die
   Überlappungen Daumen↔Handfläche und Handfläche↔Unterarm in Ruhe stören nicht).
3. **Action-Graph-Trigger `OnPhysicsStep`** statt `OnPlaybackTick` (Sim läuft oft < 60 FPS;
   Graph-Prim braucht dafür `evaluationMode=Standalone` + `pipelineStage=pipelineStageOnDemand`).
4. **Asset-Audit** (`isaac_sim/tools/audit_asset.py`) statt Annahmen: Massen USD = PhysX =
   URDF (Onshape) für alle 47 Links, effektive Gelenkträgheit aus der Massenmatrix.

Geprüft, ohne Wirkung oder nicht verfügbar:
- Zeitschritt 60 → 240 Hz: keine Verbesserung (bei ω_n·Δt ~ 100–400 erwartbar).
- Mimic-Compliance (`naturalFrequency`/`dampingRatio`) und `solveArticulationContactLast`:
  gibt es in Isaac Sim 5.1 / omni.physx 107.3 nicht (nur 6.0-Docs).
- Dämpfung der Folgegelenke: von NVIDIA nicht gestützt, nicht umgesetzt.

**Begründung**: So nah wie möglich an NVIDIA-Praxis und bewährten Projekten (Robotiq-2F-85-
Beispiel; SO-ARM100 in Isaac Lab nutzt ebenfalls ST3215 mit `effort_limit` = Stall-Torque
und Geschwindigkeitslimit). Mit dem Rezept liegt ω_n·Δt für alle umgestellten Gelenke bei
~0,4–1,4.

**Konsequenzen**:
- Verifiziert (Tischtest): `index_left` bleibt bei MCP ≈10° stabil am Tisch stehen
  (Spannweite 0,0°, Kopplung ≤ 0,1°, Arm-Drift ≤ 2,4°); vier Finger gleichzeitig: das
  Handgelenk gibt nach (Reaktionsmoment > 2,94 Nm) und die Hand kippt — realistisch.
- Bewusst akzeptiert („reale Gelenke sind auch nicht perfekt"): Handgelenk hängt in der
  Tisch-Testpose 2,7–5,4° durch (weiche Servo-Gains); mit Self-Collision blockieren sich
  Daumen und Zeigefinger bei voller Beugung ohne Daumenrotation (~70°), die übrigen Finger
  stoppen bei ~88,5° (Convex Hull der Handfläche).
- Massen aus Onshape sind Vollmaterial-PLA (1,30 g/cm³), ohne Servos/Infill — bewusst so
  belassen; einziger Fix: Unterarm-Override 30 g → 0,229 kg (URDF + USD, gegen Onshape
  verifiziert).
- Mit dem Servo-Arm (2,94 Nm Ellbogen/Oberarm, 9,32 Nm Schulter) ist jetzt der Arm das
  schwächste Glied: Beim Tischtest drückt der Finger die Hand weg (Ellbogen gibt ~5° nach)
  statt am Tisch zu stallen; bei der Pickup-Demo hält der ausgestreckte Arm die Dose nur
  knapp und hängt sichtbar durch — laut Leon realistisch im Vergleich zum Laborroboter.
- Stellschraube, falls das Durchhängen stört: `SERVO_SATURATION_ERROR_DEG` (5°; SO-ARM100
  nutzt effektiv 0,5–2°) — kleinere Werte erhöhen ω_n·Δt, danach Audit erneut prüfen.
- Die Experiment-Schalter der Fehlersuche (`SERVO_*_ENABLED`, `FOLLOWER_*`,
  `ARM_GAIN_SCALE`) sind durch die Aktuator-Tabelle ersetzt (Git-Historie: `383c4ef`).

---

## ADR-013: Fingerspitzenkräfte gebündelt als ein zeitgestempeltes JointState-Topic (v5)

**Problem**: ADR-008 sah ein `std_msgs/Float32`-Topic pro Fingerspitze vor. Für alle 10
Fingerspitzen hieße das 20 Graph-Knoten und 10 Topics ohne gemeinsamen Zeitstempel. Eine
RL-Policy (und später die echte Hand) braucht pro Schritt **einen** Kraftvektor zu einem
Zeitpunkt; wie der echte FSR-Treiber publiziert, ist offen — das Format soll generisch sein.

**Entscheidung**: Nur native Nodes (Leon gegen einen Script Node), in `/Graph/ROS_JointStates`:

| Knoten | Typ | Aufgabe |
|---|---|---|
| `ReadContact_<finger>` ×10 | `isaacsim.sensors.physics.IsaacReadContactSensor` | Kraft (N, float) je `<Fingertip-Link>/Contact_Sensor` |
| `FingertipForceArray` | `omni.graph.nodes.ConstructArray` | 10 Werte → `float[]` (`arrayType = auto`) |
| `FingertipForceToDouble` | `omni.graph.nodes.ToDouble` | `float[]` → `double[]` |
| `FingertipForceTime` | `isaacsim.core.nodes.IsaacTimeSplitter` | Simulationszeit → `sec`/`nanosec` |
| `PublisherFingertipForces` | `isaacsim.ros2.bridge.ROS2Publisher` | `sensor_msgs/JointState` auf `/pib/fingertip_forces` |

Nachricht: `name` = `thumb_left, index_left, middle_left, ring_left, pinky_left, thumb_right,
index_right, middle_right, ring_right, pinky_right`, `effort` = Kraft in N (gleiche
Reihenfolge), `header.stamp` = Simulationszeit, `position`/`velocity` leer. Reader und
Publisher hängen parallel an `on_physics_step` (60 Hz) — der Publisher kann den Wert des
vorigen Physikschritts senden (bewusst: eine `execOut`-Kette würde abreißen, weil `execOut`
nur feuert, wenn der Sensor Daten hat). Aufbau reproduzierbar per
`isaac_sim/tools/build_contact_sensors_v5.py` (Sensor-Prims) und
`isaac_sim/tools/build_fingertip_force_graph_v5.py` (Graph).

**Begründung**: Ein synchroner, selbstbeschreibender Vektor (Namen + Zeitstempel in der
Nachricht) entspricht dem Beobachtungsvektor einer Policy und braucht kein Topic-Syncing.
JointState ist ein Standardtyp (kein eigenes Message-Package); `effort` ist semantisch
zweckentfremdet (Kraft statt Moment), wie schon in ADR-005 geplant.

**Konsequenzen**:
- Verifiziert: Pickup-Demo, rechte Hand an der Dose ≈ Daumen 42 N / Zeigefinger 25 N /
  Mittelfinger 16 N / Ringfinger 2 N — Kräftebilanz geht auf; der Daumen-MCP liegt am
  Stall-Torque (2,94 Nm / ~6,5 cm ≈ 45 N). Topic überlebt Speichern + Neu-Öffnen.
- `/pib/fingertip_force/<finger>` gibt es in v5 nicht mehr.
- **Fallstricke beim Aufbau (alle 2026-10-03 aufgetreten):**
  1. `ConstructArray` wandelt nicht `float` → `double` ("Mismatched array element type …
     expected 'double', got 'float'") → `ToDouble`-Knoten dahinter.
  2. Über `og.Controller` gesetzte Werte/Verbindungen landen nur im **laufenden** Graph, nicht
     in der USD. Beim nächsten Neuaufbau aus der USD verwirft der `ROS2Publisher` seine
     dynamischen Eingänge ("remove dynamic attributes") → leere Nachrichten. Fix: die
     dynamischen Publisher-Eingänge (alle JointState-Felder) direkt in der USD anlegen und
     verbinden; dann meldet er beim Laden "reuse of existing dynamic attributes". Nach jedem
     Graph-Skript: speichern **und neu öffnen**, erst dann testen.
  3. Umbenennen/Verschieben von Graph-Knoten im **Stage-Tree** und "Make Compound" arbeiten
     auf dem laufenden Graph — mit einem davon abweichenden USD-Stand entstand ein Zustand,
     der bei Play reproduzierbar im Kontaktsensor-Plugin abstürzte (Physik-Warmup). Lösung
     war ein Neuaufbau aus dem committeten Stand. Compound daher vorerst nicht verwendet.
     **Korrektur 2026-10-04:** Der Compound war trotzdem in der committeten USD
     (`/Graph/ROS_JointStates/compound/Subgraph` mit allen 10 Readern + Publisher, schon in
     `b6b414d`). Jede frisch geöffnete Stage stürzte bei Play ab; gelaufen war es nur in
     Sessions, in denen die Knoten vorher per Skript gebaut wurden — „überlebt Speichern +
     Neu-Öffnen" stimmte nicht. Erkennen: Backtrace mit `libisaacsim.sensors.physics.plugin.so`
     über `omni.graph.action_core` in `initialize_physics`/`_warm_start` (Kit-Log), auch bei
     deaktiviertem Graph-Prim. Behoben: Compound-Prim offline per `Sdf` aus der USD gelöscht,
     Knoten per `build_fingertip_force_graph_v5.py` flach neu gebaut, gespeichert, neu
     geöffnet — Play, Pickup-Demo und `/pib/fingertip_forces` laufen. Prüfen, dass kein
     Compound in der USD steckt: Graph-Inventur (`inspect_action_graph.py`) bzw. nach Prims
     mit „compound" im Pfad suchen.
  4. `og.Controller.edit(graph, {DELETE_NODES: [...]})` stellt Pfad-Strings den Graph-Pfad
     voran → Knoten-Objekte übergeben.
- Für RL: Training in Isaac Lab nutzt diesen Graph nicht (`ContactSensorCfg` über PhysX);
  das FSR-Modell (Normalkraft, Sättigung, Rauschen, Schwelle, Entprellen) gehört in die
  Trainingsumgebung.

---

## ADR-014: Handgelenk-Pleuel — Gelenkgrenzen und Aktuatormodell (v5)

**Problem**: Das v5-Handgelenk wird nicht direkt vom ST3215 bewegt, sondern über ein Pleuel
(Viergelenk: Kurbel am Servo → Pleuel → Hebel an der Handfläche). Das Modell nahm direkten
Antrieb an (2,94 Nm, 270 °/s am Gelenk) und Grenzen [−90°, +30°] aus dem Onshape-Mate.

**Entscheidung**: Maße aus Onshape (Kurbel 6 mm, Pleuel 115 mm, Hebel 12 mm, Gestell
115,43 mm). Die Kurbel ist umlauffähig (Grashof), der Hebel schwenkt zwischen den beiden
Totlagen genau 60° bei 180° Kurbelwinkel → Grenzen **[−60°, 0°]** (−60° = voll nach innen
gebeugt; Vorzeichen-Ausnahme, siehe `docs/conventions.md`). In Onshape korrigiert, URDFs und
USDs ohne Neuimport nachgezogen. Übersetzung analytisch (`config/pib_hand_config_v5.py` →
`wrist_transmission()`): Mitte n ≈ 2,0, an den Totlagen → ∞.
- **Isaac Sim** (PhysX kann nur konstante Grenzen): Servo-Werte mit der Übersetzung der
  Bereichsmitte aufs Gelenk umgerechnet — 5,87 Nm, 135 °/s, Armature × n² = 0,02 kg·m²
  (`TRANSMISSIONS` → `servo_actuator()`).
- **Isaac Lab**: NVIDIAs `RemotizedPDActuatorCfg` (Referenz: Spot-Knie,
  `isaaclab_assets/robots/spot.py`) mit Tabelle Winkel → Moment (`wrist_lookup_table()`),
  nahe den Totlagen bei 12 Nm gekappt (Leon).

**Begründung**: NVIDIA-Muster für gestängegetriebene Gelenke; ein geschlossenes Viergelenk
in PhysX (Gelenk außerhalb der Artikulation) wäre weniger stabil und vom URDF-Import nicht
abgedeckt — NVIDIA meidet das selbst (Inspire-Hand → Mimic Joints).

**Konsequenzen**:
- Handgelenk real etwa doppelt so stark und halb so schnell wie bisher modelliert; Durchhängen
  in Ruhe von −3,6° auf −0,2°.
- Annahme: 0° liegt an der „gestreckten“ Totlage (Übersetzung fast symmetrisch, unkritisch).
- Explizite PD-Regelung in Isaac Lab stabil (`check_hand_asset.py`); Verzögerung vorerst 0
  (Spot: 0–4 Physikschritte, später als Sim-to-Real-Maßnahme).

---

## ADR-015: RL-Greifen als Proof of Concept in Isaac Lab (linke v5-Hand)

**Problem**: Ziel ist eine Greif-Policy für die reale linke v5-Hand (8 Servos, 5 FSR an den
Fingerspitzen), die auf einem STM32N657 (NUCLEO-N657X0, Neural-ART-NPU) laufen soll. Zeit
für den ersten Schritt: etwa eine Woche — Proof of Concept in der Simulation.

**Entscheidung**: Vorgehen nach NVIDIA-Referenzen, wo immer möglich:
- **Asset**: eigener `onshape-to-robot`-Export nur Unterarm + Hand
  (`pib_hand_left_urdf_v5/`), importiert als `isaac_sim/usd/pib_hand_left_v5.usd`; Mimic
  Joints, Limits, Antriebe und Self-Collision per `bake_hand_asset_v5.py` eingebrannt (Isaac
  Lab führt `start.py` nicht aus). Filtered Pair Unterarm ↔ Daumen-Rotator (Convex Hull des
  Unterarms blockierte den Rotator). Isaac Lab übernimmt die PhysX-Mimic-Kopplung aus der
  USD (GPU, Δ ≤ 0,01°).
- **Aufgabe** (`isaac_lab/pib_grasp/`) als abgespeckte Kopie von Isaac Labs **Dexsuite**
  (Kuka-Allegro-Lift): Hand fest, seitlich (Daumen oben), Dose Ø 6 cm vor der Handfläche;
  ab 2 s senkt sich ein kinematischer Tisch um 10 cm (≙ Arm hebt an), Erfolg = Dose bleibt.
- **Asymmetric Actor-Critic**: Policy sieht nur reale Sensoren — 8 Servo-Gelenkwinkel, 5 FSR
  (auf 20 N gekappt wie Dexsuite), letzte Aktion, 5 Schritte Verlauf (105 Werte); Critic
  zusätzlich Objektlage/-geschwindigkeit, alle Gelenke, Objekt-Kontaktkräfte, Phase.
- **Aktion**: relative Gelenkposition auf die 8 Servos (Dexsuite), Schritt 0,1 rad
  (Handgelenk/Unterarm 0,03 rad), Policy 60 Hz.
- **Belohnung**: Annäherung, Daumen-Gegengriff (beide Dexsuite), Halten nach dem Absenken
  (Hauptterm), Strafen für Kraft > 15 N, Aktionsgröße/-sprünge, Abbruch.
- **Randomisierung**: Reibung, Dosenmasse/-größe/-lage, Servo-Gains ±25 %, zufällige
  Gelenk-Startstellung (Daumen-Rotator 0–90°).
- **PPO** (`rsl_rl`, Werte aus Dexsuite), Actor 256-128-64 (klein, für die NPU).
- **Installation** nach NVIDIA-Doku in einer **eigenen conda-Umgebung** (`env_isaaclab`,
  Miniconda) — nicht in Isaac Sims Python.

**Begründung**: Dexsuite ist NVIDIAs aktuelle Referenz für dexterous Lift/Grasp in Isaac Lab
(Gewichte, Clip, Aktionsart, Randomisierung übernommen). Policy-Beobachtungen auf reale
Sensoren beschränkt, damit sie auf der echten Hand laufen kann.

**Konsequenzen**:
- Machbarkeitstest ohne Policy (`scripted_grasp_test.py`): Daumen-Rotator 0° → 0/16 gehalten,
  90° → 14–15/16 — die Szene ist lösbar, Opposition ist entscheidend.
- Probelauf (1024 Umgebungen, 300 Iterationen, ~10 Mio. Schritte, ~10 min auf RTX 3060 Ti):
  Anteil fallengelassener Dosen 100 % → 19 %, Daumen-Gegengriff 0 → 0,38 — die Policy findet
  die Opposition selbst. ONNX-Export über Isaac Labs `play.py`.
- **Fallstricke** (alle 2026-10-04):
  1. Isaac Lab ohne Umgebung installiert landet in der gerade aktiven Python (hier zuerst die
     Projekt-`.venv`, danach Isaac Sims eigenes Python mit 100 Fremdpaketen) → immer
     `env_isaaclab`; Isaac Sims Python hat nur `pip`, `setuptools`, `psutil`, `starlette`.
  2. `flatdict` baut nur mit `setuptools<81` ohne Build-Isolation (`pkg_resources`).
  3. `ContactSensorCfg` mit Objekt-Filter funktioniert nur, wenn ein Sensor **genau einen**
     Prim abdeckt (Isaac-Lab-Doku) → ein Sensor je Fingerspitze, wie Dexsuite.
  4. `simulation_app.close()` hängt nach Skriptende minutenlang → Bericht schreiben, dann
     `os._exit(0)`; vorher `stdout` flushen.
- Bekannte Sim-to-Real-Lücken: lineare Fingerkopplung (bis ~22° Abweichung, Spitzenkraft
  ~2× zu hoch), idealisierte FSR, keine Latenz, geschätzte Servo-Gains/Armature,
  Vollmaterial-Massen, Convex Hulls, int8 noch nicht geprüft.

---

## ADR-016: Experiment-Framework und Bewertungsprotokoll für das RL-Greifen

**Problem**: Der Probelauf (ADR-015) wurde nur über die Trainingskurve und ein Video bewertet.
Die Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar, sobald sich die
Belohnung ändert; welcher Code-Stand einen Lauf erzeugt hat, war nicht gesichert (Isaac Lab
speichert nur den Git-Stand von Isaac Lab selbst); Hypothese und Schluss standen nirgends.

**Entscheidung**: `experiments/` (im Git) mit einem `experiment.yaml` je Experiment (Hypothese,
genau eine Änderung zu den Eltern, Bedingungen, Training, Schluss) und `isaac_lab/experiments.py`
(`new`, `bench`, `run`, `eval`, `done`). Ablauf in 7 Schritten: Planen → Prüfen (Kurztest) →
Trainieren (≥ 3 Seeds) → Evaluieren → Sichten (Video) → Bewerten (Urteilsvorschlag) →
Dokumentieren & Entscheiden. Bewertungsprotokoll `eval-v1` (`isaac_lab/eval_policy.py`):
1000 Episoden, Bewertungs-Seed 1000, deterministischer Actor, nur die Abbrüche „gefallen“ und
„instabil“; Hauptmetrik **Aufgabenerfolg** (gehalten und Anforderung der Bedingung erfüllt),
dazu Haltequote, Fehlerarten und Leitplanken (Kippwinkel, Unterarm, Griffkraft, Kraft > 15 N,
Stall-Anteil, Absinken, Unruhe); Statistik per zweistufigem Bootstrap (Seeds, Episoden),
Urteilsvorschlag nach fester Regel. Ergebnisse je **Bedingung** (Objekt × Startpose ×
Anforderung), nicht je Griffart. Lokal (TensorBoard + Dateien), kein externer Dienst.
Details: `experiments/README.md`.

**Begründung**: Übliche Praxis — Henderson et al. 2018 (Seeds), Agarwal et al. 2021 / rliable
(Bootstrap-Konfidenzintervalle), NeurIPS-Reproduzierbarkeits-Checkliste, YCB-Protokolle
(Erfolgsquote je Objekt/Startlage). Dexsuite unterscheidet Lift und Reorient nur im
Erfolgskriterium → Anforderung (z. B. aufrecht) ist eine Eigenschaft der Aufgabe/des Objekts,
nicht der Griffart. Griffarten strukturieren weder Dexsuite noch DextrAH, UniDexGrasp++ oder
HORA; dort zählt Erfolg je Objekt und bekannte vs. neue Objekte.

**Konsequenzen**:
- Je Lauf zusätzlich `meta.json` (Commit, Versionen, GPU, Befehl), `pib_hand_sim.diff` und die
  nicht eingecheckten Dateien; Isaac Labs `train.py` hängt am Ende → Prozess wird 60 s nach dem
  letzten Checkpoint beendet.
- Die Bewertung schaltet trainingsspezifische Abbrüche ab (Kippen wird gemessen) — so bleiben
  Experimente mit unterschiedlichen Trainingsabbrüchen vergleichbar.
- EXP-000 (Probelauf) unter eval-v1: Haltequote 86,1 %, Aufgabenerfolg 0,0 % (Kippwinkel
  Median 104°, Unterarm 90°, Stall-Anteil 99,6 % — die Policy gibt fast immer Vollausschlag).
- PhysX (GPU) ist nicht bitgenau reproduzierbar — reproduzierbar heißt statistisch gleich.
- `experiments.py` läuft mit System-Python; `conda activate env_isaaclab` setzt `PYTHONPATH` auf
  Isaac Sims Pakete, das Skript blendet sie für sich selbst aus.

---

## ADR-017: Belohnung nach Dexsuite statt Eigenbau — Lehren aus EXP-001 bis EXP-004

**Problem**: Der Probelauf (EXP-000) hielt die Dose nur, indem der Unterarm sie auf die
Handfläche kippte (Aufgabenerfolg ≤ 45°: 2 %). Drei eigene Korrekturversuche scheiterten
vollständig (0 % gehalten): Kippabbruch bei 20° (EXP-001), dazu 5× Training (EXP-002), Halten
nur multiplikativ mit Aufrecht (EXP-003). Die Policy spreizte die Finger und berührte die Dose nicht.

**Entscheidung**: Belohnungssatz von Isaac Labs Dexsuite übernehmen (EXP-004), Zielpose ersetzt
durch „nach dem Absenken auf Höhe gehalten, aufrecht“: Annäherung (std 0,4), Gegengriff (0,5),
dichtes Halten (2) und Aufrecht (4, std 1,5 rad) ab dem Absenken × Gegengriff, scharfer Erfolg
Halten × Aufrecht (10, rot_std 0,5), gekappte Aktionsstrafen (Dexsuite-Funktionen), keine
Kraftstrafe, kein Kippabbruch. Anforderung der Bedingung: Kippwinkel ≤ 45° (verschlossene Packung).

**Begründung** (gemessen, `experiments/`):
- Annäherung mit std 0,1 auf den größten Fingerabstand war praktisch 0 (0,001–0,003/s); die
  eigene, unbegrenzte Kraftstrafe (> 15 N) war am Anfang 3× größer → Berühren kostete, Annähern
  brachte nichts → Finger gespreizt.
- Ohne dichtes, additives Haltesignal wird Halten nie entdeckt: ein früher Griff kippt die Dose
  ~50° (Machbarkeitstest), Halten × Aufrecht ist dort ≈ 0.
- Strenger Orientierungsabbruch ist bei NVIDIA nur üblich, wenn das Objekt schon gegriffen ist
  (deploy/gear_assembly); blinde Policies in der Literatur (HORA) starten aus einem Griff-Cache.
- Aufrecht-Belohnung erst ab dem Absenken — auf dem Tisch steht die Dose von selbst aufrecht
  (sonst Belohnung fürs bloße Antippen; Dexsuite-Lift hat keinen Orientierungsterm).

**Konsequenzen**:
- EXP-004: Aufgabenerfolg 77 % [56–89] (Seeds 88/56/88), Haltequote 90 %, Kippwinkel 27°,
  Unterarm 26° — der blinde Actor lernt aufrechtes Halten in 300 Iterationen.
- Offen: Zweifinger-Pinzettengriff (Daumen + ein Finger; der Gegengriff-Term verlangt nur das,
  wie bei Dexsuite), Griffkraft/Stall hoch (Kraftstrafe vorerst bewusst nicht, Leon), Seed-Streuung.
- Ein Fehler im Halteterm behoben: Absinken gegen die Höhe beim Absenken statt Standardhöhe
  (±10 % Größe → bis 7,5 mm Versatz).
- Arbeitsregel: zuerst das NVIDIA-Rezept vollständig, eigene Terme nur einzeln und begründet;
  Belohnungsanteile (`Episode_Reward/*`) vor dem Lauf auf Größenordnung prüfen (`_reward_diag.txt`).
- **Korrektur 2026-10-08:** Die Annäherung (`mdp.fingertips_to_object`, eigene Kopie von Dexsuites
  `object_ee_distance`) hatte die Fingerspitzen als Standardargument `SceneEntityCfg(..., body_names=…)` in der
  Funktionssignatur. Isaac Lab löst SceneEntityCfg nur in den `params` eines Terms auf — `body_ids` blieb
  `slice(None)`, der Term maß den größten Abstand **aller** Handkörper (inkl. Unterarmansatz) und war praktisch
  konstant (≈ 0,34/s). Die Annäherung hat in EXP-004–011 also kaum geformt; die Schlüsse oben zur Annäherung
  (std 0,1 → 0,4) sind entsprechend schwächer. Behoben in `RewardsDexsuiteCfg` (EXP-012): Dexsuite-Funktion,
  Körper in den `params`. Regel: SceneEntityCfg mit Namen nie als Standardargument, immer über `params`.

---

## ADR-018: Greif-Architektur — Planer oben, ein Spezialist je Greifart unten

**Problem**: Der Actor ist blind (8 Gelenkwinkel, 5 FSR) und läuft auf dem STM32N657. Er kennt weder das
Objekt noch die Handausrichtung — ein einziges Netz kann nicht wissen, ob es seitlich an einer Milchpackung
oder von oben an einem Apfel greifen soll. Offen war: regelbasiert Spezialisten wählen oder ein Netz für alles?

**Entscheidung** (Leon, 2026-10-07): zweistufig. Oben wählt ein Planer (zuerst Regeltabelle, später gelernt,
z. B. VLM/GraspGen) Objektkategorie → Startpose + Greifart, der Arm (IK-Team) fährt die Vorgreifpose an, unten
schließt die Hand-Policy reflexartig. **Ein Spezialist je Greifart**, der alle Objekte seiner Kategorie über
Tasten abdeckt: Kraftgriff seitlich (Milch, Becher, Flasche), Griff von oben (Obst); Hakengriff (Tasche)
zurückgestellt. Später ggf. Destillation in ein Netz mit Greifart als One-Hot.

**Begründung**: Stand der Technik ist zweistufig — GR00T N1.6 (System 2 plant, System 1 führt aus),
DexGraspVLA (VLM-Planer + gelernter Regler), GRIT (Greifart als Kommando an eine Policy). Ein Netz für alles
(DextrAH-RGB) sieht das Objekt. Erst Spezialisten, dann destillieren (UniDexGrasp++, UniGraspTransformer) —
die Spezialisten sind dann die Lehrer. Mehrere Spezialisten passen auf die NPU (je ~70 kB int8).

**Konsequenzen**:
- Schnittstelle zum IK-/Greifpunkt-Team: Vorgreifpose je Greifart (Sim: Handfläche 3,5 cm vor der
  Objektoberfläche) und ein Signal „Griff steht“ für das Anheben (Sim: Tisch senkt sich fest nach 2 s) — offen.
- Seitlich greifen braucht ≥ ~15 cm Objekthöhe (Fingerspitzen 2,5–16,5 cm über dem Tisch); flache Objekte
  gehören zu „von oben“.
- `docs/architecture.md` → „Ziel-Architektur Greifen“.

---

## ADR-019: Benchmark-Bedingungen und Leaderboard nach rliable

**Problem**: Mit mehreren Objekten und Experimenten ohne eigenes Training (Transfer) war nicht mehr auf einen
Blick zu sehen, welche Policy am besten ist; die Trainings-Belohnung ist nicht vergleichbar (ADR-016), und mit
3 Seeds täuschten einzelne Seeds (EXP-004: 77 % mit 3, 48 % mit 5 Seeds).

**Entscheidung**: Jede Policy (Experiment mit eigenem Training) wird unter festen **Benchmark-Bedingungen**
bewertet (`experiments.py` → `BENCHMARK`: Zylinder Ø 6 cm, Ø 8 cm, Quader 7 × 7 × 20 cm, je Kippwinkel ≤ 45°).
`experiments/leaderboard.md` (von `done` erzeugt) sortiert nach dem **IQM des Aufgabenerfolgs über alle
Objekte** (Seeds × Objekte gepoolt, stratifizierter Bootstrap) und zeigt die **probability of improvement**
P(Platz 1 > X) — gesichert, wenn die untere KI-Grenze über 0,5 liegt. Dazu IQM je Objekt, Verhalten und der
beste Seed als Einsatz-Kandidat. Je Policy/Seed/Objekt Verlauf über die Episode und Video (`medien`).

**Begründung**: Agarwal et al. 2021 (rliable, *Deep RL at the Edge of the Statistical Precipice*): IQM über
Aufgaben × Läufe mit stratifiziertem Bootstrap und P(X > Y) statt Mittelwert und Rangfolge allein; Ergebnis je
Objekt bleibt sichtbar (YCB-Protokolle). Einzige Stelle, an der über Bedingungen zusammengefasst wird
(Leon, 2026-10-08).

**Konsequenzen**:
- EXP-006 ist Platz 1 und neue Baseline; EXP-005/007/011 statistisch gleichauf, EXP-004 gesichert schlechter.
- Neue Objekte im Benchmark erfordern die Nachbewertung aller Policies (`leaderboard --bewerten`, ~1 min je
  Lauf und Objekt); Testobjekte (nie trainiert) als eigene Bedingung kennzeichnen.
- Videos aller Seeds nicht im Git (Hugging Face), die besten je Policy schon (`beste_videos/`).
- **Ergänzung 2026-10-08 — Auswertung v2:** EXP-012 (3 von 5 Seeds greifen, 2 gar nicht) zeigte, dass das Mittel
  über alle Seeds zwei Fragen vermischt. Getrennt nach Chan et al. 2020 (*Measuring the Reliability of RL
  Algorithms*): **Leistung** (IQM der erfolgreichen Seeds) und **Zuverlässigkeit** (erfolgreiche Seeds k/n,
  Clopper-Pearson, exakter Fisher-Test); Gesamt-IQM bleibt Sortierschlüssel des Leaderboards. Befund: wenn das
  Training gelingt, liegen alle Rezepte bei 68–75 % Leistung — sie unterscheiden sich vor allem in der
  Zuverlässigkeit, und der Quader ist überall der Engpass. Bericht auf einen Kopf mit fünf Zeilen verdichtet,
  Details ausklappbar (`experiments/README.md` → „Auswertung v2“).

---

## ADR-020: Regel-Baselines als Vergleich für RL

**Problem**: Ob RL überhaupt mehr leistet als ein programmierter Griff, war offen; der Machbarkeitstest
(2026-10-04: Daumen auf 90°, dann zu → 14–15/16) deutete an, dass eine einfache Regel stark ist.

**Entscheidung** (Leon, 2026-10-08): Regelbasierte Griffe als eigene Experimente im selben Aktionsraum, mit
denselben Sensoren und demselben Protokoll wie die Policies (`eval_policy.py --regel`, `experiments.py` →
`run_rule`): „alle schließen“ (Heuristik, wie Chen et al. 2022) und „schließen bis Kontakt“ (taktiler Reflex,
Hsiao et al. 2010). Parameter per kleinem Raster mit eigenem Bewertungs-Seed (2000) gewählt, final eval-v1 —
Auswahl und Bewertung getrennt (Patterson et al. 2024). Eine Zeile im Leaderboard je Regel.

**Begründung**: Gelernte Policies gegen eine faire Heuristik zu stellen ist übliche Praxis; ohne sie lässt sich
der Mehrwert von RL nicht beurteilen.

**Konsequenzen**:
- EXP-014 „alle schließen“ 71 %, EXP-015 „bis Kontakt“ 68 % Leistung; RL (EXP-013) gesichert besser (+6 PP),
  aber die Regel ist ruhiger, kippt weniger, nutzt ~5 Finger; Quader bei beiden gleich schwach.
- Folgerung: das Benchmark misst noch vor allem „festhalten“ — RL soll sich bei Dingen beweisen, die eine Regel
  nicht kann (Kraft dosieren, schwere/rutschige Objekte, Störungen, ungenaue Vorgreifpose); YCB mit echter Masse
  ist der erste Schritt dahin.
- Für jede weitere Greifart gehört eine eigene Regel-Baseline dazu.

---

## Template für neue Entscheidungen

**Problem**: [Was ist das konkrete Problem oder der Trade-off?]

**Entscheidung**: [Was wurde entschieden?]

**Begründung**: [Warum diese Option?]

**Konsequenzen**: [Was ändert sich, was muss beachtet werden?]
