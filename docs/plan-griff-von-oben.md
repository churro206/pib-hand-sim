# Plan: Griff von oben (Stufe 4b)

Stand 2026-10-10 abends, Entwurf (Claude, während Leon unterwegs war). Szene gebaut und geprüft (Schritte 1–3 unten);
noch keine Regel-Baseline nach ADR-020 und kein Training.
Entscheidungen, die Leon treffen muss, stehen am Ende unter „Offene Fragen“. Einordnung: ADR-018 (ein Spezialist je
Greifart), `docs/current-sprint.md` → Stufe 4b und Punkt 5e.

## Ziel

Ein zweiter Spezialist für die Hand-Policy: Obst und kleine/flache Objekte **von oben** greifen und halten, während der Arm
anhebt. Im Ablauf ändert sich nichts: Der Arm (IK-Team) fährt die Vorgreifpose an, die blinde Policy (8 Gelenkwinkel,
5 FSR) schließt die Hand, nach 2 s „hebt der Arm an“ (in der Sim senkt sich der Tisch um 10 cm), danach muss das Objekt
2 s in der Hand bleiben. Anders als seitlich gibt es keine Handfläche, die das Objekt von unten stützt: Es hängt zwischen
Daumen und Fingern.

## Abgleich mit der Literatur

| Vorbild | Startpose der Hand | Erfolg | Was wir übernehmen |
|---|---|---|---|
| **UniDexGrasp** (Xu et al., CVPR 2023; Isaac Gym, ShadowHand frei schwebend) | Handfläche nach unten, feste Höhe h₀ über dem Tisch, alle Gelenke 0, Gierwinkel zum Objekt ausgerichtet | Objekt am letzten Schritt < 5 cm vom Ziel 0,3 m über der Startlage | Handfläche unten, Gelenke offen, Gier aus der Vorgreifpose (Planer) |
| **UniDexGrasp++** (Wan et al., ICCV 2023) | wie UniDexGrasp | wie UniDexGrasp; 85 % Training / 78 % neue Objekte | Spezialisten → Destillation (schon ADR-018) |
| **Dexsuite Lift** (Isaac Lab, Kuka-Allegro; unsere Vorlage) | Arm fährt von oben an | Position allein; `orientation_tracking = None`, `success.rot_std = None` | **Kein Orientierungsterm** beim Heben, sonst gleiche Belohnung |
| **Cross-Embodiment Dexterous Grasping** (Yuan et al., ICLR 2025; 45 YCB-Objekte) | Arm + Hand über dem Tisch | Objekt 30 Schritte auf Zielhöhe, Hand nah dran | Strafe −0,3·‖xy − xy_Start‖ (= EXP-023) |
| **RobustDexGrasp** (2025; 512 reale Objekte) | 25 cm entfernt, teilweise offen, Handfläche zur Objektmitte | 0,1 m anheben, 5 s ohne Fallen; Störung 2,5 N | Strafe auf die Objektverschiebung (−15); später Störkraft als eigene Bedingung |
| **DexPBT / AllegroKuka** (Petrenko et al. 2023) | Arm fährt an | – | Fortschritt je Fingerspitze (seit EXP-019) |

Was daraus folgt:
- Handfläche nach unten, Gelenke offen und eine feste Höhe über dem Objekt sind Standard (UniDexGrasp). Unser Unterschied
  bleibt: Die Hand fährt **nicht** selbst an, das macht der Arm (ADR-018). Deshalb startet die Hand nah am Objekt
  (Vorgreifabstand) und nicht 25 cm entfernt wie bei RobustDexGrasp.
- Heben braucht keinen Orientierungsterm (Dexsuite Lift). Die Anforderung „Kippwinkel ≤ 45°“ fällt weg.
- Die Lage in der Tischebene zu halten ist bei Top-Down-Greifern üblich (Cross-Embodiment, RobustDexGrasp). Ob der Term
  bei uns hilft, zeigt EXP-023, bevor wir ihn für „von oben“ übernehmen.

## Setup-Vorschlag

### Handpose
- **Handfläche nach unten, Unterarm waagrecht.** Im Hand-Root-Frame zeigen die Finger ohne Drehung schon nach −y, die
  Handfläche nach −z und der Daumen nach −x (`env_cfg.py`, Kommentar zur Geometrie). Also `HAND_ROT = (1, 0, 0, 0)`;
  für seitlich drehen wir heute +90° um y.
- Später möglich: Unterarm 20–30° nach unten geneigt (so greift ein Mensch einen Apfel vom Tisch). Die Handgelenkbeugung
  (bis −60°) kann das teilweise selbst leisten, die Policy darf sie nutzen.

### Vorgreifpose — die eigentliche Machbarkeitsfrage
Fingerglieder laut URDF: MCP→PIP 36 mm, PIP→DIP 31 mm, dazu die Spitze (~2 cm). Mit Handfläche nach unten und der
linearen Kopplung (alle drei Gelenke gleich weit gebeugt) liegt die größte Reichweite nach unten bei MCP ≈ 40°, etwa
**7 cm unter der MCP-Achse**. Danach rollen die Spitzen wieder zurück. Bei einer Kugel Ø 7 cm und dem seitlichen
Vorgreifabstand von 3,5 cm liegt der Äquator aber 7 cm unter der Handfläche: Die Finger kämen kaum darunter.
→ Ich erwarte einen **kleineren Abstand von oben (1–2 cm)** und die Objektmitte eher unter den Grundgliedern
(Pinzetten-/Dreipunktgriff Daumen ↔ Zeige/Mittel) statt unter der Handflächenmitte. Das soll gemessen und nicht
geschätzt werden (Schritt 1–2 im Ablauf).

**Gemessen** (`tools/probe_oben.py`, 2026-10-10, Gelenkrahmen der Spitzen relativ zum Hand-Root, `_probe_oben.txt`):
- Fingerspitzen offen bei y ≈ −0,38, z −5 mm; tiefster Punkt **−62 mm bei MCP 50–60°** (y −0,32 … −0,33), bei MCP 90°
  wieder −40 mm (y −0,28).
- Daumen: bei Rotator 90° zeigt die Spitze schon offen 71 mm nach unten (x −25, y −0,26), gebeugt (−14, −0,29, −41 mm).
  Bei Rotator 0° liegt sie seitlich neben der Hand (x −94, z −4).
- Greifzone also zwischen Daumen (y −0,26 … −0,29) und eingerollten Fingern (y −0,32 … −0,35) → Objektmitte
  `OBJECT_XY_OBEN = (−0,01, −0,31)` (vorher geschätzt (0,01, −0,34)).
- **Machbarkeit** (`tools/machbarkeit_oben.py`, Regel „alle schließen“ wie EXP-014, 24 Episoden je Rotator-Ziel,
  Startstellung wie im Training inkl. Rotator 0–90°; `_machbarkeit_oben.txt`). Kugel Ø 7 cm:

  | Abstand | y | gehalten Rot. 45° / 90° | Startkontakt > 0,5 N |
  |---|---|---|---|
  | 5 mm | −0,29 / −0,31 / −0,33 | ≤ 5 / ≤ 5 | 24/24 (bis 2500 N) |
  | 15 mm | −0,31 | 11 / 5 | 4/24 |
  | 15 mm | −0,29 / −0,33 | 13 / 5 · 11 / 2 | 17–20/24 |
  | 25 mm | −0,33 | 15 / 8 | 0/24 |
  | **35 mm** | **−0,31** | **8 / 17** | 1/24 (1,2 N) |
  | 35 mm | −0,33 | 8 / 14 | 0/24 |

  Gegen die Erwartung ist **mehr** Abstand besser: Der Daumen zeigt bei Rotator 90° 7 cm nach unten und braucht Platz
  über dem Objekt; mit 3,5 cm (= seitlicher Vorgreifabstand) greift die Regel die Kugel in 17/24 Episoden. Wie der Griff
  dann aussieht (Kugelmitte 70 mm unter der Handfläche, Fingerspitzen-Gelenke bis 62 mm), ist noch im Fenster anzusehen.

### Tisch
- Platte auf Höhe der Objektunterseite, Absenken wie bisher (ab 2 s, 10 cm, 0,2 m/s).
- Ganz offene Finger liegen waagrecht auf Höhe der Handfläche und berühren den Tisch nicht. Zu prüfen ist, ob die Finger
  beim Zugreifen auf flache Objekte (Höhe 4 cm) an die Tischplatte stoßen.

### Objekte
Kategorie „von oben“ nach ADR-018: rund, klein oder flach (seitlich braucht ≥ 15 cm Höhe).

| Rolle | Objekte | Bemerkung |
|---|---|---|
| Training (prozedural, wie EXP-013) | Kugeln Ø 5–9 cm (`sim_utils.SphereCfg`), kurze Zylinder aufrecht Ø 5–8 × 6–10 cm, flache Quader (z. B. 9×6×4, 8×8×5 cm) | Masse 0,04–0,4 kg wie `Heavy`; Gier ±15° für Quader |
| Benchmark | Kugel Ø 7 cm (Apfel-Ersatz), Kugel Ø 5 cm, Dose Ø 6,8 × 10 cm, flacher Quader 9×6×4 cm | eigene Leaderboard-Tabelle „von oben“ |
| Testobjekte (nie trainiert) | **YCB 005 Tomatensuppendose** (349 g, Physik-Asset vorhanden, 6,8 × 10,2 cm) | Ruhelage messen wie bei 003/004/006 |
| später | YCB 007 Thunfisch, 008 Pudding, 009 Gelatine, 010 Fleischdose, 011 Banane, 061 Schaumstoffziegel | nur in `Axis_Aligned` **ohne** Physik: Starrkörper, Collider und Masse in der Wrapper-USD ergänzen |

- Ein YCB-Apfel (013) fehlt in Isaac Sim 5.1 (`_ycb_inspect.txt`), deshalb die Kugel.
- **Kugeln rollen.** Ein echter Apfel liegt auf einer leicht flachen Unterseite, eine Sim-Kugel rollt beim ersten
  Antippen weg. Zuerst messen (`analyse_reset.py`, `diag_objektweg.py` mit der Regel). Falls es stört: Winkeldämpfung
  am Objekt (`RigidBodyPropertiesCfg.angular_damping`) oder eine leicht abgeflachte Form.

### Aufgabe, Belohnung, Bewertung
- Beobachtung, Aktion, Startstellung (fast offen, Rotator 0–90°), Randomisierung: unverändert wie das seitliche Rezept.
- Belohnung: bestes seitliches Rezept (EXP-022, mit xy-Strafe falls EXP-023 sie stützt), **ohne `upright`** und mit
  `success` ohne Kippfaktor (wie Dexsuite Lift).
- Abbrüche unverändert: gefallen (> 5 cm abgesunken), instabil.
- Bewertung eval-v2 mit `--max_kipp_deg -1` (keine Anforderung). Erfolg = bis zum Ende gehalten; Leitplanken wie
  bisher, inklusive Objektweg.

### Code (umgesetzt 2026-10-10, nicht committet)
1. `isaac_lab/pib_grasp/env_cfg_oben.py`: Handpose, `PALM_GAP_OBEN` 3,5 cm, `OBJECT_XY_OBEN` (−0,01, −0,33), Tisch
   je Umgebung an die Objektunterseite, `OBJECTS_OBEN` (Kugeln, Dose, Schachtel, YCB 005), `apply_object_oben`,
   Varianten `PibGraspEnvCfg_Oben` (Bewertung), `_ObenMulti` (17 Formen, Training), `_ObenMultiXY`.
2. `mdp.place_objects_from_above`: Startlage aus der Bounding Box, Abstand nach unten, Tischhöhe je Umgebung.
3. Tasks `Pib-Grasp-Hand-Left-Oben-v0`, `-ObenMulti-v0`, `-ObenMultiXY-v0` (Agent mit Aktionen auf ±1).
4. `eval_policy.py --greifart oben`, `tools/analyse_reset.py --greifart oben`.
5. `experiments.py`: `BENCHMARK_OBEN`/`TESTOBJEKTE_OBEN`, `greifart` im experiment.yaml und je Bedingung, eigene
   Leaderboard-Tabelle je Greifart (Ausgabe für „seitlich“ byte-gleich geprüft).
6. Werkzeuge `tools/probe_oben.py` (Geometrie), `tools/machbarkeit_oben.py` (Raster mit Regel).

## Ablauf (Prüfschritte nach CLAUDE.md)

1. **Geometrie messen** (`probe_geometry.py`, ohne Schwerkraft): Fingerspitzen und Daumenspitze bei MCP 0–90° und
   Rotator 0/45/90°, Handfläche unten → Reichweite nach unten, Lage der Greifzone.
2. **Machbarkeitstest ohne Policy** (`scripted_grasp_test.py` bzw. Regel „alle schließen“, mit Fenster): kleines Raster
   aus Vorgreifabstand {1; 2; 3,5 cm} × Lage in y (unter Handfläche / unter den Grundgliedern) × Rotator {45; 90°}, je
   Kugel Ø 5/7 und Dose. Ergebnis: Abstand und Lage für die Szene. Vorbild ist der Test vom 2026-10-04 (Rotator 90° →
   14–15/16 gehalten).
3. **Szene festlegen und prüfen**: `analyse_reset.py` (≥ 256 Starts, 0 Kontakte Hand↔Objekt, Kontaktsensor über beide
   Physik-Unterschritte), `check_multi.py` (Bilder aller Trainingsformen), Ruhelage der YCB-005-Dose.
4. **Regel-Baseline „von oben“** (ADR-020): Raster mit Seed 2000, final eval-v2.
5. **Belohnungsdiagnose** (`reward_diag.py`) mit der Regel bzw. der seitlichen Policy auf der neuen Szene.
6. **EXP-024 Spezialist „von oben“**: bestes seitliches Rezept, 5 Seeds, 300 Iterationen, eigenes Benchmark. Kurztraining
   vorab (Curriculum-Pfade gibt es nicht, Kurztest genügt).

Schritte 1–3 sind erledigt (headless, Leon war unterwegs — im Fenster noch einmal ansehen), Schritt 6 braucht etwa 2 h
Training plus Bewertung.

### Ergebnis Schritt 3 und Bewertungspfad (2026-10-10)
- `analyse_reset.py --greifart oben`, 256 Starts: Dose und YCB-Suppendose 0/256 Handkontakt, nichts verschoben (Suppe
  fällt wie vorgesehen 3 mm); Kugel Ø 7 0/256 Handkontakt, aber **14/256 rollen > 5 mm in 0,1 s** ohne Berührung;
  Trainingsszene (17 Formen) 2/256 Kontakt Daumenspitze (≤ 22 N), 36/256 verschoben > 5 mm (Kugeln).
- Ungeklärt: in einer Umgebung (Kugel Skala 0,91, Rotator-Start 82°) dreht sich der Daumen-Rotator in 0,1 s um 80°,
  die Kugel rollt 9 mm und dreht 76° — ohne gemessenen Kontakt Hand↔Kugel. Im Fenster ansehen.
- `eval_policy.py --greifart oben`, Regel „alle schließen“ (Rotator 90°, 0,2), 256 Episoden: Dose 75 % (Objektweg
  14 mm), Kugel Ø 7 64,5 % mit **13 % Startfehlern** (Episode endet ≤ 0,1 s) — vermutlich dasselbe Rollen; vor einem
  Training klären (Winkeldämpfung, Kugel leicht abgeflacht, oder Startlage prüfen).
- **Kleine und flache Objekte** (Kugel Ø 5, Schachtel 9×6×4) mit dieser Pose nicht machbar: bei 35 mm ≤ 3/24 gehalten,
  bei 15–25 mm steckt der nach unten zeigende Daumen im Objekt (bis 2900 N). → Frage 1/3.

## Offene Fragen an Leon

1. **Handpose**: Unterarm waagrecht und Handfläche unten (Vorschlag, wie UniDexGrasp) oder gleich geneigt? Was kann der
   pib-Arm real anfahren (IK-Team)?
2. **Vorgreifabstand von oben**: gemessen sind 3,5 cm am besten (wie seitlich) — passt das für die Schnittstelle zum
   IK-Team (Handfläche 3,5 cm über der Objektoberseite)?
3. **Objektkatalog**: kleine/flache Objekte (Kugel Ø 5, Schachtel) mit waagrechter Hand nicht greifbar. Aus dem
   Benchmark nehmen (Benchmark dann Kugel Ø 7 + Dose, Training ohne die flachen Quader und Ø 5) oder geneigte Hand
   als eigene Startpose?
4. **Kugeln rollen lassen** (realistisch schwer) oder dämpfen bzw. abflachen (näher am Apfel)?
5. **Rezept**: EXP-023 (xy-Strafe) senkt das Ziehen, macht aber 3/5 Seeds unruhig (Leitplanke verletzt) → Vorschlag:
   „von oben“ mit dem EXP-022-Rezept ohne xy-Strafe (Task `ObenMulti-v0`).

## Quellen
- UniDexGrasp: https://arxiv.org/abs/2303.00938 (Abschnitt 3.3 und Anhang C.1: Startpose, Erfolg 0,3 m / 5 cm)
- UniDexGrasp++: https://arxiv.org/abs/2304.00464
- Isaac Lab Dexsuite: `~/IsaacLab/source/isaaclab_tasks/isaaclab_tasks/manager_based/manipulation/dexsuite/dexsuite_env_cfg.py`
  (`DexsuiteLiftEnvCfg`)
- Cross-Embodiment Dexterous Grasping: https://arxiv.org/abs/2410.02479
- RobustDexGrasp: https://arxiv.org/abs/2504.05287
- DexPBT: https://arxiv.org/abs/2305.12127
