"""
bake_hand_asset_v5.py — Roboter-Einstellungen fest in die Hand-USD schreiben (Isaac Lab).

Isaac Lab führt start.py nicht aus. Alles, was dort pro Session gesetzt wird und für die
Physik der Hand zählt, muss deshalb in der Asset-USD stehen. Dieses Skript wendet aus
isaac_sim/setup_stage.py nur den roboterbezogenen Teil an — keine Physics Scene, kein
Boden, kein Licht (gehören nicht in ein Asset):
  - configure_drives       Servo-Aktuatormodell + passive Folgegelenke (ADR-012)
  - configure_mimic_joints PIP/DIP/IP folgen dem MCP (ADR-011) — einziger Punkt, den
                           Isaac Lab nicht selbst konfigurieren kann
  - set_joint_limits       wie im Vollroboter
  - Self-Collision am Articulation Root an (ADR-012)
Danach prüft es das Ergebnis und schreibt einen Bericht nach
isaac_sim/tools/_hand_asset_bake.txt.

Ablauf (Script Editor):
  1. pib_hand_left_urdf_v5/robot.urdf importieren (Static Base, Convex Hull,
     Self-Collision an), als isaac_sim/usd/pib_hand_left_v5.usd speichern und öffnen
  2. dieses Skript ausführen
  3. Bericht prüfen, Stage speichern (Ctrl+S) und neu öffnen
"""
import os
import sys
import importlib.util
from pathlib import Path

import omni.usd  # type: ignore
from pxr import Usd, UsdPhysics, PhysxSchema  # type: ignore

EXPECTED_JOINTS = 17          # 8 Servos + 9 Mimic-Folgegelenke (linke Hand)
EXPECTED_MIMIC = 9

stage = omni.usd.get_context().get_stage()
_root = os.environ.get("PIB_HAND_SIM_ROOT", str(Path.home() / "repos" / "pib-hand-sim"))
_report_path = os.path.join(_root, "isaac_sim", "tools", "_hand_asset_bake.txt")
_lines = []


def _log(msg: str = "") -> None:
    print(msg)
    _lines.append(msg)


def _load_mod(name, path, **pre_attrs):
    sys.modules.pop(name, None)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    for k, v in pre_attrs.items():
        setattr(mod, k, v)
    spec.loader.exec_module(mod)
    return mod


ss = _load_mod("setup_stage", os.path.join(_root, "isaac_sim", "setup_stage.py"), _SKIP_AUTO_SETUP=True)
cfg5 = ss._cfg5

_log(f"Stage: {stage.GetRootLayer().realPath}")
_log()
ss.configure_drives(stage)
ss.configure_mimic_joints(stage)
ss.set_joint_limits(stage)

# ── Articulation Root: Self-Collision an ──────────────────────────────────────
roots = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
for prim in roots:
    PhysxSchema.PhysxArticulationAPI.Apply(prim).CreateEnabledSelfCollisionsAttr().Set(True)

# ── Prüfung ───────────────────────────────────────────────────────────────────
_log()
_log("── Prüfung ──")
problems = []

default_prim = stage.GetDefaultPrim()
_log(f"Default Prim: {default_prim.GetPath() if default_prim else '— keiner —'}")
if not default_prim:
    problems.append("kein Default Prim (Isaac Lab referenziert die USD über den Default Prim)")

_log(f"Articulation Root(s): {[str(p.GetPath()) for p in roots]}")
if len(roots) != 1:
    problems.append(f"{len(roots)} Articulation Roots statt 1")

joints = {p.GetPath().name: p for p in stage.Traverse()
          if p.GetTypeName() == "PhysicsRevoluteJoint" or p.HasAPI(UsdPhysics.RevoluteJoint)}
_log(f"Revolute Joints: {len(joints)}")
if len(joints) != EXPECTED_JOINTS:
    problems.append(f"{len(joints)} Revolute Joints statt {EXPECTED_JOINTS}")

missing = [n for n in cfg5.LEFT_HAND_SERVO_JOINTS if n not in joints]
if missing:
    problems.append(f"Servo-Gelenke fehlen: {missing}")

_log()
_log(f"{'Gelenk':24s} {'Limit [°]':>16s} {'k [Nm/°]':>9s} {'d [Nm·s/°]':>11s} {'maxF':>6s}  Mimic")
mimic_count = 0
for name in sorted(joints):
    prim = joints[name]
    lo = prim.GetAttribute("physics:lowerLimit").Get()
    hi = prim.GetAttribute("physics:upperLimit").Get()
    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    k = drive.GetStiffnessAttr().Get() if drive else None
    d = drive.GetDampingAttr().Get() if drive else None
    f = drive.GetMaxForceAttr().Get() if drive else None
    mimic = ""
    for schema in prim.GetAppliedSchemas():
        if schema.startswith("PhysxMimicJointAPI"):
            inst = schema.split(":", 1)[1]
            api = PhysxSchema.PhysxMimicJointAPI(prim, inst)
            targets = api.GetReferenceJointRel().GetTargets()
            mimic = f"<- {targets[0].name if targets else '?'} (gearing {api.GetGearingAttr().Get():g})"
            mimic_count += 1
    _log(f"{name:24s} [{lo:6.1f}, {hi:6.1f}] {k!s:>9.9s} {d!s:>11.11s} {f!s:>6.6s}  {mimic}")
    if name in ss.MIMIC_JOINTS and not mimic:
        problems.append(f"{name}: Mimic fehlt")

if mimic_count != EXPECTED_MIMIC:
    problems.append(f"{mimic_count} Mimic-Gelenke statt {EXPECTED_MIMIC}")

instanceable = [str(p.GetPath()) for p in stage.Traverse() if p.IsInstanceable()]
_log()
_log(f"Instanceable Prims: {len(instanceable)}")

_log()
if problems:
    _log("PROBLEME:")
    for p in problems:
        _log(f"  - {p}")
else:
    _log("OK — Stage speichern (Ctrl+S) und neu öffnen.")

with open(_report_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(_lines) + "\n")
print(f"\nBericht: {_report_path}")
