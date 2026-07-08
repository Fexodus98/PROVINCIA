# PROVINCIA

**Prosopographische Vernetzung und Informationsgraphen für Computergestützte Intelligente Analyse**

PROVINCIA ist eine modulare Pipeline, die einen gedruckten Band der *Prosopographia Imperii Romani* (PIR²)
quellentreu in einen abfragbaren RDF-Wissensgraphen über die kaiserlichen Provinzstatthalter
(*legatus Augusti pro praetore provinciae*) überführt. Sie kombiniert deterministische Standardverfahren
(PDF-Rendering, OCR, Regex-Filterung, RDF-Erzeugung) mit einem gezielten, kontrollierten Einsatz
Vision-fähiger Large Language Models für die Extraktion und eine unabhängige Prüfung („Proposer–Judge“).
Ein menschlicher Review als letzte Instanz sichert Qualität und Auditierbarkeit.

Testband: **PIR² Pars I, A–B** (396 Seiten). Ergebnis: ein kollisionsfreier Graph mit
**44 Personen, 61 Statthalterschaften, 25 Provinzen**, serialisiert in vier Formaten.

## Struktur

```
pipeline/     Die nummerierten Verarbeitungsschritte (Stufe 1–8) + Konfiguration
data/         Strukturierte Ergebnisse (JSON), RDF-Graph, Review-Protokolle, Korrekturskripte
```

## Pipeline (Stufen)

| Stufe | Skript | Aufgabe |
|---|---|---|
| 1 | `01_render_pdf.py` | Seiten aus der PDF in Bilder rendern (PyMuPDF, 300 dpi) |
| 2 | `02_ocr_pages.py` | OCR mit Tesseract (LSTM, PSM 6, lat+eng) → Text + TSV mit Konfidenz |
| 3 | `03_find_candidates.py` | Kandidatenfilter: Regex auf die Statthalter-Formel |
| 4 | `04_extract_entries_api.py` | Extraktion durch ein Vision-LLM (Proposer), striktes JSON |
| 4b | `04b_judge_entries.py` | Unabhängige Prüfung durch ein zweites LLM (Judge) |
| 5 | `05_validate_entries.py` | Deterministische Validierung, Normalisierung, Cross-Page-Merge |
| 6 | `06_json_to_rdf.py` | Erzeugung des RDF-Graphen (rdflib) in vier Serialisierungen |
| 7/8 | `07_eval_ocr.py`, `08_llm_ocr_eval.py` | Quantitative OCR-Evaluation (CER/WER) |

Der menschliche Review-Workflow ist in [`data/REVIEW_WORKFLOW.md`](data/REVIEW_WORKFLOW.md) beschrieben;
sämtliche Einzelentscheidungen sind in [`data/REVIEW_DECISIONS.md`](data/REVIEW_DECISIONS.md) protokolliert.
Korrekturen werden isoliert in `data/entries_corrected_hutter/` geführt und via `apply_corrections.py`
(zwischen Stufe 5 und 6) in den Graphen eingespielt.

## Ausführung

```bash
pip install -r requirements.txt
# Tesseract-OCR muss separat installiert sein (lat+eng Sprachpakete).
# Ein Mistral-API-Key wird über eine Umgebungsvariable erwartet (kein Key im Code).

# Beispiel (Pfade über Umgebungsvariablen):
export PROVINCIA_BASE_DIR=/pfad/zu/data
export PROVINCIA_OUTPUT_DIR=/pfad/zu/data
python pipeline/06_json_to_rdf.py     # baut den RDF-Graphen aus data/entries_validated/
```

Die Stufen sind einzeln lauffähig; die Reihenfolge ist 1 → 2 → 3 → 4 → 4b → 5 → (Review) → 6 → 7/8.

## Daten und Urheberrecht

Enthalten sind ausschließlich die **strukturierten Extraktionsergebnisse** (Fakten und kurze,
wörtliche Beleg-Zitate) sowie der daraus erzeugte RDF-Graph. **Nicht enthalten** sind die
Seiten-Scans, die vollständigen OCR-Volltexte und die Ground-Truth-Transkriptionen der PIR²:
Diese sind urheberrechtlich geschützt und werden bewusst ausgeschlossen. Der Graph modelliert
prosopographische Aussagen (Person – ist Statthalter von – Provinz) mit Quellseite und Beleg;
jede Aussage bleibt bis zur Buchseite rückverfolgbar.

## Lizenz

Der **Code** steht unter der MIT-Lizenz (siehe `LICENSE`). Die **Daten** sind aus der PIR² abgeleitet;
es werden nur Fakten und kurze Zitate bereitgestellt. Für eine Weiterverwendung der zugrunde liegenden
Texte gelten die Rechte der Rechteinhaber.

## Kontext

Das Projekt ist Teil einer Masterarbeit im Studiengang Digitale Geisteswissenschaften (Universität Graz).
