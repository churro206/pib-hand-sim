"""
Setzt alle Gelenke auf stiffness=0 / damping=0.
Gelenke haengen dann frei unter Schwerkraft.
Danach fix_joints.py ausfuehren um wieder einzufrieren.
"""
import omni.usd  # type: ignore
from pxr import UsdPhysics  # type: ignore

stage = omni.usd.get_context().get_stage()
count = 0

for prim in stage.Traverse():
    if prim.GetTypeName() not in ("PhysicsRevoluteJoint", "PhysicsPrismaticJoint"):
        continue
    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    if not drive:
        continue
    drive.GetStiffnessAttr().Set(0.0)
    drive.GetDampingAttr().Set(0.0)
    drive.GetTargetPositionAttr().Set(0.0)
    count += 1

print(f"{count} Gelenke freigegeben. Beobachte das Verhalten, dann fix_joints.py ausfuehren.")
