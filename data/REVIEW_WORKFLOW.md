# Review-Workflow: vom Judge geflaggte Einträge prüfen & korrigieren

Nächster Projektschritt: die vom Judge (Stufe 4b) markierten Einträge menschlich prüfen,
korrigieren und die Korrekturen in den RDF-Graphen zurückführen — **ohne** den Audit-Trail
zu zerstören. Leitprinzip: Der Mensch ist die letzte Instanz; Rohdaten (`entries_raw/`,
`entries_judged/`) bleiben unverändert, Korrekturen leben in einer eigenen Ablage.

---

## 0 · Beteiligte Dateien (alle relativ zu `PARS_I_A-B/`)

| Datei/Ordner | Rolle im Review |
|---|---|
| `entries_validated/review_report.json` | **Arbeitsliste**: alle Flags mit Feld, Problem, Schweregrad, `suggested_fix` |
| `pages/page_XXXX.png` | **Quellbild = Wahrheit** — hier wird verifiziert |
| `entries_validated/provincia_entries.json` | die konsolidierten Einträge (Stand vor Korrektur) |
| `entries_raw/page_XXXX.json` | Original-Extraktion (Proposer) — nur lesen |
| `entries_judged/page_XXXX.json` | volles Judge-Urteil je Seite — nur lesen |
| `entries_corrected_hutter/page_XXXX.json` | **deine Korrekturen** (vollständiger Eintrag im selben Schema) |

Regel: **niemals** `entries_raw/` oder `entries_judged/` ändern. Korrekturen kommen ausschließlich
nach `entries_corrected_hutter/`.

---

## 1 · Triage (Reihenfolge festlegen)

Öffne `review_report.json` und arbeite **nach Schweregrad**, nicht nach Seitenzahl:

1. **`major_issues`** (hier: 1 Fall, A 1089) → immer prüfen.
2. **`missed_entries_reported_by_judge`** → prüfen, ob der Eintrag wirklich relevant ist.
   *Hinweis:* Den gemeldeten „praefectus Aegypti" (PIR 1467) hast du bereits geklärt — die
   Statthalterschaft gehört A 1465 (Galatia); Korrektur liegt in `entries_corrected_hutter/page_0313.json`.
3. **`medium`** → prüfen (oft Datierungs- oder Zuordnungsfragen).
4. **`low`** (z. B. „exact_text nicht wörtlich", Kasusform `province_text`) → meist inhaltlich
   unkritisch. Als **Sammelkorrektur** behandeln oder bewusst akzeptieren.

So vermeidest du, dich an 39 Kleinst-Flags aufzuhalten, während die wenigen echten Fälle warten.

---

## 2 · Einzelfall prüfen (pro geflaggtem Eintrag)

Für jeden Eintrag aus der Triage:

1. **Bild öffnen:** `pages/page_{source_page}.png`. Das Bild entscheidet, nicht der OCR-Text.
2. **Flag lesen:** in `review_report.json` das `field` (z. B. `governorship_factoids.gov_1.exact_text`),
   das `issue` und den `suggested_fix`.
3. **Vergleichen:** den betroffenen Wert in `provincia_entries.json` (bzw. `entries_raw/`) gegen das Bild.
4. **Entscheiden:**
   - *Judge hat recht* → Wert am Bild korrigieren (oder `suggested_fix` übernehmen, wenn am Bild bestätigt).
   - *Judge irrt* → Wert belassen, aber die Entscheidung dokumentieren (siehe Schritt 5).
5. **Korrektur ablegen:** den **vollständigen** korrigierten Eintrag (gleiches JSON-Schema wie
   `entries_raw/`) in `entries_corrected_hutter/page_XXXX.json` speichern.

### Häufige Flag-Typen und was zu tun ist
- **`exact_text` nicht wörtlich** → wörtliches Zitat vom Bild übernehmen (mit Klammerzusätzen wie
  `(v. 3, 9. t. 1)`), Datum/Kommentar in `date_text`/`notes` auslagern.
- **`province_text` Kasus** → wörtliche Form vom Bild (z. B. `Pannoniae inferioris`); `province_normalized`
  bleibt der Nominativ aus der Registry.
- **`date_normalized_start/end`** → nur setzen, was belegt ist; Unsicheres in `notes`, `certainty` senken.
- **falsche Person (major)** → Faktoid der richtigen Person zuordnen bzw. entfernen; im Zweifel
  `needs_review` lassen.

---

## 3 · Review-Status mitführen (Audit-Trail)

In jeden korrigierten Eintrag ein kleines Review-Objekt schreiben, z. B.:

```json
"review": {
  "verdict": "human_confirmed",          // oder "human_corrected" / "judge_wrong"
  "reviewed_by": "Hutter",
  "reviewed_on": "2026-07-01",
  "note": "exact_text am Bild verifiziert; Datum auf 107 konservativ gesetzt."
},
"needs_review": false
```

So bleibt nachvollziehbar, **wer wann was** entschieden hat — auch wenn der Judge widerlegt wurde.

---

## 4 · Korrekturen in den Graphen bringen

Die Korrekturen müssen die validierten Daten **überlagern**, bevor Stufe 6 läuft:

1. (Einmalig nötiges Hilfsskript) `apply_corrections`: liest `provincia_entries.json` + alle
   `entries_corrected_hutter/page_*.json`, ersetzt die Einträge mit gleicher `pir_reference`
   durch die korrigierte Fassung und schreibt `provincia_entries.json` zurück.
2. **`06_json_to_rdf.py` erneut ausführen** → neuer Graph (`rdf/provincia_graph.ttl` …).

> Wichtig: Stufe 5 (`05_validate_entries.py`) danach **nicht** erneut laufen lassen — sie würde
> `provincia_entries.json` aus `entries_raw/`+`entries_judged/` neu erzeugen und deine Overlays
> überschreiben. Reihenfolge daher: 5 → (Review) → apply_corrections → 6.

*(Dieses Overlay-Skript existiert noch nicht — ich kann es dir bauen, dann ist Schritt 4
ein einziger Befehl.)*

---

## 5 · Verifikation & Abschluss

- **SPARQL-Stichprobe** auf die korrigierten Personen/Provinzen (Abfragen aus
  `SPARQL-Abfragen PROVINCIA.txt`).
- Prüfen, dass im Graphen für korrigierte Einträge `ont:needsReview` jetzt `false` ist.
- **Korrektur-Log** führen (kurze Begründung je Fall) — entweder im `review`-Feld oder in
  `entries_corrected_hutter/CORRECTIONS.md`.

---

## 6 · Optionaler Rückkanal (Qualität verbessern)

Wiederkehrende `low`-Flags (z. B. „exact_text nicht wörtlich") sind ein Signal für den
**Proposer-System-Prompt** (`04_extract_entries_api.py`). Wenn dieselbe Fehlerklasse oft auftritt,
lohnt eine Prompt-Anpassung mehr als 39 Einzelkorrekturen — danach denselben Band neu extrahieren
und vergleichen.

---

### Kurzfassung
**Triage nach Schwere → am Bild prüfen → vollständigen Eintrag in `entries_corrected_hutter/`
korrigieren → Review-Status setzen → `apply_corrections` + `06_json_to_rdf` → per SPARQL verifizieren.**
