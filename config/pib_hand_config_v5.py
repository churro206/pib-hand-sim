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
#   - wrist_left/wrist_right: v5 ist [-90, 30] (v4 ist [0, 90]) -- beide Seiten
#     gleichermaßen betroffen, kein Links/Rechts-Unterschied, nur v4 != v5
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
        "wrist_left",                # [-90, 30]
        # Rechte Seite
        "shoulder_vertical_right",   # [-90, 90]
        "shoulder_horizontal_right", # [  0, 90]  -- Asymmetrie verifiziert, kein Bug
        "upper_arm_right",           # [-90, 90]
        "elbow_right",               # [-45, 90]
        "forearm_right",             # [-90, 90]
        "wrist_right",               # [-90, 30]
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
