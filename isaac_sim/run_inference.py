"""
Inferenz-Skript: Trainiertes LSTM in Isaac Sim betreiben.

Modi (MODE-Konstante anpassen):
  "compare"  PhysX laeuft normal. LSTM sagt Positionen vorher und vergleicht
             mit PhysX-Output. Zeigt wie gut das Netz die Simulation gelernt hat.
  "drive"    LSTM treibt die Handgelenke direkt an, PhysX-Dynamik abgeschaltet.
             Sinnvoll sobald das Netz auf echten AS5600-Daten feinabgestimmt ist.

Voraussetzungen (Reihenfolge beachten!):
  1. Isaac Sim oeffnen, USD laden
  2. Play druecken
  3. setup_stage.py ausfuehren  ← erzeugt die PhysicsScene (ohne diese schlaegt jede Physics-API fehl)
  4. fix_joints.py ausfuehren
  5. Gewichtsdatei vorhanden: models/hand_lstm_*_weights.npz
     (erzeugt durch: .venv/bin/python inference/export_weights.py)

Ausfuehren: Window -> Script Editor -> Datei oeffnen -> Run
"""
import asyncio
import numpy as np
from pathlib import Path
from datetime import datetime

import omni.usd      # type: ignore
import omni.kit.app  # type: ignore
from pxr import UsdPhysics  # type: ignore

# ============================================================
#  EINSTELLUNGEN — hier anpassen
# ============================================================

MODE           = "compare"   # "compare" | "drive"
LOG_EVERY      = 60          # Konsolenausgabe alle N Frames (~1 s)

# Nur fuer MODE="compare": Test-Trajektorie fahren (Finger auf/zu) damit
# das LSTM etwas zu vergleichen hat. False = externe Targets abwarten.
RUN_TEST_TRAJ     = True
# Geschwindigkeit pro Zyklus [Grad/s] — Anzahl Eintraege = Anzahl Zyklen.
# Beispiel: [30, 180] -> erst langsam, dann schnell auf/zu
TRAJ_SPEEDS_DEG_S = [30.0, 180.0]

# ============================================================
#  KONFIGURATION  (rechte Hand, 11 DOF)
# ============================================================

ROBOT_PATH  = "/World/pib_upperbody/pib_upperbody"
DOF_NAMES   = [
    "thumb_right_opposition", "thumb_right_proximal",  "thumb_right_distal",
    "index_right_proximal",   "index_right_distal",
    "middle_right_proximal",  "middle_right_distal",
    "ring_right_proximal",    "ring_right_distal",
    "pinky_right_proximal",   "pinky_right_distal",
]
DOF_INDICES = [19, 29, 35, 20, 30, 21, 31, 22, 32, 23, 33]
N_DOFS      = len(DOF_NAMES)
HZ          = 60


# ============================================================
#  REPO-ROOT  (Isaac Sim kopiert Skripte nach /tmp — __file__ dort unbrauchbar)
# ============================================================

def _repo_root() -> Path:
    """Leitet Repo-Root aus dem geladenen USD-Stage ab.
    Der Stage-Pfad zeigt immer auf den echten Speicherort."""
    stage_path = Path(omni.usd.get_context().get_stage().GetRootLayer().realPath)
    for candidate in [stage_path.parent, stage_path.parent.parent]:
        if (candidate / "models").is_dir():
            return candidate
    raise RuntimeError(
        f"Repo-Root nicht gefunden (gesucht ab: {stage_path})\n"
        "Stelle sicher, dass das USD aus dem Repo geladen ist."
    )


# ============================================================
#  NORMIERUNG  (identisch zu collect_data.py und training/)
# ============================================================

def _normalize(pos_deg: np.ndarray) -> np.ndarray:
    """Grad -> [0, 1]:  0° = 0.0,  -90° = 1.0"""
    return -pos_deg / 90.0


def _denormalize(pos_norm: np.ndarray) -> np.ndarray:
    return -pos_norm * 90.0


# ============================================================
#  NUMPY-LSTM  (kein sys.path / kein torch in Isaac Sim noetig)
#  Architektur muss mit training/model.py uebereinstimmen:
#    Input(22) -> LSTM(128, 2 Lagen) -> Linear(64) -> ReLU -> Linear(11) -> Sigmoid
# ============================================================

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20.0, 20.0)))


class NumpyLSTM:

    def __init__(self, w: dict):
        self._layers = [
            (w["lstm.weight_ih_l0"], w["lstm.weight_hh_l0"],
             w["lstm.bias_ih_l0"],   w["lstm.bias_hh_l0"]),
            (w["lstm.weight_ih_l1"], w["lstm.weight_hh_l1"],
             w["lstm.bias_ih_l1"],   w["lstm.bias_hh_l1"]),
        ]
        self._w_fc0, self._b_fc0 = w["head.0.weight"], w["head.0.bias"]
        self._w_fc1, self._b_fc1 = w["head.2.weight"], w["head.2.bias"]
        hidden       = self._layers[0][0].shape[0] // 4
        self._h      = [np.zeros(hidden) for _ in self._layers]
        self._c      = [np.zeros(hidden) for _ in self._layers]

    @staticmethod
    def _cell(x, h, c, w_ih, w_hh, b_ih, b_hh):
        gates        = w_ih @ x + b_ih + w_hh @ h + b_hh
        gi, gf, gg, go = np.split(gates, 4)
        c_new        = _sigmoid(gf) * c + _sigmoid(gi) * np.tanh(gg)
        h_new        = _sigmoid(go) * np.tanh(c_new)
        return h_new, c_new

    def step(self, x: np.ndarray) -> np.ndarray:
        """Ein Zeitschritt: x (22,) -> normierte Vorhersage (11,) in [0, 1]"""
        inp = x
        for i, layer in enumerate(self._layers):
            self._h[i], self._c[i] = self._cell(inp, self._h[i], self._c[i], *layer)
            inp = self._h[i]
        fc = np.maximum(0.0, self._w_fc0 @ inp + self._b_fc0)
        return _sigmoid(self._w_fc1 @ fc + self._b_fc1)

    def reset(self):
        for h, c in zip(self._h, self._c):
            h[:] = c[:] = 0.0


# ============================================================
#  ISAAC SIM HELFER
# ============================================================

def _find_weights(model_dir: Path) -> Path:
    files = sorted(model_dir.glob("hand_lstm_*_weights.npz"))
    if not files:
        raise FileNotFoundError(
            f"Keine Gewichtsdatei in {model_dir}\n"
            "Zuerst ausfuehren: .venv/bin/python inference/export_weights.py"
        )
    return files[-1]


def _build_drives(stage) -> dict:
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


def _read_targets(drives: dict) -> np.ndarray:
    """Aktuelle Sollwinkel aus DriveAPI [Grad]."""
    return np.array([(drives[n].GetTargetPositionAttr().Get() or 0.0)
                     for n in DOF_NAMES if n in drives])


def _set_targets(drives: dict, angles_deg: np.ndarray):
    """Setzt Sollwinkel fuer alle Handgelenke [Grad]."""
    for i, name in enumerate(DOF_NAMES):
        if name in drives:
            drives[name].GetTargetPositionAttr().Set(float(angles_deg[i]))


def _test_trajectory(hz: int, speeds_deg_s: list) -> np.ndarray:
    """Auf/zu-Trajektorie fuer alle Finger.
    speeds_deg_s: Liste mit Grad/s pro Zyklus — Laenge bestimmt Anzahl Zyklen.
    """
    segments = []
    for speed in speeds_deg_s:
        n = max(1, int(90.0 / speed * hz))
        segments.append(np.linspace(0.0,   -90.0, n))
        segments.append(np.linspace(-90.0,   0.0, n))
    return np.concatenate(segments)


def _read_positions(robot) -> np.ndarray:
    """Istwinkel der Handgelenke aus PhysX [Grad]."""
    all_rad = robot.get_joint_positions()
    return np.degrees(np.array([all_rad[i] for i in DOF_INDICES]))


def _disable_hand_physics(drives: dict):
    """Stiffness/Damping auf 0 — LSTM uebernimmt danach komplett."""
    for drive in drives.values():
        drive.GetStiffnessAttr().Set(0.0)
        drive.GetDampingAttr().Set(0.0)
    print("[drive] PhysX-Dynamik der Handgelenke deaktiviert.")


def _drive_joints(robot, pred_deg: np.ndarray):
    """Setzt Handgelenke direkt auf LSTM-Vorhersage (Isaac Sim erwartet Radiant)."""
    all_rad = robot.get_joint_positions().copy()
    for i, dof_idx in enumerate(DOF_INDICES):
        all_rad[dof_idx] = np.radians(pred_deg[i])
    robot.set_joint_positions(all_rad.astype(np.float32))


# ============================================================
#  HAUPT-COROUTINE
# ============================================================

async def run():
    # omni.isaac.core.articulations.Articulation ist in Isaac Sim 4.x deprecated,
    # funktioniert aber weiterhin und braucht keine explizite tensor physics_sim_view.
    from omni.isaac.core.articulations import Articulation  # type: ignore

    repo_root = _repo_root()
    model_dir = repo_root / "models"
    log_dir   = repo_root / "data"

    weights_path = _find_weights(model_dir)
    model        = NumpyLSTM(dict(np.load(weights_path)))
    print(f"[Inferenz] Gewichte:  {weights_path.name}")
    print(f"[Inferenz] Modus:     {MODE.upper()}")

    stage = omni.usd.get_context().get_stage()
    app   = omni.kit.app.get_app()

    # Mehrere Frames warten damit die PhysicsScene vollstaendig initialisiert ist
    for _ in range(3):
        await app.next_update_async()

    robot = Articulation(ROBOT_PATH)
    robot.initialize()

    drives = _build_drives(stage)
    if len(drives) < N_DOFS:
        print(f"[WARN] Nur {len(drives)}/{N_DOFS} Drives gefunden — DOF_NAMES pruefen.")

    if MODE == "drive":
        _disable_hand_physics(drives)

    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"inference_{MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npz"

    traj      = (_test_trajectory(HZ, TRAJ_SPEEDS_DEG_S)
                 if (MODE == "compare" and RUN_TEST_TRAJ) else np.array([]))
    max_steps = len(traj) if len(traj) > 0 else 0  # 0 = endlos

    n_cycles  = len(TRAJ_SPEEDS_DEG_S)
    laufzeit  = f"{max_steps / HZ:.1f} s ({n_cycles} Zyklen: {TRAJ_SPEEDS_DEG_S} °/s)" if max_steps else "endlos"
    print(f"[Inferenz] Start — Laufzeit: {laufzeit}  |  Log: {log_path.name}")

    prev_pred                   = np.zeros(N_DOFS)
    buf_cmd, buf_phys, buf_lstm = [], [], []

    step = 0
    while max_steps == 0 or step < max_steps:
        await app.next_update_async()

        # Test-Trajektorie: alle Finger gleichzeitig bewegen
        if len(traj) > 0:
            _set_targets(drives, np.full(N_DOFS, traj[step]))

        pos_phys = _read_positions(robot)
        cmd_deg  = _read_targets(drives)

        x_t       = np.concatenate([_normalize(cmd_deg), prev_pred])
        pred_norm = model.step(x_t)
        pred_deg  = _denormalize(pred_norm)
        prev_pred = pred_norm

        if MODE == "drive":
            _drive_joints(robot, pred_deg)

        buf_cmd.append(cmd_deg)
        buf_phys.append(pos_phys)
        buf_lstm.append(pred_deg)

        if step % LOG_EVERY == 0:
            err = np.abs(pred_deg - pos_phys)
            if MODE == "compare":
                print(f"  t={step/HZ:5.1f}s | Fehler LSTM vs PhysX: "
                      f"mean={err.mean():.2f}°  max={err.max():.2f}°")
            else:
                print(f"  t={step/HZ:5.1f}s | LSTM treibt Hand: "
                      f"mean={pred_deg.mean():.1f}°  "
                      f"[{pred_deg.min():.1f}° .. {pred_deg.max():.1f}°]")

        step += 1  # nach allen Lesezugriffen erhoehen

    np.savez(
        log_path,
        cmd       = np.array(buf_cmd),
        pos_phys  = np.array(buf_phys),
        pos_lstm  = np.array(buf_lstm),
        dof_names = np.array(DOF_NAMES),
    )
    print(f"\n[Inferenz] Fertig — {step} Frames gespeichert -> {log_path.name}")


asyncio.ensure_future(run())
