"""
tools/sequence_template.py — Vorlage für neue Sequenzen.

Workflow:
  1. Diese Datei kopieren (z.B. nach isaac_sim/meine_sequenz.py)
  2. Steps im markierten Block anpassen
  3. Im Isaac Script Editor öffnen und ausführen
     (start.py + Play müssen vorher gelaufen sein)

Erneut ausführen nach Änderungen — kein Isaac-Neustart nötig.
"""
import sys
import os
import importlib
import importlib.util

# ── Projekt-Root finden ───────────────────────────────────────────────────────
_ROOT = os.environ.get(
    "PIB_HAND_SIM_ROOT",
    os.path.expanduser("~/repos/pib-hand-sim"),
)
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


# ── runner als Library laden (kein auto-execute) ──────────────────────────────
_runner  = _load_mod("runner", os.path.join(_ROOT, "isaac_sim", "runner.py"),
                     _LIBRARY_MODE=True)
Sequence = _runner.Sequence
Step     = _runner.Step


# ══ SEQUENZ HIER ANPASSEN ════════════════════════════════════════════════════
#
# target: nur die Gelenke/Servos die sich ändern — Rest hält seinen Wert.
#
# DOF-Namen (DirectMode):  dof_index_right_proximal, dof_elbow_right, ...
# Servo-Namen (ServoMode): thumb_opp, thumb, index, middle, ring, pinky
#
# Winkel: Grad, Onshape-Konvention (positiv = Flexion / Heben / Vorne)
# Hand-Bereich: [0°, 90°];  Body: asymmetrisch, kein Clip

SEQ = Sequence("meine_sequenz", steps=[
    Step(
        target={"dof_index_right_proximal": 0.0},
        hold_s=1.0,
        name="offen",
    ),
    Step(
        target={"dof_index_right_proximal": 90.0},
        transition_s=2.0,
        hold_s=1.0,
        name="zu",
    ),
    Step(
        target={"dof_index_right_proximal": 0.0},
        transition_s=2.0,
        hold_s=1.0,
        name="offen",
    ),
])

MODE = "direct"   # direct | servo | nn
SIDE = "right"    # left | right  (nur relevant für servo / nn)

# ═════════════════════════════════════════════════════════════════════════════

_runner.execute(SEQ, mode=MODE, side=SIDE)
