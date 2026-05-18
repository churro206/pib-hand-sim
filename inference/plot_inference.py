"""
Plottet LSTM- vs PhysX-Trajektorien aus einer Inferenz-Log-Datei.

Ausfuehren (vom Repo-Root):
    .venv/bin/python inference/plot_inference.py
    .venv/bin/python inference/plot_inference.py data/inference_compare_XYZ.npz
"""
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def find_latest_log() -> Path:
    files = sorted(DATA_DIR.glob("inference_*.npz"))
    if not files:
        raise FileNotFoundError(f"Keine Inferenz-Logdatei in {DATA_DIR}")
    return files[-1]


def plot(log_path: Path):
    data      = np.load(log_path)
    cmd       = data["cmd"]        # (N, 11) Grad
    pos_phys  = data["pos_phys"]   # (N, 11) Grad
    pos_lstm  = data["pos_lstm"]   # (N, 11) Grad
    dof_names = data["dof_names"]  # (11,)

    N   = cmd.shape[0]
    HZ  = 60
    t   = np.arange(N) / HZ       # Zeitachse in Sekunden

    n_dofs = len(dof_names)
    ncols  = 4
    nrows  = (n_dofs + ncols - 1) // ncols  # aufgerundet

    fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3),
                             sharex=True, sharey=True)
    axes = axes.flatten()

    for i, name in enumerate(dof_names):
        ax = axes[i]
        ax.plot(t, cmd[:, i],      color="gray",   lw=1,   ls="--", label="cmd")
        ax.plot(t, pos_phys[:, i], color="#2196F3", lw=1.5, label="PhysX")
        ax.plot(t, pos_lstm[:, i], color="#FF5722", lw=1.5, ls=":",  label="LSTM")
        ax.set_title(name, fontsize=8)
        ax.set_ylabel("Winkel [°]")
        ax.set_ylim(-100, 10)
        ax.grid(True, alpha=0.3)
        if i == 0:
            ax.legend(fontsize=7)

    # Leere Subplots ausblenden
    for j in range(n_dofs, len(axes)):
        axes[j].set_visible(False)

    for ax in axes[(nrows - 1) * ncols:]:
        ax.set_xlabel("Zeit [s]")

    # Mittlerer absoluter Fehler ueber alle DOFs und Zeit
    mae = np.abs(pos_lstm - pos_phys).mean()
    fig.suptitle(
        f"{log_path.name}\nMAE LSTM vs PhysX: {mae:.2f}°",
        fontsize=10
    )
    plt.tight_layout()

    out = log_path.with_suffix(".png")
    plt.savefig(out, dpi=150)
    print(f"Gespeichert: {out}")
    plt.show()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else find_latest_log()
    print(f"Lade: {path.name}")
    plot(path)
