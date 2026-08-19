from __future__ import annotations

import json
import re
from pathlib import Path

from config import CANDIDATES_DIR, CONTEXT_WINDOW, FORMULA_PATTERNS, OCR_TXT_DIR, OUTPUT_DIR, ensure_output_dirs


def surrounding_context(text: str, start: int, end: int, width: int) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    return text[left:right].replace("\n", " ").strip()


def find_matches(text: str) -> list[dict]:
    hits: list[dict] = []
    for pattern in FORMULA_PATTERNS:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            hits.append(
                {
                    "pattern": pattern,
                    "match": m.group(0),
                    "context": surrounding_context(text, m.start(), m.end(), CONTEXT_WINDOW),
                    "start": m.start(),
                    "end": m.end(),
                }
            )
    return hits


def main() -> None:
    ensure_output_dirs()
    results: list[dict] = []
    for txt_path in sorted(OCR_TXT_DIR.glob("page_*.txt")):
        page_no = int(txt_path.stem.split("_")[1])
        text = txt_path.read_text(encoding="utf-8")
        hits = find_matches(text)
        if hits:
            page_record = {
                "page": page_no,
                "txt_path": txt_path.relative_to(OUTPUT_DIR).as_posix(),
                "image_path": (txt_path.parent.parent / "pages" / f"page_{page_no:04d}.png").relative_to(OUTPUT_DIR).as_posix(),
                "hits": hits,
            }
            results.append(page_record)
            print(f"[HIT] page {page_no}: {len(hits)} match(es)")

    out_json = CANDIDATES_DIR / "candidate_pages.json"
    out_jsonl = CANDIDATES_DIR / "candidate_pages.jsonl"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    with out_jsonl.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[DONE] wrote {out_json} and {out_jsonl}")


if __name__ == "__main__":
    main()
