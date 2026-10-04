"""play.py — wie train.py, startet Isaac Labs rsl_rl/play.py (lädt den letzten Checkpoint,
exportiert die Policy als ONNX/JIT nach <log>/exported/)."""
import os
import runpy
from pathlib import Path

os.environ["PIB_RSL_RL_SCRIPT"] = "play"

runpy.run_path(str(Path(__file__).resolve().parent / "train.py"), run_name="__main__")
