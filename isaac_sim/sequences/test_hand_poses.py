"""
isaac_sim/test_hand_poses.py — Winken → Doppelbizeps → Peace (DirectMode).

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
_NEUTRAL = {
    "dof_head_horizontal": 0.0, "dof_head_vertical": 0.0,
    "dof_shoulder_vertical_left": 0.0,   "dof_shoulder_horizontal_left": 0.0,
    "dof_upper_arm_left": 0.0,           "dof_elbow_left": 0.0,
    "dof_forearm_left": 0.0,             "dof_wrist_left": 0.0,
    "dof_shoulder_vertical_right": 0.0,  "dof_shoulder_horizontal_right": 0.0,
    "dof_upper_arm_right": 0.0,          "dof_elbow_right": 0.0,
    "dof_forearm_right": 0.0,            "dof_wrist_right": 0.0,
    # Hände offen
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

_FIST_LEFT = {
    "dof_thumb_left_rotator": 30.0,
    "dof_thumb_left_proximal": 80.0,  "dof_thumb_left_distal": 80.0,
    "dof_index_left_proximal": 85.0,  "dof_index_left_distal": 68.0,  "dof_index_left_tip": 51.0,
    "dof_middle_left_proximal": 85.0, "dof_middle_left_distal": 68.0, "dof_middle_left_tip": 51.0,
    "dof_ring_left_proximal": 85.0,   "dof_ring_left_distal": 68.0,   "dof_ring_left_tip": 51.0,
    "dof_pinky_left_proximal": 85.0,  "dof_pinky_left_distal": 68.0,  "dof_pinky_left_tip": 51.0,
}

_FIST_RIGHT = {
    "dof_thumb_right_rotator": 30.0,
    "dof_thumb_right_proximal": 80.0,  "dof_thumb_right_distal": 80.0,
    "dof_index_right_proximal": 85.0,  "dof_index_right_distal": 68.0,  "dof_index_right_tip": 51.0,
    "dof_middle_right_proximal": 85.0, "dof_middle_right_distal": 68.0, "dof_middle_right_tip": 51.0,
    "dof_ring_right_proximal": 85.0,   "dof_ring_right_distal": 68.0,   "dof_ring_right_tip": 51.0,
    "dof_pinky_right_proximal": 85.0,  "dof_pinky_right_distal": 68.0,  "dof_pinky_right_tip": 51.0,
}

# ── Sequenz ───────────────────────────────────────────────────────────────────
SEQ = Sequence("hand_poses", steps=[
    Step(_NEUTRAL, hold_s=1.0, name="neutral"),

    # Winken (3×)
    Step({
        "dof_head_horizontal": 25.0,
        "dof_shoulder_vertical_left": -30.0, "dof_elbow_left": 15.0,
        "dof_shoulder_horizontal_right": 20.0, "dof_elbow_right": 65.0,
    }, hold_s=0.2, transition_s=0.3, name="wink_a"),
    Step({"dof_elbow_right": 90.0}, hold_s=0.2, transition_s=0.2, name="wink_b"),
    Step({"dof_elbow_right": 65.0}, hold_s=0.2, transition_s=0.2, name="wink_a"),
    Step({"dof_elbow_right": 90.0}, hold_s=0.2, transition_s=0.2, name="wink_b"),
    Step({"dof_elbow_right": 65.0}, hold_s=0.2, transition_s=0.2, name="wink_a"),
    Step({"dof_elbow_right": 90.0}, hold_s=0.2, transition_s=0.2, name="wink_b"),

    # Doppelbizeps
    Step({
        **_NEUTRAL,
        "dof_elbow_left": 90.0,  "dof_forearm_left": 90.0,  "dof_wrist_left": 90.0,
        "dof_elbow_right": 90.0, "dof_forearm_right": 90.0, "dof_wrist_right": 90.0,
        **_FIST_LEFT, **_FIST_RIGHT,
    }, hold_s=2.0, transition_s=0.5, name="doppelbizeps"),

    # Peace
    Step({
        **_NEUTRAL,
        "dof_head_horizontal": -15.0,
        "dof_shoulder_vertical_left": -30.0,  "dof_elbow_left": 20.0,
        "dof_shoulder_vertical_right": 30.0,  "dof_shoulder_horizontal_right": 25.0,
        "dof_elbow_right": 40.0,
        "dof_thumb_right_rotator": 30.0,
        "dof_thumb_right_proximal": 60.0, "dof_thumb_right_distal": 60.0,
        "dof_index_right_proximal": 0.0,  "dof_index_right_distal": 0.0,  "dof_index_right_tip": 0.0,
        "dof_middle_right_proximal": 0.0, "dof_middle_right_distal": 0.0, "dof_middle_right_tip": 0.0,
        "dof_ring_right_proximal": 85.0,  "dof_ring_right_distal": 68.0,  "dof_ring_right_tip": 51.0,
        "dof_pinky_right_proximal": 85.0, "dof_pinky_right_distal": 68.0, "dof_pinky_right_tip": 51.0,
    }, hold_s=2.0, transition_s=0.5, name="peace"),

    Step(_NEUTRAL, hold_s=2.0, transition_s=0.5, name="neutral"),
])

_runner.execute(SEQ, mode="direct")
