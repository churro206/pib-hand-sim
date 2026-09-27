# Handoff

_Wird durch `/handoff` am Session-Ende aktualisiert._

---

## Stand 2026-09-27

### Zuletzt gearbeitet an

1. **Branch angelegt**, abgezweigt von `experiment/omnigraph-lightweight` direkt nach
   Abschluss der Sehnendynamik-Arbeit dort (Commit `1d0cd9c`, ADR-009) — der digitale
   Zwilling (v5-USD, Viergelenk-Kopplung, `ros2_control`-Stack) ist damit vollständig
   geerbt, kein Neuaufbau nötig.
2. **`CLAUDE.md` neu geschrieben** für diesen Branch (RL-Grasping-Scope, reale-Hardware-
   Kontext: nur linke Hand, 8 Servos, STM32 Nucleo). Geerbte Docs (`architecture.md`,
   `conventions.md`, `decisions.md`, `current-sprint.md`) mit Hinweisblock versehen, dass
   sie den Sim-Stand zum Abzweigungszeitpunkt beschreiben und dort (auf
   `experiment/omnigraph-lightweight`) weitergepflegt werden, nicht hier.
3. **`docs/rl-grasping-notes.md` angelegt**: Ursprungs-Prompt (von Leon mit Gemini
   vorbereitet) wörtlich festgehalten + Bewertung vor Beginn der Umsetzung — noch **kein**
   Isaac-Lab-Code geschrieben.

### Offene Punkte

- Isaac Lab ist auf der Entwicklungsmaschine nicht installiert — erster Blocker für jeden
  Isaac-Lab-Code (`ManagerBasedRLEnvCfg` etc.).
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
