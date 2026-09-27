# RL-Grasping — Ursprungs-Prompt, Bewertung, Klärungen

Festgehalten am 2026-09-27, direkt nach der Sehnendynamik-Session auf
`experiment/omnigraph-lightweight` (ADR-009). Dieser Branch (`feature/rl-grasping`) wurde
danach von dort abgezweigt.

## Herkunft

Leon hat den unten stehenden Prompt mit Gemini vorbereitet und Claude Code zur Bewertung
vorgelegt, bevor irgendetwas umgesetzt wurde. Wörtlich übernommen, keine Korrekturen am
Text selbst — die Korrekturen stehen in den Abschnitten danach.

## Ursprungs-Prompt (Gemini, wörtlich)

> ## 1. Kontext & Zielsetzung
> Wir implementieren eine **feinfühlige (dexterous) Greifaufgabe für einen humanoiden
> Roboter** mittels Reinforcement Learning (RL) in **NVIDIA Isaac Lab**.
> Das übergeordnete IK-Framework (Inverse Kinematik) bringt die Handfläche des Roboters
> bereits zuverlässig in die unmittelbare Nähe des Zielobjekts, welches auf einem flachen
> Tisch liegt. Die einzige Aufgabe dieser RL-Policy ist die **Feinkoordination der Finger
> und der Kraftschluss (Force Closure)**, um das Objekt sicher zu greifen und zu
> stabilisieren.
>
> Unser Robotermodell wurde via `onshape-to-robot` in Isaac Sim importiert und liegt als
> voll funktionsfähiges **USD-Asset** vor.
>
> ## 2. Hardware- / Artikulations-Spezifikationen
> * **Basis:** Starr im Raum verankert (`fix_base=True`) am Montagepunkt des Unterarms.
> * **Freiheitsgrade (DoFs / Aktionsraum):** 8 Freiheitsgrade umfassend den **Unterarm und
>   das Handgelenk** (für Rotations- und Positionierungs-Korrekturen) + alle nachfolgenden
>   **Fingergelenke einer 5-Finger-Hand**.
> * **Aktuierung:** Gelenkwinkel-Steuerung (Joint Position Control / PD-Ziele via
>   `ImplicitActuatorCfg`).
> * **Taktiles Feedback:** 5 Hardware-Kraft-/Kontaktsensoren, wobei genau ein Sensor auf dem
>   äußersten Glied (Tip-Link) jedes Fingers platziert ist (Daumen, Zeige-, Mittel-, Ring-
>   und kleiner Finger).
>
> ## 3. RL-Umgebung & Task-Design
> Wir möchten ein benutzerdefiniertes `ManagerBasedRLEnvCfg`-Setup mit folgendem Ablauf
> implementieren:
> * **Der "verschwindende Tisch"-Validierungstrick:** Das Objekt liegt anfangs auf einem
>   festen Tisch. Sobald ein Griff etabliert ist (z. B. zur Hälfte der Trainings-Episode),
>   soll die Kollision des Tisches dynamisch deaktiviert werden (oder eine künstliche,
>   starke Schwerkraft nach unten auf das Objekt wirken). Bleibt das Objekt sicher in der
>   Hand, erhält der Agent einen massiven Erfolgs-Reward. Rutscht es durch und fällt unter
>   die Tischkante, wird die Episode sofort abgebrochen (Early Termination).
> * **Best Practices für den Aktionsraum:** Implementierung einer asymmetrischen
>   Aktions-Skalierung. Die 8 Unterarm-/Handgelenksgelenke sollen kleinere relative
>   Schritte pro RL-Schritt machen dürfen als die agilen Fingergelenke, um wildes Peitschen
>   oder unruhige Bewegungen des Arms zu verhindern.
> * **Beobachtungsraum (Observations):** Zustände von Unterarm/Handgelenk,
>   Fingergelenk-Winkel, taktile Kraft-Magnituden (geglättet durch einen gleitenden
>   Mittelwert / EMA, um das PhysX-Kontaktrauschen zu minimieren) sowie die relative
>   Position/Orientierung des Zielobjekts.
> * **Belohnungsfunktion (Reward):** Eine Balance aus Annäherung (Fingerspitzen zum Objekt)
>   und symmetrischer Kraftverteilung (Force Closure), um zu verhindern, dass die Hand das
>   Objekt wegschiebt. Zudem eine Strafe auf hohe Änderungen der Gelenkgeschwindigkeiten
>   (`action_rate_penalty`) für flüssige Bewegungen.
>
> ## 4. Aufgaben für Claude Code
>
> ### Aufgabe 1: Python-Skelett für die Isaac Lab Umgebung
> Generiere eine vollständige Template-Struktur für unsere Umgebungskonfiguration
> (`GraspingEnvCfg`, die von `ManagerBasedRLEnvCfg` erbt) mit:
> 1. Einer `ArticulationCfg` für unseren Roboter, die die Aktuatoren in `arm_wrist` und
>    `fingers` mit unterschiedlichen Werten für Steifigkeit (`stiffness`), Dämpfung
>    (`damping`) und maximales Drehmoment unterteilt.
> 2. Einer `ContactSensorCfg`, die die 5 Fingerspitzen-Links über reguläre Ausdrücke
>    (Regex) erfasst.
> 3. Benutzerdefinierten MDP-Funktionen für:
>    * Das Berechnen des gleitenden Mittelwerts (EMA) der taktilen Sensorkräfte.
>    * Das Umschalten der Tisch-Kollision oder Objekt-Gravitation ab einem bestimmten
>      Zeitschritt-Schwellenwert.
>    * Einen robusten Force-Closure-Reward basierend auf der Kontaktverteilung mehrerer
>      Finger.
>
> ### Aufgabe 2: Architektur-Integration in ROS2 Control
> Wir nutzen **ROS2 Control** in unserer realen Hardware-Pipeline. Bitte erkläre, wie
> dieses Isaac Lab RL-Setup in unsere bestehende Architektur integriert werden kann:
> 1. Wie sollte der Übergang vom **Controller des IK-Teams** zur **RL-Greif-Policy** auf
>    ROS2-Ebene nahtlos und stoßfrei stattfinden?
> 2. Welche `ros2_control`-Hardware-Schnittstelle oder Controller-Architektur (z. B.
>    `JointTrajectoryController`, `ForwardCommandController` oder ein Custom Real-time
>    RL-Broadcaster) eignet sich am besten, um die von der Policy generierten
>    Delta-Gelenkwinkel auf der echten Hardware auszuführen?
> 3. Wie leiten wir die echten Daten der 5 Kraftsensoren mit minimaler Latenz und hoher
>    Frequenz zurück in den Observation-Vektor der Policy?
>
> Bitte liefere produktionsreifen Python-Code für Aufgabe 1 und eine detaillierte
> systemische Erklärung/Architektur-Skizze für Aufgabe 2.

## Bewertung (Claude Code, vor Beginn jeglicher Umsetzung)

**Konzeptionell solide**: Aufgabenteilung IK (grob) → RL (Feinkoordination/Force Closure)
ist etabliertes Muster. Asymmetrische Action-Skalierung, EMA-Glättung der taktilen Werte,
Action-Rate-Penalty, "verschwindender Tisch"-Validierungstrick — alles Standardtechniken,
nichts Exotisches.

**Zunächst unklar, dann durch Leon geklärt**: "8 Freiheitsgrade Unterarm+Handgelenk" passte
auf den ersten Blick zu keiner Lesart der pib-DOF-Struktur (Schulter/Ellbogen eingerechnet
zu viele, nur Unterarm+Handgelenk zu wenige). Klärung: gemeint sind die **8 realen Servos**
der physischen linken Hand (Handgelenk, Unterarmdrehung, Daumen-Rotator, 5× Finger-/
Daumen-MCP) — nicht 8 beliebige simulierte Gelenke. Die Zahl ist also korrekt, bezieht sich
aber auf Hardware-Servos, nicht direkt auf URDF-Joint-Namen — das Mapping muss beim
Schreiben von `ArticulationCfg` explizit hergestellt werden, nicht aus dem Prompt-Text
übernommen.

**Vor Beginn zu klären/blockierend (Stand 2026-09-27, siehe `CLAUDE.md` „Offene Punkte")**:
- Isaac Lab war auf der Entwicklungsmaschine nicht installiert (`ModuleNotFoundError:
  No module named 'isaaclab'`) — kein Code gegen ungeprüfte API-Namen schreiben.
- Kontaktsensoren: nur `index_right` in der Simulation verkabelt (ADR-008-Muster,
  `experiment/omnigraph-lightweight`), die im Prompt vorausgesetzten "5 Hardware-Kraft-
  sensoren" sind auf Simulationsseite noch nicht vollständig nachgebildet.
- Architektonisch gehörte das Vorhaben (RL-Training, Team-Integrations-Frage aus
  Aufgabe 2) laut `experiment/omnigraph-lightweight`s eigenem `CLAUDE.md` explizit nicht
  auf diesen Branch — daher eigener Branch `feature/rl-grasping`.

**Wichtigster Design-Punkt für Aufgabe 1** (aus der direkt vorangegangenen
Sehnendynamik-Arbeit, ADR-009 auf `experiment/omnigraph-lightweight`): Der Aktionsraum
muss die 8 realen Servo-DOFs sein, PIP/DIP/IP intern über die bereits validierte
`FourBar`-Kopplungsformel berechnet, nicht lernbar — sonst lernt die Policy real
unerreichbare Fingerposen. Siehe `CLAUDE.md` dieses Branches, Abschnitt „KRITISCHER
Design-Punkt: Aktionsraum".

## Entscheidung: eigener Branch statt Fortsetzung auf `experiment/omnigraph-lightweight`

Leon: "eigentlich fände ich es nicht schlimm die Sache auf diesem Repo fortzuführen" —
Rückfrage ergab: gleiches Repo ja (digitaler Zwilling wird sonst dupliziert/muss
synchronisiert werden), aber eigener Branch, weil `experiment/omnigraph-lightweight` sich
bewusst als minimaler Zweig versteht (kein Training-Pipeline-Scope, siehe dortiges
`CLAUDE.md`) und das Repo bereits das Muster "ein Branch = ein eigenes `CLAUDE.md`"
etabliert hat (`feature/ros2-control`). `feature/rl-grasping` erbt den digitalen Zwilling
zum Abzweigungszeitpunkt (Commit `1d0cd9c` auf `experiment/omnigraph-lightweight`,
„Sehnendynamik-Kopplung für v5-Hand via Script Node (ADR-009)").
