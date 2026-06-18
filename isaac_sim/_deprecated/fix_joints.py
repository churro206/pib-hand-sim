"""
Einmalig nach Play ausfuehren.
- Alle Gelenke ausser rechte Handfinger: hohe Steifigkeit -> halten T-Pose
- Rechte Handfinger: moderate Steifigkeit als Ausgangszustand fuer collect_data.py

Nach dem Ausfuehren sollte der Roboter stabil in T-Pose stehen.
"""
import omni.usd  # type: ignore
from pxr import UsdPhysics  # type: ignore

ROBOT_PATH = "/World/pib_upperbody/pib_upperbody"

# Rechte Handfinger-DOFs (aus inventory.py, 2026-05-15)
HAND_DOFS = {
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
}

# Steifigkeiten
LOCK_STIFFNESS  = 1e6   # "eingefroren"
LOCK_DAMPING    = 1e4
HAND_STIFFNESS  = 100.0  # Ausgangswert, wird von collect_data.py ueberschrieben
HAND_DAMPING    = 10.0

stage = omni.usd.get_context().get_stage()
locked = []
hand   = []

for prim in stage.Traverse():
    if prim.GetTypeName() not in ("PhysicsRevoluteJoint", "PhysicsPrismaticJoint"):
        continue

    prim_name = prim.GetPath().name  # letztes Element des Pfads
    is_hand   = prim_name in HAND_DOFS

    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    if not drive:
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")

    if is_hand:
        drive.GetStiffnessAttr().Set(HAND_STIFFNESS)
        drive.GetDampingAttr().Set(HAND_DAMPING)
        drive.GetTargetPositionAttr().Set(0.0)
        hand.append(prim_name)
    else:
        drive.GetStiffnessAttr().Set(LOCK_STIFFNESS)
        drive.GetDampingAttr().Set(LOCK_DAMPING)
        drive.GetTargetPositionAttr().Set(0.0)
        locked.append(prim_name)

print(f"\nEingefrorene Gelenke ({len(locked)}):")
for name in sorted(locked):
    print(f"  {name}")

print(f"\nRechte Hand - trainierbar ({len(hand)}):")
for name in sorted(hand):
    print(f"  {name}")

print("\nFertig. Roboter sollte jetzt stabil in T-Pose stehen.")
