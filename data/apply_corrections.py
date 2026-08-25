# -*- coding: utf-8 -*-
"""Overlay-Schritt (zwischen Stufe 5 und Stufe 6):
Spielt die menschlichen Korrekturen aus entries_corrected_hutter/ in
entries_validated/provincia_entries.json ein.

Match je Eintrag zuerst über die PIR-Nummer, sonst über die entry_id:
  - relevance == "no"  -> Eintrag aus dem Korpus entfernen
  - sonst              -> Eintrag ersetzen (oder anhängen, falls neu / zuvor 'missed')

Danach '06_json_to_rdf.py' erneut laufen lassen. Stufe 5 NICHT erneut ausführen,
sonst wird provincia_entries.json überschrieben.
Ein Backup wird als provincia_entries.backup.json angelegt.
"""
import json, glob, re, shutil
import os
from pathlib import Path

# Standardmaessig immer den data/-Ordner dieses Repositories verwenden.
# PROVINCIA_DATA_DIR erlaubt gefahrlose Tests mit einer separaten Kopie.
BASE = Path(os.environ.get("PROVINCIA_DATA_DIR", Path(__file__).resolve().parent))
AGG = BASE/"entries_validated"/"provincia_entries.json"
CORR = BASE/"entries_corrected_hutter"
REVIEW_REPORT = BASE/"entries_validated"/"review_report.json"

def norm_pir(x):
    if not x: return None
    m = re.search(r"([A-Z])\s*(\d{1,4})", str(x))
    return f"{m.group(1)} {int(m.group(2))}" if m else None

def find(entries, ce):
    pr = norm_pir(ce.get("pir_reference"))
    if pr:
        for i, e in enumerate(entries):
            if norm_pir(e.get("pir_reference")) == pr: return i
    eid = ce.get("entry_id")
    for i, e in enumerate(entries):
        if e.get("entry_id") == eid: return i
    return -1

def pir_sort_key(entry):
    ref = norm_pir(entry.get("pir_reference"))
    if ref:
        letter, number = ref.split()
        return (0, letter, int(number), str(entry.get("entry_id") or ""))
    return (1, "", 0, str(entry.get("entry_id") or ""))

def build_final_review_report(entries, previous_report=None):
    """Build the post-overlay report representing the authoritative corpus."""
    flagged = [entry for entry in entries if entry.get("needs_review")]
    previous_report = previous_report or {}
    historical_missed = previous_report.get("missed_entries_reported_by_judge", [])
    if not historical_missed:
        historical_missed = previous_report.get(
            "assessed_missed_entries_reported_by_judge", []
        )
    return {
        "report_stage": "post_human_corrections",
        "total_entries": len(entries),
        "flagged_entries": len(flagged),
        "missed_entries_reported_by_judge": [],
        "assessed_missed_entries_reported_by_judge": historical_missed,
        "review_note": (
            "The historical Judge proposals in assessed_missed_entries_reported_by_judge "
            "were assessed during human review and are no longer open items."
        ),
        "flagged": [
            {
                "pir_reference": entry.get("pir_reference"),
                "entry_id": entry.get("entry_id"),
                "lemma": entry.get("lemma"),
                "source_page": entry.get("source_page"),
                "verdict": entry.get("review", {}).get("verdict"),
                "problems": entry.get("review", {}).get("problems", []),
            }
            for entry in flagged
        ],
    }

def norm_exact_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()

def valid_source_page(value):
    return isinstance(value, int) and not isinstance(value, bool)

def preserve_entry_source_page(corrected_entry, existing_entry=None, correction_page=None):
    """Resolve the entry page without overwriting an explicit correction.

    An explicit page in the human overlay wins. If it is absent, retain the
    existing aggregate page; only a genuinely new entry falls back to the
    correction document's page.
    """
    if valid_source_page(corrected_entry.get("source_page")):
        return
    existing_page = (existing_entry or {}).get("source_page")
    if valid_source_page(existing_page):
        corrected_entry["source_page"] = existing_page
    elif valid_source_page(correction_page):
        corrected_entry["source_page"] = correction_page
    else:
        corrected_entry["source_page"] = None

def raw_page_factoid_context(raw_doc, page_no):
    """Return raw governorship factoids annotated with their file-context page."""
    factoids = []
    for entry in raw_doc.get("entries", []):
        for factoid in entry.get("governorship_factoids", []):
            factoid = dict(factoid)
            factoid["source_page"] = page_no
            factoids.append(factoid)
    return {"governorship_factoids": factoids}

def preserve_factoid_source_pages(corrected_entry, existing_entry=None):
    """Preserve only deterministic factoid-level page assignments.

    Explicit integer values in the correction overlay win. Otherwise match
    uniquely by factoid_id, then by normalized exact_text. New or ambiguous
    factoids remain null; the correction file's page is never guessed here.
    """
    corrected = corrected_entry.get("governorship_factoids", [])
    existing = (existing_entry or {}).get("governorship_factoids", [])

    old_by_id = {}
    old_by_text = {}
    for factoid in existing:
        factoid_id = str(factoid.get("factoid_id") or "").strip()
        exact_text = norm_exact_text(factoid.get("exact_text"))
        if factoid_id:
            old_by_id.setdefault(factoid_id, []).append(factoid)
        if exact_text:
            old_by_text.setdefault(exact_text, []).append(factoid)

    corrected_id_counts = {}
    corrected_text_counts = {}
    for factoid in corrected:
        factoid_id = str(factoid.get("factoid_id") or "").strip()
        exact_text = norm_exact_text(factoid.get("exact_text"))
        if factoid_id:
            corrected_id_counts[factoid_id] = corrected_id_counts.get(factoid_id, 0) + 1
        if exact_text:
            corrected_text_counts[exact_text] = corrected_text_counts.get(exact_text, 0) + 1

    for factoid in corrected:
        if valid_source_page(factoid.get("source_page")):
            continue

        match = None
        factoid_id = str(factoid.get("factoid_id") or "").strip()
        if (
            factoid_id
            and corrected_id_counts.get(factoid_id) == 1
            and len(old_by_id.get(factoid_id, [])) == 1
        ):
            match = old_by_id[factoid_id][0]
        else:
            exact_text = norm_exact_text(factoid.get("exact_text"))
            if (
                exact_text
                and corrected_text_counts.get(exact_text) == 1
                and len(old_by_text.get(exact_text, [])) == 1
            ):
                match = old_by_text[exact_text][0]

        matched_page = match.get("source_page") if match else None
        factoid["source_page"] = matched_page if valid_source_page(matched_page) else None

def main():
    data = json.loads(AGG.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    before = len(entries)
    previous_report = {}
    if REVIEW_REPORT.exists():
        previous_report = json.loads(REVIEW_REPORT.read_text(encoding="utf-8"))
    shutil.copyfile(AGG, AGG.with_suffix(".backup.json"))

    replaced = added = dropped = 0
    for f in sorted(glob.glob(str(CORR/"page_*.json"))):
        pg = int(re.search(r"page_(\d+)", f).group(1))
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        raw_path = BASE/"entries_raw"/f"page_{pg:04d}.json"
        raw_context = {"governorship_factoids": []}
        if raw_path.exists():
            raw_doc = json.loads(raw_path.read_text(encoding="utf-8"))
            raw_context = raw_page_factoid_context(raw_doc, pg)
        for ce in doc.get("entries", []):
            i = find(entries, ce)
            preserve_entry_source_page(ce, entries[i] if i >= 0 else None, pg)
            if ce.get("relevance_to_provincia_corpus") == "no":
                if i >= 0:
                    entries.pop(i); dropped += 1
                    print(f"[DROP]    {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")
                continue
            if i >= 0:
                preserve_factoid_source_pages(ce, entries[i])
                preserve_factoid_source_pages(ce, raw_context)
                entries[i] = ce; replaced += 1
                print(f"[REPLACE] {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")
            else:
                preserve_factoid_source_pages(ce)
                preserve_factoid_source_pages(ce, raw_context)
                entries.append(ce); added += 1
                print(f"[ADD]     {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")

    entries.sort(key=pir_sort_key)
    data["entries"] = entries
    AGG.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    final_report = build_final_review_report(entries, previous_report)
    REVIEW_REPORT.write_text(
        json.dumps(final_report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\n{before} -> {len(entries)} Einträge  (ersetzt: {replaced}, hinzugefügt: {added}, entfernt: {dropped})")
    print("Backup: provincia_entries.backup.json")
    print(f"Reviewbericht: {len(entries)} Einträge, {len(final_report['flagged'])} offen")
    print("Nächster Schritt: 06_json_to_rdf.py erneut ausführen.")

if __name__ == "__main__":
    main()
