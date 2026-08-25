# -*- coding: utf-8 -*-
"""Create the human-reviewed correction overlays for seven PIR entries.

The raw extraction remains untouched.  The generated overlay documents are
consumed by ``apply_corrections.py`` after validation stage 5.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
RAW = BASE / "entries_raw"
CORR = BASE / "entries_corrected_hutter"
TODAY = "2026-08-25"
TARGET_OFFICE = "legatus Augusti pro praetore provinciae"


def load_raw(page: int, pir_reference: str) -> dict[str, Any]:
    document = json.loads((RAW / f"page_{page:04d}.json").read_text(encoding="utf-8"))
    for entry in document.get("entries", []):
        if entry.get("pir_reference") == pir_reference:
            return copy.deepcopy(entry)
    raise KeyError(f"{pir_reference} not found in raw page {page}")


def mark_reviewed(entry: dict[str, Any], note: str) -> None:
    entry["review"] = {
        "verdict": "human_corrected",
        "reviewed_by": "Hutter",
        "reviewed_on": TODAY,
        "note": note,
    }
    entry["needs_review"] = False


def normalize_relations(entry: dict[str, Any], mapping: dict[str, str]) -> None:
    for relation in entry.get("relations", []):
        relation["relation"] = mapping.get(relation.get("relation"), relation.get("relation"))


def set_related_pir_reference(entry: dict[str, Any], person_id: str, pir_reference: str) -> None:
    for person in entry.get("related_persons", []):
        if person.get("id") == person_id:
            person["pir_reference"] = pir_reference
            return
    raise KeyError(f"Related person {person_id} not found in {entry.get('pir_reference')}")


def save(page: int, entries: list[dict[str, Any]], notes: str) -> None:
    document = {
        "source_page": page,
        "document_notes": notes,
        "entries": entries,
    }
    path = CORR / f"page_{page:04d}.json"
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written: {path.relative_to(BASE)}")


# A 101: the entry and attestation are on PDF/OCR page 0032 (printed page 16).
a101 = load_raw(32, "A 101")
a101["entry_id"] = "PIR_A_101"
a101["source_page"] = 32
a101["relevance_to_provincia_corpus"] = "yes"
a101["relevance_notes"] = "Governor of Germania inferior, probably AD 101-103/104."
fact = a101["governorship_factoids"][0]
fact.update(
    normalized_office=TARGET_OFFICE,
    province_text="Germaniae inferioris",
    province_normalized="Germania inferior",
    date_normalized_start=101,
    date_normalized_end=104,
    certainty="high",
    evidence_type="explicit",
    source_page=32,
)
fact.setdefault("notes", []).append(
    "The governorship is securely attested; only its dating is uncertain: PIR says "
    "'fortasse ab a. 101 usque ad a. 103/104'."
)
mark_reviewed(a101, "A 101 confirmed as governor of Germania inferior; correct scan page is page_0032 (printed page 16).")
save(32, [a101], "Human-reviewed correction for PIR A 101.")


# A 200: discard the conjectural Pannonia governorship.  The continuation on
# page 0051 explicitly records appointment to Syria and retention in Rome.
a200 = load_raw(50, "PIR² A 200")
a200["entry_id"] = "PIR_A_200"
a200["pir_reference"] = "A 200"
a200["main_person"]["pir_reference"] = "A 200"
a200["source_page"] = 50
a200["relevance_to_provincia_corpus"] = "yes"
a200["relevance_notes"] = (
    "Appointed by Tiberius to govern Syria after AD 21, but retained in Rome; "
    "he never travelled to or exercised the governorship in the province."
)
a200["segments"]["offices_and_career"] = (
    "Proconsul Africae (outside the PROVINCIA corpus); after AD 21 appointed to "
    "Syria by Tiberius, but retained at Rome and never sent to the province."
)
a200["segments"]["governorship_attestation"] = (
    "A Tiberio provinciae Syriae praepositus (post a. 21, quo anno Cn. Sentius "
    "Saturninus provinciae praefuit), sed in urbe retentus Tac. a. 6, 27."
)
a200["governorship_factoids"] = [
    {
        "factoid_id": "gov_200_syria_appointment",
        "person_id": a200["main_person"]["id"],
        "exact_text": (
            "A Tiberio provinciae Syriae praepositus (post a. 21, quo anno Cn. "
            "Sentius Saturninus provinciae praefuit), sed in urbe retentus"
        ),
        "normalized_office": TARGET_OFFICE,
        "province_text": "Syriae",
        "province_normalized": "Syria",
        "date_text": "post a. 21; appointed but retained in Rome",
        "date_normalized_start": None,
        "date_normalized_end": None,
        "certainty": "high",
        "evidence_type": "inferred_from_context",
        "source_page": 51,
        "notes": [
            "Praepositus is interpreted here as appointed/designated to govern Syria.",
            "Tac. Ann. 6.27: Tiberius retained Lamia in Rome; he never entered Syria or exercised on-site command.",
            "The conjectural Pannonia governorship in the raw extraction is rejected and is not modelled.",
        ],
    }
]
for career in a200.get("career_factoids", []):
    if career.get("factoid_id") == "fact_lamia_proconsul_africa":
        career["relevance_to_governorship"] = "low"
        career.setdefault("notes", []).append("Proconsular Africa is outside the PROVINCIA corpus.")
normalize_relations(
    a200,
    {"son of": "child_of", "grandson of": "related_to", "brother of": "sibling_of"},
)
mark_reviewed(
    a200,
    "A 200 modelled only for the Syrian appointment after AD 21; the non-assumption of office in the province is explicit. Pannonia rejected; proconsular Africa excluded.",
)
save(50, [a200], "Human-reviewed correction for PIR A 200; the governorship passage continues on page_0051.")


# A 776: entry begins on page 0165; the governorship wording is on page 0166.
a776 = load_raw(166, "A 776")
a776["entry_id"] = "PIR_A_776"
a776["source_page"] = 165
a776["relevance_to_provincia_corpus"] = "yes"
fact = a776["governorship_factoids"][0]
fact.update(
    normalized_office=TARGET_OFFICE,
    province_text="Germaniae superioris",
    province_normalized="Germania superior",
    date_normalized_start=55,
    date_normalized_end=56,
    certainty="high",
    evidence_type="explicit",
    source_page=166,
)
fact.setdefault("notes", []).append(
    "The governorship is secure, but the beginning in AD 55 is only probable "
    "('probabiliter iam a. 55'); the legateship in AD 56 is explicit."
)
normalize_relations(
    a776,
    {
        "son of": "child_of",
        "daughter of": "child_of",
        "son-in-law of": "related_to",
        "mother-in-law of": "related_to",
        "successor of": "successor_of",
    },
)
mark_reviewed(a776, "A 776 confirmed as governor of Germania superior in AD 55-56; entry spans page_0165-page_0166.")
save(166, [a776], "Human-reviewed correction for PIR A 776; entry starts on page_0165.")


# The governor is A 1304.  A 1305 is his probable grandson and not the person
# holding the Pannonia and Syria governorships.
a1304 = load_raw(281, "A 1304")
a1304["entry_id"] = "PIR_A_1304"
a1304["source_page"] = 281
a1304["relevance_to_provincia_corpus"] = "yes"
for fact in a1304["governorship_factoids"]:
    fact["normalized_office"] = TARGET_OFFICE
    fact["source_page"] = 281
    if fact["factoid_id"] == "gov_1304_1":
        fact["province_text"] = "Pannoniae"
        fact["province_normalized"] = "Pannonia"
    else:
        fact["province_text"] = "Syriae"
        fact["province_normalized"] = "Syria"
normalize_relations(a1304, {"grandfather": "related_to"})
set_related_pir_reference(a1304, "person_1305", "A 1305")
mark_reviewed(a1304, "A 1304 (not A 1305) confirmed as governor of Pannonia in AD 80 and Syria in AD 83-84; A 1305 remains only a probable grandson.")
save(281, [a1304], "Human-reviewed correction for PIR A 1304; corrects the proposed A 1305 attribution.")


a1331 = load_raw(285, "A 1331")
a1331["entry_id"] = "PIR_A_1331"
a1331["source_page"] = 285
a1331["relevance_to_provincia_corpus"] = "yes"
fact = a1331["governorship_factoids"][0]
fact.update(
    normalized_office=TARGET_OFFICE,
    province_text="Galatiae",
    province_normalized="Galatia",
    date_normalized_start=198,
    date_normalized_end=200,
    certainty="high",
    evidence_type="explicit",
    source_page=285,
)
normalize_relations(a1331, {"father": "parent_of"})
set_related_pir_reference(a1331, "person_A_1332", "A 1332")
mark_reviewed(a1331, "A 1331 confirmed as governor of Galatia in AD 198-200.")
save(285, [a1331], "Human-reviewed correction for PIR A 1331.")


a1350 = load_raw(288, "A 1350")
a1350["entry_id"] = "PIR_A_1350"
a1350["source_page"] = 288
a1350["relevance_to_provincia_corpus"] = "yes"
fact = a1350["governorship_factoids"][0]
fact.update(
    normalized_office=TARGET_OFFICE,
    province_text="Thraciae",
    province_normalized="Thracia",
    date_normalized_start=238,
    date_normalized_end=244,
    certainty="high",
    evidence_type="explicit",
    source_page=288,
)
normalize_relations(a1350, {"subject": "associated_with"})
mark_reviewed(a1350, "A 1350 confirmed as governor of Thracia under Gordian III (AD 238-244).")
save(288, [a1350], "Human-reviewed correction for PIR A 1350.")


# The raw A 1498 record is a numbering error.  The source passage begins with
# A 1517 on page 0329 and continues on page 0330.
raw_gallus = load_raw(330, "A 1498")
drop_a1498 = {
    "entry_id": "PIR_A_1498",
    "pir_reference": "A 1498",
    "relevance_to_provincia_corpus": "no",
    "source_page": 330,
    "entry_notes": ["Extraction numbering error: this record belongs to PIR A 1517."],
}
a1517 = raw_gallus
a1517["entry_id"] = "PIR_A_1517"
a1517["pir_reference"] = "A 1517"
a1517["main_person"]["pir_reference"] = "A 1517"
a1517["source_page"] = 329
a1517["relevance_to_provincia_corpus"] = "yes"
a1517["relevance_notes"] = "Governor of Moesia inferior under Septimius Severus and Caracalla, AD 202-205."
fact = a1517["governorship_factoids"][0]
fact.update(
    normalized_office=TARGET_OFFICE,
    province_text="Moesiae inferioris",
    province_normalized="Moesia inferior",
    date_normalized_start=202,
    date_normalized_end=205,
    certainty="high",
    evidence_type="explicit",
    source_page=330,
)
normalize_relations(a1517, {"son of": "child_of", "relative of": "related_to"})
set_related_pir_reference(a1517, "person_l_aurelius_gallus_cos_174", "A 1516")
mark_reviewed(a1517, "Corrected PIR number from the erroneous A 1498 extraction to A 1517; governorship of Moesia inferior dated AD 202-205.")
save(330, [drop_a1498, a1517], "Human-reviewed numbering correction: L. Aurelius Gallus is PIR A 1517, not A 1498; entry starts on page_0329.")
