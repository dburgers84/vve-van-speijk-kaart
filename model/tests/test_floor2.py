"""Tests 2e verdieping (p83): eigen kalibratie, dekking (39 woningen, geen bergingen), stabiele IDs (obj_f2_*), juridisch,
gemeten labelposities, vloerkeuze viewer, meetfunctie labels. Draai: python3 -m unittest discover -s model/tests"""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from validate import validate  # noqa: E402
from traces import f2_segments as F  # noqa: E402


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


D, D1, BG = load("f2.v2.json"), load("f1.v2.json"), load("bg.v2.json")
CALJ = load("inventory/calibration_p83.json")
O = {o["id"]: o for o in D["objects"]}
MEM = {(m["object_id"], m["split_id"]): m for m in D["memberships"]}
WONINGEN_2E = [183, 184, 194, 195, 196, 197, 200, 201, 206, 207, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225,
               230, 231, 232, 233, 234, 235, 236, 237, 241, 242, 243, 244, 245, 252, 253, 254, 255, 262, 263]


class TestCalibrationP83(unittest.TestCase):
    def setUp(self):
        self.c = D["calibrations"][0]

    def test_own_frame(self):
        self.assertEqual(self.c["id"], "cal_p83_controls")
        self.assertEqual(D["frames"][0]["id"], "frm_p83_native")
        self.assertEqual((D["frames"][0]["width_px"], D["frames"][0]["height_px"]), (7120, 10055))
        others = {BG["calibrations"][0]["m_per_px_y"], D1["calibrations"][0]["m_per_px_y"]}
        self.assertNotIn(self.c["m_per_px_y"], others)

    def test_values(self):
        ck = self.c["checks"]
        self.assertAlmostEqual(ck["m_per_px_scale_bar_0_10m"], 10 / (805.6 - 408.3), places=6)
        self.assertAlmostEqual(ck["m_per_px_ruler_x_1to200"], 2 / ((812.14 - 419.07) / 5), places=6)
        self.assertAlmostEqual(CALJ["adopted"]["m_per_px"], self.c["m_per_px_y"], places=6)
        self.assertLess(abs(ck["bar_vs_ruler_pct"]), 1.5)

    def test_margin(self):
        ru = self.c["rel_uncertainty"]
        self.assertGreaterEqual(ru["y"], self.c["checks"]["half_spread_rel"])
        self.assertGreaterEqual(ru["y"], self.c["checks"]["reading_tolerance_rel"])
        self.assertGreater(ru["x"], ru["y"])
        for e in D["edges"]:
            if e["dimension"]["status"] == "derived":
                self.assertEqual(e["dimension"]["calibration_ref"], "cal_p83_controls")
                self.assertIn("geschatte marge", e["dimension"]["display"]["text"])


class TestCoverageP83(unittest.TestCase):
    def test_valid(self):
        r = validate(D)
        self.assertEqual(r.errors, [], r.errors[:5])

    def test_all_segments(self):
        seg = load("inventory/f2_segments_p83.json")
        self.assertEqual(seg["problems"], [])
        self.assertEqual(len(seg["segments"]), len(F.SEEDS))
        self.assertEqual(len(seg["hatch"]), 1)

    def test_woningen(self):
        nums = sorted(int(o["index_number"]) for o in D["objects"] if o["kind"] == "apartment_dwelling")
        self.assertEqual(nums, WONINGEN_2E)
        self.assertFalse(set(nums) & {int(o["index_number"]) for o in D1["objects"] if o["kind"] == "apartment_dwelling"},
                         "een woningnummer staat niet op twee verdiepingen")
        self.assertFalse([o for o in D["objects"] if o["kind"] == "storage_unit"])

    def test_not_complete(self):
        self.assertIs(D["coverage"]["complete"], False)
        self.assertTrue(D["coverage"]["not_traced"])

    def test_labels_mostly_measured(self):
        c = D["coverage"]["counts"]
        self.assertGreaterEqual(c["labels_position_measured"] / c["labels_total"], 0.8)


class TestIdsLegalP83(unittest.TestCase):
    def test_keys_fixture(self):
        with open(os.path.join(HERE, "fixtures", "f2_seg_keys_v0.1.0.json")) as f:
            fx = json.load(f)["keys"]
        now = {k: [kind, idx] for k, _s, kind, _l, idx, _h, _n in F.SEEDS}
        self.assertEqual(set(now), set(fx))
        for k, v in fx.items():
            self.assertEqual(now[k][1], v[1])

    def test_id_format_no_collision(self):
        for o in D["objects"]:
            self.assertRegex(o["id"], r"^obj_f2_seg_(s\d{3}|h\d)$")
            self.assertEqual(o["floor_id"], "2e")
        self.assertFalse({o["id"] for o in BG["objects"] + D1["objects"]} & set(O))

    def test_rights(self):
        for o in D["objects"]:
            if o["kind"] == "apartment_dwelling":
                self.assertEqual(MEM[(o["id"], "ls_hoofdsplitsing")]["right_id"], "A-180")
                self.assertEqual(MEM[(o["id"], "ls_ondersplitsing_woningen")]["right_id"], "O-" + o["index_number"])
            h = MEM.get((o["id"], "ls_hoofdsplitsing"))
            if h and h["right_id"] == "A-179":
                self.assertNotEqual(MEM[(o["id"], "ls_ondersplitsing_woningen")]["relation"], "private")
        for k in F.IDX180_KEYS:
            if O[f"obj_f2_seg_{k}"]["class"] == "space":
                self.assertEqual(MEM[(f"obj_f2_seg_{k}", "ls_hoofdsplitsing")]["right_id"], "A-180")
        h = O["obj_f2_seg_h1"]
        self.assertEqual(MEM[(h["id"], "ls_hoofdsplitsing")]["relation"], "excluded")

    def test_a2_conflict_open(self):
        o = next(s for s in D["legal_splits"] if s["id"] == "ls_ondersplitsing_woningen")
        self.assertTrue(any("A-2" in u for u in o["unresolved"]))


class TestViewerP83(unittest.TestCase):
    def test_floor_switch(self):
        with open(os.path.join(ROOT, "pilot", "index.html"), encoding="utf-8") as f:
            html = f.read()
        for t in ("pilot_data_f2.js", "PILOT_DATA_F2", "floor=(1e|2e|3e|4e)", "'2e verdieping'"):
            self.assertIn(t, html)
        with open(os.path.join(ROOT, "pilot", "pilot_data_f2.js"), encoding="utf-8") as f:
            self.assertIn("window.PILOT_DATA_F2 =", f.read(200))
        self.assertEqual([ov["image"] for ov in D["reference_overlays"]], ["img/plan_2e.jpg"])


class TestMeasureLabels(unittest.TestCase):
    def test_synthetic_number_and_circle(self):
        try:
            import cv2
            import numpy as np
        except ImportError:  # pragma: no cover
            self.skipTest("opencv ontbreekt")
        import measure_labels as ML
        raw = np.zeros((600, 400), np.uint8)
        cv2.rectangle(raw, (20, 20), (380, 580), 1, 2)
        for i in range(3):                      # gedraaid nummer: 3 cijferblokken onder elkaar (60x42)
            cv2.rectangle(raw, (200, 200 + i * 52), (260, 242 + i * 52), 1, 2)
        for i in range(3):                      # '180' in een ellips: moet NIET als (klein) nummer gelden
            cv2.rectangle(raw, (80, 100 + i * 18), (100, 112 + i * 18), 1, 1)
        cv2.ellipse(raw, (90, 125), (25, 45), 0, 0, 360, 1, 2)
        poly = [[22, 22], [378, 22], [378, 578], [22, 578]]
        isl = ML.islands(raw, poly, [])
        b = ML.pick(ML.columns(isl, ML.BIG), 3, 1, (230, 280))
        self.assertIsNotNone(b)
        self.assertEqual(b[:4], [199, 199, 262, 348])
        self.assertIsNone(ML.pick(ML.columns(isl, ML.SMALL), 3, 0, (90, 125), raw))


if __name__ == "__main__":
    unittest.main()
