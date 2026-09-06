"""
flip_joint_sign.py — Dreht die Vorzeichen-Konvention aller PhysicsRevoluteJoint-
Prims in der aktuell offenen Stage um, ohne die physische Pose zu verändern.

Hintergrund: Onshape und Isaacs importierte Gelenkachsen sind vorzeicheninvertiert
(JOINT_SIGN=-1). Bisher kompensiert durch einen Script Node im Action Graph +
gespiegelte Limits in setup_stage.py. Dieses Skript behebt die Ursache direkt am
Gelenk-Prim, unabhängig vom Importweg (Onshape-Importer, nicht URDF-Import).

Mechanik: Ein Revolute Joint misst seinen Winkel aus der relativen Orientierung
von localRot0 (Body0-Seite) zu localRot1 (Body1-Seite) um die gemeinsame Achse.
Dreht man BEIDE Seiten um dieselbe 180°-Rotation um eine zur Gelenkachse senk-
rechte Achse, bleibt die Weltausrichtung der Achse unverändert (kein Snap), aber
der gemessene Winkel kehrt sein Vorzeichen um (Rotationskonjugation F⁻¹MF erhält
den Winkel, spiegelt nur die Achse — bei gleichem Winkel um gespiegelte Achse
ist das exakt das Vorzeichen-Gegenteil um die Original-Achse).

Limits werden passend mitgedreht: neu_lower = -alt_upper, neu_upper = -alt_lower.

WICHTIG:
  - Vor dem Ausführen: Simulation stoppen (nicht während Play laufen lassen).
  - Danach NICHT einfach start.py erneut ausführen, bevor setup_stage.py/
    config/pib_hand_config_v4.py angepasst sind (siehe Begleit-Änderungen) —
    sonst überschreibt set_joint_limits() die neuen Limits wieder mit den
    alten gespiegelten Werten.
  - Erst nach visueller Bestätigung (Play, ein Gelenk auf positiven Wert
    fahren, Richtung prüfen) mit Ctrl+S speichern.

Im Script Editor ausführen.
"""
import omni.usd
from pxr import Gf

stage = omni.usd.get_context().get_stage()

_AXIS_VEC = {
    "X": Gf.Vec3d(1, 0, 0),
    "Y": Gf.Vec3d(0, 1, 0),
    "Z": Gf.Vec3d(0, 0, 1),
}


def _perpendicular(axis_vec: Gf.Vec3d) -> Gf.Vec3d:
    """Beliebiger Einheitsvektor senkrecht zu axis_vec."""
    ref = Gf.Vec3d(0, 0, 1) if abs(axis_vec[2]) < 0.9 else Gf.Vec3d(0, 1, 0)
    return (axis_vec ^ ref).GetNormalized()  # Kreuzprodukt-Operator (pxr.Gf.Vec3d)


def flip_joint_sign(prim) -> bool:
    axis_attr = prim.GetAttribute("physics:axis")
    lower_attr = prim.GetAttribute("physics:lowerLimit")
    upper_attr = prim.GetAttribute("physics:upperLimit")
    rot0_attr = prim.GetAttribute("physics:localRot0")
    rot1_attr = prim.GetAttribute("physics:localRot1")
    if not all([axis_attr, lower_attr, upper_attr, rot0_attr, rot1_attr]):
        return False

    axis_vec = _AXIS_VEC.get(str(axis_attr.Get()))
    if axis_vec is None:
        return False

    perp = _perpendicular(axis_vec)
    flip = Gf.Quatf(Gf.Rotation(perp, 180.0).GetQuat())

    rot0_attr.Set(rot0_attr.Get() * flip)
    rot1_attr.Set(rot1_attr.Get() * flip)

    lower, upper = lower_attr.Get(), upper_attr.Get()
    lower_attr.Set(-upper)
    upper_attr.Set(-lower)
    return True


count = 0
for prim in stage.Traverse():
    if prim.GetTypeName() != "PhysicsRevoluteJoint":
        continue
    name = prim.GetPath().name
    lo0 = prim.GetAttribute("physics:lowerLimit").Get()
    up0 = prim.GetAttribute("physics:upperLimit").Get()
    if flip_joint_sign(prim):
        count += 1
        lo1 = prim.GetAttribute("physics:lowerLimit").Get()
        up1 = prim.GetAttribute("physics:upperLimit").Get()
        print(f"{name}: [{lo0:.1f},{up0:.1f}] -> [{lo1:.1f},{up1:.1f}]")
    else:
        print(f"ÜBERSPRUNGEN (fehlende Attribute): {name}")

print(f"\n{count} Gelenke umgedreht. NICHT speichern vor visueller Prüfung:")
print("  1. Play drücken, z.B. dof_elbow_right per Drive-Target auf +90 setzen")
print("  2. Erwartung: Ellbogen beugt sich (Onshape-Konvention direkt)")
print("  3. Erst wenn das stimmt: Stop, dann Ctrl+S")
