# Sprint — `feature/rl-grasping`

Seit 2026-10-04 Arbeitsbranch: `feature/rl-grasping` = Stand von
`experiment/omnigraph-lightweight` (digitaler Zwilling v5) plus RL-Greifen in Isaac Lab
(Abschnitt „RL-Greifen“ unten, ADR-015). Die übrigen Abschnitte sind die Historie des
Omnigraph-Sprints. Alte Sprints/Ziele (Simulation Server, Team-Integration, LSTM-Training)
verworfen — voller Fahrplan dazu auf `feature/ros2-control`.

## OmniGraph-Migration ✓

- [x] `pib_bridge.py` durch Action Graph ersetzt (`ROS2SubscribeJointState` → Script Node
      [JOINT_SIGN] → `IsaacArticulationController`, Rückweg über `ROS2PublishJointState`)
- [x] `robot_io.py`, `runner.py`, `_launch_helper.py`, `control/`, Sequenz-Pipeline,
      LSTM-Pipeline, 11 alte USD-Dateivarianten entfernt (ADR-006)
- [x] `test_client_pickup.py` — Pickup-Demo, verifiziert über `FollowJointTrajectory`
- [x] `test_client_putdown.py` — exakte Umkehrung, verifiziert
- [x] `start.py`/`setup_stage.py` behalten (Drive/Limit-Setup läuft weiterhin pro Session)
- [x] Docs (`CLAUDE.md`, `architecture.md`, `conventions.md`, `decisions.md`) an diesen
      Branch angepasst

## Vorzeichen-Fix ✓

- [x] Ursache identifiziert: Onshape und Isaacs importierte Gelenkachsen vorzeicheninvertiert
- [x] Behoben direkt an den Gelenk-Prims (`isaac_sim/tools/flip_joint_sign.py`, ADR-007) —
      kein Script Node/`JOINT_SIGN` mehr, Ist-Werte-Kompromiss aus ADR-006 miterledigt
- [x] `config/pib_hand_config_v4.py`/`isaac_sim/setup_stage.py` angepasst
- [x] Pickup-/Putdown-Demo als Regressionscheck verifiziert

## Contact Sensors ✓ (v5)

**Ziel**: Kontaktkräfte pro Fingertip, für Greif-Erkennung nutzbar.

- [x] Entscheidung: nativer `IsaacContactSensor`-Node (nicht `ArticulationView`-Tensor-API),
      siehe ADR-008
- [x] `index_right` verkabelt und verifiziert (v4): `IsaacContactSensor`-Prim + `Isaac Read
      Contact Sensor Node` + generischer `ROS2 Publisher`-Node (`std_msgs/Float32`) auf
      `/pib/fingertip_force/index_right` — Kraftwerte kommen korrekt an (~1-2 N beim
      Greifen der Testdose)
- [x] v5: alle 10 Fingerspitzen — Sensor-Prims (`build_contact_sensors_v5.py`), 10 Reader,
      gebündelt als `sensor_msgs/JointState` mit Zeitstempel auf `/pib/fingertip_forces`
      (`build_fingertip_force_graph_v5.py`, ADR-013); verifiziert an der Dose (Daumen ≈42 N,
      Zeige ≈25 N, Mittel ≈16 N, Ring ≈2 N)
- [x] Absturz bei Play behoben (2026-10-04): ein Compound-Subgraph mit allen Reader-Knoten
      steckte doch in der committeten USD — entfernt, Knoten flach neu gebaut (ADR-013,
      Korrektur zu Fallstrick 3); jetzt wirklich stabil nach Speichern + Neu-Öffnen
- [x] ~~Contact-Knoten als Compound zusammenfassen~~ — verworfen: Compound löst den Absturz
      aus (ADR-013, Fallstrick 3)
- [ ] v4: restliche 9 Fingerspitzen — v4 vorerst nicht weiterverfolgt

## Szenen-Erweiterung ← aktuell

**Ziel**: Weitere Objekte/Umgebung in `isaac_sim/usd/pib_upperbody_v4.usd`.

- [x] Tisch (fixierter Collider, `RigidBodyAPI` entfernt), Korb (mit Griffen), Tasse als
      Greif-Testobjekte ergänzt (Commit `d11e9b9`)
- [ ] Objekt-Austausch (Korb/Teller) — VariantSet-Ansatz war fertig implementiert
      (`isaac_sim/tools/make_object_variant.py`), aber verworfen; offen ob später doch
      umgesetzt oder Objekte manuell in der Stage getauscht werden

## v5-Hand-Integration ← neu

**Ziel**: v5-Hand (neue Onshape-Baugruppe, per `onshape-to-robot` als URDF exportiert und in
Isaac importiert) läuft **dauerhaft parallel** zu v4, nicht als Ablösung. v5-Gelenknamen
bleiben unverändert (kein `dof_`-Präfix, kein Onshape-Re-Export nur für den Namensabgleich).

**Repo-Struktur** (`_v4`/`_v5`-Schema durchgängig gezogen, dieser Session):
- [x] `isaac_sim/usd/pib_upperbody.usd` → `pib_upperbody_v4.usd` — dabei aufgefallen: die
      Datei war seit `737ac2e` (ADR-007) nicht mehr aktuell; der tatsächlich aktuelle Stand
      (Contact-Sensor-Rebuild + Tisch/Korb/Tasse aus `d11e9b9`) lag in
      `pib_upperbody_contact_sensors_assets.usd` — das ist jetzt `pib_upperbody_v4.usd`.
      Die beiden veralteten Dateien (`pib_upperbody.usd`, `pib_upperbody_contact_sensors.usd`)
      sind aus dem Baum entfernt (Git-Historie behält sie)
- [x] `config/pib_hand_config.py` → `pib_hand_config_v4.py`, alle Loader-Referenzen
      (`start.py`, `setup_stage.py`, `autostart.py`, `isaac_sim/tools/*.py`) nachgezogen
- [x] `pib_upperbody_urdf/` → `pib_upperbody_urdf_v4/`; `pib_upperbody_urdf_v5/` eingecheckt
      (roher `onshape-to-robot`-Export)
- [x] `ros2_ws/src/pib_description/` → `pib_description_v4/` (Package-Name in
      `package.xml`/`CMakeLists.txt`, `package://`-Mesh-Pfade in der URDF, sowie
      `pib_bringup`s `exec_depend`/Launch-Referenz mitgezogen)

**v5 in die Szene eingepflegt** (Kopie von `pib_upperbody_v4.usd`, alter Roboter-Prim
gelöscht, v5-URDF importiert, `targetPrim` des Action Graphs zeigt weiter — siehe Ablauf
weiter oben in dieser Session):
- [x] `isaac_sim/usd/pib_upperbody_v5.usd` — v5-Roboter + Tisch/Korb/Tasse aus v4 übernommen,
      Convex Hull/Static Base/Instanceable-aus beim Import gesetzt (ADR-008-Stolperstein damit
      von vornherein vermieden, nicht nachträglich pro Fingerspitze gefixt)
- [x] Drive-Bug gefunden und gefixt (`isaac_sim/setup_stage.py`): Isaac-URDF-Importer hatte
      `physics:maxForce` aus dem URDF-`effort`-Wert übernommen (10 Nm an der Schulter — real
      gebraucht werden dort deutlich mehr), v4 hatte nie ein maxForce gesetzt (Schema-Default
      `inf`). `configure_drives()` setzt jetzt explizit `maxForce=inf` auf allen Drives —
      stellt für v4 und v5 einheitlich den unbegrenzten Zustand her, kein geratener Nm-Wert
- [x] `set_initial_pose()`: alle Targets auf 0° (T-Pose), Ellbogen-Sonderfall (30°) entfernt
      — war nie begründet, jetzt einheitlich für v4/v5
- [x] Schwingen an manchen v5-Gelenken nach dem maxForce-Fix aufgetreten — Ursache gefunden:
      **Self-Collision**, nicht Damping/Solver. Articulation Root sitzt bei v5 auf `root_joint`
      (PhysicsFixedJoint, nicht auf dem Wrapper-Xform wie bei v4 — anderes, aber gültiges
      Importer-Muster). Self-Collisions dort deaktiviert, behoben. **Wichtig für später**:
      `IsaacArticulationController`s `targetPrim` muss beim Action-Graph-Verkabeln auf
      `root_joint` zeigen, nicht auf den Wrapper-Prim
- [x] `config/pib_hand_config_v5.py` — gegen die v5-URDF verifiziert; dabei v5-Limits-Bug in
      `setup_stage.py` gefunden (`_BODY_LIMITS` war nur mit v4-Werten befüllt:
      `upper_arm_left` [0°,90°] statt [-90°,90°], `wrist_*` [0°,90°] statt [-90°,30°]);
      Limits in der Stage per `audit_asset.py` bestätigt
- [x] `ros2_ws/src/pib_description_v5/` — neues Package, `<ros2_control>`-Block von Hand
      ergänzt (44 Joints, `topic_based_ros2_control`, gleiche `/pib/hw/*`-Topics wie v4 —
      unproblematisch, da nie beide Stacks gleichzeitig gegen dieselbe Isaac-Instanz laufen)
- [x] `ros2_ws/src/pib_bringup/config/controllers_v5.yaml` + `launch/pib_sim_v5.launch.py`
      — v5-Pendants zu `controllers.yaml`/`pib_sim.launch.py`, v5-Joint-Namen
- [x] `test_client_pickup_v5.py`/`test_client_putdown_v5.py` — aus der per `dump_pose.py`
      aufgenommenen Sequenz (`isaac_sim/tools/_pose_dump.json`: neutral/approach/grasp/lift,
      je 2s) gebaut, alle 44 DOFs (nicht nur Teilmenge wie bei v4), Joint-Namen gegen JSON/
      YAML/URDF kreuzgeprüft (alle 44 identisch)
- [x] **`colcon build` erfolgreich** — `ros2_ws/install/` enthält `pib_description_v5`/
      `pib_bringup` aktuell (verifiziert diese Session, war zuvor als ungetestet vermerkt)
- [x] **Action Graph für v5 fertig verkabelt** (war hier fälschlich noch als Blocker
      vermerkt — laut `docs/handoff.md` vom 2026-09-10 bereits erledigt, diese Session per
      `inspect_action_graph.py` gegen die echte Stage verifiziert: `targetPrim` zeigt
      korrekt auf `root_joint`)
- [x] Pickup-/Putdown-Demo für v5 als Regressionscheck — am 2026-09-10 end-to-end
      verifiziert. **Erneuter Regressionscheck nötig**: Mit Mimic Joints (ADR-011) sind die
      aufgezeichneten `distal`/`tip`-Werte wirkungslos, mit Self-Collision und weichen
      Servo-Gains (ADR-012) kann die Greifpose anders ausfallen
- [ ] ADR schreiben zur v5-Reimport-Entscheidung (`_v4`/`_v5`-Namensschema, maxForce-Fix,
      Erkenntnis dass dieser Import-Weg über `onshape-to-robot`+URDF lief statt über den
      direkten Onshape-Importer wie beim v4-Aufbau) — nächste freie Nummer ist ADR-016

## Fingerkopplung ✓ (ADR-009 → ADR-010 → ADR-011)

**Ziel**: Digitaler Zwilling der realen linken Hand (8 Servos) — PIP/DIP bzw. Daumen-IP folgen
dem MCP, und der MCP-Servo trägt die Last der ganzen Kette.

- [x] ADR-009: Script Node `FingerCoupling` (analytische Viergelenk-Kopplung der Soll-Winkel)
      — **ersetzt**, Branch auf `0fdbc62` zurückgesetzt (Commit `1d0cd9c` auf
      `feature/rl-grasping` und im Tag `backup/sehnendynamik-1d0cd9c`)
- [x] ADR-010: explizite Kraft-Rückwirkung PIP/DIP → MCP — instabil, **verworfen**
- [x] ADR-011: PhysX Mimic Joints, linear (gearing=-1, offset=0), 18 Gelenke beider Hände,
      Folgegelenke passiv; Konfiguration in `setup_stage.py` → `MIMIC_JOINTS`, gesetzt von
      `start.py` — `test_client_mimic_v5`: alle 10 MCPs Δ ≤ 0,2°
- [ ] Stufe 2 (adaptiv, Gearing/Offset aus der Viergelenk-Formel pro Schritt) — offen, erst
      prüfen ob Isaac Laufzeitänderungen von Gearing an PhysX weitergibt
- [ ] Geometrie nur für links an echter Hardware validierbar (rechte Hand existiert nicht
      physisch) — Annahme "gespiegelt identisch" bleibt unverifiziert

## Physik-Tuning nach NVIDIA ← aktuell (ADR-012)

**Ziel**: Stabile, realistische Simulation unter Kontakt, so nah wie möglich an NVIDIAs
Tuning-Reihe (Inspire Hand) und bewährten Projekten. Plan (Reihenfolge nach NVIDIA):

- [x] **1. Asset inspizieren** — `isaac_sim/tools/audit_asset.py`: Massen USD = PhysX = URDF für
      alle 47 Links; Onshape-Massen sind Vollmaterial-PLA ohne Servos (bewusst belassen),
      Unterarm-Override 30 g → 0,229 kg korrigiert (URDF + USD); effektive Gelenkträgheiten
      gemessen (PhysX zählt Armature nicht in die Massenmatrix)
- [x] **2. Collider-Paare** — Self-Collision am `root_joint` an (damit Tischtest stabil);
      Collision Groups vorerst nicht nötig, nur bei konkretem Problem einzelne Filtered Pairs
- [x] **3. Antriebsgrenzen** + **4. Gains** — Servo-Aktuatormodell für alle v5-Servo-Gelenke
      (ST3215 2,94 Nm/270 °/s, ST3095 `shoulder_*` 9,32 Nm/186 °/s; Stiffness = maxForce/5°,
      ζ=1 mit Nenn-Trägheit aus dem Audit) in `setup_stage.py` → `SERVOS`/`V5_ACTUATORS`;
      Experiment-Schalter entfernt, v4 zurück auf Referenzwerte. ω_n·Δt 0,44–1,36
- [ ] **5. Stabilität unter Kontakt** — nur falls nötig, einzeln: Armature,
      `maxDepenetrationVelocity`, Solver-Iterationen (Mimic-Compliance und
      `solveArticulationContactLast` gibt es in 5.1 nicht)
- [x] **6. Validierung** — Tischtest bestanden (Ellbogen gibt nach statt Finger-Stall),
      Pickup v5: Dose gegriffen, Arm hält sie nur knapp (realistisch laut Leon),
      `test_client_mimic_v5` unverändert bestanden (Δ ≤ 0,2°; Daumen/Zeigefinger blockieren
      sich bei ~70°, übrige Finger ~88,5° — Self-Collision), `audit_asset.py` ohne Warnung.
      Putdown v5 am 2026-10-04 erneut bestanden (mit Handgelenk-Pleuel und Filtered Pairs)
- [x] Action-Graph-Trigger auf `OnPhysicsStep` (v5)
- [x] Tischtest bestanden: `index_left` stabiler Stall, vier Finger → Handgelenk gibt
      realistisch nach; Durchhängen/Blockaden bewusst akzeptiert (siehe ADR-012)

---

## RL-Greifen (Isaac Lab, linke v5-Hand) ← aktuell (ADR-014, ADR-015)

**Ziel (Proof of Concept, ~1 Woche ab 2026-10-04)**: Greif-Policy in der Simulation, die nur
reale Sensoren nutzt (8 Servo-Winkel, 5 FSR) — später auf dem STM32N657 (NPU) der echten
linken Hand. Meilensteine: M1 Policy greift in der Sim, M2 läuft quantisiert auf dem Chip
(`stedgeai validate`), M3 echte Hand (optional).

- [x] Servo-Aktuatormodell nach `config/pib_hand_config_v5.py` (eine Quelle, Nm/° und Nm/rad)
- [x] Isaac Lab 2.3.2 in eigener conda-Umgebung `env_isaaclab` (Miniconda, NVIDIA-Doku);
      Hardware-Test RTX 3060 Ti: 1024 Umgebungen ≈ 16.000 Schritte/s
- [x] Hand-only-Asset: `pib_hand_left_urdf_v5/` → `pib_hand_left_v5.usd`, eingebrannt per
      `bake_hand_asset_v5.py`; Isaac Lab übernimmt die Mimic-Kopplung (GPU, Δ ≤ 0,01°)
- [x] Handgelenk-Pleuel: Grenzen [−60°, 0°], Aktuator `RemotizedPDActuatorCfg` (ADR-014)
- [x] Filtered Pair Unterarm ↔ Daumen-Rotator (Hand-USD und Vollroboter)
- [x] Aufgabe `isaac_lab/pib_grasp/` nach Dexsuite (Tisch senkt sich, Asymmetric
      Actor-Critic, ein Kontaktsensor je Fingerspitze, Zufallsstart der Gelenke)
- [x] Machbarkeitstest: Daumen-Rotator 90° → 14–15/16 gehalten, 0° → 0/16
- [x] Probelauf 300 Iterationen: Dose fällt 100 % → 19 %, Gegengriff 0 → 0,38; ONNX-Export
- [x] Policy im Fenster bewertet (`play.py`, Video `videos/isaac_lab_pib_hand_inference_test.webm`):
      hält viele Dosen — dreht dafür aber den Unterarm, bis die Dose auf der Handfläche liegt
### Plan ab 2026-10-06 (Bewertung von `docs/rl-greifen-poc-prompt.md`)

Entscheidungen (Leon, 2026-10-06):
- Unterarm bleibt im Aktionsraum — stattdessen Aufrecht-Belohnung + Abbruch bei Kippwinkel
- Griffarten für den PoC: **Kraftgriff aufrecht** (Milchpackung, Becher, Flasche) und
  **Hakengriff** (Tasche vom Gast übernehmen) — Stütz-/Randgriff, Besteck vorerst nicht
- Actor bleibt blind (nur reale Sensoren), Objektpose **inkl. Orientierung** nur im Critic
- Kein Lehrer/Schüler, kein LSTM: der Actor sieht schon nur reale Sensoren; eine Policy mit
  Griffart als One-Hot statt Spezialisten + Destillation (nur falls das scheitert) —
  **abgelöst am 2026-10-07**, siehe unten

Entscheidungen (Leon, 2026-10-07) — Greif-Architektur (`docs/architecture.md` → „Ziel-Architektur
Greifen“):
- Zweistufig wie Stand der Technik (GR00T System 2/1, DexGraspVLA, GRIT): oben wählt ein Planer
  Objektkategorie → Startpose + Greifart (zuerst Regeltabelle), der Arm fährt die Vorgreifpose an,
  unten schließt die blinde Hand-Policy aus Gelenkwinkeln + FSR
- **Ein Spezialist je Greifart/Startpose** (der blinde Actor sieht die Handausrichtung nicht); ein
  Spezialist deckt alle Objekte seiner Kategorie ab. Für den PoC zwei: **Kraftgriff seitlich**
  (Milch, Becher, Flasche) und **Griff von oben** (Obst). Später ggf. in ein Netz mit Greifart als
  One-Hot destillieren (UniDexGrasp++/UniGraspTransformer: erst Spezialisten, dann destillieren)
- **Hakengriff hinten angestellt** (Stufe 5)
- Offen mit dem IK-Team: Vorgreifpose je Greifart (in der Sim: Handfläche 3,5 cm vor der
  Objektoberfläche) und Signal „Griff steht“ für das Anheben (in der Sim fest nach 2 s)

**Phase 0 — Risiken zuerst**
- [x] ONNX der Probelauf-Policy geprüft: 4× Gemm, 3× Elu, Sub/Div (Normalisierung), Opset 18,
      69.018 Parameter — laut ST-Operatortabelle (Neural-ART r1.3) alles auf der NPU
      (Gemm/Div mit konstanten Parametern), Opset bis 20 unterstützt; float läuft nur auf der CPU,
      die NPU braucht int8 QDQ (per-channel, ss/sa)
- [x] ST Edge AI Core v4.0.1 (STM32CubeAI 12.0.1) in `~/ST/STEdgeAI/4.0/4.0`, `onnxruntime` 1.30
      in `env_isaaclab` (numpy 1.26 eingefroren). `stedgeai analyze --target stm32n6
      --st-neural-art` auf eine int8-QDQ-Version des Probelauf-ONNX (ST-Vorgaben: static,
      QDQ, QInt8/QInt8, per-channel; Kalibrierung hier nur synthetisch): **alle 4 Schichten
      (Gemm+Elu) auf der NPU** (4 HW-Epochs), nur Normalisierung (Sub/Div, 105 Werte) und
      Quantize/Dequantize auf dem M55; Gewichte 71 kB, Aktivierungen 852 B, 68.632 MACC —
      Netzgröße ist kein Engpass. Float-Modell zum Vergleich: alles SW auf dem M55
      (`arm-none-eabi-gcc` fehlt noch → Runtime-Codegröße erst mit STM32CubeIDE in Phase 4)
- [x] Kapazität NUCLEO-N657X0-Q (UM3417: 4,2 MB SRAM, 64 MB Octo-SPI-Flash, kein HyperRAM)
      per `stedgeai analyze`, Profil `internal-memories-only--default` (2,8 MB für NN), int8 QDQ:
      MLP 105→[256,128,64] 70 kB · [512,256,128] 220 kB · Verlauf 15 (315 Eingänge) 326 kB ·
      315→[1024,1024,512] 1,83 MB (passt, alle Schichten NPU) · [2048,1024,512] 3,1 MB passt
      **nicht** intern · LSTM-Zelle 256 + [256,128] 384 kB. LSTM vorerst hinten angestellt
      (rsl_rl-Export braucht eigene Zelle, ST-ONNX-LSTM nur stateless/float)
- [x] Checkpoints: Probelauf lokal als Vergleichswert behalten (nur `model_299.pt` + Export,
      4,6 MB); Meilenstein-Policies (M1, int8 für den Nucleo) künftig als GitHub Release mit
      Tag am Trainings-Commit. Speicher aufgeräumt (6,9 → 21 GB frei)
- [ ] Durchsatz/VRAM mit 2048 und 4096 Umgebungen messen

**Fahrplan, überarbeitet 2026-10-06 — schrittweise nach bewährten Projekten**

Grundsatz: bewährtes Rezept zuerst, **eine Änderung pro Lauf**, jeweils gegen den vorigen
Stand messen (Haltequote, Kippwinkel, Abbruchgründe — Isaac Lab loggt Abbrüche und
Belohnungsterme selbst in TensorBoard). Ausbau nur, wenn eine Messung ihn begründet.

Vorbilder (geprüft, Quellen im Code unter `~/IsaacLab/source/isaaclab_tasks/.../manipulation/`):
| Projekt | Was wir übernehmen |
|---|---|
| Isaac Lab **Lift** (Franka, auch SO-ARM101-Projekte mit ST3215-Servos) | wenige Belohnungsterme; Strafen erst winzig (1e-4), per `modify_reward_weight` nach 10.000 Schritten erhöht; 1500 Iterationen, 4096 Umgebungen, Actor [256,128,64] |
| Isaac Lab **Dexsuite** (Kuka-Allegro-Lift) | unsere Vorlage: Kontaktsensor je Fingerspitze, relative Gelenkaktion, Verlauf 5, Randomisierung |
| Isaac Lab **deploy/gear_assembly** (UR10e, laut NVIDIA auf echter Hardware getestet) | Abbruch bei Objekt-Kippwinkel über Schwelle, minimale Belohnung, Rauschen pro Episode konstant |
| Isaac Lab **inhand** (Allegro, DeXtreme) | Beobachtungsrauschen als einfaches Gauß-Rauschen (Gelenkwinkel std 0,005) |
| **HORA** (Qi et al. 2022, Allegro) | nur an Zylindern trainiert, real auf Dutzende Objekte übertragen; Masse/Reibung/Größe randomisiert und **aus der Propriozeptions-Historie erschlossen** („fühlen“) |

**Experiment-Framework** (ADR-016) ✓ — `experiments/` + `isaac_lab/experiments.py` +
`isaac_lab/eval_policy.py` (Protokoll eval-v1), Übersicht in `experiments/index.md`.
EXP-000 (Probelauf) bewertet: Haltequote 86,1 %, **Aufgabenerfolg 0,0 %** (Kippwinkel 104°,
Unterarm 90°, Stall-Anteil 99,6 %).

**Stufe 1 — Unterarm-Schummelei beheben (eine Änderung)** = EXP-001
- [x] Abbruch bei Kippwinkel der Dose > 20° (Muster gear_assembly) + Aufrecht-Belohnung,
      Objektorientierung im Critic; Fenstertest: alte Policy kippt 48/48, Abbruch greift
- [x] EXP-001 trainiert: 0 % gehalten (Finger gespreizt) — ebenso EXP-002 (1500 It.) und EXP-003
      (Halten × Aufrecht ohne Abbruch). Ursache: Belohnung (ADR-017)
- [x] **EXP-004 Belohnungssatz wie Dexsuite: Aufgabenerfolg 77 % (≤ 45°), Haltequote 90 %,
      Kippwinkel 27°** — neue Baseline. Anforderung für den Zylinder ≤ 45° (Leon)
- [x] Fingernutzung: EXP-004 greift mit genau 2 Fingern. EXP-005 (Kontakt nach Fingerzahl) 2,6,
      EXP-006 (Masse 0,04–0,4 kg) 3,0 Finger, EXP-007 (1500 It.) 2,3 — Aufgabenerfolg-IQM aller
      vier 81–83 %, kein messbarer Unterschied; Kippwinkel/Unterarm bei 005/006 schlechter
- [x] Seed 43 scheitert in jedem Experiment (14–56 %, Griff mit dem kleinen Finger) → Standard
      jetzt **5 Seeds**, Bericht mit IQM und Fehlschlagquote (README)
- [ ] Kraft/Stall (Griffkraft 58 N, Stall 99,7 %) — Kraftstrafe vorerst bewusst nicht (Leon)
- Entschieden (Leon, 2026-10-07): Reibung bleibt (Fingerinnenseiten **und** Handfläche real aus
  TPU, Sim mit 0,5–1,0 eher konservativ); FSR real ebenfalls bis 20 N → Beobachtung passt;
  Handgelenkwinkel nicht in die Bewertung
- [ ] Reset-Überlappung Daumen ↔ Dose (~6 %) beheben — reiner Bugfix, separat geprüft

**Stufe 2 — Rezept der Lift-Aufgabe vollständig**
- [ ] Langer Lauf EXP-002: 1500 It. × 1024 Umgebungen (wie Lift), 3 Seeds — nur die Iterationen ändern
- [ ] Durchsatz/VRAM 2048/4096 messen (`experiments.py bench`) — Grundlage für ein späteres Experiment „mehr Umgebungen“
- [ ] nur falls die Bewegung unruhig ist: Strafen-Curriculum wie Lift (`modify_reward_weight`)
- [ ] M2-Kette früh einmal durchziehen: int8 mit Sim-Kalibrierdaten, int8 vs. float in der Sim

**Stufe 3 — Robustheit nach HORA (weiter nur Zylinder)**
- [ ] Machbarkeitstest Massegrenze (`scripted_grasp_test.py`) → Obergrenze der Masse
- [ ] Masse/Reibung/Durchmesser breiter randomisieren, Masse+Reibung privilegiert im Critic,
      Gelenkreibung, Beobachtungsrauschen (Werte aus inhand) — einzeln zuschalten
- [ ] Auswertung „FSR-Kraft über Masse“ (passt die Policy die Kraft an?)
- [ ] erst wenn das nicht reicht: längerer Verlauf (10–15 Schritte), später LSTM

**Stufe 4 — andere Objekte** ← **als Nächstes** (Leon, 2026-10-07: Fokus von der Belohnung auf
die Objekte; Fingernutzung/Seed-Streuung hängen vermutlich am 6-cm-Zylinder — Ring/kleiner Finger
erreichen ihn kaum)
Plan (Leon, 2026-10-07): Objektkatalog in `env_cfg.py` (Standard `zylinder_d6` = bisherige Szene),
Abstand Handfläche ↔ **Objektoberfläche** konstant 3,5 cm, Quader mit einer Fläche zur Hand
(Drehung ±15° statt beliebig), Masse wie Training; Kugel gehört zu Stufe 4b (seitlich liegt sie
unter dem Daumen).
- [ ] Objektkatalog + `apply_object()` (`env_cfg.py`); `eval_policy.py --objekt --bedingung` →
      `eval-v1_<bedingung>.json` (Standardbedingung bleibt `eval-v1.json`)
- [ ] `experiments.py`: mehrere Bedingungen je Experiment (`objekt_id` in `bedingungen`),
      Bericht/Index je Bedingung, Experimente ohne Training (`training: null`, bewertet fremde Läufe)
- [ ] Fenstertest je Objekt (Spawn, Reset-Überlappung) — Leon schaut zu
- [ ] **EXP-008** Transfer ohne Nachtraining: EXP-004-Läufe an Zylinder Ø 6 cm (Referenz), Ø 8 cm
      (Becher), Quader 7 × 7 × 20 cm (Milchpackung)
- [ ] **EXP-009** dasselbe für EXP-006 (Masse 0,04–0,4 kg, greift mit 3 Fingern)
- [ ] Machbarkeit je Objekt mit realistischer Masse (1-l-Milch ≈ 1 kg)
- [ ] Training mit Objektvielfalt (Dexsuite `MultiAssetSpawnerCfg`), 5 Seeds

**Stufe 4b — Startpose „von oben“** (Leon, 2026-10-07): runde/kleine Objekte (Obst) von oben
greifen statt seitlich — Anfahrrichtung je Objektkategorie (wie Greifplaner, z. B. GraspGen).
Objekt hängt zwischen den Fingern (keine Handflächenstütze), Anforderung ohne Kippwinkel.
Der blinde Actor sieht die Handausrichtung nicht → **eigener Spezialist je Startpose** (beide
passen auf den Nucleo), später ggf. Startpose als One-Hot-Eingang (GRIT).
- [ ] Szene „von oben“ (Hand gedreht, Tisch/Objekt angepasst), Machbarkeitstest Kugel/kleiner Zylinder
- [ ] Spezialist mit Dexsuite-Belohnung, Bedingung ohne Kippanforderung

**Stufe 5 — Hakengriff (Tasche)** — **hinten angestellt** (Leon, 2026-10-07): eigene Startpose
(von oben), Henkel als starrer Körper; voraussichtlich eigener Spezialist (Bewegung grundverschieden:
Finger um den Henkel, Daumen fast passiv)

**Zurückgestellt** (erst bei Bedarf, mit Begründung aus einer Messung): ReLU statt ELU (ELU
läuft auf der NPU; erst wenn int8 vs. float es verlangt), Stall-Strafe, Masse-Curriculum,
Rauschen-Curriculum, LSTM. **Gestrichen**: Schwerkraft-Curriculum (bei uns ist die Schwerkraft
der Erfolgstest — Dexsuite ersetzt damit eine Heben-Belohnung).

**M2 auf dem Board** (nach Stufe 2, wenn STM32CubeIDE/-Programmer installiert): `stedgeai
validate` auf dem NUCLEO-N657X0, Rechenzeit pro Schritt

**Später (M3)**: Servo-Sprungantwort messen und Gains/Armature kalibrieren, Aktionsverzögerung
randomisieren (explizite Aktuatoren), Servo-Last als verrauschte Beobachtung, FSR-Kennlinie,
ggf. adaptive Kopplung

---

## Nicht in diesem Sprint
- Team-Integration (Koordinatenrahmen, IK-/Greifpunkt-Interface) — siehe `feature/ros2-control`
- AS5600-Sensoren, LSTM-Training — siehe `feature/ros2-control`
- Vision/VLA-Greifen auf dem künftigen Jetson Thor (GraspGen, FoundationPose, cuMotion,
  GR00T N1.6, Teacher-Student nach DextrAH) — nur skizziert, siehe Handoff 2026-10-04
