# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-10

### Zuletzt gearbeitet an

1. **Aufräumen + YCB**: eindeutige Dateinamen (`EXP-NNN_`-Präfix) in `experiments/`, Diagnose nach `isaac_lab/tools/`; YCB 003/004/006 mit echter Masse als Testobjekte (`env_cfg.OBJECTS`, Wrapper-USD, Ruhelage per `tools/ruhelage_objekt.py`), Videos `videos/isaac_lab_ycb_*`.
2. **Reset ohne Überlappung → eval-v2** (ADR-021, `tools/analyse_reset.py`): Hand steckte in 34–81 % der Starts im Objekt; jetzt Startpose fast offen, Platzierung nach Größe/Gierdrehung (`mdp.reset_object_gap_aware`); Protokoll je Experiment (`experiments.py umstellen`), Leaderboard je Protokoll.
3. **Prüfung gegen die Vorbilder** (ADR-022): kein Signal fürs Zugreifen (Annäherung maß Unterarmansatz), Aktionen unbegrenzt (rl_games `bounds_loss` fehlt in rsl_rl), Budget 0,5 % von Dexsuite; Nachträge (`nachtrag` im YAML) in EXP-000–018.
4. **Nachtlauf EXP-019–022** + EXP-018 auf 10 Seeds: **EXP-022** (Fortschritt je Fingerspitze wie DexPBT + `clip_actions = 1`) 5/5 Seeds, 83 %, Leitplanken eingehalten, Unruhe 0,36; EXP-019 10/10, aber mehr Unterarm/Kippen.

### Offene Punkte

- **Entscheidung Leon**: EXP-022 als neue Basis — erst nach Sichten von `experiments/EXP-022_fortschritt_begrenzt/beste_videos/`.
- Urteile EXP-012–022 nur als Entwurf in den YAMLs (`ergebnis`/`schluss`), von Leon zu bestätigen.
- Beste Videos von EXP-013/014/015/017 noch vom alten Reset (eval-v1-Starts) — Neuaufnahme angeboten (~20 min), nicht entschieden.
- Alle Policies drücken maximal zu (80–98 N, Stall ~100 %) — „Kraft dosieren“ bewusst hinten angestellt (Leon).

### Nächste Schritte (in Reihenfolge)

1. Leon sichtet EXP-022-Videos → bei OK EXP-022 als Basis festhalten (Sprint 5b).
2. **Griff von oben** (Stufe 4b, Leons Wunsch, Sprint 5c): gedrehte Hand, Apfel/Kugeln (Kugeln als `SphereCfg`; YCB-Apfel fehlt in Isaac Sim 5.1, mit Physik nur 003–006), `analyse_reset.py`, Regel-Baseline, Spezialist mit EXP-022-Rezept.
3. GPU besser nutzen (Sprint 6): Bewertung in einem Isaac-Prozess je Seed (~¼ der Laufzeit ist Startaufwand), `experiments.py bench` 2048 Umgebungen.
4. Trainingsdauer neu prüfen (1500 statt 300 It. auf EXP-022, Nachtlauf), dann Unruhe (Strafen-Curriculum wie Lift, Filter), Bedingung „rutschig“, M2-Kette (int8).

### Wichtige Kontextdetails

- **Nur innerhalb eines Protokolls vergleichen**; bewertet wird nur unter eval-v2, eval-v1-Zahlen sind Historie (Reset-Stöße).
- Policies mit `clip_actions` werden mit `--action_clip` bewertet (`experiments.clip_args` liest `params/agent.yaml`); Firmware muss die Netzausgabe auf ±1 begrenzen.
- Kennzahl **Unruhe wirksam** (Aktion auf ±1 begrenzt) nutzen — die alte „Unruhe“ misst bei unbegrenzten Policies v. a. Überziehen.
- Kontaktanalysen über `force_matrix_w_history` (beide Physik-Unterschritte), sonst werden Stöße übersehen.
- 8 GB VRAM: Fenstertests scheiterten mit CUDA OOM, solange Firefox/Bambu Studio offen waren; lange Läufe mit `nohup setsid` starten.
- Leon: Vorbild als Ganzes prüfen (ADR-022), nur nachbewerten, was Entscheidungen trägt; `pkill -f` mit eigenem Befehlsmuster beendet die eigene Shell; vor Pushs fragen, außer er bittet ausdrücklich.
