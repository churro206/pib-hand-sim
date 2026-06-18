"""
Manuelle Steuerung der pib-Hand (links und rechts) in Isaac Sim 5.1.
Ausführen im Script Editor (Window → Script Editor → Run).
Simulation muss laufen (Play gedrückt).

Vorzeichen-Konvention:
  Nutzerwinkel: 0° = offen, 90° = geschlossen (positive Werte = Flexion).
  Vor jedem API-Call wird JOINT_SIGN multipliziert (Onshape-Achsen-Inversion).
  Anschließend Umrechnung Grad → Radiant.
"""
import os
import math
import asyncio
import importlib.util
import numpy as np

# __file__ zeigt im Isaac Script Editor auf /tmp/ — daher kein relatives Pfad möglich.
# Projektverzeichnis über Env-Variable oder Fallback-Suche ermitteln.
def _find_project_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    for candidate in [
        os.path.expanduser("~/repos/pib-hand-sim"),
        os.path.expanduser("~/pib-hand-sim"),
        os.path.expanduser("~/projects/pib-hand-sim"),
    ]:
        if os.path.isfile(os.path.join(candidate, "config", "pib_hand_config.py")):
            return candidate
    raise FileNotFoundError(
        "pib-hand-sim Projektverzeichnis nicht gefunden. "
        "Env-Variable PIB_HAND_SIM_ROOT=<Pfad> setzen."
    )

_cfg_path = os.path.join(_find_project_root(), "config", "pib_hand_config.py")
_spec = importlib.util.spec_from_file_location("pib_hand_config", _cfg_path)
_cfg  = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)

ROBOT_PRIM_PATH    = _cfg.ROBOT_PRIM_PATH
JOINT_SIGN         = _cfg.JOINT_SIGN
HAND_DOFS          = _cfg.HAND_DOFS
GRASP_POSES        = _cfg.GRASP_POSES
servo_pose_to_joints = _cfg.servo_pose_to_joints

# ── API-Import mit Fallback ───────────────────────────────────────────────────
# Isaac Sim 5.1: isaacsim.core.prims.SingleArticulation
# Ältere Versionen: omni.isaac.core.articulations.Articulation
try:
    from isaacsim.core.prims import SingleArticulation as _ArticulationCls  # type: ignore
    _USING_NEW_API = True
except ImportError:
    from omni.isaac.core.articulations import Articulation as _ArticulationCls  # type: ignore
    _USING_NEW_API = False

_robot: _ArticulationCls | None = None


def get_robot() -> _ArticulationCls:
    """Gibt die initialisierte Artikulation zurück (lazy singleton)."""
    global _robot
    if _robot is None:
        _robot = _ArticulationCls(prim_path=ROBOT_PRIM_PATH)
        _robot.initialize()
    return _robot


# ── Interne Konvertierung ─────────────────────────────────────────────────────

def _to_rad(angle_deg: float) -> float:
    """Nutzerwinkel → Isaac-Radiant mit JOINT_SIGN-Kompensation."""
    clamped = float(np.clip(angle_deg, 0.0, 90.0))
    return JOINT_SIGN * clamped * math.pi / 180.0


def _joint_dict_to_arrays(joint_dict: dict, side: str) -> tuple[np.ndarray, np.ndarray]:
    """
    {dof_name: angle_deg} → (positions_rad, usd_indices) nur für genannte DOFs.

    Parameters
    ----------
    joint_dict : Teilmenge der 15 DOF-Namen mit Zielwinkeln
    side       : "left" oder "right"

    Returns
    -------
    positions_rad : float32-Array der Zielwinkel in Radiant
    usd_indices   : int32-Array der zugehörigen USD-Artikulations-Indizes
    """
    hand   = HAND_DOFS[side]
    names  = hand["names"]
    indices = hand["indices"]

    positions, idx_list = [], []
    for name, angle in joint_dict.items():
        if name not in names:
            continue
        i = names.index(name)
        positions.append(_to_rad(angle))
        idx_list.append(indices[i])

    return np.array(positions, dtype=np.float32), np.array(idx_list, dtype=np.int32)


def _full_pose_arrays(joint_dict: dict, side: str, robot: _ArticulationCls) -> tuple[np.ndarray, np.ndarray]:
    """
    Gibt vollständige positions/indices-Arrays zurück.
    Nicht genannte DOFs werden aus dem aktuellen Zustand übernommen.
    """
    hand    = HAND_DOFS[side]
    usd_idx = np.array(hand["indices"], dtype=np.int32)

    current = robot.get_joint_positions(joint_indices=usd_idx).astype(np.float32)
    target  = current.copy()

    names = hand["names"]
    for name, angle in joint_dict.items():
        if name not in names:
            continue
        i = names.index(name)
        target[i] = _to_rad(angle)

    return target, usd_idx


def _smoothstep(t: float) -> float:
    """Smoothstep-Kurve: weiche Ein- und Ausblendung der Bewegung."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ── Öffentliche API ───────────────────────────────────────────────────────────

def set_joint(name: str, angle_deg: float, side: str = "left", robot: _ArticulationCls | None = None) -> None:
    """
    Setzt ein einzelnes Handgelenk sofort auf den Zielwinkel.

    Parameters
    ----------
    name      : DOF-Name (z. B. "dof_index_left_proximal")
    angle_deg : Zielwinkel in Grad [0°, 90°]
    side      : "left" oder "right"
    """
    if robot is None:
        robot = get_robot()

    hand = HAND_DOFS[side]
    if name not in hand["names"]:
        raise ValueError(f"Unbekannter DOF: {name!r} (side={side!r})\nGültig: {hand['names']}")

    i = hand["names"].index(name)
    robot.set_joint_positions(
        positions=np.array([_to_rad(angle_deg)], dtype=np.float32),
        joint_indices=np.array([hand["indices"][i]], dtype=np.int32),
    )


def set_pose(joint_dict: dict, side: str = "left", robot: _ArticulationCls | None = None) -> None:
    """
    Setzt mehrere Gelenke gleichzeitig (kinematisch, sofort).

    Parameters
    ----------
    joint_dict : {dof_name: angle_deg}  — unbekannte Schlüssel werden ignoriert
    side       : "left" oder "right"
    """
    if robot is None:
        robot = get_robot()

    positions, idx = _joint_dict_to_arrays(joint_dict, side)
    if len(positions) == 0:
        return
    robot.set_joint_positions(positions=positions, joint_indices=idx)


async def move_to_pose(
    joint_dict: dict,
    duration_s: float = 1.0,
    side: str = "left",
    robot: _ArticulationCls | None = None,
) -> None:
    """
    Smoothstep-Interpolation von der aktuellen zur Zielpose.

    Aufruf: asyncio.ensure_future(move_to_pose(...))

    Parameters
    ----------
    joint_dict : {dof_name: angle_deg}
    duration_s : Bewegungszeit in Sekunden (bei 60 Hz)
    side       : "left" oder "right"
    """
    import omni.kit.app  # type: ignore  — nur im Script-Editor verfügbar

    if robot is None:
        robot = get_robot()

    app    = omni.kit.app.get_app()
    steps  = max(1, int(duration_s * 60))

    target, usd_idx = _full_pose_arrays(joint_dict, side, robot)
    start  = robot.get_joint_positions(joint_indices=usd_idx).astype(np.float32)

    for step in range(steps + 1):
        t    = _smoothstep(step / steps)
        interp = (start + t * (target - start)).astype(np.float32)
        robot.set_joint_positions(positions=interp, joint_indices=usd_idx)
        await app.next_update_async()


def set_servo_pose(servo_dict: dict, side: str = "left", robot: _ArticulationCls | None = None) -> None:
    """
    Setzt die Hand über Servo-Werte (0–90°), sofort (kinematisch).

    Parameters
    ----------
    servo_dict : {servo_name: angle_deg}  — z. B. {"index": 70, "thumb_opp": 45}
    side       : "left" oder "right"
    """
    joint_dict = servo_pose_to_joints(servo_dict, side)
    set_pose(joint_dict, side=side, robot=robot)


async def apply_grasp(
    pose_name: str,
    side: str = "left",
    duration_s: float = 1.0,
    robot: _ArticulationCls | None = None,
) -> None:
    """
    Fährt eine benannte Greifpose aus GRASP_POSES an.

    Aufruf: asyncio.ensure_future(apply_grasp("pinch", side="right"))

    Parameters
    ----------
    pose_name  : Schlüssel aus GRASP_POSES (z. B. "closed_fist")
    side       : "left" oder "right"
    duration_s : Bewegungszeit in Sekunden
    """
    if pose_name not in GRASP_POSES:
        raise ValueError(f"Unbekannte Pose: {pose_name!r}\nGültig: {list(GRASP_POSES)}")

    servo_dict = GRASP_POSES[pose_name]
    joint_dict = servo_pose_to_joints(servo_dict, side)
    await move_to_pose(joint_dict, duration_s=duration_s, side=side, robot=robot)


# ── Drive-Steuerung (physikbasiertes Halten) ─────────────────────────────────

def setup_drives(
    side: str = "left",
    stiffness: float = 200.0,
    damping: float = 20.0,
) -> None:
    """
    Setzt Steifigkeit und Dämpfung der USD-Drives für alle Handgelenke.
    Muss einmal aufgerufen werden bevor set_drive_targets funktioniert.

    Werte für "steif aber nicht fixiert": stiffness=200, damping=20.
    Für Training/Datengenerierung niedrigere Werte (50–200) verwenden.

    Parameters
    ----------
    side      : "left" oder "right"
    stiffness : Federsteifigkeit (N·m/rad) — höher = steifer
    damping   : Dämpfung — verhindert Schwingen
    """
    import omni.usd  # type: ignore
    from pxr import UsdPhysics  # type: ignore

    stage = omni.usd.get_context().get_stage()
    for name in HAND_DOFS[side]["names"]:
        prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
        if not prim.IsValid():
            print(f"[WARN] Prim nicht gefunden: {name}")
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        drive.GetStiffnessAttr().Set(stiffness)
        drive.GetDampingAttr().Set(damping)


def set_drive_targets(joint_dict: dict, side: str = "left") -> None:
    """
    Setzt Drive-Sollwerte (physikbasiert — Gelenk hält Position gegen Kräfte).
    setup_drives() muss vorher aufgerufen worden sein.

    Parameters
    ----------
    joint_dict : {dof_name: angle_deg}
    side       : "left" oder "right"
    """
    import omni.usd  # type: ignore
    from pxr import UsdPhysics  # type: ignore

    stage = omni.usd.get_context().get_stage()
    names = HAND_DOFS[side]["names"]

    for name, angle_deg in joint_dict.items():
        if name not in names:
            continue
        prim = stage.GetPrimAtPath(f"{ROBOT_PRIM_PATH}/{name}")
        if not prim.IsValid():
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            continue
        # USD DriveAPI nimmt Grad (nicht Radiant), mit JOINT_SIGN-Kompensation
        target = JOINT_SIGN * float(np.clip(angle_deg, 0.0, 90.0))
        drive.GetTargetPositionAttr().Set(target)


# ── Debug-Ausgabe ─────────────────────────────────────────────────────────────

def print_joint_state(side: str = "left", robot: _ArticulationCls | None = None) -> None:
    """Gibt den aktuellen Gelenkzustand leserlich auf der Konsole aus."""
    if robot is None:
        robot = get_robot()

    hand    = HAND_DOFS[side]
    usd_idx = np.array(hand["indices"], dtype=np.int32)
    pos_rad = robot.get_joint_positions(joint_indices=usd_idx)

    print(f"\n── Hand {side.upper()} — aktueller Zustand ───────────────────────────")
    for i, name in enumerate(hand["names"]):
        # Nutzerwinkel zurückrechnen: Vorzeichen umkehren
        deg = JOINT_SIGN * float(pos_rad[i]) * 180.0 / math.pi
        bar = "█" * int(abs(deg) / 4.5)
        print(f"  {name:<32s} {deg:6.1f}°  {bar}")
    print()
