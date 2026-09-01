from __future__ import annotations

import json
import unittest
from pathlib import Path

from rdflib import Graph, Literal, URIRef


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ENTRIES_PATH = DATA / "entries_validated" / "provincia_entries.json"
RDF_PATH = DATA / "rdf" / "provincia_graph.ttl"
ONTOLOGY = "https://provincia.uni-graz.at/ontology/"
RESOURCE = "https://provincia.uni-graz.at/resource/"


class AdditionalGovernorCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        document = json.loads(ENTRIES_PATH.read_text(encoding="utf-8"))
        cls.entries = {entry["pir_reference"]: entry for entry in document["entries"]}

    def test_all_reviewed_entries_are_present_under_the_correct_pir_numbers(self) -> None:
        expected = {"A 101", "A 200", "A 776", "A 1304", "A 1331", "A 1350", "A 1517"}
        self.assertTrue(expected.issubset(self.entries))
        self.assertNotIn("A 1498", self.entries)

    def test_final_corpus_has_unique_entries_complete_factoid_pages_and_valid_relations(self) -> None:
        document = json.loads(ENTRIES_PATH.read_text(encoding="utf-8"))
        entries = document["entries"]
        references = [entry["pir_reference"] for entry in entries]
        self.assertEqual(len(references), len(set(references)))

        allowed_relations = {
            "parent_of",
            "child_of",
            "sibling_of",
            "spouse_of",
            "related_to",
            "predecessor_of",
            "successor_of",
            "associated_with",
            "office_holder_of",
            "possibly_same_as",
            "same_as",
        }
        for entry in entries:
            person_ids = {entry["main_person"]["id"]}
            person_ids.update(person["id"] for person in entry.get("related_persons", []))
            for factoid in entry.get("governorship_factoids", []):
                self.assertIsInstance(factoid.get("source_page"), int, entry["pir_reference"])
            for relation in entry.get("relations", []):
                self.assertIn(relation.get("relation"), allowed_relations, entry["pir_reference"])
                self.assertIn(relation.get("source"), person_ids, entry["pir_reference"])
                self.assertIn(relation.get("target"), person_ids, entry["pir_reference"])

    def test_a200_models_syria_and_records_non_assumption(self) -> None:
        entry = self.entries["A 200"]
        self.assertEqual(len(entry["governorship_factoids"]), 1)
        factoid = entry["governorship_factoids"][0]
        self.assertEqual(factoid["province_normalized"], "Syria")
        self.assertEqual(factoid["source_page"], 51)
        combined_notes = " ".join(factoid["notes"]).lower()
        self.assertIn("never entered syria", combined_notes)
        self.assertNotIn("pannonia", {f.get("province_normalized") for f in entry["governorship_factoids"]})

    def test_a101_and_a776_record_date_uncertainty_and_cross_page_source(self) -> None:
        a101 = self.entries["A 101"]
        a776 = self.entries["A 776"]
        self.assertIn("only its dating is uncertain", " ".join(a101["governorship_factoids"][0]["notes"]))
        self.assertEqual(a776["source_page"], 165)
        self.assertEqual(a776["governorship_factoids"][0]["source_page"], 166)
        self.assertIn("beginning in AD 55 is only probable", " ".join(a776["governorship_factoids"][0]["notes"]))

    def test_a338_excludes_lugdunensis_census_commission_and_records_dacia_debate(self) -> None:
        entry = self.entries["A 338"]
        factoids = {factoid["factoid_id"]: factoid for factoid in entry["governorship_factoids"]}

        self.assertEqual(
            {factoid["province_normalized"] for factoid in factoids.values()},
            {"Arabia", "Cappadocia", "Tres Daciae"},
        )
        self.assertNotIn("gov_A338_lugdunensis", factoids)
        self.assertIn("Zensus-Sonderauftrag", " ".join(entry["main_person"]["notes"]))

        dacia_notes = " ".join(factoids["gov_A338_dacia"]["notes"])
        self.assertIn("Ritterling", dacia_notes)
        self.assertIn("Sohn", dacia_notes)
        self.assertIn("weisen diese Theorie", dacia_notes)

        graph = Graph().parse(RDF_PATH, format="turtle")
        removed_factoid = URIRef(f"{RESOURCE}factoid/pir-a-338-gov-a338-lugdunensis")
        self.assertNotIn((removed_factoid, None, None), graph)

    def test_a1408_excludes_senatorial_achaia_but_preserves_extraordinary_commission_note(self) -> None:
        entry = self.entries["A 1408"]
        factoids = entry["governorship_factoids"]

        self.assertEqual(len(factoids), 1)
        self.assertEqual(factoids[0]["province_normalized"], "Moesia superior")
        self.assertNotIn("gov_1408_achaia", {factoid["factoid_id"] for factoid in factoids})

        person_notes = " ".join(entry["main_person"]["notes"])
        self.assertIn("proconsulis loco", person_notes)
        self.assertIn("keine reguläre kaiserliche Statthalterschaft", person_notes)

        graph = Graph().parse(RDF_PATH, format="turtle")
        removed_factoid = URIRef(f"{RESOURCE}factoid/pir-a-1408-gov-1408-achaia")
        self.assertNotIn((removed_factoid, None, None), graph)

    def test_known_related_people_have_pir_references(self) -> None:
        expected = {
            "A 1304": {"person_1305": "A 1305"},
            "A 1331": {"person_A_1332": "A 1332"},
            "A 1517": {"person_l_aurelius_gallus_cos_174": "A 1516"},
        }
        for entry_ref, people in expected.items():
            actual = {person["id"]: person.get("pir_reference") for person in self.entries[entry_ref]["related_persons"]}
            for person_id, pir_reference in people.items():
                self.assertEqual(actual.get(person_id), pir_reference)

    def test_a1304_not_a1305_holds_both_governorships(self) -> None:
        factoids = self.entries["A 1304"]["governorship_factoids"]
        self.assertEqual({f["province_normalized"] for f in factoids}, {"Pannonia", "Syria"})
        self.assertNotIn("A 1305", self.entries)

    def test_a1517_rdf_factoid_has_correct_source_page_and_province(self) -> None:
        graph = Graph().parse(RDF_PATH, format="turtle")
        factoid_uri = URIRef(f"{RESOURCE}factoid/pir-a-1517-gov-l-aurelius-gallus-moesia-inf")
        self.assertIn(
            (factoid_uri, URIRef(f"{ONTOLOGY}sourcePage"), Literal(330)),
            graph,
        )
        self.assertIn(
            (
                factoid_uri,
                URIRef(f"{ONTOLOGY}province"),
                URIRef(f"{RESOURCE}province/moesia-inferior"),
            ),
            graph,
        )


if __name__ == "__main__":
    unittest.main()
