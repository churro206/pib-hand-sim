"""
inventory.py — pib v4 DOF Inventur für Isaac Sim 5.1

Listet alle Gelenke der Articulation auf und gibt sie in einem Format aus,
das direkt in config/pib_hand_config.py kopiert werden kann.

VORBEDINGUNGEN:
  1. pib USD-Datei ist geladen
  2. Play-Button wurde gedrückt (Simulation läuft)
  3. setup_stage.py wurde ausgeführt (PhysicsScene existiert)

AUSFÜHRUNG:
  Window → Script Editor → diese Datei laden → Run (Ctrl+Enter)

AUSGABE:
  Konsolen-Output enthält drei Blöcke:
    - Komplette DOF-Übersicht (alle Gelenke, sortiert nach USD-Index)
    - Hand-DOF-Liste (Python-Code für pib_hand_config.py)
    - Fullbody-DOF-Liste (Python-Code für manual_control_fullbody.py)
"""

import numpy as np

# Isaac Sim 5.1 API
try:
    from isaacsim.core.prims import SingleArticulation as Articulation
except ImportError:
    # Fallback für ältere Versionen
    from omni.isaac.core.articulations import Articulation


# ── Konfiguration ─────────────────────────────────────────────────────────────

ROBOT_PATH = "/World/pib_upperbody_URDF/pib_upperbody_URDF"

# Keywords zur Klassifizierung der DOFs
HAND_KEYWORDS  = ["thumb", "index", "middle", "ring", "pinky", "wrist"]
SIDE_KEYWORDS  = ["left", "right"]
ARM_KEYWORDS   = ["shoulder", "elbow", "forearm", "upper_arm"]
HEAD_KEYWORDS  = ["head", "neck", "camera"]
BODY_KEYWORDS  = ["body", "torso", "base"]


def classify_dof(name: str) -> str:
    """Klassifiziert einen DOF-Namen in eine Kategorie."""
    n = name.lower()
    if any(k in n for k in HAND_KEYWORDS):
        return "hand"
    if any(k in n for k in ARM_KEYWORDS):
        return "arm"
    if any(k in n for k in HEAD_KEYWORDS):
        return "head"
    if any(k in n for k in BODY_KEYWORDS):
        return "body"
    return "other"


def detect_side(name: str) -> str:
    """Erkennt ob ein DOF zur linken oder rechten Seite gehört."""
    n = name.lower()
    if "left" in n:
        return "left"
    if "right" in n:
        return "right"
    return "center"


def hand_dof_sort_key(name: str) -> tuple:
    """
    Sortier-Key für Hand-DOFs in anatomischer Reihenfolge:
    thumb_rotator → thumb_proximal → thumb_distal →
    index_proximal → index_distal → index_tip →
    middle ... → ring ... → pinky ...
    """
    n = name.lower()
    finger_order = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4}
    segment_order = {"rotator": 0, "opposition": 0, "proximal": 1, "distal": 2, "tip": 3}

    finger = next((f for f in finger_order if f in n), "zzz")
    segment = next((s for s in segment_order if s in n), "zzz")

    return (finger_order.get(finger, 99), segment_order.get(segment, 99), name)


# ── Hauptprogramm ─────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("pib v4 DOF-Inventur")
    print("=" * 80)

    # Articulation initialisieren
    robot = Articulation(ROBOT_PATH)
    robot.initialize()

    dof_names = robot.dof_names
    n_dofs = len(dof_names)

    # Joint-Properties holen
    props = robot.get_articulation_controller().get_dof_properties()
    lower_rad = props["lower"]
    upper_rad = props["upper"]

    # ── Block 1: Komplette Übersicht ──────────────────────────────────────────
    print(f"\n>>> Gesamtanzahl DOFs: {n_dofs}\n")
    print(f"{'Idx':>3}  {'DOF-Name':<40} {'Kategorie':<8} {'Seite':<6}  "
          f"{'Min [°]':>8}  {'Max [°]':>8}")
    print("-" * 80)

    hand_dofs_left   = []
    hand_dofs_right  = []
    fullbody_dofs    = []

    for idx, name in enumerate(dof_names):
        category = classify_dof(name)
        side = detect_side(name)
        lo_deg = np.degrees(lower_rad[idx])
        hi_deg = np.degrees(upper_rad[idx])

        print(f"{idx:>3}  {name:<40} {category:<8} {side:<6}  "
              f"{lo_deg:>8.1f}  {hi_deg:>8.1f}")

        entry = (idx, name, lo_deg, hi_deg)
        fullbody_dofs.append(entry)

        if category == "hand":
            if side == "left":
                hand_dofs_left.append(entry)
            elif side == "right":
                hand_dofs_right.append(entry)

    # Sortiere Hand-DOFs anatomisch
    hand_dofs_left.sort(key=lambda e: hand_dof_sort_key(e[1]))
    hand_dofs_right.sort(key=lambda e: hand_dof_sort_key(e[1]))

    print(f"\n>>> Hand-DOFs links:  {len(hand_dofs_left)}")
    print(f">>> Hand-DOFs rechts: {len(hand_dofs_right)}")
    print(f">>> Erwartet für v4:  15 pro Hand")

    if len(hand_dofs_left) != 15 and len(hand_dofs_right) != 15:
        print("\n⚠️  WARNUNG: Keine Seite hat 15 DOFs. v4 sollte 15 haben.")
        print("    Prüfe ob alle drei Gelenke pro Finger im URDF enthalten sind.")

    # ── Block 2: Hand-DOF-Liste für pib_hand_config.py ────────────────────────
    print("\n" + "=" * 80)
    print("Block 2: Code für config/pib_hand_config.py")
    print("=" * 80)

    # Wähle die Seite die wir verwenden — Standard ist links wie in CLAUDE.md
    active_hand = hand_dofs_left if len(hand_dofs_left) >= 15 else hand_dofs_right
    side_label = "left" if active_hand is hand_dofs_left else "right"

    print(f"""
# Auto-generiert von inventory.py — pib v4, {side_label}e Hand
# Konvention: positive Winkel = Beugung Richtung Handfläche

# Vorzeichen-Kompensation Onshape → Isaac Sim
JOINT_SIGN = -1

# DOF-Namen in anatomischer Reihenfolge
DOF_NAMES = [""")
    for idx, name, lo, hi in active_hand:
        print(f'    "{name}",  # USD-Idx {idx}, Range [{lo:.1f}°, {hi:.1f}°]')
    print("]")

    print(f"""
# USD-Indizes (für direkten Zugriff in get_joint_positions arrays)
DOF_USD_INDICES = [""")
    for idx, name, lo, hi in active_hand:
        print(f'    {idx},  # {name}')
    print("]")

    print(f"""
# Gelenkgrenzen (Min, Max) in Grad
DOF_LIMITS = [""")
    for idx, name, lo, hi in active_hand:
        print(f"    ({lo:.1f}, {hi:.1f}),  # {name}")
    print("]")

    # Servo-Zuordnung (Annahme: 1 Servo pro Finger, plus Daumen-Opposition)
    print(f"""
# Servo-zu-Gelenk Zuordnung
# Für v4: 6 Servos pro Hand (1× Opposition + 5× Fingerantriebe)
# Daumen hat 2 Gelenke (proximal, distal), Finger haben 3 (proximal, distal, tip)
SERVO_GROUPS = {{""")

    finger_groups = {"thumb_opp": [], "thumb": [], "index": [], "middle": [],
                     "ring": [], "pinky": []}
    for idx, name, lo, hi in active_hand:
        n = name.lower()
        if "rotator" in n or "opposition" in n:
            finger_groups["thumb_opp"].append((idx, name))
        elif "thumb" in n:
            finger_groups["thumb"].append((idx, name))
        elif "index" in n:
            finger_groups["index"].append((idx, name))
        elif "middle" in n:
            finger_groups["middle"].append((idx, name))
        elif "ring" in n:
            finger_groups["ring"].append((idx, name))
        elif "pinky" in n:
            finger_groups["pinky"].append((idx, name))

    for group_name, members in finger_groups.items():
        if not members:
            continue
        idx_list = [m[0] for m in members]
        print(f'    "{group_name}": {idx_list},  # ' +
              ", ".join(m[1] for m in members))
    print("}")

    # ── Block 3: Fullbody-DOF-Liste ───────────────────────────────────────────
    print("\n" + "=" * 80)
    print("Block 3: Code für manual_control_fullbody.py")
    print("=" * 80)
    print(f"""
# Alle DOFs gruppiert nach Körperteil — für Fullbody-Steuerung in Demo-Szenen

FULLBODY_DOFS = {{""")

    by_category = {"head": [], "arm": [], "hand": [], "body": [], "other": []}
    for idx, name, lo, hi in fullbody_dofs:
        cat = classify_dof(name)
        by_category[cat].append((idx, name, lo, hi))

    for cat, dofs in by_category.items():
        if not dofs:
            continue
        print(f'    "{cat}": [')
        for idx, name, lo, hi in dofs:
            print(f'        ("{name}", {idx}, {lo:.1f}, {hi:.1f}),')
        print("    ],")
    print("}")

    # ── Sanity-Check ──────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("Sanity-Checks")
    print("=" * 80)

    # Prüfe ob alle erwarteten Finger vorhanden sind
    expected_fingers = ["thumb", "index", "middle", "ring", "pinky"]
    missing = []
    for finger in expected_fingers:
        if not any(finger in d[1].lower() for d in active_hand):
            missing.append(finger)
    if missing:
        print(f"⚠️  Fehlende Finger in der {side_label}en Hand: {missing}")
    else:
        print(f"✓ Alle 5 Finger gefunden in der {side_label}en Hand")

    # Prüfe ob die Range-Werte plausibel sind
    suspicious = [(idx, name, lo, hi) for idx, name, lo, hi in active_hand
                  if abs(hi - lo) < 1.0 or abs(hi - lo) > 360.0]
    if suspicious:
        print(f"⚠️  Verdächtige Gelenkgrenzen (zu klein oder zu groß):")
        for idx, name, lo, hi in suspicious:
            print(f"   {name}: [{lo:.1f}°, {hi:.1f}°]")
    else:
        print("✓ Alle Gelenkgrenzen plausibel")

    print("\n" + "=" * 80)
    print("Inventur abgeschlossen.")
    print("Nächster Schritt: relevante Blöcke in die Konfigurationsdateien kopieren.")
    print("=" * 80)


if __name__ == "__main__":
    main()