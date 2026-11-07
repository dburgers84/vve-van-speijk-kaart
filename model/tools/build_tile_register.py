#!/usr/bin/env python3
"""Werkregister per tile (1800x1800 native px) voor alle vijf tekenbladen.

- Automatisch (lokaal, uit scan): inktfractie per tile; kolomkandidaten uit data/inventory/columns_auto_all.json.
- Handmatig: REVIEW-notities hieronder (visueel gelezen op 0,56x-tiles of pagina-overzicht 1/7x).
Status per tile: empty_auto | auto_only | overview_reviewed | survey_reviewed | traced_partial
Per objectsoort: present | not_observed | unknown (niet bekeken) en traced | to_trace.
Geen objectaantallen tenzij geteld; kolomkandidaten zijn detector-aantallen, geen geverifieerde telling.
Zonder scan: python3 model/tools/build_tile_register.py --scans none  (hergebruikt opgeslagen inktwaarden)
"""
import argparse, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "inventory", "tile_register.json")
PAGES = {81: "BG", 82: "1e", 83: "2e", 84: "3e", 85: "4e en daken"}
T = 1800
TYPES = ["commercial", "dwelling", "storage", "common_core", "roof", "path_gallery", "wall", "column", "stair", "lift", "label", "index_number", "hatch_not_in_split"]

P = "present"
REVIEW = {  # (page, row, col): (status, {type: present/not_observed}, notes, traced_regions)
    (81, 0, 0): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, hatch_not_in_split=P),
                 "Legenda 'niet in de splitsing betrokken' (arcering); schaalbalk 0–10 m 'Schaal 1 a 200'; cm-liniaal 0–5 cm; label 'expeditie'; begin gearceerde bedrijfsruimte.", []),
    (81, 0, 1): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, index_number=P),
                 "3x 'bedrijfs-ruimte'; grote 179; gevel met kolommen; tekst 'KPN, (EV)' aan rand.", []),
    (81, 0, 2): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, common_core=P),
                 "3x 'bedrijfs-ruimte'; straat 'HET DIEP'; 'flatkast' + 'GEM.' aan gevel; kolommen.", []),
    (81, 0, 3): ("traced_partial", dict(commercial=P, wall=P, column=P, label=P, index_number=P, common_core=P, stair=P, lift=P),
                 "Straat 'DE KIEL'; 2x 179; 6+ 'bedrijfs-ruimte'; kern container/trap/lift/entree/180/flatkast; 'water, KPN, UPC'; gestippelde contour buiten gevel (betekenis onbekend).", ["reg_bg_kiel"]),
    (81, 1, 0): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, index_number=P, common_core=P, stair=P, lift=P, hatch_not_in_split=P),
                 "Gearceerde bedrijfsruimte (niet in splitsing); kern entree/trap/hal/lift/containerruimte/180; 'flatkast', 'KPN & UPC'; 4x 'bedrijfs-ruimte'; straat 'DE BINNENLOOP'.", []),
    (81, 1, 1): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, common_core=P),
                 "'bedrijfs-ruimte' x5; 'HET HAVENPLEIN'; kernfragment 'CVZ kast', 'GEM.', 'flatkast', 'UPC, water'; gestippeld element met 2 kolommen.", []),
    (81, 1, 2): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, index_number=P, common_core=P, stair=P, lift=P),
                 "Kern linksboven entree/trap/lift/180; kleine kern containerruimte/180/LS-ruimte/trafo ruimte/trap; 179; kolomraster.", []),
    (81, 1, 3): ("survey_reviewed", {t: "not_observed" for t in TYPES}, "Lege marge + vouw; alleen kaderlijn.", []),
    (81, 2, 0): ("traced_partial", dict(commercial=P, wall=P, column=P, label=P, index_number=P, common_core=P, stair=P, lift=P),
                 "Pilotkern Schans-zijde getraceerd (reg_bg_core); grote bedrijfsruimte erboven nog niet; 'DE SCHANS'.", ["reg_bg_core"]),
    (81, 2, 1): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, path_gallery=P),
                 "6+ 'bedrijfs-ruimte'; passage 'DE RELING' met gestippelde lijnen (overkapping?); kolommen in gevels.", []),
    (81, 2, 2): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, stair=P),
                 "'expeditie gang'; buitentrap met getekende treden (streepjes) bij expeditie; 'HET DIEP'; kolommen.", []),
    (81, 3, 0): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, common_core=P, stair=P),
                 "'GEM.', 'trafo ruimte', 'LS-ruimte', 'expeditie', 'E-kast', 'hydrofoor', trap met kruisvak; 2x 'bedrijfs-ruimte'; kolomraster.", []),
    (81, 3, 1): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P, hatch_not_in_split=P),
                 "5+ 'bedrijfs-ruimte'; 2 gearceerde bedrijfsruimten (niet in splitsing); 'expeditie'; 'RELING'.", []),
    (81, 4, 0): ("survey_reviewed", dict(commercial=P, wall=P, column=P, label=P),
                 "Planonderkant 'DE KAJUIT', rond element op hoek (betekenis onbekend); titelblok begint (A-2, legenda 'Gemeenschappelijk [X] kanalen', notarisgegevens: niet overnemen).", []),
}
PAGE_NOTES = {
    82: "Pagina-overzicht (1/7x) bekeken: woningen met indexnummers (o.a. 181–215, 226–229, 238–240, 248–251 zichtbaar), bergingblokken (vele kleine genummerde vakjes), 179-zones (installatie/bedrijfsdak), gearceerd 'niet in de splitsing', kolommen, galerijen/paden, 'Bouwnr.'-teksten. Niet per tile gereviewd.",
    83: "Pagina-overzicht: woningen (o.a. 183–184, 194–197, 200–201, 206–207, 216–225, 230–237, 241–245, 252–255), dakvlakken met 179 + 'indicatieve installatiezone', gearceerd deel. Niet per tile gereviewd.",
    84: "Pagina-overzicht: woningen (o.a. 216–225, 230–237, 246–247, 256–259), dakvlakken/installatiezones, 179. Niet per tile gereviewd.",
    85: "Pagina-overzicht (4e + daken): woningen 256–259, dakvlakken met 'indicatieve installatiezone', 179, tweede schaalbalk 'Daken 1:200'. Niet per tile gereviewd.",
}


def main(scans):
    cols = json.load(open(os.path.join(ROOT, "data", "inventory", "columns_auto_all.json")))["pages"]
    old = {t["tile"]: t for t in json.load(open(OUT))["tiles"]} if os.path.exists(OUT) else {}
    tiles = []
    for page, floor in PAGES.items():
        A = None
        if scans != "none":
            import numpy as np
            from PIL import Image
            Image.MAX_IMAGE_PIXELS = None
            A = np.array(Image.open(os.path.join(scans, f"page-{page}.png")).convert("L")) < 128
            H, W = A.shape
        else:
            W, H = {81: (7118, 10099), 82: (7122, 10049), 83: (7120, 10055), 84: (7121, 10045), 85: (7084, 10039)}[page]
        for r, ty in enumerate(range(0, H, T)):
            for c, tx in enumerate(range(0, W, T)):
                box = [tx, ty, min(tx + T, W), min(ty + T, H)]
                tid = f"p{page}_r{r}c{c}"
                ink = round(float(A[box[1]:box[3], box[0]:box[2]].mean()), 4) if A is not None else old.get(tid, {}).get("ink_fraction")
                ncol = sum(1 for k in cols.get(str(page), []) if box[0] <= k["x"] < box[2] and box[1] <= k["y"] < box[3])
                rv = REVIEW.get((page, r, c))
                if rv:
                    status, present, notes, traced = rv
                    types = {t: present.get(t, "not_observed") for t in TYPES} if status != "auto_only" else {t: "unknown" for t in TYPES}
                elif ink is not None and ink < 0.003:
                    status, types, notes, traced = "empty_auto", {t: "unknown" for t in TYPES}, "Inktfractie <0,3%: waarschijnlijk leeg/marge (niet visueel bevestigd).", []
                else:
                    status = "overview_reviewed" if page != 81 else "auto_only"
                    types = {t: "unknown" for t in TYPES}
                    notes = PAGE_NOTES.get(page, "Niet visueel per tile bekeken (o.a. titelblok/situatie-inzet 1:1000 onderaan blad).")
                    traced = []
                work = {t: ("traced_partial" if traced and types.get(t) == P else ("to_trace" if types.get(t) in (P, "unknown") else "n/a")) for t in TYPES}
                tiles.append({"tile": tid, "page": page, "floor": floor, "box_px": box, "ink_fraction": ink,
                              "column_candidates_auto": ncol, "status": status, "types": types, "work": work,
                              "traced_regions": traced, "notes": notes})
    summary = {}
    for t in tiles:
        s = summary.setdefault(t["floor"], {})
        s[t["status"]] = s.get(t["status"], 0) + 1
    out = {"tile_size_px": T, "generated_by": "model/tools/build_tile_register.py", "summary_status_per_floor": summary,
           "column_candidates_auto_per_page": {p: len(v) for p, v in cols.items()},
           "caveat": "Kolomkandidaten = detector (holle vierkanten ≥12 px), niet individueel gecontroleerd; bevat fout-positieven (letters/symbolen) en mist vage/rechthoekige kolommen.",
           "tiles": tiles}
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False), out["column_candidates_auto_per_page"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scans", default="/workspace/vve-source-audit")
    main(ap.parse_args().scans)
