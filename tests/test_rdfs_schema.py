from pathlib import Path
import unittest

from rdflib import Graph, RDF, RDFS, URIRef


ROOT = Path(__file__).resolve().parents[1]
DATA_GRAPH = ROOT / "data" / "rdf" / "provincia_graph.ttl"
SCHEMA_GRAPH = ROOT / "data" / "rdf" / "provincia_schema.ttl"
ONT = "https://provincia.uni-graz.at/ontology/"
GENERATOR_PROPERTIES = {
    "aboutPerson",
    "attestedForm",
    "attestedIn",
    "certainty",
    "commandAreaText",
    "dateNormalizedEnd",
    "dateNormalizedStart",
    "dateText",
    "derivedFromEntry",
    "displayedName",
    "evidenceType",
    "exactText",
    "needsReview",
    "normalizedName",
    "normalizedOffice",
    "note",
    "pirReference",
    "province",
    "provinceText",
    "reviewProblem",
    "reviewVerdict",
    "sourcePage",
    "sourceWork",
    "statusMarker",
}


class RdfsSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = Graph().parse(DATA_GRAPH, format="turtle")
        cls.schema = Graph().parse(SCHEMA_GRAPH, format="turtle")

    def test_every_used_provincia_class_is_declared(self) -> None:
        used_classes = {
            obj
            for obj in self.data.objects(None, RDF.type)
            if isinstance(obj, URIRef) and str(obj).startswith(ONT)
        }
        declared_classes = set(self.schema.subjects(RDF.type, RDFS.Class))

        self.assertEqual(used_classes - declared_classes, set())

    def test_every_used_provincia_property_is_declared(self) -> None:
        used_properties = {
            predicate
            for predicate in self.data.predicates()
            if str(predicate).startswith(ONT)
        }
        declared_properties = set(self.schema.subjects(RDF.type, RDF.Property))

        self.assertEqual(used_properties - declared_properties, set())

    def test_every_generator_property_is_declared(self) -> None:
        declared_properties = {
            str(prop).removeprefix(ONT)
            for prop in self.schema.subjects(RDF.type, RDF.Property)
            if str(prop).startswith(ONT)
        }

        self.assertEqual(declared_properties, GENERATOR_PROPERTIES)

    def test_every_declared_property_has_domain_and_range(self) -> None:
        for prop in self.schema.subjects(RDF.type, RDF.Property):
            with self.subTest(property=str(prop)):
                self.assertTrue(any(self.schema.objects(prop, RDFS.domain)))
                self.assertTrue(any(self.schema.objects(prop, RDFS.range)))

    def test_json_only_person_relations_are_not_claimed_as_rdf_properties(self) -> None:
        for local_name in ("possiblySameAs", "parentOf", "childOf", "relatedTo"):
            self.assertNotIn(
                (URIRef(ONT + local_name), RDF.type, RDF.Property),
                self.schema,
            )


if __name__ == "__main__":
    unittest.main()
