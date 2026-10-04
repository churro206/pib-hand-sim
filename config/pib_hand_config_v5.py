"""
config/pib_hand_config_v5.py — v5-Pendant zu pib_hand_config_v4.py.

Alle Werte direkt aus pib_upperbody_urdf_v5/robot.urdf verifiziert (nicht aus der
v4-Config übernommen/geraten) — Anlass: isaac_sim/setup_stage.py:_BODY_LIMITS wurde
bisher für v4 UND v5 gemeinsam verwendet, obwohl zwei Körper-Gelenke bei v5 andere
Grenzen haben als bei v4 (siehe "Körper-DOFs" unten). Diese Datei ist der Nachweis,
dass die Werte gegen die v5-Quelle geprüft sind — die eigentliche Durchsetzung bleibt
in isaac_sim/setup_stage.py:_BODY_LIMITS (dort mit den v4-Werten zusammengeführt,
keine Namenskollision: v4-DOF-Namen haben "dof_"-Präfix, v5 nicht).

v5-Namensschema: KEIN "dof_"-Präfix (anders als v4), Daumen-Mittelgelenk heißt "tip"
(nicht "distal" wie bei den anderen Fingern) -- siehe docs/conventions.md.
"""

# ── Roboter ───────────────────────────────────────────────────────────────────
# Articulation Root sitzt bei v5 auf root_joint (PhysicsFixedJoint), NICHT auf einem
# Wrapper-Xform wie bei v4 -- anderes, aber gültiges Importer-Muster (onshape-to-robot
# + URDF-Import statt direktem Onshape-Importer wie bei v4, siehe docs/current-sprint.md
# "v5-Hand-Integration"). Wert aus den Action-Graph-targetPrim-Relationships dieser
# Session übernommen (isaac_sim/tools/build_finger_coupling_graph.py,
# build_coupling_reflection_graph.py, isaac_sim/tools/_action_graph_inventory.txt),
# dort gegen die laufende Stage verifiziert -- hier nicht erneut geraten.
ROBOT_PRIM_PATH = "/World/pib_upperbody_urdf_v5/root_joint"

# ── Körper-DOFs (Kopf, Schultern, Arme, Handgelenke) ─────────────────────────
# Limits aus pib_upperbody_urdf_v5/robot.urdf (diese Session extrahiert und gegen
# ros2_ws/src/pib_description_v5/urdf/pib_upperbody_v5.urdf gegengeprüft, identisch).
#
# Abweichungen zu v4 (config/pib_hand_config_v4.py), NICHT einfach übernehmen:
#   - upper_arm_left: v5 ist symmetrisch [-90, 90] (v4 war [0, 90] -- siehe Kommentar
#     zu dof_upper_arm_left in setup_stage.py, dort explizit für v4 verifiziert, galt
#     nie für v5)
#   - wrist_left/wrist_right: v5 ist [-60, 0] (v4 ist [0, 90]) -- beide Seiten
#     gleichermaßen betroffen. Bis 2026-10-04 [-90, 30]; korrigiert in Onshape und
#     den URDFs, weil das Pleuel nur 60° Schwenk zulässt (WRIST_LINKAGE unten).
#     Vorzeichen-Ausnahme: -60 = voll nach innen gebeugt, 0 = gestreckt
#   - shoulder_horizontal_right: [0, 90] bei BEIDEN Versionen (v4 UND v5) -- das ist
#     KEIN Bug, sondern eine reale, in zwei unabhängigen Quellen (v4- und v5-URDF)
#     übereinstimmend verifizierte Asymmetrie gegenüber shoulder_horizontal_left
#     ([-90, 90]). Nicht auf Symmetrie "korrigieren".
BODY_DOFS = {
    "names": [
        # Kopf
        "head_horizontal",           # [-90, 90]
        "head_vertical",             # [-45, 70]
        # Linke Seite
        "shoulder_vertical_left",    # [-90, 90]
        "shoulder_horizontal_left",  # [-90, 90]
        "upper_arm_left",            # [-90, 90]
        "elbow_left",                # [-45, 90]
        "forearm_left",              # [-90, 90]
        "wrist_left",                # [-60, 0]  -- -60 = gebeugt (Ausnahme)
        # Rechte Seite
        "shoulder_vertical_right",   # [-90, 90]
        "shoulder_horizontal_right", # [  0, 90]  -- Asymmetrie verifiziert, kein Bug
        "upper_arm_right",           # [-90, 90]
        "elbow_right",               # [-45, 90]
        "forearm_right",             # [-90, 90]
        "wrist_right",               # [-60, 0]  -- -60 = gebeugt (Ausnahme)
    ],
    # TODO(param): Artikulations-DOF-Indizes (wie BODY_DOFS["indices"] in
    # pib_hand_config_v4.py) nicht übernommen -- die v4-Werte stammen aus einem
    # Isaac-Inventory-Dump (inventory_output.txt) gegen die v4-Artikulation, für v5
    # nicht verifiziert und hier bewusst nicht geraten. isaac_sim/setup_stage.py
    # braucht sie aktuell nicht (arbeitet über Namens-Traversierung, kein Index-
    # Zugriff). Falls künftig gebraucht (z.B. servo_pose_to_joints()-Äquivalent für
    # v5): gegen die laufende v5-Artikulation per IsaacArticulationState o.ä. dumpen,
    # nicht aus v4 übernehmen (andere Joint-Reihenfolge wahrscheinlich).
}

# ── Hand-/Fingergelenke ───────────────────────────────────────────────────────
# Alle 30 Hand-DOFs (Daumen: rotator+proximal+tip, Finger: proximal+distal+tip,
# je 5 Finger/Daumen-Gruppen x 2 Seiten) sind einheitlich [0, 90] -- verifiziert gegen
# die v5-URDF, identisch zu v4. Deckt sich mit der bestehenden, versions-generischen
# _HAND_KEYWORDS-Regel in isaac_sim/setup_stage.py:set_joint_limits() (Namens-
# Substring "proximal"/"distal"/"tip"/"rotator" -> [0, 90]) -- dafür ist keine eigene
# Tabelle nötig, nur hier zur Dokumentation festgehalten.
#
# HAND_DOFS (Namen, USD-Indizes, Servo-Gruppierung analog zu pib_hand_config_v4.py)
# NICHT übernommen -- aus demselben Grund wie die Körper-DOF-Indizes oben: v5 hat eine
# andere Artikulationsstruktur (44 statt 28 Gelenke insgesamt, anderes Importmuster),
# die Indizes/Servo-Gruppen aus v4 1:1 zu kopieren wäre geraten, nicht verifiziert.


# ── Servo-Aktuatormodell (ADR-012) ────────────────────────────────────────────
# Einzige Quelle für Isaac Sim (isaac_sim/setup_stage.py, Einheiten am Prim: Nm/°) und
# Isaac Lab (ArticulationCfg/ImplicitActuatorCfg, Einheiten: Nm/rad) -- servo_actuator()
# liefert beide. Rezept nach NVIDIA Articulation Stability Guide / Tuning-Reihe
# (Robotiq-Beispiel):
#   max_force         = Stall-Torque (Datenblatt, 12 V)
#   max_velocity      = Leerlaufdrehzahl (Datenblatt, 12 V)
#   stiffness         = max_force / SERVO_SATURATION_ERROR_DEG  (Sättigung bei 5° Fehler)
#   damping           = kritisch (ζ = 1) mit I = I_nominal + Armature
# Ergebnis prüfen mit isaac_sim/tools/audit_asset.py (ω_n·Δt, ζ).
_KGCM_TO_NM = 0.0980665
_RAD_PER_DEG = 0.017453292519943295

SERVOS = {
    # ST3215 (12 V): 30 kg·cm Stall, 0.222 s/60° Leerlauf (45 RPM)
    "ST3215": {"stall_nm": 30.0 * _KGCM_TO_NM, "no_load_deg_s": 60.0 / 0.222},
    # ST3095-C002 (12 V): 95 kg·cm Stall, 31 RPM Leerlauf
    "ST3095": {"stall_nm": 95.0 * _KGCM_TO_NM, "no_load_deg_s": 31.0 * 6.0},
}
SERVO_SATURATION_ERROR_DEG = 5.0
# ANNAHME, nicht gemessen: reflektierte Rotorträgheit (Rotor × Übersetzung²) — steht in
# keinem der Datenblätter. 5e-3 kg·m² = Startwert aus NVIDIAs Robotiq-Beispiel.
SERVO_ARMATURE_KGM2 = 5.0e-3

# Gelenkgruppen: (Schlüsselwort im Gelenknamen, Servo, I_nominal [kg·m²]).
# I_nominal = Diagonale der Massenmatrix in der T-Pose (audit_asset.py, 2026-10-03) — nur
# für die Dämpfung; posenabhängig, für Arm-Gelenke dominiert sie die Armature.
# Reihenfolge = Prüfreihenfolge (erstes passendes Schlüsselwort gewinnt).
V5_ACTUATORS = [
    ("shoulder_vertical",   "ST3095", 0.0249),
    ("shoulder_horizontal", "ST3095", 0.116),
    ("upper_arm",           "ST3215", 0.024),
    ("elbow",               "ST3215", 0.0426),
    ("head_horizontal",     "ST3215", 0.00591),
    ("head_vertical",       "ST3215", 0.00534),
    ("forearm",             "ST3215", 0.00128),
    ("wrist",               "ST3215", 0.00281),
    ("rotator",             "ST3215", 1.58e-4),     # Daumen-CMC
    ("proximal",            "ST3215", 6.6e-5),      # MCP Finger (Daumen 7.1e-5)
]

# Passive Mimic-Folgegelenke (PIP/DIP/IP, kein Servo): kleine Armature gegen das extreme
# Trägheitsverhältnis zum MCP (Fingerspitze M_ii ≈ 1e-6 vs. MCP 5e-3, NVIDIA: große
# Trägheitsverhältnisse vermeiden) und Geschwindigkeitsgrenze (reale Kopplung bis 1.67×
# MCP-Geschwindigkeit ≈ 450 °/s). ANNAHMEN, nicht gemessen. Welche Gelenke Folgegelenke
# sind, steht in isaac_sim/setup_stage.py → MIMIC_JOINTS (ADR-011).
FOLLOWER_ARMATURE_KGM2 = 5.0e-4
FOLLOWER_MAX_VELOCITY_DEG_S = 500.0


# ── Handgelenk-Pleuel (2026-10-04) ────────────────────────────────────────────
# Der Handgelenk-Servo (ST3215) treibt das Handgelenk über ein Pleuel an (Viergelenk:
# Kurbel am Servo → Pleuel → Hebel an der Handfläche). Maße aus Onshape bei 0°
# (Leon). Kurbel umlauffähig (Grashof), Hebel schwenkt zwischen den Totlagen genau 60°
# bei 180° Kurbelwinkel → Handgelenk [-60°, 0°]. Übersetzung in der Mitte ≈ 2:1,
# an den Totlagen gegen ∞ (Moment ↑, Geschwindigkeit ↓).
# ANNAHME: 0° (gestreckt) liegt an der Totlage "Kurbel und Pleuel gestreckt", -60° an
# der gefalteten. Die Übersetzung ist fast symmetrisch (5 % vom Rand: 0,228 bzw. 0,241),
# eine Vertauschung ändert die Tabelle kaum.
WRIST_LINKAGE = {"crank_mm": 6.0, "rod_mm": 115.0, "lever_mm": 12.0, "frame_mm": 115.43}
WRIST_RANGE_DEG = (-60.0, 0.0)
WRIST_TORQUE_CAP_NM = 12.0      # Kappung nahe den Totlagen (Leon, 2026-10-04)


def _wrist_rocker_limits():
    """Hebelwinkel β [rad] am Handgelenk in den beiden Totlagen (gestreckt, gefaltet)."""
    import math
    a, b, c, d = (WRIST_LINKAGE[k] for k in ("crank_mm", "rod_mm", "lever_mm", "frame_mm"))
    beta = lambda r: math.acos((d * d + c * c - r * r) / (2 * d * c))  # noqa: E731
    return beta(b + a), beta(b - a)


def wrist_transmission(theta_deg: float) -> float:
    """
    Übersetzung des Handgelenk-Pleuels n = dφ_servo / dθ_handgelenk (≥ 1, "in/out")
    bei Handgelenkwinkel theta_deg ∈ [-60, 0]. Analytisch aus der Geschwindigkeit der
    beiden Gelenkzapfen entlang des starren Pleuels (wie tendondrive/ für die Finger).
    """
    import math
    a, b, c, d = (WRIST_LINKAGE[k] for k in ("crank_mm", "rod_mm", "lever_mm", "frame_mm"))
    beta_ext, beta_fold = _wrist_rocker_limits()
    frac = min(max(-theta_deg / (WRIST_RANGE_DEG[1] - WRIST_RANGE_DEG[0]), 0.0), 1.0)
    beta = beta_ext + frac * (beta_fold - beta_ext)
    # Servoachse (0,0), Handgelenkachse (d,0); Hebelzapfen B, Kurbelzapfen A mit |A|=a, |A-B|=b
    bx, by = d - c * math.cos(beta), c * math.sin(beta)
    r = math.hypot(bx, by)
    gamma = math.acos(max(-1.0, min(1.0, (a * a + r * r - b * b) / (2 * a * r))))
    phi = math.atan2(by, bx) - gamma                      # ein Montagezweig, über den Bereich stetig
    ax, ay = a * math.cos(phi), a * math.sin(phi)
    ux, uy = bx - ax, by - ay                             # Pleuelrichtung
    t_a = (-math.sin(phi), math.cos(phi))                 # Tangente Kurbelzapfen
    t_b = (-math.sin(beta), -math.cos(beta))              # Tangente Hebelzapfen (dB/dβ / c)
    out_per_in = (a * (t_a[0] * ux + t_a[1] * uy)) / (c * (t_b[0] * ux + t_b[1] * uy))
    return 1.0 / max(abs(out_per_in), 1e-6)


def wrist_lookup_table(points: int = 25) -> list:
    """
    Tabelle für Isaac Labs RemotizedPDActuatorCfg.joint_parameter_lookup (NVIDIA-Muster
    für gestängegetriebene Gelenke, Spot-Knie): [Gelenkwinkel rad, Übersetzung in/out,
    Ausgangsmoment Nm], Moment = Stall-Moment × Übersetzung, gekappt bei WRIST_TORQUE_CAP_NM
    (Übersetzung entsprechend mitgekappt; Isaac Lab nutzt für die Begrenzung nur das Moment).
    """
    lo, hi = WRIST_RANGE_DEG
    stall = SERVOS["ST3215"]["stall_nm"]
    n_cap = WRIST_TORQUE_CAP_NM / stall
    table = []
    for i in range(points):
        theta = lo + (hi - lo) * i / (points - 1)
        n = min(wrist_transmission(theta), n_cap)
        table.append([theta * _RAD_PER_DEG, n, stall * n])
    return table


# Konstante Übersetzung für PhysX-Antriebe (Isaac Sim kann kein winkelabhängiges
# Moment): Mitte des Bereichs.
WRIST_TRANSMISSION_NOMINAL = wrist_transmission(sum(WRIST_RANGE_DEG) / 2)

# Übersetzung zwischen Servo und Gelenk je Gelenkgruppe (Schlüsselwort → n = dφ/dθ).
# Moment × n, Geschwindigkeit ÷ n, Armature (Rotorträgheit auf Servoseite) × n².
TRANSMISSIONS = {"wrist": WRIST_TRANSMISSION_NOMINAL}


def servo_actuator(name: str):
    """
    Parameter eines servo-getriebenen v5-Gelenks, sonst None. Beide Einheitensysteme:
      *_deg: USD-Prim (stiffness Nm/°, damping Nm·s/°, max_velocity °/s)
      *_rad: Isaac Lab / ROS (stiffness Nm/rad, damping Nm·s/rad, max_velocity rad/s)
    max_force [Nm] und armature [kg·m²] sind einheitengleich. Gelenke hinter einem
    Gestänge (TRANSMISSIONS) bekommen die auf das Gelenk umgerechneten Servowerte.
    """
    n = name.lower()
    for key, servo, inertia in V5_ACTUATORS:
        if key in n:
            spec = SERVOS[servo]
            ratio = next((r for k, r in TRANSMISSIONS.items() if k in n), 1.0)
            max_force = spec["stall_nm"] * ratio
            max_velocity_deg = spec["no_load_deg_s"] / ratio
            armature = SERVO_ARMATURE_KGM2 * ratio ** 2
            k_deg = max_force / SERVO_SATURATION_ERROR_DEG
            k_rad = k_deg / _RAD_PER_DEG
            d_rad = 2.0 * (k_rad * (inertia + armature)) ** 0.5    # ζ = 1
            return {
                "servo": servo,
                "transmission": ratio,
                "max_force": max_force,
                "armature": armature,
                "stiffness_deg": k_deg,
                "damping_deg": d_rad * _RAD_PER_DEG,
                "max_velocity_deg": max_velocity_deg,
                "stiffness_rad": k_rad,
                "damping_rad": d_rad,
                "max_velocity_rad": max_velocity_deg * _RAD_PER_DEG,
            }
    return None


# ── Reale linke Hand (Prototyp, STM32 Nucleo) ─────────────────────────────────
# Die 8 Servo-Gelenke = Aktionsraum der RL-Policy (feature/rl-grasping). Namen aus
# pib_upperbody_urdf_v5/robot.urdf. Alle übrigen Gelenke der linken Hand
# (*_distal, *_tip) sind passive Mimic-Folgegelenke (ADR-011).
LEFT_HAND_SERVO_JOINTS = [
    "forearm_left",          # Unterarmdrehung
    "wrist_left",
    "thumb_left_rotator",
    "thumb_left_proximal",
    "index_left_proximal",
    "middle_left_proximal",
    "ring_left_proximal",
    "pinky_left_proximal",
]
