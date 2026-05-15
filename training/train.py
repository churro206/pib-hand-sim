import torch
import torch.nn as nn
from pathlib import Path
from datetime import datetime

from dataset import get_loaders
from model import HandLSTM

DEVICE     = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS     = 50
LR         = 1e-3
MODEL_DIR  = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)


def train():
    print(f"Device: {DEVICE}")
    train_loader, val_loader = get_loaders(batch_size=64)

    model     = HandLSTM().to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.MSELoss()

    best_val  = float("inf")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for epoch in range(1, EPOCHS + 1):
        # --- Training ---
        model.train()
        train_loss = 0.0
        for X, y in train_loader:
            X, y = X.to(DEVICE), y.to(DEVICE)
            optimizer.zero_grad()
            pred, _ = model(X)
            loss = criterion(pred, y)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()
        train_loss /= len(train_loader)

        # --- Validierung ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X, y in val_loader:
                X, y = X.to(DEVICE), y.to(DEVICE)
                pred, _ = model(X)
                val_loss += criterion(pred, y).item()
        val_loss /= len(val_loader)

        scheduler.step(val_loss)
        lr_now = optimizer.param_groups[0]["lr"]

        # Fehler in Grad (0-90° Bereich)
        val_deg = val_loss ** 0.5 * 90.0

        print(f"Epoch {epoch:3d}/{EPOCHS}  "
              f"train={train_loss:.5f}  val={val_loss:.5f}  "
              f"({val_deg:.2f}°)  lr={lr_now:.2e}")

        if val_loss < best_val:
            best_val = val_loss
            path = MODEL_DIR / f"hand_lstm_{timestamp}.pt"
            torch.save({"epoch": epoch, "model": model.state_dict(),
                        "val_loss": val_loss}, path)
            print(f"  -> Modell gespeichert: {path.name}")

    print(f"\nBestes Val-Loss: {best_val:.5f} ({best_val**0.5*90:.2f}°)")


if __name__ == "__main__":
    train()
