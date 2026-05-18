"""
Echte Sensordaten vom Nucleo (NUCLEO-H723ZG) aufzeichnen.
Speichert: data/real_<timestamp>.npz  — gleiches Format wie synthetic_*.npz.

Voraussetzungen:
  - Nucleo per USB-CDC verbunden
  - Protokoll: ASCII-Zeilen (Option A aus README):
      t=1234,cmd=0.0,-45.2,...,pos=0.0,-42.1,...\n

AS5600-Kalibrierung (einmalig pro Gelenk messen, Werte hier eintragen):
  raw_open   = AS5600-Rohwert bei vollstaendig geoeffnetem Finger (0°)
  raw_closed = AS5600-Rohwert bei vollstaendig geschlossenem Finger (-90°)
  angle_deg  = (raw - raw_open) / (raw_closed - raw_open) * (-90.0)

Ausfuehren (vom Repo-Root):
    .venv/bin/python data/collect_real.py
    .venv/bin/python data/collect_real.py --port /dev/ttyACM1 --duration 60
"""
import argparse
import time
import numpy as np
from datetime import datetime
from pathlib import Path

# ============================================================
#  KONFIGURATION
# ============================================================

DEFAULT_PORT     = "/dev/ttyACM0"
DEFAULT_BAUD     = 115200
DEFAULT_DURATION = 30          # Sekunden

DOF_NAMES = [
    "thumb_right_opposition", "thumb_right_proximal",  "thumb_right_distal",
    "index_right_proximal",   "index_right_distal",
    "middle_right_proximal",  "middle_right_distal",
    "ring_right_proximal",    "ring_right_distal",
    "pinky_right_proximal",   "pinky_right_distal",
]
N_DOFS = len(DOF_NAMES)

# AS5600-Kalibrierung: (raw_open, raw_closed) pro Gelenk.
# TODO: Werte gemeinsam mit Nucleo-Kollegen messen und eintragen.
# Format: [(raw_open, raw_closed), ...]  — Reihenfolge = DOF_NAMES
AS5600_CALIB = [
    (0, 4095),  # thumb_right_opposition  ← Platzhalter, bitte ersetzen
    (0, 4095),  # thumb_right_proximal
    (0, 4095),  # thumb_right_distal
    (0, 4095),  # index_right_proximal
    (0, 4095),  # index_right_distal
    (0, 4095),  # middle_right_proximal
    (0, 4095),  # middle_right_distal
    (0, 4095),  # ring_right_proximal
    (0, 4095),  # ring_right_distal
    (0, 4095),  # pinky_right_proximal
    (0, 4095),  # pinky_right_distal
]

SAVE_DIR = Path(__file__).parent

# ============================================================
#  AS5600-KALIBRIERUNG
# ============================================================

def raw_to_deg(raw: np.ndarray) -> np.ndarray:
    """Konvertiert AS5600-Rohwerte (0-4095) in kalibrierte Winkel [Grad]."""
    result = np.zeros(N_DOFS)
    for i, (r_open, r_closed) in enumerate(AS5600_CALIB):
        if r_closed == r_open:
            result[i] = 0.0
        else:
            result[i] = (raw[i] - r_open) / (r_closed - r_open) * (-90.0)
    return result


# ============================================================
#  PROTOKOLL-PARSER
# ============================================================
# TODO: Protokoll mit Nucleo-Kollegen abstimmen.
# Aktuell implementiert: Option A (ASCII) aus README.
#
# Erwartetes Format pro Zeile:
#   t=1234,cmd=0.0,-45.2,...,pos=0.0,-42.1,...\n
#   (pos = AS5600-Rohwerte 0-4095 ODER bereits kalibrierte Winkel — TBD)
#
# Option B (binaer, 4+44+44 = 92 Bytes pro Paket) hier noch nicht implementiert.

def parse_ascii_line(line: str):
    """
    Parst eine ASCII-Zeile vom Nucleo.
    Gibt (timestamp_s, cmd_deg, pos_raw_or_deg) zurueck oder None bei Fehler.
    """
    try:
        parts = dict(p.split("=") for p in line.strip().split(",") if "=" in p)
        t_ms  = int(parts["t"])
        cmd   = np.array([float(v) for v in parts["cmd"].split(";")])
        pos   = np.array([float(v) for v in parts["pos"].split(";")])
        if len(cmd) != N_DOFS or len(pos) != N_DOFS:
            return None
        return t_ms / 1000.0, cmd, pos
    except Exception:
        return None


# ============================================================
#  AUFZEICHNUNG
# ============================================================

def record(port: str, baud: int, duration: float, pos_is_raw: bool = True):
    """
    Liest vom Nucleo und speichert als .npz.
    pos_is_raw: True  = Nucleo schickt AS5600-Rohwerte (0-4095) → wird kalibriert
                False = Nucleo schickt bereits kalibrierte Winkel [Grad]
    """
    try:
        import serial  # pyserial
    except ImportError:
        raise ImportError("pyserial nicht installiert. Ausfuehren: pip install pyserial")

    print(f"Verbinde mit {port} @ {baud} Baud ...")
    ser = serial.Serial(port, baud, timeout=1.0)
    time.sleep(2.0)  # Nucleo braucht kurz zum Aufwachen nach USB-Verbindung
    ser.reset_input_buffer()
    print(f"Verbunden. Aufzeichnung fuer {duration} s ...")

    buf_t, buf_cmd, buf_pos = [], [], []
    t_start = time.time()
    n_errors = 0

    try:
        while time.time() - t_start < duration:
            raw_line = ser.readline().decode("ascii", errors="ignore")
            if not raw_line:
                continue
            parsed = parse_ascii_line(raw_line)
            if parsed is None:
                n_errors += 1
                continue
            t_s, cmd_deg, pos_data = parsed
            pos_deg = raw_to_deg(pos_data) if pos_is_raw else pos_data

            buf_t.append(t_s)
            buf_cmd.append(cmd_deg)
            buf_pos.append(pos_deg)

            if len(buf_t) % 600 == 0:
                print(f"  {len(buf_t)} Samples | Fehlerhafte Zeilen: {n_errors}")
    finally:
        ser.close()

    if not buf_t:
        print("[FEHLER] Keine Daten empfangen. Protokoll pruefen.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = SAVE_DIR / f"real_{timestamp}.npz"
    np.savez(
        out_path,
        t         = np.array(buf_t),
        cmd       = np.array(buf_cmd),
        pos       = np.array(buf_pos),
        dof_names = np.array(DOF_NAMES),
    )
    hz_approx = len(buf_t) / duration
    print(f"\nFertig: {len(buf_t)} Samples (~{hz_approx:.0f} Hz) -> {out_path}")
    print(f"Fehlerhafte Zeilen: {n_errors}")


# ============================================================

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port",     default=DEFAULT_PORT)
    ap.add_argument("--baud",     default=DEFAULT_BAUD,     type=int)
    ap.add_argument("--duration", default=DEFAULT_DURATION, type=float)
    ap.add_argument("--raw",      action="store_true",
                    help="Nucleo schickt AS5600-Rohwerte (0-4095), nicht Grad")
    args = ap.parse_args()

    record(args.port, args.baud, args.duration, pos_is_raw=args.raw)
