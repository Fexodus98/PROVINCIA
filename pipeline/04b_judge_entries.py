"""Judge pass: verify every extracted page against the page image.

For each page in entries_raw/, a judge model re-reads the page image and
checks the proposer's JSON. It never rewrites the data — it produces
verdicts and problem flags that stage 5 attaches to the entries.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import (
    CANDIDATES_DIR,
    CANONICAL_PROVINCES,
    ENTRIES_JUDGED_DIR,
    ENTRIES_RAW_DIR,
    MISTRAL_JUDGE_MODEL,
    MISTRAL_MAX_TOKENS,
    ensure_output_dirs,
)
from llm_mistral import chat_with_image, get_client

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "page_notes": {"type": "array", "items": {"type": "string"}},
        "missed_entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lemma": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["lemma", "reason"],
            },
        },
        "judgments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["confirm", "minor_issues", "major_issues", "reject"],
                    },
                    "problems": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "issue": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "suggested_fix": {"type": ["string", "null"]},
                            },
                            "required": ["field", "issue", "severity", "suggested_fix"],
                        },
                    },
                },
                "required": ["entry_id", "verdict", "problems"],
            },
        },
    },
    "required": ["page_notes", "missed_entries", "judgments"],
}

SYSTEM_PROMPT = """
You are a meticulous verification judge for the project PROVINCIA. A proposer model has extracted structured prosopographical data from a page of the Prosopographia Imperii Romani (PIR). Your job is to verify that extraction against the page image, which is the only authoritative source.

For EVERY entry in the proposed JSON, check:
1. ENTRY IDENTITY: Does the entry exist on this page? Are lemma and pir_reference exactly what the printed page shows (PIR number printed at the start of the entry)? Watch for italic-print OCR traps (m/n, i/l, u/n confusions).
2. RELEVANCE: Is the person explicitly attested as legatus Augusti pro praetore (or abbreviated equivalent: leg. Aug. pr. pr., legatus Aug. pro pr., legatus Augg./Augustorum pr. pr.)? Quote-check the formula on the image. If the formula belongs to a DIFFERENT person (e.g. a relative or predecessor mentioned inside the entry), that is a major issue.
3. GOVERNORSHIP FACTOIDS: Is exact_text a verbatim quote from the page? Is the province reading correct (right province, right casus in province_text)? Is province_normalized exactly one of the registry labels below, or null? Are dates supported by the text?
4. PERSON DATA: displayed_name / normalized_name correctly transcribed? status_markers supported?
5. RELATIONS: supported by the page text?

Also report entries on the page that ARE relevant (formula visible) but missing from the proposal (missed_entries), including entries that begin on the previous page and continue here.

Verdicts:
- "confirm": everything checks out (possibly trivial notes).
- "minor_issues": small fixable problems (typos, slightly off dates, too-long exact_text). List each as a problem with severity low/medium.
- "major_issues": wrong person, wrong province, formula not actually attested for this person, wrong PIR number. Severity high.
- "reject": entry should not be in the corpus at all (relevance rule violated or entry not on this page).

Be conservative: only flag what you can verify from the image. Do not rewrite the data; suggest fixes in suggested_fix.

Province registry:
{province_registry}

Return only strict JSON matching the schema in the user message. No markdown fences.
""".strip().replace("{province_registry}", ", ".join(CANONICAL_PROVINCES))

USER_TEMPLATE = """
Page number: {page_no}

Proposed extraction JSON for this page:
---
{proposal_json}
---

Raw OCR text of the page (noisy aid for locating passages; the image is authoritative):
---
{ocr_text}
---

Judge output schema (reproduce keys exactly):
{schema_json}
""".strip()


def load_candidates_by_page() -> dict[int, dict[str, Any]]:
    path = CANDIDATES_DIR / "candidate_pages.json"
    records = json.loads(path.read_text(encoding="utf-8"))
    return {r["page"]: r for r in records}


def judge_page(client, page_no: int, proposal: dict[str, Any], image_path: Path, ocr_text: str) -> dict[str, Any]:
    prompt = USER_TEMPLATE.format(
        page_no=page_no,
        proposal_json=json.dumps(proposal, ensure_ascii=False, indent=2),
        ocr_text=ocr_text[:30000],
        schema_json=json.dumps(JUDGE_SCHEMA, ensure_ascii=False),
    )
    text = chat_with_image(
        client,
        model=MISTRAL_JUDGE_MODEL,
        user_text=prompt,
        image_path=image_path,
        system=SYSTEM_PROMPT,
        max_tokens=MISTRAL_MAX_TOKENS,
        json_mode=True,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raw_path = ENTRIES_JUDGED_DIR / f"page_{page_no:04d}.raw.txt"
        raw_path.write_text(text, encoding="utf-8")
        raise


def main() -> None:
    ensure_output_dirs()
    client = get_client()
    candidates = load_candidates_by_page()
    manifest: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for raw_path in sorted(ENTRIES_RAW_DIR.glob("page_*.json")):
        if raw_path.name.endswith(".error.txt"):
            continue
        page_no = int(raw_path.stem.split("_")[1])
        out_path = ENTRIES_JUDGED_DIR / f"page_{page_no:04d}.json"
        if out_path.exists():
            print(f"[SKIP] page {page_no} (already judged)")
            continue
        record = candidates.get(page_no)
        if not record:
            print(f"[SKIP] page {page_no}: not in candidate list")
            continue
        proposal = json.loads(raw_path.read_text(encoding="utf-8"))
        ocr_text = Path(record["txt_path"]).read_text(encoding="utf-8")
        print(f"[JUDGE] page {page_no} ({len(proposal.get('entries', []))} entries)")
        try:
            judged = judge_page(client, page_no, proposal, Path(record["image_path"]), ocr_text)
        except Exception as exc:
            print(f"[FAIL] page {page_no}: {type(exc).__name__}: {exc}")
            failures.append({"page": page_no, "error": f"{type(exc).__name__}: {exc}"})
            continue
        out_path.write_text(json.dumps(judged, indent=2, ensure_ascii=False), encoding="utf-8")
        verdicts = [j.get("verdict") for j in judged.get("judgments", [])]
        manifest.append({"page": page_no, "judged_json": str(out_path), "verdicts": verdicts, "missed": len(judged.get("missed_entries", []))})

    (ENTRIES_JUDGED_DIR / "judge_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if failures:
        (ENTRIES_JUDGED_DIR / "judge_failures.json").write_text(
            json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"[DONE-WITH-ERRORS] {len(manifest)} judged, {len(failures)} failed")
    else:
        print(f"[DONE] judged {len(manifest)} pages")


if __name__ == "__main__":
    main()
