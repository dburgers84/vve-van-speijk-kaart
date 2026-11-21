#!/usr/bin/env python3
"""Bouwt data/f1.v2.json + pilot/pilot_data_f1.js: 1e verdieping (akte 2006 p.82).

Hergebruikt de Builder/maatlogica van build_model.py met een EIGEN frame + kalibratie (p82),
en de semi-automatische segmentatie uit data/inventory/f1_segments_p82.json
(tools/segment_bg.py --floor 1e, zelfde lijnwerk tools/linework.py als de BG).
Zonder lokale scan (--scan none) wordt de inkt-ondersteuning uit de vorige build overgenomen (reproduceerbaar).
"""
import argparse
import copy
import hashlib
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_model as BM  # noqa: E402
from traces import f1_segments as M  # noqa: E402

ROOT = os.path.dirname(HERE)
DATASET_VERSION = "f1-0.1.0"
FLOOR, FRAME, SOURCE, CAL = "1e", "frm_p82_native", "src_akte2006_p82", "cal_p82_controls"
NATIVE = M.NATIVE
# ---- kalibratie p82 (zie data/inventory/calibration_p82.json; gemeten 2026-11-21 op de lokale scan)
BAR_X, BAR_PX, BAR_M = 77, (335.5, 728.7), 10.0
RULER_X, RULER_TICKS = 438, (379.34, 773.49)          # 0 en 5 cm
RULER_PX_PER_CM = (RULER_TICKS[1] - RULER_TICKS[0]) / 5
M_BAR = BAR_M / (BAR_PX[1] - BAR_PX[0])               # 0.025432 m/px
M_RULER = 2.0 / RULER_PX_PER_CM                         # 0.025371 m/px
M_NOMINAL = 0.0254
M_ADOPT = round((M_BAR + M_RULER) / 2, 7)
HALF_SPREAD = abs(M_BAR - M_RULER) / 2 / M_ADOPT        # ~0,12 %
READ_TOL = math.sqrt(2) * 1.5 / (BAR_PX[1] - BAR_PX[0])  # ~0,54 %
REL_U_Y = round(max(HALF_SPREAD, READ_TOL), 4)
REL_ANISO_P81 = BM.REL_ANISO                           # 0,88 % (kolomstramien p81)
REL_U_X = round(REL_U_Y + REL_ANISO_P81, 4)
OUT = os.path.join(ROOT, "data", "f1.v2.json")
JS_OUT = os.path.join(ROOT, "pilot", "pilot_data_f1.js")
SEG_JSON = os.path.join(ROOT, "data", "inventory", "f1_segments_p82.json")
REG_JSON = BM.REG_JSON

# Builder/dim_for lezen deze module-globals van build_model: zet ze op het p82-frame
for k, v in dict(FLOOR=FLOOR, FRAME=FRAME, SOURCE=SOURCE, CAL=CAL, NATIVE=NATIVE, M_PER_PX=(M_ADOPT, M_ADOPT),
                 REL_U_X=REL_U_X, REL_U_Y=REL_U_Y,
                 EV_TRACE={"source_id": SOURCE, "method": "auto_segment_inner_face"}).items():
    setattr(BM, k, v)

H, O = "ls_hoofdsplitsing", "ls_ondersplitsing_woningen"
WONING_RANGE, BERGING_RANGE = range(181, 266), range(266, 357)
ELEMENT_KINDS = {"wall_band": "Wandstrook tussen dubbele lijnen (getekende wanddikte)"}
UNRES = ("unlabeled_space", "unresolved_space", "cross_marked_cell")


def legal_splits():
    ls = copy.deepcopy(BM.LEGAL_SPLITS)
    o = next(s for s in ls if s["id"] == O)
    o["rights"] = ([{"id": f"O-{n}", "name": f"Woonappartement (indexnummer {n})", "drawing_index": str(n)} for n in WONING_RANGE]
                   + [{"id": f"O-{n}", "name": f"Berging (indexnummer {n})", "drawing_index": str(n)} for n in BERGING_RANGE])
    o["rights_note"] = ("Rechten-id 'O-n' = indexnummer n op de splitsingstekening (181-265 woningen, 266-356 bergingen = 176 rechten volgens de akte). "
                        "De kadastrale appartementsrechtnummers zijn NIET gelezen; dit is een tekening-index, geen kadastrale aanduiding.")
    return ls


def display_name(kind, lit, idx):
    if kind == "apartment_dwelling":
        return f"Woning {idx}"
    if kind == "storage_unit":
        return f"Berging {idx}"
    if kind == "apartment_part":
        return f"Vak bij recht {idx} (deel van woning {idx}? onzeker)"
    return {"private_outdoor": "Buitenruimte", "private_outdoor_multi_unresolved": "Buitenruimte(n) — onderverdeling niet getraceerd",
            "roof": "Dak", "void": "Vide", "stair": "Trap", "lift_shaft": "Lift", "core_multi_unresolved": "Kern trap/lift — niet onderverdeeld",
            "storage_corridor": "Gang/bergingen", "roof_path_network_unresolved": "Pad(en) over dak — onopgelost",
            "cross_marked_cell": "Vak met kruis (X)", "unlabeled_space": "Onbenoemd vak", "unresolved_space": "Vak met meerdere functies — onopgelost",
            "commercial_unit": "bedrijfs-ruimte", "commercial_multi_unresolved": "Bedrijfsruimte(n) — onderverdeling onopgelost",
            "a179_region_unresolved": "Gebied met indexnummer 179 — onopgelost",
            "commercial_round_part": "Halfrond vak met 179"}.get(kind) or lit or kind


def certainty(kind):
    if kind.endswith("unresolved") or kind in UNRES:
        return "unresolved"
    return "uncertain" if kind == "apartment_part" else "probable"


def legal_for(kind, idx, h179):
    """Afgeleide lidmaatschappen per vak; ontbrekend = unknown."""
    n = int(idx) if idx else None
    out = {}
    if kind in ("apartment_dwelling", "storage_unit"):
        what = "woningen" if kind == "apartment_dwelling" else "bergingen"
        rng = WONING_RANGE if kind == "apartment_dwelling" else BERGING_RANGE
        assert n in rng, (kind, n)
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 staat bij vrijwel alle woningen/bergingen op dit blad (niet per vak gepositioneerd); A-180 = Woningen (MVGM)")
        out[O] = ("private", f"O-{n}", "probable", f"Indexnummer {n} in dit vak (visueel gelezen); {rng.start}-{rng.stop - 1} = {what} volgens de nummering van de ondersplitsing (176 rechten)")
    elif kind == "apartment_part":
        out[H] = ("private", "A-180", "uncertain", "Groot indexnummer zonder label 'woning'; vermoedelijk onderdeel van een woning binnen A-180")
        out[O] = ("private", f"O-{n}", "uncertain", f"Nummer {n} zonder label 'woning': mogelijk buitenruimte/trap van woning {n}; niet bewezen")
    elif kind.startswith("private_outdoor"):
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 met verwijsstreep bij buitenruimten op dit blad; A-180 = Woningen (MVGM)")
    elif kind.startswith("commercial") or kind == "a179_region_unresolved":
        out[H] = ("private", "A-179", "probable" if h179 else "uncertain",
                  "Indexnummer 179 in dit vak; A-179 = Winkels (commerciële ruimten) volgens MVGM-begroting hoofdsplitsing" if h179 else
                  "Commerciële functie gelezen, geen 179 in dit vak; A-179 = commerciële ruimten (MVGM)")
        out[O] = ("excluded", None, "uncertain", "Valt onder A-179; ondersplitsing is genest binnen A-180 (woningen + bergingen)")
    elif kind == "void" and h179:
        out[H] = ("private", "A-179", "uncertain", "Indexnummer 179 in deze vide; vide boven commerciële ruimte? niet bewezen")
        out[O] = ("excluded", None, "uncertain", "179 in deze vide; ondersplitsing is genest binnen A-180")
    elif kind == "storage_corridor":
        out[H] = ("private", "A-180", "uncertain", "Gang naar bergingen 266-356 (ondersplitsing); geen eigen indexnummer")
        out[O] = ("common", None, "uncertain", "Gang tussen bergingen; gemeenschappelijk niet per vak bewezen")
    elif kind in ("stair", "lift_shaft", "core_multi_unresolved"):
        out[O] = ("common", None, "uncertain", BM._AKTE_O + "; welke trappen/liften bij de woningen horen is niet per vak bewezen")
    return out


class F1Builder(BM.Builder):
    def add_segments_f1(self, seg):
        P = M.PREFIX
        okey, meta = {}, []
        for key, seed, kind, lit, idx, h179, note in M.SEEDS:
            g = seg["segments"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="auto_segment_inner_face", tol=3) for i, xy in enumerate(g["polygon"])]
            is_el = kind in ELEMENT_KINDS
            fields = {"kind": kind, "class": "element" if is_el else "space", "region_id": M.REGION_ID,
                      "display_name": ELEMENT_KINDS.get(kind) or display_name(kind, lit, idx),
                      "certainty": certainty(kind), "review_status": "needs_review",
                      "evidence": {"source_id": SOURCE, "method": "auto_segment_inner_face (tools/segment_bg.py --floor 1e) + visuele review contactbladen",
                                   "boundary": "binnenzijde getekende lijn",
                                   "note": " ".join(x for x in [(note or "").rstrip(".") + ("." if note else ""),
                                                                "" if is_el else "Grens = binnenzijde van de getekende lijn (wandstrook ligt ertussen)."] if x)}}
            if not is_el:
                fields["source_label_text"] = lit
                fields["current_use"] = None
                if idx:
                    fields["index_number"] = idx
            o = self.polygon_object(o_id, P, vids, (lambda a, b: "element_outline") if is_el else (lambda a, b: "wall_inner_face"), **fields)
            for hi, hole in enumerate(g.get("holes", [])):   # omsloten buurvakken (binnenringen)
                hv = [self.vertex(f"v_{P}_{key}_h{hi}_{i}", tuple(xy), method="auto_segment_inner_face", tol=3) for i, xy in enumerate(hole)]
                o["geometry"]["rings"].append(hv)
                o["edge_ids"] += [self.edge(P, hv[i], hv[(i + 1) % len(hv)], "wall_inner_face") for i in range(len(hv))]
            if g.get("holes"):
                o["evidence"]["note"] += f" {len(g['holes'])} omsloten buurvakken als gaten (binnenringen)."
            sx, sy = seed
            approx = "Visueel gelezen op contactblad; bbox BENADERD rond het zaadpunt (tekstpositie niet gemeten)"
            if idx:
                self.label(f"lbl_{P}_{key}_n", idx, "index_number", (sx - 45, sy - 80, sx + 45, sy + 80), [o_id], "probable", approx)
            if lit:
                self.label(f"lbl_{P}_{key}", lit, "space_name", (sx - 60, sy - 60, sx + 60, sy + 60), [o_id], "probable", approx)
            if h179:
                self.label(f"lbl_{P}_{key}_i179", "179", "index_number", (sx - 40, sy - 75, sx + 40, sy + 75), [o_id], "probable",
                           "Indexnummer 179 in dit vak (visueel); bbox benaderd")
            if not is_el:
                meta.append((o_id, legal_for(kind, idx, h179)))
        for key, seed, note in M.HATCH_SEEDS:
            g = seg["hatch"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="hatch_diagonal_density_outline", tol=8) for i, xy in enumerate(g["polygon"])]
            self.polygon_object(o_id, P, vids, lambda a, b: "virtual_boundary", kind="not_in_split_area", **{"class": "space"},
                                region_id=M.REGION_ID, display_name="Gearceerd: niet in de splitsing betrokken",
                                source_label_text=None, current_use=None, certainty="probable", review_status="needs_review",
                                evidence={"source_id": SOURCE, "method": "dichtheid diagonale arceerlijnen (tools/segment_bg.py --floor 1e)",
                                          "boundary": "buitenrand arcering (±8 px)",
                                          "note": note + ". Labels binnen de arcering (o.a. 'vide', 'dak') niet als aparte vakken getraceerd."})
            ex = ("excluded", None, "probable", "Arcering = 'niet in de splitsing betrokken' (legenda op het blad)")
            meta.append((o_id, {H: ex, O: ex}))
        self.label(f"lbl_{P}_legend_hatch", "= niet in de splitsing betrokken", "note", M.LEGEND_BBOX,
                   [okey[k] for k, *_ in M.HATCH_SEEDS if k in okey], "source", "Legenda op het blad (arcering)")
        return okey, meta


def coverage_block(B, seg):
    kinds = Counter(o["kind"] for o in B.objects if o.get("region_id") == M.REGION_ID)
    unres = sum(v for k, v in kinds.items() if k.endswith("unresolved") or k in UNRES)
    won = sorted(int(i) for _k, _s, kd, _l, i, _h, _n in M.SEEDS if kd == "apartment_dwelling" and f"obj_{M.PREFIX}_{_k}" in {o["id"] for o in B.objects})
    berg = sorted(int(i) for _k, _s, kd, _l, i, _h, _n in M.SEEDS if kd == "storage_unit")
    return {"complete": False,
            "scope": "Alleen 1e verdieping (blad p.82). Semi-automatisch: alle gesloten vakken met zaadpunt (binnenzijde getekende lijn), "
                     "2 arceringen en wandstroken. Classificatie visueel gelezen op contactbladen. BG staat in bg.v2.json; 2e-4e verdieping nog niet getraceerd.",
            "floors_covered": ["1e (grotendeels, deels onopgelost)"],
            "counts": {"segment_kinds": dict(sorted(kinds.items())), "unresolved_or_unlabeled_segments": unres,
                       "woningen_on_sheet": len(won), "woningen_numbers": won,
                       "bergingen_on_sheet": len(berg), "bergingen_missing_266_356": sorted(set(BERGING_RANGE) - set(berg)),
                       "segments_problems": seg.get("problems", [])},
            "traced": [f"{len(won)} woningen (indexnummers visueel gelezen)", f"{len(berg)} bergingen = alle 266-356",
                       "buitenruimten, daken, vides, trappen/liften, gangen bergingen, bedrijfsruimten (labels visueel gelezen)",
                       "2 arceringen 'niet in de splitsing betrokken' (diagonaaldetectie)", "wandstroken tussen dubbele lijnen"],
            "not_traced": ["deuren/draaibogen en traptreden (niet getraceerd; niet verzonnen)",
                           "onderverdeling van buitenruimten met meerdere omcirkelde 180 en gestippelde deellijnen",
                           "scheiding woning/buitenruimte waar de lijn niet gesloten is (WB-vakken) en kernen trap+lift in één vlak",
                           "onderverdeling multi-label bedrijfsvakken en 179-gebieden",
                           "posities van de omcirkelde 180-symbolen (alleen als toelichting, niet per vak gemeten)",
                           "exacte tekstposities: labelboxen zijn benaderd rond het zaadpunt",
                           "kolommen (p82 kolomkandidaten niet beoordeeld)", "gestippelde contouren (bijv. 'contour bovengelegen ...')",
                           "2e, 3e en 4e verdieping/daken: niets getraceerd"]}


def build(scan_path=None):
    A, scan_sha = None, None
    if scan_path and scan_path != "none" and os.path.exists(scan_path):
        from PIL import Image
        import numpy as np
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(scan_path).convert("L")
        assert im.size == NATIVE, im.size
        A = np.array(im) < BM.INK_SUPPORT_THRESHOLD
        scan_sha = hashlib.sha256(open(scan_path, "rb").read()).hexdigest()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    old_ink = {e["id"]: e.get("ink_support") for e in old.get("edges", [])}
    if scan_sha is None:
        scan_sha = (old.get("sources") or [{}])[0].get("scan_sha256")
    seg = json.load(open(SEG_JSON))
    reg = json.load(open(REG_JSON)) if os.path.exists(REG_JSON) else None
    B = F1Builder(A, old_ink)
    okey, seg_meta = B.add_segments_f1(seg)
    pts = [B.pos[v] for o in B.objects for v in o["geometry"]["rings"][0]]
    regions = [{"id": M.REGION_ID, "name": M.REGION_NAME, "region_px": list(M.REGION_PX), "floor_id": FLOOR,
                "fit_px": [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)],
                "columns_from_detector": 0, "method": "semi-automatische segmentatie (binnenzijde lijn) + visuele review", "local_crop_scale": 0.25}]
    overlays = []
    if reg and FLOOR in reg.get("floors", {}):
        r = reg["floors"][FLOOR]
        overlays.append({"id": "ovl_plan_1e_jpg", "frame_id": FRAME, "image": "img/plan_1e.jpg", "public": True,
                         "size_px": r["image_size"], "image_to_native_affine": r["image_to_native_affine"],
                         "method": r["method"], "ecc_correlation": r["ecc_correlation"],
                         "note": "Eerder gepubliceerde lage-resolutie (≈0,24x) referentie; geen nieuwe bronpublicatie."})
    seg_ids = {o for o, _ in seg_meta}
    data = {
        "schema_version": BM.SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "generated": "2026-11-21",
        "sources": [{
            "id": SOURCE, "title": "Splitsingsakte 2006, tekenblad 1e verdieping (ondersplitsingstekening woningen + bergingen)",
            "document": "1050_96739052_Splitsingsakte_+_tekeningen.pdf", "page": 82, "drawing_sheet": "02",
            "author": "W. Grandia BV, project 2273", "native_size_px": list(NATIVE), "dpi": 200, "raster_only": True,
            "scan_sha256": scan_sha, "pdf_extract_sha256": (old.get("sources") or [{}])[0].get("pdf_extract_sha256"),
            "privacy_class": "private_deed_drawing", "publish_native_raster": False,
            "note": "Bladtitel '1e Verdieping, Schaal 1 a 200' gelezen; bladnummer 02 afgeleid uit de volgorde. Native raster blijft lokaal."}] + BM.EXTRA_SOURCES,
        "calibrations": [{
            "id": CAL, "frame_id": FRAME, "model": "nominal_scale", "m_per_px_x": M_ADOPT, "m_per_px_y": M_ADOPT,
            "basis": "Gemiddelde van twee controles langs native y op blad 82: eigen schaalbalk ('1e Verdieping Schaal 1 a 200', 0-10 m) en cm-liniaal x opgegeven schaal 1:200",
            "status": "controls_checked_one_axis", "uncertainty_m": None, "uncertainty_status": "estimated",
            "rel_uncertainty": {"x": REL_U_X, "y": REL_U_Y},
            "axis_status": {"y": "checked_against_scale_bar_and_ruler", "x": "assumed_isotropic_not_independently_verified"},
            "control_points": [
                {"id": "bar_0m", "kind": "scale_bar_tick", "x_px": BAR_X, "y_px": BAR_PX[0], "value_m": 0.0, "reading_tolerance_px": 1.5},
                {"id": "bar_10m", "kind": "scale_bar_tick", "x_px": BAR_X, "y_px": BAR_PX[1], "value_m": 10.0, "reading_tolerance_px": 1.5},
                {"id": "ruler_0cm", "kind": "ruler_tick", "x_px": RULER_X, "y_px": RULER_TICKS[0], "value_cm": 0},
                {"id": "ruler_5cm", "kind": "ruler_tick", "x_px": RULER_X, "y_px": RULER_TICKS[1], "value_cm": 5}],
            "checks": {
                "m_per_px_scale_bar_0_10m": round(M_BAR, 6), "m_per_px_ruler_x_1to200": round(M_RULER, 6),
                "m_per_px_nominal_1to200_200dpi": M_NOMINAL, "adopted": M_ADOPT,
                "bar_vs_ruler_pct": round((M_BAR / M_RULER - 1) * 100, 2),
                "bar_vs_nominal_pct": round((M_BAR / M_NOMINAL - 1) * 100, 2), "ruler_vs_nominal_pct": round((M_RULER / M_NOMINAL - 1) * 100, 2),
                "half_spread_rel": round(HALF_SPREAD, 4), "reading_tolerance_rel": round(READ_TOL, 4),
                "bar_segments_px_per_2m": [76.5, 81.5, 80.7, 75.5, 79.0],
                "bar_segment_note": "Segmenten ongelijk (75,5-81,5 px per 2 m); alleen eindpunten gebruikt",
                "x_margin_note": "x-as niet onafhankelijk gecontroleerd; marge = marge y + 0,88 % anisotropie (kolomstramien p81)",
                "p81_comparison": "Balk p81 387,0 px vs p82 393,2 px per 10 m: reproductieschaal verschilt per blad (1,6 %), dus per blad gekalibreerd"},
            "residuals": None,
            "note": "GESCHATTE marge: y = max(halve spreiding balk/liniaal, afleestolerantie balkeinden). Zie data/inventory/calibration_p82.json."}],
        "frames": [{"id": FRAME, "source_id": SOURCE, "floor_id": FLOOR, "unit": "px_native", "width_px": NATIVE[0],
                    "height_px": NATIVE[1], "axis_x": "right", "axis_y": "down",
                    "orientation": "scan_as_is_not_north_up", "calibration_ids": [CAL]}],
        "floors": [{"id": FLOOR, "name": "1e verdieping", "level": 1, "source_ids": [SOURCE]}],
        "regions": regions, "reference_overlays": overlays,
        "objects": B.objects, "vertices": B.vertices, "edges": B.edges, "labels": B.labels,
        "connections": [],
        "legal_splits": legal_splits(),
        "legal_split_ui": {"enabled": True,
                           "reason": "Gedeeltelijk: lidmaatschap per vak afgeleid uit indexnummers (181-356, 179, omcirkeld 180) + MVGM-stukken en akte-tekst; splitsingsgrenzen zelf niet als lijn getekend. Zekerheid per vak zichtbaar."},
        "memberships": _memberships(seg_meta),
        "legacy_links": [],
        "coverage": coverage_block(B, seg),
        "review_log": [{"date": "2026-11-21", "by": "Grok Bot (executor)",
                        "action": "fase 4: 1e verdieping (p82) kalibratie + semi-automatische segmentatie + visuele classificatie", "status": "needs_human_review"}],
    }
    assert seg_ids <= {o["id"] for o in B.objects}
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(JS_OUT, "w") as f:
        f.write("// gegenereerd door model/tools/build_floor1.py\nwindow.PILOT_DATA_F1 = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    return data


def _memberships(seg_meta):
    old = BM.TRACES, BM.LEGAL_SPLITS
    BM.TRACES, BM.LEGAL_SPLITS = [], legal_splits()
    try:
        return BM.memberships(None, seg_meta)
    finally:
        BM.TRACES, BM.LEGAL_SPLITS = old


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", default="/workspace/vve-source-audit/page-82.png")
    a = ap.parse_args()
    d = build(a.scan)
    weak = [e for e in d["edges"] if e["ink_support"] and e["role"] == "wall_inner_face" and e["ink_support"]["fraction"] < 0.9]
    print(OUT, len(d["objects"]), "objects", len(d["edges"]), "edges;", len(weak), "space edges ink<0.9")
