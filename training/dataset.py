import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SEQ_LEN  = 32   # Zeitschritte pro Trainingssequenz


def _normalize(pos_deg: np.ndarray) -> np.ndarray:
    return -pos_deg / 90.0  # 0.0=offen, 1.0=geschlossen


def load_all_npz() -> dict:
    """Alle .npz-Dateien laden und zusammenfuehren."""
    files = sorted(DATA_DIR.glob("synthetic_*.npz"))
    if not files:
        raise FileNotFoundError(f"Keine Daten in {DATA_DIR}")
    print(f"{len(files)} Datei(en) gefunden: {[f.name for f in files]}")

    cmds, poss = [], []
    for f in files:
        d = np.load(f, allow_pickle=True)
        cmds.append(_normalize(d["cmd"].astype(np.float32)))
        poss.append(_normalize(d["pos"].astype(np.float32)))

    return {
        "cmd": np.concatenate(cmds, axis=0),
        "pos": np.concatenate(poss, axis=0),
    }


class HandDataset(Dataset):
    """
    Gibt Sequenzen der Laenge SEQ_LEN zurueck.
    Input:  (SEQ_LEN, 22)  — [cmd_t, pos_{t-1}] konkateniert
    Target: (SEQ_LEN, 11)  — pos_t
    """
    def __init__(self, cmd: np.ndarray, pos: np.ndarray):
        n = len(cmd)
        # Sliding-Window-Indizes (kein Ueberlapp ueber Episodengrenzen noetig
        # da die Daten ohnehin zusammenhaengend sind)
        starts = np.arange(0, n - SEQ_LEN, SEQ_LEN // 2)

        self.X = np.stack([
            np.concatenate([cmd[s:s+SEQ_LEN],
                            np.roll(pos[s:s+SEQ_LEN], shift=1, axis=0)], axis=-1)
            for s in starts
        ]).astype(np.float32)
        # pos_{t-1} bei t=0 = pos_t (kein vorheriger Schritt)
        self.X[:, 0, 11:] = self.X[:, 0, :11]

        self.y = np.stack([
            pos[s:s+SEQ_LEN] for s in starts
        ]).astype(np.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return torch.from_numpy(self.X[idx]), torch.from_numpy(self.y[idx])


def get_loaders(val_split: float = 0.15, batch_size: int = 64):
    data   = load_all_npz()
    n      = len(data["cmd"])
    split  = int(n * (1 - val_split))

    train_ds = HandDataset(data["cmd"][:split], data["pos"][:split])
    val_ds   = HandDataset(data["cmd"][split:], data["pos"][split:])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=2)

    print(f"Train: {len(train_ds)} Sequenzen, Val: {len(val_ds)} Sequenzen")
    return train_loader, val_loader
