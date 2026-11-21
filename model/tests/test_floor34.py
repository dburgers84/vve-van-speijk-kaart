"""Tests 3e (p84) en 4e verdieping + daken (p85): kalibratie per blad (p85 via liniaal + overdracht p84), dekking, stabiele IDs
(obj_f3_*, obj_f4_*), juridisch, gemeten labels, vloerkeuze, nummercontrole over alle bladen."""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from validate import validate  # noqa: E402
from traces import f3_segments as F3, f4_segments as F4  # noqa: E402


def load(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


D3, D4 = load("f3.v2.json"), load("f4.v2.json")
ALL = {n: load(n) for n in ("bg.v2.json", "f1.v2.json", "f2.v2.json")}
NC = load("inventory/number_check.json")


def mem(D):
    return {(m["object_id"], m["split_id"]): m for m in D["memberships"]}


class TestCalibration(unittest.TestCase):
    def test_p84_bar_ruler(self):
        c = D3["calibrations"][0]
        self.assertEqual((c["id"], D3["frames"][0]["id"]), ("cal_p84_controls", "frm_p84_native"))
        self.assertAlmostEqual(c["checks"]["m_per_px_scale_bar_0_10m"], 10 / (747.6 - 352.25), places=6)
        self.assertAlmostEqual(c["checks"]["m_per_px_ruler_x_1to200"], 2 / ((783.47 - 390.43) / 5), places=6)
        self.assertGreaterEqual(c["rel_uncertainty"]["y"], c["checks"]["half_spread_rel"])

    def test_p85_transfer_and_rejected_bar(self):
        c = D4["calibrations"][0]
        ck = c["checks"]
        self.assertEqual(c["id"], "cal_p85_controls")
        self.assertAlmostEqual(ck["m_per_px_transfer_from_p84"], D3["calibrations"][0]["m_per_px_y"] * 1207 / 1205, places=6)
        self.assertLess(abs(ck["transfer_vs_ruler_pct"]), 0.6)
        self.assertGreater(abs(ck["rejected_bar_daken"]["vs_ruler_pct"]), 2.0, "verworpen balk blijft zichtbaar als afwijkend")
        self.assertNotIn("bar_0m", [p["id"] for p in c["control_points"]])
        self.assertGreaterEqual(c["rel_uncertainty"]["y"], D3["calibrations"][0]["rel_uncertainty"]["y"])

    def test_dimensions_use_own_calibration(self):
        for D, cal in ((D3, "cal_p84_controls"), (D4, "cal_p85_controls")):
            for e in D["edges"]:
                if e["dimension"]["status"] == "derived":
                    self.assertEqual(e["dimension"]["calibration_ref"], cal)


class TestCoverage(unittest.TestCase):
    def test_valid(self):
        for D in (D3, D4):
            r = validate(D)
            self.assertEqual(r.errors, [], r.errors[:5])
            self.assertIs(D["coverage"]["complete"], False)

    def test_segments(self):
        for n, F, D in (("f3_segments_p84.json", F3, D3), ("f4_segments_p85.json", F4, D4)):
            seg = load("inventory/" + n)
            self.assertEqual(seg["problems"], [])
            self.assertEqual(len(seg["segments"]), len(F.SEEDS))
            self.assertEqual(len([o for o in D["objects"] if o["id"].endswith(tuple(k for k, *_ in F.SEEDS))]), len(F.SEEDS))

    def test_woningen(self):
        w3 = sorted(int(o["index_number"]) for o in D3["objects"] if o["kind"] == "apartment_dwelling")
        w4 = sorted(int(o["index_number"]) for o in D4["objects"] if o["kind"] == "apartment_dwelling")
        self.assertEqual(w3, list(range(216, 226)) + list(range(230, 238)) + [246, 247, 256, 257, 258, 259, 264, 265])
        self.assertEqual(w4, [256, 257, 258, 259])

    def test_cuts_documented(self):
        self.assertEqual(len(F3.CUTS), 4)
        o = next(o for o in D3["objects"] if o.get("index_number") == "246")
        self.assertLess(o["geometry"]["rings"][0].__len__(), 40)
        self.assertIn("CUTS", next(s for s in F3.SEEDS if s[0] == "s052")[6])

    def test_labels_measured(self):
        for D in (D3, D4):
            c = D["coverage"]["counts"]
            self.assertGreaterEqual(c["labels_position_measured"] / c["labels_total"], 0.6)


class TestIdsLegal(unittest.TestCase):
    def test_fixtures(self):
        """Eerder uitgegeven sleutels blijven bestaan met dezelfde soort/nummer; de laatste fixture = huidige stand."""
        for n, F in ((3, F3), (4, F4)):
            now = {k: [kd, i] for k, _s, kd, _l, i, _h, _n in F.SEEDS}
            for v in ("0.1.0", "0.1.1"):
                with open(os.path.join(HERE, "fixtures", f"f{n}_seg_keys_v{v}.json")) as f:
                    fx = json.load(f)["keys"]
                for k, val in fx.items():
                    self.assertEqual(now.get(k), val, (n, v, k))
            self.assertEqual(now, fx)

    def test_ids_unique_across_floors(self):
        seen = set()
        for D in list(ALL.values()) + [D3, D4]:
            ids = {o["id"] for o in D["objects"]}
            self.assertFalse(ids & seen)
            seen |= ids
        for D, p in ((D3, "f3"), (D4, "f4")):
            for o in D["objects"]:
                self.assertRegex(o["id"], rf"^obj_{p}_seg_s\d{{3}}$")

    def test_rights(self):
        for D in (D3, D4):
            M = mem(D)
            for o in D["objects"]:
                if o["kind"] == "apartment_dwelling":
                    self.assertEqual(M[(o["id"], "ls_hoofdsplitsing")]["right_id"], "A-180")
                    self.assertEqual(M[(o["id"], "ls_ondersplitsing_woningen")]["right_id"], "O-" + o["index_number"])
                if o["class"] == "element":
                    self.assertNotIn((o["id"], "ls_hoofdsplitsing"), {k for k, v in M.items() if v["relation"] != "unknown"})
        M4 = mem(D4)
        self.assertEqual(M4[("obj_f4_seg_s017", "ls_hoofdsplitsing")]["right_id"], "A-179")
        M3 = mem(D3)
        self.assertEqual(M3[("obj_f3_seg_s074", "ls_hoofdsplitsing")]["right_id"], "A-180")
        self.assertEqual(M3[("obj_f3_seg_s074", "ls_ondersplitsing_woningen")]["relation"], "common")


class TestNumberCheck(unittest.TestCase):
    def test_totals(self):
        self.assertEqual((NC["woningen_found"], NC["bergingen_found"]), (85, 91))
        self.assertEqual(NC["woningen_missing"] + NC["bergingen_missing"], [])
        self.assertEqual(NC["duplicate_on_same_sheet"], {})
        self.assertEqual(NC["wrong_kind_for_range"], [])

    def test_multi_sheet_reported(self):
        multi = NC["woningen_on_multiple_sheets"]
        self.assertEqual(sorted(map(int, multi)), list(range(216, 226)) + list(range(230, 238)) + [256, 257, 258, 259])
        self.assertEqual(multi["256"], ["3e", "4e"])

    def test_reproducible(self):
        import number_check
        o = number_check.run()
        self.assertEqual(o, NC)


class TestViewer(unittest.TestCase):
    def test_floor_switch(self):
        with open(os.path.join(ROOT, "pilot", "index.html"), encoding="utf-8") as f:
            html = f.read()
        for t in ("pilot_data_f3.js", "pilot_data_f4.js", "PILOT_DATA_F3", "PILOT_DATA_F4", "floor=(1e|2e|3e|4e)", "'4e verdieping + daken'",
                  "m_per_px_transfer_from_p84", "roof_symbol"):
            self.assertIn(t, html)
        for n, v in ((3, "PILOT_DATA_F3"), (4, "PILOT_DATA_F4")):
            with open(os.path.join(ROOT, "pilot", f"pilot_data_f{n}.js"), encoding="utf-8") as f:
                self.assertIn(f"window.{v} =", f.read(200))


if __name__ == "__main__":
    unittest.main()
