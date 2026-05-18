"""
Extrahiert LSTM-Gewichte aus dem PyTorch-Checkpoint als Numpy-Arrays.
Ausgabe: models/hand_lstm_*_weights.npz

Wird von isaac_sim/run_inference.py benoetigt (kein torch in Isaac Sim noetig).
Einmalig ausfuehren, danach reicht die .npz-Datei.

Ausfuehren (vom Repo-Root):
    .venv/bin/python inference/export_weights.py
"""
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import torch

MODEL_DIR = Path(__file__).parent.parent / "models"


def find_latest_checkpoint() -> Path:
    files = sorted(MODEL_DIR.glob("hand_lstm_*.pt"))
    if not files:
        raise FileNotFoundError(f"Kein Checkpoint in {MODEL_DIR}")
    return files[-1]


def export():
    ckpt_path = find_latest_checkpoint()
    print(f"Lade: {ckpt_path.name}")

    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    weights    = {k: v.numpy() for k, v in checkpoint["model"].items()}

    out_path = MODEL_DIR / (ckpt_path.stem + "_weights.npz")
    np.savez(out_path, **weights)

    print(f"Gespeichert: {out_path.name}")
    print(f"Keys ({len(weights)}): {', '.join(weights.keys())}")


if __name__ == "__main__":
    export()
