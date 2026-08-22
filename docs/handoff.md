# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-08-22

### Zuletzt gearbeitet an

1. **JOINT_SIGN-Fix behoben (ADR-007, Commit `737ac2e`)**: `isaac_sim/tools/flip_joint_sign.py` dreht `localRot0`+`localRot1` aller 44 Gelenke symmetrisch um 180° um eine zur Gelenkachse senkrechte Achse — Vorzeichen umgekehrt, keine Geometrie bewegt. Script Node aus dem Action Graph entfernt, `JOINT_SIGN` aus `config/pib_hand_config.py` und Limit-Spiegelung aus `isaac_sim/setup_stage.py` entfernt.
2. **Verworfener Zwischenschritt**: URDF editieren + Isaac-Reimport (Weg 1) — Prämisse war falsch, Leon baut `pib_upperbody.usd` per Onshape-Importer direkt aus Onshape, nicht aus der URDF. Artefakte (`flip_urdf_for_isaac.py`, generierte URDF) wieder entfernt.
3. **Docs nachgezogen**: `CLAUDE.md`, `architecture.md`, `conventions.md`, `decisions.md` (ADR-007 neu, ADR-006 als überholt markiert), `current-sprint.md` — alle committed in `737ac2e`.
4. **Isaac-Sim-Crash während der Session behoben**: hängende `kit`-Prozesse gekillt, verwaiste Extension-Registry-Locks (`~/.local/share/ov/data/exts/v2/index/*/registry.lock`) und verwaiste `/dev/shm/sem.carbonite-sharedmemory` entfernt.

### Offene Punkte

- Contact-Sensor-Ansatz noch nicht entschieden: nativer `IsaacContactSensor`-Node vs. `ArticulationView.get_net_contact_forces()` in einem Script Node (Abwägung in `docs/architecture.md` → „Offen").
- Fingertip-Prim-Pfade in der USD noch nicht identifiziert — zuletzt bei Leon nachgefragt, ob er da schon reingeschaut hat, keine Antwort mehr erhalten vor Sessionende.
- Nicht bestätigt, ob Isaac Sim nach dem Crash-Fix (Punkt 4 oben) sauber wieder hochkommt — letzter Schritt vor `/handoff` war der Neustart-Versuch.
- Szenen-Erweiterung (welche Objekte, welche Anordnung) komplett offen, noch nicht angefangen.

### Nächste Schritte (in Reihenfolge)

1. Isaac Sim erfolgreich neu starten bestätigen (siehe Offene Punkte).
2. Fingertip-Prim-Pfade im Stage-Baum identifizieren (Isaac Sim UI, kein `inventory.py` mehr auf diesem Branch).
3. Contact-Sensor-Ansatz entscheiden (nativer Node vs. Script Node) und umsetzen.
4. Kontaktkräfte auf ROS2-Topic veröffentlichen (Name/Format noch offen).
5. Szenen-Erweiterung: weitere Objekte/Umgebung in `pib_upperbody.usd` ergänzen.

### Wichtige Kontextdetails

- **Leon will weniger Skill-Prozess-Overhead**: den vollen superpowers-Workflow (brainstorming → writing-plans → subagent-driven-development) nicht mehr standardmäßig für normale Fixes einsetzen — direkt/pragmatisch arbeiten, nur auf explizite Anfrage die volle Kette (siehe Memory `feedback_process-overhead.md`).
- **JOINT_SIGN-Fix-Mechanik**: Ein `PhysicsRevoluteJoint` speichert seine Achsrichtung über `localRot0`(Body0)/`localRot1`(Body1). Beide Seiten symmetrisch um dieselbe 180°-Rotation (senkrecht zur Gelenkachse) drehen kehrt das gemessene Vorzeichen um, ohne die Weltausrichtung der Achse zu ändern (Rotationskonjugation `F·M·F`: gleicher Winkel, aber am Ende Vorzeichen-invertiert relativ zur ursprünglichen Achse). **Nur eine Seite** zu drehen (z.B. nur `localRot1`) ist falsch — verschiebt die Weltachse, PhysX lässt beim nächsten Play die nachgeordnete Kette verspringen.
- **USD und URDF sind unabhängige Onshape-Exporte**: `isaac_sim/usd/pib_upperbody.usd` kommt vom Onshape-Importer direkt aus Onshape, NICHT aus `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` (die URDF wird nur für ros2_control/RViz gebraucht). Bei künftigem Onshape-Reimport: `flip_joint_sign.py` erneut gegen die neue Stage ausführen.
- **Zwei Body-Limits waren falsch geschätzt**: `dof_upper_arm_left`/`dof_shoulder_horizontal_right` waren in `setup_stage.py` symmetrisch `[-90°,90°]` geraten, echte Onshape-Quelle ist `[0°,90°]` — jetzt korrigiert (gegen `ros2_ws/src/pib_description/urdf/pib_upperbody.urdf` verifiziert).
- **`start.py`/`setup_stage.py` bleiben nötig** — PhysX cached Drive-Stiffness/Damping nicht zwischen Sessions.
- **`ros2_ws/install/setup.bash`** muss in jeder Shell explizit gesourced werden — `cd` allein ändert `AMENT_PREFIX_PATH` nicht.
