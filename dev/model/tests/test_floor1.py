"""Tests 1e verdieping (p82): eigen kalibratie, dekking (bergingen 266-356, woningen), stabiele IDs, juridisch, viewer-vloerkeuze.
Draai: python3 -m unittest discover -s model/tests"""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from validate import validate  # noqa: E402
from traces import f1_segments as F  # noqa: E402

D = json.load(open(os.path.join(ROOT, "data", "f1.v2.json"), encoding="utf-8"))
BG = json.load(open(os.path.join(ROOT, "data", "bg.v2.json"), encoding="utf-8"))
CALJ = json.load(open(os.path.join(ROOT, "data", "inventory", "calibration_p82.json"), encoding="utf-8"))
O = {o["id"]: o for o in D["objects"]}
MEM = {(m["object_id"], m["split_id"]): m for m in D["memberships"]}
WONINGEN_1E = [181, 182, 185, 186, 187, 188, 189, 190, 191, 192, 193, 198, 199, 202, 203, 204, 205, 208, 209, 210, 211, 212, 213,
               214, 215, 226, 227, 228, 229, 238, 239, 240, 248, 249, 250, 251, 260, 261]


class TestCalibrationP82(unittest.TestCase):
    def setUp(self):
        self.c = D["calibrations"][0]

    def test_own_frame_and_calibration(self):
        self.assertEqual(self.c["id"], "cal_p82_controls")
        self.assertEqual(D["frames"][0]["id"], "frm_p82_native")
        self.assertEqual((D["frames"][0]["width_px"], D["frames"][0]["height_px"]), (7122, 10049))
        self.assertNotEqual(self.c["m_per_px_y"], BG["calibrations"][0]["m_per_px_y"], "p82 heeft een eigen schaal, niet die van p81")

    def test_values_from_bar_and_ruler(self):
        ck = self.c["checks"]
        self.assertAlmostEqual(ck["m_per_px_scale_bar_0_10m"], 10 / (728.7 - 335.5), places=6)
        self.assertAlmostEqual(ck["m_per_px_ruler_x_1to200"], 2 / ((773.49 - 379.34) / 5), places=6)
        self.assertAlmostEqual(self.c["m_per_px_y"], (ck["m_per_px_scale_bar_0_10m"] + ck["m_per_px_ruler_x_1to200"]) / 2, places=6)
        self.assertLess(abs(ck["bar_vs_ruler_pct"]), 0.5)
        self.assertAlmostEqual(CALJ["adopted"]["m_per_px"], self.c["m_per_px_y"], places=6)

    def test_estimated_margin_not_smaller_than_reading_tolerance(self):
        ru = self.c["rel_uncertainty"]
        self.assertGreaterEqual(ru["y"], self.c["checks"]["reading_tolerance_rel"])
        self.assertGreaterEqual(ru["y"], self.c["checks"]["half_spread_rel"])
        self.assertGreater(ru["x"], ru["y"], "x-as niet getoetst: ruimere marge")
        self.assertEqual(self.c["axis_status"]["x"], "assumed_isotropic_not_independently_verified")
        self.assertIn("GESCHATTE", self.c["note"])

    def test_dimensions_display_rounded(self):
        for e in D["edges"]:
            dm = e["dimension"]
            if dm["status"] == "derived":
                self.assertIn(dm["display"]["step_m"], (0.01, 0.1, 0.5))
                self.assertIn("geschatte marge", dm["display"]["text"])
                self.assertEqual(dm["calibration_ref"], "cal_p82_controls")


class TestCoverageP82(unittest.TestCase):
    def test_valid(self):
        r = validate(D)
        self.assertEqual(r.errors, [], r.errors[:5])

    def test_all_segments_present(self):
        seg = json.load(open(os.path.join(ROOT, "data", "inventory", "f1_segments_p82.json")))
        self.assertEqual(seg["problems"], [])
        self.assertEqual(len(seg["segments"]), len(F.SEEDS))
        for k, *_ in F.SEEDS:
            self.assertIn(f"obj_f1_seg_{k}", O)

    def test_all_bergingen_266_356_once(self):
        nums = sorted(int(o["index_number"]) for o in D["objects"] if o["kind"] == "storage_unit")
        self.assertEqual(nums, list(range(266, 357)))
        self.assertEqual(D["coverage"]["counts"]["bergingen_missing_266_356"], [])

    def test_woningen_on_sheet(self):
        nums = sorted(int(o["index_number"]) for o in D["objects"] if o["kind"] == "apartment_dwelling")
        self.assertEqual(nums, WONINGEN_1E)
        self.assertTrue(all(181 <= n <= 265 for n in nums))

    def test_not_complete(self):
        self.assertIs(D["coverage"]["complete"], False)
        self.assertTrue(D["coverage"]["not_traced"])

    def test_hatch_excluded_both_splits(self):
        hs = [o for o in D["objects"] if o["kind"] == "not_in_split_area"]
        self.assertEqual(len(hs), 2)
        for o in hs:
            for sp in ("ls_hoofdsplitsing", "ls_ondersplitsing_woningen"):
                self.assertEqual(MEM[(o["id"], sp)]["relation"], "excluded")

    def test_enclosing_segment_has_holes(self):
        o = O["obj_f1_seg_s108"]
        self.assertGreater(len(o["geometry"]["rings"]), 10, "bergingenblok binnen s108 moet als gaten staan (geen overlap)")

    def test_labels_marked_approximate(self):
        for lbl in D["labels"]:
            if lbl["id"].endswith("_n"):
                self.assertIn("BENADERD", lbl["note"])
                self.assertNotEqual(lbl["certainty"], "source")


class TestStableIdsP82(unittest.TestCase):
    def test_keys_fixture(self):
        fx = json.load(open(os.path.join(HERE, "fixtures", "f1_seg_keys_v0.1.0.json")))["keys"]
        now = {k: [kind, idx] for k, _s, kind, _l, idx, _h, _n in F.SEEDS}
        self.assertEqual(set(now), set(fx), "sleutels f1_seg gewijzigd: alleen via bewuste migratie")
        for k, v in fx.items():
            self.assertEqual(now[k][1], v[1], f"{k}: indexnummer gewijzigd")

    def test_id_format(self):
        for o in D["objects"]:
            self.assertRegex(o["id"], r"^obj_f1_seg_(s\d{3}|h\d)$")
            self.assertEqual(o["floor_id"], "1e")
        bg_ids = {o["id"] for o in BG["objects"]}
        self.assertFalse(bg_ids & set(O), "geen id-botsing tussen BG en 1e")


class TestLegalP82(unittest.TestCase):
    def test_woning_berging_rights(self):
        for o in D["objects"]:
            if o["kind"] in ("apartment_dwelling", "storage_unit"):
                h = MEM[(o["id"], "ls_hoofdsplitsing")]
                u = MEM[(o["id"], "ls_ondersplitsing_woningen")]
                self.assertEqual((h["relation"], h["right_id"]), ("private", "A-180"))
                self.assertEqual((u["relation"], u["right_id"]), ("private", "O-" + o["index_number"]))
                self.assertNotEqual(u["certainty"], "source")

    def test_179_never_in_ondersplitsing_private(self):
        for o in D["objects"]:
            h = MEM.get((o["id"], "ls_hoofdsplitsing"))
            if h and h["right_id"] == "A-179":
                self.assertNotEqual(MEM[(o["id"], "ls_ondersplitsing_woningen")]["relation"], "private")

    def test_a2_conflict_kept_open(self):
        o = next(s for s in D["legal_splits"] if s["id"] == "ls_ondersplitsing_woningen")
        self.assertTrue(any("A-2" in u for u in o["unresolved"]))
        self.assertEqual(len(o["rights"]), 176)


class TestViewerFloors(unittest.TestCase):
    def test_floor_switch(self):
        html = open(os.path.join(ROOT, "pilot", "index.html"), encoding="utf-8").read()
        self.assertIn("floor=1e", html)
        self.assertIn("pilot_data_f1.js", html)
        self.assertIn("PILOT_DATA_F1", html)
        self.assertIn("fill-rule", html, "gaten (binnenringen) moeten als gat getekend worden")
        js = open(os.path.join(ROOT, "pilot", "pilot_data_f1.js"), encoding="utf-8").read(200)
        self.assertIn("window.PILOT_DATA_F1 =", js)

    def test_overlay_public_only_published_jpg(self):
        for ov in D["reference_overlays"]:
            self.assertEqual(ov["image"], "img/plan_1e.jpg")
        self.assertFalse(D["sources"][0]["publish_native_raster"])


@unittest.skipIf(__import__("importlib").util.find_spec("cv2") is None, "opencv ontbreekt")
class TestDiagonalHatch(unittest.TestCase):
    def test_crosshatch_detected_dense_text_not(self):
        import cv2
        import numpy as np
        import segment_bg as SB
        SB.S = F
        img = np.zeros((400, 800), np.uint8)
        for t in range(-400, 800, 16):   # kruisarcering links
            cv2.line(img, (t, 0), (t + 400, 400), 1, 1)
            cv2.line(img, (t + 400, 0), (t, 400), 1, 1)
        img[:, 360:] = 0
        for y in range(40, 380, 34):     # dichte tekst + omcirkelde nummers rechts
            for x in range(440, 760, 70):
                cv2.putText(img, "273", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, 1, 2)
                cv2.ellipse(img, (x - 12, y - 8), (10, 14), 0, 0, 360, 1, 2)
        m = SB.diagonal_hatch_mask(img)
        self.assertGreater(m[50:350, 50:300].mean(), 0.95)
        self.assertLess(m[:, 440:].mean(), 0.02)


if __name__ == "__main__":
    unittest.main()
