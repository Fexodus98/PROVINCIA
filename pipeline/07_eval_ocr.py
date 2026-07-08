"""Evaluate Tesseract OCR output against a hand-corrected ground truth.

Ground truth files are named PIR_I_NNNN.txt and correspond to
ocr_txt/page_NNNN.txt. Reports CER and WER per page plus aggregates.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from config import OCR_TXT_DIR, OUTPUT_DIR

GROUND_TRUTH_DIR = Path(
    os.environ.get(
        "PROVINCIA_GROUND_TRUTH_DIR",
        Path(__file__).resolve().parent.parent / "ocr_ground_truth" / "ocr_ground_truth",
    )
)


def normalize(text: str) -> str:
    # Layout-independent comparison: collapse all whitespace runs.
    return re.sub(r"\s+", " ", text).strip()


def evaluate_page(gt_text: str, ocr_text: str) -> dict:
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


def main() -> None:
    if not GROUND_TRUTH_DIR.is_dir():
        raise SystemExit(f"Ground truth dir not found: {GROUND_TRUTH_DIR}")

    rows = []
    for gt_path in sorted(GROUND_TRUTH_DIR.glob("PIR_I_*.txt")):
        page_no = int(gt_path.stem.split("_")[-1])
        ocr_path = OCR_TXT_DIR / f"page_{page_no:04d}.txt"
        if not ocr_path.exists():
            print(f"[SKIP] page {page_no}: no OCR file {ocr_path.name}")
            continue
        gt_text = gt_path.read_text(encoding="utf-8")
        ocr_text = ocr_path.read_text(encoding="utf-8")
        m = evaluate_page(gt_text, ocr_text)
        m["page"] = page_no
        rows.append(m)
        print(f"page {page_no:4d}  CER {m['cer']*100:6.2f}%   WER {m['wer']*100:6.2f}%   ({m['gt_chars']} chars, {m['gt_words']} words)")

    if not rows:
        raise SystemExit("No overlapping pages between ground truth and OCR output.")

    total_chars = sum(r["gt_chars"] for r in rows)
    total_words = sum(r["gt_words"] for r in rows)
    total_char_edits = sum(r["char_edits"] for r in rows)
    total_word_edits = sum(r["word_edits"] for r in rows)
    summary = {
        "pages": len(rows),
        "micro_cer": total_char_edits / total_chars,
        "micro_wer": total_word_edits / total_words,
        "macro_cer": sum(r["cer"] for r in rows) / len(rows),
        "macro_wer": sum(r["wer"] for r in rows) / len(rows),
        "worst_pages_by_cer": [
            {"page": r["page"], "cer": round(r["cer"], 4)}
            for r in sorted(rows, key=lambda r: -r["cer"])[:5]
        ],
    }

    print()
    print(f"=== OCR evaluation over {summary['pages']} pages ===")
    print(f"micro CER: {summary['micro_cer']*100:.2f}%   micro WER: {summary['micro_wer']*100:.2f}%")
    print(f"macro CER: {summary['macro_cer']*100:.2f}%   macro WER: {summary['macro_wer']*100:.2f}%")
    print("worst pages:", ", ".join(f"{w['page']} ({w['cer']*100:.1f}%)" for w in summary["worst_pages_by_cer"]))

    report = {"summary": summary, "pages": rows}
    out_path = OUTPUT_DIR / "ocr_eval_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] wrote {out_path}")


if __name__ == "__main__":
    main()
