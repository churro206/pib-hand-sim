"""
Exportiert das trainierte LSTM-Modell nach ONNX fuer den NUCLEO-H723ZG.
Danach mit STM32Cube.AI (X-CUBE-AI) in C-Code konvertieren.

Ausfuehren (vom Repo-Root):
    .venv/bin/python inference/export_onnx.py
"""
import sys
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from training.model import HandLSTM

MODEL_DIR  = Path(__file__).parent.parent / "models"
EXPORT_DIR = Path(__file__).parent.parent / "models"
SEQ_LEN    = 1   # Fuer Nucleo: ein Schritt pro Inferenz (online/autoregressiv)


def find_latest_model() -> Path:
    checkpoints = sorted(MODEL_DIR.glob("hand_lstm_*.pt"))
    if not checkpoints:
        raise FileNotFoundError(f"Kein Modell in {MODEL_DIR}")
    return checkpoints[-1]


def export():
    model_path = find_latest_model()
    print(f"Lade Modell: {model_path.name}")

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
    model = HandLSTM()
    model.load_state_dict(checkpoint["model"])
    model.eval()

    # Dummy-Input: (batch=1, seq=1, features=22)
    dummy_input = torch.zeros(1, SEQ_LEN, 22)

    # LSTM-Hidden-State als separate Inputs (wichtig fuer Nucleo-Inferenz)
    dummy_h = torch.zeros(2, 1, 128)  # (num_layers, batch, hidden)
    dummy_c = torch.zeros(2, 1, 128)

    out_path = EXPORT_DIR / (model_path.stem.replace("hand_lstm", "hand_lstm_nucleo") + ".onnx")

    torch.onnx.export(
        model,
        (dummy_input, (dummy_h, dummy_c)),
        str(out_path),
        input_names  = ["input", "h_in", "c_in"],
        output_names = ["output", "h_out", "c_out"],
        dynamic_axes = {
            "input":  {0: "batch"},
            "h_in":   {1: "batch"},
            "c_in":   {1: "batch"},
            "h_out":  {1: "batch"},
            "c_out":  {1: "batch"},
        },
        opset_version = 17,
        do_constant_folding = True,
    )
    print(f"ONNX gespeichert: {out_path}")

    # Groesse + Parameteranzahl
    n_params = sum(p.numel() for p in model.parameters())
    size_kb  = out_path.stat().st_size / 1024
    print(f"Parameter: {n_params:,}  |  Dateigroesse: {size_kb:.1f} KB")
    print(f"\nfloat32: {n_params*4/1024:.0f} KB")
    print(f"int8:    {n_params*1/1024:.0f} KB  (nach STM32Cube.AI Quantisierung)")

    # Schnelltest: Output-Shape pruefen
    with torch.no_grad():
        out, (h, c) = model(dummy_input, (dummy_h, dummy_c))
    print(f"\nOutput-Shape: {tuple(out.shape)}  (erwartet: [1, 1, 11])")
    print(f"Hidden-Shape: {tuple(h.shape)}")

    print("\nNaechster Schritt:")
    print("  1. STM32CubeIDE oeffnen")
    print("  2. X-CUBE-AI installieren (Help -> Manage Embedded Software Packages)")
    print(f"  3. ONNX-Datei importieren: {out_path}")
    print("  4. Analyse ausfuehren -> pruefen ob Modell auf H723ZG passt")
    print("  5. C-Code generieren")


if __name__ == "__main__":
    export()
