# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-10

### Zuletzt gearbeitet an

1. **Reset ohne Überlappung → eval-v2** (ADR-021, `tools/analyse_reset.py`): Hand steckte in 34–81 % der Starts im Objekt; jetzt Startpose fast offen, Platzierung nach Größe/Gierdrehung; Protokoll je Experiment (`experiments.py umstellen`), Leaderboard je Protokoll. Vorher: Aufräumen (`EXP-NNN_`-Dateinamen, `isaac_lab/tools/`) und YCB 003/004/006 als Testobjekte.
2. **Prüfung gegen die Vorbilder** (ADR-022): kein Signal fürs Zugreifen, Aktionen unbegrenzt (rl_games `bounds_loss` fehlt in rsl_rl), Budget 0,5 % von Dexsuite; Nachträge (`nachtrag` im YAML) in EXP-000–018.
3. **Nachtlauf EXP-019–022** + EXP-018 auf 10 Seeds, beste Videos aufgenommen: **EXP-022** (Fortschritt je Fingerspitze wie DexPBT + `clip_actions = 1`) 5/5 Seeds, 83 %, Leitplanken eingehalten, Unruhe 0,36.
4. **Befund Objektweg** (`tools/diag_objektweg.py`, ADR-022 Nachtrag): Linie mit 18 Formen (EXP-013/017/018–022) zieht das Objekt ~13 cm in der Tischebene Richtung Unterarm; Zylinder-Policies 3–7 cm, Regel 4 cm; Literatur bestraft das (Cross-Embodiment, RobustDexGrasp).

### Offene Punkte

- **Entscheidung Leon**: EXP-022 als neue Basis — nach Sichten von `experiments/EXP-022_fortschritt_begrenzt/beste_videos/` (Sprint 5b).
- Urteile EXP-012–022 nur als Entwurf in den YAMLs (`ergebnis`/`schluss`), von Leon zu bestätigen.
- Beste Videos von EXP-013/014/015/017 noch vom alten Reset — Neuaufnahme angeboten (~20 min), nicht entschieden.
- Alle Policies drücken maximal zu (80–98 N, Stall ~100 %) — „Kraft dosieren“ bewusst hinten angestellt (Leon).

### Nächste Schritte (in Reihenfolge)

1. Leitplanke **Objektweg** in `eval_policy.py` (Verschiebung der Objektmitte in xy ggü. t = 0,1 s), Sprint 5c.
2. **EXP-023** (Eltern EXP-022): Strafe auf xy-Verschiebung ggü. Startlage wie Cross-Embodiment (−0,3·‖xy − xy_Start‖, ganze Episode, z bleibt beim Halte-Term); Gewicht per `reward_diag`, sodass 13 cm Ziehen etwa den Gegengriff aufwiegt (Sprint 5d).
3. **Griff von oben planen** und mit der Literatur abgleichen (Dexsuite, DexPBT, UniDexGrasp++, HORA): Handpose, Tisch, Kugeln (`SphereCfg`; YCB-Apfel fehlt in Isaac Sim 5.1), YCB 005, Anforderung ohne Kippwinkel → voraussichtlich EXP-024 (Sprint 5e).
4. Danach: GPU besser nutzen (Bewertung je Seed in einem Prozess, `bench` 2048), Trainingsdauer auf der Basis neu prüfen, Unruhe, „rutschig“, M2.

### Wichtige Kontextdetails

- **Nur innerhalb eines Protokolls vergleichen**; bewertet wird nur unter eval-v2, eval-v1-Zahlen sind Historie.
- Policies mit `clip_actions` werden mit `--action_clip` bewertet (`experiments.clip_args` liest `params/agent.yaml`); Firmware muss die Netzausgabe auf ±1 begrenzen. Kennzahl **Unruhe wirksam** nutzen.
- Isaac Lab: nur eine Umgebung je Prozess; `env.reset` in Diagnoseskripten innerhalb `torch.inference_mode()`; Kontakte über `force_matrix_w_history`.
- 8 GB VRAM: Fenstertests scheitern mit CUDA OOM, wenn Firefox/Bambu Studio offen sind; lange Läufe mit `nohup setsid`.
- Leon: Vorbild als Ganzes prüfen (ADR-022), nur nachbewerten, was Entscheidungen trägt; `pkill -f` mit eigenem Befehlsmuster beendet die eigene Shell; vor Pushs fragen, außer er bittet ausdrücklich.
