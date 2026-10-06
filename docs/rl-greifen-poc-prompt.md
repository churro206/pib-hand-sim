# Auftrag: RL-Greifstrategien für verschiedene Objekte – Proof of Concept (RoboCup@Home 2027)

## Wie dieser Prompt gemeint ist

Dieser Prompt ist **eine Sammlung von Empfehlungen, keine Vorschrift.**
Sie stammen aus einer Webrecherche (NVIDIA-Dokumentation und -Blogs, aktuelle Forschung, RoboCup-Regelwerk, ST-Datenblätter). Den Stand unseres Repositorys kenne ich dabei nur teilweise.
**Du kennst das Repository, die laufende Isaac-Lab-Umgebung und die bisherigen Entscheidungen besser.** Prüfe jede Empfehlung gegen diesen Kontext:
- Übernimm, was passt.
- Weiche ab, wo der Code oder die Messungen etwas anderes nahelegen. Begründe die Abweichung kurz.
- Wenn du eine bessere Lösung siehst, schlage sie vor.
- Wenn eine Empfehlung auf einer Annahme beruht, die im Repository nicht stimmt, sag es mir.

Bevor du größere Änderungen machst: Lege mir einen Plan vor (Phasen, Reihenfolge, was du übernimmst und was du anders machst) und warte auf meine Freigabe.

---

## 1. Ausgangslage (aus meiner Sicht, bitte gegen das Repository prüfen)

- Die Hand läuft in Isaac Lab. Ein erster Testlauf hat ihr bereits beigebracht, einen **Zylinder zu heben**.
- Die Hand hat **8 Servos** (ST3215): Handgelenk, Unterarmdrehung, Daumen-Rotator (CMC) und je ein MCP pro Finger und Daumen. PIP/DIP/IP sind über Viergelenk-Stangen gekoppelt und in der Simulation als **Mimic Joints** umgesetzt (ADR-011, Stufe 1 linear). Das MCP hat `maxForce = 2,94 Nm` (Stall-Torque @ 12 V, Spannung unbestätigt).
- Der Aktionsraum der RL-Policy umfasst die 8 Servo-DOFs (`feature/rl-grasping`, eigenes `CLAUDE.md`).
- Der ST3215 meldet **Position und Last** zurück. Ob echte Kontaktsensoren an den Fingerspitzen verbaut sind oder nur simuliert werden, weißt du besser als ich.

## 2. Ziel und Randbedingungen

**Ziel:** Ein Proof of Concept, der zeigt, dass die Hand **verschiedene Objekte mit unterschiedlichen Griffarten** heben und halten kann: zum Beispiel aufrecht halten (Milch, Becher) oder von unten stützen (Schüssel, Tablett). Es geht um einen PoC, nicht um ein wettbewerbsfertiges System.

| Randbedingung | Folge |
|---|---|
| **Training nur auf einer RTX 3060 Ti (8 GB VRAM)** | zustandsbasiertes RL ohne Kameras im Training, etwa 2048–4096 Umgebungen headless, moderate Objektmenge |
| **Inferenz auf einem STM32N6-Nucleo** (Cortex-M55 800 MHz, Neural-ART-NPU 600 GOPS, 4,2 MB internes RAM, Toolchain ST Edge AI / STM32Cube.AI, Modelle aus ONNX/TFLite) | kleine, quantisierbare Netze (int8), nur Operatoren, die ST Edge AI unterstützt |
| **Zielwettbewerb RoboCup@Home 2027 (Open Platform League)** | Objekte und Griffarten nach dem Regelwerk 2027 auswählen |

## 3. Was RoboCup@Home 2027 verlangt (Regelwerk 2027 Rev-1)

- **Pick and Place:** Besteck und Geschirr in die Spülmaschine, Müll entsorgen, Objekte nach Kategorie ins Regal, Frühstück decken (Schüssel, Löffel, Cerealien, Milch). Optional: Milch und Cerealien gießen.
- **Human-Robot Interaction:** Eine Tasche vom Gast übernehmen und am Zielort abstellen.
- **Objektkategorien:** Geschirr, Besteck, Taschen, Tabletts, Gießbares, schwere, winzige, zerbrechliche und verformbare Objekte. Für den ersten erfolgreichen Griff gibt es einen Bonus.

**Mein Vorschlag für den PoC: 3 Griffarten**

| Griffart | Objekte | Was die Aufgabe ausmacht |
|---|---|---|
| Kraftgriff mit Aufrecht-Bedingung | Milchkarton, Cerealien-Packung, Becher, Flasche | Kippwinkel während der ganzen Episode klein halten |
| Hakengriff | Tasche, Henkel | Last hängt an gebeugten Fingern, Daumen unbeteiligt, Servo-Stall relevant |
| Stütz- oder Randgriff | Schüssel, Teller, Tablett | Handfläche oben bzw. Daumen innen am Rand |

Besteck und winzige Objekte halte ich mit 1 Freiheitsgrad pro Finger für zu schwer für den PoC. Wenn du das anders einschätzt, sag es.

## 4. Empfohlene Architektur

```
Hauptrechner des Roboters
  ├─ Wahrnehmung: Objekt erkennen, Objektpose schätzen
  ├─ Regel: Objektklasse → Griffart (Tabelle; die RoboCup-Objekte sind vorher bekannt)
  └─ Armplanung (klassisch): Hand zur Pre-Grasp-Pose fahren
              │ Objektpose relativ zur Hand, Griffart, Ziel (z. B. Zielhöhe, „aufrecht“)
              ▼
STM32N6 (50–60 Hz): kleine RL-Policy → 8 Servo-Positionsziele
```

**Begründung:**
- NVIDIA setzt in DextrAH-G unter die Policy einen sicheren Regler (Geometric Fabrics) und reduziert den Aktionsraum. Die Policy lernt nur, was klassische Verfahren schlecht können.
- DemoGrasp (2025) zeigt: Wenn Annäherung („wo greifen“) und Fingerbewegung („wie greifen“) getrennt sind, wird RL sehr effizient. Das passt gut zu unserem kleinen Aktionsraum.
- Die Bildverarbeitung bleibt auf dem Hauptrechner. Der Nucleo bekommt nur Zahlen.

**Offene Frage an dich:** Steuert die bestehende Umgebung den Arm mit, oder startet die Hand bereits nahe am Objekt? Passe die Empfehlung an das an, was dort schon funktioniert.

## 5. Empfehlungen zum Training (NVIDIA-Best-Practice, an unseren Rahmen angepasst)

### 5.1 Vorlage
NVIDIA bietet mit **Dexsuite** (`Isaac-Dexsuite-Kuka-Allegro-Lift-v0`, Isaac Lab PR #3378) eine vereinfachte, manager-basierte Neuauflage der DextrAH-Arbeiten: vereinfachte Belohnungen, einheitliche MDP-Struktur. Lift und Reorient teilen sich den Beobachtungsraum.
- **Empfehlung:** Vergleiche unsere bestehende Zylinder-Umgebung mit Dexsuite-Lift (Belohnungsterme, Terminierung, Randomisierung, Curriculum). Übernimm, was besser ist. Einen kompletten Umbau halte ich nur dann für sinnvoll, wenn unsere Umgebung strukturell schwächer ist.
- Richtwert von NVIDIA: Lift konvergiert in etwa 4 h mit 8192 Umgebungen auf deutlich stärkerer Hardware. Rechne bei uns mit dem 2- bis 4-fachen. Den Reorient-Task (etwa 2 Tage auf 40.960 verteilten Umgebungen) halte ich für außer Reichweite und für den PoC nicht nötig.

### 5.2 Aufgabenformulierung
- **Zielaufgabe statt reines Heben:** Objekt auf eine Zielhöhe/-pose bringen und dort halten. Die Orientierung ist Teil des Ziels.
- **Aufrecht-Bedingung als laufende Belohnung**, zum Beispiel r = exp(−α·(1 − ẑ_Objekt·ẑ_Welt)), plus Abbruch über einem Grenzwinkel (etwa 20°).
- **Griffart als One-Hot-Eingang.** Belohne das passende Kontaktmuster (welche Finger, Handfläche). Das GRIT-Projekt (2026) zeigt: Eine grobe Griffart-Vorgabe verbessert die Übertragung auf neue Objekte und verhindert, dass RL immer dieselbe Handhaltung wählt.
- **Stufenbelohnung:** Annähern → Kontakt → Heben → Halten → Ziel. DextrAH-G kommt im Kern mit Fingerspitzenkontakt und Heben zum Ziel aus.
- **Kleine Strafe für dauerhaft hohe MCP-Last nahe 2,94 Nm.** Der reale Servo überhitzt im Dauer-Stall.

### 5.3 Lernstrategie
- **Spezialisten → Generalist:** Pro Griffart ein Spezialist, danach Destillation in eine Policy. Diese Idee stammt aus UniDexGrasp++ und aus Lin et al. 2025 („Divide-and-Conquer Distillation“). Sie passt zur GPU, weil jeder Spezialist klein bleibt.
- **Curriculum:** Erst ein Objekt in fester Lage, dann mehr Formen und Lagen (geometriebasiertes Curriculum nach UniDexGrasp++). Die Domain Randomization schrittweise steigern, wie in DextrAH.
- **Abklingende Hilfskraft:** Für „aufrecht“ und „von unten“ eine Hilfskraft auf das Objekt, deren Stärke über das Training abnimmt (Idee aus DexMachina). Das hilft, wenn das Objekt sonst sofort kippt und die Exploration scheitert.
- **Startposen:** Eine handgemachte Pre-Grasp-Pose pro Griffart. Lin et al. zeigen, dass gute Startposen die Exploration stark verbessern.

### 5.4 Lehrer und Schüler
- **Lehrer:** PPO mit asymmetrischem Actor-Critic. Der Critic bekommt privilegierte Daten (exakte Objektpose, Kontaktkräfte, Objekt-ID). Ein LSTM im Lehrer ist erlaubt. NVIDIA nutzt das in DextrAH, damit sich die Policy an die Physik anpasst und nachgreift.
- **Schüler für den Nucleo:** DAgger-Destillation (wie DextrAH-RGB) in ein kleines MLP. Der Schüler sieht nur, was der echte Roboter liefert: Servo-Position, Servo-Last, vorherige Aktion, Objektpose vom Hauptrechner, Griffart, Ziel.
- Wenn du einen einfacheren Weg siehst, zum Beispiel einen Actor, der von Anfang an nur reale Beobachtungen bekommt und keinen eigenen Schüler braucht, ist das für einen PoC völlig legitim.

### 5.5 Sim-to-Real (aus NVIDIA-Blogs)
- **Aktionen:** relative Gelenk-Positionsziele mit fester Frequenz (NVIDIA: 60 Hz, ein Low-Level-Regler setzt sie um). Bei uns ist das der interne Positionsregler des ST3215.
- **Beobachtungen:** dieselben in Sim und Realität, inklusive vorheriger Aktion, mit **Beobachtungsrauschen**.
- **Randomisierung:** Gelenkreibung und -dämpfung, Regler-Gains, Masse, Reibung, Schwerpunkt, Störkräfte auf das Objekt. Für uns zusätzlich: Servo-Latenz (zum Beispiel 10–40 ms) und Stall-Torque (Versorgungsspannung unbestätigt).
- **Aktuatormodell:** Isaac Lab bietet explizite Aktuatormodelle. Wenn wir reale Messdaten des ST3215 haben (Sprungantwort, Last), lohnt sich die Anpassung.
- **Servo-Last als Tastsinn:** Ohne echte Kontaktsensoren ist die Lastmeldung des ST3215 der beste Kontakt- und Rutschindikator. Simuliere sie als verrauschtes Gelenkmoment.

## 6. Empfehlungen für den STM32N6

- **Netzgröße:** Ein MLP mit etwa 80 Eingängen, [128, 128] oder [256, 128] und 8 Ausgängen hat 30.000–60.000 Parameter. Das sind int8 deutlich unter 100 kB. NVIDIA nutzt für Spot [512, 256, 128] auf einem Jetson. Für den N6 empfehle ich kleiner.
- **Aktivierung:** ReLU statt ELU (`rsl_rl`-Standard). ReLU ist für int8 und NPU unkritischer.
- **Kein LSTM im Schüler.** Die Vorgeschichte geht stattdessen als gestapelte Beobachtungen ein. Rekurrente Schichten sind auf MCU-NPUs oft nur eingeschränkt unterstützt. Bitte gegen die Operator-Liste von ST Edge AI prüfen.
- **Beobachtungsnormierung ins Modell einbauen**, damit der Nucleo dieselben Eingänge verarbeitet wie das Training.
- **Export:** `.pt` → ONNX (NVIDIA-Praxis) → int8 mit ST Edge AI.
- **Wichtigster Prüfpunkt:** Das **quantisierte** Modell zurück in Isaac Lab laden (zum Beispiel über onnxruntime im Regelkreis) und Erfolgsrate sowie Kippwinkel mit dem float-Modell vergleichen. NVIDIA beschreibt diesen Schritt nicht, weil ein Jetson in float rechnet. Für uns ist er der billigste Schutz vor einer stillen Verschlechterung.

## 7. Was ich für den PoC weglassen würde

- RL mit Kamerabildern (VRAM).
- Tausende Objekte (10–30 nach RoboCup-Kategorien reichen).
- Reorientierung in der Hand.
- Menschliche Demonstrationen und Imitationslernen (NVIDIAs zweiter Weg mit Isaac Lab Mimic und GR00T, siehe `Isaac-PickPlace-G1-InspireFTP-Abs-v0`). Für 3060 Ti und STM32N6 zu groß, außer du siehst einen schlanken Weg.
- Beidhändiges Greifen (später interessant für Tabletts und große Kisten).

## 8. Vorschlag für Phasen und Messgrößen

| Phase | Inhalt | Messgröße |
|---|---|---|
| 1 | Bestehende Zylinder-Umgebung mit Dexsuite-Lift abgleichen, Zielaufgabe mit Orientierung, Griffart-Eingang | Erfolgsrate „heben + 10 s halten“ am Zylinder bleibt erhalten |
| 2 | Pro Griffart ein Spezialist, Curriculum, Hilfskraft | Erfolgsrate pro Griffart, Kippwinkel bei Gießbarem |
| 3 | Destillation in ein kleines MLP (nur reale Beobachtungen) | Erfolgsrate des Schülers relativ zu den Spezialisten |
| 4 | ONNX → int8, Test des int8-Modells in Isaac Lab | Erfolgsrate int8 vs. float |
| 5 | Umsetzung auf dem STM32N6 | Rechenzeit pro Schritt, 50–60 Hz erreicht? |
| 6 | Reale Tests mit RoboCup-Objekten | Erfolgsrate real, Kippwinkel |

Halte die Ergebnisse jeder Phase kurz fest (README oder ADR, je nachdem, was im Repository üblich ist).

## 9. Fragen, die du mir beantworten oder stellen solltest

1. Wie sieht die aktuelle Zylinder-Umgebung aus (Beobachtungen, Belohnung, Aktionsraum, Arm ja/nein)? Was davon würdest du behalten?
2. Sind echte Kontaktsensoren geplant, oder ist die Servo-Last die einzige taktile Information?
3. Wie viele Umgebungen schafft die 3060 Ti mit unserer Hand tatsächlich, und wie lange dauert ein Lauf?
4. Unterstützt die installierte ST-Edge-AI-Version alle Operatoren des geplanten Schüler-Netzes?
5. Wo siehst du die größten Risiken für den PoC, und welche Empfehlung oben hältst du für falsch?

## Quellen der Empfehlungen

- NVIDIA Isaac Lab Dexsuite: github.com/isaac-sim/IsaacLab/pull/3378
- NVIDIA R²D² Blog (DextrAH-RGB, DexMimicGen, Lehrer mit LSTM, DAgger): developer.nvidia.com/blog/r2d2-adapting-dexterous-robots-with-nvidia-research-workflows-and-models/
- NVIDIA Sim-to-Real Montage-Blog (relative Gelenkziele 60 Hz, Randomisierung, Beobachtungsrauschen): developer.nvidia.com/blog/bridging-the-sim-to-real-gap-for-industrial-robotic-assembly-applications-using-nvidia-isaac-lab/
- NVIDIA Spot-Blog (MLP [512, 256, 128], ONNX-Export, 4096 Umgebungen auf RTX 4090): developer.nvidia.com/blog/closing-the-sim-to-real-gap-training-spot-quadruped-locomotion-with-nvidia-isaac-lab/
- DextrAH-G (Geometric Fabrics, Eigengrasps, privilegierter Lehrer): arxiv.org/abs/2407.02274
- DemoGrasp (Editieren einer Demonstration, Ein-Schritt-RL): arxiv.org/abs/2509.22149
- GRIT (Griffart-Taxonomie als Vorgabe): arxiv.org/abs/2604.04138
- UniDexGrasp++ (geometriebasiertes Curriculum, Spezialist → Generalist): pku-epic.github.io/UniDexGrasp++/
- Lin et al. 2025, Sim-to-Real RL on Humanoids (Startposen, Kontaktziele, Divide-and-Conquer): arxiv.org/abs/2502.20396
- DexMachina (abklingende Hilfskraft): project-dexmachina.github.io
- RoboCup@Home Regelwerk 2027 Rev-1: robocupathome.github.io/RuleBook/rulebook/master.pdf
- STM32N6 (ST Blog): blog.st.com/stm32n6/
