# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-10 (abends, Leon unterwegs — nichts committet, nichts gepusht, kein HF-Backup)

### Zuletzt gearbeitet an

1. **Leitplanke Objektweg** (`eval_policy.py`: `objektweg_mm` Ende/`objektweg_max_mm` ggü. t = 0,1 s; `experiments.py` GUARDRAILS +20 mm; README). EXP-022 nur in der Hauptbedingung neu bewertet (Objektweg Ø 6: 112 mm).
2. **EXP-023** (xy-Strafe −4·‖xy − xy_Start‖, `mdp.object_xy_displacement`, Task `HeavyMultiProgressClipXY-v0`): 87 %, 5/5, Objektweg 112 → 75 mm (s42 unverändert 144), aber Leitplanke Unruhe verletzt (1,65 vs. 0,36). Ergebnis/Schluss als Entwurf im YAML.
3. **Griff von oben**: Plan `docs/plan-griff-von-oben.md` (Literatur: UniDexGrasp, Dexsuite Lift, Cross-Embodiment, RobustDexGrasp) + Code: `pib_grasp/env_cfg_oben.py`, `mdp.place_objects_from_above`, Tasks `Oben-v0`/`ObenMulti-v0`/`ObenMultiXY-v0`, `eval_policy.py`/`analyse_reset.py --greifart oben`.
4. **`experiments.py` je Greifart** (`BENCHMARK_OBEN`, `greifart` in YAML und Bedingung, Leaderboard-Tabelle je Greifart) — Ausgabe für „seitlich“ byte-gleich geprüft; Werkzeuge `tools/probe_oben.py`, `tools/machbarkeit_oben.py`.

### Offene Punkte

- **Einsatz-Kandidat seitlich** (Gegenprüfung Bewertungs-Seed 2000, 8 Objekte, `logs/gegenpruefung_seed2000/`): EXP-023 s43 85,0 % (Seed 1000: 83,8), Objektweg Ø 25 mm, Kipp 11°, Unterarm 8°, Unruhe 0,32; EXP-022 s45 87,5 % (87,9), Weg 33 mm, Kipp 18°, Unterarm 15°, Unruhe 0,39. Keine Auswahlverzerrung; Vorschlag s43 (ruhiger), s45 als Reserve — Entscheidung Leon.
- **Von oben, Kugel**: 14/256 Kugeln rollen beim Reset > 5 mm ohne Kontakt; in der Bewertung 13 % Startfehler (Episode endet ≤ 0,1 s). Eine Umgebung (Skala 0,91, Rotator-Start 82°): Daumen-Rotator springt 80° in 0,1 s ohne gemessenen Kontakt — ungeklärt.
- Kleine/flache Objekte (Kugel Ø 5, Schachtel 9×6×4) mit waagrechter Hand nicht greifbar (Regel ≤ 3/24); stehen noch in `BENCHMARK_OBEN`/Training.
- Entscheidungen Leon: Fragen 1–5 im Plan; EXP-022 als Basis (Videos), EXP-023-Urteil (Videos s43 37 mm vs. s42 144 mm).
- Alle Läufe heute headless (Leon war weg) — Szene „von oben“ noch nie im Fenster gesehen.

### Nächste Schritte (in Reihenfolge)

1. Leon: Plan-Fragen beantworten, Szene im Fenster zeigen: `isaaclab.sh -p isaac_lab/tools/machbarkeit_oben.py --objekt kugel_d7 --num_envs 16 --real_time`.
2. Kugel-Rollen/Startfehler klären (Fenster, Env 124); ggf. `angular_damping` am Objekt oder Startlage; danach `analyse_reset.py --greifart oben` erneut (Ziel 0 Kontakt, nichts verschoben).
3. Objektkatalog „von oben“ nach Leons Entscheidung bereinigen (`env_cfg_oben.OBJECTS_OBEN`/`TRAIN_*_OBEN`, `experiments.BENCHMARK_OBEN`).
4. Regel-Baseline „von oben“ nach ADR-020 (Raster Seed 2000, `greifart: oben` im YAML), dann EXP-024 (`ObenMulti-v0`, EXP-022-Rezept), Bedingungen aus `BENCHMARK_OBEN` ins YAML kopieren.
5. Danach Commit (Leon schaut drüber) und `experiments.py done` mit HF-Backup.

### Wichtige Kontextdetails

- Geometrie Handfläche unten (`_probe_oben.txt`): Fingerspitzen max. 62 mm unter der Handfläche (MCP 50–60°); Daumen bei Rotator 90° zeigt offen 71 mm nach unten → näher als 3,5 cm steckt er beim Reset im Objekt. Gewählt: `PALM_GAP_OBEN` 0,035, Mitte (−0,01, −0,33).
- Hand-Root-Frame ohne Drehung: Finger −y, Handfläche −z, Daumen −x → „von oben“ = `HAND_ROT_OBEN` (1,0,0,0); Tisch je Umgebung an die Objektunterseite (Höhe hängt von der Größe ab).
- Neue Experimente „von oben“ brauchen `greifart: oben` im experiment.yaml **und** je Bedingung (sonst Benchmark seitlich); `max_kipp_deg: null` → `--max_kipp_deg -1`.
- Während eines `experiments.py run` keine Dateien ändern, die neue Prozesse importieren (`env_cfg`, `mdp`, `__init__`, `eval_policy`, `experiments`) — jeder Seed/jede Bedingung startet frisch.
- Bewertung dauert ~1,5 min je Bedingung (8 Bedingungen ≈ 12 min je Seed); Training 300 It. ≈ 11 min.
