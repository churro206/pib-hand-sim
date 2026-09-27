# pib-Hand-Sim

Leon, RoboCup 2027 @Home: feinmotorisches Greifen (Force Closure) für die reale linke
pib-Hand per Reinforcement Learning in NVIDIA Isaac Lab.

## Branch `feature/rl-grasping`
Von `experiment/omnigraph-lightweight` abgezweigt (2026-09-27), **nachdem** dort der
digitale Zwilling der Hand fertig war (v5-USD, Sehnendynamik-Kopplung ADR-009,
`ros2_control`-Stack). Dieser Branch **erbt** diesen Zwilling und baut eine RL-Trainings-
umgebung obendrauf — er pflegt nicht die Simulations-/Action-Graph-Seite selbst weiter,
das bleibt auf `experiment/omnigraph-lightweight` (eigenes, dort gültiges `CLAUDE.md`).
Team-Integration/LSTM-Fahrplan liegt weiterhin auf `feature/ros2-control`.

## Session-Start
**Lies zuerst `docs/handoff.md`** — Stand der letzten Session auf diesem Branch. Für den
geerbten Sim-Kontext: `docs/architecture.md`/`docs/decisions.md` (Stand zum Abzweigungs-
zeitpunkt, siehe Hinweisblöcke dort) und `docs/rl-grasping-notes.md` (Ursprungs-Prompt +
Bewertung dieses Vorhabens).

## Reale Hardware (Kontext, nicht simuliert von diesem Branch selbst)
- Physischer Prototyp: **nur die linke Hand + Unterarm** existiert real, kein rechter Arm.
- **8 Servos**, gesteuert über einen STM32 Nucleo: Handgelenk, Unterarmdrehung,
  Daumen-Rotator, sowie je ein Servo pro Finger-MCP (Zeige-/Mittel-/Ring-/kleiner Finger)
  und Daumen-MCP.
- PIP/DIP (Finger) bzw. IP (Daumen) sind **nicht** individuell aktuiert — mechanische
  Kopplung über Kopplungsstangen (Viergelenkgetriebe). In der Simulation bereits korrekt
  nachgebildet: `experiment/omnigraph-lightweight`, ADR-009,
  `isaac_sim/tools/finger_coupling_script_node.py` (`FourBar`-Klasse).
- Taktiles Feedback: FSR-artige Kontaktsensoren, in der Simulation als `IsaacContactSensor`
  nachgebildet (ADR-008-Muster) — bisher nur `index_right` verkabelt, Rest offen (Abhängigkeit
  von `experiment/omnigraph-lightweight`, nicht hier zu lösen).

## Aufgabe dieser RL-Policy
Übergeordnetes IK-Framework bringt die Handfläche bereits zuverlässig in Objektnähe (Objekt
liegt auf flachem Tisch). Die Policy übernimmt **nur** die Feinkoordination der Finger und
den Kraftschluss (Force Closure) — kein Greifpunkt-/Trajektorien-Learning, keine
Armbewegung im großen Maßstab.

## KRITISCHER Design-Punkt: Aktionsraum
Der Aktionsraum der Policy **muss exakt den 8 realen Servo-DOFs entsprechen** — nicht allen
simulierten Gelenken. PIP/DIP/IP dürfen **nicht** unabhängig im Aktionsraum liegen: auf der
echten Hand ist das physikalisch unmöglich (Sehnenkopplung, kein Motor pro Gelenk). Die
Env-Step-Logik muss PIP/DIP/IP intern über **dieselbe** Viergelenk-Formel berechnen wie der
Action-Graph-Script-Node auf `experiment/omnigraph-lightweight`
(`isaac_sim/tools/finger_coupling_script_node.py`, Geometrie/Herleitung validiert in
`tendondrive/finger_analytisch.py` + `daumen_analytisch.py`) — **nicht lernbar**. Sonst
lernt die Policy Posen, die auf der realen Hand unerreichbar sind, und der Sim-to-Real-
Transfer bricht. Das gilt für Observation UND Action Space gleichermaßen (beobachtete
PIP/DIP/IP-Winkel sind redundant zum MCP-Winkel, kein unabhängiger Freiheitsgrad).

## Stack (Ziel — noch nicht installiert)
- **NVIDIA Isaac Lab** (`ManagerBasedRLEnvCfg`, `ArticulationCfg`, `ContactSensorCfg`,
  `ImplicitActuatorCfg`) — **auf dieser Maschine noch nicht installiert**
  (`ModuleNotFoundError: No module named 'isaaclab'`, kein `IsaacLab`-Verzeichnis
  gefunden, Stand 2026-09-27). Erster konkreter Schritt.
- Isaac Sim 5.1 (gemeinsam mit `experiment/omnigraph-lightweight`)
- PyTorch (Isaac-Lab-Abhängigkeit), RL-Library noch nicht festgelegt (z.B. `rsl-rl`,
  `skrl` — Isaac Lab bringt Referenz-Integrationen mit, gegen installierte Version prüfen)

## Isaac Sim / Isaac Lab API-Regeln
- **Nie Isaac-Lab-Klassennamen/-Signaturen raten** — gegen die tatsächlich installierte
  Version prüfen, bevor Code geschrieben wird (analog zur OmniGraph-Node-Regel auf
  `experiment/omnigraph-lightweight` — API-Namen/Argumente ändern sich zwischen Isaac-Lab-
  Versionen).
- **DOF-Namen/-Zahl nie annehmen** — aus `config/pib_hand_config_v5.py` (fehlt noch) bzw.
  direkt aus der v5-URDF/USD ableiten, nicht aus dem Ursprungs-Prompt übernehmen (dessen
  "8 DOFs" bezieht sich auf die 8 realen Servos, nicht 1:1 auf URDF-Joint-Namen — Mapping
  Servo→Joint-Namen muss explizit hergestellt werden, siehe oben).
- Script-Node-Sandbox-Gotcha (falls Action-Graph-Code für Sim-Vorbereitung nötig wird):
  siehe `docs/conventions.md` (geerbt) → Klassen/Instanzen nur in `setup(db)`, nicht auf
  Modulebene.

## Offene Punkte (Start dieses Branches)
- Isaac Lab installieren.
- Echte v5-Gelenkstruktur (Namen, Limits, Trägheiten) gegen die im Ursprungs-Prompt
  behauptete 8-DOF-Beschreibung abgleichen, bevor `ArticulationCfg` geschrieben wird.
- `config/pib_hand_config_v5.py` (Abhängigkeit von `experiment/omnigraph-lightweight`,
  dort noch offen).
- Kontaktsensor-Abdeckung nur `index_right` (Abhängigkeit von
  `experiment/omnigraph-lightweight`, dort als nächstes geplant).

## Nicht Teil dieses Branches
Sim-Infrastruktur/Action-Graph/Kontaktsensor-Ausbau selbst — das ist
`experiment/omnigraph-lightweight`. Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-
Interface an echter Hardware), LSTM-Gelenkdynamik, AS5600-Sensordaten — `feature/ros2-control`.

→ Sim-/Digitaler-Zwilling-Kontext: `docs/architecture.md`, `docs/decisions.md` (ADR-001–009,
geerbt von `experiment/omnigraph-lightweight`)
→ RL-Ursprungs-Prompt + Bewertung: `docs/rl-grasping-notes.md`
→ Aktueller Stand: `docs/handoff.md`
