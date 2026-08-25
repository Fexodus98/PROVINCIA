from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from config import (
    BASE_URI,
    CANONICAL_PROVINCE_SET,
    ENTRIES_VALIDATED_DIR,
    NON_PROVINCE_COMMANDS,
    ONTOLOGY_URI,
    PROVINCE_MAP,
    RDF_DIR,
    SOURCE_WORK_LABEL,
    SOURCE_WORK_URI,
    ensure_output_dirs,
)

RES = Namespace(BASE_URI)
ONT = Namespace(ONTOLOGY_URI)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "item"


def normalize_province(attested: str | None) -> str | None:
    """Normalize an attested province string to its nominative label.

    Returns None for empty input and for attested command areas that are
    not provinces (e.g. "exercitus Africanus") — those must not become
    ont:Province resources.
    """
    if not attested:
        return None
    cleaned = attested.strip()
    # Remove brackets/parens anywhere, not only at the edges:
    # "Hispaniam (citeriorem)" -> "Hispaniam citeriorem"
    cleaned = re.sub(r"[()\[\]]", " ", cleaned)
    cleaned = re.sub(r"\bsc\.\s*", "", cleaned, flags=re.IGNORECASE)
    # Drop leading "provincia/provinciae/provinciarum" qualifiers
    cleaned = re.sub(r"\bprovinci\w*\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.")
    if not cleaned:
        return None
    key = cleaned.lower()
    if key in NON_PROVINCE_COMMANDS:
        return None
    return PROVINCE_MAP.get(key, cleaned)


def add_literal(g: Graph, s: URIRef, p: URIRef, value: Any, datatype=None) -> None:
    if value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    if datatype:
        g.add((s, p, Literal(value, datatype=datatype)))
    else:
        g.add((s, p, Literal(value)))


def build_graph(entries: list[dict[str, Any]]) -> Graph:
    g = Graph()
    g.bind("res", RES)
    g.bind("ont", ONT)

    work_uri = URIRef(SOURCE_WORK_URI)
    g.add((work_uri, RDF.type, ONT.SourceWork))
    add_literal(g, work_uri, RDFS.label, SOURCE_WORK_LABEL)

    for entry in entries:
        entry_id = entry["entry_id"]
        # Prefer the normalized PIR reference for stable, citable URIs
        # (entry/pir-a-1322); fall back to the model-assigned entry_id.
        pir_ref = entry.get("pir_reference")
        entry_slug = f"pir-{slugify(pir_ref)}" if pir_ref else slugify(entry_id)
        entry_uri = RES[f"entry/{entry_slug}"]
        g.add((entry_uri, RDF.type, ONT.PIREntry))
        add_literal(g, entry_uri, RDFS.label, entry.get("lemma"))
        add_literal(g, entry_uri, ONT.pirReference, entry.get("pir_reference"))
        add_literal(g, entry_uri, ONT.sourcePage, entry.get("source_page"), XSD.integer)
        g.add((entry_uri, ONT.sourceWork, work_uri))

        review = entry.get("review", {})
        add_literal(g, entry_uri, ONT.needsReview, bool(entry.get("needs_review")), XSD.boolean)
        add_literal(g, entry_uri, ONT.reviewVerdict, review.get("verdict"))
        for problem in review.get("problems", []):
            severity = problem.get("severity", "?")
            field = problem.get("field", "?")
            issue = problem.get("issue", "")
            add_literal(g, entry_uri, ONT.reviewProblem, f"[{severity}] {field}: {issue}")

        person = entry["main_person"]
        person_id = person["id"]
        # Namespace local IDs by entry_slug to prevent cross-entry URI collisions
        # (the model often re-uses generic ids like "p1" / "gov-1" per page).
        person_uri = RES[f"person/{entry_slug}-{slugify(person_id)}"]
        g.add((person_uri, RDF.type, ONT.Person))
        add_literal(g, person_uri, ONT.displayedName, person.get("displayed_name"))
        add_literal(g, person_uri, ONT.normalizedName, person.get("normalized_name"))
        add_literal(g, person_uri, ONT.pirReference, person.get("pir_reference"))
        g.add((person_uri, ONT.attestedIn, entry_uri))

        for marker in person.get("status_markers", []):
            add_literal(g, person_uri, ONT.statusMarker, marker)
        for note in person.get("notes", []):
            add_literal(g, person_uri, ONT.note, note)

        for factoid in entry.get("governorship_factoids", []):
            factoid_uri = RES[f"factoid/{entry_slug}-{slugify(factoid['factoid_id'])}"]
            g.add((factoid_uri, RDF.type, ONT.GovernorshipFactoid))
            g.add((factoid_uri, ONT.aboutPerson, person_uri))
            g.add((factoid_uri, ONT.derivedFromEntry, entry_uri))
            add_literal(g, factoid_uri, ONT.exactText, factoid.get("exact_text"))
            add_literal(g, factoid_uri, ONT.dateText, factoid.get("date_text"))
            add_literal(g, factoid_uri, ONT.certainty, factoid.get("certainty"))
            add_literal(g, factoid_uri, ONT.evidenceType, factoid.get("evidence_type"))
            add_literal(g, factoid_uri, ONT.dateNormalizedStart, factoid.get("date_normalized_start"), XSD.integer)
            add_literal(g, factoid_uri, ONT.dateNormalizedEnd, factoid.get("date_normalized_end"), XSD.integer)

            office_label = factoid.get("normalized_office")
            if office_label:
                office_uri = RES[f"office/{slugify(office_label)}"]
                g.add((office_uri, RDF.type, ONT.Office))
                add_literal(g, office_uri, RDFS.label, office_label)
                g.add((factoid_uri, ONT.normalizedOffice, office_uri))

            province_attested = factoid.get("province_text")
            # Prefer the LLM's registry-validated label; fall back to the
            # deterministic case-form normalization of the attested text.
            province_label = factoid.get("province_normalized")
            if province_label and province_label.lower() not in CANONICAL_PROVINCE_SET:
                print(f"[WARN] province_normalized not in registry: {province_label!r} (entry {entry_id})")
                province_label = None
            if not province_label:
                province_label = normalize_province(province_attested)
                if province_label and province_label.lower() not in CANONICAL_PROVINCE_SET:
                    print(f"[WARN] unmapped province form kept as-is: {province_label!r} (entry {entry_id})")
            if province_label:
                province_uri = RES[f"province/{slugify(province_label)}"]
                g.add((province_uri, RDF.type, ONT.Province))
                add_literal(g, province_uri, RDFS.label, province_label)
                add_literal(g, province_uri, ONT.attestedForm, province_attested)
                if province_attested and normalize_province(province_attested) is None:
                    add_literal(g, factoid_uri, ONT.commandAreaText, province_attested)
                else:
                    add_literal(g, factoid_uri, ONT.provinceText, province_attested)
                g.add((factoid_uri, ONT.province, province_uri))
            elif province_attested:
                # Non-province command area (e.g. "exercitus Africanus") or
                # unparseable attestation: keep the raw text on the factoid.
                add_literal(g, factoid_uri, ONT.commandAreaText, province_attested)

            for note in factoid.get("notes", []):
                add_literal(g, factoid_uri, ONT.note, note)

    return g


def main() -> None:
    ensure_output_dirs()
    entries_path = ENTRIES_VALIDATED_DIR / "provincia_entries.json"
    data = json.loads(entries_path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    graph = build_graph(entries)

    ttl_path = RDF_DIR / "provincia_graph.ttl"
    jsonld_path = RDF_DIR / "provincia_graph.jsonld"
    rdfxml_path = RDF_DIR / "provincia_graph.rdf"
    nt_path = RDF_DIR / "provincia_graph.nt"

    graph.serialize(ttl_path, format="turtle")
    graph.serialize(jsonld_path, format="json-ld")
    graph.serialize(rdfxml_path, format="pretty-xml")
    graph.serialize(nt_path, format="nt")
    print(f"[DONE] wrote RDF files to {RDF_DIR}")


if __name__ == "__main__":
    main()
