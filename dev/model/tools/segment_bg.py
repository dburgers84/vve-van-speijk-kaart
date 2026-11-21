#!/usr/bin/env python3
"""Semi-automatische segmentatie van de BG-ruimtes (akte 2006 p.81) — LOKAAL draaien (privébron).

Methode (reproduceerbaar, geen handmatige polygonen):
  1. inkt = grijswaarde < INK_THRESHOLD; plus expliciete CUTS (gestippelde/onderbroken lijnen die als
     grens zijn gekozen, elk met reden) en de handmatig getraceerde regio's (bg_core, bg_kiel) als barrière;
  2. inkt 1 px gedilateerd (3x3) -> vrije ruimte -> 4-samenhangende componenten;
  3. per SEED (vaste sleutel + punt in traces/bg_segments.py) de component die het punt bevat;
  4. gaten (kolommen, tekst) gevuld; kleine inkepingen gesloten; contour vereenvoudigd (approxPolyDP);
  5. arcering 'niet in de splitsing betrokken' via inktdichtheid (HATCH).
Resultaat: data/inventory/bg_segments_p81.json (alleen afgeleide geometrie; geen raster).
Grens = BINNENZIJDE van de getekende lijn (niet de hartlijn): polygonen raken elkaar dus niet, er ligt een
wandstrook tussen. Gebruik: python3 model/tools/segment_bg.py [--scan /pad/page-81.png]
"""
import argparse, json, os, sys
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from traces import bg_core, bg_kiel, bg_segments, f1_segments, f2_segments, f3_segments, f4_segments  # noqa: E402
S = bg_segments
FLOORS = {"BG": (bg_segments, "/workspace/vve-source-audit/page-81.png", "bg_segments_p81.json", True),
          "1e": (f1_segments, "/workspace/vve-source-audit/page-82.png", "f1_segments_p82.json", False),
          "2e": (f2_segments, "/workspace/vve-source-audit/page-83.png", "f2_segments_p83.json", False),
          "3e": (f3_segments, "/workspace/vve-source-audit/page-84.png", "f3_segments_p84.json", False),
          "4e": (f4_segments, "/workspace/vve-source-audit/page-85.png", "f4_segments_p85.json", False)}
from linework import bridged_mask, simplify, add_columns  # noqa: E402

OUT = os.path.join(ROOT, "data", "inventory", "bg_segments_p81.json")


def manual_mask(shape):
    m = np.zeros(shape, np.uint8)
    for T in (bg_core, bg_kiel):
        for key, kind, ring, *_ in T.SPACES:
            pts = np.array([T.VERTICES[v] for v in ring], np.int32)
            cv2.fillPoly(m, [pts], 1)
        for key, kind, pts, *_ in getattr(T, "ELEMENTS", []):
            if len(pts) >= 3:
                cv2.fillPoly(m, [np.array(pts, np.int32)], 1)
    return cv2.dilate(m, np.ones((5, 5), np.uint8))


def _simple(poly):
    n = len(poly)
    def cross(a, b, c, d):
        def o(p, q, r):
            v = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
            return (v > 0) - (v < 0)
        return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if cross(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                return False
    return len(set(map(tuple, poly))) == n and n >= 3


def polygon_of(mask, allowed, inr):
    """mask: component; allowed: component + wandpixels (nooit buurcomponenten)."""
    mask = mask.astype(np.uint8)
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, cs, -1, 1, -1)
    k = S.CLOSE_PX_LARGE if inr >= 40 else S.CLOSE_PX_SMALL
    if k > 1:
        filled = cv2.morphologyEx(filled, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    filled &= allowed.astype(np.uint8)
    if getattr(S, "HOLE_MIN_PX2", 0) and getattr(polygon_of, "others", None) is not None:
        filled &= 1 - _enclosed_claims(filled, mask, allowed.astype(np.uint8), polygon_of.others)
    filled = cv2.erode(filled, np.ones((3, 3), np.uint8))  # 1 px marge: vereenvoudiging kan buren nooit raken
    cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None, 0
    c = max(cs, key=cv2.contourArea)
    if getattr(S, "HOLE_MIN_PX2", 0):   # 1e+: omsloten buurvakken als gaten (binnenringen), anders overlap
        polygon_of.holes = holes_of(filled, c, polygon_of.others)
    for eps in ((S.EPS_LARGE if inr >= 40 else S.EPS_SMALL), 1.0, 0.7, 0.5):
        ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c, eps, True)[:, 0, :]]
        ap = simplify(ap, S.MIN_JOG_AREA_PX2)
        if _simple(ap):
            return ap, int(filled.sum())
    for eps in (1.0, 0.7, 0.5):   # terugval: zonder Visvalingam-vereenvoudiging (komt op p81 niet voor)
        ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c, eps, True)[:, 0, :]]
        if _simple(ap):
            return ap, int(filled.sum())
    return None, 0


def _enclosed_claims(filled, mask, allowed, others):
    """Wandpixels die een OMSLOTEN buurvak (zelfde sluiting als dat vak zelf maximaal krijgt) kan claimen:
    die mag het omsluitende vak niet ook claimen, anders overlappen vak en gat."""
    cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    inner = np.zeros_like(filled)
    cv2.drawContours(inner, cs, -1, 1, -1)
    walls = allowed & (1 - mask)
    n, ol, st, _ = cv2.connectedComponentsWithStats(others, connectivity=4)
    claim = np.zeros_like(filled)
    k, pad = S.CLOSE_PX_LARGE, S.CLOSE_PX_LARGE + 2
    H, W = filled.shape
    for j in range(1, n):
        x, y, w, h, _a = st[j]
        X0, Y0, X1, Y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
        m = (ol[Y0:Y1, X0:X1] == j).astype(np.uint8)
        if not (m & inner[Y0:Y1, X0:X1]).any():
            continue
        c2, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        f = np.zeros_like(m)
        cv2.drawContours(f, c2, -1, 1, -1)
        f = cv2.morphologyEx(f, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8)) & (m | walls[Y0:Y1, X0:X1])
        claim[Y0:Y1, X0:X1] |= cv2.dilate(f, np.ones((3, 3), np.uint8))
    return claim


def holes_of(filled, outer, others=None):  # noqa: C901
    """Binnenringen (gaten) van het grootste vlak, >= S.HOLE_MIN_PX2, alleen als er een ANDER gezaaid vak in ligt
    (tekst-/cijfereilanden zijn geen gat: het vak loopt eronder door). Geen Visvalingam (gaten volgen de buurgrens)."""
    cs, hier = cv2.findContours(filled, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return []
    oi = max(range(len(cs)), key=lambda i: cv2.contourArea(cs[i]))
    out = []
    for i, c in enumerate(cs):
        if hier[0][i][3] != oi or cv2.contourArea(c) < S.HOLE_MIN_PX2:
            continue
        if others is not None:
            hm_ = np.zeros_like(filled)
            cv2.drawContours(hm_, [c], -1, 1, -1)
            if not (hm_ & others).any():
                continue
        for eps in (S.EPS_SMALL, 1.0, 0.7, 0.5):
            ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c, eps, True)[:, 0, :]]
            if len(ap) >= 3 and _simple(ap):
                out.append(ap)
                break
        else:   # geknepen gat (twee buurvakken raken in één punt): splitsen door 1 px erosie
            hm_ = np.zeros_like(filled)
            cv2.drawContours(hm_, [c], -1, 1, -1)
            hm_ = cv2.erode(hm_ & (1 - filled), np.ones((3, 3), np.uint8))
            ok = False
            for c3 in cv2.findContours(hm_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]:
                if cv2.contourArea(c3) < S.HOLE_MIN_PX2 / 4:
                    continue
                ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c3, 0.7, True)[:, 0, :]]
                if len(ap) >= 3 and _simple(ap):
                    out.append(ap)
                    ok = True
            if not ok:
                holes_of.dropped.append(cv2.boundingRect(c))
    return out


def hatch_polys(g):  # gebruikt ruwe inkt (arcering), zonder indexcirkels (dichte inkt naast arcering, geen arcering)
    ink = (g < S.INK_THRESHOLD).astype(np.float32)
    for x0, y0, x1, y1 in S.IDX180.values():
        ink[y0 - 3:y1 + 4, x0 - 3:x1 + 4] = 0
    if getattr(S, "HATCH_MODE", "density") == "diagonal":
        m = diagonal_hatch_mask(ink.astype(np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        return _hatch_out(lab, st)
    dens = cv2.boxFilter(ink, -1, (S.HATCH_WIN, S.HATCH_WIN))
    coarse = cv2.morphologyEx((dens > S.HATCH_DENSITY).astype(np.uint8), cv2.MORPH_OPEN, np.ones((41, 41), np.uint8))
    region = cv2.dilate(coarse, np.ones((45, 45), np.uint8))
    fine = ((cv2.boxFilter(ink, -1, (15, 15)) > 0.08).astype(np.uint8)) & region
    fine = cv2.morphologyEx(fine, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(fine, cv2.MORPH_OPEN, np.ones((21, 21), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    return _hatch_out(lab, st)


def diagonal_hatch_mask(ink):
    """Arcering = dichtheid van diagonale lijnstukken (45/135 graden, >= HATCH_DIAG_LEN px).
    Tekst en omcirkelde nummers hebben nauwelijks lange diagonalen, dus lekt niet in dicht beschreven vakken (p82)."""
    L = S.HATCH_DIAG_LEN
    k1 = np.eye(L, dtype=np.uint8)
    d = cv2.morphologyEx(ink, cv2.MORPH_OPEN, k1) | cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.fliplr(k1).copy())
    dens = cv2.boxFilter(d.astype(np.float32), -1, (S.HATCH_WIN, S.HATCH_WIN))
    m = (dens > S.HATCH_DENSITY).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((25, 25), np.uint8))


def _hatch_out(lab, st):
    out = {}
    for key, (sx, sy), *_ in S.HATCH_SEEDS:
        i = lab[sy, sx]
        if i == 0:
            raise SystemExit(f"hatch seed {key} niet in arcering")
        cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)
        ap = cv2.approxPolyDP(c, S.EPS_LARGE * 2, True)[:, 0, :]
        out[key] = {"polygon": [[int(x), int(y)] for x, y in ap], "area_px": int(st[i, 4])}
    return out


def text_boxes(pad=4):
    """Bekende tekst-/indexposities (omcirkelde 180, handmatig gelezen labels, template-hits 'bedrijfs-ruimte')."""
    out = [tuple(b) for b in S.IDX180.values()]
    if S is not bg_segments:   # 1e+: geen gemeten labelboxen (labels visueel gelezen, positie niet gemeten)
        return out
    for _k, _seed, _kind, _lit, lbox, _note, bhits, _h179 in S.SEEDS:
        if lbox:
            out.append(tuple(lbox))
        out += [tuple(h[:4]) for h in bhits]
    return [(x0 - pad, y0 - pad, x1 + pad, y1 + pad) for x0, y0, x1, y1 in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", default="BG", choices=sorted(FLOORS))
    ap.add_argument("--scan", default=None)
    a = ap.parse_args()
    global S
    S, scan, outname, is_bg = FLOORS[a.floor]
    out_path = os.path.join(ROOT, "data", "inventory", outname)
    g = cv2.imread(a.scan or scan, cv2.IMREAD_GRAYSCALE)
    assert g is not None and g.shape == ((10099, 7118) if is_bg else (S.NATIVE[1], S.NATIVE[0])), f"lokale bronscan {a.floor} vereist"
    raw_ink = (g < S.INK_THRESHOLD).astype(np.uint8)
    cols = []
    if is_bg:   # alleen p81 heeft een visuele kolomreview; p82 kolomkandidaten zijn NIET beoordeeld -> geen kolombarrières
        colrev = json.load(open(os.path.join(ROOT, "data", "inventory", "columns_review_p81.json")))["verdicts"]
        cols = [(c["x"], c["y"], c["size_px"]) for c in colrev if c["verdict"] in ("column_symbol", "uncertain")]
    ink, _arch = bridged_mask(raw_ink, S.LINE_MIN_PX, 5, cols=cols, text_boxes=text_boxes(), gap=S.LINE_GAP_PX,
                            symbol_boxes=[tuple(b) for b in S.IDX180.values()])   # tekst, indexcirkels, kolomsymbolen, stippels eruit
    for key, p, q, why in S.CUTS:
        cv2.line(ink, tuple(p), tuple(q), 1, 3)
    man = manual_mask(g.shape) if is_bg else np.zeros_like(ink)
    hatch = hatch_polys(g)
    hm = np.zeros_like(ink)
    for h in hatch.values():
        cv2.fillPoly(hm, [np.array(h["polygon"], np.int32)], 1)
    wall = cv2.dilate(ink, np.ones((3, 3), np.uint8)) | man | cv2.erode(hm, np.ones((S.HATCH_BARRIER_ERODE, S.HATCH_BARRIER_ERODE), np.uint8))
    n, lab = cv2.connectedComponents((1 - wall).astype(np.uint8), connectivity=4)
    used, segs, problems = {}, {}, []
    seed_comps = [int(lab[sy, sx]) for _k, (sx, sy), *_ in S.SEEDS if lab[sy, sx]]
    for key, (sx, sy), *_ in S.SEEDS:
        i = int(lab[sy, sx])
        if i == 0:
            problems.append(f"{key}: seed op inkt/barrière")
            continue
        if i in used:
            problems.append(f"{key}: zelfde component als {used[i]}")
            continue
        used[i] = key
        m = lab == i
        ys, xs = np.nonzero(m)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        if x0 == 0 or y0 == 0 or x1 >= g.shape[1] - 1 or y1 >= g.shape[0] - 1:
            problems.append(f"{key}: lekt naar buitengebied/bladrand")
            continue
        pad = S.CLOSE_PX_LARGE
        X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
        L = lab[Y0:y1 + pad + 1, X0:x1 + pad + 1]
        sub = L == i
        dt = cv2.distanceTransform(np.pad(m[y0:y1 + 1, x0:x1 + 1].astype(np.uint8), 1), cv2.DIST_L2, 5)
        inr = float(dt.max())
        polygon_of.holes = []
        holes_of.dropped = []
        polygon_of.others = (np.isin(L, seed_comps) & (L != i)).astype(np.uint8) if getattr(S, "HOLE_MIN_PX2", 0) else None
        poly, area = polygon_of(sub, (L == i) | (L == 0) & (hm[Y0:y1 + pad + 1, X0:x1 + pad + 1] == 0), inr)
        if poly is None:
            problems.append(f"{key}: geen geldige polygoon")
            continue
        poly = [[x + int(X0), y + int(Y0)] for x, y in poly]
        segs[key] = {"polygon": poly, "area_px": area, "inscribed_radius_px": round(inr, 1),
                     "bbox_px": [int(x0), int(y0), int(x1), int(y1)]}
        if holes_of.dropped:
            problems.append(f"{key}: {len(holes_of.dropped)} gat(en) zonder geldige ring: {holes_of.dropped}")
        if polygon_of.holes:
            segs[key]["holes"] = [[[x + int(X0), y + int(Y0)] for x, y in h] for h in polygon_of.holes]
    seedmask = np.isin(lab, list(used.keys())).astype(np.uint8)
    seedmask = cv2.dilate(seedmask, np.ones((7, 7), np.uint8))
    for key, h in hatch.items():
        hmask = np.zeros_like(ink)
        cv2.fillPoly(hmask, [np.array(h["polygon"], np.int32)], 1)
        hmask &= (1 - seedmask)
        hmask = cv2.erode(hmask, np.ones((3, 3), np.uint8))
        cs, _ = cv2.findContours(hmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=cv2.contourArea)
        for eps in (2.0, 1.0, 0.7):
            ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c, eps, True)[:, 0, :]]
            if _simple(ap):
                break
        h["polygon"], h["area_px"] = ap, int(hmask.sum())
    out = {"generated_by": f"tools/segment_bg.py --floor {a.floor}", "source_page": 81 if is_bg else S.PAGE,
           "params": {"ink_threshold": S.INK_THRESHOLD, "dilate_px": 1, "line_min_px": S.LINE_MIN_PX, "min_jog_area_px2": S.MIN_JOG_AREA_PX2,
                      "linework": "architectural_mask (rechte lijnen >= line_min_px); tekst/symbolen/stippels gemaskeerd", "close_px": [S.CLOSE_PX_SMALL, S.CLOSE_PX_LARGE],
                      "approx_eps_px": [S.EPS_SMALL, S.EPS_LARGE], "hatch": [S.HATCH_WIN, S.HATCH_DENSITY]},
           "boundary_reference": "inner_face_of_drawn_line",
           "segments": segs, "hatch": hatch, "problems": problems}
    with open(out_path, "w") as f:
        json.dump(out, f, indent=0)
    print(out_path, len(segs), "segmenten,", len(hatch), "arceringen;", len(problems), "problemen")
    for p in problems:
        print("  !", p)


if __name__ == "__main__":
    main()
