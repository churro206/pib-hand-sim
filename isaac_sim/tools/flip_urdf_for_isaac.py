"""
flip_urdf_for_isaac.py — Erzeugt eine Isaac-Import-Variante der URDF mit
umgedrehter Vorzeichen-Konvention für revolute Gelenke.

Hintergrund: Onshape/URDF und Isaacs importierte Gelenkachsen sind für alle
44 DOFs vorzeicheninvertiert (siehe docs/decisions.md). Statt das zur
Laufzeit zu kompensieren (Script Node im Action Graph), wird hier eine
abgeleitete URDF erzeugt, deren <axis>-Vektoren negiert und deren <limit>
lower/upper vertauscht+negiert sind. Isaac importiert daraus direkt in
Onshape-Konvention.

Die kanonische ros2_ws/src/pib_description/urdf/pib_upperbody.urdf bleibt
UNVERÄNDERT (weiterhin Onshape-Konvention für ros2_control/IK-Team/RViz).
Diese Datei hier wird NUR für den Isaac-Reimport verwendet (Mesh-Referenzen
sind package://pib_description/... — ortsunabhängig, solange ros2_ws gebaut
und gesourced ist).

Bei jedem Onshape-Re-Export: dieses Skript erneut laufen lassen, dann den
Isaac-Reimport wiederholen (siehe
docs/superpowers/plans/2026-08-22-joint-sign-fix.md, Tasks 3-6).

Aufruf: python3 isaac_sim/tools/flip_urdf_for_isaac.py
"""
import xml.etree.ElementTree as ET
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = _ROOT / "ros2_ws/src/pib_description/urdf/pib_upperbody.urdf"
TARGET = _ROOT / "isaac_sim/urdf/pib_upperbody_isaac_import.urdf"

# Referenzwerte zur Selbstprüfung (aus dem Onshape-Export, radiant).
# (axis_danach, lower_danach, upper_danach)
_EXPECTED = {
    "dof_elbow_right":               ([1.0, -0.0, 1.22465e-16], -1.5708, 0.785398),
    "dof_wrist_right":               ([1.0, -5.48963e-16, -0.0], -1.5708, -0.0),
    "dof_index_right_proximal":      ([1.0, -0.0, -0.0], -1.5708, -0.0),
    "dof_shoulder_horizontal_right": ([-0.0, 1.0, -0.0], -1.5708, -0.0),
}


def flip_urdf(source: Path, target: Path) -> int:
    """Negiert axis + vertauscht/negiert limit für alle revolute Joints."""
    tree = ET.parse(source)
    root = tree.getroot()
    count = 0
    for joint in root.findall("joint"):
        if joint.get("type") != "revolute":
            continue
        axis_el = joint.find("axis")
        limit_el = joint.find("limit")
        if axis_el is None or limit_el is None:
            continue

        xyz = [float(v) for v in axis_el.get("xyz").split()]
        axis_el.set("xyz", " ".join(repr(-v) for v in xyz))

        lower = float(limit_el.get("lower"))
        upper = float(limit_el.get("upper"))
        limit_el.set("lower", repr(-upper))
        limit_el.set("upper", repr(-lower))

        count += 1

    tree.write(target, xml_declaration=True, encoding="UTF-8")
    return count


def _selfcheck(target: Path) -> None:
    tree = ET.parse(target)
    root = tree.getroot()
    joints = {j.get("name"): j for j in root.findall("joint")}
    for name, (axis_after, lo_after, up_after) in _EXPECTED.items():
        joint = joints[name]
        axis = [float(v) for v in joint.find("axis").get("xyz").split()]
        limit = joint.find("limit")
        lower = float(limit.get("lower"))
        upper = float(limit.get("upper"))
        assert all(abs(a - b) < 1e-6 for a, b in zip(axis, axis_after)), \
            f"{name}: axis {axis} != erwartet {axis_after}"
        assert abs(lower - lo_after) < 1e-6, f"{name}: lower {lower} != erwartet {lo_after}"
        assert abs(upper - up_after) < 1e-6, f"{name}: upper {upper} != erwartet {up_after}"
        print(f"OK  {name}: axis={axis} limit=[{lower:.4f},{upper:.4f}]")


if __name__ == "__main__":
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    n = flip_urdf(SOURCE, TARGET)
    print(f"{n} revolute Gelenke transformiert -> {TARGET}")
    assert n == 44, f"Erwartet 44 revolute Gelenke, gefunden {n}"
    _selfcheck(TARGET)
    print("Selfcheck OK")
