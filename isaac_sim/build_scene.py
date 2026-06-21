"""
isaac_sim/build_scene.py — Demo-Szene aufbauen (Tisch + Dose + Materialien).

Idempotent: mehrfach ausführbar. Existierende Prims werden aktualisiert,
nicht neu erstellt.

Workflow:
  Script Editor: setup_stage.py → Ctrl+S → Play → build_scene.py ausführen.
  Das Skript legt Tisch und Dose in der aktuellen Stage an und bindet
  Physik-Materialien. Danach Ctrl+S → Simulation läuft.
"""

import os
import importlib.util
from pathlib import Path

import omni.usd  # type: ignore
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, Gf, Sdf  # type: ignore

stage = omni.usd.get_context().get_stage()

# ── Projekt-Root ermitteln (gleiche Logik wie setup_stage.py) ─────────────────

def _find_root() -> str:
    if "PIB_HAND_SIM_ROOT" in os.environ:
        return os.environ["PIB_HAND_SIM_ROOT"]
    f = Path(stage.GetRootLayer().realPath)
    for ancestor in [f.parent, f.parent.parent]:
        if (ancestor / "config" / "pib_hand_config.py").is_file():
            return str(ancestor)
    for candidate in [Path.home() / "repos" / "pib-hand-sim",
                      Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config.py").is_file():
            return str(candidate)
    raise FileNotFoundError("Projekt nicht gefunden. PIB_HAND_SIM_ROOT setzen.")

_root = _find_root()
_spec = importlib.util.spec_from_file_location(
    "pib_hand_config", f"{_root}/config/pib_hand_config.py"
)
_cfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cfg)
ROBOT_PRIM_PATH = _cfg.ROBOT_PRIM_PATH


# ── Einheitswürfel-Geometrie ──────────────────────────────────────────────────

def _cube_points():
    h = 0.5
    return [Gf.Vec3f(x, y, z)
            for x in (-h, h) for y in (-h, h) for z in (-h, h)]

def _cube_face_counts():
    return [4] * 6

def _cube_face_indices():
    # 6 Seiten à 4 Vertices (outward normals)
    return [0,2,3,1,  4,5,7,6,  0,1,5,4,  1,3,7,5,  3,2,6,7,  2,0,4,6]


# ── Physik-Material-Helper ────────────────────────────────────────────────────

def _bind_physics_material(prim, material):
    """Bindet ein UsdShade.Material als Physik-Material an den Prim."""
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(
        material,
        UsdShade.Tokens.weakerThanDescendants,
        "physics",
    )


# ── Physik-Materialien ────────────────────────────────────────────────────────

_MAT_BASE = "/World/PhysicsMaterials"
_MAT_SPECS = {
    # name           dynFriction  statFriction  restitution
    "HandMaterial":  (1.0,        1.2,          0.0),
    "CanMaterial":   (0.6,        0.8,          0.1),
    "TableMaterial": (0.4,        0.5,          0.0),
}


def configure_materials(stg) -> dict:
    """
    Erstellt/aktualisiert Physik-Materialien unter /World/PhysicsMaterials.
    Returns {name: UsdShade.Material}.
    """
    if not stg.GetPrimAtPath(_MAT_BASE).IsValid():
        UsdGeom.Scope.Define(stg, _MAT_BASE)

    mats = {}
    for name, (dyn, stat, rest) in _MAT_SPECS.items():
        path = f"{_MAT_BASE}/{name}"
        if not stg.GetPrimAtPath(path).IsValid():
            mat = UsdShade.Material.Define(stg, path)
        else:
            mat = UsdShade.Material(stg.GetPrimAtPath(path))

        pm = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
        pm.CreateDynamicFrictionAttr().Set(dyn)
        pm.CreateStaticFrictionAttr().Set(stat)
        pm.CreateRestitutionAttr().Set(rest)

        mats[name] = mat
        print(f"[scene] Material: {name}  dyn={dyn}  stat={stat}  rest={rest}")

    return mats


# ── Tisch ─────────────────────────────────────────────────────────────────────
# Einheitswürfel skaliert auf 1.0×0.5×0.5 m, Oberfläche bei z=0.5 m.
# Statisch (kein RigidBodyAPI).

def configure_table(stg, table_mat) -> None:
    xform_path = "/World/table"
    mesh_path  = "/World/table/table"

    if not stg.GetPrimAtPath(xform_path).IsValid():
        UsdGeom.Xform.Define(stg, xform_path)
    xform = UsdGeom.Xformable(stg.GetPrimAtPath(xform_path))
    UsdGeom.XformCommonAPI(xform).SetTranslate(Gf.Vec3d(-0.3, -0.5, 0.25))

    if not stg.GetPrimAtPath(mesh_path).IsValid():
        mesh = UsdGeom.Mesh.Define(stg, mesh_path)
    else:
        mesh = UsdGeom.Mesh(stg.GetPrimAtPath(mesh_path))

    mesh.CreatePointsAttr(_cube_points())
    mesh.CreateFaceVertexCountsAttr(_cube_face_counts())
    mesh.CreateFaceVertexIndicesAttr(_cube_face_indices())
    mesh.CreateSubdivisionSchemeAttr("none")
    UsdGeom.XformCommonAPI(mesh).SetScale(Gf.Vec3f(1.0, 0.5, 0.5))

    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr().Set("convexHull")

    _bind_physics_material(mesh.GetPrim(), table_mat)
    print("[scene] Tisch: /World/table  (1.0×0.5×0.5 m, Oberfläche z=0.5)")


# ── Dose ──────────────────────────────────────────────────────────────────────
# UsdGeom.Cylinder, unit (r=0.5, h=1.0), skaliert auf r=0.04 m, h=0.15 m.
# Dynamisch (RigidBodyAPI) mit physikalisch korrekten Trägheitsmomenten.

def configure_can(stg, can_mat) -> None:
    xform_path = "/World/can"
    cyl_path   = "/World/can/can"

    if not stg.GetPrimAtPath(xform_path).IsValid():
        UsdGeom.Xform.Define(stg, xform_path)

    UsdGeom.XformCommonAPI(stg.GetPrimAtPath(xform_path)).SetTranslate(
        Gf.Vec3d(-0.15, -0.45, 0.6)
    )

    # RigidBody und Mass auf dem Body-Xform
    rb = UsdPhysics.RigidBodyAPI.Apply(stg.GetPrimAtPath(xform_path))

    mass_api = UsdPhysics.MassAPI.Apply(stg.GetPrimAtPath(xform_path))
    mass_api.CreateMassAttr().Set(0.05)
    # Zylinder: r=0.04 m, h=0.15 m, m=0.05 kg
    # Ixx = Iyy = (1/12)*m*(3*r² + h²) ≈ 1.1e-4 kg·m²
    # Izz = (1/2)*m*r²                  ≈ 4.0e-5 kg·m²
    mass_api.CreateDiagonalInertiaAttr().Set(Gf.Vec3f(1.1e-4, 1.1e-4, 4.0e-5))

    if not stg.GetPrimAtPath(cyl_path).IsValid():
        cyl = UsdGeom.Cylinder.Define(stg, cyl_path)
    else:
        cyl = UsdGeom.Cylinder(stg.GetPrimAtPath(cyl_path))

    # Unit-Zylinder: Skalierung ergibt r_eff=0.04, h_eff=0.15
    cyl.CreateRadiusAttr().Set(0.5)
    cyl.CreateHeightAttr().Set(1.0)
    cyl.CreateAxisAttr().Set("Z")
    UsdGeom.XformCommonAPI(cyl).SetScale(Gf.Vec3f(0.08, 0.08, 0.15))

    UsdPhysics.CollisionAPI.Apply(cyl.GetPrim())
    # UsdGeom.Cylinder wird von PhysX als analytische Form erkannt.
    # convexHull-Override falls Isaac Sim es als Mesh behandelt:
    UsdPhysics.MeshCollisionAPI.Apply(cyl.GetPrim()).CreateApproximationAttr().Set("convexHull")

    _bind_physics_material(cyl.GetPrim(), can_mat)
    print("[scene] Dose: /World/can  (r=0.04 m, h=0.15 m, m=0.05 kg, z=0.6)")


# ── Hand-Collider Material-Binding ────────────────────────────────────────────

_HAND_SUBSTRINGS = ("palm", "thumb", "index", "middle", "ring", "pinky", "finger")


def bind_hand_materials(stg, hand_mat) -> int:
    """
    Findet alle Collision-Prims unter dem Roboter, deren Pfad einen
    Hand-Substring enthält, und bindet HandMaterial.
    Gibt Anzahl gebundener Prims zurück.
    """
    robot_prim = stg.GetPrimAtPath(ROBOT_PRIM_PATH)
    if not robot_prim.IsValid():
        print(f"[scene] Roboter nicht gefunden: {ROBOT_PRIM_PATH}")
        return 0

    count = 0
    for prim in Usd.PrimRange(robot_prim):
        if not prim.HasAPI(UsdPhysics.CollisionAPI):
            continue
        path_lower = str(prim.GetPath()).lower()
        if any(sub in path_lower for sub in _HAND_SUBSTRINGS):
            _bind_physics_material(prim, hand_mat)
            count += 1

    print(f"[scene] HandMaterial: {count} Collider gebunden")
    return count


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def build_scene(stg) -> None:
    mats = configure_materials(stg)
    configure_table(stg, mats["TableMaterial"])
    configure_can(stg,   mats["CanMaterial"])
    bind_hand_materials(stg, mats["HandMaterial"])
    print("[scene] Demo-Szene vollständig aufgebaut.")


# ── Script-Editor-Block ───────────────────────────────────────────────────────
if not globals().get("_SKIP_AUTO_SETUP"):
    build_scene(stage)
    print("\nSzene bereit. Stage speichern (Ctrl+S) wenn noch nicht getan.")
