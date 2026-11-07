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
        for e in d["edges"]:
            dm = e["dimension"]
            self.assertIn(dm["status"], {"source", "derived", "unknown"})
            if dm["status"] == "unknown":
                self.assertIsNone(dm["length_m"])
            if dm["status"] == "derived":
                self.assertIsNone(dm["uncertainty_m"])
                self.assertEqual(dm["uncertainty_status"], "unknown")
        for c in d["calibrations"]:
            self.assertEqual(c["status"], "nominal_unverified")
            self.assertIsNone(c["uncertainty_m"])

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
        self.assertEqual(prob, {"obj_bg_core_trap180", "obj_bg_kiel_entree"})

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
        self.assertEqual(len(cont), 2)
        for o in cont:
            self.assertEqual(o["source_label_text"], "container-ruimte")
            self.assertEqual(o["current_use"]["value"], "fietsenberging")
            self.assertNotEqual(o["current_use"]["certainty"], "source")

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

    def test_derived_with_invented_uncertainty_rejected(self):
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
