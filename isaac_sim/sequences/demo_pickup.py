"""
isaac_sim/demo_pickup.py — Dose greifen und heben (DirectMode).

Physikalisch verifiziert: hebt Zylinder tatsächlich an.
Keyframes wurden im Physics Inspector validiert (_isaac() negiert auf Onshape-Konvention).

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


def _isaac(d: dict) -> dict:
    """Physics-Inspector-Werte → Onshape-Konvention."""
    return {k: -v for k, v in d.items()}


# ── T-Pose (44 DOFs = 0°) ─────────────────────────────────────────────────────
_T_POSE = {
    "dof_head_horizontal": 0.0, "dof_head_vertical": 0.0,
    "dof_shoulder_vertical_left": 0.0,   "dof_shoulder_horizontal_left": 0.0,
    "dof_upper_arm_left": 0.0,           "dof_elbow_left": 0.0,
    "dof_forearm_left": 0.0,             "dof_wrist_left": 0.0,
    "dof_shoulder_vertical_right": 0.0,  "dof_shoulder_horizontal_right": 0.0,
    "dof_upper_arm_right": 0.0,          "dof_elbow_right": 0.0,
    "dof_forearm_right": 0.0,            "dof_wrist_right": 0.0,
    "dof_thumb_left_rotator": 0.0,  "dof_thumb_left_proximal": 0.0,  "dof_thumb_left_distal": 0.0,
    "dof_index_left_proximal": 0.0, "dof_index_left_distal": 0.0,    "dof_index_left_tip": 0.0,
    "dof_middle_left_proximal": 0.0,"dof_middle_left_distal": 0.0,   "dof_middle_left_tip": 0.0,
    "dof_ring_left_proximal": 0.0,  "dof_ring_left_distal": 0.0,     "dof_ring_left_tip": 0.0,
    "dof_pinky_left_proximal": 0.0, "dof_pinky_left_distal": 0.0,    "dof_pinky_left_tip": 0.0,
    "dof_thumb_right_rotator": 0.0, "dof_thumb_right_proximal": 0.0, "dof_thumb_right_distal": 0.0,
    "dof_index_right_proximal": 0.0,"dof_index_right_distal": 0.0,   "dof_index_right_tip": 0.0,
    "dof_middle_right_proximal": 0.0,"dof_middle_right_distal": 0.0, "dof_middle_right_tip": 0.0,
    "dof_ring_right_proximal": 0.0, "dof_ring_right_distal": 0.0,    "dof_ring_right_tip": 0.0,
    "dof_pinky_right_proximal": 0.0,"dof_pinky_right_distal": 0.0,   "dof_pinky_right_tip": 0.0,
}

# ── Approach-Pose (aus Physics Inspector, negiert auf Onshape) ────────────────
_APPROACH = _isaac({
    "dof_shoulder_vertical_left":    -90.0, "dof_shoulder_horizontal_left": -90.0,
    "dof_upper_arm_left":             -0.1, "dof_elbow_left":               45.0,
    "dof_forearm_left":                0.2,
    "dof_shoulder_vertical_right":   -62.5, "dof_shoulder_horizontal_right": -90.0,
    "dof_elbow_right":               -17.7, "dof_forearm_right":             -1.4,
    "dof_wrist_right":                -4.0,
    "dof_thumb_right_rotator":       -90.0,
})

# ── Greif-Winkel ──────────────────────────────────────────────────────────────
_G = 33.3  # °, Onshape (entspricht Isaac -33.3)

_GRASP = {
    "dof_thumb_right_proximal":  _G, "dof_thumb_right_distal":  _G,
    "dof_index_right_proximal":  _G, "dof_index_right_distal":  _G, "dof_index_right_tip":  _G,
    "dof_middle_right_proximal": _G, "dof_middle_right_distal": _G, "dof_middle_right_tip": _G,
    "dof_ring_right_proximal":   _G, "dof_ring_right_distal":   _G, "dof_ring_right_tip":   _G,
    "dof_pinky_right_proximal":  _G, "dof_pinky_right_distal":  _G, "dof_pinky_right_tip":  _G,
}

# ── Sequenz ───────────────────────────────────────────────────────────────────
SEQ = Sequence("pickup", steps=[
    Step(_T_POSE,    hold_s=2.0, transition_s=0.5, name="neutral"),
    Step(_APPROACH,  hold_s=0.1, transition_s=0.5, name="approach"),
    Step(_GRASP,     hold_s=0.1, transition_s=0.5, name="grasp"),
    Step({"dof_elbow_right": 55.4}, hold_s=0.0, transition_s=0.5, name="lift"),
])

_runner.execute(SEQ, mode="direct")
