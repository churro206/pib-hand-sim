"""
isaac_sim/test_tendon.py — Sehnenmechanik rechte Hand (ServoMode).

Arm absenken, dann Hand 3× langsam schließen und öffnen.
Zeigt Tendon-Mapping: ein Servo-Wert steuert mehrere Gelenke.

Workflow: start.py → Play → dieses Skript ausführen.
"""
import sys
import os
import importlib
import importlib.util

_ROOT = os.environ.get("PIB_HAND_SIM_ROOT", os.path.expanduser("~/repos/pib-hand-sim"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


_runner  = _load_mod("runner", os.path.join(_ROOT, "isaac_sim", "runner.py"),
                     _LIBRARY_MODE=True)
Sequence = _runner.Sequence
Step     = _runner.Step

# ── Bausteine ─────────────────────────────────────────────────────────────────
_ARM_DOWN = {
    "dof_shoulder_vertical_left":    90.0,
    "dof_shoulder_horizontal_left":  90.0,
    "dof_elbow_left":               -90.0,
    "dof_shoulder_horizontal_right": 90.0,
}

_OPEN  = {"thumb_opp":  0, "thumb":  0, "index":  0, "middle":  0, "ring":  0, "pinky":  0}
_CLOSE = {"thumb_opp": 30, "thumb": 90, "index": 90, "middle": 90, "ring": 90, "pinky": 90}

CYCLES = 3
RAMP_S = 5.0

# ── Sequenz ───────────────────────────────────────────────────────────────────
_steps = [Step({**_ARM_DOWN, **_OPEN}, hold_s=2.0, transition_s=1.0, name="arm_runter")]
for i in range(CYCLES):
    _steps.append(Step(_CLOSE, transition_s=RAMP_S, name=f"schliessen_{i + 1}"))
    _steps.append(Step(_OPEN,  transition_s=RAMP_S, name=f"oeffnen_{i + 1}"))

SEQ = Sequence("tendon", steps=_steps)

_runner.execute(SEQ, mode="servo", side="right")
