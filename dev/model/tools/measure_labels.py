#!/usr/bin/env python3
"""Meet tekstposities (labelboxen) per vak op een bronblad, i.p.v. ze rond het zaadpunt te benaderen.

Werkwijze (geen OCR): inkt-eilanden die volledig BINNEN het vak liggen (polygon 4 px ingekrompen, gaten uitgesloten)
worden per tekstkolom gegroepeerd (tekst staat op p82/p83 90 graden gedraaid: tekens onder elkaar langs native y).
- groot nummer (index 181-356 of 179): tekens 40-80 px breed (x), 8-60 px hoog (y);
- klein woord (bv. 'woning', 'buitenr.'): tekens 8-32 px breed, 2-24 px hoog.
Een cluster wordt alleen aanvaard als het aantal tekens past bij de visueel gelezen tekst
(nummer: precies het aantal cijfers, +-1 bij versmolten/gebroken cijfers; woord: +-max(2, 35 %)). Anders: geen meting
(de builder valt dan terug op een benaderde box en markeert die zo).
Uitvoer: data/inventory/labels_measured_<page>.json (alleen boxen; geen bronpixels).
"""
import argparse
import json
import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

BIG = dict(w=(40, 90), h=(8, 62), dx=14, gap=60)
SMALL = dict(w=(8, 32), h=(2, 24), dx=9, gap=13)


def islands(raw, poly, holes):
    poly = np.array(poly, np.int32)
    x, y, w, h = cv2.boundingRect(poly)
    m = np.zeros((h + 2, w + 2), np.uint8)
    cv2.fillPoly(m, [poly - [x - 1, y - 1]], 1)
    for hl in holes:
        cv2.fillPoly(m, [np.array(hl, np.int32) - [x - 1, y - 1]], 0)
    m = cv2.erode(m, np.ones((9, 9), np.uint8))
    r = raw[y - 1:y + h + 1, x - 1:x + w + 1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(r, connectivity=8)
    out = []
    for i in range(1, n):
        X, Y, W, H, A = st[i]
        if A < 12:
            continue
        comp = lab[Y:Y + H, X:X + W] == i
        if (comp & (m[Y:Y + H, X:X + W] == 0)).any():
            continue
        out.append((int(X + x - 1), int(Y + y - 1), int(W), int(H)))
    # tekens BINNEN een ander eiland (cijfers in een omcirkelde 180, binnenkant van letters) tellen niet
    return [b for b in out if not any(o is not b and o[0] <= b[0] and o[1] <= b[1] and b[0] + b[2] <= o[0] + o[2]
                                      and b[1] + b[3] <= o[1] + o[3] and o[2] * o[3] > b[2] * b[3] for o in out)]


def columns(isl, P):
    """Tekstkolommen (tekens onder elkaar langs y; gedraaide tekst) + tekstregels (tekens naast elkaar langs x)."""
    groups = []
    c = [b for b in isl if P["w"][0] <= b[2] <= P["w"][1] and P["h"][0] <= b[3] <= P["h"][1]]
    for b in sorted(c, key=lambda b: b[1]):
        for gr in groups:
            last = gr[-1]
            if abs(b[0] - gr[0][0]) <= P["dx"] and 0 <= b[1] - (last[1] + last[3]) <= P["gap"]:
                gr.append(b)
                break
        else:
            groups.append([b])
    rows = []
    c = [b for b in isl if P["w"][0] <= b[3] <= P["w"][1] and P["h"][0] <= b[2] <= P["h"][1]]   # zelfde tekens, 90 graden
    for b in sorted(c, key=lambda b: b[0]):
        for gr in rows:
            last = gr[-1]
            if abs((b[1] + b[3]) - (gr[0][1] + gr[0][3])) <= P["dx"] and 0 <= b[0] - (last[0] + last[2]) <= P["gap"]:
                gr.append(b)
                break
        else:
            rows.append([b])
    return groups + [r for r in rows if len(r) >= 2]


def bbox(gr):
    return [min(b[0] for b in gr), min(b[1] for b in gr), max(b[0] + b[2] for b in gr), max(b[1] + b[3] for b in gr)]


def enclosed(raw, b, d=(3, 14)):
    """True als er aan BEIDE uiteinden van de tekstkolom inkt ligt (ellips van een omcirkelde 180 rond de cijfers)."""
    x0, y0, x1, y1 = b[:4]
    xs = slice(x0 + (x1 - x0) // 4, x1 - (x1 - x0) // 4 + 1)
    return raw[y0 - d[1]:y0 - d[0], xs].any() and raw[y1 + d[0]:y1 + d[1], xs].any() \
        and raw[y0:y1, x0 - d[1]:x0 - d[0]].any() and raw[y0:y1, x1 + d[0]:x1 + d[1]].any()


def pick(groups, n_expect, tol, seed, raw=None):
    ok = [gr for gr in groups if abs(len(gr) - n_expect) <= tol and (raw is None or not enclosed(raw, bbox(gr)))]
    if not ok:
        return None
    sx, sy = seed
    best = min(ok, key=lambda gr: (abs(len(gr) - n_expect), -len(gr), abs((bbox(gr)[0] + bbox(gr)[2]) / 2 - sx) + abs((bbox(gr)[1] + bbox(gr)[3]) / 2 - sy)))
    return bbox(best) + [len(best)]


def measure(M, seg, raw):
    out = {}
    for key, seed, kind, lit, idx, h179, note in M.SEEDS:
        g = seg["segments"].get(key)
        if g is None:
            continue
        isl = islands(raw, g["polygon"], g.get("holes", []))
        big, small = columns(isl, BIG), columns(isl, SMALL)
        r = {}
        if idx:
            b = pick(big, len(idx), 1 if len(idx) >= 3 else 0, seed)
            if b:
                r["number"] = b
                big = [gr for gr in big if bbox(gr) + [len(gr)] != b]
            else:   # bergingnummers zijn klein geschreven (zelfde grootte als de tekst in de 180-cirkel)
                b = pick(small, len(idx), 0, seed, raw)
                if b:
                    r["number"] = b + ["small"]
                    small = [gr for gr in small if bbox(gr) + [len(gr)] != b[:5]]
        if h179:
            b = pick(big, 3, 1, seed)
            if b:
                r["i179"] = b
        if lit:
            n = len(lit.replace(" ", "").replace("-", ""))
            b = pick(small, n, max(2, round(0.35 * n)), seed)
            if b:
                r["literal"] = b
        if r:
            out[key] = r
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", choices=["1e", "2e"], required=True)
    a = ap.parse_args()
    import importlib
    mod, page = {"1e": ("f1_segments", 82), "2e": ("f2_segments", 83)}[a.floor]
    M = importlib.import_module("traces." + mod)
    seg = json.load(open(os.path.join(ROOT, "data", "inventory", f"{M.PREFIX.split('_')[0]}_segments_p{page}.json")))
    g = cv2.imread(f"/workspace/vve-source-audit/page-{page}.png", cv2.IMREAD_GRAYSCALE)
    assert g is not None and g.shape == (M.NATIVE[1], M.NATIVE[0]), "lokale bronscan vereist"
    raw = (g < M.INK_THRESHOLD).astype(np.uint8)
    res = measure(M, seg, raw)
    want = {"number": sum(1 for s in M.SEEDS if s[4]), "literal": sum(1 for s in M.SEEDS if s[3]), "i179": sum(1 for s in M.SEEDS if s[5])}
    got = {k: sum(1 for r in res.values() if k in r) for k in want}
    outp = os.path.join(ROOT, "data", "inventory", f"labels_measured_p{page}.json")
    json.dump({"generated_by": f"tools/measure_labels.py --floor {a.floor}", "page": page, "method": __doc__.strip().splitlines()[0],
               "counts": {"wanted": want, "measured": got}, "labels": res}, open(outp, "w"), indent=0)
    print(outp, got, "van", want)


if __name__ == "__main__":
    main()
