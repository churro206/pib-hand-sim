"""
Einmalig ausfuehren im Script Editor um die Stage mit
Boden, Licht und Physics Scene auszustatten.
Danach Stage speichern.
"""
import omni.usd  # type: ignore
from pxr import UsdGeom, UsdLux, UsdPhysics, PhysxSchema, Sdf, Gf  # type: ignore

stage = omni.usd.get_context().get_stage()
root = "/World"

# Physics Scene
physics_scene_path = f"{root}/PhysicsScene"
if not stage.GetPrimAtPath(physics_scene_path):
    scene = UsdPhysics.Scene.Define(stage, physics_scene_path)
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr(9.81)
    PhysxSchema.PhysxSceneAPI.Apply(stage.GetPrimAtPath(physics_scene_path))
    print("Physics Scene erstellt")
else:
    print("Physics Scene bereits vorhanden")

# Boden
ground_path = f"{root}/GroundPlane"
if not stage.GetPrimAtPath(ground_path):
    ground = UsdGeom.Mesh.Define(stage, ground_path)
    ground.CreatePointsAttr([(-5,-5,0),(5,-5,0),(5,5,0),(-5,5,0)])
    ground.CreateFaceVertexCountsAttr([4])
    ground.CreateFaceVertexIndicesAttr([0,1,2,3])
    ground.CreateNormalsAttr([(0,0,1),(0,0,1),(0,0,1),(0,0,1)])
    UsdPhysics.CollisionAPI.Apply(stage.GetPrimAtPath(ground_path))
    print("Boden erstellt")
else:
    print("Boden bereits vorhanden")

# Dome Light (gleichmaessige Ausleuchtung)
dome_path = f"{root}/DomeLight"
if not stage.GetPrimAtPath(dome_path):
    dome = UsdLux.DomeLight.Define(stage, dome_path)
    dome.CreateIntensityAttr(500.0)
    print("Dome Light erstellt")
else:
    print("Dome Light bereits vorhanden")

# Distant Light (Richtungslicht / Schatten)
sun_path = f"{root}/DistantLight"
if not stage.GetPrimAtPath(sun_path):
    sun = UsdLux.DistantLight.Define(stage, sun_path)
    sun.CreateIntensityAttr(1000.0)
    sun.CreateAngleAttr(0.53)
    xform = UsdGeom.XformCommonAPI(sun)
    xform.SetRotate(Gf.Vec3f(315.0, 0.0, 45.0))
    print("Distant Light erstellt")
else:
    print("Distant Light bereits vorhanden")

print("\nSetup abgeschlossen. Stage speichern nicht vergessen (Ctrl+S).")
