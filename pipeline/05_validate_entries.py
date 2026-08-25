from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import (
    ALLOWED_RELATIONS,
    ENTRIES_JUDGED_DIR,
    ENTRIES_RAW_DIR,
    ENTRIES_VALIDATED_DIR,
    ensure_output_dirs,
)

VERDICT_RANK = {"confirm": 0, "minor_issues": 1, "major_issues": 2, "reject": 3}

TARGET_OFFICE = "legatus Augusti pro praetore provinciae"
FORMULA_RE = re.compile(
    r"leg(?:atus|ati|atum|ato|\.)\s+"
    r"(?:aug\.|augusti|augustorum|augg\.)"
    r"(?:\s+vel\s+(?:aug\.|augusti|augustorum|augg\.))?\s+"
    r"(?:pro\s+praetore|pro\s+pr\.?|pr\.?\s*pr\.?)",
    flags=re.IGNORECASE,
)

# Map free-text relation labels (as the LLM often produces) onto the controlled
# ALLOWED_RELATIONS vocabulary. Keys are matched lower-cased and substring-wise,
# so "son-in-law of" is checked before "son of".
RELATION_ALIAS_RULES: list[tuple[str, str]] = [
    # uncertain person identity
    ("possibly identical", "possibly_same_as"),
    ("possibly the same", "possibly_same_as"),
    ("possibly same", "possibly_same_as"),
    ("may be identical", "possibly_same_as"),
    # resolved person identity
    ("certainly identical", "same_as"),
    ("is identical to", "same_as"),
    ("same person as", "same_as"),
    # in-law and extended family → related_to (no specific vocabulary slot)
    ("in-law", "related_to"),
    ("in law", "related_to"),
    ("nephew", "related_to"),
    ("niece", "related_to"),
    ("uncle", "related_to"),
    ("aunt", "related_to"),
    ("cousin", "related_to"),
    ("grandfather", "related_to"),
    ("grandmother", "related_to"),
    ("grandson", "related_to"),
    ("granddaughter", "related_to"),
    ("ancestor", "related_to"),
    ("descendant", "related_to"),
    # parent / child
    ("father", "parent_of"),
    ("mother", "parent_of"),
    ("parent", "parent_of"),
    ("son", "child_of"),
    ("daughter", "child_of"),
    ("child", "child_of"),
    # siblings
    ("brother", "sibling_of"),
    ("sister", "sibling_of"),
    ("sibling", "sibling_of"),
    # spouse
    ("husband", "spouse_of"),
    ("wife", "spouse_of"),
    ("spouse", "spouse_of"),
    ("married", "spouse_of"),
    # office succession
    ("predecessor", "predecessor_of"),
    ("succeeded by", "predecessor_of"),
    ("successor", "successor_of"),
    ("followed", "successor_of"),
    # office binding
    ("office holder", "office_holder_of"),
    ("held office", "office_holder_of"),
    # generic association
    ("associated", "associated_with"),
    ("colleague", "associated_with"),
    ("amicus", "associated_with"),
    ("friend", "associated_with"),
    ("patron", "associated_with"),
    ("client", "associated_with"),
]


def normalize_relation(raw: str | None) -> str | None:
    if not raw:
        return None
    val = str(raw).strip().lower().replace("_", " ")
    if val in ALLOWED_RELATIONS:
        return val
    val_us = val.replace(" ", "_")
    if val_us in ALLOWED_RELATIONS:
        return val_us
    for needle, target in RELATION_ALIAS_RULES:
        if needle in val:
            return target
    return None


def ensure_list(value: Any) -> list:
    return value if isinstance(value, list) else []


PIR_REF_RE = re.compile(r"(?:PIR\s*[²2]?\s*)?\b([A-Z])\s*(\d{1,4})\b")
# entry_id-derived refs require an explicit PIR prefix to avoid false reads
# from ids like "entry_l_arruntius_222".
PIR_REF_FROM_ID_RE = re.compile(r"PIR[\s_]*[²2]?[\s_]*([A-Za-z])[\s_]+(\d{1,4})\b", flags=re.IGNORECASE)

# Praenomen spelling variants for cross-page name matching
_PRAENOMEN_VARIANTS = {
    "caius": "gaius",
    "c.": "gaius",
    "cnaeus": "gnaeus",
    "cn.": "gnaeus",
}


def normalize_pir_reference(raw: Any) -> str | None:
    """Normalize 'PIR2 A 184' / 'PIR² A 235' / 'A 1322 (continuation)' -> 'A 1322'."""
    if not raw:
        return None
    m = PIR_REF_RE.search(str(raw))
    if not m:
        return None
    return f"{m.group(1).upper()} {int(m.group(2))}"


def pir_reference_from_entry_id(entry_id: Any) -> str | None:
    """Extract a PIR ref from ids like 'PIR_A_1341_continuation' -> 'A 1341'."""
    if not entry_id:
        return None
    m = PIR_REF_FROM_ID_RE.search(str(entry_id))
    if not m:
        return None
    return f"{m.group(1).upper()} {int(m.group(2))}"


def name_key(entry: dict[str, Any]) -> str | None:
    """Stable lower-case key from the person name for adjacent-page matching."""
    person = entry.get("main_person", {})
    name = person.get("normalized_name") or person.get("displayed_name") or ""
    tokens = [t for t in re.split(r"\s+", name.lower().strip()) if t]
    tokens = [_PRAENOMEN_VARIANTS.get(t, t) for t in tokens]
    return " ".join(tokens) or None


def merge_entries(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Merge a continuation fragment into the primary entry (the one that
    carries the lemma header). Factoids are deduplicated on exact_text."""
    merged = dict(primary)
    primary_pid = primary["main_person"]["id"]

    def _dedupe_key(f: dict[str, Any]) -> str:
        return re.sub(r"\s+", " ", str(f.get("exact_text", ""))).strip().lower()

    for field in ("governorship_factoids", "career_factoids"):
        seen = {_dedupe_key(f) for f in primary.get(field, [])}
        extra = []
        for f in ensure_list(secondary.get(field)):
            if _dedupe_key(f) not in seen:
                f = dict(f)
                f["person_id"] = primary_pid
                extra.append(f)
                seen.add(_dedupe_key(f))
        merged[field] = primary.get(field, []) + extra

    seen_rel = {(r.get("source"), r.get("target"), r.get("relation")) for r in primary.get("relations", [])}
    merged["relations"] = primary.get("relations", []) + [
        r for r in ensure_list(secondary.get("relations"))
        if (r.get("source"), r.get("target"), r.get("relation")) not in seen_rel
    ]

    seen_rp = {rp.get("displayed_name") for rp in primary.get("related_persons", [])}
    merged["related_persons"] = primary.get("related_persons", []) + [
        rp for rp in ensure_list(secondary.get("related_persons"))
        if rp.get("displayed_name") not in seen_rp
    ]

    merged["entry_notes"] = (
        primary.get("entry_notes", [])
        + secondary.get("entry_notes", [])
        + [f"Merged continuation fragment '{secondary.get('entry_id')}' (page {secondary.get('_page')}) into this entry."]
    )
    if not merged.get("pir_reference"):
        merged["pir_reference"] = secondary.get("pir_reference")

    # Combine judge reviews: worst verdict wins, problems are unioned.
    rev_p = primary.get("review", {"verdict": "not_judged", "problems": []})
    rev_s = secondary.get("review", {"verdict": "not_judged", "problems": []})
    worst = max(rev_p.get("verdict"), rev_s.get("verdict"), key=lambda v: VERDICT_RANK.get(v, 1))
    merged["review"] = {"verdict": worst, "problems": rev_p.get("problems", []) + rev_s.get("problems", [])}
    merged["needs_review"] = bool(primary.get("needs_review") or secondary.get("needs_review"))
    return merged


def merge_cross_page_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge entries that describe the same PIR entry across page breaks.

    Pass 1 groups by normalized pir_reference. Pass 2 attaches PIR-less
    fragments to a group when the person name matches and the pages are
    adjacent (<= 2 apart). Unmatched fragments are kept and flagged.
    """

    def is_fragment(e: dict[str, Any]) -> bool:
        eid = str(e.get("entry_id", "")).lower()
        return "cont" in eid or not e.get("pir_reference")

    groups: dict[str, list[dict[str, Any]]] = {}
    no_ref: list[dict[str, Any]] = []
    for e in entries:
        ref = normalize_pir_reference(e.get("pir_reference"))
        if ref:
            e["pir_reference"] = ref
            groups.setdefault(ref, []).append(e)
        else:
            no_ref.append(e)

    # Pass 2: name + page adjacency
    for frag in list(no_ref):
        fkey = name_key(frag)
        fpage = frag.get("_page", -999)
        if not fkey:
            continue
        for ref, members in groups.items():
            if any(name_key(m) == fkey and abs(m.get("_page", 999) - fpage) <= 2 for m in members):
                members.append(frag)
                no_ref.remove(frag)
                break

    result: list[dict[str, Any]] = []
    for ref, members in groups.items():
        if len(members) == 1:
            result.append(members[0])
            continue
        members.sort(key=lambda e: (is_fragment(e), e.get("_page", 0)))
        primary = members[0]
        for sec in members[1:]:
            primary = merge_entries(primary, sec)
            print(f"[MERGE] {ref}: page {sec.get('_page')} fragment '{sec.get('entry_id')}' -> '{primary.get('entry_id')}'")
        result.append(primary)

    for frag in no_ref:
        frag["entry_notes"] = ensure_list(frag.get("entry_notes")) + [
            "Unresolved continuation fragment: no PIR reference and no adjacent-page name match. "
            "The entry probably starts on a non-candidate page."
        ]
        frag["needs_review"] = True
        rev = frag.setdefault("review", {"verdict": "minor_issues", "problems": []})
        rev["problems"] = ensure_list(rev.get("problems")) + [
            {
                "field": "pir_reference",
                "issue": "Orphan continuation fragment without PIR reference; start page not in candidate set.",
                "severity": "high",
                "suggested_fix": "Check the preceding PDF page for the entry header and PIR number.",
            }
        ]
        print(f"[ORPHAN] page {frag.get('_page')}: '{frag.get('entry_id')}' kept as fragment without PIR reference")
        result.append(frag)

    return result


def clean_factoid(obj: dict[str, Any], source_page: int | None = None) -> dict[str, Any] | None:
    exact_text = str(obj.get("exact_text", "")).strip()
    if not exact_text:
        return None

    normalized_office = obj.get("normalized_office")
    if FORMULA_RE.search(exact_text):
        normalized_office = TARGET_OFFICE
    elif normalized_office == TARGET_OFFICE:
        # Keep only if text still looks like the formula; otherwise drop normalization.
        normalized_office = None

    if normalized_office != TARGET_OFFICE:
        return None

    page_value = source_page if isinstance(source_page, int) and not isinstance(source_page, bool) else None
    if page_value is None:
        existing_page = obj.get("source_page")
        if isinstance(existing_page, int) and not isinstance(existing_page, bool):
            page_value = existing_page

    return {
        "factoid_id": str(obj.get("factoid_id", "")).strip() or "g1",
        "person_id": str(obj.get("person_id", "")).strip() or "p1",
        "exact_text": exact_text,
        "source_page": page_value,
        "normalized_office": TARGET_OFFICE,
        "province_text": obj.get("province_text"),
        "province_normalized": obj.get("province_normalized"),
        "date_text": obj.get("date_text"),
        "date_normalized_start": obj.get("date_normalized_start"),
        "date_normalized_end": obj.get("date_normalized_end"),
        "certainty": obj.get("certainty") if obj.get("certainty") in {"high", "medium", "low"} else "medium",
        "evidence_type": obj.get("evidence_type") if obj.get("evidence_type") in {"explicit", "inferred_from_context", "uncertain_reading"} else "explicit",
        "notes": ensure_list(obj.get("notes")),
    }


def clean_entry(entry: dict[str, Any], source_page: int | None = None) -> dict[str, Any] | None:
    gov_factoids = []
    for factoid in ensure_list(entry.get("governorship_factoids")):
        cleaned = clean_factoid(factoid, source_page)
        if cleaned:
            gov_factoids.append(cleaned)

    if not gov_factoids:
        return None

    person = entry.get("main_person", {})
    relations = []
    for rel in ensure_list(entry.get("relations")):
        normalized = normalize_relation(rel.get("relation"))
        if normalized:
            rel = dict(rel)
            rel["relation"] = normalized
            relations.append(rel)

    pir_ref = (
        normalize_pir_reference(entry.get("pir_reference"))
        or normalize_pir_reference(person.get("pir_reference"))
        or pir_reference_from_entry_id(entry.get("entry_id"))
    )

    related_persons = []
    for related in ensure_list(entry.get("related_persons")):
        related = dict(related)
        if "pir_reference" in related:
            related["pir_reference"] = normalize_pir_reference(related.get("pir_reference"))
        related_persons.append(related)

    return {
        "entry_id": str(entry.get("entry_id", "")).strip() or "e1",
        "pir_reference": pir_ref,
        "lemma": str(entry.get("lemma", "")).strip(),
        "relevance_to_provincia_corpus": "yes",
        "relevance_notes": str(entry.get("relevance_notes", "")).strip(),
        "segments": entry.get("segments", {
            "lemma": "",
            "name_variants": "",
            "identification_and_sources": "",
            "offices_and_career": "",
            "governorship_attestation": "",
            "family_and_social_relations": "",
            "prosopographical_commentary": "",
            "bibliography_or_cross_references": "",
        }),
        "main_person": {
            "id": str(person.get("id", "")).strip() or "p1",
            "displayed_name": str(person.get("displayed_name", "")).strip(),
            "normalized_name": person.get("normalized_name"),
            "pir_reference": pir_ref,
            "status_markers": ensure_list(person.get("status_markers")),
            "notes": ensure_list(person.get("notes")),
        },
        "governorship_factoids": gov_factoids,
        "career_factoids": ensure_list(entry.get("career_factoids")),
        "related_persons": related_persons,
        "relations": relations,
        "entry_notes": ensure_list(entry.get("entry_notes")),
    }


def attach_review(entry: dict[str, Any], judgment: dict[str, Any] | None) -> None:
    """Attach the judge verdict to a cleaned entry. Flag, never rewrite."""
    if judgment is None:
        entry["review"] = {"verdict": "not_judged", "problems": []}
        entry["needs_review"] = True
        return
    verdict = judgment.get("verdict", "minor_issues")
    entry["review"] = {
        "verdict": verdict,
        "problems": ensure_list(judgment.get("problems")),
    }
    entry["needs_review"] = verdict != "confirm"


def validate_page(
    raw_doc: dict[str, Any],
    judgments: dict[str, dict[str, Any]] | None = None,
    page_no: int | None = None,
) -> dict[str, Any]:
    entries = []
    for entry in ensure_list(raw_doc.get("entries")):
        cleaned = clean_entry(entry, page_no)
        if cleaned:
            raw_id = str(entry.get("entry_id", "")).strip()
            attach_review(cleaned, (judgments or {}).get(raw_id))
            entries.append(cleaned)
    return {
        "document_notes": ensure_list(raw_doc.get("document_notes")),
        "entries": entries,
    }


def load_judgments(page_no: int) -> tuple[dict[str, dict[str, Any]] | None, list[dict[str, Any]]]:
    """Return (entry_id -> judgment, missed_entries) for a page, if judged."""
    path = ENTRIES_JUDGED_DIR / f"page_{page_no:04d}.json"
    if not path.exists():
        return None, []
    doc = json.loads(path.read_text(encoding="utf-8"))
    mapping = {str(j.get("entry_id", "")).strip(): j for j in ensure_list(doc.get("judgments"))}
    return mapping, ensure_list(doc.get("missed_entries"))


def main() -> None:
    ensure_output_dirs()
    manifest = []
    all_entries = []
    all_missed: list[dict[str, Any]] = []
    for raw_path in sorted(ENTRIES_RAW_DIR.glob("page_*.json")):
        page_no = int(raw_path.stem.split("_")[1])
        raw_doc = json.loads(raw_path.read_text(encoding="utf-8"))
        judgments, missed = load_judgments(page_no)
        for m in missed:
            all_missed.append({"page": page_no, **m})
        validated = validate_page(raw_doc, judgments, page_no)
        out_path = ENTRIES_VALIDATED_DIR / raw_path.name
        out_path.write_text(json.dumps(validated, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest.append({"page": page_no, "validated_json": str(out_path), "entry_count": len(validated["entries"])})
        for entry in validated["entries"]:
            entry["_page"] = page_no
            all_entries.append(entry)
        print(f"[VALIDATE] page {page_no}: {len(validated['entries'])} kept")

    merged_entries = merge_cross_page_entries(all_entries)
    for entry in merged_entries:
        entry["source_page"] = entry.pop("_page", None)

    (ENTRIES_VALIDATED_DIR / "entries_valid_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (ENTRIES_VALIDATED_DIR / "provincia_entries.json").write_text(
        json.dumps({"entries": merged_entries}, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    flagged = [e for e in merged_entries if e.get("needs_review")]
    review_report = {
        "total_entries": len(merged_entries),
        "flagged_entries": len(flagged),
        "missed_entries_reported_by_judge": all_missed,
        "flagged": [
            {
                "pir_reference": e.get("pir_reference"),
                "entry_id": e.get("entry_id"),
                "lemma": e.get("lemma"),
                "source_page": e.get("source_page"),
                "verdict": e.get("review", {}).get("verdict"),
                "problems": e.get("review", {}).get("problems", []),
            }
            for e in flagged
        ],
    }
    (ENTRIES_VALIDATED_DIR / "review_report.json").write_text(
        json.dumps(review_report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[DONE] {len(all_entries)} page-level entries -> {len(merged_entries)} merged entries in {ENTRIES_VALIDATED_DIR}")
    print(f"[REVIEW] {len(flagged)} flagged for review, {len(all_missed)} possible missed entries -> review_report.json")


if __name__ == "__main__":
    main()
