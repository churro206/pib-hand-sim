"""
Datensammlung in Isaac Sim.
Ausfuehren im Script Editor (Window -> Script Editor -> Run).
Simulation muss laufen (Play gedrueckt).

Speichert: data/synthetic_<timestamp>.npz
  - t:          (N,)        Zeitstempel [s]
  - cmd:        (N, 11)     Sollwinkel [Grad]
  - pos:        (N, 11)     Istwinkel [Grad]
  - stiffness:  (N,)        Gelenk-Steifigkeit dieser Episode
  - damping:    (N,)        Daempfung dieser Episode
  - dof_names:  (11,)       DOF-Namen zur Referenz
"""
import asyncio
import numpy as np
from datetime import datetime
from pathlib import Path

import omni.usd  # type: ignore
import omni.kit.app  # type: ignore
from pxr import UsdPhysics  # type: ignore

# Konstanten direkt (kein sys.path-Eingriff um Isaac Sim cv2-Konflikt zu vermeiden)
ROBOT_PATH = "/World/pib_upperbody/pib_upperbody"
SAVE_DIR   = Path(__file__).parent.parent / "data"

DOF_NAMES = [
    "thumb_right_opposition",
    "thumb_right_proximal",
    "thumb_right_distal",
    "index_right_proximal",
    "index_right_distal",
    "middle_right_proximal",
    "middle_right_distal",
    "ring_right_proximal",
    "ring_right_distal",
    "pinky_right_proximal",
    "pinky_right_distal",
]
DOF_INDICES  = [19, 29, 35, 20, 30, 21, 31, 22, 32, 23, 33]
DOF_LIMITS   = np.array([[-90.0, 0.0]] * 11)  # 0° = offen, -90° = geschlossen
N_DOFS       = 11
PHYSICS_RANGES = {"stiffness": (50.0, 200.0), "damping": (5.0, 30.0)}

# --- Einstellungen ---
N_EPISODES = 20   # Episoden pro Durchlauf
HZ         = 60   # Physik-Schritte pro Sekunde (Isaac Sim default)
SAVE_DIR.mkdir(exist_ok=True)

rng = np.random.default_rng(seed=42)


def _get_joint_drives(stage):
    """Gibt {dof_name: DriveAPI} zurueck fuer alle rechten Handgelenke."""
    drives = {}
    for name in DOF_NAMES:
        prim = stage.GetPrimAtPath(f"{ROBOT_PATH}/{name}")
        if not prim.IsValid():
            print(f"[WARN] Prim nicht gefunden: {name}")
            continue
        drive = UsdPhysics.DriveAPI.Get(prim, "angular")
        if not drive:
            drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
        drives[name] = drive
    return drives


def _set_physics(drives, stiffness: float, damping: float):
    for drive in drives.values():
        drive.GetStiffnessAttr().Set(stiffness)
        drive.GetDampingAttr().Set(damping)


def _set_targets(drives, angles_deg: np.ndarray):
    """Setzt Sollwinkel in Grad (USD DriveAPI nimmt Grad)."""
    for i, (name, drive) in enumerate(drives.items()):
        drive.GetTargetPositionAttr().Set(float(angles_deg[i]))


def _get_positions(robot) -> np.ndarray:
    """Gibt Istwinkel in Grad zurueck, nur die rechten Hand-DOFs."""
    all_pos = robot.get_joint_positions()  # Radiant
    pos_rad = np.array([all_pos[i] for i in DOF_INDICES])
    return np.degrees(pos_rad)


def _trajectory_ramp(lo: float, hi: float, n_steps: int) -> np.ndarray:
    """Lineare Rampe von lo nach hi."""
    return np.linspace(lo, hi, n_steps)


def _trajectory_sweep(lo: float, hi: float, n_steps: int) -> np.ndarray:
    """Hin-und-her: lo -> hi -> lo (Hysterese sichtbar)."""
    half = n_steps // 2
    return np.concatenate([
        np.linspace(lo, hi, half),
        np.linspace(hi, lo, n_steps - half)
    ])


TRAJECTORIES = {
    "slow_close":  (lambda: _trajectory_ramp(0.0,  -90.0, int(3.0 * HZ))),
    "slow_open":   (lambda: _trajectory_ramp(-90.0,  0.0, int(3.0 * HZ))),
    "fast_close":  (lambda: _trajectory_ramp(0.0,  -90.0, int(0.5 * HZ))),
    "fast_open":   (lambda: _trajectory_ramp(-90.0,  0.0, int(0.5 * HZ))),
    "sweep":       (lambda: _trajectory_sweep(0.0, -90.0, int(4.0 * HZ))),
}


async def collect():
    from omni.isaac.core.articulations import Articulation  # type: ignore

    stage = omni.usd.get_context().get_stage()
    app   = omni.kit.app.get_app()

    # Physics View braucht mind. einen Frame um bereit zu sein
    await app.next_update_async()

    robot = Articulation(ROBOT_PATH)
    robot.initialize()

    drives = _get_joint_drives(stage)
    if len(drives) != N_DOFS:
        print(f"[FEHLER] Nur {len(drives)}/{N_DOFS} Drives gefunden. Abbruch.")
        return

    all_t, all_cmd, all_pos, all_stiff, all_damp = [], [], [], [], []

    for ep in range(N_EPISODES):
        stiffness = float(rng.uniform(*PHYSICS_RANGES["stiffness"]))
        damping   = float(rng.uniform(*PHYSICS_RANGES["damping"]))
        _set_physics(drives, stiffness, damping)

        print(f"Episode {ep+1}/{N_EPISODES}  stiffness={stiffness:.1f}  damping={damping:.1f}")

        t_offset = 0.0

        for traj_name, traj_fn in TRAJECTORIES.items():
            angles_seq = traj_fn()  # (n_steps,) — ein Winkel fuer alle Finger
            n_steps = len(angles_seq)

            for step in range(n_steps):
                target_deg = np.full(N_DOFS, angles_seq[step])
                _set_targets(drives, target_deg)

                await app.next_update_async()

                pos_deg = _get_positions(robot)
                t_now   = t_offset + step / HZ

                all_t.append(t_now)
                all_cmd.append(target_deg.copy())
                all_pos.append(pos_deg)
                all_stiff.append(stiffness)
                all_damp.append(damping)

            t_offset += n_steps / HZ

    # Speichern
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = SAVE_DIR / f"synthetic_{timestamp}.npz"
    np.savez(
        out_path,
        t         = np.array(all_t),
        cmd       = np.array(all_cmd),
        pos       = np.array(all_pos),
        stiffness = np.array(all_stiff),
        damping   = np.array(all_damp),
        dof_names = np.array(DOF_NAMES),
    )

    n_samples = len(all_t)
    print(f"\nFertig: {n_samples} Samples gespeichert -> {out_path}")
    print(f"Shape: cmd={np.array(all_cmd).shape}, pos={np.array(all_pos).shape}")


# Starten
asyncio.ensure_future(collect())
