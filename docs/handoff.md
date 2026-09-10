# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-09-06

### Zuletzt gearbeitet an

1. **v4/v5-Namensschema repo-weit durchgezogen**: `isaac_sim/usd/pib_upperbody.usd` → `pib_upperbody_v4.usd`, `config/pib_hand_config.py` → `pib_hand_config_v4.py`, `pib_upperbody_urdf/` → `pib_upperbody_urdf_v4/`, `ros2_ws/src/pib_description/` → `pib_description_v4/`. Dabei gefunden: `pib_upperbody.usd` war seit ADR-007 stale — der echte v4-Stand (Contact-Sensor-Rebuild + Tisch/Korb/Tasse) lag in `pib_upperbody_contact_sensors_assets.usd`, das ist jetzt `pib_upperbody_v4.usd`.
2. **v5-Hand-URDF importiert und in die Szene eingepflegt**: `isaac_sim/usd/pib_upperbody_v5.usd` = Kopie von v4, alter Roboter-Prim gelöscht, v5-URDF (`pib_upperbody_urdf_v5/robot.urdf`) reinimportiert (Convex Hull, Static Base, Instanceable aus), Tisch/Korb/Tasse aus v4 übernommen.
3. **`isaac_sim/setup_stage.py` gefixt** (gilt für v4 und v5): `configure_drives()` setzt jetzt `physics:maxForce=inf` auf allen Drives (Isaac-Importer hatte für v5 den URDF-`effort`-Wert als Kappung übernommen, 10 Nm an der Schulter reichte nicht gegen die Trägheit). `set_initial_pose()` setzt alle Targets auf 0° (Ellbogen-30°-Sonderfall entfernt, war nie begründet).
4. Nach dem maxForce-Fix schwangen manche v5-Gelenke — Ursache war **Self-Collision**, nicht Damping/Solver. Deaktiviert auf `root_joint` (v5s Articulation Root sitzt dort, nicht auf dem Wrapper-Xform wie bei v4). Alles committed (`877f714`) und gepusht.

### Offene Punkte

- `config/pib_hand_config_v5.py` fehlt noch — DOF-Namen liegen aus der URDF vor, aber Limits/`ROBOT_PRIM_PATH`/Drive-Werte müssen gegen die echte Isaac-Stage verifiziert werden, nicht aus der URDF übernommen.
- `ros2_ws/src/pib_description_v5/` fehlt — die v4-URDF hat 8 handgepflegte `<ros2_control>`-Tags gegenüber dem rohen Export, kein reiner Kopiervorgang.
- Action Graph und Contact Sensors sind für v5 noch nicht verkabelt.
- ADR-009 noch nicht geschrieben (v5-Reimport-Entscheidung, `_v4`/`_v5`-Schema, maxForce-/Self-Collision-Fund) — Leon wollte das bewusst erst nach dem Einpflegen machen.

### Nächste Schritte (in Reihenfolge)

1. Test-Trajektorien für v5 aufnehmen (`dump_pose.py`-Workflow, analog zu v4).
2. Contact Sensors für v5 verkabeln (`index_right`-Muster aus ADR-008) — `SetInstanceable(False)` vermutlich **nicht** nötig, da Instanceable beim v5-Import schon deaktiviert war, aber gegenprüfen.
3. Action Graph für v5 aufbauen (`ROS2SubscribeJointState`/`IsaacArticulationController`/`ROS2PublishJointState`) — `targetPrim` **muss** auf `root_joint` zeigen, nicht auf den Wrapper-Xform (anders als bei v4).
4. `config/pib_hand_config_v5.py` schreiben — Voraussetzung für `set_joint_limits()`/`set_initial_pose()` mit v5-Namen und für die ros2_control-Seite.

### Wichtige Kontextdetails

- **v5-Joint-Namen bewusst ohne `dof_`-Präfix gelassen** (Onshape-Assembly-Konvention, kein Re-Export nur für Namensangleich, Leons Entscheidung) — Daumen-Mittelgelenk heißt `tip` statt `distal` wie bei v4. Nie versuchen anzugleichen.
- **v5s Articulation Root sitzt auf `root_joint`** (ein `PhysicsFixedJoint`-Prim), nicht auf dem Wrapper-Xform wie bei v4 — anderes, aber gültiges Muster des neueren Isaac-URDF-Importers. Beim Action-Graph-Verkabeln unbedingt beachten.
- **Instanceable beim v5-Import deaktiviert** → der ADR-008-Stolperstein (`SetInstanceable(False)` pro Fingerspitze nötig für Contact Sensors) entfällt für v5 komplett, war für v4 nötig.
- **maxForce=inf gilt jetzt für v4 und v5 gleichermaßen** (`configure_drives()` ist rein namens-generisch, kein Config-Bezug) — v4 lief nur zufällig nie in den Bug, weil dort nie explizit ein `maxForce` gesetzt wurde (USD-Schema-Default ist `inf`).
- **`isaac_sim/usd/configuration/`** (neu im Repo) ist eine Live-Dependency von `pib_upperbody_v5.usd` (Isaac-Importer-Sublayer-Struktur, ähnlich `pib_upperbody_urdf_v5/robot/configuration/`) — nicht löschen/verschieben, ohne die USD vorher zu flattenen.
- Schwing-Debugging-Reihenfolge fürs nächste Mal: **maxForce-Kappung → Self-Collision → Solver-Iterationen → Damping-Retuning**, in dieser Priorität (billigster/nicht-invasivster Test zuerst).
