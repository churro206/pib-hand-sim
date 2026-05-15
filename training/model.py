import torch
import torch.nn as nn

INPUT_SIZE  = 22   # 11 cmd + 11 pos_{t-1}
HIDDEN_SIZE = 128
NUM_LAYERS  = 2
OUTPUT_SIZE = 11   # pos_t fuer alle Fingergelenke


class HandLSTM(nn.Module):
    """
    Vorwaertsmodell: (sollpos_t, istpos_{t-1}) -> istpos_t
    Lernt Dynamik: Traegheit, Reibung, Hysterese.
    """
    def __init__(self, input_size=INPUT_SIZE, hidden_size=HIDDEN_SIZE,
                 num_layers=NUM_LAYERS, output_size=OUTPUT_SIZE, dropout=0.1):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, output_size),
            nn.Sigmoid(),  # Ausgabe in [0, 1] (normierte Position)
        )

    def forward(self, x: torch.Tensor, hidden=None):
        # x: (batch, seq_len, 22)
        out, hidden = self.lstm(x, hidden)          # (batch, seq_len, hidden)
        pred = self.head(out)                        # (batch, seq_len, 11)
        return pred, hidden

    def predict_sequence(self, cmd_seq: torch.Tensor) -> torch.Tensor:
        """Autoregressiv: gibt pos_{t-1} aus dem eigenen Output zurueck."""
        batch = cmd_seq.shape[0]
        seq   = cmd_seq.shape[1]
        prev_pos = torch.zeros(batch, 11, device=cmd_seq.device)
        preds, hidden = [], None

        for t in range(seq):
            x_t   = torch.cat([cmd_seq[:, t, :], prev_pos], dim=-1).unsqueeze(1)
            out_t, hidden = self.forward(x_t, hidden)
            prev_pos = out_t.squeeze(1)
            preds.append(prev_pos)

        return torch.stack(preds, dim=1)  # (batch, seq, 11)
