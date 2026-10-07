# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-07 (Abend)

### Zuletzt gearbeitet an

1. **Experiment-Framework** (ADR-016): `experiments/` (README: 7-Schritte-Ablauf, Metriken, Entscheidungsregel; `index.md`), `isaac_lab/experiments.py` (`new/bench/run/eval/done`), `isaac_lab/eval_policy.py` (eval-v1). Neu heute: Fingernutzung, IQM + Fehlschlagquote, **Standard 5 Seeds** (42–46).
2. **EXP-001–003** je 0 % gehalten (Finger gespreizt); **EXP-004 Belohnungssatz wie Dexsuite → 77 % Aufgabenerfolg (≤ 45°), IQM 83 %**, Kippwinkel 27° (ADR-017) = Baseline.
3. **EXP-005 (Fingerzahl-Kontakt), EXP-006 (Masse 0,04–0,4 kg), EXP-007 (1500 It.)**, Eltern EXP-004: IQM 76–82 %, kein messbarer Unterschied; Finger an der Dose 2,6 / 3,0 / 2,3 (EXP-004: 2,0); Kippwinkel/Unterarm bei 005/006 schlechter.
4. Plan überarbeitet (`docs/current-sprint.md`): Fokus jetzt **andere Objekte** (Stufe 4) und **Startpose „von oben“** (Stufe 4b).

### Offene Punkte

- **Seed 43 scheitert in jedem Experiment** (14–56 %, Griff mit dem kleinen Finger) — Hauptquelle der Streuung; EXP-004–007 haben nur 3 Seeds (45, 46 nachrechnen, wenn ein Vergleich nötig wird).
- Urteile in EXP-001–007 sind Entwürfe („von Leon zu bestätigen“); EXP-005–007 haben noch keinen Schluss-Text.
- Kraft/Stall hoch (Griffkraft 58–85 N, Stall ~100 %) — Kraftstrafe vorerst bewusst nicht (Leon).
- Manche Seeds beugen das Handgelenk an den Anschlag (−60°, Pleuel-Totlage; EXP-005 s42, Dose 7 cm näher am Arm) — in der Sim bis 12 Nm, Wert ist eine Annahme (ADR-014).
- Reset-Überlappung Daumen ↔ Dose (~0,5–2 % Startfehler) noch nicht behoben.

### Nächste Schritte (in Reihenfolge)

1. `eval_policy.py`: Objekt als Teil der Bedingung austauschbar (Quader 7 × 7 × 20 cm, Zylinder Ø 8 cm, Ø 6 cm, ggf. Kugel Ø 7 cm), Masse wie Training.
2. EXP-004/006-Policies **ohne Nachtraining** an diesen Objekten bewerten (alle Seeds), Fingernutzung je Objekt vergleichen, Inferenz mit Fenster zeigen.
3. Danach mit Leon entscheiden: Training mit Objektvielfalt (`MultiAssetSpawnerCfg`, Dexsuite) und/oder Machbarkeit mit realistischer Masse (Milch ≈ 1 kg).
4. Startpose „von oben“: Szene anlegen, Machbarkeitstest Kugel/kleiner Zylinder, eigener Spezialist (Bedingung ohne Kippanforderung).

### Wichtige Kontextdetails

- **Arbeitsweise**: jede Änderung als Experiment (Hypothese vorher, genau eine Änderung, 5 Seeds, Commit vor dem Lauf); Leon gibt Läufe frei, schaut Inferenz im Fenster („sichten“), bestätigt Urteile. Keine Läufe ohne Freigabe.
- **Entschieden (Leon)**: Zylinder-Anforderung ≤ 45°; Reibung bleibt (Fingerinnenseiten und Handfläche real TPU → Sim 0,5–1,0 konservativ); FSR real bis 20 N (Beobachtung passt); Handgelenkwinkel nicht in die Bewertung; Kraftstrafe vorerst nicht; Startpose je Objektkategorie (seitlich: Milch/Becher/Flasche, von oben: Obst/Tasche), Spezialist je Startpose.
- **Actor** (blind): 8 Servo-Winkel, 5 FSR (alle Kontakte, 0–20 N), 8 letzte Aktionen, Verlauf 5 = 105 Eingänge; keine Zeit/Phase, keine Objektinfo, keine Handausrichtung.
- **Belohnung** nach Dexsuite (ADR-017); Aufrecht-Terme erst ab dem Absenken; Belohnungsanteile vor Läufen prüfen (`isaac_sim/tools/_reward_diag.txt`-Muster). Bewertung schaltet Trainingsabbrüche ab, Anforderung wird erst bei der Auswertung angewandt (Eltern unter der Bedingung des Kindes).
- **Trainingsvarianten** als Task-IDs (`Pib-Grasp-Hand-Left-FingerCount-v0`, `-Heavy-v0`); Bewertung immer in `Pib-Grasp-Hand-Left-v0`.
- `experiments.py` mit **System-Python** bei aktiver conda-Umgebung; lange Läufe `setsid nohup … &`. `pkill -f` mit Muster aus dem eigenen Befehl beendet die eigene Shell. Zwei Isaac-Umgebungen nacheinander im selben Prozess hängen → je Prozess eine.
- **Sicherung**: Policies aller Läufe (EXP-000–007, 119 MB) im privaten HF-Repo `churro206/pib-grasp-policies`; nach jedem Experiment `~/IsaacLab/isaaclab.sh -p isaac_lab/backup_policies.py --upload` (über isaaclab.sh, weil `requests` sonst fehlt; Login liegt in `~/.cache/huggingface/token`).
- **STM32N6**: ST Edge AI 4.0.1 in `~/ST/STEdgeAI/4.0/4.0`; int8-Policy komplett auf der NPU, bis ~1,8 MB Gewichte intern; mehrere Spezialisten passen.
