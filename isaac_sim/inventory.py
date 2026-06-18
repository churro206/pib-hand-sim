import numpy as np
import omni.usd
from pxr import UsdPhysics  # type: ignore
import sys
from io import StringIO

output_buffer = StringIO()
sys.stdout = output_buffer

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
        for side in ("left", "right"):
            hand_dofs = [n for n in dof_names
                         if side in n.lower() and any(k in n.lower()
                         for k in ["thumb", "index", "middle", "ring", "pinky"])]
            print(f"\n{side.capitalize()} Hand DOFs ({len(hand_dofs)}): {hand_dofs}")
    except Exception as e:
        print(f"[INFO] Articulation API: {e}")
        print("-> Simulation starten (Play), dann nochmal ausfuehren")

print("\n" + "="*60 + "\n")

# ─── Erweiterung für v4: Hand-DOF-Liste in Konfig-Format ─────────────────────
if art_roots and 'dof_names' in dir():
    print("\n" + "="*60)
    print("BLOCK FÜR pib_hand_config.py")
    print("="*60)

    finger_order  = {"thumb": 0, "index": 1, "middle": 2, "ring": 3, "pinky": 4}
    segment_order = {"rotator": 0, "opposition": 0,
                     "proximal": 1, "distal": 2, "tip": 3}
    finger_kws    = list(finger_order.keys())

    def sort_key(name):
        n = name.lower()
        f = next((v for k, v in finger_order.items()  if k in n), 99)
        s = next((v for k, v in segment_order.items() if k in n), 99)
        return (f, s, n)

    hand_data = {}
    for side in ("left", "right"):
        dofs = [(i, n) for i, n in enumerate(dof_names)
                if side in n.lower() and any(k in n.lower() for k in finger_kws)]
        dofs.sort(key=lambda x: sort_key(x[1]))
        hand_data[side] = dofs

    print(f"\nHand-DOFs links:  {len(hand_data['left'])}")
    print(f"Hand-DOFs rechts: {len(hand_data['right'])}")
    print(f"Erwartet für v4:  15 pro Hand\n")

    print("# --- Auto-generiert: pib v4, beide Haende ---\n")
    print("JOINT_SIGN = -1  # Onshape → Isaac Vorzeichen-Kompensation\n")
    print("HAND_DOFS = {")

    for side, active in hand_data.items():
        print(f'    "{side}": {{')

        print('        "names": [')
        for idx, name in active:
            print(f'            "{name}",')
        print("        ],")

        print('        "indices": [')
        for idx, name in active:
            print(f"            {idx},  # {name}")
        print("        ],")

        groups = {"thumb_opp": [], "thumb": [], "index": [],
                  "middle": [], "ring": [], "pinky": []}
        for idx, name in active:
            n = name.lower()
            if   "rotator" in n or "opposition" in n: groups["thumb_opp"].append(idx)
            elif "thumb"  in n: groups["thumb"].append(idx)
            elif "index"  in n: groups["index"].append(idx)
            elif "middle" in n: groups["middle"].append(idx)
            elif "ring"   in n: groups["ring"].append(idx)
            elif "pinky"  in n: groups["pinky"].append(idx)

        print('        "servos": {')
        for k, v in groups.items():
            if v:
                print(f'            "{k}": {v},')
        print("        },")
        print("    },")

    print("}")

sys.stdout = sys.__stdout__  # Stdout zurücksetzen
output_text = output_buffer.getvalue()

# Auf Konsole zeigen (wie gewohnt)
print(output_text)

# Zusätzlich in Datei schreiben
output_path = "/home/athome/repos/pib-hand-sim/isaac_sim/inventory_output.txt"
with open(output_path, "w") as f:
    f.write(output_text)
print(f"\n>>> Output gespeichert in: {output_path}")
