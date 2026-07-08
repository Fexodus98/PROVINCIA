# -*- coding: utf-8 -*-
"""Schreibt die im Review beschlossenen Korrekturen der 5 HIGH-Fälle als
vollständige per-Seite-JSONs nach entries_corrected_hutter/.
Basis: entries_validated/ (Stand vor Korrektur); entry_id bleibt unverändert
(dient apply_corrections als Match-Schlüssel)."""
import json
from pathlib import Path

BASE = Path(r"C:\Users\hutterf\OneDrive\Desktop\Felix\Master\Masterarbeit\Wachter\hutter\PARS_I_A-B")
VAL = BASE/"entries_validated"; RAW = BASE/"entries_raw"; OUT = BASE/"entries_corrected_hutter"
OUT.mkdir(exist_ok=True)
TODAY = "2026-07-01"
TARGET_OFFICE = "legatus Augusti pro praetore provinciae"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def save(pg, doc):
    (OUT/f"page_{pg:04d}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"geschrieben: entries_corrected_hutter/page_{pg:04d}.json")
def review(note, verdict="human_corrected"):
    return {"verdict": verdict, "reviewed_by": "Hutter", "reviewed_on": TODAY, "note": note}
def add_notes(obj, key, items):
    obj[key] = obj.get(key, []) + items

# ---------- page 231 · A 1089: nicht relevant ----------
d = load(VAL/"page_0231.json"); e = d["entries"][0]
e["relevance_to_provincia_corpus"] = "no"
e["governorship_factoids"] = []                       # Faktoid gehört dem Vater A 1088
add_notes(e, "entry_notes", [
  "Statthalterschaft 'leg. Aug. pr. pr. Daciarum' gehört dem Vater A 1088 (dort belegt: Cappadocia + Tres Daciae); "
  "A 1089 selbst kein Statthalter -> nicht PROVINCIA-relevant."])
e["review"] = review("A 1089 nicht relevant; Dacia-Faktoid entfernt (gehört Vater A 1088).")
e["needs_review"] = False
save(231, d)

# ---------- page 77 · A 369 ----------
d = load(VAL/"page_0077.json"); e = d["entries"][0]
for g in e["governorship_factoids"]:
    if g.get("factoid_id") == "gov_A369_pannonia":
        g["certainty"] = "low"
        g["exact_text"] = "qui legatus Augusti pro praetore provinciam Pannoniam rexit"
        add_notes(g, "notes", ["Datierung a. 8/9 aus Kontext erschlossen; Text: 'Fortasse primus fuit'."])
# Hispania citerior aus RAW wieder aufnehmen (in Stufe 5 zu Unrecht verworfen)
raw = load(RAW/"page_0077.json")
for re_ in raw.get("entries", []):
    if str(re_.get("pir_reference", "")).endswith("369"):
        for g in re_.get("governorship_factoids", []):
            if "Hispania" in str(g.get("province_text", "")):
                g = dict(g)
                g["normalized_office"] = TARGET_OFFICE
                g["province_normalized"] = "Hispania citerior"
                g["certainty"] = "high"
                add_notes(g, "notes", ["In Stufe 5 fälschlich verworfen (Formel nicht wörtlich zusammenhängend); manuell wieder aufgenommen."])
                e["governorship_factoids"].append(g)
e["main_person"]["status_markers"] = [s for s in e["main_person"].get("status_markers", []) if s != "patricius"]
add_notes(e, "entry_notes", ["Prokonsulat Asiae (proconsul Asiae a. 21/22) ist kein leg. Aug. pr. pr. -> nicht als Statthalterschaft geführt."])
e["review"] = review("Asia (Prokonsulat) draußen; Hispania citerior wieder aufgenommen; Pannonia certainty=low + wörtliches Zitat; 'patricius' entfernt.")
e["needs_review"] = False
save(77, d)

# ---------- page 238 · Orphan -> A 1130 ----------
d = load(VAL/"page_0238.json"); e = d["entries"][0]
e["pir_reference"] = "A 1130"; e["main_person"]["pir_reference"] = "A 1130"
for g in e["governorship_factoids"]:
    g["province_normalized"] = "Hispania citerior"
    g["date_normalized_end"] = None
    add_notes(g, "notes", ["Enddatum ungewiss: 'incertum, num Hispaniae legationem usque ad finem vitae retinuerit'."])
add_notes(e, "entry_notes", ["PIR-Nummer A 1130 (L. Arruntius, cos. 6 n. Chr.) vom Eintragskopf S. 237 ergänzt (Orphan-Fortsetzung)."])
e["review"] = review("Orphan aufgelöst: PIR A 1130 zugewiesen; Enddatum null (in absentia, Ende ungewiss).")
e["needs_review"] = False
save(238, d)

# ---------- page 341 · Orphan -> A 1592 ----------
d = load(VAL/"page_0341.json"); e = d["entries"][0]
e["pir_reference"] = "A 1592"; e["main_person"]["pir_reference"] = "A 1592"
add_notes(e, "entry_notes", ["PIR-Nummer A 1592 (T. Aurelius Quietus, cos. suff. 82) vom Eintragskopf S. 340 ergänzt (Orphan-Fortsetzung)."])
e["review"] = review("Orphan aufgelöst: PIR A 1592 zugewiesen; Statthalterschaft Lycia et Pamphylia behalten.")
e["needs_review"] = False
save(341, d)

# ---------- page 347 · Orphan -> A 1623 ----------
d = load(VAL/"page_0347.json"); e = d["entries"][0]
e["pir_reference"] = "A 1623"; e["main_person"]["pir_reference"] = "A 1623"
e["main_person"]["displayed_name"] = "M. Aurelius Valentinianus"
e["main_person"]["normalized_name"] = "M. Aurelius Valentinianus"
for g in e["governorship_factoids"]:
    if g.get("factoid_id") == "gov_1": g["province_normalized"] = "Pannonia inferior"
    if g.get("factoid_id") == "gov_2": g["province_normalized"] = "Hispania citerior"
add_notes(e, "entry_notes", [
  "PIR-Nummer A 1623 (M. Aurelius Valentinianus) vom Eintragskopf S. 346 ergänzt.",
  "Reihenfolge der beiden Statthalterschaften unbestimmt ('Utri provinciae prius praefuerit, discerni nequit').",
  "Homonym-Warnung: 'Aurelius Valentinianus, vir perfectissimus, praeses Dalmatiae (a. 305)' ist eine EIGENE, "
  "ritterliche Person -- nicht PROVINCIA-relevant und nicht mit A 1623 zu verwechseln."])
e["review"] = review("Orphan aufgelöst: PIR A 1623, Name gesetzt; beide Statthalterschaften (Pannonia inf., Hispania cit.) behalten; Homonym (praeses Dalmatiae) abgegrenzt.")
e["needs_review"] = False
save(347, d)

print("\nFertig: 5 Korrektur-Dateien geschrieben (page_0313 bleibt unverändert).")
