# -*- coding: utf-8 -*-
"""Setzt die 28 MEDIUM- + 5 LOW-Beschlüsse (REVIEW_DECISIONS.md #1–#28, L1–L5) als
vollständige per-Seite-JSONs nach entries_corrected_hutter/ um.
Basis: aktuelle entries_validated/provincia_entries.json (Stand nach HIGH).
entry_id + pir_reference bleiben unverändert (Match-Schlüssel für apply_corrections).

Durchgängige Fixes: province_normalized aus der Registry setzen; Amt nicht als
status_marker; exact_text von Quellenangaben säubern; Datierungs-/ID-Notizen.
Hinweis: Stufe 6 verarbeitet KEINE relations/career_factoids — die betreffenden
Beschlüsse wirken nur im JSON, nicht im Graphen.
"""
import json, re, copy, sys
from pathlib import Path

BASE = Path(r"C:\Users\hutterf\OneDrive\Desktop\Felix\Master\Masterarbeit\Wachter\hutter\PARS_I_A-B")
PIPE = Path(r"C:\Users\hutterf\OneDrive\Desktop\Felix\Master\Masterarbeit\Wachter\hutter\provincia_pipeline")
AGG = json.loads((BASE/"entries_validated"/"provincia_entries.json").read_text(encoding="utf-8"))
OUT = BASE/"entries_corrected_hutter"; OUT.mkdir(exist_ok=True)
TODAY = "2026-07-06"
TARGET = "legatus Augusti pro praetore provinciae"

sys.path.insert(0, str(PIPE))
from config import CANONICAL_PROVINCE_SET   # noqa

def npir(x):
    if not x: return None
    s = re.sub(r"\bPIR\s*2?\b|\bPIR²\b", " ", str(x), flags=re.I)  # drop 'PIR'/'PIR2' prefix
    m = re.search(r"([A-Z])\s*(\d{1,4})", s)
    return f"{m.group(1)} {int(m.group(2))}" if m else None
IDX = {npir(e.get("pir_reference")): e for e in AGG["entries"]}

def get(pir):
    e = IDX.get(pir)
    if not e: raise SystemExit(f"NOT FOUND: {pir}")
    return copy.deepcopy(e)

def raw_factoid(page, pir, fid):
    d = json.loads((BASE/"entries_raw"/f"page_{page:04d}.json").read_text(encoding="utf-8"))
    for e in d.get("entries", []):
        if npir(e.get("pir_reference")) == pir:
            for g in e.get("governorship_factoids", []):
                if g.get("factoid_id") == fid:
                    return copy.deepcopy(g)
    raise SystemExit(f"RAW factoid not found: {pir}/{fid}")

def F(e, fid):
    for g in e.get("governorship_factoids", []):
        if g.get("factoid_id") == fid: return g
    raise SystemExit(f"factoid {fid} not in {e.get('pir_reference')}")

def setf(e, fid, **kw):
    g = F(e, fid)
    notes = kw.pop("addnotes", None)
    for k, v in kw.items(): g[k] = v
    if notes: g["notes"] = g.get("notes", []) + notes
    return g

def dropf(e, fid):
    e["governorship_factoids"] = [g for g in e["governorship_factoids"] if g.get("factoid_id") != fid]

def addf(e, g):
    e["governorship_factoids"].append(g)

def pnote(e, *notes):
    e["main_person"]["notes"] = e["main_person"].get("notes", []) + list(notes)

def enote(e, *notes):
    e["entry_notes"] = e.get("entry_notes", []) + list(notes)

def review(e, note):
    e["review"] = {"verdict": "human_corrected", "reviewed_by": "Hutter", "reviewed_on": TODAY, "note": note}
    e["needs_review"] = False

RESULT = {}   # page -> [entry,...]
def emit(e):
    pg = e.get("source_page")
    RESULT.setdefault(pg, []).append(e)

# ============================ MEDIUM ============================

# #1 A 184 (Hadrian) — Syria wieder aufnehmen; Pann.inf 106->107; patricius raus
e = get("A 184")
setf(e, "gov_1", province_normalized="Pannonia inferior", date_normalized_start=107,
     addnotes=["Beginn 107 erschlossen (vor dem Konsulat 108)."])
sy = raw_factoid(45, "A 184", "gov_2")
sy["normalized_office"] = TARGET; sy["province_normalized"] = "Syria"; sy["certainty"] = "high"
sy["evidence_type"] = "explicit"; sy["date_normalized_start"] = 117; sy["date_normalized_end"] = 117
sy["notes"] = ["'legatus Syriae certe a. 117'; bis zum Regierungsantritt (Aug. 117).",
               "In Stufe 5 fälschlich verworfen (Formel nicht zusammenhängend); manuell wieder aufgenommen."]
addf(e, sy)
e["main_person"]["status_markers"] = [s for s in e["main_person"]["status_markers"] if s != "patricius"]
review(e, "#1: Syria wieder aufgenommen (Stufe-5-Fehlausfall); Pann. inf. Beginn 107; 'patricius' entfernt; province_normalized gesetzt.")
emit(e)

# #2 A 260 — Thracia (erschlossen) aufnehmen; Amt-Status raus
e = get("A 260")
setf(e, "gov_1", province_normalized="Arabia")
th = {"factoid_id": "gov_2_thracia", "person_id": "P_Aelius_Severianus_Maximus_A260",
      "province_text": "Thracia", "province_normalized": "Thracia",
      "normalized_office": TARGET, "certainty": "low", "evidence_type": "inferred_from_context",
      "exact_text": "Severianum post consulatum legatum provinciae Thraciae fuisse viri docti e titulo 2 filio Perinthi dicato collegerunt (cf. Stein Thracia p. 39 sq.), dubito num iure",
      "date_text": "nach Arabia (nach 194); konsularisch", "date_normalized_start": None, "date_normalized_end": None,
      "notes": ["Von A. Stein erschlossen: Ehreninschrift Perinth (IGR I 794 = AEM VIII 217,43) fuer den Sohn A 261 "
                "nennt den Vater lamprotatos hypatikos (vir clarissimus consularis); da A 260 Statthalter von Arabia "
                "(193/194, praetorisch) und hier Konsular ist, verwaltete er Thracia (konsularisch) nach Arabia. "
                "Erschlossen, nicht direkt bezeugt."]}
addf(e, th)
e["main_person"]["status_markers"] = ["consularis"]
review(e, "#2: Thracia als erschlossen (low, Stein IGR I 794) aufgenommen; Arabia bleibt; Amt-Status entfernt; province_normalized gesetzt.")
emit(e)

# #3 A 338 — 4 govs behalten; Cappadocia start->null; Arabia end 150->149
e = get("A 338")
setf(e, "gov_A338_arabia", province_normalized="Arabia", date_normalized_end=149,
     addnotes=["Ende 149 ('ante a. 150', bis L. Attidius Cornelianus A 1341 uebernahm)."])
setf(e, "gov_A338_lugdunensis", province_normalized="Gallia Lugdunensis")
setf(e, "gov_A338_cappadocia", province_normalized="Cappadocia", date_normalized_start=None,
     addnotes=["Beginn unbestimmt (nur Terminus vor M. Sedatius Severianus, bis 161)."])
setf(e, "gov_A338_dacia", province_normalized="Tres Daciae")
review(e, "#3: 4 Statthalterschaften behalten; Cappadocia-Beginn null; Arabia-Ende 149; province_normalized gesetzt.")
emit(e)

# #4 A 346 — Gallia Lugdunensis; Name Frontinus vel Fronto
e = get("A 346")
setf(e, "gov_346_1", province_normalized="Gallia Lugdunensis")
mp = e["main_person"]
mp["normalized_name"] = "Lucius Aemilius Frontinus vel Fronto"
mp["name_variants"] = ["Lucius Aemilius Frontinus", "Lucius Aemilius Fronto"]
pnote(e, "Cognomen unsicher (Frontinus vel Fronto, Lakune); Tribus Quirina; Filiation unbekannt.")
review(e, "#4: Gallia Lugdunensis; normalized_name 'Frontinus vel Fronto' + name_variants; province_normalized gesetzt.")
emit(e)

# #5 A 382 — Numidia + Unsicherheitsnotiz
e = get("A 382")
setf(e, "gov_A382_1", province_normalized="Numidia",
     addnotes=["Beginn/Ende evtl. geringfuegig davor/danach."])
review(e, "#5: Numidia behalten + Unsicherheitsnotiz; province_normalized gesetzt.")
emit(e)

# #6 A 443 — Pannonia inferior; end 114->null
e = get("A 443")
setf(e, "gov_A443_1", province_normalized="Pannonia inferior", date_normalized_end=None,
     addnotes=["Nur 1. Sept. 114 (Militaerdiplom) bezeugt; Ende offen."])
pnote(e, "'consularis' erschlossen (Konsulat c. 115).")
review(e, "#6: Pannonia inferior; Ende null (nur Diplom 114); province_normalized gesetzt.")
emit(e)

# #7 A 470 — Germania superior wieder aufnehmen; Arabia end 204->null
e = get("A 470")
setf(e, "gov_A470_1", province_normalized="Arabia", date_normalized_end=None,
     addnotes=["Ende offen; aus XVvir-Amt 204 nur Terminus erschlossen."])
gs = raw_factoid(96, "A 470", "gov_A470_2")
gs["normalized_office"] = TARGET; gs["province_normalized"] = "Germania superior"; gs["certainty"] = "high"
gs["evidence_type"] = "explicit"; gs["date_normalized_start"] = 209; gs["date_normalized_end"] = 209
gs["notes"] = ["fortasse auch Vor-/Folgejahre.",
               "In Stufe 5 faelschlich verworfen (Formel nicht zusammenhaengend); manuell wieder aufgenommen."]
addf(e, gs)
review(e, "#7: Germania superior wieder aufgenommen (Stufe-5-Fehlausfall); Arabia-Ende null; province_normalized gesetzt.")
emit(e)

# #8 A 477 — nur Pontus et Bithynia
e = get("A 477")
setf(e, "gov_477_1", province_normalized="Pontus et Bithynia",
     date_text="ante legationem Ponti et Bithyniae ut videtur")
enote(e, "Prokonsulate Achaiae und Asiae sind keine leg. Aug. pr. pr. -> nicht als Statthalterschaft gefuehrt.",
      "'Asturia et Callaecia' = Sonderkommando/Distrikt der leg. VII Gemina, keine Provinz -> NICHT nach Hispania citerior normalisiert.")
review(e, "#8: nur Pontus et Bithynia; date_text angepasst; Achaia/Asia/Asturia-Callaecia ausgeschlossen; province_normalized gesetzt.")
emit(e)

# #9 A 519 — Arabia; date_text; Identitaet A 735
e = get("A 519")
setf(e, "gov_519_1", province_normalized="Arabia", date_text="a. 209 (?, umstritten)",
     addnotes=["'dubito num recte' — Datierung 209 umstritten (evtl. Syria statt Arabia).",
               "Moegliche Identitaet mit A 735 ([.....]us Antianus/Avitianus): PIR erwaegt bei A 735 Lesung 'Avitianus' (cf. n. 519). Entity-Resolution-Kandidat."])
review(e, "#9: Arabia; date_text '209 (?, umstritten)'; Identitaetsnotiz A 735; province_normalized gesetzt.")
emit(e)

# #10 A 534 — Galatia + Pannonia superior (sehr gering); Identitaet A 535; Amt-Status raus
e = get("A 534")
setf(e, "gov_534_1", province_normalized="Galatia",
     date_text="temp. Antoninus Pius, Commodus oder Caracalla (Antoninus Severi filius)")
ps = {"factoid_id": "gov_2_pann_sup", "person_id": "person_534",
      "province_text": "Pannonia superior", "province_normalized": "Pannonia superior",
      "normalized_office": TARGET, "certainty": "low", "evidence_type": "inferred_from_context",
      "exact_text": "videtur fuisse legatus Pannoniae superioris", "date_text": None,
      "date_normalized_start": None, "date_normalized_end": None,
      "notes": ["Statthalterschaft von Pannonia superior nicht explizit bezeugt; erschlossen allein daraus, dass Alfius "
                "als Senator im zentralen Verwaltungssitz Pannoniens geehrt wurde — CIL III 14356^4 (= EDH HD072856). "
                "Moeglicherweise Statthalter von Pannonia superior; sehr geringe Sicherheit.",
                "Personenidentitaet: moeglicherweise dieselbe Person wie A 535 (P. Alfius Maximus Numerius Licinianus). "
                "PIR wechselseitig: bei 534 'Fortasse non diversus ab eo qui sequitur', bei 535 'Potest idem esse is, qui praecedit'. sameAs-Kandidat."]}
addf(e, ps)
e["main_person"]["status_markers"] = ["senator"]
review(e, "#10: Galatia + Pannonia superior (low, erschlossen CIL III 14356^4); Identitaet A 535; Amt-Status -> senator; province_normalized gesetzt.")
emit(e)

# #11 A 544 — Arabia; Datierung gehoert dem Konsulat, nicht der Statthalterschaft
e = get("A 544")
setf(e, "gov_A_544_1", province_normalized="Arabia", date_normalized_start=None, date_normalized_end=None,
     date_text="vor dem Konsulat; auf dem Gerasa-Titel consul designatus",
     addnotes=["In der PIR 'consul (suffectus anno incerto saec. II medii)' — die Klammer markiert Erschlossenes "
               "(belegt nur 'consul'); diese Datierung gilt dem KONSULAT, nicht der Statthalterschaft. "
               "Arabia-Statthalterschaft (CIL III 118 = 14156^3, Gerasa) faellt kurz vor das Konsulat (dort consul designatus). "
               "Moegliche Identitaet mit C. Allius C. f. Fuscianus (Ostia a. 140, a. 152)."])
review(e, "#11: Arabia; Datierung (saec. II medii) gilt dem Konsulat, nicht der Statthalterschaft -> Daten null; province_normalized gesetzt.")
emit(e)

# #12 A 643 — Dacia; vir clarissimus raus
e = get("A 643")
setf(e, "gov_643_1", province_normalized="Dacia",
     addnotes=["'ante imperatorem Marcum' = vor 161; Ende ~161 (praetorischer Legat)."])
e["main_person"]["status_markers"] = ["senator"]
review(e, "#12: Dacia behalten; 'vir clarissimus' entfernt (nicht belegt); province_normalized gesetzt.")
emit(e)

# #13 A 659 — Moesia inferior; Beziehung A 660 Sohn ODER Enkel
e = get("A 659")
setf(e, "gov_A659_1", province_normalized="Moesia inferior")
pnote(e, "Beziehung zu A 660 (L. Annius Italicus Rutilianus): Verwandtschaft gesichert, Grad unsicher — Sohn ODER Enkel. "
         "PIR: A 660 'Italici filius … cf. n. 659'; offen, ob der Vater A 659 selbst ('hic') oder dessen gleichnamiger "
         "Sohn Italicus ist ('Incertum utrum hic an filius Italicus, qui L. Annio Italico Rutiliano filio posuit "
         "t. sepulcralem XI 5808 Iguvinum'). Sohn (falls A 659 = Italicus) oder Enkel (falls ueber den Sohn Italicus). "
         "Enkel-Deutung: Danuta Okon, Res Historica 59 (2025). Beleg CIL XI 5808.")
review(e, "#13: Moesia inferior behalten; Beziehung A 660 = Sohn oder Enkel (beide Moeglichkeiten, CIL XI 5808); province_normalized gesetzt.")
emit(e)

# #14 A 735 — Pannonia inferior; non ante Commodum; Name; A 519
e = get("A 735")
setf(e, "gov_735_1", province_normalized="Pannonia inferior",
     date_normalized_start=180, date_normalized_end=None,
     date_text="non ante Commodum (nach 180); Kaisername im Titel unvollstaendig, fruehestens Commodus; Ritterling erwog Elagabal",
     addnotes=["Fortsetzung S.153: 'Titulus non ante Commodum positus est' (CIL III 3637) -> Kaiser 'Imp. Caesar "
               "M. Aureli[us…] p. f. Aug.' fruehestens Commodus (ab 180); Ritterling erwog sogar Elagabal (218/222)."])
mp = e["main_person"]; mp["normalized_name"] = "[.....]us Antianus"
pnote(e, "Nomen verloren; PIR erwaegt Lesung 'Avitianus' statt 'Antianus' (cf. n. 519) -> moeglicherweise = "
         "L. Alfenus Avitianus (A 519). Entity-Resolution-Kandidat.")
review(e, "#14: Pannonia inferior; Datierung 'non ante Commodum' (start 180, statt Judge 161-180); moegl. = A 519; province_normalized gesetzt.")
emit(e)

# #15 A 754 — 3 Provinzen; Datierungen; +patricius
e = get("A 754")
setf(e, "gov_754_1", province_normalized="Arabia", date_normalized_start=165, date_normalized_end=167,
     date_text="c. 165-167; als cos. designatus noch 'legatus etiamtum Arabiae', consul suff. 166/167")
setf(e, "gov_2", province_normalized="Germania inferior", date_normalized_start=169, date_normalized_end=None,
     date_text="nach der expeditio Germanica (a. c. 169); c. 170-174")
setf(e, "gov_3", province_normalized="Britannia", date_text="c. 175/178 (letzte Statthalterschaft; Sohn 178 inter salios Palatinos)",
     addnotes=["Provinzname erschlossen ('Legatus Aug. pr. pr. (Britanniae)'), durch CIL VII 440 gestuetzt."])
mp = e["main_person"]
if "patricius" not in mp["status_markers"]: mp["status_markers"] = mp["status_markers"] + ["patricius"]
pnote(e, "'patricius' erschlossen: 'Antistios a Marco imperatore inter gentes patricias adlectos'.")
review(e, "#15: Arabia/Germania inf./Britannia (province_normalized gesetzt); Datierungen praezisiert; 'patricius' ergaenzt.")
emit(e)

# #16 A 816 — Cilicia; exact 'sine dubio'; vir clarissimus behalten
e = get("A 816")
setf(e, "gov_A816_cilicia", province_normalized="Cilicia",
     exact_text="sine dubio legatus Aug. pr. pr. provinciae Ciliciae",
     addnotes=["Datierung = Zeitfenster der Inschrift IGR 3,838 (unter Sept. Severus, 198-209); genaue Amtsdauer nicht bestimmbar."])
pnote(e, "'vir clarissimus' belegt: Eintrag nennt A 816 'lamprotatos strategos' (= vir clarissimus) + Inschrift 'la[mp]rotato[u]'.")
review(e, "#16: Cilicia; exact 'sine dubio'; 'vir clarissimus' behalten (lamprotatos); province_normalized gesetzt.")
emit(e)

# #17 A 883 — Thracia; end 140->null; Amt-Status raus; lemma
e = get("A 883")
setf(e, "gov_883_1", province_normalized="Thracia", date_normalized_end=None,
     exact_text="Legatus Augusti pr. pr. Thraciae imperante Antonino Pio (nummi anno 140; non ante a. 140)",
     addnotes=["Muenzen 'non ante a. 140' (nach Tod der Faustina d.Ae.); Statthalterschaft um 140, vor dem Konsulat 148; genaues Ende unbestimmt."])
e["lemma"] = "M. Antonius Zeno"
e["main_person"]["status_markers"] = [s for s in e["main_person"]["status_markers"] if s != "legatus Augusti pro praetore"]
review(e, "#17: Thracia; Ende null ('non ante a.140'); exact praezisiert; Amt-Status entfernt; province_normalized gesetzt.")
emit(e)

# #18 A 1088 — Cappadocia/Tres Daciae Datierungen
e = get("A 1088")
setf(e, "gov_1", province_normalized="Cappadocia", date_normalized_start=174, date_normalized_end=177,
     date_text="t.11 'ante a. 175 vel eo ipso anno' (Germanicus nondum Sarmaticus), t.9 'post 27. Nov. 176' -> c. 174-177")
setf(e, "gov_2", province_normalized="Tres Daciae", date_normalized_start=177, date_normalized_end=None,
     date_text="post Cappadociam (nach c. 177); vor Prokonsulat Asiae c. 184/185")
review(e, "#18: Cappadocia c.174-177 (Judge-Ende 175 widerlegt via t.9 post Nov 176); Tres Daciae ab 177; province_normalized gesetzt.")
emit(e)

# #19 A 1180 — Moesia inferior; sameAs PIR V 907
e = get("A 1180")
setf(e, "gov_1180_1", province_normalized="Moesia inferior",
     addnotes=["Nur fuer a. 120 bezeugt (Punktbeleg CIL III 7539 = IGR I 606, Tomi); genaue Amtsdauer unbekannt."])
pnote(e, "Wahrscheinlich identisch mit G. Ummidius Quadratus Sallustius Sertorius (PIR2 V 907) — dieselbe Inschrift "
         "CIL III 7539 belegt beide; Namensrest wohl 'Se]rtorius', nicht 'A]rtorius'. sameAs-Kandidat.",
         "consularis aus dem Amt erschlossen (Moesia inferior = konsularische Provinz).")
review(e, "#19: Moesia inferior; sameAs PIR V 907 (CIL III 7539); province_normalized gesetzt.")
emit(e)

# #20 A 1322 — 4 Provinzen; Syria maior -> Syria Coele (Vorbehalt); Datierungen; Status
e = get("A 1322")
setf(e, "gov_1322_1", province_normalized="Thracia", date_normalized_start=211, date_normalized_end=217,
     date_text="regnante (Severo) Antonino = Caracalla (211-217; Mitregent ab 198)")
FULL = "Legatus Aug. pr. pr. provinciarum Cappadociae, Syriae maioris, Hispaniae citerioris t. 1."
setf(e, "gov_1", province_normalized="Cappadocia", date_normalized_start=None, date_normalized_end=None,
     exact_text=FULL, date_text="konsularisch, nach Konsulat ~217, vor Hispania citerior; einzeln nicht datiert",
     addnotes=["Teil des Tarraco-Cursus (CIL II 4111 = ILS 1176)."])
setf(e, "gov_2", province_normalized="Syria Coele", date_normalized_start=None, date_normalized_end=None,
     exact_text=FULL, date_text="konsularisch, zwischen Cappadocia und Hispania citerior; einzeln nicht datiert",
     addnotes=["Im Text 'Syriae maioris'; keine Standard-Provinz; hier als Syria Coele (groesserer Nordteil nach "
               "Severus' Teilung 194) gedeutet — Gleichsetzung unsicher (Vorbehalt)."])
setf(e, "gov_3", province_normalized="Hispania citerior", exact_text=FULL + " Hispaniam rexit sub Severo Alexandro ib.")
e["main_person"]["status_markers"] = ["senator", "vir clarissimus", "consularis"]
e["lemma"] = "Q. ATRIVS CLONIVS."
e["main_person"]["normalized_name"] = "Q. Atrius Clonius"
review(e, "#20: Thracia (211-217, Caracalla)/Cappadocia/Syria Coele (Vorbehalt fuer 'Syria maior')/Hispania citerior; Status bereinigt; province_normalized gesetzt.")
emit(e)

# #21 A 1341 — Arabia wieder aufnehmen; Syria bleibt
e = get("A 1341")
setf(e, "gov_A1341_syria", province_normalized="Syria", exact_text="Legatus Aug. pr. pr. Syriae",
     addnotes=["anno 157 (t.6), a. 162 (t.5), a Parthis fugatus (a. 161/162).",
               "Moeglicherweise = anonymer praeses Syriae (vita Pert. 1, 6) — ER-Kandidat."])
ar = raw_factoid(287, "A 1341", "gov_A1341_arabia")
ar["normalized_office"] = TARGET; ar["province_normalized"] = "Arabia"; ar["certainty"] = "high"
ar["evidence_type"] = "explicit"; ar["date_normalized_start"] = 150; ar["date_normalized_end"] = 151
ar["date_text"] = "anno 213 aerae Pompeianae = a.p.C. 150; beim Konsulat 151 noch 'etiamtum legatus Arabiae'"
ar["notes"] = ["In Stufe 5 faelschlich verworfen ('Legatus Aug. pro pr. (Arabiae)' — abgekuerzt/Klammer); manuell wieder aufgenommen."]
addf(e, ar)
review(e, "#21: Arabia wieder aufgenommen (Stufe-5-Fehlausfall); Syria exact gekuerzt; province_normalized gesetzt.")
emit(e)

# #22 A 1383 — Thracia; Amt-Status raus
e = get("A 1383")
setf(e, "factoid_1383_gov_1", province_normalized="Thracia",
     exact_text="Legatus Aug. pr. pr. provinciae Thraciae sub Severo Alexandro t. 4.",
     addnotes=["= Regierungszeit Severus Alexander (222-235), Naeherung."])
e["main_person"]["status_markers"] = ["senator"]
enote(e, "Lycia et Pamphylia war seit Marcus Aurelius wieder senatorische Provinz; der dort bezeugte Posten ist ein "
         "legatus proconsulis (dem Prokonsul unterstellt), kein legatus Augusti pro praetore — daher kein Ziel-Faktoid.")
review(e, "#22: Thracia; Amt-Status entfernt; Notiz Lycia-et-Pamphylia (senatorisch, kein Ziel-Amt); province_normalized gesetzt.")
emit(e)

# #23 A 1402 — Syria; start 165->166; Status  (exact_text bleibt PIR-woertlich)
e = get("A 1402")
setf(e, "gov_1402_1", province_normalized="Syria", date_normalized_start=166,
     addnotes=["Vorgaenger Cn. Iulius Verus bis ~165; Statthalterschaft belegt bis 171/2; danach "
       "ausserordentliches Ostkommando bis zum Aufstand 175; kein Arabia-Kommando (Ritterling irrt: 'Haud recte … Arabiae praefuisse')."])
e["main_person"]["status_markers"] = ["consularis", "vir clarissimus"]
e["lemma"] = "C. AVIDIVS CASSIVS"
review(e, "#23: Syria (start 166); Status -> consularis + vir clarissimus; lemma-Fix; province_normalized gesetzt.")
emit(e)

# #24 A 1408 — Dacia-Dublette loeschen; Moesia superior; Achaia
e = get("A 1408")
dropf(e, "gov_1408_dacia")
setf(e, "gov_1", province_normalized="Moesia superior", certainty="medium",
     date_normalized_start=116, date_normalized_end=118,
     date_text="bis 117/118 ('ab Hadriano e provincia avocatum', dann hingerichtet); Beginn ungewiss (~116)",
     addnotes=["Domaszewski (CIL III 7904): Statthalter jener Provinz, zu deren Heer die legio IV Flavia Felix "
               "gehoerte = Moesia superior. Dedikant M. Calventius Viator war Centurio der legio IV Flavia Felix; "
               "Fundort Sarmizegetusa/Dacia allein nicht entscheidend (equites singulares konnten einen Ausbilder aus "
               "dem Heer einer Nachbarprovinz haben). Daher wahrscheinlicher Moesia superior; Dacia nicht sicher "
               "auszuschliessen ('potius quam Daciae'). Viator spaeter unter den equites singulares Hadriani in Gerasa (129/130 oder 131/132).",
               "Dublette-Faktoid 'Dacia' (gleicher Beleg CIL III 7904) entfernt."])
setf(e, "gov_1408_achaia", province_normalized="Achaia", date_normalized_start=114, date_normalized_end=117,
     date_text="legatus Aug. pr. pr. extra ordinem (Delphi-Grenzstreit), sub finem imperii Traiani, c. 114-117")
review(e, "#24: Dacia-Dublette geloescht; Moesia superior (medium, Domaszewski); Achaia c.114-117; province_normalized gesetzt.")
emit(e)

# #25 A 1410 — Britannia; Thracia-Irrtum
e = get("A 1410")
setf(e, "gov_1", province_normalized="Britannia",
     addnotes=["certainty medium: Identifikation beruht auf editorisch ergaenztem Cognomen im Militaerdiplom ('cognomen Quieti suppleverunt')."])
enote(e, "Fruehere Forschung hielt ihn irrtuemlich fuer Statthalter von Thracia; in Wahrheit legatus legionis VIII "
         "Augustae ('errore statuerunt priores'). Prokonsulat Achaia ist senatorisch, kein Ziel-Amt.")
review(e, "#25: Britannia (medium); Thracia-Irrtum notiert; province_normalized gesetzt.")
emit(e)

# #26 A 1570 — Arabia unter Vorbehalt
e = get("A 1570")
setf(e, "gov_1570_1", province_normalized="Arabia",
     addnotes=["Arabia seit 106 n. Chr. kaiserliche Provinz. Fuer Aur. Petrus (278/279, hegemon/praeses Arabiae) "
               "bleibt unsicher, ob legatus Augusti pro praetore oder ritterlicher praeses; die Inschrift nennt ihn "
               "diasemotatos (= perfectissimus, ritterlich). Unter Vorbehalt aufgenommen — koennte leg. Aug. pr. pr. gewesen sein."])
pnote(e, "'vir perfectissimus' (diasemotatos) belegt -> Hinweis auf moeglichen Ritterrang, nicht gesicherter senatorischer Status.")
review(e, "#26: Arabia unter Vorbehalt (Amt unsicher: leg. Aug. pr. pr. oder ritterl. praeses); province_normalized gesetzt.")
emit(e)

# #27 B 14 — Pannonia inferior; vir clarissimus raus
e = get("B 14")
setf(e, "factoid-gov-b-14-pannonia-inf", province_normalized="Pannonia inferior",
     addnotes=["Nur fuer a. 199 bezeugt (Meilensteine); Amtsdauer nicht naeher bestimmt."])
e["main_person"]["status_markers"] = ["senator"]
e["main_person"]["normalized_name"] = "L. Baebius Caecilianus"
review(e, "#27: Pannonia inferior; 'vir clarissimus' entfernt (redundant/nicht belegt); province_normalized gesetzt.")
emit(e)

# #28 B 164 — Galatia; patricius raus
e = get("B 164")
setf(e, "gov-1", province_normalized="Galatia",
     exact_text="— Legatus Aug. pr. pr. (Galatiae) sub Hadriano t. 1.",
     addnotes=["sub Hadriano (117-138); vor dem ersten Konsulat -> eher fruehe Hadrianszeit; genauer nicht bestimmbar."])
e["main_person"]["status_markers"] = ["consularis"]
enote(e, "Nur Galatia; die Mehr-Provinzen-Karriere (Mactar-Inschrift) ist post-1950 und nicht in PIR2.")
review(e, "#28: Galatia; 'patricius' entfernt (nicht belegt); province_normalized gesetzt.")
emit(e)

# ============================ LOW ============================

# L1 A 235 — Lycia et Pamphylia
e = get("A 235")
setf(e, "gov_235_1", province_normalized="Lycia et Pamphylia",
     addnotes=["a. 152 ut videtur (Opramoas-Monument IGR 3, 739); Amtsdauer nicht bestimmbar.",
               "Provinz-Status: unter Antoninus Pius kaiserlich (Lycia et Pamphylia erst seit Marcus Aurelius wieder senatorisch).",
               "Namensergaenzung durch Heberdey unsicher ('num recte nomina suppleverit … incertum')."])
review(e, "L1: Lycia et Pamphylia (province_normalized gesetzt); Unsicherheitsnotizen.")
emit(e)

# L2 A 236 — Cappadocia; cert -> low
e = get("A 236")
setf(e, "gov_236_1", province_normalized="Cappadocia", certainty="low",
     addnotes=["Amt 'fortasse' (verstuemmelte Inschrift IGR 3, 106 aus Comana); aus gemeinsamer Regierung Marcus + Verus erschlossen (161-169)."])
review(e, "L2: Cappadocia; certainty medium->low ('fortasse'); province_normalized gesetzt.")
emit(e)

# L3 A 271 — Pannonia inferior; Amt-Status raus
e = get("A 271")
setf(e, "gov_271_1", province_normalized="Pannonia inferior",
     addnotes=["Regierung Macrinus (Apr 217 - Jun 218); Diadumenianus Augustus ab Mai 218 ('Augustorum')."])
e["main_person"]["status_markers"] = ["senator"]
review(e, "L3: Pannonia inferior; Amt-Status entfernt; province_normalized gesetzt.")
emit(e)

# L4 A 1421 — Germania superior; Amt-Status -> senator
e = get("A 1421")
setf(e, "gov_1421_1", province_normalized="Germania superior",
     addnotes=["a. 213 ut videtur, Punktbeleg Mainz CIL XIII 6762; Provinz durch Fundort Mainz gestuetzt."])
e["main_person"]["status_markers"] = ["senator"]
review(e, "L4: Germania superior; Amt-Status -> senator; province_normalized gesetzt.")
emit(e)

# L5 B 59 — Galatia; cert -> low; Identitaet T. Helvius Basila
e = get("B 59")
setf(e, "gov_59_galatia", province_normalized="Galatia", certainty="low",
     addnotes=["imperante Tiberio (14-37), ut videtur.",
               "probabiliter idem atque T. Helvius Basila (cf. Rostowzew Mel. Boissier 422). sameAs-Kandidat."])
e["main_person"]["status_markers"] = ["senator"]
review(e, "L5: Galatia; certainty medium->low ('ut videtur'); Amt-Status -> senator; Identitaet T. Helvius Basila; province_normalized gesetzt.")
emit(e)

# ============================ WRITE + VALIDATE ============================
bad = []
for pg, entries in RESULT.items():
    for e in entries:
        for g in e.get("governorship_factoids", []):
            pn = g.get("province_normalized")
            if pn is not None and pn.lower() not in CANONICAL_PROVINCE_SET:
                bad.append((e.get("pir_reference"), g.get("factoid_id"), pn))
if bad:
    print("!!! province_normalized NICHT in Registry:")
    for b in bad: print("   ", b)
    raise SystemExit("Abbruch: ungueltige Provinznamen.")

for pg, entries in sorted(RESULT.items()):
    doc = {"source_page": pg, "entries": entries}
    (OUT/f"page_{pg:04d}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

npages = len(RESULT); nentries = sum(len(v) for v in RESULT.values())
print(f"OK: {nentries} Eintraege in {npages} Korrektur-Dateien geschrieben (alle province_normalized in Registry).")
print("Seiten:", ", ".join(str(p) for p in sorted(RESULT)))
