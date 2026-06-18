# Projektkontext für Claude Code

## Wer ich bin und was das Projekt ist

Ich bin Leon, Informatikstudent. Ich arbeite an einem Simulationsprojekt für den
RoboCup 2027 (@Home Liga). Meine 3er-Gruppe ist für das Greifen mit der Hand des
Roboters "pib" (von isento, Open-Source, 3D-gedruckt) zuständig. Meine spezifische
Aufgabe: eine realitätsnahe Simulation der Handmotorik in NVIDIA Isaac Sim aufbauen.

## Wichtige Update — pib v4 Hand

Wir verwenden jetzt die neue pib v4 Hand. Diese hat **drei Gelenke pro Finger**
(proximal, distal, tip) statt zwei wie in v3. Die alte Konfiguration mit 11 DOF
ist überholt — neu sind es **16 DOF** pro Hand.

## Aktuelles Setup — Konventionen

### Winkelkonvention
- **Positive Winkel = Sehne verkürzt sich = Finger beugt sich Richtung Handfläche**
- 0° = vollständig offen (T-Pose)
- ~90° = vollständig gebeugt
- Diese Konvention gilt in Onshape und im Code

### Vorzeichen zwischen Onshape und Isaac Sim
- Onshape und Isaac sind invertiert. Pib steht im Welt-Koordinatensystem
  korrekt orientiert in Isaac, aber positive Winkel im Onshape-Slider entsprechen
  negativen Winkeln in Isaac (oder umgekehrt, je nach Joint Property).
- **Wir akzeptieren das und kompensieren per Konstante:** `JOINT_SIGN = -1` in
  `config/pib_hand_config.py`. Diese Konstante wird überall multipliziert wo
  Winkel zwischen unserem Code und Isaac ausgetauscht werden.
- Onshape wird **nicht** angefasst, die dortige Logik bleibt intuitiv

## Technischer Stack

- **Isaac Sim 5.1** (NVIDIA, Python API) — Roboter-Simulation, USD-Format
- **PyTorch** — LSTM-Netz (in Phase 3)
- **ONNX** — Export für STM32Cube.AI (Nucleo H723ZG, NPU des STM32N6)
- **ROS2** — Roboter-Middleware (spätere Integration in pib-backend)
- **Python 3.10+**, numpy, matplotlib, pyserial
- **Ubuntu 24.04** (Haupt-Entwicklungsumgebung)
- **Docker** — Training auf Schul-Workstation (GPU), Basis: `nvcr.io/nvidia/pytorch:24.12-py3`

## Roboter: pib v4 Handstruktur (linke Hand)

USD-Pfad in Isaac Sim: `/World/pib_upperbody_URDF/pib_upperbody_URDF`

**16 DOF, müssen per `isaac_sim/inventory.py` verifiziert werden:**

| Index | DOF-Name                          | Gelenk                  |
|-------|-----------------------------------|-------------------------|
| 0     | dof_thumb_left_rotator (Opposition)| Daumen CMC             |
| 1     | dof_thumb_left_proximal           | Daumen Grundgelenk     |
| 2     | dof_thumb_left_distal             | Daumen Mittelgelenk    |
| 3     | dof_thumb_left_tip                | Daumen Endglied        |
| 4     | dof_index_left_proximal           | Zeigefinger MCP        |
| 5     | dof_index_left_distal             | Zeigefinger PIP        |
| 6     | dof_index_left_tip                | Zeigefinger DIP        |
| 7-9   | dof_middle_left_proximal/distal/tip| Mittelfinger         |
| 10-12 | dof_ring_left_proximal/distal/tip | Ringfinger             |
| 13-15 | dof_pinky_left_proximal/distal/tip| Kleiner Finger         |

**Wichtig:** Die exakten DOF-Namen und Indizes kommen aus dem Isaac Sim Stage —
Inventory-Script auszuführen ist erster Schritt vor jedem Code-Update.

### Sehnenkopplung pro Finger
- Ein Servo treibt drei Gelenke über eine Sehne
- Bewegungsanteil grob: proximal 1.0, distal 0.8, tip 0.6 (anatomisch motivierte
  Startwerte, später kalibrieren mit AS5600)

## Projektstruktur

```
pib-hand-sim/
├── config/
│   └── pib_hand_config.py          # DOF-Namen, Indizes, Grenzen, JOINT_SIGN, Greifposen
├── isaac_sim/
│   ├── inventory.py                # Debug: alle DOFs + Grenzen aus Stage auslesen
│   ├── setup_stage.py              # Boden, Licht, PhysicsScene einrichten
│   ├── fix_joints.py               # Nicht-Hand-Gelenke einfrieren
│   ├── manual_control.py           # NEU: Phase 1 — Einzelgelenke per Winkel steuern
│   ├── servo_control.py            # NEU: Phase 2 — lineare Servo→Gelenk Approximation
│   └── run_inference.py            # Phase 3: LSTM in Isaac (kommt später)
├── kinematics/
│   └── servo_to_joint.py           # NEU: lineare Approximation Funktion
├── data/
│   ├── collect_real.py             # Echtdaten vom Nucleo aufzeichnen (Phase 3)
│   └── *.npz                       # Trainingsdaten (nicht im Git)
├── training/                       # Phase 3
│   ├── dataset.py
│   ├── model.py
│   └── train.py
├── inference/                      # Phase 3
│   ├── export_onnx.py
│   └── plot_inference.py
├── models/                         # Trainierte Modelle (nicht im Git)
├── Dockerfile
├── compose.yml
└── requirements.txt
```

## Phasenplan

### Phase 1 — Direktsteuerung als Baseline
**Ziel:** Per Python-Script einzelne Gelenke ansprechen können.

**Status:**
- [ ] inventory.py für v4 anpassen (16 DOF erkennen)
- [ ] pib_hand_config.py auf 16 DOF erweitern + JOINT_SIGN einbauen
- [ ] manual_control.py schreiben: Funktion `set_joint(name, angle_deg)` und
      vordefinierte Greifposen abspielen

### Phase 2 — Lineare Approximation als Platzhalter
**Ziel:** Funktion `winkel(servo_pos)` linear approximiert, damit ein virtueller
Servo-Befehl alle drei Fingergelenke koordiniert bewegt — bis echte AS5600-Daten
vorhanden sind.

**Status:**
- [ ] kinematics/servo_to_joint.py: Lineare Funktion pro Finger
      `(proximal, distal, tip) = (1.0·s, 0.8·s, 0.6·s)` mit s ∈ [0, 90]°
- [ ] servo_control.py: Skript das 5 Servo-Werte annimmt und alle 15 Gelenke setzt
      (plus Opposition separat)
- [ ] Greifposen aus pib_hand_config.py als Servo-Werte definieren statt
      Einzel-DOF-Werte

### Phase 3 — Echte Messdaten und LSTM
**Ziel:** AS5600-Sensordaten sammeln, LSTM trainieren, Approximation ersetzen.

**Status:** Erst starten wenn Sensoren ankommen und am Nucleo angebunden sind.

## Wichtige Konventionen (alle Phasen)

- Winkel intern immer in **Grad**, Isaac API verlangt Radiant → `np.degrees()` / `np.radians()`
- Vorzeichen-Kompensation: vor `set_joint_positions()` mit `JOINT_SIGN` multiplizieren
- Normierung Servo-Werte (später): 0 = offen, 1 = geschlossen, linear über die
  ganze Bewegung
- Greifposen werden über **Servo-Werte** parametriert, nicht über Einzelgelenke,
  damit sie phasenübergreifend gültig bleiben

## Was ich von dir brauche

Kenn den Projektkontext. Arbeite direkt mit den vorhandenen Dateien.
Frag nach bevor du Gelenknamen oder Vorzeichen erfindest — die werden per
inventory.py verifiziert.

Wenn unklar ist welche Phase wir gerade bearbeiten, frag nach — Code für Phase 3
zu schreiben während Phase 1 noch nicht steht, ist nicht produktiv.

Aktuell arbeiten wir an **Phase 1** — manuelle Direktsteuerung als Baseline.