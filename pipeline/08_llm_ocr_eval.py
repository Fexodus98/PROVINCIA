"""Benchmark LLM-based OCR against the hand-corrected ground truth.

Transcribes the ground-truth pages with one or more Gemini models, then
reports CER/WER per model next to the Tesseract baseline. Transcriptions
are cached per model directory, so reruns only process missing pages.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from config import (
    OCR_TXT_DIR,
    OUTPUT_DIR,
    PAGES_DIR,
    ensure_output_dirs,
)
from llm_mistral import chat_with_image, get_client, ocr_image

GROUND_TRUTH_DIR = Path(
    os.environ.get(
        "PROVINCIA_GROUND_TRUTH_DIR",
        Path(__file__).resolve().parent.parent / "ocr_ground_truth" / "ocr_ground_truth",
    )
)

MODELS = [
    m.strip()
    for m in os.environ.get(
        "PROVINCIA_LLM_OCR_MODELS", "mistral-ocr-latest,mistral-medium-latest,mistral-large-latest"
    ).split(",")
    if m.strip()
]

# A PIR page is ~3000 chars (~2000 tokens of Latin); thinking tokens also
# count against the budget, so stay generous.
MAX_OUTPUT_TOKENS = int(os.environ.get("PROVINCIA_LLM_OCR_MAX_OUTPUT_TOKENS", "32768"))

TRANSCRIBE_PROMPT = """
Transcribe this page of the Prosopographia Imperii Romani (PIR, 1933 print) exactly as printed.

Rules:
- Output plain text only: no markdown, no code fences, no commentary, no translation.
- Follow the reading order of the page, including the running header line.
- Preserve original orthography: V for U in lemmata (AELIVS), ligatures resolved naturally.
- Preserve Greek passages in Greek letters.
- Preserve superscript edition and note numbers as Unicode superscripts (I², Syll.³, 2⁷).
- Preserve punctuation and brackets exactly: [ ] ( ) — ; spacing before semicolons as printed.
- Keep line breaks where the print has them; join hyphenated words ONLY if the hyphen is a line-break artifact, otherwise keep the hyphen.
- If a character is illegible, use ⟨?⟩.
""".strip()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def page_metrics(gt_text: str, ocr_text: str) -> dict:
    gt_n = normalize(gt_text)
    ocr_n = normalize(ocr_text)
    char_dist = Levenshtein.distance(gt_n, ocr_n)
    gt_words = gt_n.split(" ")
    ocr_words = ocr_n.split(" ")
    word_dist = Levenshtein.distance(gt_words, ocr_words)
    return {
        "gt_chars": len(gt_n),
        "gt_words": len(gt_words),
        "char_edits": char_dist,
        "word_edits": word_dist,
        "cer": char_dist / max(1, len(gt_n)),
        "wer": word_dist / max(1, len(gt_words)),
    }


def model_slug(model: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")


def transcribe(client, model: str, image_path: Path) -> str:
    if "ocr" in model:
        # Dedicated Mistral OCR API (returns markdown-ish plain text)
        return ocr_image(client, model, image_path)
    return chat_with_image(
        client,
        model=model,
        user_text=TRANSCRIBE_PROMPT,
        image_path=image_path,
        max_tokens=MAX_OUTPUT_TOKENS,
        json_mode=False,
    )


def aggregate(rows: list[dict]) -> dict:
    total_chars = sum(r["gt_chars"] for r in rows)
    total_words = sum(r["gt_words"] for r in rows)
    return {
        "pages": len(rows),
        "micro_cer": sum(r["char_edits"] for r in rows) / max(1, total_chars),
        "micro_wer": sum(r["word_edits"] for r in rows) / max(1, total_words),
    }


def main() -> None:
    if not GROUND_TRUTH_DIR.is_dir():
        raise SystemExit(f"Ground truth dir not found: {GROUND_TRUTH_DIR}")
    ensure_output_dirs()
    client = get_client()

    gt_pages: list[tuple[int, str]] = []
    for gt_path in sorted(GROUND_TRUTH_DIR.glob("PIR_I_*.txt")):
        page_no = int(gt_path.stem.split("_")[-1])
        gt_pages.append((page_no, gt_path.read_text(encoding="utf-8")))

    report: dict = {"models": {}}

    # Tesseract baseline from the existing OCR output
    tess_rows = []
    for page_no, gt_text in gt_pages:
        ocr_path = OCR_TXT_DIR / f"page_{page_no:04d}.txt"
        if ocr_path.exists():
            m = page_metrics(gt_text, ocr_path.read_text(encoding="utf-8"))
            m["page"] = page_no
            tess_rows.append(m)
    report["models"]["tesseract"] = {"summary": aggregate(tess_rows), "pages": tess_rows}

    for model in MODELS:
        out_dir = OUTPUT_DIR / f"ocr_llm_{model_slug(model)}"
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        failures = []
        for page_no, gt_text in gt_pages:
            image_path = PAGES_DIR / f"page_{page_no:04d}.png"
            if not image_path.exists():
                print(f"[SKIP] {model}: no image for page {page_no}")
                continue
            txt_path = out_dir / f"page_{page_no:04d}.txt"
            if txt_path.exists():
                text = txt_path.read_text(encoding="utf-8")
                print(f"[CACHED] {model} page {page_no}")
            else:
                print(f"[OCR] {model} page {page_no}")
                try:
                    text = transcribe(client, model, image_path)
                except Exception as exc:
                    print(f"[FAIL] {model} page {page_no}: {type(exc).__name__}: {exc}")
                    failures.append({"page": page_no, "error": str(exc)})
                    continue
                txt_path.write_text(text, encoding="utf-8")
            m = page_metrics(gt_text, text)
            m["page"] = page_no
            rows.append(m)
        report["models"][model] = {
            "summary": aggregate(rows),
            "pages": rows,
            "failures": failures,
        }

    print()
    print(f"=== LLM OCR benchmark over {len(gt_pages)} ground-truth pages ===")
    print(f"{'model':35s} {'pages':>5s} {'CER':>8s} {'WER':>8s}")
    for name, data in report["models"].items():
        s = data["summary"]
        print(f"{name:35s} {s['pages']:5d} {s['micro_cer']*100:7.2f}% {s['micro_wer']*100:7.2f}%")

    out_path = OUTPUT_DIR / "llm_ocr_benchmark.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] wrote {out_path}")


if __name__ == "__main__":
    main()
