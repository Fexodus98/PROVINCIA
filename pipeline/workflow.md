# PROVINCIA workflow: PDF -> OCR -> candidate pages -> JSON -> RDF

## Goal
Build a band-scale pipeline for *Prosopographia Imperii Romani* that:
1. reads a PIR PDF,
2. runs OCR page by page,
3. finds pages that may contain the target governorship formula,
4. extracts only PROVINCIA-relevant entries as JSON,
5. validates them,
6. transforms them into RDF.

## Folder layout
Place your PDF here first:

- `input/pir_band.pdf`

The scripts write to:
- `output/pages/`
- `output/ocr_txt/`
- `output/ocr_tsv/`
- `output/candidates/`
- `output/entries_raw/`
- `output/entries_validated/`
- `output/rdf/`

## Prerequisites
- Python 3.10+
- Tesseract installed and callable as `tesseract`
- Google Gemini API key in `GEMINI_API_KEY` for the extraction step

Install Python packages:

```powershell
py -m pip install -r requirements.txt
```

## Step 1: render the PDF

```powershell
py .\01_render_pdf.py
```

This creates one PNG per PDF page and writes `output/pages/pages_manifest.json`.

## Step 2: OCR every rendered page

```powershell
py .\02_ocr_pages.py
```

This creates:
- one OCR text file per page in `output/ocr_txt/`
- one TSV file per page in `output/ocr_tsv/`
- one manifest file in `output/ocr_manifest.json`

## Step 3: find candidate pages by formula matching

```powershell
py .\03_find_candidates.py
```

This creates:
- `output/candidates/candidate_pages.json`
- `output/candidates/candidate_pages.jsonl`

At this point you should manually inspect the candidate list and a few corresponding OCR text files.

## Step 4: extract only relevant entries via API

Before this step, set your Google Gemini API key:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
```

Optional model override (default is `gemini-3.5-flash`; if that ID is rejected, fall back to `gemini-2.5-flash`):

```powershell
$env:PROVINCIA_GEMINI_MODEL="gemini-2.5-flash"
```

Run extraction:

```powershell
py .\04_extract_entries_api.py
```

This writes one raw JSON page extraction into `output/entries_raw/`.

## Step 4b: judge pass (verification against the page image)

A second model call re-reads every page image and checks the proposer's
extraction: entry identity (lemma, PIR number), relevance formula, factoid
quotes, province readings, person names, relations. It also reports relevant
entries the proposer missed.

```powershell
py .\04b_judge_entries.py
```

Optional stronger judge model:

```powershell
$env:PROVINCIA_GEMINI_JUDGE_MODEL="gemini-2.5-pro"
```

This writes one judgment file per page into `output/entries_judged/`.
Nothing is rewritten: judges only produce verdicts
(`confirm | minor_issues | major_issues | reject`) and problem flags, which
step 5 attaches to the entries (`needs_review`, `review`) and step 6
serializes as `ont:needsReview` / `ont:reviewVerdict` / `ont:reviewProblem`.
A summary lands in `output/entries_validated/review_report.json`.

## Step 5: validate and keep only PROVINCIA-relevant entries

```powershell
py .\05_validate_entries.py
```

This writes:
- per-page validated JSON to `output/entries_validated/`
- aggregate entries file `output/entries_validated/provincia_entries.json`

## Step 6: transform validated JSON to RDF

```powershell
py .\06_json_to_rdf.py
```

This writes:
- `output/rdf/provincia_graph.ttl`
- `output/rdf/provincia_graph.jsonld`
- `output/rdf/provincia_graph.rdf`
- `output/rdf/provincia_graph.nt`

## Recommended working method
1. Run steps 1-3 on a small PDF sample first.
2. Inspect OCR quality and candidate-page recall.
3. Tune regex patterns if needed.
4. Run step 4 only on candidate pages.
5. Inspect the validated JSON before creating RDF.
6. Only after that process a full band.

## Why this workflow is robust
- OCR handles bulk reading.
- Candidate-page filtering reduces cost and noise.
- The API only solves the difficult semantic extraction step.
- JSON validation prevents bad model output from entering RDF.
- RDF generation stays deterministic in Python.
