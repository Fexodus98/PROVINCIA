from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from rdflib import Literal
from rdflib.namespace import RDF


PIPELINE_DIR = Path(__file__).resolve().parents[1] / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))
MODULE_SPEC = importlib.util.spec_from_file_location(
    "provincia_json_to_rdf", PIPELINE_DIR / "06_json_to_rdf.py"
)
assert MODULE_SPEC and MODULE_SPEC.loader
RDF_GENERATOR = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(RDF_GENERATOR)


def make_factoid(
    factoid_id: str,
    province_text: str | None,
    province_normalized: str | None,
) -> dict:
    return {
        "factoid_id": factoid_id,
        "person_id": "person_1",
        "exact_text": "Test attestation",
        "normalized_office": "legatus Augusti pro praetore provinciae",
        "province_text": province_text,
        "province_normalized": province_normalized,
        "date_text": None,
        "date_normalized_start": None,
        "date_normalized_end": None,
        "certainty": "high",
        "evidence_type": "explicit",
        "notes": [],
    }


def make_entry(factoids: list[dict]) -> dict:
    return {
        "entry_id": "entry_1",
        "pir_reference": "A 1",
        "lemma": "Test person",
        "main_person": {
            "id": "person_1",
            "displayed_name": "Test person",
            "normalized_name": "Test Person",
            "pir_reference": "A 1",
            "status_markers": [],
            "notes": [],
        },
        "governorship_factoids": factoids,
    }


class ProvinceTextRdfTests(unittest.TestCase):
    def test_factoids_keep_their_own_attested_forms(self) -> None:
        graph = RDF_GENERATOR.build_graph(
            [
                make_entry(
                    [
                        make_factoid("gov_1", "Moesiae inferioris", "Moesia inferior"),
                        make_factoid("gov_2", "Moesiam inferiorem", "Moesia inferior"),
                    ]
                )
            ]
        )

        factoid_1 = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]
        factoid_2 = RDF_GENERATOR.RES["factoid/pir-a-1-gov-2"]
        province = RDF_GENERATOR.RES["province/moesia-inferior"]

        self.assertIn(
            (factoid_1, RDF_GENERATOR.ONT.provinceText, Literal("Moesiae inferioris")),
            graph,
        )
        self.assertIn(
            (factoid_2, RDF_GENERATOR.ONT.provinceText, Literal("Moesiam inferiorem")),
            graph,
        )
        self.assertIn((factoid_1, RDF_GENERATOR.ONT.province, province), graph)
        self.assertIn((factoid_2, RDF_GENERATOR.ONT.province, province), graph)
        self.assertIn(
            (province, RDF_GENERATOR.ONT.attestedForm, Literal("Moesiae inferioris")),
            graph,
        )
        self.assertIn(
            (province, RDF_GENERATOR.ONT.attestedForm, Literal("Moesiam inferiorem")),
            graph,
        )

    def test_fallback_normalization_adds_province_text(self) -> None:
        graph = RDF_GENERATOR.build_graph(
            [make_entry([make_factoid("gov_1", "Moesiae inferioris", None)])]
        )
        factoid = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]
        province = RDF_GENERATOR.RES["province/moesia-inferior"]

        self.assertIn(
            (factoid, RDF_GENERATOR.ONT.provinceText, Literal("Moesiae inferioris")),
            graph,
        )
        self.assertIn((factoid, RDF_GENERATOR.ONT.province, province), graph)

    def test_non_province_command_area_remains_on_factoid(self) -> None:
        graph = RDF_GENERATOR.build_graph(
            [make_entry([make_factoid("gov_1", "exercitus Africanus", None)])]
        )
        factoid = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]

        self.assertIn(
            (
                factoid,
                RDF_GENERATOR.ONT.commandAreaText,
                Literal("exercitus Africanus"),
            ),
            graph,
        )
        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.province)))
        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.provinceText)))
        self.assertFalse(any(graph.subjects(RDF.type, RDF_GENERATOR.ONT.Province)))

    def test_explicit_province_interpretation_keeps_command_area_separate(self) -> None:
        graph = RDF_GENERATOR.build_graph(
            [make_entry([make_factoid("gov_1", "exercitus Africanus", "Numidia")])]
        )
        factoid = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]
        province = RDF_GENERATOR.RES["province/numidia"]

        self.assertIn(
            (
                factoid,
                RDF_GENERATOR.ONT.commandAreaText,
                Literal("exercitus Africanus"),
            ),
            graph,
        )
        self.assertIn((factoid, RDF_GENERATOR.ONT.province, province), graph)
        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.provinceText)))

    def test_missing_province_text_creates_no_empty_literal(self) -> None:
        graph = RDF_GENERATOR.build_graph(
            [make_entry([make_factoid("gov_1", None, None)])]
        )
        factoid = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]

        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.province)))
        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.provinceText)))
        self.assertFalse(any(graph.objects(factoid, RDF_GENERATOR.ONT.commandAreaText)))

    def test_entry_and_factoid_keep_their_own_source_pages(self) -> None:
        entry = make_entry([make_factoid("gov_1", "Arabiae", "Arabia")])
        entry["source_page"] = 100
        entry["governorship_factoids"][0]["source_page"] = 101
        graph = RDF_GENERATOR.build_graph([entry])
        entry_uri = RDF_GENERATOR.RES["entry/pir-a-1"]
        factoid_uri = RDF_GENERATOR.RES["factoid/pir-a-1-gov-1"]

        self.assertIn(
            (entry_uri, RDF_GENERATOR.ONT.sourcePage, Literal(100, datatype=RDF_GENERATOR.XSD.integer)),
            graph,
        )
        self.assertIn(
            (factoid_uri, RDF_GENERATOR.ONT.sourcePage, Literal(101, datatype=RDF_GENERATOR.XSD.integer)),
            graph,
        )


if __name__ == "__main__":
    unittest.main()
