# EXP-015: Regel-Baseline: schließen bis Kontakt, taktiler Reflex (kein RL)

> **Nachtrag 2026-10-09 (ADR-021/022):** Nachbewertet unter eval-v2: 68 % — RL gesichert besser; der Schluss „bis auf wenige PP an RL“ gilt nur unter eval-v1.

**Leistung** 68 % [66–70 %] (erfolgreiche Seeds, IQM über die Objekte; je Objekt Ø 6 cm 74 % · Ø 8 cm 68 % · Quader 61 %) — ggü. EXP-013: P(besser) = 0.11 [0.00–0.33] → gesichert schlechter

**Testobjekte** (nie trainiert, erfolgreiche Seeds, Median): Flasche 72 % · Saftpackung 72 % · Cracker (YCB) 66 % · Zucker (YCB) 68 % · Senf (YCB) 59 %

**Zuverlässigkeit** 1/1 Seeds erfolgreich [2–100 %] — EXP-013: 3/5, exakter Fisher-Test p = 1.00 → nicht unterscheidbar (für eine Aussage ≥ 10 Seeds je Experiment)

**Leitplanken** eingehalten

**Befund** Engpass Quader (61 %); Kippwinkel 18° (EXP-013: 28°); Finger am Objekt 4.8 (EXP-013: 2.9); Unruhe 0.01 (EXP-013: 0.76)

**Urteilsvorschlag** (auswertung-v2): **schlechter**

**Beste Videos** (Seed 0, 3 Episoden): [Ø 6 cm](beste_videos/EXP-015_zylinder_d6_s0.mp4) · [Ø 8 cm](beste_videos/EXP-015_zylinder_d8_s0.mp4) · [Quader](beste_videos/EXP-015_quader_7x7x20_s0.mp4)

![Ergebnis je Bedingung — Punkte = Seeds](diagramme/EXP-015_bedingungen.svg)

<details>
<summary>Ergebnisse je Bedingung (eval-v2, Leitplanken, Fehlerarten, Fingernutzung)</summary>


#### Bedingung `zylinder_seitlich`

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 74.4 % | 71.8 % – 77.0 % | 74.4 % | 0.0 % | 51.0 % / 56.4 % |
| haltequote | 74.4 % | 71.8 % – 77.0 % | 74.4 % | 0.0 % | 58.1 % / 67.2 % |
| Kippwinkel Median [°] | 18.4 | | | | 28 |
| Unterarm Median [°] | 0.262 | | | | 33 |
| Griffkraft Mittel [N] | 82.3 | | | | 93.6 |
| Kraft > 15 N [Anteil] | 96.0 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 1.8 % | | | | 100.0 % |
| Absinken [mm] | 0.0216 | | | | 0 |
| Unruhe | 0.0081 | | | | 0.762 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 25.6 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +23.1 Prozentpunkte (95-%-KI -12.2 … +58.5)

Je Seed: 74.4 %

Fingernutzung (Haltephase): im Mittel 4.80 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 97/99/100/95/89

#### Bedingung `zylinder_d8_seitlich`

Bedingung `zylinder_d8_seitlich` (Objekt `zylinder_d8`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 67.9 % | 65.1 % – 70.8 % | 67.9 % | 0.0 % | 53.0 % / 60.7 % |
| haltequote | 67.9 % | 64.9 % – 70.9 % | 67.9 % | 0.0 % | 55.6 % / 64.2 % |
| Kippwinkel Median [°] | 12.7 | | | | 22.5 |
| Unterarm Median [°] | 0.276 | | | | 32 |
| Griffkraft Mittel [N] | 72.1 | | | | 88.3 |
| Kraft > 15 N [Anteil] | 99.8 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0 |
| Unruhe | 0.00814 | | | | 0.889 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 32.1 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +14.5 Prozentpunkte (95-%-KI -21.5 … +51.3)

Je Seed: 67.9 %

Fingernutzung (Haltephase): im Mittel 4.89 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/100/100/97/92

#### Bedingung `quader_seitlich`

Bedingung `quader_seitlich` (Objekt `quader_7x7x20`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 61.4 % | 58.2 % – 64.3 % | 61.4 % | 0.0 % | 44.0 % / 48.0 % |
| haltequote | 61.4 % | 58.2 % – 64.4 % | 61.4 % | 0.0 % | 48.3 % / 55.6 % |
| Kippwinkel Median [°] | 13.9 | | | | 23.4 |
| Unterarm Median [°] | 0.291 | | | | 32.5 |
| Griffkraft Mittel [N] | 72.3 | | | | 82.5 |
| Kraft > 15 N [Anteil] | 92.4 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 0.7 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0174 |
| Unruhe | 0.00811 | | | | 0.953 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 38.6 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +17.1 Prozentpunkte (95-%-KI -14.4 … +48.7)

Je Seed: 61.4 %

Fingernutzung (Haltephase): im Mittel 4.79 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 97/98/99/97/88

#### Bedingung `flasche_seitlich`

Bedingung `flasche_seitlich` (Objekt `flasche_d7x25`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 71.5 % | 68.7 % – 74.2 % | 71.5 % | 0.0 % | 52.7 % / 59.3 % |
| haltequote | 71.5 % | 68.6 % – 74.4 % | 71.5 % | 0.0 % | 56.3 % / 65.1 % |
| Kippwinkel Median [°] | 15 | | | | 24.6 |
| Unterarm Median [°] | 0.272 | | | | 31.4 |
| Griffkraft Mittel [N] | 77.1 | | | | 90.8 |
| Kraft > 15 N [Anteil] | 99.5 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 0.7 % | | | | 100.0 % |
| Absinken [mm] | 0.012 | | | | 0.0161 |
| Unruhe | 0.00813 | | | | 0.834 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 28.5 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +18.4 Prozentpunkte (95-%-KI -17.7 … +54.9)

Je Seed: 71.5 %

Fingernutzung (Haltephase): im Mittel 4.80 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/100/100/93/87

#### Bedingung `saftpackung_seitlich`

Bedingung `saftpackung_seitlich` (Objekt `saftpackung_9x6x19`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 72.3 % | 69.5 % – 75.0 % | 72.3 % | 0.0 % | 51.0 % / 57.3 % |
| haltequote | 72.3 % | 69.5 % – 74.9 % | 72.3 % | 0.0 % | 53.9 % / 62.2 % |
| Kippwinkel Median [°] | 15.7 | | | | 24.1 |
| Unterarm Median [°] | 0.353 | | | | 34.8 |
| Griffkraft Mittel [N] | 70.8 | | | | 82.4 |
| Kraft > 15 N [Anteil] | 88.9 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 0.9 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0045 |
| Unruhe | 0.0082 | | | | 0.856 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 27.7 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +21.0 Prozentpunkte (95-%-KI -14.4 … +56.7)

Je Seed: 72.3 %

Fingernutzung (Haltephase): im Mittel 4.89 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 94/100/100/99/96

</details>

<details>
<summary>Videos aller Seeds</summary>

16 Umgebungen, eine Episode (nicht im Git, Hugging Face).

| Objekt | Seed 0 |
|---|---|
| `quader_7x7x20` | [▶](videos/EXP-015_quader_7x7x20_s0.mp4) |
| `zylinder_d6` | [▶](videos/EXP-015_zylinder_d6_s0.mp4) |
| `zylinder_d8` | [▶](videos/EXP-015_zylinder_d8_s0.mp4) |

</details>

<details>
<summary>Regel und Parameterwahl</summary>

Regel `bis_kontakt`, gewählt `schliessen=0.4,nachdruck_deg=2` aus dem Raster (Aufgabenerfolg mit Seed 2000, Mittel über die Benchmark-Objekte): `schliessen=0.4,nachdruck_deg=2` 67 %, `schliessen=0.4,nachdruck_deg=4` 39 %, `schliessen=0.4,nachdruck_deg=5.7` 19 %

</details>
