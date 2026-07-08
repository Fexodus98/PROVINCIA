from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from config import OCR_TSV_DIR, OCR_TXT_DIR, PAGES_DIR, TESSERACT_CMD, TESS_LANG, TESS_OEM, TESS_PSM, ensure_output_dirs


def list_page_images() -> list[Path]:
    return sorted(PAGES_DIR.glob("page_*.png"))


def tesseract_txt(image_path: Path) -> str:
    cmd = [
        TESSERACT_CMD,
        str(image_path),
        "stdout",
        "-l",
        TESS_LANG,
        "--oem",
        str(TESS_OEM),
        "--psm",
        str(TESS_PSM),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
    return result.stdout


def tesseract_tsv(image_path: Path) -> str:
    cmd = [
        TESSERACT_CMD,
        str(image_path),
        "stdout",
        "-l",
        TESS_LANG,
        "--oem",
        str(TESS_OEM),
        "--psm",
        str(TESS_PSM),
        "tsv",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8")
    return result.stdout


def count_nonempty_words(tsv_text: str) -> int:
    rows = list(csv.DictReader(tsv_text.splitlines(), delimiter="\t"))
    return sum(1 for row in rows if row.get("text", "").strip())


def main() -> None:
    ensure_output_dirs()
    manifest: list[dict] = []
    for image_path in list_page_images():
        page_no = int(image_path.stem.split("_")[1])
        print(f"[OCR] page {page_no}: {image_path.name}")
        txt = tesseract_txt(image_path)
        tsv = tesseract_tsv(image_path)

        txt_path = OCR_TXT_DIR / f"page_{page_no:04d}.txt"
        tsv_path = OCR_TSV_DIR / f"page_{page_no:04d}.tsv"
        txt_path.write_text(txt, encoding="utf-8")
        tsv_path.write_text(tsv, encoding="utf-8")

        manifest.append(
            {
                "page": page_no,
                "image_path": str(image_path),
                "txt_path": str(txt_path),
                "tsv_path": str(tsv_path),
                "text_length": len(txt),
                "word_boxes": count_nonempty_words(tsv),
            }
        )

    out_path = OCR_TXT_DIR.parent / "ocr_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] wrote {out_path}")


if __name__ == "__main__":
    main()
