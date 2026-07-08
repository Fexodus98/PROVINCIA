from __future__ import annotations

import os
from pathlib import Path

# --- Core paths -------------------------------------------------------------
BASE_DIR = Path(os.environ.get("PROVINCIA_BASE_DIR", Path.cwd()))
INPUT_PDF = Path(os.environ.get("PROVINCIA_INPUT_PDF", BASE_DIR / "input" / "pir_band.pdf"))
OUTPUT_DIR = Path(os.environ.get("PROVINCIA_OUTPUT_DIR", BASE_DIR / "output"))

PAGES_DIR = OUTPUT_DIR / "pages"
OCR_TXT_DIR = OUTPUT_DIR / "ocr_txt"
OCR_TSV_DIR = OUTPUT_DIR / "ocr_tsv"
CANDIDATES_DIR = OUTPUT_DIR / "candidates"
ENTRIES_RAW_DIR = OUTPUT_DIR / "entries_raw"
ENTRIES_JUDGED_DIR = OUTPUT_DIR / "entries_judged"
ENTRIES_VALIDATED_DIR = OUTPUT_DIR / "entries_validated"
RDF_DIR = OUTPUT_DIR / "rdf"
LOGS_DIR = OUTPUT_DIR / "logs"

# --- PDF rendering ----------------------------------------------------------
RENDER_DPI = int(os.environ.get("PROVINCIA_RENDER_DPI", "300"))
PAGE_LIMIT = int(os.environ.get("PROVINCIA_PAGE_LIMIT", "0"))  # 0 = unlimited

# --- OCR -------------------------------------------------------------------
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "tesseract")
TESS_LANG = os.environ.get("PROVINCIA_TESS_LANG", "lat+eng")
TESS_OEM = int(os.environ.get("PROVINCIA_TESS_OEM", "1"))
TESS_PSM = int(os.environ.get("PROVINCIA_TESS_PSM", "6"))

# --- Candidate discovery ----------------------------------------------------
# Covers nom/gen/acc/dat (legatus/legati/legatum/legato) + abbrev "leg.",
# both Aug. / Augusti / Augustorum / Augg., and pro praetore / pr. pr. / pr.pr.
# Whitespace tolerant (whitespace or short OCR-noise between tokens).
_LEG = r"leg(?:atus|ati|atum|ato|\.)"
_AUG = r"Aug(?:ustorum|usti|g\.|\.)"
_PR = r"(?:pro\s+praetore|pro\s+pr\.?|pr\.?\s*pr\.?)"
_GAP = r"\s+"
FORMULA_PATTERNS = [
    rf"{_LEG}{_GAP}{_AUG}{_GAP}{_PR}",
]
CONTEXT_WINDOW = int(os.environ.get("PROVINCIA_CONTEXT_WINDOW", "160"))

# --- API extraction (Mistral) ------------------------------------------------
# Set MISTRAL_API_KEY in your environment (PowerShell: setx MISTRAL_API_KEY "...").
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.environ.get("PROVINCIA_MISTRAL_MODEL", "mistral-medium-latest")
# Judge model for the verification pass (04b): strongest vision model.
MISTRAL_JUDGE_MODEL = os.environ.get("PROVINCIA_MISTRAL_JUDGE_MODEL", "mistral-large-latest")
MISTRAL_OCR_MODEL = os.environ.get("PROVINCIA_MISTRAL_OCR_MODEL", "mistral-ocr-latest")
# Generous output budget: a dense PIR page can produce >20k chars of JSON.
MISTRAL_MAX_TOKENS = int(os.environ.get("PROVINCIA_MISTRAL_MAX_TOKENS", "32768"))

# --- Legacy Gemini config (kept for reference; pipeline now runs on Mistral) --
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("PROVINCIA_GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_JUDGE_MODEL = os.environ.get("PROVINCIA_GEMINI_JUDGE_MODEL", "gemini-3.1-pro-preview")
GEMINI_MAX_OUTPUT_TOKENS = int(os.environ.get("PROVINCIA_GEMINI_MAX_OUTPUT_TOKENS", "65536"))
GEMINI_JUDGE_MAX_OUTPUT_TOKENS = int(os.environ.get("PROVINCIA_GEMINI_JUDGE_MAX_OUTPUT_TOKENS", "65536"))

# --- RDF -------------------------------------------------------------------
BASE_URI = os.environ.get("PROVINCIA_BASE_URI", "https://provincia.uni-graz.at/resource/")
ONTOLOGY_URI = os.environ.get("PROVINCIA_ONTOLOGY_URI", "https://provincia.uni-graz.at/ontology/")
SOURCE_WORK_URI = os.environ.get("PROVINCIA_SOURCE_WORK_URI", BASE_URI + "source/pir-work")
SOURCE_WORK_LABEL = os.environ.get("PROVINCIA_SOURCE_WORK_LABEL", "Prosopographia Imperii Romani")

# Keys are matched lower-cased after bracket/"provincia"-word stripping.
# Covers nominative, genitive and accusative attestations.
PROVINCE_MAP = {
    "achaiae": "Achaia",
    "achaiam": "Achaia",
    "arabiae": "Arabia",
    "arabiam": "Arabia",
    "britanniae": "Britannia",
    "britanniam": "Britannia",
    "cappadociae": "Cappadocia",
    "cappadociam": "Cappadocia",
    "ciliciae": "Cilicia",
    "daciae": "Dacia",
    "daciam": "Dacia",
    "daciarum": "Tres Daciae",
    "trium daciarum": "Tres Daciae",
    "tres daciae": "Tres Daciae",
    "dalmatiae": "Dalmatia",
    "dalmatiam": "Dalmatia",
    "galatiae": "Galatia",
    "galatiam": "Galatia",
    "galliae lugdunensis": "Gallia Lugdunensis",
    "lugdunensis": "Gallia Lugdunensis",
    "lugudunensis": "Gallia Lugdunensis",
    "germaniae inferioris": "Germania inferior",
    "germaniam inferiorem": "Germania inferior",
    "germaniae superioris": "Germania superior",
    "germaniam superiorem": "Germania superior",
    "hispaniae citerioris": "Hispania citerior",
    "hispaniam citeriorem": "Hispania citerior",
    "hispaniae ulterioris": "Hispania ulterior",
    "hispaniam": "Hispania",
    "lyciae et pamphyliae": "Lycia et Pamphylia",
    "mauretaniae": "Mauretania",
    "moesiae inferioris": "Moesia inferior",
    "moesiam inferiorem": "Moesia inferior",
    "moesiae superioris": "Moesia superior",
    "moesiam superiorem": "Moesia superior",
    "noricae": "Noricum",
    "numidiae": "Numidia",
    "pannoniae": "Pannonia",
    "pannoniam": "Pannonia",
    "pannoniae inferioris": "Pannonia inferior",
    "pannoniam inferiorem": "Pannonia inferior",
    "pannoniae superioris": "Pannonia superior",
    "ponti et bithyniae": "Pontus et Bithynia",
    "syriae": "Syria",
    "syriam": "Syria",
    "syriae coeles": "Syria Coele",
    "thraciae": "Thracia",
    "thraciam": "Thracia",
}

# Attested command areas that are NOT provinces. These keep their attested
# form in the RDF but must not be minted as ont:Province resources.
NON_PROVINCE_COMMANDS = {
    "exercitus africanus",
    "exercitus illyricus",
}

# Canonical registry of imperial-era provinces (nominative). The LLM picks
# province_normalized from this list (or null); stage 6 warns when a
# normalized label is not in the registry so unknown forms surface for review.
CANONICAL_PROVINCES = [
    "Achaia", "Aegyptus", "Africa proconsularis", "Alpes Cottiae",
    "Alpes Graiae et Poeninae", "Alpes Maritimae", "Aquitania", "Arabia",
    "Armenia", "Asia", "Baetica", "Belgica", "Bithynia et Pontus",
    "Britannia", "Cappadocia", "Cilicia", "Corsica et Sardinia", "Creta et Cyrenae",
    "Cyprus", "Dacia", "Dacia Apulensis", "Dacia Malvensis", "Dacia Porolissensis",
    "Tres Daciae", "Dalmatia", "Epirus", "Galatia", "Gallia Lugdunensis",
    "Gallia Narbonensis", "Germania inferior", "Germania superior", "Hispania",
    "Hispania citerior", "Hispania ulterior", "Iudaea", "Lusitania",
    "Lycia et Pamphylia", "Macedonia", "Mauretania", "Mauretania Caesariensis",
    "Mauretania Tingitana", "Mesopotamia", "Moesia", "Moesia inferior",
    "Moesia superior", "Noricum", "Numidia", "Pannonia", "Pannonia inferior",
    "Pannonia superior", "Pontus et Bithynia", "Raetia", "Sicilia", "Syria",
    "Syria Coele", "Syria Palaestina", "Syria Phoenice", "Thracia",
    # joint/special commands attested in PIR
    "Cappadocia et Galatia", "Lycia", "Pamphylia",
]
CANONICAL_PROVINCE_SET = {p.lower() for p in CANONICAL_PROVINCES}

ALLOWED_RELATIONS = {
    "parent_of",
    "child_of",
    "sibling_of",
    "spouse_of",
    "related_to",
    "predecessor_of",
    "successor_of",
    "associated_with",
    "office_holder_of",
}

ENTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_notes": {"type": "array", "items": {"type": "string"}},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "entry_id": {"type": "string"},
                    "pir_reference": {"type": ["string", "null"]},
                    "lemma": {"type": "string"},
                    "relevance_to_provincia_corpus": {
                        "type": "string",
                        "enum": ["yes", "no", "uncertain"],
                    },
                    "relevance_notes": {"type": "string"},
                    "segments": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "lemma": {"type": "string"},
                            "name_variants": {"type": "string"},
                            "identification_and_sources": {"type": "string"},
                            "offices_and_career": {"type": "string"},
                            "governorship_attestation": {"type": "string"},
                            "family_and_social_relations": {"type": "string"},
                            "prosopographical_commentary": {"type": "string"},
                            "bibliography_or_cross_references": {"type": "string"},
                        },
                        "required": [
                            "lemma",
                            "name_variants",
                            "identification_and_sources",
                            "offices_and_career",
                            "governorship_attestation",
                            "family_and_social_relations",
                            "prosopographical_commentary",
                            "bibliography_or_cross_references",
                        ],
                    },
                    "main_person": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "displayed_name": {"type": "string"},
                            "normalized_name": {"type": ["string", "null"]},
                            "pir_reference": {"type": ["string", "null"]},
                            "status_markers": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": [
                            "id",
                            "displayed_name",
                            "normalized_name",
                            "pir_reference",
                            "status_markers",
                            "notes",
                        ],
                    },
                    "governorship_factoids": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "factoid_id": {"type": "string"},
                                "person_id": {"type": "string"},
                                "exact_text": {"type": "string"},
                                "normalized_office": {"type": ["string", "null"]},
                                "province_text": {"type": ["string", "null"]},
                                "province_normalized": {"type": ["string", "null"]},
                                "date_text": {"type": ["string", "null"]},
                                "date_normalized_start": {"type": ["integer", "null"]},
                                "date_normalized_end": {"type": ["integer", "null"]},
                                "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                                "evidence_type": {
                                    "type": "string",
                                    "enum": ["explicit", "inferred_from_context", "uncertain_reading"],
                                },
                                "notes": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "factoid_id",
                                "person_id",
                                "exact_text",
                                "normalized_office",
                                "province_text",
                                "province_normalized",
                                "date_text",
                                "date_normalized_start",
                                "date_normalized_end",
                                "certainty",
                                "evidence_type",
                                "notes",
                            ],
                        },
                    },
                    "career_factoids": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "factoid_id": {"type": "string"},
                                "person_id": {"type": "string"},
                                "exact_text": {"type": "string"},
                                "normalized_office": {"type": ["string", "null"]},
                                "province_text": {"type": ["string", "null"]},
                                "province_normalized": {"type": ["string", "null"]},
                                "date_text": {"type": ["string", "null"]},
                                "date_normalized_start": {"type": ["integer", "null"]},
                                "date_normalized_end": {"type": ["integer", "null"]},
                                "relevance_to_governorship": {"type": "string", "enum": ["high", "medium", "low"]},
                                "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                                "evidence_type": {
                                    "type": "string",
                                    "enum": ["explicit", "inferred_from_context", "uncertain_reading"],
                                },
                                "notes": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "factoid_id",
                                "person_id",
                                "exact_text",
                                "normalized_office",
                                "province_text",
                                "province_normalized",
                                "date_text",
                                "date_normalized_start",
                                "date_normalized_end",
                                "relevance_to_governorship",
                                "certainty",
                                "evidence_type",
                                "notes",
                            ],
                        },
                    },
                    "related_persons": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string"},
                                "displayed_name": {"type": "string"},
                                "normalized_name": {"type": ["string", "null"]},
                                "relation_context": {"type": "string"},
                                "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                                "notes": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "id",
                                "displayed_name",
                                "normalized_name",
                                "relation_context",
                                "certainty",
                                "notes",
                            ],
                        },
                    },
                    "relations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "source": {"type": "string"},
                                "target": {"type": "string"},
                                "relation": {"type": "string"},
                                "certainty": {"type": "string", "enum": ["high", "medium", "low"]},
                                "basis": {"type": "string"},
                                "notes": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["source", "target", "relation", "certainty", "basis", "notes"],
                        },
                    },
                    "entry_notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "entry_id",
                    "pir_reference",
                    "lemma",
                    "relevance_to_provincia_corpus",
                    "relevance_notes",
                    "segments",
                    "main_person",
                    "governorship_factoids",
                    "career_factoids",
                    "related_persons",
                    "relations",
                    "entry_notes",
                ],
            },
        },
    },
    "required": ["document_notes", "entries"],
}


def ensure_output_dirs() -> None:
    for path in [
        OUTPUT_DIR,
        PAGES_DIR,
        OCR_TXT_DIR,
        OCR_TSV_DIR,
        CANDIDATES_DIR,
        ENTRIES_RAW_DIR,
        ENTRIES_JUDGED_DIR,
        ENTRIES_VALIDATED_DIR,
        RDF_DIR,
        LOGS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
