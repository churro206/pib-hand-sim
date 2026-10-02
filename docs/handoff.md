# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-10-02

### Zuletzt gearbeitet an

Keine neue Arbeit seit dem 2026-09-27-Stand — diese Session begann nur mit einer
Push-Status-Prüfung (beide Branches `experiment/omnigraph-lightweight`/
`feature/rl-grasping` bestätigt sauber auf `origin`, keine lokalen Commits ausstehend) und
diesem Handoff-Eintrag. Der unten stehende Stand ist inhaltlich identisch zur letzten
Session (Branch-Setup, `CLAUDE.md`, `docs/rl-grasping-notes.md`) — siehe Commit `085c5d8`.

### Offene Punkte

- Isaac Lab ist auf der Entwicklungsmaschine nicht installiert — erster Blocker für jeden
  Isaac-Lab-Code (`ManagerBasedRLEnvCfg` etc.). Noch nicht angegangen.
- Der Ursprungs-Prompt geht von "8 DOFs Unterarm+Handgelenk" als direktem Aktionsraum aus —
  das sind die 8 realen Servos, kein 1:1-URDF-Joint-Mapping. Muss beim Schreiben von
  `ArticulationCfg` explizit hergestellt werden, nicht aus dem Prompt übernehmen.
- Kontaktsensor-Abdeckung (nur `index_right` in Sim) und `config/pib_hand_config_v5.py`
  sind Abhängigkeiten von `experiment/omnigraph-lightweight`, dort offen — nicht auf
  diesem Branch zu lösen, aber blockierend für einen vollständigen Observation-Space.

### Nächste Schritte (in Reihenfolge)

1. Isaac Lab installieren, Version/API gegen `docs/rl-grasping-notes.md`s Kritikpunkte
   prüfen (keine Klassennamen/Signaturen raten).
2. Echte v5-Gelenkstruktur (Namen, Limits) gegen die 8-Servo-Beschreibung abgleichen,
   bevor `ArticulationCfg` geschrieben wird.
3. `ArticulationCfg` + Aktionsraum-Mapping (8 Servo-DOFs → volle Gelenkstruktur inkl.
   `FourBar`-Kopplung für PIP/DIP/IP) als erster Baustein von Aufgabe 1 aus dem
   Ursprungs-Prompt.

### Wichtige Kontextdetails

- **Reale Hand**: nur links existiert physisch, 8 Servos (Handgelenk, Unterarmdrehung,
  Daumen-Rotator, 5× Finger-/Daumen-MCP), PIP/DIP/IP mechanisch gekoppelt — siehe
  `CLAUDE.md` „KRITISCHER Design-Punkt: Aktionsraum". Das ist der wichtigste Punkt, den
  jede künftige Session hier zuerst verinnerlichen muss, bevor Env-Code entsteht.
- Geerbte Docs (`architecture.md`/`conventions.md`/`decisions.md`/`current-sprint.md`)
  NICHT als "hier zu pflegen" missverstehen — sie sind ein Snapshot der Sim-Seite, echte
  Änderungen an der Simulation/dem Action Graph gehören auf
  `experiment/omnigraph-lightweight`.
- ADR-Nummerierung läuft auf diesem Branch unabhängig weiter (nächste eigene Entscheidung
  hier wäre ADR-010, unabhängig davon, was `experiment/omnigraph-lightweight` parallel an
  eigenen ADR-010 etc. bekommt — Branches sind komplett getrennte `decisions.md`-Historien
  ab jetzt).
- Falls zwischen den Sessions auf `experiment/omnigraph-lightweight` weitergearbeitet wurde
  (z.B. restliche Kontaktsensoren, `config/pib_hand_config_v5.py`): dort erst `git pull`
  und den dortigen `docs/handoff.md`-Stand prüfen, bevor hier auf diesem Branch gemerget
  oder erneut abgezweigt wird — dieser Branch war zum Zeitpunkt dieses Eintrags noch exakt
  auf dem Stand von Commit `1d0cd9c`.
