# EXP-018: Neue Basis: EXP-013 mit Reset ohne Überlappung (ADR-021)

> **Nachtrag 2026-10-09 (ADR-021/022):** 1/5 Seeds lernen greifen: ohne die zufälligen Kontakte der Reset-Stöße fehlt jede Hilfe beim Entdecken — die Lernkurven entscheiden sich in den ersten 10–25 Iterationen. Der Annäherungsterm maß bis EXP-018 alle Handkörper (Unterarmansatz) statt der Fingerspitzen und wäre auch korrigiert für 3–4 cm Fingerweg zu flach: ein Signal fürs Zugreifen fehlte, Seeds scheiterten deshalb am Entdecken des Griffs (ADR-022).

> **Nachtrag 2026-10-09 (ADR-021/022):** Aktionen unbegrenzt (rsl_rl ohne NVIDIAs bounds_loss): Aktionsstrafen und Leitplanke Unruhe messen großteils Rauschen und Überziehen jenseits der Servo-Sättigung, nicht Bewegung (ADR-022).

> **Nachtrag 2026-10-09 (ADR-021/022):** Seeds 47–51 im Nachtlauf 2026-10-09 nachtrainiert (Basis für EXP-019–021 mit 10 Seeds).

**Leistung** 71 % [69–73 %] (erfolgreiche Seeds, IQM über die Objekte; je Objekt Ø 6 cm 77 % · Ø 8 cm 59 % · Quader 72 %) — ggü. EXP-013: P(besser) = 0.11 [0.00–0.33] → gesichert schlechter

**Testobjekte** (nie trainiert, erfolgreiche Seeds, Median): Flasche 62 % · Saftpackung 78 % · Cracker (YCB) 76 % · Zucker (YCB) 87 % · Senf (YCB) 66 %

**Zuverlässigkeit** 1/5 Seeds erfolgreich [1–72 %] — EXP-013: 3/5, exakter Fisher-Test p = 0.52 → nicht unterscheidbar (für eine Aussage ≥ 10 Seeds je Experiment)

**Leitplanken** Unterarm Median [°]: 48.6 > 43 ✗

**Befund** ohne Erfolg: Seed 42 (lernt nicht zu greifen), Seed 44 (lernt nicht zu greifen), Seed 45 (lernt nicht zu greifen), Seed 46 (lernt nicht zu greifen); Engpass Ø 8 cm (59 %); Unruhe 0.51 (EXP-013: 0.76)

**Urteilsvorschlag** (auswertung-v2): **schlechter, Leitplanke verletzt**

![Ergebnis je Bedingung — Punkte = Seeds](diagramme/EXP-018_bedingungen.svg)

<details>
<summary>Ergebnisse je Bedingung (eval-v2, Leitplanken, Fehlerarten, Fingernutzung)</summary>


#### Bedingung `zylinder_seitlich`

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 15.5 % | 0.0 % – 46.5 % | 0.0 % | 80.0 % | 51.0 % / 56.4 % |
| haltequote | 17.3 % | 0.0 % – 51.9 % | 0.0 % | 80.0 % | 58.1 % / 67.2 % |
| Kippwinkel Median [°] | 23.3 | | | | 28 |
| Unterarm Median [°] | 48.6 | | | | 33 |
| Griffkraft Mittel [N] | 91.7 | | | | 93.6 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0 |
| Unruhe | 0.511 | | | | 0.762 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 82.7 %, instabil 0.0 %, anforderung_verletzt 1.8 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -36.2 Prozentpunkte (95-%-KI -86.7 … +27.5)
- Leitplanke: Unterarm Median [°]: 48.6 > 43

Je Seed: 0.0 %, 77.3 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 2.80 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 98/18/0/99/64 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `zylinder_d8_seitlich`

Bedingung `zylinder_d8_seitlich` (Objekt `zylinder_d8`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 11.8 % | 0.0 % – 35.5 % | 0.0 % | 80.0 % | 53.0 % / 60.7 % |
| haltequote | 13.6 % | 0.0 % – 40.9 % | 0.0 % | 80.0 % | 55.6 % / 64.2 % |
| Kippwinkel Median [°] | 26.4 | | | | 22.5 |
| Unterarm Median [°] | 44.8 | | | | 32 |
| Griffkraft Mittel [N] | 91.7 | | | | 88.3 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0 |
| Unruhe | 0.688 | | | | 0.889 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 86.4 %, instabil 0.0 %, anforderung_verletzt 1.8 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -41.8 Prozentpunkte (95-%-KI -88.9 … +16.6)
- Leitplanke: Unterarm Median [°]: 44.8 > 42

Je Seed: 0.0 %, 59.2 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.07 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 99/21/0/100/87 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `quader_seitlich`

Bedingung `quader_seitlich` (Objekt `quader_7x7x20`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 14.4 % | 0.0 % – 43.4 % | 0.0 % | 80.0 % | 44.0 % / 48.0 % |
| haltequote | 14.5 % | 0.0 % – 43.8 % | 0.0 % | 80.0 % | 48.3 % / 55.6 % |
| Kippwinkel Median [°] | 22.2 | | | | 23.4 |
| Unterarm Median [°] | 47.4 | | | | 32.5 |
| Griffkraft Mittel [N] | 84.8 | | | | 82.5 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0174 |
| Unruhe | 1.08 | | | | 0.953 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 85.5 %, instabil 0.0 %, anforderung_verletzt 0.1 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -30.1 Prozentpunkte (95-%-KI -75.7 … +26.6)
- Leitplanke: Unterarm Median [°]: 47.4 > 42.5

Je Seed: 0.0 %, 72.2 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.22 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 99/28/0/100/96 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `flasche_seitlich`

Bedingung `flasche_seitlich` (Objekt `flasche_d7x25`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 12.5 % | 0.0 % – 37.4 % | 0.0 % | 80.0 % | 52.7 % / 59.3 % |
| haltequote | 15.5 % | 0.0 % – 46.7 % | 0.0 % | 80.0 % | 56.3 % / 65.1 % |
| Kippwinkel Median [°] | 21.3 | | | | 24.6 |
| Unterarm Median [°] | 47.7 | | | | 31.4 |
| Griffkraft Mittel [N] | 90.9 | | | | 90.8 |
| Kraft > 15 N [Anteil] | 99.9 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0.0531 | | | | 0.0161 |
| Unruhe | 0.873 | | | | 0.834 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 84.5 %, instabil 0.0 %, anforderung_verletzt 3.0 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -40.9 Prozentpunkte (95-%-KI -88.7 … +18.2)
- Leitplanke: Unterarm Median [°]: 47.7 > 41.4

Je Seed: 0.0 %, 62.3 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.01 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 99/30/1/98/73 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `saftpackung_seitlich`

Bedingung `saftpackung_seitlich` (Objekt `saftpackung_9x6x19`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 15.6 % | 0.0 % – 46.8 % | 0.0 % | 80.0 % | 51.0 % / 57.3 % |
| haltequote | 15.7 % | 0.0 % – 47.1 % | 0.0 % | 80.0 % | 53.9 % / 62.2 % |
| Kippwinkel Median [°] | 20.9 | | | | 24.1 |
| Unterarm Median [°] | 49.4 | | | | 34.8 |
| Griffkraft Mittel [N] | 89.3 | | | | 82.4 |
| Kraft > 15 N [Anteil] | 99.9 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0045 |
| Unruhe | 1.14 | | | | 0.856 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 84.3 %, instabil 0.0 %, anforderung_verletzt 0.1 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -36.0 Prozentpunkte (95-%-KI -86.6 … +28.3)
- Leitplanke: Unterarm Median [°]: 49.4 > 44.8
- Leitplanke: Unruhe: 1.14 > 1.03

Je Seed: 0.0 %, 77.9 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.22 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 98/38/0/100/86 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `ycb_cracker_seitlich`

Bedingung `ycb_cracker_seitlich` (Objekt `ycb_003_cracker`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 15.2 % | 0.0 % – 45.8 % | 0.0 % | 80.0 % | 48.4 % / 55.1 % |
| haltequote | 15.2 % | 0.0 % – 45.9 % | 0.0 % | 80.0 % | 48.8 % / 55.1 % |
| Kippwinkel Median [°] | 17 | | | | 21.5 |
| Unterarm Median [°] | 44.1 | | | | 32.2 |
| Griffkraft Mittel [N] | 98.8 | | | | 84.5 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.087 |
| Unruhe | 0.589 | | | | 0.822 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 84.8 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -33.9 Prozentpunkte (95-%-KI -81.6 … +28.2)
- Leitplanke: Unterarm Median [°]: 44.1 > 42.2

Je Seed: 0.0 %, 76.1 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 3.10 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/11/0/100/99 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `ycb_zucker_seitlich`

Bedingung `ycb_zucker_seitlich` (Objekt `ycb_004_zucker`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 17.5 % | 0.0 % – 52.4 % | 0.0 % | 80.0 % | 53.9 % / 60.5 % |
| haltequote | 18.9 % | 0.0 % – 56.7 % | 0.0 % | 80.0 % | 56.3 % / 63.5 % |
| Kippwinkel Median [°] | 26.6 | | | | 21.2 |
| Unterarm Median [°] | 13 | | | | 35.6 |
| Griffkraft Mittel [N] | 75.3 | | | | 85.6 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0.0787 | | | | 0.142 |
| Unruhe | 0.232 | | | | 0.528 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 81.1 %, instabil 0.0 %, anforderung_verletzt 1.4 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -37.1 Prozentpunkte (95-%-KI -90.7 … +32.7)
- Leitplanke: Kippwinkel Median [°]: 26.6 > 26.2

Je Seed: 0.0 %, 87.4 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 2.77 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/23/1/97/55 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

#### Bedingung `ycb_senf_seitlich`

Bedingung `ycb_senf_seitlich` (Objekt `ycb_006_senf`, Kippwinkel ≤ 45°), Protokoll eval-v2, 5 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 13.1 % | 0.0 % – 39.4 % | 0.0 % | 80.0 % | 48.6 % / 52.4 % |
| haltequote | 16.8 % | 0.0 % – 50.4 % | 0.0 % | 80.0 % | 52.3 % / 56.6 % |
| Kippwinkel Median [°] | 31.9 | | | | 23.2 |
| Unterarm Median [°] | 46.9 | | | | 33.4 |
| Griffkraft Mittel [N] | 84.4 | | | | 90.7 |
| Kraft > 15 N [Anteil] | 100.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 99.8 % | | | | 100.0 % |
| Absinken [mm] | 0.711 | | | | 0.539 |
| Unruhe | 0.93 | | | | 0.432 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 83.2 %, instabil 0.0 %, anforderung_verletzt 3.7 %

**Urteilsvorschlag: kein messbarer Unterschied** (gegenüber EXP-013)
Unterschied Aufgabenerfolg -36.2 Prozentpunkte (95-%-KI -83.2 … +20.4)
- Leitplanke: Kippwinkel Median [°]: 31.9 > 28.2
- Leitplanke: Unterarm Median [°]: 46.9 > 43.4
- Leitplanke: Unruhe: 0.93 > 0.519

Je Seed: 0.0 %, 65.5 %, 0.0 %, 0.0 %, 0.0 %

Fingernutzung (Haltephase): im Mittel 2.68 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): –/–/–/–/– · 100/20/0/97/51 · –/–/–/–/– · –/–/–/–/– · –/–/–/–/–

</details>

<details>
<summary>Trainingsverlauf</summary>


Seeds dünn, Mittel kräftig, Eltern gestrichelt (nur Abbrüche/PPO — Trainings-Belohnung ist zwischen Experimenten nicht vergleichbar); geglättet, x = Simulationsschritte. Endwerte = Mittel der letzten 10 Iterationen (Belohnungsanteile je Sekunde Episode).

| Größe | Seed 42 | Seed 43 | Seed 44 | Seed 45 | Seed 46 | Mittel |
|---|---|---|---|---|---|---|
| mean_reward | 1.59 | 22.3 | 1.58 | 1.59 | 1.62 | 5.74 |
| action_l2 | -0.00827 | -0.0805 | -0.00696 | -0.00572 | -0.00398 | -0.0211 |
| action_rate_l2 | -0.00918 | -0.0723 | -0.00862 | -0.00719 | -0.00436 | -0.0203 |
| early_termination | 0 | -5.51e-06 | 0 | 0 | 0 | -1.1e-06 |
| fingertips_to_object | 0.161 | 0.364 | 0.158 | 0.157 | 0.152 | 0.198 |
| good_contact | 0.000166 | 0.319 | 0.000117 | 2.02e-06 | 0 | 0.0638 |
| held | 0 | 0.675 | 0 | 0 | 0 | 0.135 |
| success | 0.207 | 2.49 | 0.208 | 0.21 | 0.216 | 0.666 |
| upright | 0 | 1.29 | 0 | 0 | 0 | 0.259 |
| object_dropped | 100.0 % | 33.7 % | 100.0 % | 100.0 % | 100.0 % | 86.7 % |
| mean_noise_std | 0.454 | 0.858 | 0.445 | 0.398 | 0.31 | 0.493 |

![Lernkurve](diagramme/EXP-018_lernkurve.svg)

![Belohnungsanteile](diagramme/EXP-018_belohnung.svg)

![Abbrüche](diagramme/EXP-018_abbrueche.svg)

![PPO-Diagnose](diagramme/EXP-018_ppo.svg)

</details>

<details>
<summary>Netz, Training und Konfiguration</summary>

Actor [256, 128, 64] (elu), 68808 Parameter, 105 Eingänge (Verlauf 5) · Critic [512, 256, 128] · PPO: Lernrate 0.001, Entropie 0.005, 5 Epochen × 4 Mini-Batches, 32 Schritte/Umgebung · 1024 Umgebungen × 300 Iterationen

Geplante Änderung: Reset ohne Überlappung (ADR-021): Startbeugung Daumen-MCP 0–4° statt 0–15°, Handgelenk −1–0° statt −3–0°, Abstand zur Handfläche nach der Gierdrehung (reset_object_gap_aware). Sonst wie EXP-013 (HeavyMulti-v0, 300 It. × 1024, 5 Seeds); YCB-Bedingungen nur in der Bewertung.

Konfiguration gegenüber EXP-013 (5 Unterschiede):

- `env.events.place_objects.params.lift: ∅ → 0.0`
- `env.events.place_objects.params.root_height: ∅ → None`
- `env.events.reset_hand.params.ranges_deg.thumb_left_proximal: (0.0, 15.0) → (0.0, 4.0)`
- `env.events.reset_hand.params.ranges_deg.wrist_left: (-3.0, 0.0) → (-1.0, 0.0)`
- `env.events.reset_object.func: isaaclab.envs.mdp.events:reset_root_state_uniform → pib_grasp.mdp:reset_object_gap_aware`

</details>
