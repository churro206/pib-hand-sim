import numpy as np

# USD Pfad des Roboters in Isaac Sim
ROBOT_PATH = "/World/pib_upperbody/pib_upperbody"

# DOF-Namen und Indizes der rechten Hand (verifiziert per inventory.py, 2026-05-15)
# Winkel in Grad: 0° = offen (T-Pose), -90° = vollständig gebeugt (Flexion)
HAND_RIGHT_DOFS = {
    "thumb_right_opposition": {"idx": 19, "min": -90.0, "max": 0.0},
    "thumb_right_proximal":   {"idx": 29, "min": -90.0, "max": 0.0},
    "thumb_right_distal":     {"idx": 35, "min": -90.0, "max": 0.0},
    "index_right_proximal":   {"idx": 20, "min": -90.0, "max": 0.0},
    "index_right_distal":     {"idx": 30, "min": -90.0, "max": 0.0},
    "middle_right_proximal":  {"idx": 21, "min": -90.0, "max": 0.0},
    "middle_right_distal":    {"idx": 31, "min": -90.0, "max": 0.0},
    "ring_right_proximal":    {"idx": 22, "min": -90.0, "max": 0.0},
    "ring_right_distal":      {"idx": 32, "min": -90.0, "max": 0.0},
    "pinky_right_proximal":   {"idx": 23, "min": -90.0, "max": 0.0},
    "pinky_right_distal":     {"idx": 33, "min": -90.0, "max": 0.0},
}

DOF_NAMES   = list(HAND_RIGHT_DOFS.keys())
DOF_INDICES = [v["idx"] for v in HAND_RIGHT_DOFS.values()]
DOF_LIMITS  = np.array([[v["min"], v["max"]] for v in HAND_RIGHT_DOFS.values()])  # (11,2) Grad
N_DOFS      = len(DOF_NAMES)  # 11

# Physics-Parameter-Bereiche für synthetische Datengenerierung
PHYSICS_RANGES = {
    "stiffness": (50.0, 200.0),
    "damping":   (5.0,  30.0),
}

# Greifposen in Grad (0 = offen, negativ = gebeugt)
GRASP_POSES = {
    "open": np.zeros(N_DOFS),
    "power_grasp": np.array([-45, -60, -50,   # Daumen
                               -70, -60,        # Zeigefinger
                               -70, -60,        # Mittelfinger
                               -70, -60,        # Ringfinger
                               -70, -60]),      # Kleiner Finger
    "pinch": np.array([-60, -70, -50,          # Daumen
                        -80, -70,               # Zeigefinger
                        -10, -10,               # Mittelfinger (leicht)
                        -10, -10,               # Ringfinger (leicht)
                        -10, -10]),             # Kleiner Finger (leicht)
}

# Normierung: 0.0 = offen (0°), 1.0 = geschlossen (-90°)
def normalize_pos(pos_deg: np.ndarray) -> np.ndarray:
    return -pos_deg / 90.0

def denormalize_pos(pos_norm: np.ndarray) -> np.ndarray:
    return -pos_norm * 90.0
