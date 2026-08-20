# -*- coding: utf-8 -*-
"""Apply the human-reviewed PIR identity and kinship corrections.

The script only writes complete overlay documents to
``entries_corrected_hutter``. Raw and judged extraction data remain unchanged.
It is idempotent so that the reviewed relation layer can be reproduced safely.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
CORR = BASE / "entries_corrected_hutter"
RAW = BASE / "entries_raw"
TODAY = "2026-08-20"
TARGET_OFFICE = "legatus Augusti pro praetore provinciae"


def load_page(page: int, *, raw: bool = False) -> dict[str, Any]:
    path = (RAW if raw else CORR) / f"page_{page:04d}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_page(page: int, document: dict[str, Any]) -> None:
    path = CORR / f"page_{page:04d}.json"
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"written: {path.relative_to(BASE)}")


def get_entry(document: dict[str, Any], pir_reference: str) -> dict[str, Any]:
    for entry in document.get("entries", []):
        if entry.get("pir_reference") == pir_reference:
            return entry
    raise KeyError(f"Entry {pir_reference} not found")


def upsert_related(entry: dict[str, Any], person: dict[str, Any], *old_ids: str) -> None:
    candidates = {person["id"], *old_ids}
    for existing in entry.setdefault("related_persons", []):
        if existing.get("id") in candidates:
            existing.clear()
            existing.update(copy.deepcopy(person))
            return
    entry["related_persons"].append(copy.deepcopy(person))


def rename_relation_target(entry: dict[str, Any], old: str, new: str) -> None:
    for relation in entry.setdefault("relations", []):
        if relation.get("source") == old:
            relation["source"] = new
        if relation.get("target") == old:
            relation["target"] = new


def upsert_relation(entry: dict[str, Any], relation: dict[str, Any]) -> None:
    key = (relation["source"], relation["target"], relation["relation"])
    for existing in entry.setdefault("relations", []):
        existing_key = (existing.get("source"), existing.get("target"), existing.get("relation"))
        if existing_key == key:
            existing.clear()
            existing.update(copy.deepcopy(relation))
            return
    entry["relations"].append(copy.deepcopy(relation))


def mark_reviewed(entry: dict[str, Any], note: str) -> None:
    entry["review"] = {
        "verdict": "human_corrected",
        "reviewed_by": "Hutter",
        "reviewed_on": TODAY,
        "note": note,
    }
    entry["needs_review"] = False


def external_person(
    person_id: str,
    pir_reference: str,
    displayed_name: str,
    normalized_name: str | None,
    context: str,
    certainty: str,
    notes: list[str],
) -> dict[str, Any]:
    return {
        "id": person_id,
        "displayed_name": displayed_name,
        "normalized_name": normalized_name,
        "pir_reference": pir_reference,
        "relation_context": context,
        "certainty": certainty,
        "notes": notes,
    }


def identity(source: str, target: str, certainty: str, basis: str, notes: list[str]) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "relation": "possibly_same_as",
        "certainty": certainty,
        "basis": basis,
        "notes": notes,
    }


# A 345 / A 346: explicit open identity.
doc = load_page(70)
entry = get_entry(doc, "A 346")
upsert_related(
    entry,
    external_person(
        "person_A345", "A 345", "L. AEMILIVS FRON....", "Lucius Aemilius Fron...",
        "Fortasse idem qui praecedit.", "medium",
        ["PIR A 345; the two PIR entries remain separate."],
    ),
    "person_345",
)
rename_relation_target(entry, "person_345", "person_A345")
upsert_relation(
    entry,
    identity(
        "person_346", "person_A345", "medium", "Fortasse idem qui praecedit.",
        ["A 346 may be identical with the preceding PIR entry A 345; no merge was performed."],
    ),
)
mark_reviewed(entry, "A 345/A 346 as possibly_same_as; separate PIR identities retained.")
save_page(70, doc)


# A 470 / A 468: the supposedly missing counterpart is the fragmentary PIR A 468.
doc = load_page(96)
entry = get_entry(doc, "A 470")
for field in ("prosopographical_commentary", "bibliography_or_cross_references"):
    text = entry.get("segments", {}).get(field)
    if isinstance(text, str):
        entry["segments"][field] = text.replace("IGR 4, 872", "IGR 4, 372")
upsert_related(
    entry,
    external_person(
        "person_A468", "A 468", "Q. AI......", None,
        "Plane incertum, num idem sit ...; vide num idem sit Q. Aiacius Modestus Crescentianus.",
        "low",
        ["Fragmentary PIR A 468, attested in IGR IV 372; the nomen may also be Aelius or Aemilius."],
    ),
)
upsert_relation(
    entry,
    identity(
        "person_A470", "person_A468", "low",
        "A 468: 'Vide num idem sit Q. Aiacius Modestus Crescentianus'; A 470: 'Plane incertum, num idem sit ...'",
        ["Very uncertain identification because the nomen in IGR IV 372 is fragmentary."],
    ),
)
mark_reviewed(entry, "A 468 identified as the fragmentary comparison entry for A 470; IGR IV 372 corrected; low-confidence possibly_same_as.")
save_page(96, doc)


# A 519: Arabia is secure; the Wadd. 2460 attribution to Syria is a separate low-confidence factoid.
doc = load_page(104)
entry = get_entry(doc, "A 519")
arabia = next(f for f in entry["governorship_factoids"] if f.get("factoid_id") == "gov_519_1")
arabia.update(
    {
        "date_text": None,
        "date_normalized_start": None,
        "date_normalized_end": None,
        "certainty": "high",
        "evidence_type": "explicit",
        "notes": [
            "The governorship of Arabia is securely attested by the Gerasene inscription IGR III 1371.",
            "The conjectural identification in Wadd. 2460 and its date of 209 do not date this secure Arabia factoid.",
        ],
    }
)
syria = {
    "factoid_id": "gov_519_2_syria",
    "person_id": "person_519",
    "exact_text": "hunc nominatum fuisse in t. posito a. 209, Wadd. 2460, ubi nomina legati perierunt praeter ....ητιανοῦ, suspicati sunt Bruennow et Domaszewski; qui simul monuerunt fieri posse ut non Arabiae sed Syriae legatus in hoc t. memoratus sit",
    "normalized_office": TARGET_OFFICE,
    "province_text": "Syria",
    "province_normalized": "Syria",
    "date_text": "a. 209 (conjectural attribution of Wadd. 2460)",
    "date_normalized_start": 209,
    "date_normalized_end": 209,
    "certainty": "low",
    "evidence_type": "uncertain_reading",
    "notes": [
        "Both the identification of the fragmentary name ...ητιανοῦ with A 519 and the assignment of the inscription to Syria are conjectural.",
        "The PIR author explicitly adds 'dubito num recte'.",
    ],
}
entry["governorship_factoids"] = [
    f for f in entry["governorship_factoids"] if f.get("factoid_id") != "gov_519_2_syria"
] + [syria]
upsert_related(
    entry,
    external_person(
        "person_735", "A 735", ".....VS ANTIANVS", "[.....]us Antianus",
        "At A 735 Ritterling conjectured Avitianus instead of Antianus and referred to A 519.",
        "low",
        ["Identity rests on a conjectural restoration of the damaged nomen."],
    ),
)
mark_reviewed(entry, "Arabia separated from the conjectural Syria/Wadd. 2460 factoid; A 735 identity candidate retained at low confidence.")
save_page(104, doc)

doc = load_page(152)
entry = get_entry(doc, "A 735")
upsert_related(
    entry,
    external_person(
        "person_519", "A 519", "L. ALFENVS AVITIANVS", "Lucius Alfenus Avitianus",
        "pro Antianus fortasse legendum Avitianus (cf. L. Alfenum Avitianum supra n. 519)",
        "low",
        ["Ritterling's identification depends on the conjectural reading Avitianus."],
    ),
)
upsert_relation(
    entry,
    identity(
        "person_735", "person_519", "low",
        "pro Antianus fortasse legendum Avitianus (cf. L. Alfenum Avitianum supra n. 519)",
        ["The two PIR entries remain distinct; no certainty is transferred to the governorship of Pannonia inferior."],
    ),
)
mark_reviewed(entry, "A 735/A 519 as low-confidence possibly_same_as based on a conjectural name reading.")
save_page(152, doc)


# A 534 / A 535 was already modeled; retain the explicit target PIR reference.
doc = load_page(106)
entry = get_entry(doc, "A 534")
for related in entry.get("related_persons", []):
    if related.get("id") == "person_535":
        related["pir_reference"] = "A 535"
mark_reviewed(entry, "Existing A 534/A 535 possibly_same_as confirmed; target PIR reference made explicit.")
save_page(106, doc)


# A 544 / A 545: possible father and son.
doc = load_page(107)
entry = get_entry(doc, "A 544")
upsert_related(
    entry,
    external_person(
        "person_A545", "A 545", "C. ALLIVS C. F. FVSCVS", "Gaius Allius Fuscus",
        "Huius filius fortasse C. Allius C. f. Fuscus.", "medium",
        ["PIR A 545; possible, not certain, son of A 544."],
    ),
)
upsert_relation(
    entry,
    {
        "source": "person_A_544", "target": "person_A545", "relation": "parent_of",
        "certainty": "medium", "basis": "Huius filius fortasse C. Allius C. f. Fuscus.",
        "notes": ["Possible father-son relation; not an identity relation."],
    },
)
mark_reviewed(entry, "Possible parent relation A 544 -> A 545 added.")
save_page(107, doc)


# A 595 was lost because the old validator did not recognize 'Augusti vel Augustorum'.
doc = load_page(114, raw=True)
entry = get_entry(doc, "A 595")
entry["source_page"] = 114
entry["main_person"]["id"] = "person_A595"
for factoid in entry["governorship_factoids"]:
    factoid["person_id"] = "person_A595"
entry["governorship_factoids"] = [f for f in entry["governorship_factoids"] if f.get("factoid_id") in {"gov_1", "gov_2"}]
numidia = next(f for f in entry["governorship_factoids"] if f["factoid_id"] == "gov_1")
numidia.update(
    {
        "normalized_office": TARGET_OFFICE,
        "province_normalized": "Numidia",
        "date_normalized_end": 201,
        "notes": ["Attested from 196/197 through 201; the office is explicit."],
    }
)
moesia = next(f for f in entry["governorship_factoids"] if f["factoid_id"] == "gov_2")
moesia.update(
    {
        "normalized_office": TARGET_OFFICE,
        "province_normalized": "Moesia superior",
        "notes": ["The office is explicit; the exact years 202-207 remain uncertain because the tribunician-power numerals are corrupt."],
    }
)
upsert_related(
    entry,
    external_person(
        "person_A596", "A 596", "SEXTVS ANICIVS FAVSTVS", "Sextus Anicius Faustus",
        "Pater fortasse Sex. Anicii Fausti ... Anici consularis filius.", "medium",
        ["PIR A 596; possible son of A 595."],
    ),
    "PIR_A_596",
)
entry["relations"] = [
    {
        "source": "person_A595", "target": "person_A596", "relation": "parent_of",
        "certainty": "medium",
        "basis": "Pater fortasse Sex. Anicii Fausti, qui dicitur in t. Thamugadensi VIII 17890 Anici consularis filius.",
        "notes": ["Possible father-son relation; A 595 and A 596 are not identified with one another."],
    }
]
mark_reviewed(entry, "A 595 restored as governor of Numidia and Moesia superior; possible father of A 596 normalized to parent_of.")
save_page(114, doc)


# A 596 / A 599: open identity; reuse the A 596 target used by A 595.
doc = load_page(115)
entry = get_entry(doc, "A 599")
upsert_related(
    entry,
    external_person(
        "person_A596", "A 596", "SEX. ANICIVS FAVSTVS", "Sextus Anicius Faustus",
        "fortasse non diversus a Sex. Anicio Fausto (n. 596)", "medium",
        ["PIR A 596; possible son of A 595 and possibly identical with A 599."],
    ),
    "person_sex_anicius_faustus",
)
rename_relation_target(entry, "person_sex_anicius_faustus", "person_A596")
upsert_relation(
    entry,
    identity(
        "person_599", "person_A596", "medium",
        "fortasse non diversus a Sex. Anicio Fausto (n. 596)",
        ["A 596 remains a separate PIR person node; A 595 is modeled separately as his possible father."],
    ),
)
mark_reviewed(entry, "A 599/A 596 possibly_same_as added; A 595 kept separately as possible father of A 596.")
save_page(115, doc)


# A 668 was lost because the old validator did not recognize the accusative 'legatum'.
doc = load_page(130, raw=True)
entry = get_entry(doc, "A 668")
entry["source_page"] = 130
governorship = entry["governorship_factoids"][0]
governorship.update(
    {
        "normalized_office": TARGET_OFFICE,
        "province_normalized": "Syria",
        "certainty": "low",
        "evidence_type": "inferred_from_context",
        "notes": ["The governorship is a PIR inference ('putaverim'), not an explicit office attestation."],
    }
)
upsert_related(
    entry,
    external_person(
        "person_A648", "A 648", "M. ANNIVS FLAVIVS LIBO", "Marcus Annius Flavius Libo",
        "Nepos Libonis huius videtur; nepos, non filius.", "medium",
        ["PIR A 648; probable grandson, explicitly not son, of A 668."],
    ),
    "person_668_nephew",
)
entry["relations"] = [
    {
        "source": "person_668", "target": "person_668_father", "relation": "child_of",
        "certainty": "high", "basis": "Filius sine dubio M. Annii Libonis consulis a. 128", "notes": [],
    },
    {
        "source": "person_668_son", "target": "person_668", "relation": "child_of",
        "certainty": "medium", "basis": "Fortasse filius eius M. Annius Sabinus Libo", "notes": [],
    },
    {
        "source": "person_668", "target": "person_A648", "relation": "related_to",
        "certainty": "medium", "basis": "Nepos Libonis huius videtur; nepos, non filius.",
        "notes": ["Specific kinship: A 668 is the probable grandfather of A 648."],
    },
    {
        "source": "person_668_wife", "target": "person_668", "relation": "spouse_of",
        "certainty": "high", "basis": "Libonis uxorem", "notes": [],
    },
]
mark_reviewed(entry, "A 668 restored as low-certainty governor of Syria; probable grandfather relation to A 648 added.")
save_page(130, doc)


# Existing family relations: attach explicit PIR references to the external nodes.
doc = load_page(172)
entry = get_entry(doc, "A 816")
entry["related_persons"][0]["pir_reference"] = "A 817"
mark_reviewed(entry, "Existing possible parent relation A 816 -> A 817 confirmed; PIR reference made explicit.")
save_page(172, doc)


# A 836 was lost because the old validator did not recognize the accusative 'legatum'.
doc = load_page(179, raw=True)
entry = get_entry(doc, "A 836")
entry["source_page"] = 179
governorship = entry["governorship_factoids"][0]
governorship.update(
    {
        "exact_text": "ex contextu apparet eum legatum Augusti pr. pr. Moesiam inferiorem rexisse aetate Antonini Pii vel divorum fratrum",
        "normalized_office": TARGET_OFFICE,
        "province_normalized": "Moesia inferior",
        "certainty": "medium",
        "evidence_type": "inferred_from_context",
        "notes": ["The office is inferred from the context; normalized dates cover Antoninus Pius and the divi fratres."],
    }
)
upsert_related(
    entry,
    external_person(
        "person_A837", "A 837", "M. ANTONIVS HIBERVS", "Marcus Antonius Hiberus",
        "Probabiliter non diversus a consule a. 133, qui sequitur.", "medium",
        ["PIR A 837; probably identical, but retained as a separate person node."],
    ),
    "person_837",
)
entry["relations"] = [
    identity(
        "person_836", "person_A837", "medium",
        "A 836: 'Probabiliter non diversus ...'; A 837: 'Probabiliter idem qui praecedit.'",
        ["No merge; both PIR entries remain distinct."],
    )
]
mark_reviewed(entry, "A 836 restored as governor of Moesia inferior; A 836/A 837 possibly_same_as added.")
save_page(179, doc)


doc = load_page(187)
entry = get_entry(doc, "A 883")
upsert_related(
    entry,
    external_person(
        "person_A882", "A 882", "M. Antonius Zeno", "Marcus Antonius Zeno",
        "Ex posteris videtur eius qui praecedit.", "medium",
        ["PIR A 882; probable ancestor, without a more specific generation."],
    ),
    "person_882",
)
rename_relation_target(entry, "person_882", "person_A882")
mark_reviewed(entry, "Existing probable ancestor relation A 882/A 883 retained as related_to; PIR reference made explicit.")
save_page(187, doc)


doc = load_page(225)
entry = get_entry(doc, "A 1070")
entry["related_persons"][0]["pir_reference"] = "A 1071"
mark_reviewed(entry, "Existing parent relation A 1070 -> A 1071 confirmed; PIR reference made explicit.")
save_page(225, doc)


# A 1089 is not a governor, but remains a JSON relation target of A 1088.
doc = load_page(229)
entry = get_entry(doc, "A 1088")
upsert_related(
    entry,
    external_person(
        "person_A1089", "A 1089", "C. ARRIVS ANTONINVS", "Gaius Arrius Antoninus",
        "C. Arrius Antoninus ... filius.", "high",
        ["PIR A 1089; not a governor. The Daciae governorship belongs to his father A 1088."],
    ),
    "person_c_arrius_antoninus_filius",
)
rename_relation_target(entry, "person_c_arrius_antoninus_filius", "person_A1089")
mark_reviewed(entry, "A 1089 retained only as the son/relation target of governor A 1088; Daciae remains assigned to A 1088.")
save_page(229, doc)

doc = load_page(231)
entry = get_entry(doc, "A 1089")
entry["main_person"]["id"] = "person_A1089"
upsert_related(
    entry,
    external_person(
        "person_arrius_antoninus", "A 1088", "C. ARRIVS ANTONINVS", "Gaius Arrius Antoninus",
        "filius C. Arri Antonini leg. Aug. pr. pr. Daciarum", "high",
        ["The governorship of the Daciae belongs to A 1088, the father."],
    ),
    "person_1089_father",
)
rename_relation_target(entry, "person_1089_main", "person_A1089")
rename_relation_target(entry, "person_1089_father", "person_arrius_antoninus")
mark_reviewed(entry, "A 1089 remains excluded as a governor but is preserved as the child node of A 1088.")
save_page(231, doc)


# A 1180 / V 907: the later PIR resolves the older fragmentary entry.
doc = load_page(252)
entry = get_entry(doc, "A 1180")
entry["main_person"]["normalized_name"] = "Gaius Ummidius Quadratus Sallustius Sertorius"
entry["main_person"]["notes"] = [
    note for note in entry["main_person"].get("notes", [])
    if not (
        "Wahrscheinlich identisch mit G. Ummidius Quadratus" in note
        or "sameAs-Kandidat" in note
    )
]
resolved_note = (
    "The later PIR entry V 907 resolves the fragmentary A 1180 attestation as "
    "Gaius Ummidius Quadratus Sallustius Sertorius; the surviving name ending is Se]rtorius."
)
if resolved_note not in entry["main_person"].setdefault("notes", []):
    entry["main_person"]["notes"].append(resolved_note)
upsert_related(
    entry,
    external_person(
        "person_V907", "V 907", "C. VMMIDIVS QVADRATVS S[ALLVSTIVS?] SERTORIVS",
        "Gaius Ummidius Quadratus Sallustius Sertorius",
        "The new fragment assigns the inscription and the material formerly placed under A 1180 to V 907.",
        "high",
        ["V 907 is not otherwise modeled in the current A-B pilot corpus.",
         "The later PIR wording ('ita ut omnia ... ad eum pertineant') resolves the identity."],
    ),
)
entry["relations"] = [
    relation for relation in entry["relations"]
    if not (
        relation.get("source") == "person_1180"
        and relation.get("target") == "person_V907"
        and relation.get("relation") in {"possibly_same_as", "same_as"}
    )
]
upsert_relation(
    entry,
    {
        "source": "person_1180",
        "target": "person_V907",
        "relation": "same_as",
        "certainty": "high",
        "basis": "ita ut omnia, quae supra A 1180 de [A?]rtorio scripta sunt, ad eum pertineant",
        "notes": [
            "Resolved identity based on the new inscription fragment; V 907 remains an external PIR target in the A-B pilot."
        ],
    },
)
mark_reviewed(entry, "A 1180/V 907 recorded as resolved same_as (high); normalized historical name assigned to A 1180.")
save_page(252, doc)


# A 1341 / A 1342: father or grandfather, therefore not the narrower parent_of relation.
doc = load_page(287)
entry = get_entry(doc, "A 1341")
entry["related_persons"][0]["id"] = "person_A1342"
entry["related_persons"][0]["pir_reference"] = "A 1342"
entry["relations"] = [
    relation for relation in entry["relations"]
    if not (relation.get("source") == "person_A1341" and relation.get("target") in {"person_1342", "person_A1342"})
]
upsert_relation(
    entry,
    {
        "source": "person_A1341", "target": "person_A1342", "relation": "related_to",
        "certainty": "medium", "basis": "Pater vel avus eius qui sequitur; filius vel nepos eius qui praecedit.",
        "notes": ["A 1341 is either father or grandfather of A 1342; the exact generation is unresolved."],
    },
)
mark_reviewed(entry, "A 1341/A 1342 changed from parent_of to related_to because father or grandfather are alternatives.")
save_page(287, doc)


# A 1410 is the probable father of A 1409.
doc = load_page(305)
entry = get_entry(doc, "A 1410")
upsert_related(
    entry,
    external_person(
        "person_A1409", "A 1409", "AVIDIVS QVIETVS", "Avidius Quietus",
        "Filius probabiliter T. Avidii Quieti qui sequitur.", "medium",
        ["PIR A 1409; probable son of A 1410."],
    ),
    "person_avidius_quietus_jr",
)
rename_relation_target(entry, "person_avidius_quietus_jr", "person_A1409")
mark_reviewed(entry, "Existing probable son relation identified explicitly as A 1409 -> A 1410.")
save_page(305, doc)


# A 1465/A 1466 and A 1466/A 1467 are alternative, non-transitive identities.
doc = load_page(313)
entry = get_entry(doc, "A 1465")
upsert_related(
    entry,
    external_person(
        "person_A1466", "A 1466", "M. Aurelius Basileus", "Marcus Aurelius Basileus",
        "Nescio an idem is qui sequitur; idem fortasse aut is qui praecedit aut qui sequitur.",
        "low", ["A 1466 may be A 1465 or A 1467; the alternatives are not cumulative."],
    ),
)
upsert_related(
    entry,
    external_person(
        "person_A1467", "A 1467", "Aurel(ius) Basileus", "Aurelius Basileus",
        "A 1466: idem fortasse ... qui sequitur.", "low",
        ["PIR A 1467, prefect of Egypt; external relation target, not a governor in the PROVINCIA sense."],
    ),
)
entry["relations"] = [
    identity(
        "person_1465", "person_A1466", "low", "Nescio an idem is qui sequitur.",
        ["First of two alternatives stated for A 1466."],
    ),
    identity(
        "person_A1466", "person_A1467", "low", "Idem fortasse aut is qui praecedit aut qui sequitur.",
        ["Second alternative stated for A 1466; no A 1465/A 1467 edge is inferred."],
    ),
]
mark_reviewed(entry, "Alternative low-confidence identity edges A 1465/A 1466 and A 1466/A 1467 added; non-transitivity documented.")
save_page(313, doc)


# A 1592 / A 1410: rejected hypothesis, documented without a positive edge.
doc = load_page(341)
entry = get_entry(doc, "A 1592")
upsert_related(
    entry,
    external_person(
        "person_A1410", "A 1410", "T. AVIDIVS QVIETVS", "Titus Avidius Quietus",
        "Hunc non diversum ... coniecit Benndorf ... vix recte.", "low",
        ["Rejected identification hypothesis: PIR judges Benndorf's equation as 'vix recte'. No possibly_same_as edge is created."],
    ),
    "person_t_avidius_quietus",
)
rename_relation_target(entry, "person_t_avidius_quietus", "person_A1410")
entry["relations"] = [
    relation for relation in entry["relations"]
    if not (relation.get("relation") == "possibly_same_as" and relation.get("target") == "person_A1410")
]
mark_reviewed(entry, "Rejected A 1592/A 1410 identity documented as a note only; no positive possibly_same_as relation.")
save_page(341, doc)


# B 59 / H 67: reciprocal probable identity; H 67 remains external.
doc = load_page(371)
entry = get_entry(doc, "B 59")
upsert_related(
    entry,
    external_person(
        "person_H67", "H 67", "T. HELVIVS BASILA", "Titus Helvius Basila",
        "probabiliter idem atque T. Helvius Basila; idem ut videtur Basila supra B 59",
        "medium", ["PIR H 67 is not otherwise modeled in the current A-B pilot corpus."],
    ),
    "person_t_helvius_basila",
)
rename_relation_target(entry, "person_t_helvius_basila", "person_H67")
upsert_relation(
    entry,
    identity(
        "person_basila", "person_H67", "medium",
        "B 59: 'probabiliter idem atque T. Helvius Basila'; H 67: 'Idem ut videtur Basila supra B 59'",
        ["H 67 remains an external person target; no node merge was performed."],
    ),
)
mark_reviewed(entry, "B 59/H 67 possibly_same_as added; H 67 retained as an external PIR target.")
save_page(371, doc)


# B 161 -> B 164 -> B 165: normalize existing genealogical IDs and PIR references.
doc = load_page(387)
entry = get_entry(doc, "B 164")
upsert_related(
    entry,
    external_person(
        "person_B161", "B 161", "(BRVTTIVS) PRAESENS", "Bruttius Praesens",
        "Filius videtur (Bruttii) Praesentis amici Plinii (n. 161).", "medium",
        ["PIR B 161; probable father of B 164."],
    ),
    "person-bruttius-praesens-friend-pliny",
)
upsert_related(
    entry,
    external_person(
        "person_B165", "B 165", "C. BRVTTIVS PRAESENS", "Gaius Bruttius Praesens",
        "Pater sine dubio C. Bruttii Praesentis cos. a. 153 (n. 165).", "high",
        ["PIR B 165; certain son of B 164."],
    ),
    "person-c-bruttius-praesens-cos-153",
)
rename_relation_target(entry, "person-bruttius-praesens-friend-pliny", "person_B161")
rename_relation_target(entry, "person-c-bruttius-praesens-cos-153", "person_B165")
mark_reviewed(entry, "Existing genealogy normalized as B 161 probable father of B 164 and B 164 certain father of B 165.")
save_page(387, doc)


# Repair two pre-existing relation-source ID mismatches.
doc = load_page(158)
entry = get_entry(doc, "A 754")
rename_relation_target(entry, "person_A754", "person_754")
mark_reviewed(entry, "Relation source IDs normalized from person_A754 to the main-person ID person_754.")
save_page(158, doc)

doc = load_page(301)
entry = get_entry(doc, "A 1408")
rename_relation_target(entry, "person_avidius_nigrinus", "person_1408")
mark_reviewed(entry, "Relation source IDs normalized from person_avidius_nigrinus to the main-person ID person_1408.")
save_page(301, doc)


print("Identity and kinship correction overlays complete.")
