# EXP-014: Regel-Baseline: alle Finger schließen (kein RL)

> **Nachtrag 2026-10-09 (ADR-021/022):** Nachbewertet unter eval-v2: 69 % — RL (EXP-013, 83 %) gesichert besser; der Schluss „Regel bis auf 6 PP an RL“ gilt nur unter eval-v1 (Reset-Stöße trafen RL stärker).

**Leistung** 69 % [67–71 %] (erfolgreiche Seeds, IQM über die Objekte; je Objekt Ø 6 cm 78 % · Ø 8 cm 69 % · Quader 59 %) — ggü. EXP-013: P(besser) = 0.00 [0.00–0.00] → gesichert schlechter

**Testobjekte** (nie trainiert, erfolgreiche Seeds, Median): Flasche 72 % · Saftpackung 71 % · Cracker (YCB) 68 % · Zucker (YCB) 53 % · Senf (YCB) 45 %

**Zuverlässigkeit** 1/1 Seeds erfolgreich [2–100 %] — EXP-013: 3/5, exakter Fisher-Test p = 1.00 → nicht unterscheidbar (für eine Aussage ≥ 10 Seeds je Experiment)

**Leitplanken** eingehalten

**Befund** Engpass Quader (59 %); Kippwinkel 16° (EXP-013: 28°); Finger am Objekt 4.9 (EXP-013: 2.9); Unruhe 0.01 (EXP-013: 0.76)

**Urteilsvorschlag** (auswertung-v2): **schlechter**

**Beste Videos** (Seed 0, 3 Episoden): [Ø 6 cm](beste_videos/EXP-014_zylinder_d6_s0.mp4) · [Ø 8 cm](beste_videos/EXP-014_zylinder_d8_s0.mp4) · [Quader](beste_videos/EXP-014_quader_7x7x20_s0.mp4)

![Ergebnis je Bedingung — Punkte = Seeds](diagramme/EXP-014_bedingungen.svg)

<details>
<summary>Ergebnisse je Bedingung (eval-v2, Leitplanken, Fehlerarten, Fingernutzung)</summary>


#### Bedingung `zylinder_seitlich`

Bedingung `zylinder_seitlich` (Objekt `zylinder_d6`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 77.6 % | 75.1 % – 80.3 % | 77.6 % | 0.0 % | 51.0 % / 56.4 % |
| haltequote | 77.6 % | 75.0 % – 80.3 % | 77.6 % | 0.0 % | 58.1 % / 67.2 % |
| Kippwinkel Median [°] | 15.8 | | | | 28 |
| Unterarm Median [°] | 0.261 | | | | 33 |
| Griffkraft Mittel [N] | 46.6 | | | | 93.6 |
| Kraft > 15 N [Anteil] | 92.9 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0.00333 | | | | 0 |
| Unruhe | 0.00573 | | | | 0.762 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 22.4 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +26.4 Prozentpunkte (95-%-KI -8.8 … +62.0)

Je Seed: 77.6 %

Fingernutzung (Haltephase): im Mittel 4.87 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 99/99/100/98/91

#### Bedingung `zylinder_d8_seitlich`

Bedingung `zylinder_d8_seitlich` (Objekt `zylinder_d8`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 69.2 % | 66.3 % – 72.1 % | 69.2 % | 0.0 % | 53.0 % / 60.7 % |
| haltequote | 69.2 % | 66.3 % – 72.1 % | 69.2 % | 0.0 % | 55.6 % / 64.2 % |
| Kippwinkel Median [°] | 10.9 | | | | 22.5 |
| Unterarm Median [°] | 0.27 | | | | 32 |
| Griffkraft Mittel [N] | 40.9 | | | | 88.3 |
| Kraft > 15 N [Anteil] | 96.4 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0 |
| Unruhe | 0.0057 | | | | 0.889 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 30.8 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +15.8 Prozentpunkte (95-%-KI -20.3 … +52.5)

Je Seed: 69.2 %

Fingernutzung (Haltephase): im Mittel 4.96 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/100/100/99/97

#### Bedingung `quader_seitlich`

Bedingung `quader_seitlich` (Objekt `quader_7x7x20`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 58.7 % | 55.6 % – 61.7 % | 58.7 % | 0.0 % | 44.0 % / 48.0 % |
| haltequote | 58.7 % | 55.6 % – 61.8 % | 58.7 % | 0.0 % | 48.3 % / 55.6 % |
| Kippwinkel Median [°] | 12.8 | | | | 23.4 |
| Unterarm Median [°] | 0.286 | | | | 32.5 |
| Griffkraft Mittel [N] | 40.6 | | | | 82.5 |
| Kraft > 15 N [Anteil] | 86.4 % | | | | 100.0 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0174 |
| Unruhe | 0.00572 | | | | 0.953 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 41.3 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +14.4 Prozentpunkte (95-%-KI -17.0 … +45.9)

Je Seed: 58.7 %

Fingernutzung (Haltephase): im Mittel 4.77 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 96/97/99/97/88

#### Bedingung `flasche_seitlich`

Bedingung `flasche_seitlich` (Objekt `flasche_d7x25`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 72.2 % | 69.5 % – 75.0 % | 72.2 % | 0.0 % | 52.7 % / 59.3 % |
| haltequote | 72.2 % | 69.4 % – 75.0 % | 72.2 % | 0.0 % | 56.3 % / 65.1 % |
| Kippwinkel Median [°] | 13.4 | | | | 24.6 |
| Unterarm Median [°] | 0.261 | | | | 31.4 |
| Griffkraft Mittel [N] | 43.3 | | | | 90.8 |
| Kraft > 15 N [Anteil] | 90.3 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0 | | | | 0.0161 |
| Unruhe | 0.00577 | | | | 0.834 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 27.8 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +19.0 Prozentpunkte (95-%-KI -17.0 … +55.7)

Je Seed: 72.2 %

Fingernutzung (Haltephase): im Mittel 4.84 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 100/100/100/95/89

#### Bedingung `saftpackung_seitlich`

Bedingung `saftpackung_seitlich` (Objekt `saftpackung_9x6x19`, Kippwinkel ≤ 45°), Protokoll eval-v2, 1 Seed(s); Spalte EXP-013 unter derselben Anforderung

| Metrik | Mittel | 95-%-KI | IQM | Fehlschlag-Seeds (< 50 %) | EXP-013 (Mittel / IQM) |
|---|---|---|---|---|---|
| aufgabenerfolg | 71.1 % | 68.2 % – 73.8 % | 71.1 % | 0.0 % | 51.0 % / 57.3 % |
| haltequote | 71.1 % | 68.3 % – 73.7 % | 71.1 % | 0.0 % | 53.9 % / 62.2 % |
| Kippwinkel Median [°] | 14.3 | | | | 24.1 |
| Unterarm Median [°] | 0.318 | | | | 34.8 |
| Griffkraft Mittel [N] | 39.8 | | | | 82.4 |
| Kraft > 15 N [Anteil] | 86.2 % | | | | 99.9 % |
| Stall-Anteil [Anteil] | 0.0 % | | | | 100.0 % |
| Absinken [mm] | 0.00573 | | | | 0.0045 |
| Unruhe | 0.0058 | | | | 0.856 |
| Unruhe wirksam (Aktion auf ±1 begrenzt) | – | | | | – |

Fehlerarten: startfehler 0.0 %, gefallen 28.9 %, instabil 0.0 %, anforderung_verletzt 0.0 %

**Urteilsvorschlag: kein messbarer Unterschied (vorläufig: < 3 Seeds)** (gegenüber EXP-013)
Unterschied Aufgabenerfolg +19.8 Prozentpunkte (95-%-KI -15.3 … +55.5)

Je Seed: 71.1 %

Fingernutzung (Haltephase): im Mittel 4.88 Finger am Objekt; Kontaktanteil je Seed (Daumen, Zeige, Mittel, Ring, klein): 94/99/100/99/95

</details>

<details>
<summary>Videos aller Seeds</summary>

16 Umgebungen, eine Episode (nicht im Git, Hugging Face).

| Objekt | Seed 0 |
|---|---|
| `quader_7x7x20` | [▶](videos/EXP-014_quader_7x7x20_s0.mp4) |
| `zylinder_d6` | [▶](videos/EXP-014_zylinder_d6_s0.mp4) |
| `zylinder_d8` | [▶](videos/EXP-014_zylinder_d8_s0.mp4) |

</details>

<details>
<summary>Regel und Parameterwahl</summary>

Regel `alle_schliessen`, gewählt `schliessen=0.2` aus dem Raster (Aufgabenerfolg mit Seed 2000, Mittel über die Benchmark-Objekte): `schliessen=0.2` 68 %, `schliessen=0.4` 65 %, `schliessen=0.8` 34 %

</details>
