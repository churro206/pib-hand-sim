"""
config/sequences.py — Ebene 3: Pose-Sequenzen für pib.

Eine Sequenz ist eine Liste von Steps. Jeder Step gibt ein Ziel-Kommando, eine
Übergangszeit (Ramp) und eine Haltedauer an. Der Runner (isaac_sim/runner.py)
führt sie über den gewählten ControlMode aus.

Wichtigste Regel — NICHT redundant:
  Ein Step listet NUR die Gelenke/Servos die sich ändern. Alles andere hält
  seinen Wert aus dem vorherigen Step (persistenter Zustand im Runner).

command-Keys:
  dof_*       → direkter Gelenkwinkel (Onshape-Konvention: positiv = Flexion/Vorne/Heben)
  servo_name  → nur sinnvoll mit ServoMode/NNMode (thumb_opp, thumb, index, ...)

Konventions-Hinweis Pickup:
  Die Pickup-Keyframes wurden im Physics Inspector (Isaac-Konvention) validiert.
  _isaac() negiert sie in die Onshape-Konvention — verlustfrei, da set_all_targets
  identisch zu apply_full_pose(isaac) arbeitet.

Mode-Kompatibilität:
  HAND_POSES → direct
  TENDON     → servo (right) oder nn
  PICKUP     → direct
"""
from dataclasses import dataclass, field


@dataclass
class Step:
    target:       dict           # nur die Änderungen ggü. vorherigem Step
    hold_s:       float = 0.0     # Haltedauer nach Erreichen
    transition_s: float = 0.0     # Übergangszeit (0 = sofort, >0 = Smoothstep-Ramp)
    name:         str   = ""      # optionales Label fürs Logging


@dataclass
class Sequence:
    name:  str
    steps: list = field(default_factory=list)


def _isaac(d: dict) -> dict:
    """Isaac-Inspector-Werte → Onshape-Konvention (Negation)."""
    return {k: -v for k, v in d.items()}


# ══ Wiederverwendbare Bausteine ═══════════════════════════════════════════════

_BODY_NEUTRAL = {
    "dof_head_horizontal":           0.0, "dof_head_vertical":             0.0,
    "dof_shoulder_vertical_left":    0.0, "dof_shoulder_horizontal_left":  0.0,
    "dof_upper_arm_left":            0.0, "dof_elbow_left":                0.0,
    "dof_forearm_left":              0.0, "dof_wrist_left":                0.0,
    "dof_shoulder_vertical_right":   0.0, "dof_shoulder_horizontal_right": 0.0,
    "dof_upper_arm_right":           0.0, "dof_elbow_right":               0.0,
    "dof_forearm_right":             0.0, "dof_wrist_right":               0.0,
}

_HAND_OPEN = {  # eine Seite offen — _side() expandiert auf left/right
    "thumb_rotator":  0.0,
    "thumb_proximal": 0.0, "thumb_distal":  0.0,
    "index_proximal": 0.0, "index_distal":  0.0, "index_tip":  0.0,
    "middle_proximal":0.0, "middle_distal": 0.0, "middle_tip": 0.0,
    "ring_proximal":  0.0, "ring_distal":   0.0, "ring_tip":   0.0,
    "pinky_proximal": 0.0, "pinky_distal":  0.0, "pinky_tip":  0.0,
}

_HAND_FIST = {
    "thumb_rotator":  30.0,
    "thumb_proximal": 80.0, "thumb_distal":  80.0,
    "index_proximal": 85.0, "index_distal":  68.0, "index_tip":  51.0,
    "middle_proximal":85.0, "middle_distal": 68.0, "middle_tip": 51.0,
    "ring_proximal":  85.0, "ring_distal":   68.0, "ring_tip":   51.0,
    "pinky_proximal": 85.0, "pinky_distal":  68.0, "pinky_tip":  51.0,
}


def _side(part: dict, side: str) -> dict:
    """{teil_xxx: deg} → {dof_teil_<side>_xxx: deg}."""
    return {f"dof_{k.rsplit('_', 1)[0]}_{side}_{k.rsplit('_', 1)[1]}": v
            for k, v in part.items()}


# Vollständige T-Pose (44 DOF = 0) — einmal definiert, als Reset-Baustein.
T_POSE = {**_BODY_NEUTRAL, **_side(_HAND_OPEN, "left"), **_side(_HAND_OPEN, "right")}


# ══ HAND_POSES — DirectMode ═══════════════════════════════════════════════════
# Winken → Doppelbizeps → Peace. command = {dof_name: deg}.

_WINK_BODY = {
    "dof_head_horizontal":           25.0,
    "dof_shoulder_vertical_left":   -30.0, "dof_elbow_left": 15.0,
    "dof_shoulder_horizontal_right": 20.0,
}

HAND_POSES = Sequence("hand_poses", [
    Step(T_POSE,                                     hold_s=1.0,                  name="neutral"),
    Step({**_WINK_BODY, "dof_elbow_right": 65.0},    hold_s=0.2, transition_s=0.3, name="wink_a"),
    Step({"dof_elbow_right": 90.0},                  hold_s=0.2, transition_s=0.2, name="wink_b"),
    Step({"dof_elbow_right": 65.0},                  hold_s=0.2, transition_s=0.2, name="wink_a"),
    Step({"dof_elbow_right": 90.0},                  hold_s=0.2, transition_s=0.2, name="wink_b"),
    Step({"dof_elbow_right": 65.0},                  hold_s=0.2, transition_s=0.2, name="wink_a"),
    Step({"dof_elbow_right": 90.0},                  hold_s=0.2, transition_s=0.2, name="wink_b"),
    Step({  # Doppelbizeps — beide Ellbogen 90°, Unterarme gedreht, Fäuste
        **_BODY_NEUTRAL,
        "dof_elbow_left":  90.0, "dof_forearm_left":  90.0, "dof_wrist_left":  90.0,
        "dof_elbow_right": 90.0, "dof_forearm_right": 90.0, "dof_wrist_right": 90.0,
        **_side(_HAND_FIST, "left"), **_side(_HAND_FIST, "right"),
    }, hold_s=2.0, transition_s=0.5, name="doppelbizeps"),
    Step({  # Peace — rechte Hand V-Zeichen
        **_BODY_NEUTRAL,
        "dof_head_horizontal":          -15.0,
        "dof_shoulder_vertical_left":   -30.0, "dof_elbow_left": 20.0,
        "dof_shoulder_vertical_right":   30.0, "dof_shoulder_horizontal_right": 25.0,
        "dof_elbow_right":               40.0,
        **_side(_HAND_OPEN, "left"),
        "dof_thumb_right_rotator":   30.0,
        "dof_thumb_right_proximal":  60.0, "dof_thumb_right_distal":  60.0,
        "dof_index_right_proximal":   0.0, "dof_index_right_distal":   0.0, "dof_index_right_tip":  0.0,
        "dof_middle_right_proximal":  0.0, "dof_middle_right_distal":  0.0, "dof_middle_right_tip": 0.0,
        "dof_ring_right_proximal":   85.0, "dof_ring_right_distal":   68.0, "dof_ring_right_tip":  51.0,
        "dof_pinky_right_proximal":  85.0, "dof_pinky_right_distal":  68.0, "dof_pinky_right_tip": 51.0,
    }, hold_s=2.0, transition_s=0.5, name="peace"),
    Step(T_POSE, hold_s=2.0, transition_s=0.5, name="neutral"),
])


# ══ TENDON — ServoMode("right") ═══════════════════════════════════════════════
# Rechten Arm nach vorne, dann Hand 3× langsam schließen/öffnen (Sehnenmechanik).
# Arm via dof_* (Pass-through), Finger via Servo-Namen.

_ARM_DOWN = {
    "dof_shoulder_vertical_left":   90.0,
    "dof_shoulder_horizontal_left": 90.0,
    "dof_elbow_left": -90,
    "dof_shoulder_horizontal_right": 90.0,  
}
_SERVO_OPEN  = {"thumb_opp":  0, "thumb":  0, "index":  0, "middle":  0, "ring":  0, "pinky":  0}
_SERVO_CLOSE = {"thumb_opp": 30, "thumb": 90, "index": 90, "middle": 90, "ring": 90, "pinky": 90}


def _tendon_steps(cycles: int = 3, ramp_s: float = 5.0) -> list:
    steps = [Step({**_ARM_DOWN, **_SERVO_OPEN}, hold_s=2.0, transition_s=1.0, name="arm_runter")]
    for i in range(cycles):
        steps.append(Step(_SERVO_CLOSE, transition_s=ramp_s, name=f"schliessen_{i+1}"))
        steps.append(Step(_SERVO_OPEN,  transition_s=ramp_s, name=f"oeffnen_{i+1}"))
    return steps


TENDON = Sequence("tendon", _tendon_steps())


# ══ PICKUP — DirectMode ═══════════════════════════════════════════════════════
# Dose greifen und heben. Im Inspector (Isaac) validiert → _isaac() negiert.
# Physikalisch verifiziert: hebt den Zylinder tatsächlich an.

_PICKUP_APPROACH = _isaac({
    # Linker Arm — Haltepose
    "dof_shoulder_vertical_left":    -90.0, "dof_shoulder_horizontal_left": -90.0,
    "dof_upper_arm_left":             -0.1, "dof_elbow_left":               45.0,
    "dof_forearm_left":                0.2,
    # Rechter Arm — Hand offen über Dose
    "dof_shoulder_vertical_right":   -62.5, "dof_shoulder_horizontal_right": -90.0,
    "dof_elbow_right":               -17.7, "dof_forearm_right":             -1.4,
    "dof_wrist_right":                -4.0,
    # Daumen opponiert
    "dof_thumb_right_rotator":       -90.0,
})

_G = 33.3  # Greifwinkel aller Finger (Onshape; entspricht Isaac -33.3)
_PICKUP_GRASP = {
    "dof_thumb_right_proximal":  _G, "dof_thumb_right_distal":  _G,
    "dof_index_right_proximal":  _G, "dof_index_right_distal":  _G, "dof_index_right_tip":  _G,
    "dof_middle_right_proximal": _G, "dof_middle_right_distal": _G, "dof_middle_right_tip": _G,
    "dof_ring_right_proximal":   _G, "dof_ring_right_distal":   _G, "dof_ring_right_tip":   _G,
    "dof_pinky_right_proximal":  _G, "dof_pinky_right_distal":  _G, "dof_pinky_right_tip":  _G,
}

PICKUP = Sequence("pickup", [
    Step(T_POSE,            hold_s=2.0, transition_s=0.5, name="neutral"),
    Step(_PICKUP_APPROACH,  hold_s=0.1, transition_s=0.5, name="approach"),
    Step(_PICKUP_GRASP,     hold_s=0.1, transition_s=0.5, name="grasp"),
    Step({"dof_elbow_right": 55.4}, hold_s=0.0, transition_s=0.5, name="lift"),
])


# ── Registry für den Runner (Name → Sequenz) ─────────────────────────────────
ALL = {seq.name: seq for seq in (HAND_POSES, TENDON, PICKUP)}
