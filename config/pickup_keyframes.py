"""
config/pickup_keyframes.py — Validierte Keyframes für die Pickup-Demo.

Alle Winkel in Isaac-Konvention (direkt aus Physics Inspector abgelesen).
apply_full_pose in robot_io.py kompensiert das Vorzeichen intern.

Keyframes:
  KEYFRAME_0 — Neutral (alle 44 DOF auf 0°)
  KEYFRAME_1 — Anfahren (Hand offen, rechter Arm über Dose)
  KEYFRAME_2 — Greifen  (Finger schließen auf -33.3°)
  KEYFRAME_3 — Heben    (Ellbogen beugt weiter auf -55.4°)
"""
from dataclasses import dataclass

# ── Neutral-Basis (alle 44 DOF = 0) ──────────────────────────────────────────

_ZEROS: dict = {
    # Kopf
    "dof_head_horizontal":           0.0,
    "dof_head_vertical":             0.0,
    # Linker Arm
    "dof_shoulder_vertical_left":    0.0,
    "dof_shoulder_horizontal_left":  0.0,
    "dof_upper_arm_left":            0.0,
    "dof_elbow_left":                0.0,
    "dof_forearm_left":              0.0,
    "dof_wrist_left":                0.0,
    # Rechter Arm
    "dof_shoulder_vertical_right":   0.0,
    "dof_shoulder_horizontal_right": 0.0,
    "dof_upper_arm_right":           0.0,
    "dof_elbow_right":               0.0,
    "dof_forearm_right":             0.0,
    "dof_wrist_right":               0.0,
    # Linke Hand
    "dof_thumb_left_rotator":        0.0,
    "dof_thumb_left_proximal":       0.0,
    "dof_thumb_left_distal":         0.0,
    "dof_index_left_proximal":       0.0,
    "dof_index_left_distal":         0.0,
    "dof_index_left_tip":            0.0,
    "dof_middle_left_proximal":      0.0,
    "dof_middle_left_distal":        0.0,
    "dof_middle_left_tip":           0.0,
    "dof_ring_left_proximal":        0.0,
    "dof_ring_left_distal":          0.0,
    "dof_ring_left_tip":             0.0,
    "dof_pinky_left_proximal":       0.0,
    "dof_pinky_left_distal":         0.0,
    "dof_pinky_left_tip":            0.0,
    # Rechte Hand
    "dof_thumb_right_rotator":       0.0,
    "dof_thumb_right_proximal":      0.0,
    "dof_thumb_right_distal":        0.0,
    "dof_index_right_proximal":      0.0,
    "dof_index_right_distal":        0.0,
    "dof_index_right_tip":           0.0,
    "dof_middle_right_proximal":     0.0,
    "dof_middle_right_distal":       0.0,
    "dof_middle_right_tip":          0.0,
    "dof_ring_right_proximal":       0.0,
    "dof_ring_right_distal":         0.0,
    "dof_ring_right_tip":            0.0,
    "dof_pinky_right_proximal":      0.0,
    "dof_pinky_right_distal":        0.0,
    "dof_pinky_right_tip":           0.0,
}

# ── Keyframes (vom User im Physics Inspector validiert) ───────────────────────

KEYFRAME_0: dict = dict(_ZEROS)

KEYFRAME_1: dict = {
    **_ZEROS,
    # Linker Arm — Haltepose
    "dof_shoulder_vertical_left":    -90.0,
    "dof_shoulder_horizontal_left":  -90.0,
    "dof_upper_arm_left":             -0.1,
    "dof_elbow_left":                 45.0,
    "dof_forearm_left":                0.2,
    # Rechter Arm — Hand offen über Dose
    "dof_shoulder_vertical_right":   -62.5,
    "dof_shoulder_horizontal_right": -90.0,
    "dof_elbow_right":               -17.7,
    "dof_forearm_right":              -1.4,
    "dof_wrist_right":                -4.0,
    # Rechte Hand — offen, Daumen opponiert
    "dof_thumb_right_rotator":       -90.0,
}

_G = -33.3  # Greifwinkel aller Finger (validiert)

KEYFRAME_2: dict = {
    **KEYFRAME_1,
    "dof_thumb_right_proximal":      _G,
    "dof_thumb_right_distal":        _G,
    "dof_index_right_proximal":      _G,
    "dof_index_right_distal":        _G,
    "dof_index_right_tip":           _G,
    "dof_middle_right_proximal":     _G,
    "dof_middle_right_distal":       _G,
    "dof_middle_right_tip":          _G,
    "dof_ring_right_proximal":       _G,
    "dof_ring_right_distal":         _G,
    "dof_ring_right_tip":            _G,
    "dof_pinky_right_proximal":      _G,
    "dof_pinky_right_distal":        _G,
    "dof_pinky_right_tip":           _G,
}

KEYFRAME_3: dict = {
    **KEYFRAME_2,
    "dof_elbow_right": -55.4,
}


# ── Sequenz ───────────────────────────────────────────────────────────────────

@dataclass
class SequenceStep:
    name:         str
    keyframe:     dict
    transition_s: float  # Übergangszeit von vorheriger Pose
    hold_s:       float  # Haltedauer; 0.0 = nach Sequenz unbegrenzt halten


PICKUP_SEQUENCE: list = [
    SequenceStep("neutral",  KEYFRAME_0, transition_s=0.5, hold_s=2.0),
    SequenceStep("approach", KEYFRAME_1, transition_s=0.5, hold_s=0.1),
    SequenceStep("grasp",    KEYFRAME_2, transition_s=0.5, hold_s=0.1),
    SequenceStep("lift",     KEYFRAME_3, transition_s=0.5, hold_s=0.0),
]
