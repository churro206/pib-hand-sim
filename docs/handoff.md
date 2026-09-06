# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-09-06

### Zuletzt gearbeitet an

1. **`isaac_sim/tools/dump_pose.py` neu**: liest Drive-Targets (Grad, Onshape-Konvention) der aktuell posierten Gelenke und hängt sie als Waypoint an `isaac_sim/tools/_pose_dump.json` an (gitignored) — Vorstufe für neue `test_client_*.py`-Sequenzen, da Copy-Paste aus der Isaac-Sim-Konsole nicht zuverlässig funktioniert.
2. **`_find_root()`-Bug in `dump_pose.py` behoben**: prüfte nur 2 Eltern-Ebenen der offenen USD, Repo-Root liegt aber 3 Ebenen über `isaac_sim/usd/*.usd` — jetzt `f.parents` (alle Ebenen). **`isaac_sim/start.py` hat denselben Bug noch, unverändert** (fällt dort bisher unbemerkt auf den Home-Verzeichnis-Fallback zurück).
3. **Szenen-Erweiterung**: Tisch-Prop als statischer Collider fixiert (`RigidBodyAPI` entfernt, nur `CollisionAPI` behalten — Asset-Browser-Möbel bringen oft eine dynamische `RigidBodyAPI` mit, die zum „Wegfliegen" führte), Korb mit Griffen + Tasse als Greif-Testobjekte ergänzt. Committed in `d11e9b9`.
4. **`isaac_sim/tools/make_object_variant.py` verworfen**: sollte Korb/Teller per USD-VariantSet austauschbar machen, war fertig implementiert (Container-Prim + `create_container`/`add_variant`/`set_default_variant`), Leon hat es aber vor Umsetzung wieder verworfen — nicht mehr auf der Platte.
5. Zwei Commits: `cdd135d` (dump_pose.py + `.gitignore`), `d11e9b9` (USD-Szene Tisch/Korb/Tasse — Commit-Message ist meine Interpretation aus dem Gespräch, da USD binär ist und nicht diffbar; ggf. gegenprüfen).

### Offene Punkte

- **Noch keine echten Pose-Sequenzen aufgenommen** — `dump_pose.py` ist gebaut und lief testweise, aber `_pose_dump.json` enthält noch keine vollständige Waypoint-Serie für eine neue Sequenz (z.B. Teller/Korb greifen).
- Objekt-Austausch (Korb↔Teller) bewusst zurückgestellt — offen, ob später doch per VariantSet (Ansatz war valide, nur verworfen wegen Zeitdruck) oder einfach manuell in der Stage getauscht wird.
- `start.py`s `_find_root()` hat denselben Ebenen-Bug wie `dump_pose.py` vor dem Fix — noch nicht behoben, Leon wollte das ggf. separat entscheiden.
- Kurzzeitig `Simulation view object is invalidated and cannot be used again to call getSharedMetatype` beim Play — verschwand nach Isaac-Sim-Neustart, Root Cause nicht verifiziert (Verdacht: Nachwirkung der Contact-Sensor-Instanceable-Chirurgie aus einer früheren Session, siehe ADR-008, oder der dort nie bestätigte saubere Neustart).
- Contact Sensors unverändert: nur `index_right` verkabelt, restliche 9 Fingerspitzen offen (siehe `docs/current-sprint.md`).

### Nächste Schritte (in Reihenfolge)

1. Mit `dump_pose.py` eine erste vollständige Waypoint-Sequenz für ein neues Testobjekt aufnehmen (Label+Zeit pro Waypoint in der Datei), dann daraus `test_client_<name>.py` nach Pickup/Putdown-Muster bauen lassen.
2. Entscheiden, ob/wie Objekt-Austausch (Korb/Teller) doch noch umgesetzt wird, oder ob Szenen-Erweiterung erstmal ohne Swap-Mechanik weiterläuft.
3. Restliche 9 Fingerspitzen für Contact Sensors verkabeln (ADR-008-Muster: `SetInstanceable(False)` je Link, `IsaacContactSensor`-Prim, zwei Action-Graph-Nodes).
4. Optional: `_find_root()`-Fix aus `dump_pose.py` auch in `start.py` nachziehen.

### Wichtige Kontextdetails

- **`dump_pose.py`-Mechanik**: liest `UsdPhysics.DriveAPI.Get(prim, "angular").GetTargetPositionAttr()` — dasselbe Attribut, das `setup_stage.set_initial_pose()` schreibt, also Onshape-Konvention (Grad), kein JOINT_SIGN mehr nötig (ADR-007 gilt weiter).
- **Copy-Paste aus der Isaac-Sim-Konsole ist unzuverlässig** — deshalb schreibt `dump_pose.py` direkt in eine Datei (`isaac_sim/tools/_pose_dump.json`, gitignored), die Claude liest statt Konsolen-Output zu parsen.
- **Drive-Targets/Pose zurücksetzen ohne Neustart**: `start.py` im Script Editor erneut ausführen (setzt alle Gelenke auf 0°, Ellbogen auf 30°) — für exakt 0° überall notfalls Ellbogen manuell per `DriveAPI.GetTargetPositionAttr().Set(0.0)` nachziehen.
- **Objekt versehentlich umgekippt/verschoben**: erst Stop→Play probieren (verwirft den Session-Layer-Zustand, Objekt springt auf zuletzt gespeicherte authored Pose zurück) — funktioniert nicht, wenn zwischendurch mit Ctrl+S gespeichert wurde.
- **Statische Props**: Asset-Browser-Möbel (z.B. der Tisch) kommen oft mit dynamischer `RigidBodyAPI` — für fixe Umgebungsobjekte diese entfernen, nur `CollisionAPI` behalten, sonst "fliegt" das Objekt bei Kollisionen weg.
- **Leon macht öfter kurze Pausen mitten in der Arbeit** — Session kann mit unfertigem Zwischenstand enden (wie hier: Pose-Dump-Tooling fertig, aber noch keine echte Sequenz aufgenommen).
