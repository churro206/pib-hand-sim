"""
isaac_sim/_launch_helper.py — Isaac Sim 5.1 Standalone-Launcher.

Verwendung:
  ~/isaacsim/python.sh isaac_sim/_launch_helper.py <modul_name>
  ~/isaacsim/python.sh isaac_sim/_launch_helper.py test_hand_poses

Stellt als Modul-Globals bereit (import _launch_helper as lh):
  lh.sim_app  — SimulationApp-Instanz für sim_app.update()
  lh.robot    — initialisierter Robot-Handle (SingleArticulation)

Voraussetzung: setup_stage.py einmal im Script Editor ausgeführt und
Stage gespeichert (Ctrl+S). Der Launcher ruft configure_drives() und
set_initial_pose() automatisch erneut auf — so funktioniert er auch
auf frisch geladenen USDs ohne vorheriges setup_stage-Run.
"""
import sys
import os
from pathlib import Path

# SimulationApp MUSS als ALLERERSTES initialisiert werden — vor allen Isaac-Imports
try:
    from isaacsim import SimulationApp  # type: ignore
except ImportError:
    _msg = (
        "\n[_launch_helper] FEHLER: SimulationApp nicht importierbar.\n"
        "_launch_helper.py ist ein Standalone-Launcher — NICHT im Script Editor ausführen!\n"
        "\nKorrekte Verwendung (Terminal):\n"
        "  ~/isaacsim/python.sh isaac_sim/_launch_helper.py test_hand_poses\n"
        "\nFür den Script Editor: test_hand_poses.py direkt öffnen und ausführen.\n"
    )
    try:
        import carb  # type: ignore
        carb.log_error(_msg)
    except ImportError:
        print(_msg)
    raise SystemExit(1)

sim_app = SimulationApp({"headless": False, "renderer": "RayTracedLighting"})

# ── Pfade ─────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent       # isaac_sim/
_ROOT = _HERE.parent                # Repo-Root
_USD_DIR = _HERE / "usd"
_candidates = sorted(_USD_DIR.glob("pib_upperbody_*_flattened.usd"))
if not _candidates:
    raise FileNotFoundError(f"Keine pib_upperbody_*_flattened.usd in {_USD_DIR}")
_USD = _candidates[-1]              # höchste Versionsnummer
print(f"[launcher] Neueste USD: {_USD.name}")

for _p in [str(_HERE), str(_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Isaac-spezifische Imports (erst nach SimulationApp möglich) ───────────────
import carb            # type: ignore
import omni.usd        # type: ignore
import omni.timeline   # type: ignore
import importlib.util as _ilu

try:
    from isaacsim.core.prims import SingleArticulation as _ArtCls   # type: ignore
except ImportError:
    from omni.isaac.core.articulations import Articulation as _ArtCls  # type: ignore

# Config für ROBOT_PRIM_PATH
_cfg_spec = _ilu.spec_from_file_location("pib_hand_config", _ROOT / "config" / "pib_hand_config.py")
_cfg_mod  = _ilu.module_from_spec(_cfg_spec)
_cfg_spec.loader.exec_module(_cfg_mod)
ROBOT_PRIM_PATH = _cfg_mod.ROBOT_PRIM_PATH

# ── USD laden ─────────────────────────────────────────────────────────────────
if not _USD.exists():
    carb.log_error(f"[launcher] USD nicht gefunden: {_USD}")
    sim_app.close()
    sys.exit(1)

omni.usd.get_context().open_stage(str(_USD))
sim_app.update()
print(f"[launcher] USD geladen: {_USD.name}")

# ── Drives konfigurieren (aus setup_stage) ────────────────────────────────────
# _SKIP_AUTO_SETUP = True verhindert dass setup_stage beim Import auto-ausführt.
try:
    _ss_spec = _ilu.spec_from_file_location("_setup_stage", _HERE / "setup_stage.py")
    _ss_mod  = _ilu.module_from_spec(_ss_spec)
    _ss_mod._SKIP_AUTO_SETUP = True
    _ss_spec.loader.exec_module(_ss_mod)
    _stage = omni.usd.get_context().get_stage()
    if hasattr(_ss_mod, "configure_drives"):
        _ss_mod.configure_drives(_stage)
    if hasattr(_ss_mod, "fix_joint_limits"):
        _ss_mod.fix_joint_limits(_stage)
    if hasattr(_ss_mod, "set_initial_pose"):
        _ss_mod.set_initial_pose(_stage)
    print("[launcher] Drives konfiguriert via setup_stage")
except Exception as _e:
    carb.log_warn(f"[launcher] setup_stage nicht geladen: {_e}")

# ── Physik starten ────────────────────────────────────────────────────────────
_timeline = omni.timeline.get_timeline_interface()
_timeline.play()
for _ in range(10):    # Physik-Initialisierung abwarten
    sim_app.update()

# ── Robot initialisieren ──────────────────────────────────────────────────────
robot = _ArtCls(prim_path=ROBOT_PRIM_PATH)
robot.initialize()
print(f"[launcher] Robot initialisiert: {ROBOT_PRIM_PATH}")

# ── robot_io mit Robot-Handle versorgen und als Modul registrieren ────────────
_io_spec = _ilu.spec_from_file_location("robot_io", _HERE / "robot_io.py")
_robot_io = _ilu.module_from_spec(_io_spec)
_io_spec.loader.exec_module(_robot_io)
_robot_io._set_robot(robot)
sys.modules["robot_io"] = _robot_io
print("[launcher] robot_io bereit")

# Selbst als Modul registrieren damit Ziel-Skripte importieren können:
#   import _launch_helper as lh → lh.sim_app, lh.robot
sys.modules.setdefault("_launch_helper", sys.modules[__name__])

# ── Ziel-Modul laden und run() aufrufen ───────────────────────────────────────
if len(sys.argv) > 1:
    _target      = sys.argv[1]
    _target_path = _HERE / f"{_target}.py"
    if not _target_path.exists():
        carb.log_error(f"[launcher] Modul nicht gefunden: {_target_path}")
        sim_app.close()
        sys.exit(1)

    _mod_spec = _ilu.spec_from_file_location(_target, _target_path)
    _mod      = _ilu.module_from_spec(_mod_spec)
    sys.modules[_target] = _mod
    _mod_spec.loader.exec_module(_mod)
    if hasattr(_mod, "run"):
        _mod.run()
    else:
        carb.log_warn(f"[launcher] Kein run() in {_target}.py gefunden — Modul geladen")
else:
    print("[launcher] Kein Ziel-Modul angegeben. Ctrl+C zum Beenden.")

# ── Simulation offen halten bis Fenster geschlossen ──────────────────────────
while sim_app.is_running():
    sim_app.update()

sim_app.close()
