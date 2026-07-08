# -*- coding: utf-8 -*-
"""Overlay-Schritt (zwischen Stufe 5 und Stufe 6):
Spielt die menschlichen Korrekturen aus entries_corrected_hutter/ in
entries_validated/provincia_entries.json ein.

Match je Eintrag zuerst über die PIR-Nummer, sonst über die entry_id:
  - relevance == "no"  -> Eintrag aus dem Korpus entfernen
  - sonst              -> Eintrag ersetzen (oder anhängen, falls neu / zuvor 'missed')

Danach '06_json_to_rdf.py' erneut laufen lassen. Stufe 5 NICHT erneut ausführen,
sonst wird provincia_entries.json überschrieben.
Ein Backup wird als provincia_entries.backup.json angelegt.
"""
import json, glob, re, shutil
from pathlib import Path

BASE = Path(r"C:\Users\hutterf\OneDrive\Desktop\Felix\Master\Masterarbeit\Wachter\hutter\PARS_I_A-B")
AGG = BASE/"entries_validated"/"provincia_entries.json"
CORR = BASE/"entries_corrected_hutter"

def norm_pir(x):
    if not x: return None
    m = re.search(r"([A-Z])\s*(\d{1,4})", str(x))
    return f"{m.group(1)} {int(m.group(2))}" if m else None

def find(entries, ce):
    pr = norm_pir(ce.get("pir_reference"))
    if pr:
        for i, e in enumerate(entries):
            if norm_pir(e.get("pir_reference")) == pr: return i
    eid = ce.get("entry_id")
    for i, e in enumerate(entries):
        if e.get("entry_id") == eid: return i
    return -1

def main():
    data = json.loads(AGG.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    before = len(entries)
    shutil.copyfile(AGG, AGG.with_suffix(".backup.json"))

    replaced = added = dropped = 0
    for f in sorted(glob.glob(str(CORR/"page_*.json"))):
        pg = int(re.search(r"page_(\d+)", f).group(1))
        doc = json.loads(Path(f).read_text(encoding="utf-8"))
        for ce in doc.get("entries", []):
            ce.setdefault("source_page", pg)
            i = find(entries, ce)
            if ce.get("relevance_to_provincia_corpus") == "no":
                if i >= 0:
                    entries.pop(i); dropped += 1
                    print(f"[DROP]    {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")
                continue
            if i >= 0:
                ce["source_page"] = entries[i].get("source_page", ce.get("source_page"))
                entries[i] = ce; replaced += 1
                print(f"[REPLACE] {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")
            else:
                entries.append(ce); added += 1
                print(f"[ADD]     {ce.get('pir_reference') or ce.get('entry_id')} (S.{pg})")

    data["entries"] = entries
    AGG.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{before} -> {len(entries)} Einträge  (ersetzt: {replaced}, hinzugefügt: {added}, entfernt: {dropped})")
    print("Backup: provincia_entries.backup.json")
    print("Nächster Schritt: 06_json_to_rdf.py erneut ausführen.")

if __name__ == "__main__":
    main()
