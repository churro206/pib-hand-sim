"""
inspect_ycb.py — YCB-Assets aus Isaac Sim 5.1 inspizieren, bevor sie Testobjekte werden (nur lesend).

Listet Props/YCB/ auf dem Asset-Server und liest je USD in Axis_Aligned_Physics/: Einheiten/Hochachse,
Default-Prim, Bounding Box (Welt, in m), Lage des Ursprungs relativ zur Box, Rigid Body, Masse/Dichte,
Collider (Approximation) und gebundenes Physik-Material (Reibung). Bericht: isaac_sim/tools/_ycb_inspect.txt.

  ~/IsaacLab/isaaclab.sh -p isaac_lab/tools/inspect_ycb.py --headless
"""
import argparse
import os
import sys
from pathlib import Path

from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
args = parser.parse_args()
app = AppLauncher(args).app

import omni.client  # noqa: E402
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "isaac_sim" / "tools" / "_ycb_inspect.txt"
ROOT = f"{ISAAC_NUCLEUS_DIR}/Props/YCB"
lines = [f"Asset-Root: {ROOT}", ""]


def listdir(url):
    res, entries = omni.client.list(url)
    return res, sorted(e.relative_path for e in entries)


res, subdirs = listdir(ROOT)
lines.append(f"Props/YCB/ ({res}): {subdirs}")
for sub in subdirs:
    r, files = listdir(f"{ROOT}/{sub}")
    lines.append(f"  {sub}: {files}")
lines.append("")


def fmt(v):
    return "(" + ", ".join(f"{x:+.4f}" for x in v) + ")"


def material_info(stage, prim):
    """Physik-Material: direkt gebunden (purpose physics) oder allgemein gebunden, mit Reibwerten."""
    for purpose in ("physics", ""):
        rel = UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel(purpose) if purpose else \
            UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel()
        for t in rel.GetTargets() if rel else []:
            m = stage.GetPrimAtPath(t)
            if m and m.HasAPI(UsdPhysics.MaterialAPI):
                api = UsdPhysics.MaterialAPI(m)
                return (f"{t} [{purpose or 'allgemein'}] statisch {api.GetStaticFrictionAttr().Get()} "
                        f"dynamisch {api.GetDynamicFrictionAttr().Get()} Restitution {api.GetRestitutionAttr().Get()}")
    return None


r, files = listdir(f"{ROOT}/Axis_Aligned_Physics")
for name in [f for f in files if f.endswith(".usd")]:
    url = f"{ROOT}/Axis_Aligned_Physics/{name}"
    stage = Usd.Stage.Open(url)
    lines.append(f"== {name}")
    if stage is None:
        lines.append("  nicht ladbar")
        continue
    dp = stage.GetDefaultPrim()
    lines.append(f"  metersPerUnit {UsdGeom.GetStageMetersPerUnit(stage)}, upAxis {UsdGeom.GetStageUpAxis(stage)}, "
                 f"defaultPrim {dp.GetPath() if dp else None}")
    mpu = UsdGeom.GetStageMetersPerUnit(stage)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_], useExtentsHint=False)
    box = cache.ComputeWorldBound(dp).ComputeAlignedRange()
    lo, hi = [x * mpu for x in box.GetMin()], [x * mpu for x in box.GetMax()]
    size = [h - l for l, h in zip(lo, hi)]
    lines.append(f"  Bounding Box [m]: min {fmt(lo)} max {fmt(hi)} Größe {fmt(size)}")
    lines.append(f"  Ursprung relativ zur Boxmitte [m]: {fmt([-(l + h) / 2 for l, h in zip(lo, hi)])}")
    for prim in Usd.PrimRange(dp):
        tags = []
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            tags.append("RigidBody")
        if prim.HasAPI(UsdPhysics.MassAPI):
            m = UsdPhysics.MassAPI(prim)
            tags.append(f"Masse {m.GetMassAttr().Get()} Dichte {m.GetDensityAttr().Get()}")
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            appr = prim.GetAttribute("physics:approximation").Get() if prim.HasAPI(UsdPhysics.MeshCollisionAPI) else None
            tags.append(f"Collider ({prim.GetTypeName()}, Approximation {appr})")
        mat = material_info(stage, prim)
        if mat and (tags or prim == dp):
            tags.append(f"Material {mat}")
        if prim.IsInstance():
            tags.append("instanceable")
        if tags or prim == dp:
            xf = UsdGeom.Xformable(prim).GetOrderedXformOps() if prim.IsA(UsdGeom.Xformable) else []
            ops = ", ".join(f"{op.GetOpName()}={op.Get()}" for op in xf)
            lines.append(f"  {prim.GetPath()} [{prim.GetTypeName()}] {'; '.join(tags)}" + (f" | {ops}" if ops else ""))
    lines.append("")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
print(f"Bericht: {OUT}")
sys.stdout.flush()
os._exit(0)
