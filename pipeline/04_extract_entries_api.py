from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import (
    CANDIDATES_DIR,
    CANONICAL_PROVINCES,
    ENTRIES_RAW_DIR,
    ENTRY_SCHEMA,
    MISTRAL_MAX_TOKENS,
    MISTRAL_MODEL,
    ensure_output_dirs,
)
from llm_mistral import chat_with_image, get_client

SYSTEM_PROMPT = """
You are an expert classicist, prosopographer, historical document analyst, and knowledge graph engineer working for the project PROVINCIA.

Your task is to process OCR text plus a page image from the Prosopographia Imperii Romani (PIR) and extract structured information ONLY for entries relevant to the PROVINCIA corpus.

Relevance rule:
An entry is relevant ONLY if the person is explicitly identified in the visible page evidence as legatus Augusti pro praetore provinciae, or a safely readable abbreviated equivalent such as leg. Aug. pr. pr., legatus Aug. pro pr., legatus Augustorum pr. pr., legatus Augg. pr. pr.

Do not include entries that only show proconsul, procurator, legatus legionis, consularis, or other offices unless the target governorship formula is also explicit.

Use the OCR text as a noisy aid, but trust the page image if OCR and image conflict.

ID rule (important):
All identifiers (entry_id, main_person.id, related_persons[].id, governorship_factoids[].factoid_id, career_factoids[].factoid_id) MUST be globally unique across the whole corpus. NEVER use generic placeholders like "p1", "g1", "gov-1", "e1". Construct IDs by prefixing with the PIR reference of the surrounding entry, e.g.:
  entry_id          = "pir-a-1408"
  main_person.id    = "pir-a-1408-person"
  factoid_id        = "pir-a-1408-gov-1", "pir-a-1408-gov-2", ...
  career factoid_id = "pir-a-1408-career-1"
If a PIR reference is not visible on the page, fall back to the page-number prefix instead, e.g. "page-0055-entry-2". Generic IDs cause cross-entry URI collisions in the downstream RDF; do not produce them.

Province rule:
"province_text" is the attested form verbatim from the page (keep the original casus, e.g. "Hispaniam citeriorem", "Galatiae"). "province_normalized" must be EXACTLY one label from this registry, or null when the province is not stated or not in the registry:
{province_registry}
Never invent a registry label that is not explicitly supported by the page evidence. A command like "exercitus Africanus" is not a province: keep it in province_text, set province_normalized to null, and explain in notes.

exact_text rule:
"exact_text" must be the MINIMAL verbatim quote containing the office formula and, if present, the province name — typically under 120 characters. Do not include source citations, dates, translations, or commentary in exact_text; put dates in date_text and everything else in notes.

Relation vocabulary:
The "relation" field in relations[] must be one of: parent_of, child_of, sibling_of, spouse_of, related_to, predecessor_of, successor_of, associated_with, office_holder_of. Map natural-language phrasings ("son of" -> "child_of", "father of" -> "parent_of", "son-in-law of" -> "related_to", etc.) yourself before writing the JSON.

Return only strict JSON matching the schema described in the user message. Do not wrap the JSON in markdown code fences.
""".strip().replace("{province_registry}", ", ".join(CANONICAL_PROVINCES))

USER_TEMPLATE = """
Process exactly one PIR page.

Page number: {page_no}
Candidate hits from OCR:
{hits_json}

OCR text for this page:
---
{ocr_text}
---

Return only entries from this page that are relevant to PROVINCIA.
If no relevant entry is present, return an object with document_notes and an empty entries array.

Output JSON schema (informational; reproduce its keys exactly):
{schema_json}
""".strip()


def load_candidates() -> list[dict[str, Any]]:
    path = CANDIDATES_DIR / "candidate_pages.json"
    return json.loads(path.read_text(encoding="utf-8"))


def extract_page(client, page_record: dict[str, Any]) -> dict[str, Any]:
    page_no = page_record["page"]
    ocr_text = Path(page_record["txt_path"]).read_text(encoding="utf-8")
    image_path = Path(page_record["image_path"])

    prompt = USER_TEMPLATE.format(
        page_no=page_no,
        hits_json=json.dumps(page_record["hits"], ensure_ascii=False, indent=2),
        ocr_text=ocr_text[:25000],
        schema_json=json.dumps(ENTRY_SCHEMA, ensure_ascii=False),
    )

    text = chat_with_image(
        client,
        model=MISTRAL_MODEL,
        user_text=prompt,
        image_path=image_path,
        system=SYSTEM_PROMPT,
        max_tokens=MISTRAL_MAX_TOKENS,
        json_mode=True,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raw_path = ENTRIES_RAW_DIR / f"page_{page_no:04d}.raw.txt"
        raw_path.write_text(text, encoding="utf-8")
        raise


def main() -> None:
    ensure_output_dirs()
    client = get_client()
    candidates = load_candidates()
    manifest: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for page_record in candidates:
        page_no = page_record["page"]
        out_path = ENTRIES_RAW_DIR / f"page_{page_no:04d}.json"
        if out_path.exists():
            print(f"[SKIP] page {page_no} (already done)")
            try:
                existing = json.loads(out_path.read_text(encoding="utf-8"))
                manifest.append({"page": page_no, "raw_json": str(out_path), "entry_count": len(existing.get("entries", []))})
            except Exception:
                pass
            continue
        print(f"[API] page {page_no}")
        try:
            result = extract_page(client, page_record)
        except json.JSONDecodeError as exc:
            err_path = ENTRIES_RAW_DIR / f"page_{page_no:04d}.error.txt"
            err_path.write_text(f"JSONDecodeError: {exc}\n", encoding="utf-8")
            print(f"[FAIL] page {page_no}: invalid JSON (raw saved to {err_path.name})")
            failures.append({"page": page_no, "error": f"json_decode: {exc}"})
            continue
        except Exception as exc:
            print(f"[FAIL] page {page_no}: {type(exc).__name__}: {exc}")
            failures.append({"page": page_no, "error": f"{type(exc).__name__}: {exc}"})
            continue
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append(
            {
                "page": page_no,
                "raw_json": str(out_path),
                "entry_count": len(result.get("entries", [])),
            }
        )

    manifest_path = ENTRIES_RAW_DIR / "entries_raw_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    if failures:
        fail_path = ENTRIES_RAW_DIR / "entries_raw_failures.json"
        fail_path.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[DONE-WITH-ERRORS] {len(manifest)} ok, {len(failures)} failed -> {fail_path.name}")
    else:
        print(f"[DONE] wrote {manifest_path}")


if __name__ == "__main__":
    main()
