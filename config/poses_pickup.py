"""
config/poses_pickup.py — Greifposen für die Pickup-Demo.

Jede Pose enthält:
  joints       : alle 44 DOF-Werte in Grad (positiv = Flexion, Onshape-Konvention)
  transition_s : Übergangszeit VON der vorherigen Pose (Sekunden)
  hold_s       : Haltedauer IN dieser Pose (Sekunden)

WICHTIG — Kalibrierung:
  Die Arm-Winkel (approach, grasp, lift, show) sind Startwerte.
  Vor dem echten Demo-Lauf in der Sim visuell prüfen und anpassen.
  Insbesondere dof_shoulder_horizontal_right und dof_elbow_right bestimmen
  wie weit der rechte Arm ausgestreckt ist — ggf. auf pib v4 einstellen.

JOINT_SIGN wird in robot_io.py angewendet — hier immer Onshape-Konvention.
"""

# ── Hilfs-Dictionaries (Arm-Gruppen) ─────────────────────────────────────────

_BODY_NEUTRAL = {
    "dof_head_horizontal":            0,
    "dof_head_vertical":              0,
    "dof_shoulder_vertical_left":     0,
    "dof_shoulder_horizontal_left":   0,
    "dof_upper_arm_left":             0,
    "dof_elbow_left":                 0,
    "dof_forearm_left":               0,
    "dof_wrist_left":                 0,
    "dof_shoulder_vertical_right":    0,
    "dof_shoulder_horizontal_right":  0,
    "dof_upper_arm_right":            0,
    "dof_elbow_right":                0,
    "dof_forearm_right":              0,
    "dof_wrist_right":                0,
}

_HAND_OPEN = {
    # Linke Hand offen
    "dof_thumb_left_rotator":   0,
    "dof_thumb_left_proximal":  0,
    "dof_thumb_left_distal":    0,
    "dof_index_left_proximal":  0,
    "dof_index_left_distal":    0,
    "dof_index_left_tip":       0,
    "dof_middle_left_proximal": 0,
    "dof_middle_left_distal":   0,
    "dof_middle_left_tip":      0,
    "dof_ring_left_proximal":   0,
    "dof_ring_left_distal":     0,
    "dof_ring_left_tip":        0,
    "dof_pinky_left_proximal":  0,
    "dof_pinky_left_distal":    0,
    "dof_pinky_left_tip":       0,
    # Rechte Hand offen
    "dof_thumb_right_rotator":   0,
    "dof_thumb_right_proximal":  0,
    "dof_thumb_right_distal":    0,
    "dof_index_right_proximal":  0,
    "dof_index_right_distal":    0,
    "dof_index_right_tip":       0,
    "dof_middle_right_proximal": 0,
    "dof_middle_right_distal":   0,
    "dof_middle_right_tip":      0,
    "dof_ring_right_proximal":   0,
    "dof_ring_right_distal":     0,
    "dof_ring_right_tip":        0,
    "dof_pinky_right_proximal":  0,
    "dof_pinky_right_distal":    0,
    "dof_pinky_right_tip":       0,
}

# Linke Hand greift (Startwerte — mit AS5600 kalibrieren)
_HAND_LEFT_GRASP = {
    "dof_thumb_left_rotator":   30,
    "dof_thumb_left_proximal":  60,
    "dof_thumb_left_distal":    40,
    "dof_index_left_proximal":  70,
    "dof_index_left_distal":    60,
    "dof_index_left_tip":       40,
    "dof_middle_left_proximal": 70,
    "dof_middle_left_distal":   60,
    "dof_middle_left_tip":      40,
    "dof_ring_left_proximal":   70,
    "dof_ring_left_distal":     60,
    "dof_ring_left_tip":        40,
    "dof_pinky_left_proximal":  70,
    "dof_pinky_left_distal":    60,
    "dof_pinky_left_tip":       40,
}

# Rechte Hand bleibt offen (nur linke Seite aus _HAND_LEFT_GRASP)
_HAND_RIGHT_OPEN = {k: v for k, v in _HAND_OPEN.items() if "right" in k}


def _pose(body_overrides: dict, left_hand: dict, right_hand: dict,
          transition_s: float, hold_s: float) -> dict:
    """Baut ein vollständiges 44-DOF Pose-Dict zusammen."""
    joints = {}
    joints.update(_BODY_NEUTRAL)
    joints.update(body_overrides)
    joints.update(left_hand)
    joints.update(right_hand)
    return {"joints": joints, "transition_s": transition_s, "hold_s": hold_s}


# ── Arm-Konfigurationen ───────────────────────────────────────────────────────

# Arm-Pose für approach/above_can/grasp
# Vorzeichen-Konvention: positiv = Onshape-Flexionsrichtung, exakt wie test_hand_poses.py.
# set_body_targets wendet JOINT_SIGN=-1 an → diese Werte sind User-Konvention.
# Positiv = Arm geht nach vorne (horizontal), nach oben (vertikal), Ellbogen beugt.
# TODO: visuell kalibrieren — Startwerte abgeleitet aus test_hand_poses.py-Konvention.
_ARM_APPROACH = {
    "dof_head_vertical":             30,    # leicht nach unten schauen (pos = nicken; neg = oben)
    "dof_shoulder_vertical_left":    90,    # linken Arm heben
    "dof_shoulder_horizontal_left": -90,    # linken Arm nach vorne (neg = vorne, links gespiegelt)
    "dof_elbow_left":                45,    # linken Ellbogen beugen
    "dof_shoulder_vertical_right":   47,    # rechter Arm etwas angehoben
    "dof_shoulder_horizontal_right": 90,    # rechter Arm nach vorne (pos = vorne, verifiziert)
    "dof_elbow_right":               45,    # rechter Ellbogen
}

# Lift: linker Arm weiter gehoben
_ARM_LIFT = {
    **_ARM_APPROACH,
    "dof_shoulder_vertical_left":    60,   # Arm etwas abgesenkt (statt 90)
    "dof_elbow_left":                60,   # Ellbogen stärker gebeugt
}

# Show: Arm zur Körpermitte
_ARM_SHOW = {
    **_ARM_LIFT,
    "dof_shoulder_horizontal_left": -45,   # Arm zur Körpermitte (neg = vorne)
}


# ── Posen-Definition ──────────────────────────────────────────────────────────

POSES = {
    # Ruheposition — alle Gelenke neutral
    "home": _pose(
        body_overrides={},
        left_hand={k: v for k, v in _HAND_OPEN.items() if "left" in k},
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=2.5,  # Rückkehr zu home am Ende der Sequenz
        hold_s=1.0,
    ),

    # Arm streckt sich Richtung Dose — Annäherung
    "approach": _pose(
        body_overrides=_ARM_APPROACH,
        left_hand={k: v for k, v in _HAND_OPEN.items() if "left" in k},
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=2.5,
        hold_s=1.0,
    ),

    # Über der Dose positioniert — Platzhalter, gleich wie approach
    # TODO: Feintunen sobald Roboter-Position und Tisch-Geometrie kalibriert
    "above_can": _pose(
        body_overrides=_ARM_APPROACH,
        left_hand={k: v for k, v in _HAND_OPEN.items() if "left" in k},
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=1.0,
        hold_s=1.0,
    ),

    # Hand schließt um die Dose
    "grasp": _pose(
        body_overrides=_ARM_APPROACH,
        left_hand=_HAND_LEFT_GRASP,
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=1.2,
        hold_s=1.5,  # länger halten damit man's sieht
    ),

    # Arm hebt die Dose
    "lift": _pose(
        body_overrides=_ARM_LIFT,
        left_hand=_HAND_LEFT_GRASP,
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=1.5,
        hold_s=1.0,
    ),

    # Dose zur Körpermitte zeigen
    "show": _pose(
        body_overrides=_ARM_SHOW,
        left_hand=_HAND_LEFT_GRASP,
        right_hand=_HAND_RIGHT_OPEN,
        transition_s=1.5,
        hold_s=1.5,  # länger halten damit man's sieht
    ),
}

SEQUENCE = ["home", "approach", "above_can", "grasp", "lift", "show", "home"]
