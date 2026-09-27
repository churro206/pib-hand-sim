"""
inspect_action_graph.py — Listet alle OmniGraph-Action-Graphs der aktuell offenen
Stage und deren Knoten (Pfad, Node-Type, wichtigste Attribute) auf.

Hintergrund: docs/handoff.md und docs/current-sprint.md widersprechen sich zum
Stand des Action Graphs in pib_upperbody_v5.usd (fertig verkabelt vs. noch
Blocker). Dieses Skript liest nur, ändert nichts — Ergebnis dient als Grundlage
für die Tendon-Dynamik-Arbeit (siehe tendondrive/PROMPT_sehnendynamik_isaac.md).

Schreibt die Ausgabe zusätzlich nach isaac_sim/tools/_action_graph_inventory.txt
(gitignored, wie isaac_sim/tools/_pose_dump.json) — Konsolenausgabe aus dem
Script Editor lässt sich schlecht kopieren, die Datei kann direkt gelesen werden.

v2: zeigt zusätzlich die tatsächlichen Attribut-Verbindungen (Exec- und
Daten-Pins) über reines pxr.Usd (UsdAttribute.GetConnections()) statt nur
Werte — ohne das weiß man nicht, WIE die Knoten verschaltet sind.

Im Script Editor ausführen, bei geöffneter pib_upperbody_v5.usd (Play-Zustand
egal).
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


_out_path = _find_project_root() / "isaac_sim" / "tools" / "_action_graph_inventory.txt"
_out_path.write_text(out.getvalue())
print(f"\nAusgabe geschrieben nach: {_out_path}")
