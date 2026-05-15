import numpy as np
import omni.usd
from pxr import UsdPhysics  # type: ignore

stage = omni.usd.get_context().get_stage()

# --- Articulation Root auto-finden ---
art_roots = []
for prim in stage.Traverse():
    if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
        art_roots.append(str(prim.GetPath()))

print("\n" + "="*60)
print("PIB HAND INVENTORY")
print("="*60)
print(f"\nGefundene ArticulationRoots: {art_roots}")

if not art_roots:
    print("\n[FEHLER] Kein ArticulationRoot gefunden!")
    print("Moegliche Ursachen:")
    print("  1. Simulation laeuft nicht -> Play druecken, dann nochmal ausfuehren")
    print("  2. Kein PhysicsArticulationRootAPI am Robot-Prim")
    print("     -> In Stage: Robot-Prim auswaehlen -> Add -> Physics -> Articulation Root")
else:
    robot_path = art_roots[0]
    print(f"Verwende: {robot_path}")

# --- Joints aus USD (funktioniert ohne Play) ---
print(f"\n{'Alle Revolute Joints im Stage':}")
print(f"{'Pfad':<65} {'Min':>8} {'Max':>8}")
print("-"*85)

joints_found = []
for prim in stage.Traverse():
    if prim.GetTypeName() in ("PhysicsRevoluteJoint", "PhysicsPrismaticJoint") or \
       prim.HasAPI(UsdPhysics.RevoluteJoint):
        path = str(prim.GetPath())
        lower = prim.GetAttribute("physics:lowerLimit").Get()
        upper = prim.GetAttribute("physics:upperLimit").Get()
        joints_found.append((path, lower, upper))
        lo_str = f"{lower:.1f}" if lower is not None else "n/a"
        hi_str = f"{upper:.1f}" if upper is not None else "n/a"
        print(f"{path:<65} {lo_str:>8} {hi_str:>8}")

print(f"\n{len(joints_found)} Joints total")

# --- Articulation API (nur wenn Play laeuft) ---
if art_roots:
    print("\n" + "="*60)
    print("ARTICULATION DOF API")
    print("="*60)
    try:
        from omni.isaac.core.articulations import Articulation
        robot = Articulation(robot_path)
        robot.initialize()
        dof_names = robot.dof_names

        # Limits: API unterscheidet sich je nach Isaac Sim Version
        limits = None
        for method in ["get_dof_limits", "dof_limits"]:
            candidate = getattr(robot, method, None)
            if candidate is not None:
                limits = candidate() if callable(candidate) else candidate
                break
        if limits is None and hasattr(robot, "_articulation_view"):
            limits = robot._articulation_view.get_dof_limits()

        print(f"\n{'Idx':<5} {'DOF-Name':<45} {'Min':>8} {'Max':>8}")
        print("-"*75)
        for i, name in enumerate(dof_names):
            if limits is not None:
                lims = np.array(limits).reshape(-1, 2)
                lo = np.degrees(lims[i, 0])
                hi = np.degrees(lims[i, 1])
                lim_str = f"{lo:>7.1f} {hi:>7.1f}"
            else:
                lim_str = "    n/a     n/a"
            print(f"{i:<5} {name:<45} {lim_str}")
        print(f"\nRechte Hand DOFs (<<): {[n for n in dof_names if 'right' in n.lower()]}")
    except Exception as e:
        print(f"[INFO] Articulation API: {e}")
        print("-> Simulation starten (Play), dann nochmal ausfuehren")

print("\n" + "="*60 + "\n")
