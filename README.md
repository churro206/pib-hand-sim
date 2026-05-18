# pib Hand Simulation

Simulationsprojekt für den RoboCup 2027 (@Home Liga).  
Ziel: Realitätsnahe Simulation der rechten Hand des Roboters **pib** mit einem LSTM-Netz,
das die Fingergelenkdynamik lernt — zuerst auf synthetischen Isaac Sim Daten, später
fine-getuned auf echten AS5600-Magnetencoder-Daten.

---

## Gesamtüberblick

```
Phase 1 — Simulation (fertig)           Phase 2 — Realität (ausstehend)
──────────────────────────────          ────────────────────────────────
Isaac Sim (PhysX)                       Nucleo → AS5600-Sensor
  collect_data.py                         collect_real.py
  20 Episoden × 5 Trajektorien            live Aufzeichnung
  stiffness/damping zufällig              kalibrierte Winkel
        ↓                                       ↓
  synthetic_*.npz                         real_*.npz
        └──────── training/train.py ───────────┘
                        ↓
                hand_lstm_*.pt
               ┌──────┴──────┐
               ↓             ↓
      export_onnx.py   export_weights.py
               ↓             ↓
       *.onnx (STM32)   *_weights.npz
                             ↓
                    run_inference.py
                    ┌────────┴────────┐
                    ↓                 ↓
               compare-Modus    drive-Modus
               LSTM vs. PhysX   LSTM treibt Hand
                    ↓
             plot_inference.py / evaluate_real.py
```

Das Netz lernt: `(Sollwinkel_t, Istwinkel_{t-1}) → Istwinkel_t`  
Es modelliert Trägheit, Reibung und Hysterese der Sehnenmechanik.

---

## Repository-Struktur

```
pib-hand-sim/
├── config/
│   └── pib_hand_config.py          # DOF-Namen, Indizes, Grenzen (rechte Hand)
├── data/
│   ├── collect_real.py             # Echtdaten vom Nucleo aufzeichnen
│   ├── synthetic_*.npz             # Synthetische Trainingsdaten (nicht im Git)
│   └── real_*.npz                  # Echte AS5600-Daten (nicht im Git)
├── isaac_sim/
│   ├── inventory.py                # Debug: alle DOFs + Grenzen ausgeben
│   ├── setup_stage.py              # Boden, Licht, PhysicsScene einrichten
│   ├── fix_joints.py               # Nicht-Hand-Gelenke einfrieren
│   ├── unfix_joints.py             # Alle Gelenke freigeben (Diagnose)
│   ├── collect_data.py             # Synthetische Daten sammeln (~3 Min)
│   └── run_inference.py            # LSTM in Isaac Sim (compare / drive Modus)
├── training/
│   ├── dataset.py                  # PyTorch Dataset aus .npz-Dateien
│   ├── model.py                    # LSTM-Architektur
│   └── train.py                    # Trainingsloop
├── inference/
│   ├── export_onnx.py              # PyTorch → ONNX (für STM32Cube.AI)
│   ├── export_weights.py           # PyTorch → .npz (für Isaac Sim)
│   ├── plot_inference.py           # Isaac Sim Inferenzlogs plotten
│   └── evaluate_real.py            # Offline: LSTM vs. Messdaten vergleichen
├── models/                         # Trainierte Modelle (nicht im Git)
│   ├── hand_lstm_*.pt              # PyTorch Checkpoint
│   ├── hand_lstm_nucleo_*.onnx     # ONNX für STM32
│   └── hand_lstm_*_weights.npz    # Numpy-Gewichte für Isaac Sim
├── Dockerfile
├── compose.yml
└── requirements.txt
```

---

## Setup

### Voraussetzungen

- Ubuntu 22.04 / 24.04
- NVIDIA GPU + CUDA 12.x
- Docker + NVIDIA Container Toolkit (für Training auf Workstation)
- NVIDIA Isaac Sim 4.x (separat installieren, nur für Datengenerierung & Simulation)

### Lokale Umgebung

```bash
git clone https://github.com/churro206/pib-hand-sim
cd pib-hand-sim

python3 -m venv .venv
source .venv/bin/activate
pip install torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
```

### Docker (Schul-Workstation ohne lokale Einrichtung)

```bash
docker compose build                      # einmalig ~5 Min
docker compose run --rm train             # Training
docker compose run --rm export            # ONNX exportieren
docker compose run --rm export-weights    # Numpy-Gewichte exportieren
```

---

## Phase 1: Synthetische Daten & Training

### Isaac Sim Workflow

> Scripts laufen im **Script Editor** (Window → Script Editor → Datei öffnen → Run).

**Reihenfolge beim Start — Pflicht:**

| Schritt | Script | Warum |
|---|---|---|
| 1 | USD laden, **Play drücken** | Simulation muss laufen |
| 2 | `setup_stage.py` | Erzeugt PhysicsScene — ohne diese schlägt jede Physics-API fehl |
| 3 | `fix_joints.py` | Friert Rumpf/Arme ein, Hand bleibt beweglich |
| 4 | `collect_data.py` | Sammelt Trainingsdaten |

### Datengenerierung (`collect_data.py`)

Pro Episode werden **stiffness** (50–200) und **damping** (5–30) zufällig gezogen,
damit das LSTM mit unterschiedlicher Gelenksteifigkeit umgehen kann.
Jede Episode fährt 5 Trajektorien ab:

| Trajektorie | Beschreibung |
|---|---|
| slow_close | 3 s: 0° → −90° |
| slow_open | 3 s: −90° → 0° |
| fast_close | 0.5 s: 0° → −90° |
| fast_open | 0.5 s: −90° → 0° |
| sweep | 4 s: 0° ↔ −90° (Hysterese sichtbar) |

Ergebnis: `data/synthetic_<timestamp>.npz` mit ~20.000 Samples.

### Datenformat

Alle `.npz`-Dateien (synthetisch **und** real) teilen dasselbe Grundformat:

| Variable | Shape | Beschreibung |
|---|---|---|
| `t` | (N,) | Zeitstempel [s] |
| `cmd` | (N, 11) | Sollwinkel [Grad] |
| `pos` | (N, 11) | Istwinkel [Grad] — PhysX oder AS5600 |
| `dof_names` | (11,) | DOF-Namen |

Synthetische Dateien enthalten zusätzlich `stiffness` (N,) und `damping` (N,).

### Training

```bash
.venv/bin/python training/train.py
# Lädt automatisch alle data/synthetic_*.npz und data/real_*.npz
# Bestes Validierungsergebnis bisher: ~1.86°
```

### Export

```bash
# ONNX für STM32Cube.AI (Nucleo-Deployment):
.venv/bin/python inference/export_onnx.py

# Numpy-Gewichte für isaac_sim/run_inference.py:
.venv/bin/python inference/export_weights.py
```

---

## LSTM in Isaac Sim (`run_inference.py`)

Einstellungen am Anfang der Datei anpassen:

```python
MODE              = "compare"      # "compare" | "drive"
RUN_TEST_TRAJ     = True           # Finger automatisch bewegen
TRAJ_SPEEDS_DEG_S = [30.0, 180.0] # °/s pro Zyklus: [langsam, schnell]
```

| Modus | Was passiert | Wann sinnvoll |
|---|---|---|
| `compare` | PhysX läuft normal, LSTM sagt parallel vorher. Fehler wird geloggt. | Sanity-Check nach Training. Echter Vergleich erst nach Fine-tuning. |
| `drive` | Hand-PhysX deaktiviert, LSTM setzt Gelenkpositionen direkt. | Nach Fine-tuning auf AS5600-Daten. |

**Voraussetzungen:** Play gedrückt → setup_stage.py → fix_joints.py → export_weights.py ausgeführt.

Nach dem Lauf: `data/inference_<modus>_<timestamp>.npz`

### Inferenzlog plotten

```bash
.venv/bin/python inference/plot_inference.py
# oder:
.venv/bin/python inference/plot_inference.py data/inference_compare_XYZ.npz
```

Zeigt alle 11 DOFs: cmd (grau gestrichelt), PhysX (blau), LSTM (orange). Speichert `.png`.

---

## Phase 2: Echte Sensordaten

### Warum Phase 2?

Phase 1 lehrt das LSTM den **linearen PD-Regler** von Isaac Sim — keine echten
Nichtlinearitäten. Erst mit AS5600-Daten lernt das Netz:

- **Hysterese:** Finger-Istposition hängt von der Bewegungsrichtung ab
- **Kabelreibung:** Öffnen und Schließen haben unterschiedliche Dynamik
- **Compliance:** 3D-Druck gibt bei Last nach

### Daten aufzeichnen

```bash
# ASCII-Protokoll (Option A):
.venv/bin/python data/collect_real.py --port /dev/ttyACM0 --duration 60

# Falls Nucleo AS5600-Rohwerte (0–4095) statt Winkel schickt:
.venv/bin/python data/collect_real.py --port /dev/ttyACM0 --raw
```

**Vor dem ersten Einsatz** in `data/collect_real.py` eintragen:
- `AS5600_CALIB` — `(raw_open, raw_closed)` pro Gelenk, gemeinsam messen
- Protokollformat bestätigen (ASCII oder Binär)

### Fine-tuning

```bash
.venv/bin/python training/train.py
# Lädt real_*.npz + synthetic_*.npz zusammen — kein Code ändern
```

### Offline-Evaluation (LSTM vs. Messung)

```bash
# Neueste real_*.npz automatisch:
.venv/bin/python inference/evaluate_real.py

# Oder explizit — funktioniert auch auf synthetischen Daten zum Testen:
.venv/bin/python inference/evaluate_real.py data/synthetic_20260515_153750.npz
```

Plottet: cmd (grau), Messung (grün), LSTM (orange). Speichert `.eval.png` und `.eval.npz`.

---

## Rechte Hand — DOF-Übersicht

Alle Winkel: **0° = offen (T-Pose), −90° = vollständig gebeugt**

| Index | DOF-Name | USD-DOF-Idx | Min | Max |
|---|---|---|---|---|
| 0 | thumb_right_opposition | 19 | −90° | 0° |
| 1 | thumb_right_proximal | 29 | −90° | 0° |
| 2 | thumb_right_distal | 35 | −90° | 0° |
| 3 | index_right_proximal | 20 | −90° | 0° |
| 4 | index_right_distal | 30 | −90° | 0° |
| 5 | middle_right_proximal | 21 | −90° | 0° |
| 6 | middle_right_distal | 31 | −90° | 0° |
| 7 | ring_right_proximal | 22 | −90° | 0° |
| 8 | ring_right_distal | 32 | −90° | 0° |
| 9 | pinky_right_proximal | 23 | −90° | 0° |
| 10 | pinky_right_distal | 33 | −90° | 0° |

---

## LSTM-Modell

**Architektur:** 2-Layer LSTM, hidden_size=128  
**Input:** `[cmd_t (11), pos_{t-1} (11)]` → 22 Features  
**Output:** `pos_t (11)` — vorhergesagte Istposition  
**Normierung:** `norm = −pos_deg / 90.0` (0.0 = offen, 1.0 = geschlossen)

---

## Für den Nucleo-Kollegen

### Ziel

Das LSTM-Modell soll mit echten AS5600-Daten fine-getuned werden.  
Wir brauchen aus dem Nucleo pro Tick (~60 Hz):

1. **Kommandierte Winkel** [Grad] — was wir dem Servo senden
2. **AS5600-Position** — Rohwert (0–4095) oder kalibrierter Winkel [Grad]
3. **Timestamp** [ms]

### AS5600-Kalibrierung

```
Einmalig pro Gelenk messen:
  raw_open   = AS5600-Wert bei 0° (offen)
  raw_closed = AS5600-Wert bei −90° (geschlossen)

Umrechnung:
  angle_deg = (raw − raw_open) / (raw_closed − raw_open) × (−90.0)
```

### Protokoll-Optionen

**Option A — ASCII (einfach, gut zum Debuggen):**
```
t=1234,cmd=0.0;-45.2;...;pos=0.0;-42.1;...\n
```

**Option B — Binär (kompakt, 92 Bytes/Paket):**
```
[timestamp_ms: uint32][cmd_0..10: float32×11][pos_0..10: float32×11]
```

**→ Bitte abstimmen welche Option auf eurer Seite einfacher ist.**

### ONNX auf dem H723ZG (STM32Cube.AI)

| Kenngröße | Wert |
|---|---|
| Parameter | ~219.000 |
| Größe float32 | ~855 KB |
| Größe int8 (nach Quantisierung) | ~214 KB → passt in 564 KB RAM |
| Input | 22 float (11 cmd + 11 pos_prev) |
| Output | 11 float (pos_pred) |
| Zielfrequenz | 60 Hz → 16.67 ms/Inferenz |

**Schritte STM32Cube.AI:**
1. STM32CubeIDE → Help → Manage Embedded Software Packages → **X-CUBE-AI** installieren
2. Neues Projekt für NUCLEO-H723ZG anlegen
3. X-CUBE-AI → Add Network → `.onnx`-Datei wählen
4. Analyze → RAM/Flash prüfen
5. Generate Code

**Wichtig:** LSTM-State (h, c) zwischen Inferenzaufrufen **nicht** zurücksetzen —
nur beim Start eines neuen Greifvorgangs.

---

## Offene Punkte

- [ ] Kommunikationsprotokoll abstimmen: ASCII oder Binär?
- [ ] Baudrate und Paketformat bestätigen
- [ ] AS5600-Kalibrierungswerte gemeinsam messen → in `data/collect_real.py` eintragen
- [ ] Klären welche der 11 Gelenke mit AS5600 bestückt sind
- [ ] Fine-tuning starten sobald erste Echtdaten da sind
- [ ] ROS2-Topic-Namen für spätere Integration klären
