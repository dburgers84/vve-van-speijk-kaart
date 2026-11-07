#!/usr/bin/env python3
"""Bouw de pilotdataset (schema vve-plan v2) uit de handmatige trace + lokale bronscan.

Gebruik:  python3 model/tools/build_pilot.py [--scan PAD_NAAR_page-81.png]

- Leest de native bronpagina ALLEEN lokaal (nooit in de repo) om per edge een
  inktsteun-maat te berekenen (aandeel samplepunten met inkt binnen 3 px).
- Schrijft model/data/pilot-bg-core.v2.json en model/pilot/pilot_data.js.
- Schrijft, als --crop-out is gezet, een lokale bronuitsnede + vergelijkingsbeeld
  (buiten de repo of in model/pilot/local/, dat door .gitignore is uitgesloten).
"""
import argparse, hashlib, json, math, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pilot_trace_bg_core as T  # noqa: E402

SCHEMA_VERSION = "vve-plan/2.0.0"
DATASET_VERSION = "pilot-bg-core-0.1.0"
FLOOR = "BG"
FRAME = "frm_p81_native"
SOURCE = "src_akte2006_p81"
NATIVE = (7118, 10099)
M_PER_PX = (0.025399999806400928, 0.025399999249508854)  # nominaal 1:200 @200dpi
SOURCE_SHA256_PDF_EXTRACT = None  # ingevuld uit --pdf indien aanwezig
PILOT_BBOX = (150, 4650, 1050, 5600)  # bronuitsnede voor review (native px)


def oid(prefix, key):
    # stabiel, niet afgeleid van positie: prefix + vaste sleutel uit trace
    return f"{prefix}_bg_core_{key}"


def ink_support(A, p, q, r=3):
    if A is None:
        return None
    (x1, y1), (x2, y2) = p, q
    n = max(2, int(math.hypot(x2 - x1, y2 - y1)))
    hits = 0
    gaps, cur = [], 0
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
    return {"radius_px": r, "fraction": round(hits / (n + 1), 3),
            "max_gap_px": max(gaps) if gaps else 0}


def build(scan_path=None, crop_out=None, pdf_path=None):
    A = None
    scan_sha = None
    if scan_path and os.path.exists(scan_path):
        from PIL import Image
        import numpy as np
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(scan_path).convert("L")
        assert im.size == NATIVE, im.size
        A = np.array(im) < 128
        scan_sha = hashlib.sha256(open(scan_path, "rb").read()).hexdigest()
    pdf_sha = None
    if pdf_path and os.path.exists(pdf_path):
        pdf_sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()

    W, H = NATIVE
    vertices = []
    vid = {}
    for k, (x, y) in T.VERTICES.items():
        vid[k] = oid("v", k)
        vertices.append({"id": vid[k], "frame_id": FRAME, "floor_id": FLOOR,
                         "x_px": x, "y_px": y,
                         "x_rel": round(x / W, 8), "y_rel": round(y / H, 8),
                         "positional_tolerance_px": 4,
                         "evidence": {"source_id": SOURCE, "method": "visual_trace_2x_grid+ink_profile"}})
    pos = T.VERTICES

    edges, ekey = [], {}

    def edge_for(a, b):
        k = tuple(sorted((a, b)))
        if k in ekey:
            return ekey[k]
        role = T.EDGE_ROLES.get(k) or T.EDGE_ROLES.get((k[1], k[0])) or "wall_drawn"
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = (x2 - x1), (y2 - y1)
        length_px = math.hypot(dx, dy)
        ink = ink_support(A, pos[a], pos[b])
        if role == "virtual_opening":
            dim = {"status": "unknown", "length_m": None, "uncertainty_m": None,
                   "uncertainty_status": "unknown", "method": None, "calibration_ref": None,
                   "source_text": None, "source_ref": None,
                   "note": "Virtuele grens (kandidaat-opening); bron toont onderbroken stippellijn, geen massieve wand; eindpunten niet scherp. Inktsteun telt stippels mee."}
        else:
            lm = math.hypot(dx * M_PER_PX[0], dy * M_PER_PX[1])
            dim = {"status": "derived", "length_m": round(lm, 2), "uncertainty_m": None,
                   "uncertainty_status": "unknown", "method": "nominal_scale_px_length",
                   "calibration_ref": "cal_p81_nominal", "source_text": None, "source_ref": None,
                   "note": "Nominaal 1:200@200dpi; scanvervorming ongetoetst; geen bronmaat op tekening gevonden."}
        e = {"id": f"e_bg_core_{k[0]}_{k[1]}", "frame_id": FRAME, "floor_id": FLOOR,
             "v": [vid[a], vid[b]], "role": role, "length_px": round(length_px, 2),
             "dimension": dim, "ink_support": ink,
             "trace_quality": (None if ink is None else ("not_applicable" if role == "virtual_opening"
                               else ("ink_confirmed" if ink["fraction"] >= 0.9 else "partial_ink"))),
             "evidence": {"source_id": SOURCE, "method": "visual_trace_2x_grid+ink_profile"}}
        edges.append(e)
        ekey[k] = e["id"]
        return e["id"]

    objects, labels, okey = [], [], {}
    for key, kind, ring, lit, bbox, cert in T.SPACES:
        o_id = oid("obj", key)
        okey[key] = o_id
        eids = [edge_for(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]
        lab_ids = []
        if lit is not None:
            l_id = oid("lbl", key)
            lab_ids.append(l_id)
            labels.append({"id": l_id, "literal_text": lit, "normalized_text": lit.lower(),
                           "category": "space_name", "bbox_px": list(bbox), "frame_id": FRAME,
                           "assigned_object_ids": [o_id],
                           "certainty": "source" if cert == "source_label" else "probable",
                           "evidence": {"source_id": SOURCE, "method": "visual_read_no_ocr"}})
        objects.append({"id": o_id, "revision": 1, "floor_id": FLOOR, "frame_id": FRAME,
                        "kind": kind, "class": "space",
                        "display_name": lit or f"Onbenoemde ruimte ({key})",
                        "geometry": {"type": "Polygon", "rings": [[vid[v] for v in ring]]},
                        "edge_ids": eids, "label_ids": lab_ids,
                        "certainty": "unresolved" if cert == "unresolved" else ("probable" if cert != "source_label" else "source"),
                        "review_status": "needs_review",
                        "evidence": {"source_id": SOURCE, "method": "visual_trace_2x_grid+ink_profile",
                                     "note": "Polygonen op getekende lijnhartlijnen; wanddikte niet afgetrokken."}})
    for key, kind, seq, note in T.LINES:
        o_id = oid("obj", key)
        okey[key] = o_id
        objects.append({"id": o_id, "revision": 1, "floor_id": FLOOR, "frame_id": FRAME,
                        "kind": kind, "class": "linear_feature", "display_name": note,
                        "geometry": {"type": "LineString", "vertices": [vid[v] for v in seq]},
                        "edge_ids": [], "label_ids": [], "certainty": "probable",
                        "review_status": "needs_review",
                        "evidence": {"source_id": SOURCE, "method": "visual_trace_2x_grid"}})
    for i, (lit, cat, bbox, assigned, cert, note) in enumerate(T.EXTRA_LABELS):
        l_id = f"lbl_bg_core_x{i:02d}"
        labels.append({"id": l_id, "literal_text": lit, "normalized_text": lit.lower(),
                       "category": cat, "bbox_px": list(bbox), "frame_id": FRAME,
                       "assigned_object_ids": [okey[a] for a in assigned],
                       "certainty": cert, "note": note,
                       "evidence": {"source_id": SOURCE, "method": "visual_read_no_ocr"}})
        for a in assigned:
            next(o for o in objects if o["id"] == okey[a])["label_ids"].append(l_id)

    connections = []
    for cid, kind, (a, b), spaces, cert, note in T.CONNECTIONS:
        connections.append({"id": f"conn_bg_core_{cid}", "kind": kind, "edge_id": ekey[tuple(sorted((a, b)))],
                            "connects": [okey[s] for s in spaces], "certainty": cert,
                            "door_leaf_drawn": False, "swing": None, "note": note,
                            "evidence": {"source_id": SOURCE, "method": "visual+ink_gap"}})

    legacy = [{"legacy_system": "svg_v2_common_json", "legacy_id": lid, "object_id": okey[k],
               "relation": rel, "certainty": "uncertain" if rel == "uncertain" else "probable",
               "note": "Koppeling op functie+label; ligging in oude SVG-coördinaten niet geometrisch getoetst."}
              for lid, k, rel in T.LEGACY]

    data = {
        "schema_version": SCHEMA_VERSION,
        "dataset_version": DATASET_VERSION,
        "generated": str(date.today()),
        "sources": [{
            "id": SOURCE, "title": "Splitsingsakte 2006, tekenblad 01 Begane grond (Rectificatie ondersplitsingstekening woningen + bergingen)",
            "document": "1050_96739052_Splitsingsakte_+_tekeningen.pdf", "page": 81,
            "drawing_sheet": "01", "author": "W. Grandia BV, project 2273",
            "native_size_px": list(NATIVE), "dpi": 200, "raster_only": True,
            "scan_sha256": scan_sha, "pdf_extract_sha256": pdf_sha,
            "privacy_class": "private_deed_drawing", "publish_native_raster": False,
            "note": "Native raster blijft lokaal; repo bevat alleen afgeleide geometrie en eerder gepubliceerde webafbeeldingen."}],
        "calibrations": [{
            "id": "cal_p81_nominal", "frame_id": FRAME, "model": "nominal_scale",
            "m_per_px_x": M_PER_PX[0], "m_per_px_y": M_PER_PX[1],
            "basis": "Schaal 1:200 hoofdplan (titelblok) x 200 dpi plaatsing in PDF",
            "control_points": [], "residuals": None, "uncertainty_m": None,
            "uncertainty_status": "unknown", "status": "nominal_unverified",
            "excludes": "SITUATIE-inzet 1:1000 niet van toepassing"}],
        "frames": [{"id": FRAME, "source_id": SOURCE, "floor_id": FLOOR, "unit": "px_native",
                    "width_px": NATIVE[0], "height_px": NATIVE[1], "axis_x": "right", "axis_y": "down",
                    "orientation": "scan_as_is_not_north_up", "calibration_ids": ["cal_p81_nominal"]}],
        "floors": [{"id": "BG", "name": "Begane grond", "level": 0, "source_ids": [SOURCE]}],
        "objects": objects, "vertices": vertices, "edges": edges, "labels": labels,
        "connections": connections,
        "legal_splits": [
            {"id": "ls_a2_ondersplitsing", "name": "Ondersplitsing appartementsrecht A-2 (woningen + bergingen)",
             "legal_reference": "Gemeente Dronten, appartementsrecht A-2; 176 rechten (85 woningen + 91 bergingen)",
             "parent_id": "ls_hoofdsplitsing", "status": "identified_in_source",
             "boundary_status": "unknown",
             "evidence": {"source_id": SOURCE, "method": "titelblok + akte p.2 visueel gelezen"}},
            {"id": "ls_hoofdsplitsing", "name": "Hoofdsplitsing (waarvan A-2 deel is)",
             "legal_reference": None, "parent_id": None, "status": "referenced_not_located",
             "boundary_status": "unknown",
             "evidence": {"source_id": SOURCE, "method": "afgeleid uit verwijzing 'appartementsrecht A-2'"}}],
        "legal_split_ui": {"enabled": False,
                           "reason": "Welke twee splitsingen de gebruiker bedoelt en hun grenzen op deze bladen zijn niet bewezen; hoofdsplitsingstekening niet gevonden."},
        "memberships": [{"object_id": o["id"], "split_id": "ls_a2_ondersplitsing", "relation": "unknown",
                         "certainty": "unknown", "evidence": None}
                        for o in objects if o["class"] == "space"],
        "legacy_links": legacy,
        "coverage": {"complete": False, "scope": "pilot: één gemeenschappelijke kern BG (Schans-zijde), bronregio px",
                     "region_px": list(PILOT_BBOX), "floors_covered": ["BG"],
                     "traced": ["ruimtegrenzen (hartlijn)", "trap-ruimten (2)", "liftschacht + kooisymbool",
                                "gevellijn (deel)", "ruimtelabels", "1 open doorgang"],
                     "not_traced": ["wanddikte/dubbele lijnen", "kozijnen/raamstroken gevel", "kolommen",
                                    "trap-treden afzonderlijk", "deurposities buiten entree-hal",
                                    "hydrofoor-contour (gestippeld)", "inhoud GEM.-vakken",
                                    "aangrenzende bedrijfsruimte (alleen label gezien, geen polygon)",
                                    "alle overige delen van alle verdiepingen"]},
        "review_log": [{"date": str(date.today()), "by": "Grok Bot (executor)",
                        "action": "pilot trace v0.1", "status": "needs_human_review"}],
    }
    out = os.path.join(ROOT, "data", "pilot-bg-core.v2.json")
    with open(out, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "pilot", "pilot_data.js"), "w") as f:
        f.write("// gegenereerd door model/tools/build_pilot.py\nwindow.PILOT_DATA = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    if crop_out and A is not None:
        write_review_images(scan_path, data, crop_out)
    return data, out


def write_review_images(scan_path, data, outdir):
    from PIL import Image, ImageDraw
    Image.MAX_IMAGE_PIXELS = None
    os.makedirs(outdir, exist_ok=True)
    x0, y0, x1, y1 = PILOT_BBOX
    crop = Image.open(scan_path).convert("L").crop(PILOT_BBOX)
    crop.save(os.path.join(outdir, "src_p81_bg_core_crop.png"))
    V = {v["id"]: (v["x_px"] - x0, v["y_px"] - y0) for v in data["vertices"]}
    s = 2
    base = crop.convert("RGB").resize((crop.width * s, crop.height * s))
    ov = base.copy()
    d = ImageDraw.Draw(ov, "RGBA")
    colors = {"stair": (220, 40, 40), "lift_shaft": (40, 90, 220), "unknown": (150, 150, 150)}
    for o in data["objects"]:
        if o["class"] != "space":
            continue
        ring = [(V[v][0] * s, V[v][1] * s) for v in o["geometry"]["rings"][0]]
        c = colors.get(o["kind"], (20, 160, 80))
        d.polygon(ring, fill=c + (45,))
    for e in data["edges"]:
        a, b = (V[e["v"][0]], V[e["v"][1]])
        f = (e["ink_support"] or {}).get("fraction", 0)
        col = (255, 0, 255, 230) if e["role"] == "virtual_opening" else ((0, 170, 0, 230) if f >= 0.9 else (255, 140, 0, 230))
        d.line([(a[0] * s, a[1] * s), (b[0] * s, b[1] * s)], fill=col, width=3)
    for o in data["objects"]:
        if o["class"] == "linear_feature":
            pts = [(V[v][0] * s, V[v][1] * s) for v in o["geometry"]["vertices"]]
            d.line(pts, fill=(0, 120, 255, 200), width=2)
    for k, (px, py) in V.items():
        d.ellipse([px * s - 4, py * s - 4, px * s + 4, py * s + 4], outline=(255, 0, 0, 255), width=2)
    for o in data["objects"]:
        if o["class"] != "space":
            continue
        ring = [V[v] for v in o["geometry"]["rings"][0]]
        cx = sum(p[0] for p in ring) / len(ring) * s
        cy = sum(p[1] for p in ring) / len(ring) * s
        d.text((cx - 20, cy), o["id"].replace("obj_bg_core_", ""), fill=(0, 0, 0, 255))
    combo = Image.new("RGB", (base.width * 2 + 10, base.height), "white")
    combo.paste(base, (0, 0))
    combo.paste(ov, (base.width + 10, 0))
    combo.save(os.path.join(outdir, "compare_p81_bg_core.png"))
    ov.save(os.path.join(outdir, "overlay_p81_bg_core.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", default="/workspace/vve-source-audit/page-81.png")
    ap.add_argument("--pdf", default="/workspace/exports/Kadastertekeningen_Van_Speijk_2006_BG-tm-4e.pdf")
    ap.add_argument("--crop-out", default=os.path.join(ROOT, "pilot", "local"))
    a = ap.parse_args()
    data, out = build(a.scan, a.crop_out, a.pdf)
    weak = [e for e in data["edges"] if e["ink_support"] and e["role"] != "virtual_opening" and e["ink_support"]["fraction"] < 0.9]
    print(out, len(data["objects"]), "objects", len(data["edges"]), "edges;", len(weak), "edges ink<0.9")
    for e in weak:
        print("  weak", e["id"], e["ink_support"])
