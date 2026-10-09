"""
backup_policies.py — Trainierte Policies der Experimente nach Hugging Face sichern (privates Repo).

Je Lauf (logs/rsl_rl/pib_grasp_hand_left/<lauf>/) nur das Nötige: letzter Checkpoint (zum
Weitertrainieren), exported/ (JIT + ONNX für den Nucleo), params/, meta.json, Diff, Bewertung,
TensorBoard-Log, Video — keine Zwischen-Checkpoints. Dazu experiments/ (Pläne, Berichte) und
eine Modellkarte. Unveränderte Dateien lädt Hugging Face nicht erneut hoch (Hash-Abgleich).

Start über isaaclab.sh -p (nur Python, keine Simulation — liefert requests für huggingface_hub):
  conda activate env_isaaclab
  ~/IsaacLab/isaaclab.sh -p isaac_lab/backup_policies.py            # Probelauf: was, wie groß
  ~/IsaacLab/isaaclab.sh -p isaac_lab/backup_policies.py --upload   # hochladen (Repo privat)
Anmeldung vorher einmalig selbst: hf auth login (Token nie ins Repo/in Skripte).
"""
import argparse
import os
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "logs" / "rsl_rl" / "pib_grasp_hand_left"
DEFAULT_REPO_ID = "churro206/pib-grasp-policies"
KEEP = ["exported/*", "params/*", "meta.json", "pib_hand_sim.diff", "pib_hand_sim_untracked.tar.gz",
        "eval-v*.json", "eval-v*.txt", "verlauf-v*.json", "events.out.tfevents.*", "video_eval/videos/*.mp4"]

MODEL_CARD = """---
license: other
tags: [reinforcement-learning, isaac-lab, robotics, dexterous-grasping, rsl-rl]
---
# pib v5 Hand — RL-Greif-Policies (Sicherung)

Privates Archiv der in Isaac Lab trainierten Greif-Policies der realen linken pib-v5-Hand
(Projekt `pib-hand-sim`, Branch `feature/rl-grasping`). Ziel-Hardware: STM32N657 (NPU, int8).

- `runs/<lauf>/` — je Trainingslauf: letzter Checkpoint (`model_*.pt`, rsl_rl), `exported/policy.pt`
  (TorchScript) und `exported/policy.onnx` (Actor inkl. Beobachtungsnormierung), `params/` (vollständige
  Isaac-Lab-Konfiguration), `meta.json` (Commit, Versionen), `eval-v*.*` (Bewertung je Protokoll), TensorBoard-Log, Video
- `experiments/` — Hypothesen, Berichte und Übersicht (`index.md`), Ablauf und Metriken (`README.md`)

**Actor-Eingang** (105 = 5 Schritte × 21): 8 Servo-Winkel [rad] (forearm, wrist, thumb_rotator,
thumb/index/middle/ring/pinky proximal), 5 FSR [N, 0–20] (Daumen … klein), 8 letzte Aktionen.
**Ausgang**: 8 relative Gelenkziele (× 0,03 rad Unterarm/Handgelenk, × 0,1 rad übrige).
Details: `docs/conventions.md` → „Isaac Lab“ im Projekt-Repository.
"""


def files_of(run: Path) -> list[Path]:
    ckpts = sorted(run.glob("model_*.pt"), key=lambda p: int(p.stem.split("_")[1]))
    out = ckpts[-1:]                                   # nur der letzte Checkpoint
    for pattern in KEEP:
        out += [p for p in run.glob(pattern) if p.is_file()]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    ap.add_argument("--upload", action="store_true", help="tatsächlich hochladen (sonst nur anzeigen)")
    a = ap.parse_args()

    runs = sorted(p for p in RUNS.glob("*") if p.is_dir() and any(p.glob("model_*.pt")))
    total = 0
    for run in runs:
        size = sum(f.stat().st_size for f in files_of(run))
        total += size
        print(f"{run.name:45s} {len(files_of(run)):3d} Dateien  {size / 1e6:7.1f} MB")
    exp_size = sum(f.stat().st_size for f in (REPO / "experiments").rglob("*") if f.is_file())
    print(f"{'experiments/':45s} {exp_size / 1e6:19.1f} MB")
    print(f"Gesamt: {len(runs)} Läufe, {(total + exp_size) / 1e6:.1f} MB → {a.repo_id} (privat)")
    if not a.upload:
        print("Probelauf — mit --upload hochladen.")
        return

    from huggingface_hub import HfApi
    api = HfApi()
    print(f"Angemeldet als: {api.whoami()['name']}")
    api.create_repo(a.repo_id, repo_type="model", private=True, exist_ok=True)
    # Staging mit Hardlinks (kein zusätzlicher Speicher), dann ein einziger Upload
    with tempfile.TemporaryDirectory(dir=REPO / "logs") as tmp:
        stage = Path(tmp)
        for run in runs:
            for f in files_of(run):
                dst = stage / "runs" / run.name / f.relative_to(run)
                dst.parent.mkdir(parents=True, exist_ok=True)
                os.link(f, dst)
        shutil.copytree(REPO / "experiments", stage / "experiments")
        (stage / "README.md").write_text(MODEL_CARD, encoding="utf-8")
        commit = os.popen(f"git -C {REPO} rev-parse --short HEAD").read().strip()
        api.upload_folder(repo_id=a.repo_id, repo_type="model", folder_path=str(stage),
                          commit_message=f"Sicherung der Experiment-Läufe (pib-hand-sim {commit})")
    print(f"Fertig: https://huggingface.co/{a.repo_id}")


if __name__ == "__main__":
    main()
