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
from traces import bg_core, bg_kiel, bg_segments  # noqa: E402

TRACES = [bg_core, bg_kiel]
SCHEMA_VERSION = "vve-plan/2.1.0"
DATASET_VERSION = "bg-0.3.0"
FLOOR = "BG"
FRAME = "frm_p81_native"
SOURCE = "src_akte2006_p81"
CAL = "cal_p81_controls"
NATIVE = (7118, 10099)
# ---- kalibratie (zie data/inventory/calibration_p81.json; gemeten 2026-11-07 op de lokale scan)
# Schaalbalk 'Begane grond Schaal 1 a 200' (linksboven in het kader van het hoofdplan): 0 m bij y=443.3, 10 m bij y=830.3 (x≈80), dus langs native y.
# cm-liniaal 'IN CM' (reproductiecontrole, langs native y): streepjes 0..5 cm bij y=477.27 ... 869.62 → 78.47 px/cm.
BAR_PX = (443.3, 830.3)
BAR_M = 10.0
RULER_PX_PER_CM = (869.62 - 477.27) / 5
M_BAR = BAR_M / (BAR_PX[1] - BAR_PX[0])            # 0.025840 m/px  (eigen schaalbalk tekening)
M_RULER = 2.0 / RULER_PX_PER_CM                       # 0.025488 m/px  (liniaal x opgegeven 1:200)
M_NOMINAL = 0.0254                                    # 1:200 @ 200 dpi (oude aanname)
M_ADOPT = round((M_BAR + M_RULER) / 2, 7)             # midden van beide controles
REL_U_Y = round(abs(M_BAR - M_RULER) / 2 / M_ADOPT, 4)  # halve spreiding tussen controles (~0,7 %)
GRID_PITCH_PX = {"x": 295.63, "y": 298.24}            # kolomstramien (auto-kolommen, mediaan-omgeving)
REL_ANISO = round(abs(GRID_PITCH_PX["y"] - GRID_PITCH_PX["x"]) / GRID_PITCH_PX["y"], 4)
REL_U_X = round(REL_U_Y + REL_ANISO, 4)               # x-as niet onafhankelijk gecontroleerd: ruimere marge
M_PER_PX = (M_ADOPT, M_ADOPT)
OUT = os.path.join(ROOT, "data", "bg.v2.json")
COLUMNS_JSON = os.path.join(ROOT, "data", "inventory", "columns_auto_all.json")
COLREVIEW_JSON = os.path.join(ROOT, "data", "inventory", "columns_review_p81.json")
SEG_JSON = os.path.join(ROOT, "data", "inventory", "bg_segments_p81.json")
REG_JSON = os.path.join(ROOT, "data", "inventory", "registration_plan_jpg.json")
INK_SUPPORT_THRESHOLD = 200  # zelfde drempel als segmentatie (dunne grijze lijnen tellen mee)
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


def dim_for(role, p, q, tol=(4, 4)):
    if role == "virtual_opening":
        return {"status": "unknown", "length_m": None, "uncertainty_m": None, "uncertainty_status": "unknown",
                "method": None, "calibration_ref": None, "source_text": None, "source_ref": None,
                "note": "Virtuele grens (kandidaat-opening); eindpunten niet scherp in bron."}
    dx, dy = q[0] - p[0], q[1] - p[1]
    lm = math.hypot(dx * M_PER_PX[0], dy * M_PER_PX[1])
    u = math.sqrt((dx * M_PER_PX[0] * REL_U_X) ** 2 + (dy * M_PER_PX[1] * REL_U_Y) ** 2
                  + (tol[0] ** 2 + tol[1] ** 2) * M_PER_PX[0] ** 2)
    return {"status": "derived", "length_m": round(lm, 2), "uncertainty_m": max(0.01, round(u, 2)), "uncertainty_status": "estimated",
            "method": "px_length x m_per_px (schaalbalk 0-10 m + cm-liniaal, y-as; x-as isotroop aangenomen)",
            "calibration_ref": CAL, "source_text": None, "source_ref": None,
            "note": "Afgeleid; geen maat op de tekening gevonden. Onzekerheid = schaalspreiding tussen schaalbalk en liniaal (y), "
                    "plus mogelijke anisotropie (x, niet onafhankelijk getoetst), plus aflees-/trace-tolerantie van beide eindpunten."}


LEGAL_SPLITS = [
    {"id": "ls_hoofdsplitsing", "name": "Hoofdsplitsing complex Van Speijk — VvE Van Speijk (Hoofdsplitsing)",
     "legal_reference": "Appartementsrechten A-179 (Winkels / commerciële ruimten) en A-180 (Woningen)",
     "rights": [{"id": "A-179", "name": "Winkels (commerciële ruimten)", "drawing_index": "179"},
                {"id": "A-180", "name": "Woningen (ondergesplitst)", "drawing_index": "180"}],
     "parent_id": None, "status": "identified_in_source", "boundary_status": "partial",
     "scope": "Hele complex: A-179 (winkels/commercieel) én A-180 (woningen). Gebieden zijn AFGELEID uit labels/indexnummers; buitengrenzen tussen A-179 en A-180 niet als lijn getekend gevonden.",
     "evidence": {"source_id": "src_mvgm_hoofdsplitsing_stukken", "method": "tekst gelezen (pdftotext): begroting 2025 + jaarrekening 2023 hoofdsplitsing"}},
    {"id": "ls_ondersplitsing_woningen", "name": "Ondersplitsing — VvE Van Speijk (Woningen): 85 woonappartementen + 91 bergingen",
     "legal_reference": "Akte van ondersplitsing 2006 (176 rechten). Titelblok tekening noemt 'appartementsrecht A-2'; relatie tot A-180 (MVGM) nog niet opgehelderd.",
     "rights": [], "parent_id": "ls_hoofdsplitsing", "status": "identified_in_source", "boundary_status": "partial",
     "nested_in_right": "A-180",
     "scope": "Genest BINNEN A-180 van de hoofdsplitsing (geen naastgelegen gebied). Alleen ruimtes binnen A-180 kunnen erin vallen; A-179 en de arcering vallen erbuiten.",
     "unresolved": ["Titelblok splitsingstekening noemt 'appartementsrecht A-2'; MVGM noemt het woningen-recht A-180. Relatie niet opgehelderd (geen bron gevonden)."],
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


_AKTE_O = "Akte ondersplitsing 2006 (visueel gelezen): entrees, liften/trappen, technische ruimten behoren tot de gemeenschap"


def seg_legal(M, key, kind, h179):
    """Afgeleide lidmaatschappen voor gesegmenteerde vakken; leeg = unknown."""
    H, O = "ls_hoofdsplitsing", "ls_ondersplitsing_woningen"
    out = {}
    if kind.startswith("commercial"):
        out[H] = ("private", "A-179", "probable" if h179 else "uncertain",
                  "Indexnummer 179 staat in dit vak; A-179 = Winkels (commerciële ruimten) volgens MVGM-begroting hoofdsplitsing" if h179 else
                  "Label 'bedrijfs-ruimte'; 179 staat één keer per blok (niet in dit vak); A-179 = commerciële ruimten (MVGM)")
        out[O] = ("excluded", None, "uncertain", "Valt onder A-179; ondersplitsing is genest binnen A-180 (woningen + bergingen)")
    core = next((c for c, ks in M.CORES.items() if key in ks), None)
    if core in M.CORE_HAS_180:
        has = M.CORE_HAS_180[core] == key
        if kind != "technical_room":
            out[H] = ("private", "A-180", "probable" if has else "uncertain",
                      "Omcirkeld 180 staat in dit vak; A-180 = Woningen (MVGM)" if has else f"Zelfde woonkern ({core}) als omcirkeld 180; eigen indexnummer ontbreekt")
            strong = kind in ("entrance_hall", "stair", "lift_shaft", "hall")
            out[O] = ("common", None, "probable" if strong else "uncertain",
                      _AKTE_O if strong else "Vak in woonkern; gemeenschappelijk niet per vak bewezen")
    return out


def memberships(B, seg_meta=()):
    out = []

    def emit(oid_, given):
        for sp in LEGAL_SPLITS:
            if sp["id"] in given:
                rel, right, cert, note = given[sp["id"]]
                out.append({"object_id": oid_, "split_id": sp["id"], "relation": rel, "right_id": right,
                            "certainty": cert, "evidence": {"source_id": sp["evidence"]["source_id"], "method": "label+akte/MVGM-tekst (afgeleid)", "note": note}})
            else:
                out.append({"object_id": oid_, "split_id": sp["id"], "relation": "unknown", "right_id": None,
                            "certainty": "unknown", "evidence": None})
    for T in TRACES:
        legal = getattr(T, "LEGAL", {})
        for key, *_ in T.SPACES:
            emit(f"obj_{T.PREFIX}_{key}", {m[0]: m[1:] for m in legal.get(key, [])})
    for oid_, given in seg_meta:
        emit(oid_, given)
    return out


class Builder:
    def __init__(self, A, old_ink):
        self.A, self.old_ink = A, old_ink
        self.vertices, self.vid, self.pos, self.tol = [], {}, {}, {}
        self.edges, self.ekey = [], {}
        self.objects, self.labels, self.connections, self.legacy = [], [], [], []

    def vertex(self, vkey, xy, method="visual_trace_2x_grid+ink_profile", tol=4):
        if vkey in self.vid:
            return self.vid[vkey]
        x, y = xy
        W, H = NATIVE
        self.vid[vkey] = vkey
        self.pos[vkey] = (x, y)
        self.tol[vkey] = tol
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
        tq = None if ink is None else ("not_applicable" if role in ("virtual_opening", "virtual_boundary")
                                       else ("ink_confirmed" if ink["fraction"] >= 0.9 else "partial_ink"))
        self.edges.append({"id": eid, "frame_id": FRAME, "floor_id": FLOOR, "v": [a, b], "role": role,
                           "length_px": round(math.hypot(q[0] - p[0], q[1] - p[1]), 2),
                           "dimension": dim_for(role, p, q, (self.tol[a], self.tol[b])), "ink_support": ink, "trace_quality": tq,
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

    def _column(self, prefix, key, region_id, c, verdict, note):
        h = c["size_px"] / 2
        pts = [(c["x"] - h, c["y"] - h), (c["x"] + h, c["y"] - h), (c["x"] + h, c["y"] + h), (c["x"] - h, c["y"] + h)]
        vids = [self.vertex(f"v_{prefix}_{key}_{i}", xy, method="auto_detect_hollow_square", tol=2) for i, xy in enumerate(pts)]
        unc = verdict == "uncertain"
        self.polygon_object(f"obj_{prefix}_{key}", prefix, vids, lambda a, b: "element_outline",
                            kind="column", **{"class": "element"}, region_id=region_id,
                            display_name=("Kolomkandidaat (onzeker" + (": " + note if note else "") + ")") if unc
                            else f"Kolom (getekend vierkant, {c['size_px']} px)",
                            certainty="uncertain" if unc else "probable", review_status="reviewed",
                            evidence={"source_id": SOURCE, "method": "auto_detect_hollow_square + visuele controle contactblad",
                                      "note": f"detector side_min={c.get('side_min')}; kandidaat #{c['i']} in data/inventory/columns_review_p81.json; "
                                              "vierkant symbool zonder legenda: betekenis 'kolom' is interpretatie, geen materiaal/maat vermeld"})

    def add_columns(self, T, cols):
        """Kolommen binnen een handmatige regio (ids kolomNN blijven als in fase 2b)."""
        x0, y0, x1, y1 = T.REGION_PX
        n = 0
        boxes = [l["bbox_px"] for l in self.labels]
        for c in sorted(cols, key=lambda c: (c["y"], c["x"])):
            if not (x0 <= c["x"] <= x1 and y0 <= c["y"] <= y1):
                continue
            if any(b[0] - 4 <= c["x"] <= b[2] + 4 and b[1] - 4 <= c["y"] <= b[3] + 4 for b in boxes):
                continue  # valt binnen tekstlabel: letter, geen kolom
            n += 1
            c["_used"] = True
            if c["verdict"] == "rejected":
                continue
            self._column(T.PREFIX, f"kolom{n:02d}", T.REGION_ID, c, c["verdict"], c.get("note"))
        return n

    def add_global_columns(self, cols, prefix, region_id):
        n = 0
        for c in cols:
            if c.get("_used") or c["verdict"] == "rejected":
                continue
            self._column(prefix, f"c{c['i']:03d}", region_id, c, c["verdict"], c.get("note"))
            n += 1
        return n

    def add_segments(self, M, seg):
        """Semi-automatische segmenten (tools/segment_bg.py) + arceringen."""
        P = M.PREFIX
        okey = {}
        ELEMENT_KINDS = {"wall_band": "Wandstrook tussen dubbele lijnen (getekende wanddikte)",
                         "round_element_part": "Deel rond element (betekenis onbekend)"}
        NAMES = {"commercial_unit": "bedrijfs-ruimte", "commercial_multi_unresolved": "Bedrijfsruimte(n) — onderverdeling onopgelost",
                 "commercial_large_region_unresolved": "Grote bedrijfsruimte — aantal eenheden onopgelost",
                 "unlabeled_space": "Onbenoemd vak", "unresolved_space": "Vak met onbekende functie",
                 "cross_marked_cell": "Vak met kruis (X)", "passage_or_overhang_unresolved": "Strook De Kajuit (passage/overbouwing?)"}
        cu = getattr(M, "CURRENT_USE", {})
        for key, seed, kind, lit, lbb, note, bhits, h179 in M.SEEDS:
            g = seg["segments"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="auto_segment_inner_face", tol=3) for i, xy in enumerate(g["polygon"])]
            is_el = kind in ELEMENT_KINDS
            if kind == "commercial_unit":
                cert = "probable"
            elif kind.endswith("unresolved") or kind in ("unlabeled_space", "unresolved_space", "cross_marked_cell"):
                cert = "unresolved"
            else:
                cert = "probable"
            fields = {"kind": kind, "class": "element" if is_el else "space", "region_id": M.REGION_ID,
                      "display_name": (ELEMENT_KINDS.get(kind) or ("bedrijfs-ruimte" if kind == "commercial_unit" else None)
                                       or NAMES.get(kind) or lit or kind),
                      "certainty": cert, "review_status": "needs_review",
                      "evidence": {"source_id": SOURCE, "method": "auto_segment_inner_face (tools/segment_bg.py) + visuele review",
                                   "boundary": "binnenzijde getekende lijn",
                                   "note": " ".join(x for x in [(note or "").rstrip(".") + ("." if note else ""), "" if is_el else "Grens = binnenzijde van de getekende lijn (wandstrook ligt ertussen)."] if x)}}
            if not is_el:
                fields["source_label_text"] = lit
                fields["current_use"] = None
                if key in cu:
                    val, src_, c_ = cu[key]
                    fields["current_use"] = {"value": val, "source": src_, "certainty": c_}
            self.polygon_object(o_id, P, vids, (lambda a, b: "element_outline") if is_el else (lambda a, b: "wall_inner_face"), **fields)
            if lit and lbb:
                self.label(f"lbl_{P}_{key}", lit, "street_name" if kind.startswith("passage") else "space_name", lbb, [o_id], "source",
                           "Visueel gelezen")
            for j, (x0, y0, x1, y1, sc) in enumerate(bhits):
                self.label(f"lbl_{P}_{key}_b{j}", "bedrijfs-ruimte", "space_name", (x0, y0, x1, y1), [o_id], "probable",
                           f"Gevonden met template-matching (score {sc}); tekst gedraaid op blad")
            for j, (x, y) in enumerate(h179):
                self.label(f"lbl_{P}_{key}_i179_{j}", "179", "index_number", (x, y, x + 75, y + 150), [o_id], "source",
                           "Indexnummer 179 (groot, visueel bevestigd); staat één keer per blok, niet in elke bedrijfsruimte")
            if key in M.IDX180:
                self.label(f"lbl_{P}_{key}_i180", "180", "index_number_candidate", M.IDX180[key], [o_id], "probable",
                           "Omcirkeld 180 in dit vak (visueel)")
        for key, seed, note in M.HATCH_SEEDS:
            g = seg["hatch"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="hatch_density_outline", tol=8) for i, xy in enumerate(g["polygon"])]
            self.polygon_object(o_id, P, vids, lambda a, b: "virtual_boundary", kind="not_in_split_area", **{"class": "space"},
                                region_id=M.REGION_ID, display_name="Gearceerd: niet in de splitsing betrokken",
                                source_label_text=None, current_use=None, certainty="probable", review_status="needs_review",
                                evidence={"source_id": SOURCE, "method": "inktdichtheid arcering (tools/segment_bg.py)", "boundary": "buitenrand arcering (±8 px)",
                                          "note": note + ". Binnen de arcering staan o.a. 'bedrijfs-ruimte'-labels; vlak niet verder onderverdeeld."})
        self.label(f"lbl_{P}_legend_hatch", "= niet in de splitsing betrokken", "note", M.LEGEND_BBOX,
                   [okey[k] for k, *_ in M.HATCH_SEEDS if k in okey], "source", "Legenda op het blad (arcering)")
        return okey


def coverage_block(B, seg, cols):
    from collections import Counter
    kinds = Counter(o["kind"] for o in B.objects if o.get("region_id") == bg_segments.REGION_ID)
    unres = sum(v for k, v in kinds.items() if k.endswith("unresolved") or k in ("unlabeled_space", "unresolved_space", "cross_marked_cell"))
    return {"complete": False,
            "scope": "Alleen BG (blad p.81). Handmatig: 2 kernen + 1 bedrijfsruimte. Semi-automatisch: overige gesloten vakken van het BG-plan "
                     "(binnenzijde lijn), arceringen, wandstroken en visueel gecontroleerde kolomsymbolen. 1e-4e verdieping: nog niet getraceerd.",
            "floors_covered": ["BG (grotendeels, deels onopgelost)"],
            "counts": {"segment_kinds": dict(sorted(kinds.items())), "unresolved_or_unlabeled_segments": unres,
                       "column_candidates_p81": len(cols), "columns_rejected": sum(c["verdict"] == "rejected" for c in cols),
                       "columns_uncertain": sum(c["verdict"] == "uncertain" for c in cols)},
            "traced": ["handmatig: kern Schans-zijde + kern De Kiel + 1 bedrijfsruimte (hartlijn/binnenlijn)",
                       "semi-automatisch: alle gesloten vakken van het BG-plan met zaadpunt (binnenzijde getekende lijn)",
                       "woonkernen A, B, C en kern E (labels visueel gelezen)", "3 expeditiegangen", "strook De Kajuit (onopgelost)",
                       "2 arceringen 'niet in de splitsing betrokken'", "wandstroken tussen dubbele lijnen (getekende wanddikte)",
                       "kolomsymbolen (visueel gecontroleerd; 10 afgekeurd, 12 onzeker)", "indexnummers 179 (5x) en omcirkeld 180 (5x)",
                       "hedendaags gebruik apart (alle containerruimtes -> fietsenberging, door gebruiker bevestigd)"],
            "not_traced": ["onderverdeling van bedrijfsruimtes waar tussenwanden deels/niet getekend zijn (3 'multi' + 3 'groot' vakken)",
                           "binnen de arceringen (niet in splitsing)", "deuren/draaibogen (niet getekend op BG)",
                           "traptreden (in BG-kernen alleen looppijl/snijlijn; de eerder genoemde 'treden' bij de expeditiegang bleken korte dwarsstreepjes, geen treden)",
                           "korte dwarsstreepjes op veel lijnen (betekenis niet in legenda)", "straten/buitenruimte (alleen als labels gezien)",
                           "daken: niet op BG-blad (daken op blad 4e verdieping en daken)", "hydrofoor-contour (gestippeld)",
                           "1e, 2e, 3e en 4e verdieping/daken: niets getraceerd"]}


def build(scan_path=None, crop_out=None, pdf_path=None):
    A, scan_sha = None, None
    if scan_path and scan_path != "none" and os.path.exists(scan_path):
        from PIL import Image
        import numpy as np
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(scan_path).convert("L")
        assert im.size == NATIVE, im.size
        A = np.array(im) < INK_SUPPORT_THRESHOLD
        scan_sha = hashlib.sha256(open(scan_path, "rb").read()).hexdigest()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    old_ink = {e["id"]: e.get("ink_support") for e in old.get("edges", [])}
    if scan_sha is None:
        scan_sha = (old.get("sources") or [{}])[0].get("scan_sha256")
    pdf_sha = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest() if pdf_path and os.path.exists(pdf_path) \
        else (old.get("sources") or [{}])[0].get("pdf_extract_sha256")
    review = {(v["x"], v["y"]): v for v in json.load(open(COLREVIEW_JSON))["verdicts"]}
    cols = []
    for c in json.load(open(COLUMNS_JSON))["pages"]["81"]:
        v = review[(c["x"], c["y"])]
        cols.append(dict(c, i=v["i"], verdict=v["verdict"], note=v["note"]))
    cols.sort(key=lambda c: c["i"])
    seg = json.load(open(SEG_JSON))
    reg = json.load(open(REG_JSON)) if os.path.exists(REG_JSON) else None

    B = Builder(A, old_ink)
    regions, ncols = [], {}
    for T in TRACES:
        B.add_trace(T)
        ncols[T.REGION_ID] = B.add_columns(T, cols)
        regions.append({"id": T.REGION_ID, "name": T.REGION_NAME, "region_px": list(T.REGION_PX), "floor_id": FLOOR,
                        "columns_from_detector": ncols[T.REGION_ID], "method": "handmatige trace (hartlijn/binnenlijn)"})
    M = bg_segments
    okey = B.add_segments(M, seg)
    ncols[M.REGION_ID] = B.add_global_columns(cols, "bg_col", M.REGION_ID)
    regions.append({"id": M.REGION_ID, "name": M.REGION_NAME, "region_px": list(M.REGION_PX), "floor_id": FLOOR,
                    "columns_from_detector": ncols[M.REGION_ID], "method": "semi-automatische segmentatie (binnenzijde lijn) + visuele review",
                    "local_crop_scale": 0.25})
    for rg in regions:  # passende fit: bbox van de objecten in de regio
        pts = [B.pos[v] for o in B.objects if o.get("region_id") == rg["id"]
               for v in (o["geometry"]["rings"][0] if o["geometry"]["type"] == "Polygon" else o["geometry"].get("vertices", []))]
        rg["fit_px"] = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)]
    space_ids = {o["id"] for o in B.objects if o["class"] == "space"}
    seg_meta = []
    for key, seed, kind, lit, lbb, note, bhits, h179 in M.SEEDS:
        oid_ = okey.get(key)
        if oid_ in space_ids:
            seg_meta.append((oid_, seg_legal(M, key, kind, h179)))
    for key, *_ in M.HATCH_SEEDS:
        if key in okey:
            seg_meta.append((okey[key], {"ls_hoofdsplitsing": ("excluded", None, "probable", "Arcering = 'niet in de splitsing betrokken' (legenda op het blad)"),
                                         "ls_ondersplitsing_woningen": ("excluded", None, "probable", "Arcering = 'niet in de splitsing betrokken' (legenda op het blad)")}))

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
            "basis": "Gemiddelde van twee controles langs native y: eigen schaalbalk hoofdplan ('Begane grond Schaal 1 a 200', 0-10 m) en cm-liniaal x opgegeven schaal 1:200",
            "status": "controls_checked_one_axis", "uncertainty_m": None, "uncertainty_status": "estimated",
            "rel_uncertainty": {"x": REL_U_X, "y": REL_U_Y},
            "axis_status": {"y": "checked_against_scale_bar_and_ruler",
                            "x": "assumed_isotropic_not_independently_verified"},
            "control_points": [
                {"id": "bar_0m", "kind": "scale_bar_tick", "x_px": 80, "y_px": BAR_PX[0], "value_m": 0.0, "reading_tolerance_px": 1.5},
                {"id": "bar_10m", "kind": "scale_bar_tick", "x_px": 80, "y_px": BAR_PX[1], "value_m": 10.0, "reading_tolerance_px": 1.5},
                {"id": "ruler_0cm", "kind": "ruler_tick", "x_px": 433, "y_px": 477.27, "value_cm": 0},
                {"id": "ruler_5cm", "kind": "ruler_tick", "x_px": 433, "y_px": 869.62, "value_cm": 5}],
            "checks": {
                "m_per_px_scale_bar_0_10m": round(M_BAR, 6), "m_per_px_ruler_x_1to200": round(M_RULER, 6),
                "m_per_px_nominal_1to200_200dpi": M_NOMINAL, "adopted": M_ADOPT,
                "bar_vs_nominal_pct": round((M_BAR / M_NOMINAL - 1) * 100, 2), "ruler_vs_nominal_pct": round((M_RULER / M_NOMINAL - 1) * 100, 2),
                "adopted_vs_nominal_pct": round((M_ADOPT / M_NOMINAL - 1) * 100, 2),
                "bar_segments_px_per_2m": [78.5, 78.0, 79.0, 77.0, 74.5],
                "bar_segment_note": "Segmenten van de balk zijn ongelijk (74,5-79 px per 2 m): plot-/scanonnauwkeurigheid in de balk zelf",
                "column_grid_pitch_px": GRID_PITCH_PX, "column_grid_anisotropy_pct": round(REL_ANISO * 100, 2),
                "column_grid_note": "Kolomstramien x 295,6 px vs y 298,2 px. Of het stramien vierkant is, is NIET bekend; daarom alleen als marge voor de x-as gebruikt, niet als correctie."},
            "residuals": None,
            "excludes": "SITUATIE-inzet 1:1000 (onderaan blad) niet gebruikt",
            "note": "Eerdere fase noemde alleen een balk bij de situatie; correctie: de 0-10 m balk staat linksboven IN het kader van het hoofdplan met tekst 'Begane grond Schaal 1 a 200' en hoort dus bij het hoofdplan. Alle bladen 82-85 hebben dezelfde soort balk + liniaal, ook alleen langs native y."}],
        "frames": [{"id": FRAME, "source_id": SOURCE, "floor_id": FLOOR, "unit": "px_native", "width_px": NATIVE[0],
                    "height_px": NATIVE[1], "axis_x": "right", "axis_y": "down",
                    "orientation": "scan_as_is_not_north_up", "calibration_ids": [CAL],
                    "north_arrow_px": {"x": 6150, "y": 4990, "note": "Noordpijl rechts op het blad (≈ native omhoog); niet gebruikt voor geometrie"}}],
        "floors": [{"id": "BG", "name": "Begane grond", "level": 0, "source_ids": [SOURCE]}],
        "regions": regions, "reference_overlays": overlays,
        "objects": B.objects, "vertices": B.vertices, "edges": B.edges, "labels": B.labels,
        "connections": B.connections,
        "legal_splits": LEGAL_SPLITS,
        "legal_split_ui": {"enabled": True,
                           "reason": "Gedeeltelijk: lidmaatschap per ruimte afgeleid uit indexnummers 179/180 op de tekening + MVGM-stukken (A-179 Winkels, A-180 Woningen) en akte-tekst; splitsingsgrenzen zelf niet als lijn getekend. Hoofdsplitsingstekening niet gevonden. Zekerheid per ruimte zichtbaar."},
        "memberships": memberships(B, seg_meta),
        "legacy_links": B.legacy,
        "coverage": coverage_block(B, seg, cols),
        "review_log": [
            {"date": "2026-11-07", "by": "Grok Bot (executor)", "action": "pilot trace v0.1 (Schans-kern)", "status": "needs_human_review"},
            {"date": "2026-11-07", "by": "Grok Bot (executor)", "action": "fase 2b: regio Kiel + bouwdetails + kolommen + juridische lidmaatschappen", "status": "needs_human_review"},
            {"date": "2026-11-07", "by": "Grok Bot (executor)", "action": "fase 3: kalibratiecontrole (schaalbalk+liniaal), BG-segmentatie, kolomreview, geneste splitsingsweergave", "status": "needs_human_review"}],
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
        cs = reg.get("local_crop_scale", 1)
        if cs != 1:
            crop = crop.resize((int(crop.width * cs), int(crop.height * cs)))
        crop.save(os.path.join(outdir, f"src_p81_{reg['id']}.png"))
        s = 2 if cs == 1 else cs
        base = full.crop((x0, y0, x1, y1)).convert("RGB").resize((int((x1 - x0) * s), int((y1 - y0) * s)))
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
    for e in weak[:10]:
        print("  weak", e["id"], e["ink_support"])
    if len(weak) > 10:
        print(f"  ... en {len(weak) - 10} meer (zie trace_quality in de dataset)")
