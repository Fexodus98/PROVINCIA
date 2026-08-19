from __future__ import annotations

import json
from pathlib import Path

import fitz

from config import INPUT_PDF, OUTPUT_DIR, PAGE_LIMIT, PAGES_DIR, RENDER_DPI, ensure_output_dirs


def render_pdf(pdf_path: Path, dpi: int, page_limit: int = 0) -> list[dict]:
    ensure_output_dirs()
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    manifest: list[dict] = []

    max_pages = len(doc) if page_limit <= 0 else min(len(doc), page_limit)
    for idx in range(max_pages):
        page = doc.load_page(idx)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out_path = PAGES_DIR / f"page_{idx + 1:04d}.png"
        pix.save(out_path)
        manifest.append(
            {
                "page": idx + 1,
                "image_path": out_path.relative_to(OUTPUT_DIR).as_posix(),
                "width": pix.width,
                "height": pix.height,
                "dpi": dpi,
            }
        )
        print(f"[RENDER] page {idx + 1} -> {out_path.name}")

    manifest_path = PAGES_DIR / "pages_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[DONE] wrote {manifest_path}")
    return manifest


if __name__ == "__main__":
    render_pdf(INPUT_PDF, RENDER_DPI, PAGE_LIMIT)
