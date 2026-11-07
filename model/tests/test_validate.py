"""Tests voor model/validate.py en de pilotdataset. Draai: python3 -m unittest discover -s model/tests"""
import copy, json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from validate import validate  # noqa: E402

PILOT = os.path.join(ROOT, "data", "bg.v2.json")
STABLE = os.path.join(HERE, "fixtures", "stable_ids_v0.1.json")


def load():
    with open(PILOT, encoding="utf-8") as f:
        return json.load(f)


def errs(d):
    return validate(d).errors


class PilotDataset(unittest.TestCase):
    def test_pilot_is_valid(self):
        rep = validate(load())
        self.assertEqual(rep.errors, [])

    def test_pilot_is_declared_incomplete(self):
        d = load()
        self.assertIs(d["coverage"]["complete"], False)
        self.assertTrue(d["coverage"]["not_traced"])

    def test_no_fake_precision(self):
        d = load()
        cal = d["calibrations"][0]
        for e in d["edges"]:
            dm = e["dimension"]
            self.assertIn(dm["status"], {"source", "derived", "unknown"})
            if dm["status"] == "unknown":
                self.assertIsNone(dm["length_m"])
            if dm["status"] == "derived":
                # gecontroleerde kalibratie: altijd een onzekerheid, nooit 0
                self.assertEqual(dm["uncertainty_status"], "estimated")
                self.assertGreaterEqual(dm["uncertainty_m"], 0.01)
                self.assertEqual(dm["calibration_ref"], cal["id"])
            if dm["status"] == "source":
                self.fail("geen bronmaten op de BG-tekening gevonden; 'source' mag niet voorkomen")

    def test_calibration_from_main_plan_scale_bar_one_axis_only(self):
        cal = load()["calibrations"][0]
        self.assertEqual(cal["status"], "controls_checked_one_axis")
        self.assertEqual(cal["axis_status"]["x"], "assumed_isotropic_not_independently_verified")
        self.assertTrue(cal["axis_status"]["y"].startswith("checked"))
        ids = {c["id"] for c in cal["control_points"]}
        self.assertTrue({"bar_0m", "bar_10m", "ruler_0cm", "ruler_5cm"} <= ids)
        ck = cal["checks"]
        bar = 10.0 / (830.3 - 443.3)
        self.assertAlmostEqual(ck["m_per_px_scale_bar_0_10m"], bar, places=5)
        self.assertAlmostEqual(ck["m_per_px_ruler_x_1to200"], 2.0 / ((869.62 - 477.27) / 5), places=5)
        # gekozen waarde ligt tussen de twee controles; onzekerheid dekt beide
        lo, hi = sorted((ck["m_per_px_scale_bar_0_10m"], ck["m_per_px_ruler_x_1to200"]))
        self.assertTrue(lo <= cal["m_per_px_y"] <= hi)
        self.assertGreaterEqual(cal["m_per_px_y"] * (1 + cal["rel_uncertainty"]["y"]) + 1e-7, hi)
        self.assertGreater(cal["rel_uncertainty"]["x"], cal["rel_uncertainty"]["y"])
        self.assertIn("1:1000", cal["excludes"])

    def test_lengths_use_adopted_scale(self):
        import math
        d = load()
        cal = d["calibrations"][0]
        V = {v["id"]: v for v in d["vertices"]}
        e = next(e for e in d["edges"] if e["id"] == "e_bg_core_A_B")
        (a, b) = e["v"]
        L = math.hypot((V[b]["x_px"] - V[a]["x_px"]) * cal["m_per_px_x"], (V[b]["y_px"] - V[a]["y_px"]) * cal["m_per_px_y"])
        self.assertAlmostEqual(e["dimension"]["length_m"], round(L, 2), places=2)
        # ~1 % langer dan de oude nominale 0,0254 m/px
        nominal = math.hypot((V[b]["x_px"] - V[a]["x_px"]) * 0.0254, (V[b]["y_px"] - V[a]["y_px"]) * 0.0254)
        self.assertGreater(e["dimension"]["length_m"], nominal)

    def test_legal_memberships_are_evidenced_not_exact(self):
        d = load()
        self.assertTrue(d["legal_split_ui"]["enabled"])
        self.assertIn("Gedeeltelijk", d["legal_split_ui"]["reason"])
        self.assertTrue(all(s["boundary_status"] != "traced" for s in d["legal_splits"]))
        claimed = [m for m in d["memberships"] if m["relation"] != "unknown"]
        self.assertTrue(claimed)
        for m in claimed:
            self.assertIn(m["certainty"], ("probable", "uncertain"))
            self.assertTrue(m["evidence"]["note"])
        # alleen ruimtes met omcirkeld 180 krijgen 'probable' voor A-180
        prob = {m["object_id"] for m in claimed if m.get("right_id") == "A-180" and m["certainty"] == "probable"}
        self.assertEqual(prob, {"obj_bg_core_trap180", "obj_bg_kiel_entree", "obj_bg_seg_s039", "obj_bg_seg_s052", "obj_bg_seg_s061"})
        labs = {l["id"]: l for l in d["labels"]}
        O = {o["id"]: o for o in d["objects"]}
        for oid in prob:
            self.assertTrue(any(labs[i]["literal_text"] == "180" for i in O[oid]["label_ids"]), oid)
        # A-179 'probable' alleen waar een 179-index in het vak staat
        p179 = {m["object_id"] for m in claimed if m.get("right_id") == "A-179" and m["certainty"] == "probable"}
        self.assertEqual(len(p179), 5)
        for oid in p179:
            self.assertTrue(any(labs[i]["literal_text"] == "179" for i in O[oid]["label_ids"]), oid)

    def test_legal_splits_are_nested_not_disjoint(self):
        d = load()
        S = {s["id"]: s for s in d["legal_splits"]}
        onder = S["ls_ondersplitsing_woningen"]
        self.assertEqual(onder["parent_id"], "ls_hoofdsplitsing")
        self.assertEqual(onder["nested_in_right"], "A-180")
        self.assertIn("A-179", S["ls_hoofdsplitsing"]["scope"])
        self.assertIn("A-180", S["ls_hoofdsplitsing"]["scope"])
        self.assertTrue(any("A-2" in u for u in onder["unresolved"]))
        H = {m["object_id"]: m for m in d["memberships"] if m["split_id"] == "ls_hoofdsplitsing"}
        for m in d["memberships"]:
            if m["split_id"] == "ls_ondersplitsing_woningen" and m["relation"] in ("common", "private"):
                # binnen de ondersplitsing => in de hoofdsplitsing A-180 of nog onbekend, nooit A-179/uitgesloten
                h = H[m["object_id"]]
                self.assertIn(h["right_id"], ("A-180", None), m["object_id"])
                self.assertNotEqual(h["relation"], "excluded")
        for m in d["memberships"]:
            if m["split_id"] == "ls_hoofdsplitsing" and m.get("right_id") == "A-179":
                u = next(x for x in d["memberships"] if x["object_id"] == m["object_id"] and x["split_id"] == "ls_ondersplitsing_woningen")
                self.assertIn(u["relation"], ("excluded", "unknown"))

    def test_hatched_not_in_split(self):
        d = load()
        h = [o for o in d["objects"] if o["kind"] == "not_in_split_area"]
        self.assertEqual(len(h), 2)
        for o in h:
            ms = [m for m in d["memberships"] if m["object_id"] == o["id"]]
            self.assertTrue(all(m["relation"] == "excluded" for m in ms))

    def test_broad_bg_coverage_and_honest_unresolved(self):
        d = load()
        cov = d["coverage"]
        self.assertFalse(cov["complete"])
        self.assertTrue(any("1e" in x for x in cov["not_traced"]))
        spaces = [o for o in d["objects"] if o["class"] == "space"]
        self.assertGreaterEqual(len(spaces), 90)
        unres = [o for o in spaces if o["certainty"] == "unresolved"]
        self.assertGreaterEqual(len(unres), 15)
        for o in unres:
            self.assertTrue(o["evidence"].get("note") or o["kind"].endswith("unresolved"), o["id"])
        for o in spaces:
            self.assertTrue(o["edge_ids"] and o["display_name"])
        self.assertGreaterEqual(sum(o["kind"] == "wall_band" for o in d["objects"]), 30)
        self.assertEqual(sum(o["kind"] == "service_corridor" for o in d["objects"]), 3)

    def test_private_raster_not_published(self):
        d = load()
        for s in d["sources"]:
            self.assertFalse(s["publish_native_raster"])

    def test_every_space_clickable_has_name_and_edges(self):
        d = load()
        for o in d["objects"]:
            self.assertTrue(o["display_name"])
            if o["class"] == "space":
                self.assertGreaterEqual(len(o["edge_ids"]), 3)

    def test_shared_boundaries_are_single_edges(self):
        d = load()
        users = {}
        for o in d["objects"]:
            for e in o["edge_ids"]:
                users.setdefault(e, []).append(o["id"])
        shared = [e for e, u in users.items() if len(u) == 2]
        self.assertGreater(len(shared), 10)

    def test_ids_are_stable_across_rebuild(self):
        """Alle ids uit pilot v0.1 bestaan nog (ids volgen trace-sleutels, niet posities)."""
        d = load()
        with open(STABLE) as f:
            old = json.load(f)
        for coll in ("objects", "vertices", "edges"):
            have = {x["id"] for x in d[coll]}
            missing = [i for i in old[coll] if i not in have]
            self.assertEqual(missing, [], coll)

    def test_two_regions_and_commercial_unit(self):
        d = load()
        self.assertGreaterEqual(len(d["regions"]), 2)
        self.assertTrue(any(o["kind"] == "commercial_unit" for o in d["objects"]))

    def test_columns_visually_reviewed(self):
        d = load()
        rev = json.load(open(os.path.join(ROOT, "data", "inventory", "columns_review_p81.json")))["verdicts"]
        rejected = {(v["x"], v["y"]) for v in rev if v["verdict"] == "rejected"}
        self.assertEqual(len(rejected), 10)
        V = {v["id"]: v for v in d["vertices"]}
        cols = [o for o in d["objects"] if o["kind"] == "column" and o["evidence"]["method"].startswith("auto_detect")]
        self.assertGreaterEqual(len(cols), 240)
        for o in cols:
            self.assertEqual(o["review_status"], "reviewed")
            r = o["geometry"]["rings"][0]
            cx = round(sum(V[i]["x_px"] for i in r) / 4)
            cy = round(sum(V[i]["y_px"] for i in r) / 4)
            self.assertNotIn((cx, cy), rejected, o["id"])
        self.assertEqual(sum(o["certainty"] == "uncertain" for o in cols), 12)

    def test_no_treads_or_doors_invented(self):
        d = load()
        self.assertFalse(any("tread" in o["kind"] or "door" in o["kind"] for o in d["objects"]))
        self.assertTrue(any("treden" in x for x in d["coverage"]["not_traced"]))

    def test_columns_and_details_are_clickable_elements(self):
        d = load()
        cols = [o for o in d["objects"] if o["kind"] == "column"]
        self.assertGreaterEqual(len(cols), 4)
        for o in cols:
            self.assertEqual(o["class"], "element")
            self.assertTrue(o["display_name"] and o["evidence"]["method"])
        self.assertTrue(any(o["kind"] == "facade_frame_strip" for o in d["objects"]))

    def test_source_label_and_current_use_separate(self):
        d = load()
        cont = [o for o in d["objects"] if o["kind"] == "container_room"]
        self.assertEqual(len(cont), 4)
        for o in cont:
            self.assertEqual(o["source_label_text"], "container-ruimte")
            self.assertEqual(o["current_use"]["value"], "fietsenberging")
            # gebruiker heeft bevestigd dat ALLE containerruimtes omgebouwd zijn: niet 'probable' o.b.v. oude tekst
            self.assertEqual(o["current_use"]["certainty"], "user_confirmed")
            self.assertIn("Gebruiker", o["current_use"]["source"])

    def test_no_door_claimed_without_leaf(self):
        d = load()
        for c in d["connections"]:
            self.assertNotEqual(c["kind"], "door")

    def test_public_overlay_is_existing_plan_jpg(self):
        d = load()
        for ov in d["reference_overlays"]:
            self.assertTrue(ov["image"].startswith("img/plan_"))
            self.assertTrue(os.path.exists(os.path.join(os.path.dirname(ROOT), ov["image"])))


class NegativeCases(unittest.TestCase):
    def setUp(self):
        self.d = load()

    def edge(self, status):
        return next(e for e in self.d["edges"] if e["dimension"]["status"] == status)

    def test_unknown_with_length_rejected(self):
        self.edge("unknown")["dimension"]["length_m"] = 1.0
        self.assertTrue(any("unknown vereist length_m null" in m for m in errs(self.d)))

    def test_derived_without_uncertainty_rejected(self):
        dm = self.edge("derived")["dimension"]
        dm["uncertainty_m"] = None
        dm["uncertainty_status"] = "unknown"
        self.assertTrue(any("gecontroleerde kalibratie vereist uncertainty_m" in m for m in errs(self.d)))

    def test_too_small_uncertainty_rejected(self):
        e = max(self.d["edges"], key=lambda e: e["length_px"] if e["dimension"]["status"] == "derived" else 0)
        e["dimension"]["uncertainty_m"] = 0.0
        self.assertTrue(any("kleiner dan schaalonzekerheid" in m for m in errs(self.d)))

    def test_both_axes_checked_claim_rejected(self):
        self.d["calibrations"][0]["axis_status"]["x"] = "checked_against_scale_bar_and_ruler"
        self.assertTrue(any("beide assen" in m for m in errs(self.d)))

    def test_derived_with_invented_uncertainty_rejected(self):
        self.d["calibrations"][0]["status"] = "nominal_unverified"
        self.d["calibrations"][0].pop("rel_uncertainty")
        self.d["calibrations"][0]["uncertainty_status"] = "unknown"
        dm = self.edge("derived")["dimension"]
        dm["uncertainty_m"] = 0.01
        dm["uncertainty_status"] = "estimated"
        self.assertTrue(any("fictieve exactheid" in m for m in errs(self.d)))

    def test_derived_wrong_length_rejected(self):
        self.edge("derived")["dimension"]["length_m"] += 0.5
        self.assertTrue(any("!= afgeleid" in m for m in errs(self.d)))

    def test_derived_without_calibration_rejected(self):
        self.edge("derived")["dimension"]["calibration_ref"] = None
        self.assertTrue(any("calibration_ref" in m for m in errs(self.d)))

    def test_source_without_text_rejected(self):
        dm = self.edge("derived")["dimension"]
        dm["status"] = "source"
        self.assertTrue(any("source-maat vereist" in m for m in errs(self.d)))

    def test_bad_status_rejected(self):
        self.edge("derived")["dimension"]["status"] = "exact"
        self.assertTrue(errs(self.d))

    def test_rel_coords_inconsistent_rejected(self):
        self.d["vertices"][0]["x_rel"] += 0.01
        self.assertTrue(any("x_rel/y_rel" in m for m in errs(self.d)))

    def test_duplicate_id_rejected(self):
        self.d["objects"][1]["id"] = self.d["objects"][0]["id"]
        self.assertTrue(any("dubbel id" in m for m in errs(self.d)))

    def test_missing_ref_rejected(self):
        self.d["labels"][0]["assigned_object_ids"] = ["obj_bestaat_niet"]
        self.assertTrue(any("onbekend object" in m for m in errs(self.d)))

    def test_overlap_rejected(self):
        hal = next(o for o in self.d["objects"] if o["id"] == "obj_bg_core_hal")
        dup = copy.deepcopy(hal)
        dup["id"] = "obj_bg_core_haldup"
        dup["label_ids"] = []
        self.d["objects"].append(dup)
        self.assertTrue(any("overlap" in m and "haldup" in m for m in errs(self.d)))

    def test_self_intersection_rejected(self):
        o = next(o for o in self.d["objects"] if o["id"] == "obj_bg_core_lift")
        r = o["geometry"]["rings"][0]
        r[1], r[2] = r[2], r[1]
        self.assertTrue(any("zelfdoorsnijding" in m for m in errs(self.d)))

    def test_connection_needs_adjacency(self):
        self.d["connections"][0]["connects"] = ["obj_bg_core_entree", "obj_bg_core_ls"]
        self.assertTrue(any("geen adjacency" in m for m in errs(self.d)))

    def test_legal_ui_cannot_enable_without_boundaries(self):
        for sp in self.d["legal_splits"]:
            sp["boundary_status"] = "unknown"
        self.assertTrue(any("splitsgrens" in m for m in errs(self.d)))

    def test_membership_claim_needs_evidence(self):
        m = next(m for m in self.d["memberships"] if m["relation"] != "unknown")
        m["evidence"] = None
        self.assertTrue(any("zonder evidence" in x for x in errs(self.d)))

    def test_membership_unknown_right_rejected(self):
        m = next(m for m in self.d["memberships"] if m.get("right_id"))
        m["right_id"] = "A-999"
        self.assertTrue(any("onbekend recht" in x for x in errs(self.d)))

    def test_private_raster_publish_rejected(self):
        self.d["sources"][0]["publish_native_raster"] = True
        self.assertTrue(any("privé-bron" in m for m in errs(self.d)))

    def test_door_without_leaf_rejected(self):
        self.d["connections"][0]["kind"] = "door"
        self.assertTrue(any("deurblad" in m for m in errs(self.d)))

    def test_current_use_as_source_rejected(self):
        o = next(o for o in self.d["objects"] if o.get("current_use"))
        o["current_use"]["certainty"] = "source"
        self.assertTrue(any("current_use" in m for m in errs(self.d)))

    def test_private_overlay_rejected(self):
        self.d["reference_overlays"][0]["image"] = "model/pilot/local/src.png"
        self.assertTrue(any("publieke overlay" in m for m in errs(self.d)))

    def test_duplicate_shared_edge_rejected(self):
        e = copy.deepcopy(self.d["edges"][0])
        e["id"] = "e_bg_core_dup"
        self.d["edges"].append(e)
        self.assertTrue(any("dubbele edge" in m for m in errs(self.d)))


if __name__ == "__main__":
    unittest.main()
