"""
Offline-Evaluation: LSTM gegen aufgezeichnete Messdaten vergleichen.

Funktioniert mit echten AS5600-Daten (real_*.npz) UND synthetischen Daten
(synthetic_*.npz) — damit kann die Pipeline auch ohne Hardware getestet werden.

Ausfuehren (vom Repo-Root):
    # Neueste Datei automatisch:
    .venv/bin/python inference/evaluate_real.py

    # Explizite Datei:
    .venv/bin/python inference/evaluate_real.py data/real_20260601_120000.npz

    # Synthetische Daten zum Testen der Pipeline:
    .venv/bin/python inference/evaluate_real.py data/synthetic_20260515_153750.npz
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import torch
from training.model import HandLSTM  # type: ignore

REPO_ROOT  = Path(__file__).parent.parent
MODEL_DIR  = REPO_ROOT / "models"
DATA_DIR   = REPO_ROOT / "data"


# ============================================================
#  MODELL LADEN
# ============================================================

def load_model() -> HandLSTM:
    files = sorted(MODEL_DIR.glob("hand_lstm_*.pt"))
    if not files:
        raise FileNotFoundError(f"Kein Modell in {MODEL_DIR}")
    path  = files[-1]
    ckpt  = torch.load(path, map_location="cpu", weights_only=True)
    model = HandLSTM()
    model.load_state_dict(ckpt["model"])
    model.eval()
    print(f"Modell: {path.name}")
    return model


# ============================================================
#  AUTOREGRESSIVE INFERENZ
# ============================================================

def run_lstm(model: HandLSTM, cmd_deg: np.ndarray) -> np.ndarray:
    """
    Fuehrt LSTM autogressiv auf einer cmd-Sequenz aus.
    cmd_deg: (N, 11) Grad
    Gibt pred_deg: (N, 11) Grad zurueck.
    """
    N = cmd_deg.shape[0]
    cmd_norm = -cmd_deg / 90.0                        # [0, 1]
    preds    = np.zeros((N, 11))
    prev     = np.zeros(11)
    hidden   = None

    with torch.no_grad():
        for t in range(N):
            x = torch.tensor(
                np.concatenate([cmd_norm[t], prev]),
                dtype=torch.float32
            ).unsqueeze(0).unsqueeze(0)               # (1, 1, 22)
            out, hidden = model(x, hidden)
            pred_norm = out.squeeze().numpy()         # (11,)
            preds[t]  = -pred_norm * 90.0             # -> Grad
            prev      = pred_norm

    return preds


# ============================================================
#  PLOT
# ============================================================

def plot(log_path: Path, cmd: np.ndarray, pos_real: np.ndarray,
         pos_lstm: np.ndarray, dof_names: list, is_real: bool):

    N   = cmd.shape[0]
    HZ  = 60
    t   = np.arange(N) / HZ

    ncols = 4
    nrows = (len(dof_names) + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3),
                             sharex=True, sharey=True)
    axes = axes.flatten()

    src_label  = "AS5600 (real)" if is_real else "PhysX (synth)"
    src_color  = "#4CAF50"       if is_real else "#2196F3"

    for i, name in enumerate(dof_names):
        ax = axes[i]
        ax.plot(t, cmd[:, i],      color="gray",    lw=1,   ls="--", label="cmd")
        ax.plot(t, pos_real[:, i], color=src_color, lw=1.5, label=src_label)
        ax.plot(t, pos_lstm[:, i], color="#FF5722", lw=1.5, ls=":",  label="LSTM")
        ax.set_title(name, fontsize=8)
        ax.set_ylim(-100, 10)
        ax.set_ylabel("Winkel [°]", fontsize=7)
        ax.grid(True, alpha=0.3)
        if i == 0:
            ax.legend(fontsize=7)

    for j in range(len(dof_names), len(axes)):
        axes[j].set_visible(False)

    for ax in axes[(nrows - 1) * ncols : (nrows - 1) * ncols + ncols]:
        ax.set_xlabel("Zeit [s]")

    mae = np.abs(pos_lstm - pos_real).mean()
    max_err = np.abs(pos_lstm - pos_real).max()
    source  = "echten AS5600-Daten" if is_real else "synthetischen PhysX-Daten"
    fig.suptitle(
        f"{log_path.name}  |  LSTM vs. {source}\n"
        f"MAE: {mae:.2f}°   Max-Fehler: {max_err:.2f}°",
        fontsize=10
    )
    plt.tight_layout()

    out = log_path.with_suffix(".eval.png")
    plt.savefig(out, dpi=150)
    print(f"Plot gespeichert: {out}")
    plt.show()


# ============================================================
#  HAUPTPROGRAMM
# ============================================================

def evaluate(data_path: Path):
    data      = np.load(data_path)
    cmd       = data["cmd"].astype(np.float32)    # (N, 11) Grad
    pos_real  = data["pos"].astype(np.float32)    # (N, 11) Grad (PhysX oder AS5600)
    dof_names = list(data["dof_names"])
    is_real   = data_path.name.startswith("real_")

    print(f"Datei:    {data_path.name}")
    print(f"Samples:  {len(cmd)}  (~{len(cmd)/60:.0f} s @ 60 Hz)")
    print(f"Quelle:   {'echte AS5600-Daten' if is_real else 'synthetische PhysX-Daten'}")

    model     = load_model()
    pos_lstm  = run_lstm(model, cmd)

    mae = np.abs(pos_lstm - pos_real).mean()
    print(f"MAE LSTM vs. Messung: {mae:.2f}°")

    plot(data_path, cmd, pos_real, pos_lstm, dof_names, is_real)

    out_npz = data_path.with_suffix(".eval.npz")
    np.savez(out_npz, cmd=cmd, pos_real=pos_real, pos_lstm=pos_lstm,
             dof_names=np.array(dof_names))
    print(f"Daten gespeichert:    {out_npz}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        files = sorted(DATA_DIR.glob("real_*.npz"))
        if not files:
            # Fallback: neueste synthetische Datei (zum Testen der Pipeline)
            files = sorted(DATA_DIR.glob("synthetic_*.npz"))
        if not files:
            raise FileNotFoundError(f"Keine .npz-Datei in {DATA_DIR}")
        path = files[-1]
        print(f"Keine Datei angegeben — nehme: {path.name}")

    evaluate(path)
