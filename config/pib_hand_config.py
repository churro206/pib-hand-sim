import numpy as np

# ── Roboter ───────────────────────────────────────────────────────────────────
ROBOT_PRIM_PATH = "/World/pib_upperbody_URDF/pib_upperbody_URDF"

# ── Vorzeichen-Kompensation ───────────────────────────────────────────────────
# Onshape-Import invertiert Gelenkachsen gegenüber Isaac Sim.
# Alle Winkel werden vor dem Isaac-API-Call mit JOINT_SIGN multipliziert.
JOINT_SIGN = -1  # positive Isaac-Richtung = Extension; negativ = Flexion

# ── DOF-Daten beider Hände (aus inventory_output.txt, 2026-06-18) ─────────────
# Anatomisch sortiert: Daumen-Rotator → Daumen MCP → IP →
#   Zeigefinger MCP → PIP → DIP → Mittelfinger ... → Kleiner Finger
#
# Struktur pro Seite:
#   names   — DOF-Namen in anatomischer Reihenfolge (15 Einträge)
#   indices — zugehörige Artikulations-DOF-Indizes (aus inventory DOF API)
#   servos  — 6 Servo-Gruppen: {servo_name: [usd_index, ...]}
#
# Servo-Gruppen:
#   thumb_opp  — Daumen CMC (Opposition/Abduktion), 1 Gelenk
#   thumb      — Daumen MCP + IP, 2 Gelenke
#   index/middle/ring/pinky — MCP + PIP + DIP, je 3 Gelenke

HAND_DOFS = {
    "left": {
        "names": [
            "dof_thumb_left_rotator",    # 0  — Daumen CMC
            "dof_thumb_left_proximal",   # 1  — Daumen MCP
            "dof_thumb_left_distal",     # 2  — Daumen IP
            "dof_index_left_proximal",   # 3  — Zeigefinger MCP
            "dof_index_left_distal",     # 4  — Zeigefinger PIP
            "dof_index_left_tip",        # 5  — Zeigefinger DIP
            "dof_middle_left_proximal",  # 6  — Mittelfinger MCP
            "dof_middle_left_distal",    # 7  — Mittelfinger PIP
            "dof_middle_left_tip",       # 8  — Mittelfinger DIP
            "dof_ring_left_proximal",    # 9  — Ringfinger MCP
            "dof_ring_left_distal",      # 10 — Ringfinger PIP
            "dof_ring_left_tip",         # 11 — Ringfinger DIP
            "dof_pinky_left_proximal",   # 12 — Kleiner Finger MCP
            "dof_pinky_left_distal",     # 13 — Kleiner Finger PIP
            "dof_pinky_left_tip",        # 14 — Kleiner Finger DIP
        ],
        "indices": [
            18,  # dof_thumb_left_rotator
            28,  # dof_thumb_left_proximal
            38,  # dof_thumb_left_distal
            14,  # dof_index_left_proximal
            24,  # dof_index_left_distal
            34,  # dof_index_left_tip
            15,  # dof_middle_left_proximal
            25,  # dof_middle_left_distal
            35,  # dof_middle_left_tip
            16,  # dof_ring_left_proximal
            26,  # dof_ring_left_distal
            36,  # dof_ring_left_tip
            17,  # dof_pinky_left_proximal
            27,  # dof_pinky_left_distal
            37,  # dof_pinky_left_tip
        ],
        "servos": {
            "thumb_opp": [18],
            "thumb":     [28, 38],
            "index":     [14, 24, 34],
            "middle":    [15, 25, 35],
            "ring":      [16, 26, 36],
            "pinky":     [17, 27, 37],
        },
    },
    "right": {
        "names": [
            "dof_thumb_right_rotator",    # 0  — Daumen CMC
            "dof_thumb_right_proximal",   # 1  — Daumen MCP
            "dof_thumb_right_distal",     # 2  — Daumen IP
            "dof_index_right_proximal",   # 3  — Zeigefinger MCP
            "dof_index_right_distal",     # 4  — Zeigefinger PIP
            "dof_index_right_tip",        # 5  — Zeigefinger DIP
            "dof_middle_right_proximal",  # 6  — Mittelfinger MCP
            "dof_middle_right_distal",    # 7  — Mittelfinger PIP
            "dof_middle_right_tip",       # 8  — Mittelfinger DIP
            "dof_ring_right_proximal",    # 9  — Ringfinger MCP
            "dof_ring_right_distal",      # 10 — Ringfinger PIP
            "dof_ring_right_tip",         # 11 — Ringfinger DIP
            "dof_pinky_right_proximal",   # 12 — Kleiner Finger MCP
            "dof_pinky_right_distal",     # 13 — Kleiner Finger PIP
            "dof_pinky_right_tip",        # 14 — Kleiner Finger DIP
        ],
        "indices": [
            23,  # dof_thumb_right_rotator
            33,  # dof_thumb_right_proximal
            43,  # dof_thumb_right_distal
            19,  # dof_index_right_proximal
            29,  # dof_index_right_distal
            39,  # dof_index_right_tip
            20,  # dof_middle_right_proximal
            30,  # dof_middle_right_distal
            40,  # dof_middle_right_tip
            21,  # dof_ring_right_proximal
            31,  # dof_ring_right_distal
            41,  # dof_ring_right_tip
            22,  # dof_pinky_right_proximal
            32,  # dof_pinky_right_distal
            42,  # dof_pinky_right_tip
        ],
        "servos": {
            "thumb_opp": [23],
            "thumb":     [33, 43],
            "index":     [19, 29, 39],
            "middle":    [20, 30, 40],
            "ring":      [21, 31, 41],
            "pinky":     [22, 32, 42],
        },
    },
}

# ── Greifposen als Servo-Werte (0–90°) ───────────────────────────────────────
# Seitenneutral — servo_pose_to_joints() rechnet auf 15 DOF-Winkel um.
# Alle Werte sind Richtwerte; beim Test mit test_hand_poses.py anpassen.
GRASP_POSES = {
    "open": {
        "thumb_opp": 0,
        "thumb":     0,
        "index":     0,
        "middle":    0,
        "ring":      0,
        "pinky":     0,
    },
    "closed_fist": {
        "thumb_opp": 30,
        "thumb":     80,
        "index":     85,
        "middle":    85,
        "ring":      85,
        "pinky":     85,
    },
    "pinch": {
        "thumb_opp": 60,
        "thumb":     70,
        "index":     70,
        "middle":    0,
        "ring":      0,
        "pinky":     0,
    },
    "cylindrical": {
        "thumb_opp": 15,
        "thumb":     60,
        "index":     70,
        "middle":    70,
        "ring":      70,
        "pinky":     70,
    },
    "lateral": {
        "thumb_opp": 30,
        "thumb":     50,
        "index":     10,
        "middle":    30,
        "ring":      40,
        "pinky":     50,
    },
}

# ── Lineare Approximations-Faktoren pro Gelenk-Typ ───────────────────────────
# Sehnen-Mechanismus: distal/tip folgen dem proximalen Gelenk.
# thumb_opp und thumb_prox sind 1:1, kein Tip-Gelenk am Daumen.
_SERVO_FACTORS = {
    "thumb_opp": [1.0],           # 1 Gelenk: CMC
    "thumb":     [1.0, 0.8],      # 2 Gelenke: MCP, IP
    "index":     [1.0, 0.8, 0.6], # 3 Gelenke: MCP, PIP, DIP
    "middle":    [1.0, 0.8, 0.6],
    "ring":      [1.0, 0.8, 0.6],
    "pinky":     [1.0, 0.8, 0.6],
}


def servo_pose_to_joints(servo_pose: dict, side: str) -> dict:
    """
    Rechnet ein Servo-Dictionary in ein vollständiges 15-DOF-Dictionary um.

    Lineare Näherung: proximal = servo_wert * 1.0,
                      distal   = servo_wert * 0.8,
                      tip      = servo_wert * 0.6.

    Parameters
    ----------
    servo_pose : {servo_name: winkel_deg}  — fehlende Servos werden als 0° angenommen
    side       : "left" oder "right"

    Returns
    -------
    {dof_name: winkel_deg}  — 15 Einträge, alle in Grad
    """
    hand = HAND_DOFS[side]
    dof_names  = hand["names"]
    servos     = hand["servos"]

    result = {name: 0.0 for name in dof_names}

    for servo_name, factors in _SERVO_FACTORS.items():
        usd_indices = servos[servo_name]
        servo_val   = float(servo_pose.get(servo_name, 0.0))

        for usd_idx, factor in zip(usd_indices, factors):
            # DOF-Name über den USD-Index ermitteln
            art_idx = hand["indices"].index(usd_idx)
            result[dof_names[art_idx]] = np.clip(servo_val * factor, 0.0, 90.0)

    return result


# ── Normierung ────────────────────────────────────────────────────────────────
# 0.0 = offen (0°), 1.0 = geschlossen (90°)

def normalize_pos(pos_deg: np.ndarray) -> np.ndarray:
    return np.clip(pos_deg / 90.0, 0.0, 1.0)

def denormalize_pos(pos_norm: np.ndarray) -> np.ndarray:
    return np.clip(pos_norm * 90.0, 0.0, 90.0)

# ── Physik-Parameterbereiche (für synthetische Datengenerierung) ──────────────
PHYSICS_RANGES = {
    "stiffness": (50.0, 200.0),
    "damping":   (5.0,  30.0),
}
