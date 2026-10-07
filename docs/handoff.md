# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-07

### Zuletzt gearbeitet an

1. **Experiment-Framework** (ADR-016): `experiments/` (README mit 7-Schritte-Ablauf, Metriken, Entscheidungsregel; `index.md`), `isaac_lab/experiments.py` (`new/bench/run/eval/done`), `isaac_lab/eval_policy.py` (Protokoll eval-v1: Aufgabenerfolg, Haltequote, Leitplanken, Fingernutzung, Video).
2. **EXP-000–004**: Kippabbruch (001), 1500 It. (002), Halten × Aufrecht (003) → je 0 % gehalten (Finger gespreizt). **EXP-004 Belohnungssatz wie Dexsuite → Aufgabenerfolg 77 % (≤ 45°), Haltequote 90 %, Kippwinkel 27°** (ADR-017).
3. **Phase 0 STM32N6**: ST Edge AI Core 4.0.1 in `~/ST/STEdgeAI/4.0/4.0`; int8-QDQ-Policy läuft komplett auf der NPU (71 kB), bis ~1,8 MB Gewichte passen intern; LSTM möglich, zurückgestellt.
4. **Gestartet (während Leon weg ist)**: EXP-005 (Fingerzahl-Kontakt), EXP-006 (Masse 0,04–0,4 kg), EXP-007 (EXP-004 mit 1500 It.), alle Eltern EXP-004 — Log `logs/experiments/exp005-007_2026-10-07.log`.

### Offene Punkte

- **Ergebnisse EXP-005–007 auswerten** (`experiments/index.md`, je `bericht.md`), Inferenz mit Fenster zeigen, Urteile mit Leon bestätigen.
- EXP-004 hält mit **genau 2 Fingern** (Daumen + Zeige/klein/Mittel je nach Seed), Daumen-MCP gestreckt, Rotator ~90°.
- Leitplanken EXP-004 verletzt: Griffkraft 58 N, Kraft > 15 N 99 %, Stall 99,7 % — Kraftstrafe **vorerst bewusst nicht** (Leon).
- Urteile in EXP-001–004 sind Entwürfe („von Leon zu bestätigen“).
- Seed-Streuung EXP-004: 88/56/88 % (Seed 43 hält mit dem kleinen Finger).

### Nächste Schritte (in Reihenfolge)

1. EXP-005–007 auswerten (`/usr/bin/python3 isaac_lab/experiments.py done`), Fingernutzung vergleichen, Inferenz des besten Laufs mit Fenster (`eval_policy.py --policy … --num_envs 16 --real_time --out <scratch>`).
2. Je nach Ergebnis: beste Einzeländerung als neue Baseline; ggf. Kombination als eigenes Experiment.
3. Danach (einzeln): Aktionen auf ±1 kappen (gegen Unruhe/Sättigung), begrenzte Kraftstrafe (wenn Leon will).
4. Stufe 3/4 nach Fahrplan (`docs/current-sprint.md`); M2: int8 mit Sim-Kalibrierdaten, `stedgeai validate` (STM32CubeIDE/-Programmer fehlen noch).

### Wichtige Kontextdetails

- **Arbeitsweise**: jede Änderung als Experiment (Hypothese vorher, genau eine Änderung, 3 Seeds, Commit vor dem Lauf); Leon gibt Läufe frei, schaut Inferenz im Fenster, bestätigt Urteile.
- **Belohnung**: nach Dexsuite (ADR-017); Aufrecht-Terme erst ab dem Absenken (sonst Belohnung fürs Antippen); Belohnungsanteile vor Läufen prüfen (`isaac_sim/tools/_reward_diag.txt`-Muster).
- **Bewertung** schaltet Trainingsabbrüche ab (Kippen wird gemessen); Anforderung (≤ 45° für den Zylinder, Leon) wird erst bei der Auswertung angewandt, Eltern unter der Bedingung des Kindes.
- **Trainingsvarianten** als eigene Task-IDs (`Pib-Grasp-Hand-Left-FingerCount-v0`, `-Heavy-v0`), Bewertung immer in `Pib-Grasp-Hand-Left-v0`.
- `experiments.py` mit **System-Python** bei aktiver conda-Umgebung starten (blendet Isaac-Pfade aus); lange Läufe mit `setsid nohup … &`. `pkill -f` mit Muster aus dem eigenen Befehl beendet die eigene Shell.
- Zwei Isaac-Umgebungen nacheinander im selben Prozess (mit `env.close()`) hängen → je Prozess eine Umgebung.
- Machbarkeitstest: fester Gegengriff kippt die 6-cm-Dose 43–78°; Ring/kleiner Finger erreichen sie nicht. Speicher: ~21 GB frei (aufgeräumt).
