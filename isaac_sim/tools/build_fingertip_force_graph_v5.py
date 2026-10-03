"""
build_fingertip_force_graph_v5.py — bündelt die 10 Fingerspitzen-Kontaktkräfte von pib v5 auf
EIN zeitgestempeltes Topic, nur native Nodes (ADR-008-Nachtrag):

  ReadContact_<finger> ×10   isaacsim.sensors.physics.IsaacReadContactSensor (vorhanden, bleiben)
  FingertipForceArray        omni.graph.nodes.ConstructArray (arraySize 10, arrayType auto → float[])
      input0..input9 ← Reader.outputs:value   (Kraft in N, float)
  FingertipForceToDouble     omni.graph.nodes.ToDouble  (float[] → double[], JointState erwartet double)
  FingertipForceTime         isaacsim.core.nodes.IsaacTimeSplitter
      time ← ReadSimTime.outputs:simulationTime
  PublisherFingertipForces   isaacsim.ros2.bridge.ROS2Publisher, sensor_msgs/JointState
      execIn ← on_physics_step, name = 10 Fingernamen, effort ← FingertipForceToDouble.converted,
      header.stamp ← FingertipForceTime (Simulationszeit)
      topic = /pib/fingertip_forces

Verdrahtung des Publishers und arrayType werden DIREKT IN DIE USD geschrieben: über
og.Controller gesetzte Werte/Verbindungen landen nur im laufenden Graph, nicht in der Datei —
beim nächsten Neuaufbau aus der USD (Datei öffnen, Knoten umbenennen) verwirft der Publisher
seine dynamischen Eingänge ("remove dynamic attributes") und sendet leere Nachrichten.
Stehen sie in der USD, verwendet er sie beim Laden wieder ("reuse"). Nach dem Lauf deshalb:
speichern UND Stage neu öffnen.

ConstructArray wandelt float NICHT nach double (Log: "Mismatched array element type ...
expected 'double', got 'float'"), deshalb der ToDouble-Knoten. Existiert der Graph schon,
repariert das Skript nur die Verdrahtung (idempotent).

Ersetzt die Einzel-Publisher (PublishContact_<finger>, PublisherContactForces) und den alten
index_right-Reader (isaac_read_contact_sensor_node) — die werden gelöscht. Fehlende
ReadContact_<finger> werden angelegt.

Danach KEINE Knoten im Stage-Tree umbenennen/verschieben und keinen Compound bilden, ohne
vorher gespeichert und neu geöffnet zu haben: beides arbeitet auf dem laufenden Graph, der vom
USD-Stand abweichen kann — so entstand am 2026-10-03 ein Stand, der bei Play abstürzt.

Reader und Publisher hängen parallel am Trigger: der Publisher kann den Wert des vorigen
Physikschritts senden (1 Schritt Verzögerung) — bewusst, eine execOut-Kette würde abreißen,
weil execOut laut Node-Doku nur feuert, wenn der Sensor Daten hat.

Im Script Editor ausführen, bei geöffneter pib_upperbody_v5.usd, Simulation GESTOPPT.
Danach Stage SPEICHERN und NEU ÖFFNEN, start.py, Play, `ros2 topic echo /pib/fingertip_forces`.
Ausgabe (jeder Schritt OK/FEHLER + Attributliste des Publishers) nach
isaac_sim/tools/_fingertip_force_graph_build.txt (gitignored).
"""
import io
from pathlib import Path

import omni.graph.core as og
import omni.usd
import usdrt
from pxr import Gf, Sdf, Vt

stage = omni.usd.get_context().get_stage()
out = io.StringIO()

ROBOT = "/World/pib_upperbody_urdf_v5"
GRAPH = "/Graph/ROS_JointStates"
TRIGGER = f"{GRAPH}/on_physics_step.outputs:step"
CONTEXT = f"{GRAPH}/Context.outputs:context"
SIM_TIME = f"{GRAPH}/ReadSimTime.outputs:simulationTime"
ARRAY = "FingertipForceArray"
TO_DOUBLE = "FingertipForceToDouble"
TIME = "FingertipForceTime"
PUB = "PublisherFingertipForces"
TOPIC = "/pib/fingertip_forces"

# Reihenfolge = Reihenfolge in JointState.name/effort
FINGERTIPS = {
    "thumb_left": "urdf_thumb_tip",
    "index_left": "urdf_finger_tip",
    "middle_left": "urdf_finger_tip_2",
    "ring_left": "urdf_finger_tip_3",
    "pinky_left": "urdf_finger_tip_4",
    "thumb_right": "urdf_thumb_tip_2",
    "index_right": "urdf_finger_tip_5",
    "middle_right": "urdf_finger_tip_6",
    "ring_right": "urdf_finger_tip_7",
    "pinky_right": "urdf_finger_tip_8",
}
# Altlasten aus dem v4-Graph-Kopie / den Einzel-Topics — werden gelöscht. Der alte index_right-
# Reader zeigte im committeten Stand mit csPrim auf den Roboter-Wrapper (falsch), daher kein
# Wiederverwenden mehr: alle 10 Reader heißen einheitlich ReadContact_<finger>.
LEGACY_READERS = {"index_right": "isaac_read_contact_sensor_node"}
OLD_PUBLISHERS = ["PublisherContactForces"] + [f"PublishContact_{f}" for f in FINGERTIPS]
OLD_NODES = OLD_PUBLISHERS + list(LEGACY_READERS.values())


def emit(line: str = "") -> None:
    print(line)
    out.write(line + "\n")


def _find_project_root() -> Path:
    stage_file = Path(stage.GetRootLayer().realPath)
    for ancestor in [stage_file.parent, stage_file.parent.parent, stage_file.parent.parent.parent]:
        if (ancestor / "config" / "pib_hand_config_v4.py").is_file():
            return ancestor
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config_v4.py").is_file():
            return candidate
    raise FileNotFoundError("pib-hand-sim nicht gefunden.")


def _exists(node: str) -> bool:
    return bool(stage.GetPrimAtPath(f"{GRAPH}/{node}"))


def _step(label: str, fn) -> bool:
    try:
        fn()
        emit(f"  OK      {label}")
        return True
    except Exception as exc:  # noqa: BLE001
        emit(f"  FEHLER  {label}: {exc}")
        return False


def _set_pos(node: str, x: float, y: float) -> None:
    prim = stage.GetPrimAtPath(f"{GRAPH}/{node}")
    if prim:
        prim.CreateAttribute("ui:nodegraph:node:pos", Sdf.ValueTypeNames.Float2).Set(Gf.Vec2f(x, y))


def _inputs(node: str) -> list:
    return [a for a in og.Controller.node(f"{GRAPH}/{node}").get_attributes() if a.get_name().startswith("inputs:")]


def _connected(src: str, dst: str) -> bool:
    ups = og.Controller.attribute(dst).get_upstream_connections()
    return any(u.get_path() == src for u in ups)


def _connect_once(src: str, dst: str) -> None:
    if not _connected(src, dst):
        og.Controller.connect(og.Controller.attribute(src), og.Controller.attribute(dst))


def _reader_for(finger: str) -> str:
    return f"ReadContact_{finger}"


def _usd_attr(prim, name: str, vtype):
    attr = prim.GetAttribute(name)
    return attr if attr else prim.CreateAttribute(name, vtype, custom=True)


def _wire_output() -> None:
    """Array (auto) → ToDouble → effort, Reader → Array, Zeitstempel, Namen — direkt in der USD.
    Idempotent (Neubau und Reparatur). Wirkt erst nach Speichern + Neu-Öffnen der Stage."""
    keys = og.Controller.Keys
    if not _exists(TO_DOUBLE):
        _step("ToDouble anlegen", lambda: og.Controller.edit(GRAPH, {
            keys.CREATE_NODES: [(TO_DOUBLE, "omni.graph.nodes.ToDouble")]}))
    arr = stage.GetPrimAtPath(f"{GRAPH}/{ARRAY}")
    conv = stage.GetPrimAtPath(f"{GRAPH}/{TO_DOUBLE}")
    pub = stage.GetPrimAtPath(f"{GRAPH}/{PUB}")
    emit("5. Verdrahtung in die USD schreiben")
    _step("ConstructArray.arrayType = auto", lambda: arr.GetAttribute("inputs:arrayType").Set("auto"))
    for i, finger in enumerate(FINGERTIPS):
        reader = _reader_for(finger)
        _step(f"input{i} ← {reader}.value", lambda i=i, reader=reader: arr.GetAttribute(f"inputs:input{i}")
              .SetConnections([Sdf.Path(f"{GRAPH}/{reader}.outputs:value")]))
    _step("ToDouble.value ← array", lambda: conv.GetAttribute("inputs:value")
          .SetConnections([Sdf.Path(f"{GRAPH}/{ARRAY}.outputs:array")]))
    # Alle Felder von sensor_msgs/JointState als dynamische Eingänge (Namen/Typen laut Log von
    # OgnROS2Publisher "create dynamic attributes") — vollständig, damit der Publisher sie
    # beim Laden als passend erkennt und wiederverwendet
    fields = {
        "inputs:header:stamp:sec": Sdf.ValueTypeNames.Int,
        "inputs:header:stamp:nanosec": Sdf.ValueTypeNames.UInt,
        "inputs:header:frame_id": Sdf.ValueTypeNames.Token,
        "inputs:name": Sdf.ValueTypeNames.TokenArray,
        "inputs:position": Sdf.ValueTypeNames.DoubleArray,
        "inputs:velocity": Sdf.ValueTypeNames.DoubleArray,
        "inputs:effort": Sdf.ValueTypeNames.DoubleArray,
    }
    attrs = {}
    for name, vtype in fields.items():
        if _step(f"Publisher-Eingang {name}", lambda name=name, vtype=vtype: attrs.__setitem__(name, _usd_attr(pub, name, vtype))):
            pass
    _step("effort ← ToDouble.converted", lambda: attrs["inputs:effort"]
          .SetConnections([Sdf.Path(f"{GRAPH}/{TO_DOUBLE}.outputs:converted")]))
    _step("header:stamp:sec ← seconds", lambda: attrs["inputs:header:stamp:sec"]
          .SetConnections([Sdf.Path(f"{GRAPH}/{TIME}.outputs:seconds")]))
    _step("header:stamp:nanosec ← nanoseconds", lambda: attrs["inputs:header:stamp:nanosec"]
          .SetConnections([Sdf.Path(f"{GRAPH}/{TIME}.outputs:nanoseconds")]))
    _step("name = Fingernamen", lambda: attrs["inputs:name"].Set(Vt.TokenArray(list(FINGERTIPS))))
    _set_pos(TO_DOUBLE, 1100.0, 800.0)


def _diagnose() -> None:
    """Liest aus der USD — das ist der Stand, der gespeichert und beim Öffnen geladen wird."""
    emit("\nDiagnose (USD):")
    for node in (ARRAY, TO_DOUBLE, PUB):
        prim = stage.GetPrimAtPath(f"{GRAPH}/{node}")
        emit(f"  {node}")
        for attr in prim.GetAttributes():
            name = attr.GetName()
            if not name.startswith("inputs:") or name in ("inputs:execIn", "inputs:context"):
                continue
            conns = [str(c) for c in attr.GetConnections()]
            value = attr.Get() if not conns else None
            if conns or value not in (None, "", [], 0, 0.0):
                emit(f"    {name}  [{attr.GetTypeName()}]  " + (f"<- {conns[0]}" if conns else f"= {value}"))


def main() -> None:
    if not stage.GetPrimAtPath(GRAPH):
        emit(f"Graph {GRAPH} nicht gefunden — falsche Stage offen?")
        return
    if _exists(PUB):
        emit(f"{PUB} existiert schon — Reparatur-Modus")
        old = [n for n in OLD_PUBLISHERS if _exists(n)]
        if old:
            _step(f"{len(old)} alte Einzel-Publisher löschen", lambda: og.Controller.edit(
                GRAPH, {og.Controller.Keys.DELETE_NODES: [og.Controller.node(f"{GRAPH}/{n}") for n in old]}))
        _wire_output()
        _diagnose()
        return
    missing = [f for f, link in FINGERTIPS.items() if not stage.GetPrimAtPath(f"{ROBOT}/{link}/Contact_Sensor")]
    if missing:
        emit(f"ABBRUCH: Sensor-Prims fehlen für {missing} — erst build_contact_sensors_v5.py.")
        return
    keys = og.Controller.Keys

    emit("1. Altlasten entfernen (Einzel-Publisher, alter index_right-Reader)")
    old = [n for n in OLD_NODES if _exists(n)]
    if old:
        # Knoten-Objekte statt Pfad-Strings: edit(GRAPH, ...) stellt Strings den Graph-Pfad
        # voran ("/Graph/X//Graph/X/Node" → nicht gefunden)
        _step(f"{len(old)} Knoten löschen", lambda: og.Controller.edit(
            GRAPH, {keys.DELETE_NODES: [og.Controller.node(f"{GRAPH}/{n}") for n in old]}))
    else:
        emit("  keine vorhanden")

    emit("2. Reader zuordnen (vorhandene weiterverwenden)")
    readers = {}
    for finger, link in FINGERTIPS.items():
        name = f"ReadContact_{finger}"
        if _exists(name):
            readers[finger] = name
        else:
            sensor = f"{ROBOT}/{link}/Contact_Sensor"
            if _step(f"{name} anlegen", lambda name=name, sensor=sensor: og.Controller.edit(GRAPH, {
                keys.CREATE_NODES: [(name, "isaacsim.sensors.physics.IsaacReadContactSensor")],
                keys.SET_VALUES: [(f"{name}.inputs:csPrim", [usdrt.Sdf.Path(sensor)])],
                keys.CONNECT: [(TRIGGER, f"{name}.inputs:execIn")],
            })):
                readers[finger] = name
        emit(f"  {finger:<13} → {readers.get(finger, 'FEHLT')}")
    if len(readers) != len(FINGERTIPS):
        emit("ABBRUCH: nicht alle Reader vorhanden.")
        return

    emit("3. Array, Zeit, Publisher anlegen")
    if not _step("Knoten + Grundverbindungen", lambda: og.Controller.edit(GRAPH, {
        keys.CREATE_NODES: [(ARRAY, "omni.graph.nodes.ConstructArray"),
                            (TIME, "isaacsim.core.nodes.IsaacTimeSplitter"),
                            (PUB, "isaacsim.ros2.bridge.ROS2Publisher")],
        keys.SET_VALUES: [(f"{ARRAY}.inputs:arraySize", len(FINGERTIPS)),
                          (f"{ARRAY}.inputs:arrayType", "auto"),
                          (f"{PUB}.inputs:messagePackage", "sensor_msgs"),
                          (f"{PUB}.inputs:messageSubfolder", "msg"),
                          (f"{PUB}.inputs:messageName", "JointState"),
                          (f"{PUB}.inputs:topicName", TOPIC)],
        # Bestehende Knoten mit vollem Pfad (relative Namen nur für neu angelegte)
        keys.CONNECT: [(TRIGGER, f"{PUB}.inputs:execIn"),
                       (CONTEXT, f"{PUB}.inputs:context"),
                       (SIM_TIME, f"{TIME}.inputs:time")],
    })):
        return

    emit("4. ConstructArray: Eingänge input1..input9 + Reader verbinden")
    _step("dynamische Eingänge", lambda: og.Controller.edit(GRAPH, {
        keys.CREATE_ATTRIBUTES: [(f"{GRAPH}/{ARRAY}.inputs:input{i}", "any") for i in range(1, len(FINGERTIPS))]}))
    for i, (finger, reader) in enumerate(readers.items()):
        _step(f"{reader}.value → input{i} ({finger})", lambda reader=reader, i=i: og.Controller.connect(
            og.Controller.attribute(f"{GRAPH}/{reader}.outputs:value"),
            og.Controller.attribute(f"{GRAPH}/{ARRAY}.inputs:input{i}")))

    _wire_output()

    for i, reader in enumerate(readers.values()):
        _set_pos(reader, 600.0, 400.0 + 110.0 * i)
    _set_pos(ARRAY, 950.0, 800.0)
    _set_pos(TIME, 950.0, 600.0)
    _set_pos(PUB, 1250.0, 700.0)

    _diagnose()
    emit(f"\nFertig. Stage SPEICHERN, Stage NEU ÖFFNEN (File → Open), start.py, Play, "
         f"dann `ros2 topic echo {TOPIC}`.")
    emit("Optional im GUI: Reader, Array, Zeit, Publisher markieren → Rechtsklick → Make Compound.")


main()

_out_path = _find_project_root() / "isaac_sim" / "tools" / "_fingertip_force_graph_build.txt"
_out_path.write_text(out.getvalue())
print(f"\nAusgabe geschrieben nach: {_out_path}")
