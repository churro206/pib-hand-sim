"""
isaac_sim/robot_io.py — Isaac-IO-Schicht für alle pib-Gelenke (Isaac Sim 5.1).

Einzige Schicht die direkt mit der Isaac Articulation-API spricht.
Kapselt: JOINT_SIGN, Grad→Radiant-Konvertierung, Drive-Targets.

Aufgerufen von Steuer-Skripten (control/) und Test-Skripten.
Wird von _launch_helper.py via _set_robot() initialisiert.
"""
import math
import numpy as np
from pathlib import Path
import importlib.util

# ── Config (immer aus Repo, relativ zu __file__) ──────────────────────────────
# invalidate_caches() + pop: Isaac Sims Python validiert .pyc-Zeitstempel nicht
# zuverlässig → stale Bytecode würde neu hinzugefügte Attribute (z.B. BODY_DOFS)
# verbergen. Beide Zeilen erzwingen einen frischen Reload aus dem Quellcode.
importlib.invalidate_caches()
import sys as _sys
_sys.modules.pop("pib_hand_config", None)
_cfg_path = Path(__file__).parent.parent / "config" / "pib_hand_config.py"
_spec = importlib.util.spec_from_file_location("pib_hand_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

JOINT_SIGN      = _cfg.JOINT_SIGN
HAND_DOFS       = _cfg.HAND_DOFS
BODY_DOFS       = _cfg.BODY_DOFS
ROBOT_PRIM_PATH = _cfg.ROBOT_PRIM_PATH

# ── Robot-Handle (injiziert von _launch_helper.py) ────────────────────────────
_robot = None


def _set_robot(robot) -> None:
    """Wird von _launch_helper nach Initialisierung aufgerufen."""
    global _robot
    _robot = robot


def _get_robot():
    if _robot is None:
        raise RuntimeError(
            "[robot_io] Robot nicht initialisiert. "
            "_launch_helper.py muss zuerst laufen."
        )
    return _robot


# ── Interner Target-Cache (letzte gesetzte Drive-Targets) ────────────────────
_targets: dict = {"left": None, "right": None}


def _current_targets(side: str) -> np.ndarray:
    """Gibt aktuellen Target-Vektor zurück; initialisiert mit 0 (offen) wenn leer."""
    if _targets[side] is None:
        _targets[side] = np.zeros(len(HAND_DOFS[side]["indices"]), dtype=np.float32)
    return _targets[side].copy()


# ── Konvertierung — EINZIGE Stelle mit JOINT_SIGN ────────────────────────────

def _to_isaac_rad(angle_deg: float) -> float:
    """Nutzerwinkel [0°,90°] → Isaac-Radiant. Einzige Stelle mit JOINT_SIGN."""
    return JOINT_SIGN * float(np.clip(angle_deg, 0.0, 90.0)) * math.pi / 180.0


def _from_isaac_rad(rad: float) -> float:
    """Isaac-Radiant → Nutzerwinkel in Grad (Inverse von _to_isaac_rad)."""
    return JOINT_SIGN * float(rad) * 180.0 / math.pi


# ── Interne Anwendung ─────────────────────────────────────────────────────────

def _apply_targets(targets: np.ndarray, indices: np.ndarray, side: str) -> None:
    """Sendet Target-Array an Isaac-API; Fallback auf USD DriveAPI wenn nötig."""
    robot = _get_robot()

    # Primär: Articulation API (set_joint_position_targets, Einheit: Radiant)
    try:
        robot.set_joint_position_targets(positions=targets, joint_indices=indices)
        return
    except (AttributeError, TypeError):
        pass

    # Fallback: USD DriveAPI (targetPosition in Grad)
    try:
        import omni.usd       # type: ignore
        from pxr import UsdPhysics  # type: ignore
        stage = omni.usd.get_context().get_stage()
        for i, name in enumerate(HAND_DOFS[side]["names"]):
            prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
            if not prim.IsValid():
                continue
            drive = UsdPhysics.DriveAPI.Get(prim, "angular")
            if drive:
                # targets[i] ist in Radiant; DriveAPI erwartet Grad
                drive.GetTargetPositionAttr().Set(math.degrees(float(targets[i])))
    except Exception as e:
        print(f"[robot_io] DriveAPI-Fallback fehlgeschlagen: {e}")


# ── Öffentliche API ───────────────────────────────────────────────────────────

def set_hand_targets(joint_angles_deg: dict, side: str = "left") -> None:
    """
    Setzt Drive-Targets für die Hand-Gelenke einer Seite.

    joint_angles_deg : {dof_name: angle_deg}. Fehlende Gelenke bleiben unverändert.
    side             : "left" oder "right"

    Konvention: positive Winkel = Beugung (Flexion). JOINT_SIGN wird intern
    angewendet — der Aufrufer arbeitet immer mit der intuitiven Konvention.
    """
    hand    = HAND_DOFS[side]
    indices = np.array(hand["indices"], dtype=np.int32)
    targets = _current_targets(side)

    for name, angle_deg in joint_angles_deg.items():
        if name not in hand["names"]:
            print(f"[robot_io] Unbekannter DOF: {name!r} (side={side!r}) — übersprungen")
            continue
        i = hand["names"].index(name)
        targets[i] = _to_isaac_rad(angle_deg)

    _targets[side] = targets
    _apply_targets(targets, indices, side)


def get_hand_state(side: str = "left") -> dict:
    """
    Liest aktuelle Ist-Positionen der Hand-Gelenke.
    Returns: {dof_name: angle_deg}  (positive = gebeugt)
    """
    robot   = _get_robot()
    hand    = HAND_DOFS[side]
    indices = np.array(hand["indices"], dtype=np.int32)
    pos_rad = robot.get_joint_positions(joint_indices=indices)
    return {name: _from_isaac_rad(pos_rad[i]) for i, name in enumerate(hand["names"])}


def hold_current_pose(side: str = "left") -> None:
    """
    Liest aktuelle Position und setzt sie als Drive-Target (aktive Haltung).
    Verhindert dass Gravitation die Hand aus der Position drückt.
    """
    robot   = _get_robot()
    hand    = HAND_DOFS[side]
    indices = np.array(hand["indices"], dtype=np.int32)
    pos_rad = robot.get_joint_positions(joint_indices=indices).astype(np.float32)

    _targets[side] = pos_rad.copy()
    _apply_targets(pos_rad, indices, side)
    print(f"[robot_io] hold_current_pose: {side}")


def print_hand_state(side: str = "left") -> None:
    """Gibt aktuellen Gelenkzustand leserlich aus."""
    state = get_hand_state(side)
    print(f"\n── Hand {side.upper()} ──────────────────────────────────────────")
    for name, deg in state.items():
        bar = "█" * int(abs(deg) / 4.5)
        print(f"  {name:<32s} {deg:6.1f}°  {bar}")
    print()


# ── Körpergelenke (Kopf, Schultern, Arme, Handgelenke) ───────────────────────

def set_body_targets(joint_angles_deg: dict) -> None:
    """
    Setzt Drive-Targets für Körpergelenke via USD DriveAPI.

    JOINT_SIGN wird angewendet — gleiche Invertierung wie Handgelenke.
    Kein Clip: Körpergelenke haben verschiedene asymmetrische Limits.
    Nur explizit übergebene Gelenke werden verändert.
    """
    known = set(BODY_DOFS["names"])
    try:
        import omni.usd            # type: ignore
        from pxr import UsdPhysics # type: ignore
        stage = omni.usd.get_context().get_stage()
        for name, angle_deg in joint_angles_deg.items():
            if name not in known:
                print(f"[robot_io] Unbekannter Body-DOF: {name!r} — übersprungen")
                continue
            prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
            if not prim.IsValid():
                print(f"[robot_io] Body-DOF Prim nicht gefunden: {name!r}")
                continue
            drive = UsdPhysics.DriveAPI.Get(prim, "angular")
            if drive:
                drive.GetTargetPositionAttr().Set(JOINT_SIGN * float(angle_deg))
    except Exception as e:
        print(f"[robot_io] set_body_targets fehlgeschlagen: {e}")


def get_body_state() -> dict:
    """
    Liest aktuelle Ist-Positionen der Körpergelenke.
    Returns: {dof_name: angle_deg}  (positive = Onshape-Konvention)
    """
    robot   = _get_robot()
    indices = np.array(BODY_DOFS["indices"], dtype=np.int32)
    pos_rad = robot.get_joint_positions(joint_indices=indices)
    return {name: _from_isaac_rad(pos_rad[i]) for i, name in enumerate(BODY_DOFS["names"])}


def get_all_joint_states() -> dict:
    """
    Gibt Ist-Positionen aller 44 DOFs zurück.
    Returns: {dof_name: angle_deg}  (Onshape-Konvention)
    """
    state = get_body_state()
    state.update(get_hand_state("left"))
    state.update(get_hand_state("right"))
    return state


def apply_full_pose(joint_dict: dict) -> None:
    """
    Setzt Drive-Targets aus einem Isaac-Konvention Pose-Dict (Physics Inspector).

    Konvention: Werte direkt aus dem Inspector — negativ = Flexion/Vorne/Heben.
    Intern wird negiert (Onshape = -Isaac) und dann set_all_targets aufgerufen,
    das JOINT_SIGN anwendet.

    Geeignet für pickup_keyframes.py und jeden Code der Inspector-Werte trägt.
    """
    set_all_targets({name: -val for name, val in joint_dict.items()})


def set_all_targets(joint_angles_deg: dict) -> None:
    """
    Unified Setter für alle 44 DOFs (14 Körper + 15 linke + 15 rechte Hand).
    Dispatcht nach DOF-Name an set_body_targets / set_hand_targets.
    Unbekannte Namen werden geloggt.
    """
    body_names  = set(BODY_DOFS["names"])
    left_names  = set(HAND_DOFS["left"]["names"])
    right_names = set(HAND_DOFS["right"]["names"])

    body_d, left_d, right_d = {}, {}, {}
    for name, deg in joint_angles_deg.items():
        if   name in body_names:  body_d[name]  = deg
        elif name in left_names:  left_d[name]  = deg
        elif name in right_names: right_d[name] = deg
        else: print(f"[robot_io] set_all_targets: unbekannter DOF {name!r}")

    if body_d:  set_body_targets(body_d)
    if left_d:  set_hand_targets(left_d,  "left")
    if right_d: set_hand_targets(right_d, "right")
