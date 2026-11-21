"""Regressietests lijnwerk (tools/linework.py) en BG-segmentatie v0.4: tekst/indexcirkels geen wand, geen gaten/inkepingen,
stabiele IDs, afronding met geschatte marge. Draai: python3 -m unittest discover -s model/tests"""
import copy, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from validate import validate  # noqa: E402

try:
    import cv2
    import numpy as np
    from linework import bridged_mask, simplify  # noqa: E402
except ImportError:  # pragma: no cover
    cv2 = None

from traces import bg_segments as S  # noqa: E402

D = json.load(open(os.path.join(ROOT, "data", "bg.v2.json"), encoding="utf-8"))
V = {v["id"]: (v["x_px"], v["y_px"]) for v in D["vertices"]}
O = {o["id"]: o for o in D["objects"]}


def ring(o):
    return [V[i] for i in o["geometry"]["rings"][0]]


def pip(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def dist_to_poly(p, poly):
    best = 1e9
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i - 1], poly[i]
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / float(dx * dx + dy * dy or 1)))
        best = min(best, ((x1 + t * dx - p[0]) ** 2 + (y1 + t * dy - p[1]) ** 2) ** 0.5)
    return best


def synth(circle_touches_wall=False):
    """Kamer 300x200 px (lijn 2 px) met tekst en een omcirkelde '180' binnenin."""
    img = np.zeros((260, 360), np.uint8)
    cv2.rectangle(img, (30, 30), (330, 230), 1, 2)
    cv2.putText(img, "entree", (80, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 1, 2)
    cx = 309 if circle_touches_wall else 250
    cv2.ellipse(img, (cx, 80), (20, 30), 0, 0, 360, 1, 2)
    cv2.putText(img, "180", (cx - 17, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1, 1)
    return img, (cx - 22, 48, cx + 22, 112)


def free_components(mask):
    wall = cv2.dilate(mask, np.ones((3, 3), np.uint8))
    n, lab = cv2.connectedComponents((1 - wall).astype(np.uint8), connectivity=4)
    return n, lab


@unittest.skipIf(cv2 is None, "opencv/numpy niet beschikbaar")
class LineworkSynthetic(unittest.TestCase):
    def test_text_and_index_circle_are_not_walls(self):
        img, box = synth(False)
        m, _ = bridged_mask(img, 31, 5)
        x0, y0, x1, y1 = box
        self.assertEqual(int(m[y0:y1, x0:x1].sum()), 0, "omcirkelde 180 mag geen wandinkt blijven")
        self.assertEqual(int(m[100:150, 75:200].sum()), 0, "tekst 'entree' mag geen wandinkt blijven")
        self.assertGreater(int(m[29:33, 40:320].sum()), 250, "wandlijn moet blijven")

    def test_room_without_holes_or_notches(self):
        img, _ = synth(False)
        m, _ = bridged_mask(img, 31, 5)
        n, lab = free_components(m)
        inner = lab[130, 180]
        comp = (lab == inner).astype(np.uint8)
        # binnenruimte = volledige rechthoek binnen de lijn (geen gaten door tekst/cirkel)
        filled = comp.sum()
        expect = (330 - 30 - 4) * (230 - 30 - 4)
        self.assertGreater(filled, expect * 0.97)
        cs, _ = cv2.findContours(comp, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        self.assertEqual(len(cs), 1, "geen binnencontouren (gaten)")

    def test_circle_touching_wall_removed_via_text_box(self):
        img, box = synth(True)
        m, _ = bridged_mask(img, 31, 5, text_boxes=[box], symbol_boxes=[box])
        x0, y0, x1, y1 = box
        # alleen de wandlijn zelf (x 329..331) mag binnen de box overblijven
        rest = m[y0:y1, x0:327]
        self.assertEqual(int(rest.sum()), 0)
        self.assertGreater(int(m[60:100, 328:333].sum()), 60, "wand naast de cirkel blijft intact")

    def test_broken_line_stub_stays_barrier(self):
        img = np.zeros((200, 300), np.uint8)
        cv2.rectangle(img, (20, 20), (280, 180), 1, 2)
        cv2.line(img, (20, 100), (150, 100), 1, 2)       # scheidingslijn ...
        cv2.line(img, (153, 100), (165, 100), 1, 2)      # ... met kort stompje na 2 px uitval
        cv2.line(img, (168, 100), (280, 100), 1, 2)
        m, _ = bridged_mask(img, 31, 5)
        n, lab = free_components(m)
        self.assertNotEqual(lab[60, 150], lab[140, 150], "onderbroken scheidingslijn blijft barrière")

    def test_simplify_drops_jogs_keeps_real_recess(self):
        poly = [[0, 0], [100, 0], [100, 50], [101, 52], [100, 54], [100, 100], [60, 100], [60, 80], [40, 80], [40, 100], [0, 100]]
        out = simplify(poly, 60)
        self.assertNotIn([101, 52], out)
        for p in ([60, 80], [40, 80]):
            self.assertIn(p, out, "echte inspringing (800 px2) blijft")


class SegmentationDataset(unittest.TestCase):
    def test_index_circles_no_edges_no_holes(self):
        """Omcirkelde 180: geen enkel segmenthoekpunt in de ring; het vak omsluit de hele ring (geen inkeping/gat)."""
        self.assertEqual(set(S.IDX180), {"s039", "s052", "s061"})
        for key, (x0, y0, x1, y1) in S.IDX180.items():
            self.assertLessEqual(x1 - x0, 60)
            self.assertLessEqual(y1 - y0, 80)
            poly = ring(O[f"obj_bg_seg_{key}"])
            import math
            cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
            pts = [(cx + rx * math.cos(t * math.pi / 8), cy + ry * math.sin(t * math.pi / 8)) for t in range(16)] + [(cx, cy)]
            for p in pts:   # ring mag tegen de wand liggen: punt binnen vak of <= 3 px van de vakgrens
                self.assertTrue(pip(p, poly) or dist_to_poly(p, poly) <= 3, f"{key}: ring-punt {p} buiten vak")
            for o in D["objects"]:
                if o["id"].startswith("obj_bg_seg_") and o["geometry"].get("rings"):
                    for x, y in ring(o):
                        self.assertFalse(x0 + 3 < x < x1 - 3 and y0 + 3 < y < y1 - 3,
                                         f"{o['id']} heeft een hoekpunt in indexcirkel {key}")
            lbl = [l for l in D["labels"] if l["id"] == f"lbl_bg_seg_{key}_i180"][0]
            self.assertEqual(lbl["bbox_px"], [x0, y0, x1, y1])

    def test_core_cells_clean(self):
        """s039 (entree kern A): weinig hoekpunten, geen rafels (geen hoekdriehoek < MIN_JOG_AREA_PX2)."""
        from linework import _tri
        for key in ("s039", "s042", "s052", "s052b", "s061"):
            poly = ring(O[f"obj_bg_seg_{key}"])
            self.assertLessEqual(len(poly), 14, key)
            for i in range(len(poly)):
                self.assertGreaterEqual(_tri(poly[i - 1], poly[i], poly[(i + 1) % len(poly)]), S.MIN_JOG_AREA_PX2, key)

    def test_text_labels_do_not_cut_spaces(self):
        """Geen segmenthoekpunt binnen een tekstlabel-box van zijn eigen vak (tekst is geen grens)."""
        L = {l["id"]: l for l in D["labels"]}
        for o in D["objects"]:
            if not o["id"].startswith("obj_bg_seg_") or o["class"] != "space" or o["kind"] == "not_in_split_area":
                continue
            for lid in o["label_ids"]:
                x0, y0, x1, y1 = L[lid]["bbox_px"]
                if L[lid]["category"] == "index_number":
                    continue
                inside = [(x, y) for x, y in ring(o) if x0 + 3 < x < x1 - 3 and y0 + 3 < y < y1 - 3]
                self.assertEqual(inside, [], f"{o['id']}: hoekpunt binnen label {lid}")

    def test_multi_label_cells_resolved_where_source_allows(self):
        self.assertEqual(O["obj_bg_seg_s060"]["kind"], "commercial_unit")
        self.assertEqual(O["obj_bg_seg_s060n"]["kind"], "commercial_unit")
        self.assertIn("bgD_s060", [c[0] for c in S.CUTS])
        s126 = O["obj_bg_seg_s126"]
        self.assertEqual(s126["kind"], "service_space")
        self.assertEqual(s126["source_label_text"], "expeditie")
        self.assertFalse(any(l["literal_text"] == "bedrijfs-ruimte" for l in D["labels"] if l["id"] in s126["label_ids"]))
        self.assertEqual(O["obj_bg_seg_s079"]["kind"], "commercial_multi_unresolved")   # geen tussenwand getekend

    def test_segment_ids_stable_since_v030(self):
        keys = json.load(open(os.path.join(HERE, "fixtures", "bg_seg_keys_v0.3.0.json")))["keys"]
        for k in keys:
            self.assertIn(f"obj_bg_seg_{k}", O, f"ID verdwenen: {k}")
        new = {o["id"][len("obj_bg_seg_"):] for o in D["objects"] if o["id"].startswith("obj_bg_seg_") and o["kind"] != "column"} - set(keys)
        self.assertEqual(new, {"s019b", "s040b", "s060n"})

    def test_display_rounding_with_estimated_margin(self):
        for e in D["edges"]:
            dm = e["dimension"]
            if dm["status"] != "derived":
                continue
            d = dm["display"]
            self.assertIn("geschatte marge", d["text"])
            self.assertGreaterEqual(d["margin_m"], dm["uncertainty_m"])
            if dm["uncertainty_m"] >= 0.05:
                self.assertAlmostEqual(round(d["length_m"], 1), d["length_m"])

    def test_too_fine_rounding_rejected(self):
        d = copy.deepcopy(D)
        e = next(e for e in d["edges"] if e["dimension"]["status"] == "derived" and e["dimension"]["uncertainty_m"] >= 0.05)
        e["dimension"]["display"].update(step_m=0.01, length_m=e["dimension"]["length_m"])
        self.assertTrue(any("afrondingsstap" in m for m in validate(d).errors))
        d = copy.deepcopy(D)
        e = next(e for e in d["edges"] if e["dimension"]["status"] == "derived")
        e["dimension"]["display"]["margin_m"] = e["dimension"]["uncertainty_m"] / 3
        self.assertTrue(any("getoonde marge" in m for m in validate(d).errors))


if __name__ == "__main__":
    unittest.main()
