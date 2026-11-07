#!/usr/bin/env python3
"""Validator voor het VvE-plattegrondmodel v2 (stdlib-only).

Gebruik:  python3 model/validate.py model/data/pilot-bg-core.v2.json

Controleert naast de structuur (subset van schema/vve-plan-v2.schema.json; als het
pakket `jsonschema` aanwezig is wordt ook het volledige schema gecontroleerd):
- unieke, stabiele ids; alle referenties bestaan
- vertices binnen het frame en x_rel/y_rel consistent met x_px/y_px
- polygonen: >=3 unieke vertices, oppervlak > 0, geen zelfdoorsnijding, ring-randen
  bestaan als edges; gaten liggen binnen de buitenring
- topologie: geen overlap tussen ruimtes op dezelfde verdieping (tolerantie),
  T-knopen (vertex op het inwendige van een gebruikte edge) worden gemeld
- maatstatus per edge: unknown => length null; derived => kalibratie bestaat,
  methode gezet, lengte consistent; onzekerheid null alleen met status 'unknown';
  source => brontekst en bronverwijzing verplicht
- geen 'exacte' maten: derived met nominale kalibratie mag geen uncertainty_m claimen
- verbindingen: edge gedeeld door beide verbonden ruimtes
- juridische memberships: verwijzen naar bestaande splits; UI moet uit staan zolang
  een split boundary_status 'unknown' heeft en relation != unknown ontbreekt
- coverage.complete moet expliciet zijn
Retourneert exit-code 1 bij fouten. Waarschuwingen breken niet.
"""
import json, math, re, sys

ID_RE = re.compile(r"^[a-z][a-z0-9]*(_[A-Za-z0-9]+)+$")
DIM_STATUS = {"source", "derived", "unknown"}
EPS_REL = 1e-6


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    @property
    def ok(self):
        return not self.errors


def _area(pts):
    return 0.5 * sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                     for i in range(len(pts)))


def _seg_cross(p1, p2, p3, p4):
    """Echte (eigenlijke) doorsnijding van twee segmenten, geen aanraking."""
    def o(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(p3, p4, p1), o(p3, p4, p2), o(p1, p2, p3), o(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def _point_in_poly(pt, poly):
    x, y = pt
    inside = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


def _on_segment_interior(p, a, b, tol=0.5):
    (px, py), (ax, ay), (bx, by) = p, a, b
    L = math.hypot(bx - ax, by - ay)
    if L == 0:
        return False
    t = ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / (L * L)
    if t <= 1e-6 or t >= 1 - 1e-6:
        return False
    d = abs((bx - ax) * (ay - py) - (ax - px) * (by - ay)) / L
    return d <= tol


def _bbox_hit(P, Q):
    return not (max(p[0] for p in P) <= min(q[0] for q in Q) or max(q[0] for q in Q) <= min(p[0] for p in P)
                or max(p[1] for p in P) <= min(q[1] for q in Q) or max(q[1] for q in Q) <= min(p[1] for p in P))


def _seg_cross(a, b, c, d):
    def o(p, q, r):
        v = (q[0] - p[0]) * (r[1] - q[1]) - (q[1] - p[1]) * (r[0] - q[0])
        return (v > 1e-9) - (v < -1e-9)
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def _edges_cross(P, Q):
    qb = [(Q[j], Q[(j + 1) % len(Q)]) for j in range(len(Q))]
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        for c, d in qb:
            if max(a[0], b[0]) < min(c[0], d[0]) or max(c[0], d[0]) < min(a[0], b[0]) or \
               max(a[1], b[1]) < min(c[1], d[1]) or max(c[1], d[1]) < min(a[1], b[1]):
                continue
            if _seg_cross(a, b, c, d):
                return True
    return False


def _interior_pt(P):
    """Punt binnen polygon: midden van de langste horizontale doorsnede op y=midden bbox."""
    ys = sorted(p[1] for p in P)
    y = (ys[0] + ys[-1]) / 2 + 0.37
    xs = []
    for i in range(len(P)):
        (x1, y1), (x2, y2) = P[i], P[(i + 1) % len(P)]
        if (y1 > y) != (y2 > y):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    best = max(((xs[k + 1] - xs[k], (xs[k] + xs[k + 1]) / 2) for k in range(0, len(xs) - 1, 2)), default=(0, P[0][0]))
    return (best[1], y)


def _poly_overlap_area(P, Q, step=2.0):
    """Ruwe overlap-schatting via raster-sampling op de doorsnede van bboxen (px)."""
    minx = max(min(p[0] for p in P), min(q[0] for q in Q))
    maxx = min(max(p[0] for p in P), max(q[0] for q in Q))
    miny = max(min(p[1] for p in P), min(q[1] for q in Q))
    maxy = min(max(p[1] for p in P), max(q[1] for q in Q))
    if minx >= maxx or miny >= maxy:
        return 0.0
    n = 0
    y = miny + step / 2
    while y < maxy:
        x = minx + step / 2
        while x < maxx:
            if _point_in_poly((x, y), P) and _point_in_poly((x, y), Q):
                n += 1
            x += step
        y += step
    return n * step * step


def _structural(d, r):
    try:
        import jsonschema  # optioneel
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        schema = json.load(open(os.path.join(here, "schema", "vve-plan-v2.schema.json")))
        for e in jsonschema.Draft202012Validator(schema).iter_errors(d):
            r.err(f"schema: {list(e.path)}: {e.message}")
        return
    except ImportError:
        pass
    req = ["schema_version", "dataset_version", "sources", "calibrations", "frames", "floors", "objects",
           "vertices", "edges", "labels", "connections", "legal_splits", "legal_split_ui", "memberships",
           "legacy_links", "coverage", "review_log"]
    for k in req:
        if k not in d:
            r.err(f"ontbrekend top-level veld: {k}")
    if not re.match(r"^vve-plan/2\.\d+\.\d+$", str(d.get("schema_version", ""))):
        r.err("schema_version moet 'vve-plan/2.x.y' zijn")


def validate(d):
    r = Report()
    _structural(d, r)
    if r.errors and any(e.startswith("ontbrekend") for e in r.errors):
        return r

    # ---- ids
    seen = {}
    for coll in ["sources", "calibrations", "frames", "regions", "reference_overlays", "objects", "vertices", "edges", "labels", "connections", "legal_splits"]:
        for it in d.get(coll, []):
            i = it.get("id")
            if not isinstance(i, str) or not ID_RE.match(i):
                r.err(f"{coll}: ongeldig id {i!r}")
                continue
            if i in seen:
                r.err(f"dubbel id {i} ({seen[i]} en {coll})")
            seen[i] = coll
    src = {s["id"]: s for s in d["sources"]}
    cal = {c["id"]: c for c in d["calibrations"]}
    frm = {f["id"]: f for f in d["frames"]}
    flr = {f["id"] for f in d["floors"]}
    V = {v["id"]: v for v in d["vertices"]}
    E = {e["id"]: e for e in d["edges"]}
    O = {o["id"]: o for o in d["objects"]}
    L = {l["id"]: l for l in d["labels"]}
    S = {s["id"]: s for s in d["legal_splits"]}

    for ov in d.get("reference_overlays", []):
        if ov["frame_id"] not in frm:
            r.err(f"overlay {ov['id']}: onbekend frame")
        if ov.get("public") and not str(ov.get("image", "")).startswith("img/plan_"):
            r.err(f"overlay {ov['id']}: publieke overlay alleen uit reeds gepubliceerde img/plan_*.jpg")
    for o in d["objects"]:
        if o.get("region_id") and o["region_id"] not in {g["id"] for g in d.get("regions", [])}:
            r.err(f"object {o['id']}: onbekende regio {o['region_id']}")
    # ---- sources/privacy
    for s in d["sources"]:
        if s.get("privacy_class") != "public" and s.get("publish_native_raster"):
            r.err(f"bron {s['id']}: privé-bron mag publish_native_raster niet true hebben")
    # ---- calibrations
    for c in d["calibrations"]:
        if c["frame_id"] not in frm:
            r.err(f"kalibratie {c['id']}: onbekend frame {c['frame_id']}")
        if c.get("uncertainty_m") is None and c.get("uncertainty_status") != "unknown" and not c.get("rel_uncertainty"):
            r.err(f"kalibratie {c['id']}: uncertainty_m null vereist uncertainty_status 'unknown' (of rel_uncertainty)")
        if c.get("status") == "controls_checked_one_axis":
            if len(c.get("control_points") or []) < 2:
                r.err(f"kalibratie {c['id']}: controle zonder minstens 2 control_points")
            ax = c.get("axis_status") or {}
            if not ax:
                r.err(f"kalibratie {c['id']}: axis_status vereist")
            if all(str(v).startswith("checked") for v in ax.values()):
                r.err(f"kalibratie {c['id']}: 'one_axis' maar beide assen als gecontroleerd opgegeven")
            ru = c.get("rel_uncertainty") or {}
            if not (ru.get("x", 0) > 0 and ru.get("y", 0) > 0):
                r.err(f"kalibratie {c['id']}: rel_uncertainty x/y > 0 vereist")
        if c.get("status") == "verified" and not c.get("control_points"):
            r.err(f"kalibratie {c['id']}: 'verified' zonder control_points")
        if c.get("status") == "nominal_unverified" and c.get("uncertainty_m") is not None:
            r.err(f"kalibratie {c['id']}: nominaal ongetoetst mag geen uncertainty_m claimen")
    # ---- frames
    for f in d["frames"]:
        if f["source_id"] not in src:
            r.err(f"frame {f['id']}: onbekende bron")
        if f["floor_id"] not in flr:
            r.err(f"frame {f['id']}: onbekende verdieping {f['floor_id']}")
        sw, sh = (src.get(f["source_id"], {}).get("native_size_px") or [None, None])
        if (sw, sh) != (f["width_px"], f["height_px"]):
            r.err(f"frame {f['id']}: afmeting wijkt af van bron native_size_px")
        for ci in f.get("calibration_ids", []):
            if ci not in cal:
                r.err(f"frame {f['id']}: onbekende kalibratie {ci}")
    # ---- vertices
    for v in d["vertices"]:
        f = frm.get(v["frame_id"])
        if not f:
            r.err(f"vertex {v['id']}: onbekend frame")
            continue
        if v["floor_id"] != f["floor_id"]:
            r.err(f"vertex {v['id']}: floor_id wijkt af van frame")
        if not (0 <= v["x_px"] <= f["width_px"] and 0 <= v["y_px"] <= f["height_px"]):
            r.err(f"vertex {v['id']}: buiten frame")
        if abs(v["x_rel"] - v["x_px"] / f["width_px"]) > EPS_REL or abs(v["y_rel"] - v["y_px"] / f["height_px"]) > EPS_REL:
            r.err(f"vertex {v['id']}: x_rel/y_rel inconsistent met x_px/y_px")
    P = {k: (v["x_px"], v["y_px"]) for k, v in V.items()}
    # ---- edges + maatstatus
    pair2edge = {}
    for e in d["edges"]:
        a, b = e["v"]
        if a not in V or b not in V:
            r.err(f"edge {e['id']}: onbekende vertex")
            continue
        if a == b:
            r.err(f"edge {e['id']}: nul-lengte (zelfde vertex)")
        if V[a]["frame_id"] != e["frame_id"] or V[b]["frame_id"] != e["frame_id"]:
            r.err(f"edge {e['id']}: vertices in ander frame")
        k = frozenset((a, b))
        if k in pair2edge:
            r.err(f"edge {e['id']}: dubbele edge voor zelfde vertexpaar als {pair2edge[k]} (gedeelde grens moet één edge zijn)")
        pair2edge[k] = e["id"]
        dm = e.get("dimension") or {}
        st = dm.get("status")
        if st not in DIM_STATUS:
            r.err(f"edge {e['id']}: dimension.status moet source/derived/unknown zijn")
            continue
        if dm.get("uncertainty_m") is None and dm.get("uncertainty_status") != "unknown":
            r.err(f"edge {e['id']}: uncertainty_m null vereist uncertainty_status 'unknown'")
        if st == "unknown":
            if dm.get("length_m") is not None:
                r.err(f"edge {e['id']}: status unknown vereist length_m null")
        elif st == "derived":
            c = cal.get(dm.get("calibration_ref"))
            if not c:
                r.err(f"edge {e['id']}: derived zonder geldige calibration_ref")
                continue
            if c["frame_id"] != e["frame_id"]:
                r.err(f"edge {e['id']}: kalibratie hoort bij ander frame")
            if not dm.get("method"):
                r.err(f"edge {e['id']}: derived zonder method")
            if not isinstance(dm.get("length_m"), (int, float)):
                r.err(f"edge {e['id']}: derived vereist numerieke length_m")
            elif c.get("m_per_px_x") and c.get("m_per_px_y"):
                (x1, y1), (x2, y2) = P[a], P[b]
                exp = math.hypot((x2 - x1) * c["m_per_px_x"], (y2 - y1) * c["m_per_px_y"])
                if abs(exp - dm["length_m"]) > 0.006:
                    r.err(f"edge {e['id']}: length_m {dm['length_m']} != afgeleid {exp:.3f}")
            if c.get("status") in ("nominal_unverified", "none"):
                if dm.get("uncertainty_m") is not None:
                    r.err(f"edge {e['id']}: nominale kalibratie kan geen uncertainty_m onderbouwen (fictieve exactheid)")
            elif c.get("rel_uncertainty"):
                if dm.get("uncertainty_m") is None:
                    r.err(f"edge {e['id']}: gecontroleerde kalibratie vereist uncertainty_m (geen schijnexactheid)")
                else:
                    (x1, y1), (x2, y2) = P[a], P[b]
                    ru = c["rel_uncertainty"]
                    umin = math.hypot((x2 - x1) * c["m_per_px_x"] * ru["x"], (y2 - y1) * c["m_per_px_y"] * ru["y"])
                    if dm["uncertainty_m"] + 0.006 < umin:
                        r.err(f"edge {e['id']}: uncertainty_m {dm['uncertainty_m']} kleiner dan schaalonzekerheid {umin:.3f}")
        elif st == "source":
            if not dm.get("source_text") or not dm.get("source_ref"):
                r.err(f"edge {e['id']}: source-maat vereist source_text en source_ref")
            if not isinstance(dm.get("length_m"), (int, float)):
                r.err(f"edge {e['id']}: source-maat vereist length_m")
    # ---- objects
    edge_users = {}
    space_polys = {}
    for o in d["objects"]:
        if o["floor_id"] not in flr:
            r.err(f"object {o['id']}: onbekende verdieping")
        if o["frame_id"] not in frm:
            r.err(f"object {o['id']}: onbekend frame")
        for li in o.get("label_ids", []):
            if li not in L:
                r.err(f"object {o['id']}: onbekend label {li}")
            elif o["id"] not in L[li]["assigned_object_ids"]:
                r.err(f"object {o['id']}: label {li} niet terug-toegewezen")
        g = o["geometry"]
        if g["type"] == "Polygon":
            rings = g["rings"]
            used = set()
            for ri, ring in enumerate(rings):
                if any(v not in V for v in ring):
                    r.err(f"object {o['id']}: ring {ri} onbekende vertex")
                    break
                if len(set(ring)) != len(ring) or len(ring) < 3:
                    r.err(f"object {o['id']}: ring {ri} moet >=3 unieke vertices hebben (impliciet gesloten)")
                    continue
                pts = [P[v] for v in ring]
                if abs(_area(pts)) < 1:
                    r.err(f"object {o['id']}: ring {ri} oppervlak ~0")
                n = len(pts)
                for i in range(n):
                    for j in range(i + 1, n):
                        if abs(i - j) in (1, n - 1):
                            continue
                        if _seg_cross(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]):
                            r.err(f"object {o['id']}: ring {ri} zelfdoorsnijding")
                for i in range(n):
                    k = frozenset((ring[i], ring[(i + 1) % n]))
                    eid = pair2edge.get(k)
                    if not eid:
                        r.err(f"object {o['id']}: ring-rand {ring[i]}-{ring[(i+1)%n]} heeft geen edge")
                    else:
                        used.add(eid)
                        edge_users.setdefault(eid, set()).add(o["id"])
                if ri > 0:
                    outer = [P[v] for v in rings[0]]
                    if not all(_point_in_poly(p, outer) for p in pts):
                        r.err(f"object {o['id']}: gat {ri} ligt niet binnen buitenring")
            if set(o.get("edge_ids", [])) != used:
                r.err(f"object {o['id']}: edge_ids komt niet overeen met ringranden")
            if o["class"] == "space":
                space_polys[o["id"]] = (o["floor_id"], [P[v] for v in rings[0] if v in P])
        elif g["type"] == "LineString":
            if any(v not in V for v in g["vertices"]):
                r.err(f"object {o['id']}: onbekende vertex in LineString")
        elif g["type"] == "Point":
            if g["vertex"] not in V:
                r.err(f"object {o['id']}: onbekende vertex in Point")
        else:
            r.err(f"object {o['id']}: onbekend geometrietype {g['type']}")
    # ongebruikte edges
    for eid in E:
        if eid not in edge_users:
            r.warn(f"edge {eid} wordt door geen polygon gebruikt")
    # T-knopen (alleen tussen ruimte-vertices en ruimte-randen; elementen mogen op wanden liggen)
    space_v = {v for o in d["objects"] if o["class"] == "space" for r in o["geometry"]["rings"] for v in r}
    space_e = {e for o in d["objects"] if o["class"] == "space" for e in o["edge_ids"]}
    for eid, e in E.items():
        if eid not in space_e:
            continue
        a, b = e["v"]
        for vid in space_v:
            p = P[vid]
            if vid in (a, b) or V[vid]["frame_id"] != e["frame_id"]:
                continue
            if _on_segment_interior(p, P[a], P[b]):
                r.warn(f"T-knoop: vertex {vid} ligt op inwendige van edge {eid}")
    # overlap tussen ruimtes
    ids = list(space_polys)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            fa, pa = space_polys[ids[i]]
            fb, pb = space_polys[ids[j]]
            if fa != fb or len(pa) < 3 or len(pb) < 3:
                continue
            if not _bbox_hit(pa, pb):
                continue
            if not (_edges_cross(pa, pb) or _point_in_poly(_interior_pt(pa), pb) or _point_in_poly(_interior_pt(pb), pa)):
                continue
            ov = _poly_overlap_area(pa, pb)
            if ov > 16:  # >16 px² ~ 0.01 m² nominaal
                r.err(f"overlap ~{ov:.0f} px² tussen {ids[i]} en {ids[j]}")
    # ---- labels
    for l in d["labels"]:
        for oi in l["assigned_object_ids"]:
            if oi not in O:
                r.err(f"label {l['id']}: onbekend object {oi}")
            elif l["id"] not in O[oi]["label_ids"]:
                r.err(f"label {l['id']}: object {oi} verwijst niet terug")
        x1, y1, x2, y2 = l["bbox_px"]
        if not (x2 > x1 and y2 > y1):
            r.err(f"label {l['id']}: ongeldige bbox")
        if l.get("literal_text") is None and l.get("certainty") == "source":
            r.err(f"label {l['id']}: onleesbaar label kan geen certainty 'source' hebben")
    # ---- hedendaags gebruik gescheiden van bronlabel
    for o in d["objects"]:
        cu = o.get("current_use")
        if cu is not None and (not cu.get("value") or not cu.get("source") or cu.get("certainty") == "source"):
            r.err(f"object {o['id']}: current_use vereist value+source en is nooit 'source' (bronlabel staat apart)")
    # ---- connections
    for c in d["connections"]:
        if c["kind"] == "door" and not c.get("door_leaf_drawn"):
            r.err(f"verbinding {c['id']}: 'door' alleen bij getekend deurblad/draaicirkel; gebruik opening(_candidate)")
        for oi in c["connects"]:
            if oi not in O and oi != "exterior":
                r.err(f"verbinding {c['id']}: onbekend object {oi}")
        if c.get("edge_id"):
            if c["edge_id"] not in E:
                r.err(f"verbinding {c['id']}: onbekende edge")
            else:
                users = edge_users.get(c["edge_id"], set())
                for oi in c["connects"]:
                    if oi != "exterior" and oi not in users:
                        r.err(f"verbinding {c['id']}: edge niet gedeeld door {oi} (geen adjacency)")
    # ---- legal
    for s in d["legal_splits"]:
        if s.get("parent_id") and s["parent_id"] not in S:
            r.err(f"split {s['id']}: onbekende parent")
    for m in d["memberships"]:
        if m["object_id"] not in O:
            r.err(f"membership: onbekend object {m['object_id']}")
        if m["split_id"] not in S:
            r.err(f"membership: onbekende split {m['split_id']}")
        elif m["relation"] != "unknown":
            rights = {x["id"] for x in S[m["split_id"]].get("rights", [])}
            if m.get("right_id") and m["right_id"] not in rights:
                r.err(f"membership {m['object_id']}: onbekend recht {m['right_id']} in {m['split_id']}")
            if m.get("evidence") and m["evidence"].get("source_id") not in src:
                r.err(f"membership {m['object_id']}: evidence verwijst naar onbekende bron")
            if not m.get("evidence"):
                r.err(f"membership {m['object_id']}->{m['split_id']}: relation zonder evidence")
            if S[m["split_id"]]["boundary_status"] == "unknown" and m.get("certainty") in ("source",):
                r.err(f"membership {m['object_id']}: 'source' terwijl splitsgrens onbekend")
    ui = d["legal_split_ui"]
    if ui["enabled"]:
        if all(s["boundary_status"] == "unknown" for s in d["legal_splits"]):
            r.err("legal_split_ui.enabled terwijl geen enkele splitsgrens bekend is")
    elif not ui.get("reason"):
        r.err("legal_split_ui uitgeschakeld zonder reden")
    # ---- legacy
    for lk in d["legacy_links"]:
        if lk["object_id"] not in O:
            r.err(f"legacy {lk['legacy_id']}: onbekend object")
    # ---- coverage
    cov = d["coverage"]
    if not isinstance(cov.get("complete"), bool):
        r.err("coverage.complete moet boolean zijn")
    if cov.get("complete") is False and not cov.get("not_traced"):
        r.err("onvolledige dekking zonder not_traced-lijst")
    return r


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for p in argv[1:]:
        rep = validate(json.load(open(p, encoding="utf-8")))
        for w in rep.warnings:
            print(f"WARN  {p}: {w}")
        for e in rep.errors:
            print(f"ERROR {p}: {e}")
        print(f"{'OK' if rep.ok else 'FAIL'} {p}: {len(rep.errors)} fouten, {len(rep.warnings)} waarschuwingen")
        rc |= 0 if rep.ok else 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
