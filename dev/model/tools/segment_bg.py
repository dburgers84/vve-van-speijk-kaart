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
from traces import bg_core, bg_kiel, bg_segments as S  # noqa: E402

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
    filled = cv2.erode(filled, np.ones((3, 3), np.uint8))  # 1 px marge: vereenvoudiging kan buren nooit raken
    cs, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None, 0
    c = max(cs, key=cv2.contourArea)
    for eps in ((S.EPS_LARGE if inr >= 40 else S.EPS_SMALL), 1.0, 0.7, 0.5):
        ap = [[int(x), int(y)] for x, y in cv2.approxPolyDP(c, eps, True)[:, 0, :]]
        if _simple(ap):
            return ap, int(filled.sum())
    return None, 0


def hatch_polys(g):
    ink = (g < S.INK_THRESHOLD).astype(np.float32)
    dens = cv2.boxFilter(ink, -1, (S.HATCH_WIN, S.HATCH_WIN))
    coarse = cv2.morphologyEx((dens > S.HATCH_DENSITY).astype(np.uint8), cv2.MORPH_OPEN, np.ones((41, 41), np.uint8))
    region = cv2.dilate(coarse, np.ones((45, 45), np.uint8))
    fine = ((cv2.boxFilter(ink, -1, (15, 15)) > 0.08).astype(np.uint8)) & region
    fine = cv2.morphologyEx(fine, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    m = cv2.morphologyEx(fine, cv2.MORPH_OPEN, np.ones((21, 21), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", default="/workspace/vve-source-audit/page-81.png")
    a = ap.parse_args()
    g = cv2.imread(a.scan, cv2.IMREAD_GRAYSCALE)
    assert g is not None and g.shape == (10099, 7118), "lokale bronscan p81 vereist"
    ink = (g < S.INK_THRESHOLD).astype(np.uint8)
    for key, p, q, why in S.CUTS:
        cv2.line(ink, tuple(p), tuple(q), 1, 3)
    man = manual_mask(g.shape)
    hatch = hatch_polys(g)
    hm = np.zeros_like(ink)
    for h in hatch.values():
        cv2.fillPoly(hm, [np.array(h["polygon"], np.int32)], 1)
    wall = cv2.dilate(ink, np.ones((3, 3), np.uint8)) | man | cv2.dilate(hm, np.ones((5, 5), np.uint8))
    n, lab = cv2.connectedComponents((1 - wall).astype(np.uint8), connectivity=4)
    used, segs, problems = {}, {}, []
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
        poly, area = polygon_of(sub, (L == i) | (L == 0) & (hm[Y0:y1 + pad + 1, X0:x1 + pad + 1] == 0), inr)
        if poly is None:
            problems.append(f"{key}: geen geldige polygoon")
            continue
        poly = [[x + int(X0), y + int(Y0)] for x, y in poly]
        segs[key] = {"polygon": poly, "area_px": area, "inscribed_radius_px": round(inr, 1),
                     "bbox_px": [int(x0), int(y0), int(x1), int(y1)]}
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
    out = {"generated_by": "tools/segment_bg.py", "source_page": 81,
           "params": {"ink_threshold": S.INK_THRESHOLD, "dilate_px": 1, "close_px": [S.CLOSE_PX_SMALL, S.CLOSE_PX_LARGE],
                      "approx_eps_px": [S.EPS_SMALL, S.EPS_LARGE], "hatch": [S.HATCH_WIN, S.HATCH_DENSITY]},
           "boundary_reference": "inner_face_of_drawn_line",
           "segments": segs, "hatch": hatch, "problems": problems}
    with open(OUT, "w") as f:
        json.dump(out, f, indent=0)
    print(OUT, len(segs), "segmenten,", len(hatch), "arceringen;", len(problems), "problemen")
    for p in problems:
        print("  !", p)


if __name__ == "__main__":
    main()
