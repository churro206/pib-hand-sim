# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-04

### Zuletzt gearbeitet an

1. **Branch neu aufgesetzt**: `feature/rl-grasping` = Mimic-/Servo-Stand + RL (alter Stand im Tag `backup/rl-grasping-c0b3f6d`, force-pushed); `docs/rl-grasping-notes.md` übernommen.
2. **Hand-only-Asset + Handgelenk-Pleuel** (ADR-014): `pib_hand_left_urdf_v5/` → `isaac_sim/usd/pib_hand_left_v5.usd` (`bake_hand_asset_v5.py`); Handgelenk [−60°, 0°], `WRIST_LINKAGE`/`wrist_transmission()` in `config/pib_hand_config_v5.py`, Isaac Lab `RemotizedPDActuatorCfg`.
3. **Vollroboter-Absturz behoben**: Compound-Subgraph mit allen ReadContact-Knoten steckte seit `b6b414d` in `pib_upperbody_v5.usd` → offline entfernt, Graph flach neu gebaut (ADR-013-Korrektur); Filtered Pairs Unterarm ↔ Daumen-Rotator in beiden USDs.
4. **RL-Proof-of-Concept** (ADR-015): Isaac Lab 2.3.2 in conda `env_isaaclab`; `isaac_lab/pib_grasp/` nach Dexsuite; Machbarkeitstest (Rotator 90° → 14–15/16); Probelauf 300 It.: Dose fällt 100 % → 19 %, Gegengriff 0 → 0,38; ONNX exportiert.

### Offene Punkte

- **Policy gelernt, Inferenz sieht gut aus** (Video `videos/isaac_lab_pib_hand_inference_test.webm`), aber: sie **dreht den Unterarm**, bis die Dose über der Handfläche liegt — ungewollt (ein Wasserglas würde verschüttet).
- ~6 % der Episoden: Dose fliegt beim Reset weg (Daumen in Opposition + gebeugt überlappt die Dose).
- Kurve flacht ab Iteration ~175 ab; längeres Training und Belohnungsfeinschliff offen.
- Sim-to-Real-Lücken: lineare Kopplung, idealisierte FSR, keine Latenz, Gains/Armature geschätzt, int8 ungeprüft (ADR-015).
- 5 Commits nicht gepusht (`567fe46`…`1821896`) + Doku-Commit dieser Session.

### Nächste Schritte (in Reihenfolge)

1. Unterarmdrehung unterbinden — mit Leon entscheiden: `forearm_left` aus dem Aktionsraum nehmen (IK stellt die Hand), oder Strafe auf Abweichung von der Startlage / Neigung der Dose (Belohnung „aufrecht“).
2. Reset-Überlappung prüfen/entschärfen (Daumen-MCP-Startbereich in `env_cfg.py` → `reset_hand` verkleinern).
3. Längeres Training (z. B. 1500 It., TensorBoard), Ergebnis mit `play.py` zeigen.
4. M2: ONNX → int8 (QDQ, Kalibrierdaten aus Sim-Rollouts) → in der Sim gegen float bewerten → `stedgeai validate` auf dem NUCLEO-N657X0.
5. Für M3: Servo-Sprungantwort an der echten Hand messen, Aktionsverzögerung randomisieren (Spot: 0–4 Schritte), FSR-Kennlinie vom Kollegen.

### Wichtige Kontextdetails

- **Isaac Lab nur in `conda activate env_isaaclab`**, Projekt-`.venv` vorher `deactivate` — `isaaclab.sh` nimmt die aktive Python; Isaac Sims Python darf nur `pip`, `setuptools`, `psutil` 5.9.8, `starlette` 0.45.3 enthalten.
- **Handgelenk-Vorzeichen-Ausnahme**: −60° = nach innen gebeugt, 0° = gestreckt (fremde Konvention, bewusst nicht geflippt).
- **ContactSensor mit Objekt-Filter nur 1 Prim pro Sensor** → `fsr_thumb`…`fsr_pinky`; FSR-Reihenfolge Daumen, Zeige, Mittel, Ring, klein.
- **Compound im Action Graph = Absturz bei Play** im `isaacsim.sensors.physics`-Plugin, auch bei deaktiviertem Graph; prüfen über Prims mit „compound“ im Pfad.
- **Leon will zusehen**: Tests mit Fenster (`--real_time`), nur ein Isaac-Fenster gleichzeitig (8 GB VRAM); vorher prüfen, ob ein altes Fenster noch GPU hält.
- `~/.bashrc` setzt `ROS_DOMAIN_ID=1` — Isaac publiziert auf 0, in ROS-Terminals `export ROS_DOMAIN_ID=0`.
- Arbeitsweise: langsam, nach Teilschritten Zwischenstand; NVIDIA-Best-Practices per WebSearch prüfen und nennen.
- Zukunft: Jetson Thor im Roboter — skizziert: modular (FoundationPose, GraspGen, cuMotion) + Finger-Policy als Reflex, später GR00T N1.6.
