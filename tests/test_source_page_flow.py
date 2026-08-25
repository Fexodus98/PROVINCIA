from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_DIR = REPO_ROOT / "pipeline"
sys.path.insert(0, str(PIPELINE_DIR))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("provincia_validate_entries", PIPELINE_DIR / "05_validate_entries.py")
CORRECTIONS = load_module("provincia_apply_corrections", REPO_ROOT / "data" / "apply_corrections.py")


def raw_entry(entry_id: str, factoid_id: str, exact_text: str) -> dict:
    return {
        "entry_id": entry_id,
        "pir_reference": "A 500",
        "lemma": "Test person",
        "main_person": {
            "id": "person_500",
            "displayed_name": "Test person",
            "normalized_name": "Test Person",
            "pir_reference": "A 500",
            "status_markers": [],
            "notes": [],
        },
        "governorship_factoids": [
            {
                "factoid_id": factoid_id,
                "person_id": "person_500",
                "exact_text": exact_text,
                "normalized_office": "legatus Augusti pro praetore provinciae",
                "province_text": "Syria",
                "province_normalized": "Syria",
                "date_text": None,
                "date_normalized_start": None,
                "date_normalized_end": None,
                "certainty": "high",
                "evidence_type": "explicit",
                "notes": [],
            }
        ],
        "career_factoids": [],
        "related_persons": [],
        "relations": [],
        "entry_notes": [],
    }


class SourcePageValidationTests(unittest.TestCase):
    def test_page_validation_assigns_file_context_page(self) -> None:
        document = {
            "entries": [
                raw_entry(
                    "entry_500",
                    "gov_1",
                    "legatus Augusti pro praetore Syriae",
                )
            ]
        }

        validated = VALIDATOR.validate_page(document, page_no=60)

        self.assertEqual(validated["entries"][0]["governorship_factoids"][0]["source_page"], 60)

    def test_cross_page_merge_preserves_both_factoid_pages(self) -> None:
        primary = VALIDATOR.validate_page(
            {
                "entries": [
                    raw_entry(
                        "entry_500",
                        "gov_1",
                        "legatus Augusti pro praetore Syriae",
                    )
                ]
            },
            page_no=100,
        )["entries"][0]
        secondary = VALIDATOR.validate_page(
            {
                "entries": [
                    raw_entry(
                        "entry_500_continuation",
                        "gov_2",
                        "legatus Augusti pro praetore provinciae Syriae",
                    )
                ]
            },
            page_no=101,
        )["entries"][0]
        primary["_page"] = 100
        secondary["_page"] = 101

        merged = VALIDATOR.merge_entries(primary, secondary)

        pages = {
            factoid["factoid_id"]: factoid["source_page"]
            for factoid in merged["governorship_factoids"]
        }
        self.assertEqual(pages, {"gov_1": 100, "gov_2": 101})


class SourcePageOverlayTests(unittest.TestCase):
    def test_final_report_reflects_post_overlay_review_status(self) -> None:
        entries = [
            {
                "entry_id": "PIR_A_1",
                "pir_reference": "A 1",
                "lemma": "Reviewed",
                "source_page": 10,
                "needs_review": False,
                "review": {"verdict": "human_corrected"},
            }
        ]
        previous = {"missed_entries_reported_by_judge": [{"page": 20, "lemma": "Historical"}]}

        report = CORRECTIONS.build_final_review_report(entries, previous)

        self.assertEqual(report["total_entries"], 1)
        self.assertEqual(report["flagged_entries"], 0)
        self.assertEqual(report["missed_entries_reported_by_judge"], [])
        self.assertEqual(len(report["assessed_missed_entries_reported_by_judge"]), 1)

        repeated = CORRECTIONS.build_final_review_report(entries, report)
        self.assertEqual(len(repeated["assessed_missed_entries_reported_by_judge"]), 1)

    def test_pir_sort_key_uses_letter_and_numeric_order(self) -> None:
        entries = [
            {"pir_reference": "B 1", "entry_id": "b1"},
            {"pir_reference": "A 10", "entry_id": "a10"},
            {"pir_reference": "A 2", "entry_id": "a2"},
        ]

        entries.sort(key=CORRECTIONS.pir_sort_key)

        self.assertEqual([entry["pir_reference"] for entry in entries], ["A 2", "A 10", "B 1"])

    def test_entry_overlay_never_overwrites_explicit_page(self) -> None:
        existing = {"source_page": 166}
        corrected = {"source_page": 165}

        CORRECTIONS.preserve_entry_source_page(corrected, existing, 166)

        self.assertEqual(corrected["source_page"], 165)

    def test_entry_overlay_preserves_existing_page_without_explicit_correction(self) -> None:
        existing = {"source_page": 165}
        corrected = {}

        CORRECTIONS.preserve_entry_source_page(corrected, existing, 166)

        self.assertEqual(corrected["source_page"], 165)

    def test_overlay_preserves_page_when_content_changes(self) -> None:
        existing = {
            "governorship_factoids": [
                {"factoid_id": "gov_1", "exact_text": "Old text", "source_page": 124}
            ]
        }
        corrected = {
            "governorship_factoids": [
                {"factoid_id": "gov_1", "exact_text": "Corrected text"}
            ]
        }

        CORRECTIONS.preserve_factoid_source_pages(corrected, existing)

        self.assertEqual(corrected["governorship_factoids"][0]["source_page"], 124)

    def test_overlay_falls_back_to_unique_exact_text(self) -> None:
        existing = {
            "governorship_factoids": [
                {"factoid_id": "old_id", "exact_text": " Legatus  Syriae ", "source_page": 125}
            ]
        }
        corrected = {
            "governorship_factoids": [
                {"factoid_id": "new_id", "exact_text": "legatus syriae"}
            ]
        }

        CORRECTIONS.preserve_factoid_source_pages(corrected, existing)

        self.assertEqual(corrected["governorship_factoids"][0]["source_page"], 125)

    def test_overlay_never_overwrites_explicit_page(self) -> None:
        existing = {
            "governorship_factoids": [
                {"factoid_id": "gov_1", "exact_text": "Text", "source_page": 126}
            ]
        }
        corrected = {
            "governorship_factoids": [
                {"factoid_id": "gov_1", "exact_text": "Text", "source_page": 200}
            ]
        }

        CORRECTIONS.preserve_factoid_source_pages(corrected, existing)

        self.assertEqual(corrected["governorship_factoids"][0]["source_page"], 200)

    def test_overlay_does_not_invent_page_for_new_factoid(self) -> None:
        corrected = {
            "governorship_factoids": [
                {"factoid_id": "gov_new", "exact_text": "New attestation"}
            ]
        }

        CORRECTIONS.preserve_factoid_source_pages(corrected)

        self.assertIsNone(corrected["governorship_factoids"][0]["source_page"])

    def test_overlay_can_use_exact_raw_page_context(self) -> None:
        raw_document = {
            "entries": [
                {
                    "governorship_factoids": [
                        {"factoid_id": "raw_id", "exact_text": "Raw attestation"}
                    ]
                }
            ]
        }
        corrected = {
            "governorship_factoids": [
                {"factoid_id": "corrected_id", "exact_text": "Raw attestation"}
            ]
        }
        raw_context = CORRECTIONS.raw_page_factoid_context(raw_document, 130)

        CORRECTIONS.preserve_factoid_source_pages(corrected, raw_context)

        self.assertEqual(corrected["governorship_factoids"][0]["source_page"], 130)


if __name__ == "__main__":
    unittest.main()
