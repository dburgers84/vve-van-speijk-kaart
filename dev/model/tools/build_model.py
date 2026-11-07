#!/usr/bin/env python3
"""Bouw de BG-dataset (schema vve-plan v2) uit handmatige traces + lokale bronscan.

Gebruik:
  python3 model/tools/build_model.py                       # met lokale scan (default pad)
  python3 model/tools/build_model.py --scan none           # zonder privébron: inktsteun uit bestaande dataset

- De native bronpagina wordt ALLEEN lokaal gelezen (nooit in de repo) voor inktsteun per zijde
  en voor lokale reviewbeelden (model/pilot/local/, git-ignored).
- Kolommen komen uit data/inventory/columns_auto_p81.json (tools/detect_columns.py) en worden
  alleen opgenomen binnen getraceerde regio's, als 'probable' (auto-detectie, visueel gecontroleerd
  op reviewbeeld, nog niet per stuk gereviewd).
- Publieke overlay: img/plan_bg.jpg (al eerder gepubliceerd), geregistreerd op het native frame
  (data/inventory/registration_plan_jpg.json).
"""
import argparse, hashlib, json, math, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from traces import bg_core, bg_kiel  # noqa: E402

TRACES = [bg_core, bg_kiel]
SCHEMA_VERSION = "vve-plan/2.1.0"
DATASET_VERSION = "bg-0.2.0"
FLOOR = "BG"
FRAME = "frm_p81_native"
SOURCE = "src_akte2006_p81"
CAL = "cal_p81_nominal"
NATIVE = (7118, 10099)
M_PER_PX = (0.025399999806400928, 0.025399999249508854)  # nominaal 1:200 @200dpi
OUT = os.path.join(ROOT, "data", "bg.v2.json")
COLUMNS_JSON = os.path.join(ROOT, "data", "inventory", "columns_auto_p81.json")
REG_JSON = os.path.join(ROOT, "data", "inventory", "registration_plan_jpg.json")
EV_TRACE = {"source_id": SOURCE, "method": "visual_trace_2x_grid+ink_profile"}


def ink_support(A, p, q, r=3):
    if A is None:
        return None
    (x1, y1), (x2, y2) = p, q
    n = max(2, int(math.hypot(x2 - x1, y2 - y1)))
    hits, gaps, cur = 0, [], 0
    H, W = A.shape
    for i in range(n + 1):
        t = i / n
        x, y = int(round(x1 + t * (x2 - x1))), int(round(y1 + t * (y2 - y1)))
        win = A[max(0, y - r):min(H, y + r + 1), max(0, x - r):min(W, x + r + 1)]
        if win.any():
            hits += 1
            if cur:
                gaps.append(cur)
            cur = 0
        else:
            cur += 1
    if cur:
        gaps.append(cur)
    return {"radius_px": r, "fraction": round(hits / (n + 1), 3), "max_gap_px": max(gaps) if gaps else 0}


def dim_for(role, p, q):
    if role == "virtual_opening":
        return {"status": "unknown", "length_m": None, "uncertainty_m": None, "uncertainty_status": "unknown",
                "method": None, "calibration_ref": None, "source_text": None, "source_ref": None,
                "note": "Virtuele grens (kandidaat-opening); eindpunten niet scherp in bron."}
    dx, dy = q[0] - p[0], q[1] - p[1]
    lm = math.hypot(dx * M_PER_PX[0], dy * M_PER_PX[1])
    return {"status": "derived", "length_m": round(lm, 2), "uncertainty_m": None, "uncertainty_status": "unknown",
            "method": "nominal_scale_px_length", "calibration_ref": CAL, "source_text": None, "source_ref": None,
            "note": "Nominaal 1:200@200dpi; scanvervorming ongetoetst; geen bronmaat op tekening gevonden."}


LEGAL_SPLITS = [
    {"id": "ls_hoofdsplitsing", "name": "Hoofdsplitsing complex Van Speijk — VvE Van Speijk (Hoofdsplitsing)",
     "legal_reference": "Appartementsrechten A-179 (Winkels / commerciële ruimten) en A-180 (Woningen)",
     "rights": [{"id": "A-179", "name": "Winkels (commerciële ruimten)", "drawing_index": "179"},
                {"id": "A-180", "name": "Woningen (ondergesplitst)", "drawing_index": "180"}],
     "parent_id": None, "status": "identified_in_source", "boundary_status": "partial",
     "evidence": {"source_id": "src_mvgm_hoofdsplitsing_stukken", "method": "tekst gelezen (pdftotext): begroting 2025 + jaarrekening 2023 hoofdsplitsing"}},
    {"id": "ls_ondersplitsing_woningen", "name": "Ondersplitsing — VvE Van Speijk (Woningen): 85 woonappartementen + 91 bergingen",
     "legal_reference": "Akte van ondersplitsing 2006 (176 rechten). Titelblok tekening noemt 'appartementsrecht A-2'; relatie tot A-180 (MVGM) nog niet opgehelderd.",
     "rights": [], "parent_id": "ls_hoofdsplitsing", "status": "identified_in_source", "boundary_status": "partial",
     "evidence": {"source_id": "src_akte2006_ondersplitsing_tekst", "method": "titelpagina akte deel 1 visueel gelezen + titelblok tekening"}},
]
EXTRA_SOURCES = [
    {"id": "src_mvgm_hoofdsplitsing_stukken", "title": "MVGM: Begroting 2025 en Jaarrekening 2023 VvE Van Speijk (Hoofdsplitsing)",
     "document": "Hoofdsplitsing; Begroting 2025.pdf + Hoofdsplitsing; Jaarrekening 2023.pdf (Twinq, vergadering 2024-06-04)",
     "page": 1, "raster_only": False, "privacy_class": "private_personal_data", "publish_native_raster": False,
     "note": "Alleen gebruikt: namen van appartementsrechten A-179/A-180 en VvE-namen. Geen bedragen/personen overgenomen."},
    {"id": "src_akte2006_ondersplitsing_tekst", "title": "Akte van ondersplitsing Centrumplan complex 'Van Speijk' (2006), 85 woonappartementen met 91 bergingen",
     "document": "1050_51283635_Akte_deel_1.pdf (p.1) + 1050_51283743_Akte_deel_2.pdf", "page": 1, "raster_only": True,
     "privacy_class": "private_personal_data", "publish_native_raster": False,
     "note": "Tekstakte zonder tekenbladen (contactbladen bekeken)."},
]


def memberships(B):
    out = []
    for T in TRACES:
        legal = getattr(T, "LEGAL", {})
        for key, *_ in T.SPACES:
            oid_ = f"obj_{T.PREFIX}_{key}"
            given = {m[0]: m for m in legal.get(key, [])}
            for sp in LEGAL_SPLITS:
                if sp["id"] in given:
                    _, rel, right, cert, note = given[sp["id"]]
                    out.append({"object_id": oid_, "split_id": sp["id"], "relation": rel, "right_id": right,
                                "certainty": cert, "evidence": {"source_id": sp["evidence"]["source_id"], "method": "label+akte/MVGM-tekst", "note": note}})
                else:
                    out.append({"object_id": oid_, "split_id": sp["id"], "relation": "unknown", "right_id": None,
                                "certainty": "unknown", "evidence": None})
    return out


class Builder:
    def __init__(self, A, old_ink):
        self.A, self.old_ink = A, old_ink
        self.vertices, self.vid, self.pos = [], {}, {}
        self.edges, self.ekey = [], {}
        self.objects, self.labels, self.connections, self.legacy = [], [], [], []

    def vertex(self, vkey, xy, method="visual_trace_2x_grid+ink_profile", tol=4):
        if vkey in self.vid:
            return self.vid[vkey]
        x, y = xy
        W, H = NATIVE
        self.vid[vkey] = vkey
        self.pos[vkey] = (x, y)
        self.vertices.append({"id": vkey, "frame_id": FRAME, "floor_id": FLOOR, "x_px": x, "y_px": y,
                              "x_rel": round(x / W, 8), "y_rel": round(y / H, 8),
                              "positional_tolerance_px": tol,
                              "evidence": {"source_id": SOURCE, "method": method}})
        return vkey

    def edge(self, prefix, a, b, role):
        k = tuple(sorted((a, b)))
        if k in self.ekey:
            return self.ekey[k]
        eid = f"e_{prefix}_{k[0].split('_', 3)[-1]}_{k[1].split('_', 3)[-1]}"
        p, q = self.pos[a], self.pos[b]
        ink = ink_support(self.A, p, q) if self.A is not None else self.old_ink.get(eid)
        tq = None if ink is None else ("not_applicable" if role == "virtual_opening"
                                       else ("ink_confirmed" if ink["fraction"] >= 0.9 else "partial_ink"))
        self.edges.append({"id": eid, "frame_id": FRAME, "floor_id": FLOOR, "v": [a, b], "role": role,
                           "length_px": round(math.hypot(q[0] - p[0], q[1] - p[1]), 2),
                           "dimension": dim_for(role, p, q), "ink_support": ink, "trace_quality": tq,
                           "evidence": EV_TRACE})
        self.ekey[k] = eid
        return eid

    def polygon_object(self, oid_, prefix, ring, role_of, **fields):
        eids = [self.edge(prefix, ring[i], ring[(i + 1) % len(ring)], role_of(ring[i], ring[(i + 1) % len(ring)]))
                for i in range(len(ring))]
        o = {"id": oid_, "revision": 1, "floor_id": FLOOR, "frame_id": FRAME,
             "geometry": {"type": "Polygon", "rings": [ring]}, "edge_ids": eids, "label_ids": []}
        o.update(fields)
        self.objects.append(o)
        return o

    def label(self, lid, lit, cat, bbox, assigned, cert, note=None):
        lab = {"id": lid, "literal_text": lit, "normalized_text": None if lit is None else lit.lower(),
               "category": cat, "bbox_px": list(bbox), "frame_id": FRAME, "assigned_object_ids": assigned,
               "certainty": cert, "evidence": {"source_id": SOURCE, "method": "visual_read_no_ocr"}}
        if note:
            lab["note"] = note
        self.labels.append(lab)
        for a in assigned:
            next(o for o in self.objects if o["id"] == a)["label_ids"].append(lid)

    def add_trace(self, T):
        P = T.PREFIX
        V = {k: self.vertex(f"v_{P}_{k}", xy) for k, xy in T.VERTICES.items()}
        roles = {}
        for (a, b), r in T.EDGE_ROLES.items():
            roles[frozenset((V[a], V[b]))] = r
        role_of = lambda a, b: roles.get(frozenset((a, b)), "wall_drawn")  # noqa: E731
        okey = {}
        cu = getattr(T, "CURRENT_USE", {})
        for key, kind, ring, lit, bbox, cert in T.SPACES:
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            fields = {"kind": kind, "class": "space", "region_id": T.REGION_ID,
                      "display_name": lit or f"Onbenoemde ruimte ({key})",
                      "source_label_text": lit,
                      "current_use": None,
                      "certainty": "unresolved" if cert == "unresolved" else ("source" if cert == "source_label" else "probable"),
                      "review_status": "needs_review",
                      "evidence": dict(EV_TRACE, note="Polygonen op getekende lijnhartlijnen (bij dubbele gevellijn: binnenlijn); wanddikte niet afgetrokken.")}
            if key in cu:
                val, src, c = cu[key]
                fields["current_use"] = {"value": val, "source": src, "certainty": c}
            self.polygon_object(o_id, P, [V[v] for v in ring], role_of, **fields)
            if lit is not None:
                self.label(f"lbl_{P}_{key}", lit, "space_name", bbox, [o_id],
                           "source" if cert == "source_label" else "probable")
        for key, kind, seq, note in T.LINES:
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            self.objects.append({"id": o_id, "revision": 1, "floor_id": FLOOR, "frame_id": FRAME, "kind": kind,
                                 "class": "linear_feature", "region_id": T.REGION_ID, "display_name": note,
                                 "geometry": {"type": "LineString", "vertices": [V[v] for v in seq]},
                                 "edge_ids": [], "label_ids": [], "certainty": "probable",
                                 "review_status": "needs_review", "evidence": EV_TRACE})
        for key, kind, pts, note, cert in getattr(T, "ELEMENTS", []):
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", xy) for i, xy in enumerate(pts)]
            base = {"kind": kind, "class": "element", "region_id": T.REGION_ID, "display_name": note,
                    "certainty": cert, "review_status": "needs_review", "evidence": EV_TRACE}
            if len(pts) >= 3:
                self.polygon_object(o_id, P, vids, lambda a, b: "element_outline", **base)
            else:
                o = {"id": o_id, "revision": 1, "floor_id": FLOOR, "frame_id": FRAME,
                     "geometry": {"type": "LineString", "vertices": vids}, "edge_ids": [], "label_ids": []}
                o.update(base)
                self.objects.append(o)
        for i, (lit, cat, bbox, assigned, cert, note) in enumerate(T.EXTRA_LABELS):
            self.label(f"lbl_{P}_x{i:02d}", lit, cat, bbox, [okey[a] for a in assigned], cert, note)
        for cid, kind, (a, b), spaces, cert, note in T.CONNECTIONS:
            self.connections.append({"id": f"conn_{P}_{cid.replace('conn_', '')}", "kind": kind,
                                     "edge_id": self.ekey[tuple(sorted((V[a], V[b])))],
                                     "connects": [okey.get(s, s) for s in spaces], "certainty": cert,
                                     "door_leaf_drawn": False, "swing": None, "note": note,
                                     "evidence": {"source_id": SOURCE, "method": "visual+ink_gap"}})
        for lid, k, rel in T.LEGACY:
            self.legacy.append({"legacy_system": "svg_v2_common_json", "legacy_id": lid, "object_id": okey[k],
                                "relation": rel, "certainty": "uncertain" if rel == "uncertain" else "probable",
                                "note": "Koppeling op functie+label; ligging in oude SVG-coördinaten niet geometrisch getoetst."})
        return okey

    def add_columns(self, T, cols):
        x0, y0, x1, y1 = T.REGION_PX
        n = 0
        boxes = [l["bbox_px"] for l in self.labels]
        for c in sorted(cols, key=lambda c: (c["y"], c["x"])):
            if not (x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1):
                continue
            if any(b[0] - 4 <= c["x"] <= b[2] + 4 and b[1] - 4 <= c["y"] <= b[3] + 4 for b in boxes):
                continue  # valt binnen tekstlabel: letter, geen kolom
            n += 1
            key = f"kolom{n:02d}"
            h = c["size_px"] / 2
            pts = [(c["x"] - h, c["y"] - h), (c["x"] + h, c["y"] - h), (c["x"] + h, c["y"] + h), (c["x"] - h, c["y"] + h)]
            vids = [self.vertex(f"v_{T.PREFIX}_{key}_{i}", xy, method="auto_detect_hollow_square", tol=2) for i, xy in enumerate(pts)]
            self.polygon_object(f"obj_{T.PREFIX}_{key}", T.PREFIX, vids, lambda a, b: "element_outline",
                                kind="column", **{"class": "element"}, region_id=T.REGION_ID,
                                display_name=f"Kolom (getekend vierkantje, {c['size_px']} px)",
                                certainty="probable", review_status="needs_review",
                                evidence={"source_id": SOURCE, "method": "auto_detect_hollow_square",
                                          "note": f"detector side_min={c['side_min']}; vierkant op getekende inkt, geen materiaal/maat vermeld"})
        return n


def build(scan_path=None, crop_out=None, pdf_path=None):
    A, scan_sha = None, None
    if scan_path and scan_path != "none" and os.path.exists(scan_path):
        from PIL import Image
        import numpy as np
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(scan_path).convert("L")
        assert im.size == NATIVE, im.size
        A = np.array(im) < 128
        scan_sha = hashlib.sha256(open(scan_path, "rb").read()).hexdigest()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    old_ink = {e["id"]: e.get("ink_support") for e in old.get("edges", [])}
    if scan_sha is None:
        scan_sha = (old.get("sources") or [{}])[0].get("scan_sha256")
    pdf_sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest() if pdf_path and os.path.exists(pdf_path) \
        else (old.get("sources") or [{}])[0].get("pdf_extract_sha256")
    cols = json.load(open(COLUMNS_JSON))["candidates"] if os.path.exists(COLUMNS_JSON) else []
    reg = json.load(open(REG_JSON)) if os.path.exists(REG_JSON) else None

    B = Builder(A, old_ink)
    regions, ncols = [], {}
    for T in TRACES:
        B.add_trace(T)
        ncols[T.REGION_ID] = B.add_columns(T, cols)
        regions.append({"id": T.REGION_ID, "name": T.REGION_NAME, "region_px": list(T.REGION_PX), "floor_id": FLOOR,
                        "columns_from_detector": ncols[T.REGION_ID]})

    overlays = []
    if reg and "BG" in reg.get("floors", {}):
        r = reg["floors"]["BG"]
        overlays.append({"id": "ovl_plan_bg_jpg", "frame_id": FRAME, "image": "img/plan_bg.jpg", "public": True,
                         "size_px": r["image_size"], "image_to_native_affine": r["image_to_native_affine"],
                         "method": r["method"], "ecc_correlation": r["ecc_correlation"],
                         "note": "Eerder gepubliceerde lage-resolutie (≈0,24x) referentie; geen nieuwe bronpublicatie."})

    data = {
        "schema_version": SCHEMA_VERSION, "dataset_version": DATASET_VERSION, "generated": "2026-11-07",
        "sources": [{
            "id": SOURCE, "title": "Splitsingsakte 2006, tekenblad 01 Begane grond (Rectificatie ondersplitsingstekening woningen + bergingen)",
            "document": "1050_96739052_Splitsingsakte_+_tekeningen.pdf", "page": 81, "drawing_sheet": "01",
            "author": "W. Grandia BV, project 2273", "native_size_px": list(NATIVE), "dpi": 200, "raster_only": True,
            "scan_sha256": scan_sha, "pdf_extract_sha256": pdf_sha,
            "privacy_class": "private_deed_drawing", "publish_native_raster": False,
            "note": "Native raster blijft lokaal; repo bevat alleen afgeleide geometrie en eerder gepubliceerde webafbeeldingen."}] + EXTRA_SOURCES,
        "calibrations": [{
            "id": CAL, "frame_id": FRAME, "model": "nominal_scale", "m_per_px_x": M_PER_PX[0], "m_per_px_y": M_PER_PX[1],
            "basis": "Schaal 1:200 hoofdplan (titelblok) x 200 dpi plaatsing in PDF",
            "control_points": [], "residuals": None, "uncertainty_m": None, "uncertainty_status": "unknown",
            "status": "nominal_unverified", "excludes": "SITUATIE-inzet 1:1000 niet van toepassing",
            "available_controls": "Blad bevat schaalbalk 0–10 m (1:200) en een cm-liniaal 0–5 cm linksboven; nog niet als controlepunten gemeten."}],
        "frames": [{"id": FRAME, "source_id": SOURCE, "floor_id": FLOOR, "unit": "px_native", "width_px": NATIVE[0],
                    "height_px": NATIVE[1], "axis_x": "right", "axis_y": "down",
                    "orientation": "scan_as_is_not_north_up", "calibration_ids": [CAL]}],
        "floors": [{"id": "BG", "name": "Begane grond", "level": 0, "source_ids": [SOURCE]}],
        "regions": regions, "reference_overlays": overlays,
        "objects": B.objects, "vertices": B.vertices, "edges": B.edges, "labels": B.labels,
        "connections": B.connections,
        "legal_splits": LEGAL_SPLITS,
        "legal_split_ui": {"enabled": True,
                           "reason": "Gedeeltelijk: lidmaatschap per ruimte afgeleid uit indexnummers 179/180 op de tekening + MVGM-stukken (A-179 Winkels, A-180 Woningen) en akte-tekst; splitsingsgrenzen zelf niet als lijn getekend. Hoofdsplitsingstekening niet gevonden. Zekerheid per ruimte zichtbaar."},
        "memberships": memberships(B),
        "legacy_links": B.legacy,
        "coverage": {"complete": False,
                     "scope": "BG: twee gemeenschappelijke kernen + 1 aangrenzende bedrijfsruimte; overige BG en 1e–4e: zie data/inventory/tile_register.json",
                     "region_px": list(bg_core.REGION_PX), "floors_covered": ["BG (deels)"],
                     "traced": ["ruimtegrenzen (hartlijn/binnenlijn)", "trap-ruimten + looplijnsymbolen", "liftschachten + kooisymbool",
                                "gevellijnen (deel)", "gevelwand dubbele lijn (Kiel noord)", "kozijnstroken (3)",
                                "kolommen binnen regio's (auto-detectie)", "ruimtelabels + indexkandidaat 180",
                                "kandidaat-openingen (2, geen deur getekend)", "hedendaags gebruik apart (containerruimte→fietsenberging)"],
                     "not_traced": ["wanddikte binnenwanden", "afzonderlijke traptreden (niet getekend in deze kernen)",
                                    "deuren/draaibogen (niet getekend in bekeken BG-tiles)", "hydrofoor-contour (gestippeld)",
                                    "inhoud GEM.-vakken", "grote bedrijfsruimte naast Schans-kern",
                                    "alle overige BG-delen en alle delen van 1e–4e verdieping"]},
        "review_log": [
            {"date": "2026-11-07", "by": "Grok Bot (executor)", "action": "pilot trace v0.1 (Schans-kern)", "status": "needs_human_review"},
            {"date": "2026-11-07", "by": "Grok Bot (executor)", "action": "fase 2b: regio Kiel + bouwdetails + kolommen + juridische lidmaatschappen", "status": "needs_human_review"}],
    }
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "pilot", "pilot_data.js"), "w") as f:
        f.write("// gegenereerd door model/tools/build_model.py\nwindow.PILOT_DATA = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    if crop_out and A is not None:
        write_review_images(scan_path, data, crop_out)
    return data


def write_review_images(scan_path, data, outdir):
    from PIL import Image, ImageDraw
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs(outdir, exist_ok=True)
    full = Image.open(scan_path).convert("L")
    P = {v["id"]: (v["x_px"], v["y_px"]) for v in data["vertices"]}
    for reg in data["regions"]:
        x0, y0, x1, y1 = reg["region_px"]
        crop = full.crop((x0, y0, x1, y1))
        crop.save(os.path.join(outdir, f"src_p81_{reg['id']}.png"))
        s = 2
        base = crop.convert("RGB").resize((crop.width * s, crop.height * s))
        ov = base.copy()
        d = ImageDraw.Draw(ov, "RGBA")
        T = lambda v: ((P[v][0] - x0) * s, (P[v][1] - y0) * s)  # noqa: E731
        col = {"stair": (220, 40, 40), "lift_shaft": (40, 90, 220), "unknown": (150, 150, 150), "commercial_unit": (255, 200, 0)}
        objs = [o for o in data["objects"] if o.get("region_id") == reg["id"]]
        for o in objs:
            if o["class"] == "space":
                d.polygon([T(v) for v in o["geometry"]["rings"][0]], fill=col.get(o["kind"], (20, 160, 80)) + (45,))
        for o in objs:
            if o["class"] == "element" and o["geometry"]["type"] == "Polygon":
                c = (200, 0, 200, 255) if o["kind"] == "column" else (0, 150, 255, 255)
                d.polygon([T(v) for v in o["geometry"]["rings"][0]], outline=c, fill=c[:3] + (70,))
            elif o["geometry"]["type"] == "LineString":
                d.line([T(v) for v in o["geometry"]["vertices"]], fill=(0, 120, 255, 220), width=3)
        E = {e["id"]: e for e in data["edges"]}
        for o in objs:
            if o["class"] != "space":
                continue
            for eid in o["edge_ids"]:
                e = E[eid]
                f = (e["ink_support"] or {}).get("fraction", 0)
                c = (255, 0, 255, 230) if e["role"] == "virtual_opening" else ((0, 170, 0, 230) if f >= 0.9 else (255, 140, 0, 230))
                d.line([T(e["v"][0]), T(e["v"][1])], fill=c, width=3)
        for o in objs:
            if o["class"] == "space":
                ring = [T(v) for v in o["geometry"]["rings"][0]]
                cx, cy = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
                d.text((cx - 20, cy), o["id"].split("_", 3)[-1], fill=(0, 0, 0, 255))
        combo = Image.new("RGB", (base.width * 2 + 10, base.height), "white")
        combo.paste(base, (0, 0))
        combo.paste(ov, (base.width + 10, 0))
        combo.save(os.path.join(outdir, f"compare_p81_{reg['id']}.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", default="/workspace/vve-source-audit/page-81.png")
    ap.add_argument("--pdf", default="/workspace/exports/Kadastertekeningen_Van_Speijk_2006_BG-tm-4e.pdf")
    ap.add_argument("--crop-out", default=os.path.join(ROOT, "pilot", "local"))
    a = ap.parse_args()
    data = build(a.scan, a.crop_out, a.pdf)
    weak = [e for e in data["edges"] if e["ink_support"] and e["role"] not in ("virtual_opening", "element_outline")
            and e["ink_support"]["fraction"] < 0.9]
    print(OUT, len(data["objects"]), "objects", len(data["edges"]), "edges;", len(weak), "space edges ink<0.9")
    for e in weak:
        print("  weak", e["id"], e["ink_support"])
