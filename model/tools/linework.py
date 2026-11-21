"""Architectonische lijnen uit een bronscan scheiden van tekst/symbolen (gedeeld door alle bladen).

architectural_mask(ink): behoud alleen inkt die deel is van een rechte lijn van minstens L px
(morfologische opening met 1-px lijnkernen onder hoeken 0..175 graden, stap 5).
Effect: letters, cijfers, omcirkelde indexnummers (180), kolomvierkantjes (<L), gestippelde lijnen en
korte dwarsstreepjes verdwijnen; wanden, gevels, scheidingslijnen, hoeken en T-aansluitingen blijven.
Gestippelde lijnen die WEL als grens dienen moeten expliciet als CUT (met reden) worden toegevoegd.
simplify(poly, min_area): Visvalingam-Whyatt; verwijdert hoekpunten waarvan de driehoek < min_area px2
(flarden/rafels), behoudt echte inspringingen.
"""
import cv2
import numpy as np


def line_kernel(L, ang):
    k = np.zeros((L + 2, L + 2), np.uint8)
    c = (L + 1) / 2
    dx, dy = np.cos(np.radians(ang)) * L / 2, np.sin(np.radians(ang)) * L / 2
    cv2.line(k, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1, 1)
    return k


def architectural_mask(ink, L=31, step=5, gap=0):
    """Per richting: eerst kleine onderbrekingen (< gap px, typisch voor dunne gescande lijnen) langs die
    richting dichten, dan openen met een lijn van L px. Resultaat begrensd tot (licht verdikte) echte inkt
    plus de gedichte onderbrekingen langs dezelfde lijn."""
    out = np.zeros_like(ink)
    for a in range(0, 180, step):
        c = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, line_kernel(gap, a)) if gap else ink
        out |= cv2.morphologyEx(c, cv2.MORPH_OPEN, line_kernel(L, a))
    return out


def bridged_mask(ink, L=31, step=5, max_text=150, cols=(), text_boxes=(), cluster_gap=6, gap=0, symbol_boxes=()):
    """Bouwlijnen-masker: ruwe inkt MINUS tekst/symbolen.

    Bouwlijn = inkt in een rechte lijn >= L px (architectural_mask) of een visueel beoordeeld kolomsymbool.
    Restinkt (al het andere) wordt gegroepeerd in clusters (componenten met onderlinge afstand <= cluster_gap px).
    - symbol_boxes (nauwkeurig gemeten, bv. omcirkelde 180): binnen de box geldt alleen een rechte lijn
      langer dan de box als bouwlijn (ook als de ring een wand raakt)
    - restcomponent die grotendeels in een bekende tekst-/indexbox ligt (text_boxes)                      -> weg
    - restcomponent groter dan max_text px (gebogen/schuin lijnwerk)                                      -> blijft
    - cluster dat nergens een bouwlijn/kolom raakt (losse woorden, cijfers, indexcirkels, losse stippels,
      niet-aangesloten symbolen)                                                                         -> weg
    - cluster dat een bouwlijn raakt (onderbroken/rafelige scanlijn, wandkop, dagkant, lijnstomp)        -> blijft
    Bewuste beperking: tekst die een wand raakt en niet in text_boxes staat blijft inkt (kan een kleine
    inkeping geven; simplify() ruimt inkepingen < min_area op)."""
    arch = architectural_mask(ink, L, step, gap)
    colm = add_columns(np.zeros_like(ink), [(x, y, sz + 6) for x, y, sz in cols])
    textm = np.zeros_like(ink)
    for x0, y0, x1, y1 in text_boxes:
        textm[max(0, int(y0)):int(y1) + 1, max(0, int(x0)):int(x1) + 1] = 1
    H, W = ink.shape
    for x0, y0, x1, y1 in symbol_boxes:
        # Binnen een (nauwkeurig gemeten) symboolbox, bv. omcirkelde 180, telt alleen een rechte lijn die LANGER is dan de box zelf als bouwlijn
        # (wand die langs/door de box loopt). Flanken van de ovale 180-ring en letterstokken vallen weg,
        # ook als de ring een wand raakt.
        x0, y0, x1, y1 = max(0, int(x0)), max(0, int(y0)), min(W - 1, int(x1)), min(H - 1, int(y1))
        Lb = max(x1 - x0, y1 - y0) + 10
        X0, Y0, X1, Y1 = max(0, x0 - Lb), max(0, y0 - Lb), min(W, x1 + Lb + 1), min(H, y1 + Lb + 1)
        longl = architectural_mask(np.ascontiguousarray(ink[Y0:Y1, X0:X1]), Lb, step, gap)
        arch[y0:y1 + 1, x0:x1 + 1] = longl[y0 - Y0:y1 + 1 - Y0, x0 - X0:x1 + 1 - X0]
    resid = (ink & (1 - arch) & (1 - colm)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(resid, connectivity=8)
    k = 2 * (cluster_gap // 2) + 1
    nc, clab = cv2.connectedComponents(cv2.dilate(resid, np.ones((k, k), np.uint8)), connectivity=8)
    archd = cv2.dilate(arch | colm, np.ones((3, 3), np.uint8))
    touch = np.zeros(nc, bool)
    hit = np.unique(clab[(archd > 0) & (clab > 0) & (cv2.dilate(resid, np.ones((3, 3), np.uint8)) > 0)])
    touch[hit] = True
    keep = np.zeros_like(ink)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        sub = lab[y:y + h, x:x + w] == i
        if textm[y:y + h, x:x + w][sub].mean() > 0.5:
            continue
        if max(w, h) > max_text or touch[clab[y:y + h, x:x + w][sub][0]]:
            keep[y:y + h, x:x + w] |= sub.astype(np.uint8)
    return add_columns(arch | keep | (ink & colm & (1 - textm)), [(x, y, sz + 6) for x, y, sz in cols]), arch


def add_columns(mask, cols):
    """Visueel beoordeelde kolomsymbolen (x, y, size_px) als massieve barriere toevoegen."""
    for x, y, s in cols:
        h = int(round(s / 2))
        cv2.rectangle(mask, (int(x) - h, int(y) - h), (int(x) + h, int(y) + h), 1, -1)
    return mask


def _tri(a, b, c):
    return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2


def simplify(poly, min_area):
    p = [tuple(v) for v in poly]
    while len(p) > 3:
        areas = [_tri(p[i - 1], p[i], p[(i + 1) % len(p)]) for i in range(len(p))]
        i = int(np.argmin(areas))
        if areas[i] >= min_area:
            break
        p.pop(i)
    return [list(v) for v in p]
