"""
dump_pose.py — Liest die aktuellen Drive-Targets (Grad, Onshape-Konvention
seit ADR-007) der Gelenke aus der offenen Stage und hängt sie als Waypoint
an isaac_sim/tools/_pose_dump.json an — zum Weiterverarbeiten in einen neuen
Test-Client (test_client_*.py), ohne die Werte aus der Isaac-Sim-Konsole
copy-pasten zu müssen (dort oft nicht sauber selektierbar).

Hintergrund: Testpose-Sequenzen entstehen weiterhin manuell — Roboter in
Isaac Sim von Hand posiert (Physics Inspector / Drive-Target-Slider), siehe
docs/handoff.md. Dieses Skript ersetzt nur das fehleranfällige Abtippen/
Kopieren der Werte. Liest dasselbe Attribut, das setup_stage.set_initial_pose()
setzt (UsdPhysics.DriveAPI "angular" → TargetPosition, Grad) — also exakt die
Werte, die beim manuellen Posieren tatsächlich gesetzt wurden.

Verwendung (ein Durchlauf pro Waypoint):
  1. Roboter in Isaac Sim manuell auf die gewünschte Pose bringen (Play an,
     Zielpose über Drive-Targets/Physics Inspector anfahren, kurz einschwingen
     lassen).
  2. WAYPOINT_LABEL/WAYPOINT_TIME_S unten anpassen.
  3. Dieses Skript im Script Editor ausführen — hängt den Waypoint in
     _pose_dump.json an (bestehende Waypoints bleiben erhalten).
  4. Wenn alle Waypoints drin sind: kurz Bescheid geben, ich lese die Datei.

Im Script Editor ausführen.
"""
import json
import os
import omni.usd
from pxr import UsdPhysics

stage = omni.usd.get_context().get_stage()


def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    from pathlib import Path
    f = Path(stage.GetRootLayer().realPath)
    for ancestor in f.parents:  # alle Elternverzeichnisse, nicht nur 2 Ebenen
        if (ancestor / "config" / "pib_hand_config_v4.py").is_file():
            return str(ancestor)
    raise FileNotFoundError("pib-hand-sim nicht gefunden. PIB_HAND_SIM_ROOT setzen.")


DUMP_FILE = os.path.join(_find_root(), "isaac_sim", "tools", "_pose_dump.json")

# --- Pro Waypoint anpassen -------------------------------------------------
WAYPOINT_LABEL = "neutral"   # z.B. "neutral", "approach", "grasp", "lift"
WAYPOINT_TIME_S = 2.0         # Ziel-Zeit relativ zum Sequenzstart (Sekunden)

# Leer lassen = alle PhysicsRevoluteJoint-Prims in der Stage (alle 44 DOFs).
# Für eine konkrete Sequenz gezielt einschränken, z.B.:
# JOINT_FILTER = [
#     "dof_shoulder_vertical_right", "dof_shoulder_horizontal_right",
#     "dof_elbow_right", "dof_forearm_right", "dof_wrist_right",
#     "dof_thumb_right_rotator", "dof_index_right_proximal",
# ]
JOINT_FILTER: list = []
# ---------------------------------------------------------------------------

pose = {}
for prim in stage.Traverse():
    if prim.GetTypeName() != "PhysicsRevoluteJoint":
        continue
    name = prim.GetPath().name
    if JOINT_FILTER and name not in JOINT_FILTER:
        continue
    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    if not drive:
        continue
    pose[name] = round(drive.GetTargetPositionAttr().Get(), 1)

data = {}
if os.path.isfile(DUMP_FILE):
    with open(DUMP_FILE) as f:
        data = json.load(f)

data[WAYPOINT_LABEL] = {"t": WAYPOINT_TIME_S, "positions_deg": pose}

with open(DUMP_FILE, "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)

print(f"Waypoint '{WAYPOINT_LABEL}' (t={WAYPOINT_TIME_S}s, {len(pose)} Gelenke) -> {DUMP_FILE}")
print("Bisherige Waypoints in der Datei:", list(data.keys()))

