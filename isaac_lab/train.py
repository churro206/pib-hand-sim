"""
train.py — Isaac Labs rsl_rl-Trainingsskript mit den pib-Tasks.

Registriert die Tasks aus pib_grasp und startet dann unverändert
~/IsaacLab/scripts/reinforcement_learning/rsl_rl/train.py (alle Argumente gleich).

  ~/IsaacLab/isaaclab.sh -p isaac_lab/train.py --task Pib-Grasp-Hand-Left-v0 --headless
Logs: ~/IsaacLab/logs/rsl_rl/pib_grasp_hand_left/ (relativ zum Arbeitsverzeichnis: logs/)
"""
import os
import runpy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RSL_RL_SCRIPTS = Path(os.environ.get("ISAACLAB_PATH", Path.home() / "IsaacLab")) / "scripts/reinforcement_learning/rsl_rl"

sys.path[:0] = [str(HERE), str(RSL_RL_SCRIPTS)]
import pib_grasp  # noqa: E402,F401  (registriert die Gym-Tasks)

# play.py setzt PIB_RSL_RL_SCRIPT=play (runpy überschreibt sys.argv[0], daran lässt es sich
# nicht erkennen)
target = RSL_RL_SCRIPTS / ("play.py" if os.environ.get("PIB_RSL_RL_SCRIPT") == "play" else "train.py")
sys.argv[0] = str(target)
runpy.run_path(str(target), run_name="__main__")
