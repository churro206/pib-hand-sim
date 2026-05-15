# pib Hand Simulation

Simulationsprojekt für den RoboCup 2027 (@Home Liga).  
Ziel: Realitätsnahe Simulation der rechten Hand des Roboters **pib** (isento, Open-Source, 3D-gedruckt) mit einem LSTM-Netz, das die Fingergelenkdynamik lernt.

---

## Überblick

```
Sollposition (Gelenkwinkel)
        ↓
   LSTM-Modell          ← trainiert auf Isaac Sim + echten AS5600-Daten
        ↓
   Istposition (Vorhersage)
```

Das Netz lernt: Trägheit, Reibung, Hysterese der Sehnenmechanik.  
Trainiert wird zuerst auf synthetischen Isaac Sim Daten, später fine-getuned auf echten Sensordaten (AS5600 Magnetencoder).

---

## Repository-Struktur

```
pib-hand-sim/
├── config/
│   └── pib_hand_config.py      # DOF-Namen, Indizes, Grenzen (rechte Hand)
├── data/                        # Trainingsdaten (.npz) — nicht im Git
├── isaac_sim/
│   ├── inventory.py            # Zeigt alle DOFs + Grenzen in Isaac Sim
│   ├── setup_stage.py          # Boden, Licht, Physics Scene einrichten
│   ├── fix_joints.py           # Alle Gelenke außer rechte Hand einfrieren
│   ├── unfix_joints.py         # Alle Gelenke freigeben (zum Testen)
│   └── collect_data.py         # Synthetische Daten in Isaac Sim sammeln
├── training/
│   ├── dataset.py              # PyTorch Dataset aus .npz-Dateien
│   ├── model.py                # LSTM-Architektur
│   └── train.py                # Trainingsloop
├── inference/
│   └── export_onnx.py          # PyTorch → ONNX (für STM32Cube.AI)
├── models/                      # Trainierte Modelle (.pt, .onnx) — nicht im Git
├── Dockerfile                   # Training-Umgebung
├── compose.yml                  # Docker Compose Services
└── requirements.txt             # Python-Abhängigkeiten
```

---

## Setup

### Voraussetzungen

- Ubuntu 22.04 / 24.04
- NVIDIA GPU + CUDA 12.x
- Docker + NVIDIA Container Toolkit (für Training)
- NVIDIA Isaac Sim (für Datengenerierung, separat installieren)

### Schnellstart (Training + Export)

```bash
git clone https://github.com/churro206/pib-hand-sim
cd pib-hand-sim

# Image einmalig bauen (~5 Min)
docker compose build

# Training starten
docker compose run --rm train

# ONNX exportieren (für STM32Cube.AI)
docker compose run --rm export

# Interaktive Shell
docker compose run --rm shell
```

### Ohne Docker (lokale venv)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt

python training/train.py
python inference/export_onnx.py
```

---

## Isaac Sim Workflow

> Isaac Sim muss separat installiert sein. Scripts werden im **Script Editor** ausgeführt  
> (Window → Script Editor → Datei öffnen → Run).

### Reihenfolge beim Start

1. Isaac Sim öffnen, USD laden: `isaac_sim/pib_upperbody_3_flattened.usd`
2. **Play drücken** (Simulation starten)
3. `setup_stage.py` → einmalig ausführen (Boden, Licht, Physics)
4. `fix_joints.py` → Roboter in T-Pose einfrieren
5. `collect_data.py` → Daten sammeln (~3 Min für 20 Episoden)

### Datenformat (synthetisch)

Gespeichert in `data/synthetic_TIMESTAMP.npz`:

| Variable | Shape | Beschreibung |
|---|---|---|
| `t` | (N,) | Zeitstempel [s] |
| `cmd` | (N, 11) | Sollwinkel, normiert [0=offen, 1=geschlossen] |
| `pos` | (N, 11) | Istwinkel, normiert [0=offen, 1=geschlossen] |
| `stiffness` | (N,) | Gelenk-Steifigkeit dieser Episode |
| `damping` | (N,) | Dämpfung dieser Episode |
| `dof_names` | (11,) | DOF-Namen |

---

## Rechte Hand — DOF-Übersicht

Alle Winkel: **0° = offen (T-Pose), -90° = vollständig gebeugt**

| Index | DOF-Name | USD-DOF-Idx | Min | Max |
|---|---|---|---|---|
| 0 | thumb_right_opposition | 19 | -90° | 0° |
| 1 | thumb_right_proximal | 29 | -90° | 0° |
| 2 | thumb_right_distal | 35 | -90° | 0° |
| 3 | index_right_proximal | 20 | -90° | 0° |
| 4 | index_right_distal | 30 | -90° | 0° |
| 5 | middle_right_proximal | 21 | -90° | 0° |
| 6 | middle_right_distal | 31 | -90° | 0° |
| 7 | ring_right_proximal | 22 | -90° | 0° |
| 8 | ring_right_distal | 32 | -90° | 0° |
| 9 | pinky_right_proximal | 23 | -90° | 0° |
| 10 | pinky_right_distal | 33 | -90° | 0° |

---

## LSTM-Modell

**Architektur:** 2-Layer LSTM, hidden_size=128  
**Input:** `[cmd_t (11), pos_{t-1} (11)]` → 22 Features  
**Output:** `pos_t (11)` — vorhergesagte Istposition  
**Normierung:** `norm = -pos_deg / 90.0` (0.0 = offen, 1.0 = geschlossen)

---

---

# Für den Nucleo-Kollegen

> Dieser Abschnitt erklärt was die Simulation-/ML-Seite vom STM32-seitigen Code braucht,  
> damit echte Sensordaten für das Training und die spätere Inferenz genutzt werden können.

---

## Ziel der Integration

Das LSTM-Modell soll mit echten AS5600-Daten fine-getuned werden.  
Dafür brauchen wir aus dem Nucleo:

1. **Kommandierte Winkel** — was wir dem Servo schicken
2. **Gemessene Winkel** — was der AS5600 tatsächlich misst
3. **Timestamps** — wann die Messung war

Später, bei der Inferenz auf dem Nucleo, läuft das ONNX-Modell direkt auf dem H723ZG.

---

## AS5600 — Konvertierung

Der AS5600 gibt 12-Bit Rohwerte zurück: **0–4095 → 0–360°**

Da die Fingergelenke nur ~90° bewegen, brauchen wir eine Kalibrierung:

```
Einmalig pro Gelenk:
  raw_open   = AS5600-Wert bei vollständig geöffnetem Finger (0°)
  raw_closed = AS5600-Wert bei vollständig geschlossenem Finger (-90°)

Umrechnung:
  angle_deg = (raw - raw_open) / (raw_closed - raw_open) * (-90.0)
```

Die Kalibrierungswerte (`raw_open`, `raw_closed`) für jedes der 11 Gelenke  
müssen einmalig gemessen und hardcoded oder in einem Flash-Config-Bereich gespeichert werden.

---

## Gewünschtes Kommunikationsprotokoll

Wir brauchen vom Nucleo einen **kontinuierlichen Datenstrom** mit ~60 Hz.  
Bevorzugtes Format (noch abzustimmen):

### Option A — USB CDC Serial (einfach)

```
Paket pro Tick (binär oder ASCII):
  [timestamp_ms: uint32] [cmd_0..10: float32 x11] [pos_0..10: float32 x11]
```

ASCII-Variante (einfacher zum Debuggen):
```
t=1234,cmd=0.0,-45.2,...,pos=0.0,-42.1,...\n
```

### Option B — ROS2 Serial Bridge

Nucleo publiziert über `micro-ROS` auf Topics:
- `/hand_right/cmd` — `sensor_msgs/JointState`
- `/hand_right/pos` — `sensor_msgs/JointState`

**Bitte abstimmen:** welche Option ist auf eurer Nucleo-Seite einfacher umzusetzen?

---

## Was wir auf unserer Seite schreiben

Sobald das Protokoll feststeht, schreiben wir `data/collect_real.py`:

```python
# Pseudocode
for each packet from Nucleo:
    cmd_deg  = packet.cmd          # Sollwinkel [°], alle 11 Gelenke
    pos_deg  = calibrate(packet.raw_as5600)  # Istwinkel [°]
    timestamp = packet.t / 1000.0  # [s]
    # → speichern in .npz (gleiches Format wie synthetische Daten)
```

Das Training läuft danach **unverändert** auf echten + synthetischen Daten zusammen.

---

## ONNX-Modell auf dem H723ZG

Das exportierte Modell (`models/hand_lstm_nucleo_*.onnx`) kann mit **STM32Cube.AI (X-CUBE-AI)**  
in optimierten C-Code für den H723ZG konvertiert werden.

**Kenndaten:**
- Parameter: ~219.000
- float32: ~855 KB → nach int8-Quantisierung: **~214 KB** (passt in 564 KB RAM)
- Inferenz-Input: 22 float-Werte (11 cmd + 11 pos_prev)
- Inferenz-Output: 11 float-Werte (vorhergesagte pos)
- Benötigte Frequenz: 60 Hz → 16.67 ms pro Inferenz (H723ZG @ 550 MHz: unkritisch)

### Schritte für STM32Cube.AI

1. STM32CubeIDE öffnen
2. Help → Manage Embedded Software Packages → **X-CUBE-AI** installieren
3. Neues Projekt für NUCLEO-H723ZG anlegen
4. X-CUBE-AI → Add Network → ONNX-Datei auswählen
5. Analyze → prüfen ob RAM/Flash reicht
6. Generate Code → fertiger C-Code

### LSTM-State auf dem Nucleo

Das LSTM hat einen internen State (h, c) der zwischen den Inferenz-Aufrufen erhalten bleiben muss.  
STM32Cube.AI generiert dafür statische Buffer — diese **nicht** bei jedem Aufruf zurücksetzen,  
sondern nur beim Start eines neuen Greifvorgangs.

---

## Offene Abstimmungspunkte

- [ ] Kommunikationsprotokoll: Serial CDC oder micro-ROS?
- [ ] Paketformat und Baudrate
- [ ] Welche der 11 Gelenke sind mit AS5600 bestückt?
- [ ] Kalibrierungswerte gemeinsam messen
- [ ] ROS2-Topic-Namen für spätere Integration
