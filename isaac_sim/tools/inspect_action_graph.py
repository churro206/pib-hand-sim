"""
inspect_action_graph.py — Listet alle OmniGraph-Action-Graphs der offenen Stage mit ihren
Knoten, Attributwerten, tatsächlichen Verbindungen (Exec- und Daten-Pins) und Relationships
auf, dazu alle ContactSensor-Prims der Stage und welche Relationships auf sie zeigen.
Ändert nichts.

Gedacht als Grundlage für die Contact Sensors (ADR-008): einmal auf v4 ausführen (dort ist
index_right verifiziert = Referenzverkabelung), einmal auf v5.

Schreibt nach isaac_sim/tools/_action_graph_inventory_<stage>.txt (gitignored).
Im Script Editor ausführen, Play-Zustand egal.
"""
import io
from pathlib import Path

import omni.usd

stage = omni.usd.get_context().get_stage()
out = io.StringIO()


def emit(line: str = "") -> None:
    print(line)
    out.write(line + "\n")


emit(f"Stage: {stage.GetRootLayer().realPath}\n")

graph_prims = [p for p in stage.Traverse() if p.GetTypeName() == "OmniGraph"]

if not graph_prims:
    emit("Keine Prims vom Typ 'OmniGraph' gefunden.")
else:
    for gp in graph_prims:
        emit(f"=== Action Graph: {gp.GetPath()} ===")
        for node in gp.GetChildren():
            emit(f"  {node.GetPath()}  [{node.GetTypeName()}]")
            for attr in node.GetAttributes():
                name = attr.GetName()
                if not (name.startswith("inputs:") or name.startswith("outputs:") or name.startswith("state:")):
                    continue
                conns = attr.GetConnections()
                if conns:
                    emit(f"      {name} <- {[str(c) for c in conns]}")
                    continue
                if not name.startswith("inputs:"):
                    continue
                try:
                    value = attr.Get()
                except Exception as exc:  # noqa: BLE001 — reine Diagnoseausgabe
                    value = f"<Fehler: {exc}>"
                if value in (None, "", [], 0.0):
                    continue
                emit(f"      {name} = {value!r}")
            # Relationships (z.B. targetPrim, oder ein evtl. csPrim/sensorPrim-Bezug
            # eines Contact-Sensor-Read-Nodes) — GetAttributes() oben sieht diese NICHT.
            for rel in node.GetRelationships():
                targets = rel.GetTargets()
                if targets:
                    emit(f"      {rel.GetName()} (rel) -> {[str(t) for t in targets]}")
        emit()

# ── ContactSensor-Prims (ganze Stage, nicht nur Action-Graph-Kinder) ──────────
# ADR-008: "nativer IsaacContactSensor-Prim" — Typname hier bewusst als String-
# Vergleich (kein Schema-Import), um nichts über die tatsächliche Isaac-Sim-API
# zu raten; "contactsensor" case-insensitive als Substring, falls die exakte
# Schreibweise abweicht.
emit("=== ContactSensor-Prims (ganze Stage) ===")
sensor_prims = [p for p in stage.Traverse() if "contactsensor" in p.GetTypeName().lower()]
if not sensor_prims:
    emit("Keine Prims gefunden, deren TypeName 'contactsensor' enthält.")
else:
    for sp in sensor_prims:
        emit(f"  {sp.GetPath()}  [{sp.GetTypeName()}]  Parent: {sp.GetParent().GetPath()}")
        for attr in sp.GetAttributes():
            name = attr.GetName()
            try:
                value = attr.Get()
            except Exception as exc:  # noqa: BLE001 — reine Diagnoseausgabe
                value = f"<Fehler: {exc}>"
            if value in (None, "", [], 0.0):
                continue
            emit(f"      {name} = {value!r}")
emit()

# Welche Nodes/Relationships zeigen auf einen der obigen Sensor-Prims?
if sensor_prims:
    sensor_paths = {sp.GetPath() for sp in sensor_prims}
    emit("=== Relationships, die auf einen ContactSensor-Prim zeigen ===")
    for prim in stage.Traverse():
        for rel in prim.GetRelationships():
            targets = set(rel.GetTargets())
            hit = targets & sensor_paths
            if hit:
                emit(f"  {prim.GetPath()}.{rel.GetName()} -> {[str(t) for t in hit]}")
    emit()

emit("Fertig.")


def _find_project_root() -> Path:
    # __file__ ist im Script Editor nicht definiert (exec-Kontext) — Root wie in
    # setup_stage.py stattdessen von der offenen Stage aus suchen.
    stage_file = Path(stage.GetRootLayer().realPath)
    for ancestor in [stage_file.parent, stage_file.parent.parent, stage_file.parent.parent.parent]:
        if (ancestor / "config" / "pib_hand_config_v4.py").is_file():
            return ancestor
    for candidate in [Path.home() / "repos" / "pib-hand-sim", Path.home() / "pib-hand-sim"]:
        if (candidate / "config" / "pib_hand_config_v4.py").is_file():
            return candidate
    raise FileNotFoundError("pib-hand-sim nicht gefunden.")


_out_path = (_find_project_root() / "isaac_sim" / "tools"
             / f"_action_graph_inventory_{Path(stage.GetRootLayer().realPath).stem}.txt")
_out_path.write_text(out.getvalue())
print(f"\nAusgabe geschrieben nach: {_out_path}")
