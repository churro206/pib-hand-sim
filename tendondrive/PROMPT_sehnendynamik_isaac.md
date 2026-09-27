# Aufgabe: Sehnendynamik der Roboterfinger in NVIDIA Isaac Sim (Action Graph, analytische Kopplung)

## Deine Rolle

Du arbeitest als Experte für Robotik-Simulation, Mehrkörperdynamik, NVIDIA Isaac Sim (OmniGraph / Action Graph, PhysX-Artikulationen) und Python.
Setze die Sehnendynamik eines gekoppelten Roboterfingers in Isaac Sim um.
Die Kinematik der Kopplung ist bereits analytisch gelöst und validiert (siehe unten). Übernimm diese Ergebnisse. Leite sie nicht neu her.

## Arbeitsweise

1. Verschaffe dir zuerst einen Überblick über das Repository. Suche das USD/URDF der Hand, vorhandene Skripte und die installierte Isaac-Sim-Version.
2. Stelle mir die Fragen aus Abschnitt 8, bevor du Code schreibst. Frage nur, was du nicht aus dem Repository ermitteln kannst.
3. Schreibe einen kurzen Umsetzungsplan und warte auf meine Freigabe.
4. Arbeite danach in kleinen, testbaren Schritten (Abschnitt 7). Führe nach jedem Schritt die zugehörigen Tests aus.
5. Verändere das Original-USD nicht. Lege Änderungen in einem eigenen Layer oder in einer Kopie an.
6. Prüfe alle OmniGraph-Knotennamen und Attributnamen gegen die installierte Isaac-Sim-Version. Die Namen haben sich zwischen Version 4.2 (`omni.isaac.core_nodes.*`) und 4.5+ (`isaacsim.core.nodes.*`) geändert. Rate keine Namen. Lies sie aus der Extension oder mit `og.get_node_type(...)` aus.

---

## 1. Mechanischer Aufbau (bekannt)

Die Hand wurde in Onshape konstruiert. Jeder Finger hat 3 Gelenke:

| Gelenk | Name | verbindet |
|---|---|---|
| MCP | Fingergrundgelenk | D50-Finger_palm_connection → D52-Finger_proximal |
| PIP | Fingermittelgelenk | Grundglied → Mittelglied |
| DIP | Fingerendgelenk | Mittelglied → D54-Finger_distal / D55-Finger_tip |

- Der Finger hat **1 Freiheitsgrad**. Nur das MCP wird angetrieben (über die Sehne).
- PIP und DIP sind über zwei starre Kopplungsstangen zwangsgekoppelt:
  - **D51-Coupling-Bar-Proximal:** Pin A (am Palm, beim MCP) → Pin B (am Mittelglied, beim PIP)
  - **D53-Coupling-Bar-Distal:** Pin C (am Grundglied, beim PIP) → Pin D (am Endglied, beim DIP)
- Jede Kopplung ist ein **Viergelenkgetriebe**. Die Nicht-Linearität entsteht aus dieser Geometrie. Sie entsteht nicht aus Nocken oder Rollen.
- Onshape-Variablen: `#coupling_bars_arm_1 = 7 mm`, `#coupling_bars_arm_2 = 7 mm`, `#pretension = 20 deg`, `#gap = 0,6 mm`.
  `#pretension` beeinflusst die Kopplungsgeometrie nicht. Die Validierung passt ohne diesen Wert. Die Bedeutung ist vermutlich eine Vorspannung der Sehne oder einer Rückstellfeder. **Kläre das mit mir.**

## 2. Geometrie (Skizze „Side view“, Right-Ebene, mm)

Koordinaten: Ursprung = linke untere Ecke der Skizze. y = Fingerachse (gestreckt). Palmarseite = −x.
In Onshape-Weltkoordinaten entspricht die Skizzen-y-Achse der Welt-Z-Achse und die Skizzen-x-Achse der Welt-Y-Achse.

| Punkt | x | y |
|---|---|---|
| MCP-Drehpunkt | 9,3 | 38,0 |
| PIP-Drehpunkt | 8,4 | 74,0 |
| DIP-Drehpunkt | 7,5 | 105,0 |

- Kurbelradius aller Pins: r = 7 mm.
- Kurbeln (Pin A, Pin C) in gestreckter Lage bei α = 225° (unten-palmar). Schwingen (Pin B, Pin D) bei β = 315° (unten-dorsal).
- Koppellängen aus der gestreckten Lage: L₁ = 37,108 mm, L₂ = 32,280 mm.
- Steglängen: MCP–PIP = 36,011 mm, PIP–DIP = 31,013 mm.
- Vorzeichen: Beugung (Flexion) = positiver Winkel.

## 3. Analytische Kopplung (validiert)

Die Kopplung hat die Form **θ_PIP = F₁(θ_MCP)** und **θ_DIP = F₂(θ_PIP)**. Beide Funktionen haben dieselbe Struktur.
Betrachte jede Kette im Koordinatensystem des Glieds zwischen den Gelenken (Kette 1: Grundglied, O₁ = MCP, O₂ = PIP; Kette 2: Mittelglied, O₁ = PIP, O₂ = DIP):

```
A      = O1 + r * (cos(alpha - t_in), sin(alpha - t_in))
d      = O2 - A
K      = (L^2 - |d|^2 - r^2) / (2 r)
t_out  = atan2(d_y, d_x) - arccos(K / |d|) - beta
```

- Das Minuszeichen vor `arccos` wählt den Montagezweig mit t_out(0) = 0.
- Eine Lösung existiert nur für |K| ≤ |d|. **Totpunkte:** Kette 1 bei θ_MCP = 104,2°, Kette 2 bei θ_PIP = 102,2° (entspricht θ_MCP ≈ 94°).
- **Arbeitsbereich:** Begrenze θ_MCP auf 0°…90°.
- Die Ableitungen F₁′ und F₂′ (lokale Übersetzung) brauchst du für die Dynamik. Berechne sie analytisch durch implizites Differenzieren der Schließbedingung oder mit Autograd. Verwende keine finiten Differenzen im Regelkreis.

Referenzwerte (Formel und numerische Lösung stimmen auf 3·10⁻¹¹° überein):

| θ_MCP | θ_PIP | θ_DIP | F₁′ = dPIP/dMCP | F₂′ = dDIP/dPIP |
|---|---|---|---|---|
| 0° | 0,00° | 0,00° | 0,600 | 0,550 |
| 30° | 21,47° | 13,73° | 0,828 | 0,726 |
| 60° | 50,16° | 38,16° | 1,102 | 0,991 |
| 73,75° | 66,50° | 55,98° | 1,284 | 1,202 |
| 90° | 90,00° | 90,00° | 1,667 | 1,818 |

- Der Punkt 90°/90°/90° ist exakt. Er folgt aus den symmetrischen 45°-Pins.
- Validierung in Onshape: Die Messung Schraube MCP → Schraube PIP ergab Y = 34,81 mm, Z = 9,21 mm. Daraus folgt θ_MCP = 73,75°. Pixelmessungen an 3 Posen stimmen innerhalb von 3° mit dem Modell überein.

Vorhandene Dateien (lege sie ins Repository, falls sie fehlen):
- `finger_analytisch.py` – Klasse `Viergelenk` mit Formel, Übersetzung und Totpunkt (NumPy).
- `finger_kinematik.py` – numerische Referenzlösung und CSV-Export.
- `finger_action_graph.py` – bestehender Action Graph mit LUT (nur Positionsregelung). Ersetze die LUT durch die analytische Formel.
- `bench.py` – Benchmark: Die analytische Formel mit `torch.compile` ist schneller als jede LUT.

## 4. Ziel: Sehnendynamik statt reiner Positionsvorgabe

Der bestehende Graph setzt nur Positionsziele. Baue jetzt ein **dynamisches Modell**. Eine Sehne erzeugt eine Kraft, und der Finger bewegt sich als gekoppeltes 1-DOF-System. Kontakte mit Objekten müssen physikalisch plausibel zurückwirken.

### 4.1 Sehnenmodell

- Sehnenweg s und MCP-Winkel hängen über den Momentarm r_t(θ_MCP) zusammen: ds = r_t(θ) · dθ_MCP. Die Sehnenführung am MCP ist noch unbekannt (Abschnitt 8). Implementiere r_t als austauschbare Funktion. Beginne mit einem konstanten Radius als Platzhalter.
- Die Sehne ist ein **seriell-elastisches Element** und kann nur ziehen:
  `F_t = max(0, k_t · (s_cmd − s(θ)) + d_t · (ṡ_cmd − ṡ(θ)))`
- Eine Rückstellung (Extensor, Feder oder `#pretension`) wirkt als Moment τ_ret(θ) auf das MCP. Parametriere τ_ret. Setze es zunächst als lineare Feder mit Vorspannung an.
- Eingang des Graphen: **1 Wert pro Finger**. Unterstütze 2 Modi:
  1. Sehnenweg s_cmd (Motorposition × Rollenradius)
  2. MCP-Zielwinkel θ_cmd (wird mit der inversen Beziehung in s_cmd umgerechnet)

### 4.2 Kopplung dynamisch erzwingen

PhysX-Artikulationen erlauben keine geschlossenen Ketten. Bilde die Kopplung deshalb als Zwangsbedingung nach:

- c₁ = θ_PIP − F₁(θ_MCP) = 0, Gradient ∇c₁ = [−F₁′, 1, 0]
- c₂ = θ_DIP − F₂(θ_PIP) = 0, Gradient ∇c₂ = [0, −F₂′, 1]

Empfohlene Umsetzung (prüfe die Stabilität und begründe Abweichungen):
1. **PIP und DIP:** PhysX-Positionsantrieb mit hoher Steifigkeit. Setze die Ziele in jedem Physikschritt aus den **gemessenen** Winkeln: θ_PIP,soll = F₁(θ_MCP,ist), θ_DIP,soll = F₂(θ_PIP,ist). Der implizite PD-Regler von PhysX bleibt auch bei hoher Steifigkeit stabil.
2. **Rückwirkung auf das MCP:** Die Antriebe an PIP und DIP üben die Momente τ₂ und τ₃ aus. Nach dem Prinzip der virtuellen Arbeit muss das MCP die Reaktion tragen. Gib dem MCP deshalb zusätzlich das Moment −F₁′·τ₂ vor. Beim PIP gilt entsprechend −F₂′·τ₃. Ohne diese Rückwirkung verletzt das Modell die Energieerhaltung, und Kontaktkräfte am Endglied bremsen die Sehne nicht.
3. **MCP:** kein Positionsantrieb (Steifigkeit 0). Setze das Moment τ_MCP = r_t(θ)·F_t − τ_ret(θ) + Rückwirkung als Effort-Befehl.
4. **Prüfung:** Die gesamte generalisierte Kraft auf den einen Freiheitsgrad ist Q = τ_MCP + F₁′·τ_PIP + F₁′F₂′·τ_DIP. Logge Q und prüfe die Leistungsbilanz: P_Sehne = F_t·ṡ muss gleich der Summe τᵢ·θ̇ᵢ plus Verlusten sein.

Alternative, falls die Zwangsbedingung instabil wird: Bilde die Kopplungsstangen als eigene Rigid Bodies nach. Schließe die Schleife mit einem Revolute Joint mit `excludeFromArticulation = true`. Nutze diese Variante als Referenz zur Validierung. Sie eignet sich nicht für RL.

### 4.3 Action-Graph-Aufbau

- Auslöser: **On Physics Step** (nicht On Playback Tick). Die Dynamik muss mit der Physikschrittweite laufen.
- Kette: Physikschritt → Gelenkzustand lesen (Positionen, Geschwindigkeiten, Antriebsmomente) → Script Node „FingerTendon“ → Articulation Controller.
- Positions- und Effort-Befehle gehen an verschiedene Gelenke. Prüfe, ob ein Articulation Controller beides mit `jointIndices` kann. Sonst verwende zwei Controller-Knoten.
- Script Node:
  - `setup(db)`: Parameter laden, Gelenkindizes auflösen, Zustand in `db.per_instance_state` anlegen.
  - `compute(db)`: vektorisiert für N Finger (NumPy). Keine Python-Schleife über Gelenke pro Schritt.
  - Parameter als Knoten-Eingänge oder als eine JSON-/YAML-Datei: k_t, d_t, r_t, τ_ret, Antriebssteifigkeit und -dämpfung, Winkelgrenzen.
- Einheiten: Der Articulation Controller erwartet Radiant und SI-Einheiten. `UsdPhysics`-Gelenkgrenzen stehen in Grad. Prüfe außerdem die Meters-per-Unit der Stage.
- Vorzeichen: Prüfe die Drehachse jedes Gelenks im USD. Beugung muss positiv sein. Sonst führe einen Vorzeichenfaktor pro Gelenk ein.

## 5. Kernfunktionen (eigenes Modul, ohne Isaac-Abhängigkeit)

Lege ein Modul `finger_coupling/` an. Es muss sich ohne Isaac Sim testen lassen:

- `coupling.py`: F₁, F₂, F₁′, F₂′ als NumPy-Funktionen und als Torch-Funktionen (identische API, vektorisiert, `torch.compile`-fähig). Alle Winkel in Radiant.
- `tendon.py`: s(θ), r_t(θ), Sehnenkraft, τ_ret, Umkehrung θ_cmd → s_cmd.
- `dynamics.py`: Berechnung der Befehle (Ziele PIP/DIP, Effort MCP) aus Zustand und Eingang.
- Der Script Node importiert dieses Modul. Er enthält selbst keine Physik-Logik.
- Die Torch-Version ist für Isaac Lab / RL vorgesehen. Schreibe die Funktionen so, dass sie später ohne Änderung dort nutzbar sind.

## 6. Tests und Validierung

1. **Unit-Tests (pytest, ohne Isaac):**
   - Die Referenzwerte aus Abschnitt 3 müssen auf 0,01° stimmen.
   - F₁′ und F₂′ müssen mit finiten Differenzen übereinstimmen.
   - NumPy- und Torch-Version müssen identische Werte liefern.
   - Die Schließbedingung |B − A| = L muss auf 1e-9 mm erfüllt sein.
   - Werte außerhalb von 0°…90° müssen begrenzt werden (keine NaN).
2. **Simulationstests (Isaac Sim, headless möglich):**
   - Langsame Rampe θ_cmd von 0° auf 90°: Der Kopplungsfehler |c₁|, |c₂| muss unter 0,5° bleiben.
   - Sprungantwort: Kein Überschwingen über 90°, keine Instabilität.
   - Sehne entlastet (F_t = 0): Der Finger kehrt durch τ_ret in die gestreckte Lage zurück.
   - Kontakt: Ein Block blockiert das Endglied. Die Sehnenkraft muss steigen, und die Kopplung muss erhalten bleiben.
   - Leistungsbilanz aus Abschnitt 4.2 prüfen.
3. **Logging:** Schreibe pro Test eine CSV (Zeit, θ_ist, θ_soll, c₁, c₂, F_t, τ). Erzeuge Plots der Kopplungsfehler.

## 7. Umsetzungsschritte

1. Repository und Isaac-Version analysieren, Fragen stellen, Plan vorlegen.
2. Modul `finger_coupling` mit Unit-Tests.
3. Action Graph nur mit analytischer Positionskopplung (Ersatz der LUT). Test: Rampe.
4. Sehnenmodell und Effort-Steuerung am MCP mit Rückwirkung. Test: Sprung, Entlastung.
5. Kontakt- und Leistungstests, Parameter abstimmen.
6. Erweiterung auf alle Finger (vektorisiert). Daumen nur, wenn ich die Geometrie liefere.
7. Kurze Dokumentation (README): Aufbau, Parameter, Grenzen, Testergebnisse.

## 8. Offene Fragen (vor dem Start klären)

1. Welche Isaac-Sim-Version ist installiert? Arbeite ich mit Isaac Lab?
2. Wo liegt das USD der Hand? Wie heißen die Gelenke und der Articulation-Root-Prim?
3. Wie ist die Sehne am MCP geführt: Rolle mit Radius, Umlenkpunkte oder Ansatzpunkt am Grundglied? Welche Teile sind die pinken Bauteile im Modell?
4. Welcher Antrieb zieht die Sehne (Motor, Rollenradius, maximale Kraft)? Welches Sehnenmaterial (Steifigkeit)?
5. Was bewirkt `#pretension = 20°` (Federvorspannung, Sehnenvorspannung oder Montagewinkel)?
6. Gibt es einen Extensor (Rückstellfeder oder zweite Sehne)?
7. Soll der Eingang des Graphen der Sehnenweg oder der MCP-Winkel sein? Woher kommt der Eingang (UI, ROS 2, Skript)?
8. Welche Physikschrittweite und wie viele Substeps verwendest du?

## Randbedingungen

- Schreibe klaren, kommentierten Python-Code (PEP 8, Type Hints).
- Keine Magie-Zahlen im Code. Alle Parameter gehören in eine Konfiguration.
- Keine LUT und keine numerische Nullstellensuche im Regelkreis. Verwende nur die geschlossene Formel.
- Melde Annahmen ausdrücklich. Markiere Platzhalterwerte im Code mit `# TODO(param)`.
