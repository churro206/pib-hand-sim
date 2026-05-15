# Projektkontext für Claude Code

## Wer ich bin und was das Projekt ist

Ich bin Leon, Informatikstudent. Ich arbeite an einem Simulationsprojekt für den
RoboCup 2027 (@Home Liga). Meine 3er-Gruppe ist für das Greifen mit der Hand des
Roboters "pib" (von isento, Open-Source, 3D-gedruckt) zuständig. Meine spezifische
Aufgabe: eine realitätsnahe Simulation der Handmotorik in NVIDIA Isaac Sim aufbauen.

## Kernidee der Simulation

Wir wollen ein neuronales Netz trainieren das folgende Kette lernt:

  Sollposition (Gelenkwinkel) → Motorstrom → Istposition

Das Netz soll zuerst auf synthetischen Daten aus Isaac Sim trainiert werden, später
auf echten Sensordaten (AS5600 Magnetencoder, 12-Bit, I2C). Damit wird die Simulation
realitätsgetreuer als die reine Physik-Engine von Isaac Sim.

## Technischer Stack

- **Isaac Sim** (NVIDIA, Python API) – Roboter-Simulation, USD-Format
- **PyTorch** – LSTM-Netz (zeitabhängige Dynamik: Trägheit, Reibung)
- **ONNX** – Export des Modells zurück in Isaac Sim
- **ROS2** – Roboter-Middleware (pib nutzt pib-backend auf ROS2-Basis)
- **Python 3.10+**, numpy, pandas
- **Ubuntu 24.04** (Haupt-Entwicklungsumgebung)

## Roboter: pib Handstruktur (linke Hand)

USD-Pfad in Isaac Sim: `/World/pib_upperbody_URDF/pib_upperbody_URDF`

11 DOF (Freiheitsgrade), alle unter `.../joints/hand_left/`:

| Index | DOF-Name                    | Gelenk                  |
|-------|-----------------------------|-------------------------|
| 0     | urdf_thumb_rotator_left     | Daumen CMC (Abduktion)  |
| 1     | urdf_finger_proximal_05     | Daumen MCP              |
| 2     | urdf_finger_distal_05       | Daumen IP               |
| 3     | urdf_finger_proximal_06     | Zeigefinger MCP         |
| 4     | urdf_finger_distal_06       | Zeigefinger PIP         |
| 5     | urdf_finger_proximal_07     | Mittelfinger MCP        |
| 6     | urdf_finger_distal_07       | Mittelfinger PIP        |
| 7     | urdf_finger_proximal_08     | Ringfinger MCP          |
| 8     | urdf_finger_distal_08       | Ringfinger PIP          |
| 9     | urdf_finger_proximal_09     | Kleiner Finger MCP      |
| 10    | urdf_finger_distal_09       | Kleiner Finger PIP      |

**Wichtig:** Gelenkgrenzen kommen aus dem Onshape-Import – bitte nicht überschreiben.
DOF-Namen müssen mit `robot.dof_names` in Isaac Sim abgeglichen werden (TODO).

## Projektstruktur (Zielzustand)

```
pib_hand_sim/
├── config/
│   └── pib_hand_config.py       # DOF-Namen, Greifposen, Konstanten
├── data/
│   └── .gitkeep                 # Trainings-Daten (npz), nicht ins Git
├── isaac_sim/
│   └── collect_data.py          # Läuft IN Isaac Sim: Daten sammeln
├── training/
│   ├── dataset.py               # PyTorch Dataset + DataLoader
│   ├── model.py                 # LSTM Forward-Modell
│   └── train.py                 # Trainingsloop
├── inference/
│   └── isaac_sim_node.py        # ONNX-Modell zurück in Isaac Sim
└── pib_hand_pipeline_v2.py      # Alles-in-einem (aktueller Stand)
```

## Aktueller Stand

- [x] pib USD-Modell in Isaac Sim importiert, Gelenke per GUI steuerbar
- [x] Pipeline-Script (`pib_hand_pipeline_v2.py`) mit synthetischem Datengenerator,
      LSTM-Architektur, Trainingsloop, Isaac Sim Stub – bereit zum Testen
- [x] Konfigurationsdatei (`pib_hand_config.py`) mit Greifposen
- [ ] Isaac Sim Datensammel-Script fehlt noch
- [ ] DOF-Namen mit Isaac Sim abgeglichen (Inventar-Script ausstehend)
- [ ] Echtes Training noch nicht gestartet
- [ ] AS5600 Sensoren bestellt, noch nicht angekommen

## Nächste konkrete Schritte

1. Inventar-Script in Isaac Sim Konsole ausführen → echte DOF-Namen + Grenzen ermitteln
2. `collect_data.py` schreiben: Isaac Sim Gelenke systematisch anfahren + Daten speichern
3. Training auf synthetischen Daten starten + Evaluierung
4. Später: DataCollector mit echten AS5600-Sensordaten ersetzen

## Wichtige Konventionen

- Winkel immer in **Grad** (nicht Radiant) – Umrechnung beim Isaac Sim API-Call
- Isaac Sim gibt/nimmt Radiant: `pos_deg = pos_rad * 180 / np.pi`
- Normierung für Netz: Positionen → [0, 1], Strom → z-Score
- MCP-PIP Kopplung: PIP-Gelenke folgen MCP mit Faktor ~1.2 (Sehnenmechanismus)

## Was ich von dir brauche

Wenn ich eine Aufgabe nenne, kenn den Projektkontext. Arbeite direkt mit den
vorhandenen Dateien. Halte dich an die Konventionen oben. Frag nach wenn DOF-Namen
oder Gelenkgrenzen unklar sind – die sind kritisch.
