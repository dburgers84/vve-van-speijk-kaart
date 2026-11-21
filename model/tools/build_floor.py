#!/usr/bin/env python3
"""Bouwt per verdieping data/fN.v2.json + pilot/pilot_data_fN.js (1e = akte 2006 p.82, 2e = p.83).

Gebruik: build_floor.py --floor 1e|2e [--scan none]
Hergebruikt de Builder/maatlogica van build_model.py met een EIGEN frame + kalibratie per blad,
de semi-automatische segmentatie uit data/inventory/fN_segments_p8X.json
(tools/segment_bg.py --floor N, zelfde lijnwerk tools/linework.py als de BG) en de gemeten labelboxen
uit data/inventory/labels_measured_p8X.json (tools/measure_labels.py).
Zonder lokale scan (--scan none) wordt de inkt-ondersteuning uit de vorige build overgenomen (reproduceerbaar).
"""
import argparse
import copy
import hashlib
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_model as BM  # noqa: E402
from traces import f1_segments, f2_segments, f3_segments, f4_segments  # noqa: E402

ROOT = os.path.dirname(HERE)
# ---- per bronblad: eigen frame + kalibratie (metingen in data/inventory/calibration_p8X.json, op de lokale scan)
FLOORS = {
    "1e": dict(M=f1_segments, version="f1-0.2.1", page=82, sheet="02", name="1e verdieping", level=1, title_txt="1e Verdieping",
               bar_x=77, bar_px=(335.5, 728.7), bar_segments=[76.5, 81.5, 80.7, 75.5, 79.0],
               ruler_x=438, ruler_ticks=(379.34, 773.49), overlay="img/plan_1e.jpg", js_var="PILOT_DATA_F1", js="pilot_data_f1.js",
               out="f1.v2.json", seg="f1_segments_p82.json", labels="labels_measured_p82.json",
               review=[{"date": "2026-11-21", "by": "Grok Bot (executor)", "action": "fase 4: 1e verdieping (p82) kalibratie + semi-automatische segmentatie + visuele classificatie", "status": "needs_human_review"},
                       {"date": "2026-11-21", "by": "Grok Bot (executor)", "action": "fase 5: labelposities gemeten (tekstclusters) waar mogelijk", "status": "needs_human_review"}]),
    "2e": dict(M=f2_segments, version="f2-0.1.1", page=83, sheet="03", name="2e verdieping", level=2, title_txt="2e Verdieping",
               bar_x=76, bar_px=(408.3, 805.6), bar_segments=[81.7, 78.0, 81.0, 80.5, 76.1],
               ruler_x=434, ruler_ticks=(419.07, 812.14), overlay="img/plan_2e.jpg", js_var="PILOT_DATA_F2", js="pilot_data_f2.js",
               out="f2.v2.json", seg="f2_segments_p83.json", labels="labels_measured_p83.json",
               review=[{"date": "2026-11-21", "by": "Grok Bot (executor)", "action": "fase 5: 2e verdieping (p83) kalibratie + semi-automatische segmentatie + visuele classificatie + gemeten labelposities", "status": "needs_human_review"}]),
    "3e": dict(M=f3_segments, version="f3-0.1.1", page=84, sheet="04", name="3e verdieping", level=3, title_txt="3e Verdieping",
               bar_x=78, bar_px=(352.25, 747.6), bar_segments=[81.7, 80.0, 76.0, 79.0, 78.6],
               ruler_x=465, ruler_ticks=(390.43, 783.47), overlay="img/plan_3e.jpg", js_var="PILOT_DATA_F3", js="pilot_data_f3.js",
               out="f3.v2.json", seg="f3_segments_p84.json", labels="labels_measured_p84.json",
               review=[{"date": "2026-11-21", "by": "Grok Bot (executor)", "action": "fase 6: 3e verdieping (p84) kalibratie + semi-automatische segmentatie + visuele classificatie + gemeten labelposities", "status": "needs_human_review"}]),
    # p85: de eigen schaalbalk '4e Verdieping en daken' valt buiten de scan (alleen de 10 m-eindlijn); de tweede balk 'Daken'
    # (x 4742, y 353,5-757,5 = 404,0 px) wijkt 2,8 % af van de liniaal en van de overdracht via p84 en wordt daarom NIET gebruikt.
    # Tweede controle = overdracht van p84 via dezelfde getekende woningen 256-259 (y-overspanning 1207 px op p84, 1205 px op p85).
    "4e": dict(M=f4_segments, version="f4-0.1.1", page=85, sheet="05", name="4e verdieping en daken", level=4, title_txt="4e Verdieping en daken",
               bar_x=4742, bar_px=(353.5, 757.5), bar_segments=None, bar_rejected=True,
               transfer=dict(floor="3e", span_from=1207, span_to=1205, objects="woningen 256-259 (y-overspanning buitenzijde polygonen)"),
               ruler_x=438, ruler_ticks=(468.0, 860.52), overlay="img/plan_4e.jpg", js_var="PILOT_DATA_F4", js="pilot_data_f4.js",
               out="f4.v2.json", seg="f4_segments_p85.json", labels="labels_measured_p85.json",
               review=[{"date": "2026-11-21", "by": "Grok Bot (executor)", "action": "fase 6: 4e verdieping en daken (p85) kalibratie (liniaal + overdracht p84) + segmentatie + visuele classificatie + gemeten labelposities", "status": "needs_human_review"}]),
}
REG_JSON = BM.REG_JSON
C = None   # actieve configuratie (zie configure)
M = None
FLOOR = FRAME = SOURCE = CAL = NATIVE = None
M_BAR = M_RULER = M_ADOPT = HALF_SPREAD = READ_TOL = REL_U_Y = REL_U_X = None
M_NOMINAL = 0.0254
REL_ANISO_P81 = BM.REL_ANISO                           # 0,88 % (kolomstramien p81)


def cal_of(floor):
    """m/px en marge y van een ander blad (zonder globals te wijzigen)."""
    c = FLOORS[floor]
    (b0, b1), (r0, r1) = c["bar_px"], c["ruler_ticks"]
    mb, mr = 10.0 / (b1 - b0), 2.0 / ((r1 - r0) / 5)
    m = round((mb + mr) / 2, 7)
    return {"m": m, "u_y": round(max(abs(mb - mr) / 2 / m, math.sqrt(2) * 1.5 / (b1 - b0)), 4)}


def configure(floor):
    """Zet module- en build_model-globals op het frame/de kalibratie van dit blad (Builder/dim_for lezen die)."""
    global C, M, FLOOR, FRAME, SOURCE, CAL, NATIVE, M_BAR, M_RULER, M_ADOPT, HALF_SPREAD, READ_TOL, REL_U_Y, REL_U_X
    C = FLOORS[floor]
    M = C["M"]
    FLOOR, NATIVE = floor, M.NATIVE
    FRAME, SOURCE, CAL = f"frm_p{C['page']}_native", f"src_akte2006_p{C['page']}", f"cal_p{C['page']}_controls"
    b0, b1 = C["bar_px"]
    r0, r1 = C["ruler_ticks"]
    M_RULER = 2.0 / ((r1 - r0) / 5)
    if C.get("transfer"):
        t = C["transfer"]
        src = cal_of(t["floor"])
        C["bar_rejected_m_per_px"] = round(10.0 / (b1 - b0), 6)
        M_BAR = src["m"] * t["span_from"] / t["span_to"]        # 'tweede controle' = overdracht
        READ_TOL = math.hypot(math.sqrt(2) * 3 / t["span_to"], src["u_y"])
    else:
        M_BAR = 10.0 / (b1 - b0)
        READ_TOL = math.sqrt(2) * 1.5 / (b1 - b0)
    M_ADOPT = round((M_BAR + M_RULER) / 2, 7)
    HALF_SPREAD = abs(M_BAR - M_RULER) / 2 / M_ADOPT
    REL_U_Y = round(max(HALF_SPREAD, READ_TOL), 4)
    REL_U_X = round(REL_U_Y + REL_ANISO_P81, 4)
    for k, v in dict(FLOOR=FLOOR, FRAME=FRAME, SOURCE=SOURCE, CAL=CAL, NATIVE=NATIVE, M_PER_PX=(M_ADOPT, M_ADOPT),
                     REL_U_X=REL_U_X, REL_U_Y=REL_U_Y,
                     EV_TRACE={"source_id": SOURCE, "method": "auto_segment_inner_face"}).items():
        setattr(BM, k, v)


H, O = "ls_hoofdsplitsing", "ls_ondersplitsing_woningen"
WONING_RANGE, BERGING_RANGE = range(181, 266), range(266, 357)
ELEMENT_KINDS = {"wall_band": "Wandstrook tussen dubbele lijnen (getekende wanddikte)",
                 "roof_symbol": "Klein rechthoekig symbool op dak (opbouw/installatie? niet gelezen)"}
UNRES = ("unlabeled_space", "unresolved_space", "cross_marked_cell")


def legal_splits():
    ls = copy.deepcopy(BM.LEGAL_SPLITS)
    o = next(s for s in ls if s["id"] == O)
    o["rights"] = ([{"id": f"O-{n}", "name": f"Woonappartement (indexnummer {n})", "drawing_index": str(n)} for n in WONING_RANGE]
                   + [{"id": f"O-{n}", "name": f"Berging (indexnummer {n})", "drawing_index": str(n)} for n in BERGING_RANGE])
    o["rights_note"] = ("Rechten-id 'O-n' = indexnummer n op de splitsingstekening (181-265 woningen, 266-356 bergingen = 176 rechten volgens de akte). "
                        "De kadastrale appartementsrechtnummers zijn NIET gelezen; dit is een tekening-index, geen kadastrale aanduiding.")
    return ls


def display_name(kind, lit, idx):
    if kind == "apartment_dwelling":
        return f"Woning {idx}"
    if kind == "storage_unit":
        return f"Berging {idx}"
    if kind == "apartment_part":
        return f"Vak bij recht {idx} (deel van woning {idx}? onzeker)"
    return {"private_outdoor": "Buitenruimte", "private_outdoor_multi_unresolved": "Buitenruimte(n) — onderverdeling niet getraceerd",
            "roof": "Dak", "void": "Vide", "stair": "Trap", "lift_shaft": "Lift", "core_multi_unresolved": "Kern trap/lift — niet onderverdeeld",
            "storage_corridor": "Gang/bergingen", "roof_path_network_unresolved": "Pad(en) over dak — onopgelost",
            "cross_marked_cell": "Vak met kruis (X)", "unlabeled_space": "Onbenoemd vak", "unresolved_space": "Vak met meerdere functies — onopgelost",
            "commercial_unit": "bedrijfs-ruimte", "commercial_multi_unresolved": "Bedrijfsruimte(n) — onderverdeling onopgelost",
            "a179_region_unresolved": "Gebied met indexnummer 179 — onopgelost",
            "commercial_round_part": "Halfrond vak met 179", "gallery": "Galerij", "lift_overrun": "Liftuitloop"}.get(kind) or lit or kind


def certainty(kind):
    if kind.endswith("unresolved") or kind in UNRES:
        return "unresolved"
    return "uncertain" if kind == "apartment_part" else "probable"


def legal_for(kind, idx, h179, h180=False):
    """Afgeleide lidmaatschappen per vak; ontbrekend = unknown."""
    n = int(idx) if idx else None
    out = {}
    if kind in ("apartment_dwelling", "storage_unit"):
        what = "woningen" if kind == "apartment_dwelling" else "bergingen"
        rng = WONING_RANGE if kind == "apartment_dwelling" else BERGING_RANGE
        assert n in rng, (kind, n)
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 staat bij vrijwel alle woningen/bergingen op dit blad (niet per vak gepositioneerd); A-180 = Woningen (MVGM)")
        out[O] = ("private", f"O-{n}", "probable", f"Indexnummer {n} in dit vak (visueel gelezen); {rng.start}-{rng.stop - 1} = {what} volgens de nummering van de ondersplitsing (176 rechten)")
    elif kind == "apartment_part":
        out[H] = ("private", "A-180", "uncertain", "Groot indexnummer zonder label 'woning'; vermoedelijk onderdeel van een woning binnen A-180")
        out[O] = ("private", f"O-{n}", "uncertain", f"Nummer {n} zonder label 'woning': mogelijk buitenruimte/trap van woning {n}; niet bewezen")
    elif kind.startswith("private_outdoor"):
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 met verwijsstreep bij buitenruimten op dit blad; A-180 = Woningen (MVGM)")
    elif kind.startswith("commercial") or kind == "a179_region_unresolved":
        out[H] = ("private", "A-179", "probable" if h179 else "uncertain",
                  "Indexnummer 179 in dit vak; A-179 = Winkels (commerciële ruimten) volgens MVGM-begroting hoofdsplitsing" if h179 else
                  "Commerciële functie gelezen, geen 179 in dit vak; A-179 = commerciële ruimten (MVGM)")
        out[O] = ("excluded", None, "uncertain", "Valt onder A-179; ondersplitsing is genest binnen A-180 (woningen + bergingen)")
    elif kind == "void" and h179:
        out[H] = ("private", "A-179", "uncertain", "Indexnummer 179 in deze vide; vide boven commerciële ruimte? niet bewezen")
        out[O] = ("excluded", None, "uncertain", "179 in deze vide; ondersplitsing is genest binnen A-180")
    elif kind == "storage_corridor":
        out[H] = ("private", "A-180", "uncertain", "Gang naar bergingen 266-356 (ondersplitsing); geen eigen indexnummer")
        out[O] = ("common", None, "uncertain", "Gang tussen bergingen; gemeenschappelijk niet per vak bewezen")
    elif kind == "roof" and h179:
        out[H] = ("private", "A-179", "probable", "Indexnummer 179 in dit dakvak; A-179 = commerciële ruimten (MVGM)")
        out[O] = ("excluded", None, "uncertain", "Valt onder A-179; ondersplitsing is genest binnen A-180")
    elif kind == "void" and h180:
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 in deze vide; A-180 = Woningen (MVGM)")
        out[O] = ("unknown", None, "uncertain", "Vide naast een woning; bij welke woning (O-n) is niet per vak gelezen")
    elif kind == "gallery":
        out[O] = ("common", None, "uncertain", BM._AKTE_O + "; galerij als gemeenschappelijk niet per vak bewezen")
        if h180:
            out[H] = ("private", "A-180", "probable", "Omcirkeld 180 in de galerij; A-180 = Woningen (MVGM)")
    elif kind in ("stair", "lift_shaft", "lift_overrun", "core_multi_unresolved"):
        out[O] = ("common", None, "uncertain", BM._AKTE_O + "; welke trappen/liften bij de woningen horen is niet per vak bewezen")
        if h180:
            out[H] = ("private", "A-180", "probable", "Omcirkeld 180 in dit vak; A-180 = Woningen (MVGM)")
    elif kind == "roof" and h180:
        out[H] = ("private", "A-180", "probable", "Omcirkeld 180 in dit dak-/installatievak; A-180 = Woningen (MVGM)")
    elif kind == "unlabeled_space" and h180:
        out[H] = ("private", "A-180", "uncertain", "Omcirkeld 180 in dit vak; functie niet gelezen")
    return out


class FloorBuilder(BM.Builder):
    def add_segments_floor(self, seg, lm):
        P = M.PREFIX
        okey, meta = {}, []
        for key, seed, kind, lit, idx, h179, note in M.SEEDS:
            g = seg["segments"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="auto_segment_inner_face", tol=3) for i, xy in enumerate(g["polygon"])]
            is_el = kind in ELEMENT_KINDS
            fields = {"kind": kind, "class": "element" if is_el else "space", "region_id": M.REGION_ID,
                      "display_name": ELEMENT_KINDS.get(kind) or display_name(kind, lit, idx),
                      "certainty": certainty(kind), "review_status": "needs_review",
                      "evidence": {"source_id": SOURCE, "method": f"auto_segment_inner_face (tools/segment_bg.py --floor {FLOOR}) + visuele review contactbladen",
                                   "boundary": "binnenzijde getekende lijn",
                                   "note": " ".join(x for x in [(note or "").rstrip(".") + ("." if note else ""),
                                                                "" if is_el else "Grens = binnenzijde van de getekende lijn (wandstrook ligt ertussen)."] if x)}}
            if not is_el:
                fields["source_label_text"] = lit
                fields["current_use"] = None
                if idx:
                    fields["index_number"] = idx
            o = self.polygon_object(o_id, P, vids, (lambda a, b: "element_outline") if is_el else (lambda a, b: "wall_inner_face"), **fields)
            for hi, hole in enumerate(g.get("holes", [])):   # omsloten buurvakken (binnenringen)
                hv = [self.vertex(f"v_{P}_{key}_h{hi}_{i}", tuple(xy), method="auto_segment_inner_face", tol=3) for i, xy in enumerate(hole)]
                o["geometry"]["rings"].append(hv)
                o["edge_ids"] += [self.edge(P, hv[i], hv[(i + 1) % len(hv)], "wall_inner_face") for i in range(len(hv))]
            if g.get("holes"):
                o["evidence"]["note"] += f" {len(g['holes'])} omsloten buurvakken als gaten (binnenringen)."
            sx, sy = seed
            meas = lm.get(key, {})

            def box(kind_, text, approx_box):
                m = meas.get(kind_)
                n_txt = len(text.replace(" ", "").replace("-", ""))
                if m:
                    part = "" if m[4] == n_txt else f"; DEELS: {m[4]} van {n_txt} tekens gevonden (rest raakt een lijn)"
                    return tuple(m[:4]), f"Visueel gelezen; positie GEMETEN als tekstcluster in het vak (tools/measure_labels.py, {m[4]} tekens{part})"
                return approx_box, "Visueel gelezen op contactblad; bbox BENADERD rond het zaadpunt (tekstcluster niet eenduidig gemeten)"
            if idx:
                b, nt = box("number", idx, (sx - 30, sy - 50, sx + 30, sy + 50) if kind == "storage_unit" else (sx - 45, sy - 80, sx + 45, sy + 80))
                self.label(f"lbl_{P}_{key}_n", idx, "index_number", b, [o_id], "probable", nt)
            if lit:
                b, nt = box("literal", lit, (sx - 60, sy - 60, sx + 60, sy + 60))
                self.label(f"lbl_{P}_{key}", lit, "space_name", b, [o_id], "probable", nt)
            if h179:
                b, nt = box("i179", "179", (sx - 40, sy - 75, sx + 40, sy + 75))
                self.label(f"lbl_{P}_{key}_i179", "179", "index_number", b, [o_id], "probable", "Indexnummer 179 in dit vak. " + nt)
            if not is_el:
                meta.append((o_id, legal_for(kind, idx, h179, key in getattr(M, "IDX180_KEYS", ()))))
        for key, seed, note in M.HATCH_SEEDS:
            g = seg["hatch"].get(key)
            if g is None:
                continue
            o_id = f"obj_{P}_{key}"
            okey[key] = o_id
            vids = [self.vertex(f"v_{P}_{key}_{i}", tuple(xy), method="hatch_diagonal_density_outline", tol=8) for i, xy in enumerate(g["polygon"])]
            self.polygon_object(o_id, P, vids, lambda a, b: "virtual_boundary", kind="not_in_split_area", **{"class": "space"},
                                region_id=M.REGION_ID, display_name="Gearceerd: niet in de splitsing betrokken",
                                source_label_text=None, current_use=None, certainty="probable", review_status="needs_review",
                                evidence={"source_id": SOURCE, "method": f"dichtheid diagonale arceerlijnen (tools/segment_bg.py --floor {FLOOR})",
                                          "boundary": "buitenrand arcering (±8 px)",
                                          "note": note + ". Labels binnen de arcering (o.a. 'vide', 'dak') niet als aparte vakken getraceerd."})
            ex = ("excluded", None, "probable", "Arcering = 'niet in de splitsing betrokken' (legenda op het blad)")
            meta.append((o_id, {H: ex, O: ex}))
        if M.LEGEND_BBOX:
            self.label(f"lbl_{P}_legend_hatch", "= niet in de splitsing betrokken", "note", M.LEGEND_BBOX,
                       [okey[k] for k, *_ in M.HATCH_SEEDS if k in okey], "source", "Legenda op het blad (arcering)")
        return okey, meta


COMMON_NOT_TRACED = ["deuren/draaibogen en traptreden (niet getraceerd; niet verzonnen)",
                     "posities van de omcirkelde 180-symbolen (alleen als toelichting, niet per vak gemeten)",
                     "kolommen (kolomkandidaten op p82-p85 niet beoordeeld)", "gestippelde contouren"]
FLOORS["1e"]["not_traced"] = ["onderverdeling van buitenruimten met meerdere omcirkelde 180 en gestippelde deellijnen",
                              "scheiding woning/buitenruimte waar de lijn niet gesloten is (WB-vakken) en kernen trap+lift in één vlak",
                              "onderverdeling multi-label bedrijfsvakken en 179-gebieden"]
FLOORS["3e"]["not_traced"] = ["kleine vakjes met draaiboog (deur) zonder label: functie niet gelezen",
                              "vides met omcirkeld 180 naast 230-237: bij welke woning (O-n) ze horen is niet gelezen",
                              "blokken met installatiesymbolen zonder leesbaar label (s003, s013, s048)",
                              "buitenruimten binnen woningen 246, 247, 256-259 die naar buiten openstaan in het lijnwerk"]
FLOORS["4e"]["not_traced"] = ["23 kleine rechthoekige symbolen op de daken: betekenis niet gelezen (als element, niet als ruimte)",
                              "dakvlakken die met een dunne lijn in twee helften zijn verdeeld: de omcirkelde 180 staat maar in één helft",
                              "eigen schaalbalk valt buiten de scan; kalibratie via liniaal + overdracht p84"]
FLOORS["2e"]["not_traced"] = ["kleine buitenruimten binnen woningen (bv. 196, 197, 200, 201, 241-243, 252-255) die naar buiten openstaan in het lijnwerk: niet als eigen vak",
                              "kernen trap+lift in één vlak (s002, s036, s045) en woning 225 met lift/trap in hetzelfde vak",
                              "onderverdeling 179-stroken/-blokken; betekenis omcirkelde '1' (bij 220 en beheerder)"]


def calibration_block():
    if C.get("transfer"):
        return calibration_transfer()
    return {
            "id": CAL, "frame_id": FRAME, "model": "nominal_scale", "m_per_px_x": M_ADOPT, "m_per_px_y": M_ADOPT,
            "basis": f"Gemiddelde van twee controles langs native y op blad {C['page']}: eigen schaalbalk ('{C['title_txt']} Schaal 1 a 200', 0-10 m) en cm-liniaal x opgegeven schaal 1:200",
            "status": "controls_checked_one_axis", "uncertainty_m": None, "uncertainty_status": "estimated",
            "rel_uncertainty": {"x": REL_U_X, "y": REL_U_Y},
            "axis_status": {"y": "checked_against_scale_bar_and_ruler", "x": "assumed_isotropic_not_independently_verified"},
            "control_points": [
                {"id": "bar_0m", "kind": "scale_bar_tick", "x_px": C["bar_x"], "y_px": C["bar_px"][0], "value_m": 0.0, "reading_tolerance_px": 1.5},
                {"id": "bar_10m", "kind": "scale_bar_tick", "x_px": C["bar_x"], "y_px": C["bar_px"][1], "value_m": 10.0, "reading_tolerance_px": 1.5},
                {"id": "ruler_0cm", "kind": "ruler_tick", "x_px": C["ruler_x"], "y_px": C["ruler_ticks"][0], "value_cm": 0},
                {"id": "ruler_5cm", "kind": "ruler_tick", "x_px": C["ruler_x"], "y_px": C["ruler_ticks"][1], "value_cm": 5}],
            "checks": {
                "m_per_px_scale_bar_0_10m": round(M_BAR, 6), "m_per_px_ruler_x_1to200": round(M_RULER, 6),
                "m_per_px_nominal_1to200_200dpi": M_NOMINAL, "adopted": M_ADOPT,
                "bar_vs_ruler_pct": round((M_BAR / M_RULER - 1) * 100, 2),
                "bar_vs_nominal_pct": round((M_BAR / M_NOMINAL - 1) * 100, 2), "ruler_vs_nominal_pct": round((M_RULER / M_NOMINAL - 1) * 100, 2),
                "half_spread_rel": round(HALF_SPREAD, 4), "reading_tolerance_rel": round(READ_TOL, 4),
                "bar_segments_px_per_2m": C["bar_segments"],
                "bar_segment_note": f"Segmenten ongelijk ({min(C['bar_segments']):.1f}-{max(C['bar_segments']):.1f} px per 2 m); alleen eindpunten gebruikt".replace(".", ","),
                "x_margin_note": "x-as niet onafhankelijk gecontroleerd; marge = marge y + 0,88 % anisotropie (kolomstramien p81)",
                "p81_comparison": "Balk p81 387,0 px vs p" + str(C["page"]) + " " + f"{C['bar_px'][1] - C['bar_px'][0]:.1f}".replace(".", ",") + " px per 10 m: reproductieschaal verschilt per blad, dus per blad gekalibreerd"},
            "residuals": None,
            "note": "GESCHATTE marge: y = max(halve spreiding balk/liniaal, afleestolerantie balkeinden). Zie data/inventory/calibration_p" + str(C["page"]) + ".json."}


def calibration_transfer():
    t = C["transfer"]
    return {
        "id": CAL, "frame_id": FRAME, "model": "nominal_scale", "m_per_px_x": M_ADOPT, "m_per_px_y": M_ADOPT,
        "basis": f"Gemiddelde van twee controles langs native y op blad {C['page']}: cm-liniaal x opgegeven schaal 1:200, en overdracht van blad p84 "
                 f"via dezelfde getekende {t['objects']}. De eigen schaalbalk valt buiten de scan; de tweede balk 'Daken' is verworpen (zie checks)",
        "status": "controls_checked_one_axis", "uncertainty_m": None, "uncertainty_status": "estimated",
        "rel_uncertainty": {"x": REL_U_X, "y": REL_U_Y},
        "axis_status": {"y": "checked_against_ruler_and_transfer_p84", "x": "assumed_isotropic_not_independently_verified"},
        "control_points": [
            {"id": "ruler_0cm", "kind": "ruler_tick", "x_px": C["ruler_x"], "y_px": C["ruler_ticks"][0], "value_cm": 0},
            {"id": "ruler_5cm", "kind": "ruler_tick", "x_px": C["ruler_x"], "y_px": C["ruler_ticks"][1], "value_cm": 5}],
        "checks": {
            "m_per_px_transfer_from_p84": round(M_BAR, 6), "m_per_px_ruler_x_1to200": round(M_RULER, 6),
            "m_per_px_nominal_1to200_200dpi": M_NOMINAL, "adopted": M_ADOPT,
            "transfer_vs_ruler_pct": round((M_BAR / M_RULER - 1) * 100, 2),
            "half_spread_rel": round(HALF_SPREAD, 4), "reading_tolerance_rel": round(READ_TOL, 4),
            "transfer_span_px": {"p84": t["span_from"], "p85": t["span_to"]},
            "rejected_bar_daken": {"x_px": C["bar_x"], "y_px": list(C["bar_px"]), "m_per_px": C["bar_rejected_m_per_px"],
                                   "vs_ruler_pct": round((C["bar_rejected_m_per_px"] / M_RULER - 1) * 100, 2),
                                   "reason": "Wijkt 2,8 % af van de liniaal en 2,6 % van de overdracht (die onderling 0,26 % verschillen); niet gebruikt"},
            "x_margin_note": "x-as niet onafhankelijk gecontroleerd; marge = marge y + 0,88 % anisotropie (kolomstramien p81). "
                             "Woningen 256-259: x-maat p85 0,4 % groter dan p84 en licht scheef (≈0,5°)"},
        "residuals": None,
        "note": "GESCHATTE marge: y = max(halve spreiding liniaal/overdracht, overdrachtstolerantie ±3 px per polygoonrand gecombineerd met de marge van p84). "
                "Zie data/inventory/calibration_p85.json."}



def coverage_block(B, seg, lm):
    ids = {o["id"] for o in B.objects}
    kinds = Counter(o["kind"] for o in B.objects if o.get("region_id") == M.REGION_ID)
    unres = sum(v for k, v in kinds.items() if k.endswith("unresolved") or k in UNRES)
    won = sorted(int(i) for k, _s, kd, _l, i, _h, _n in M.SEEDS if kd == "apartment_dwelling" and f"obj_{M.PREFIX}_{k}" in ids)
    berg = sorted(int(i) for k, _s, kd, _l, i, _h, _n in M.SEEDS if kd == "storage_unit" and f"obj_{M.PREFIX}_{k}" in ids)
    lbl = [l for l in B.labels if l["id"] != f"lbl_{M.PREFIX}_legend_hatch"]
    measured = sum("GEMETEN" in (l.get("note") or "") for l in lbl)
    counts = {"segment_kinds": dict(sorted(kinds.items())), "unresolved_or_unlabeled_segments": unres,
              "woningen_on_sheet": len(won), "woningen_numbers": won, "bergingen_on_sheet": len(berg),
              "labels_total": len(lbl), "labels_position_measured": measured, "labels_position_approximated": len(lbl) - measured,
              "segments_problems": seg.get("problems", [])}
    if berg:
        counts["bergingen_missing_266_356"] = sorted(set(BERGING_RANGE) - set(berg))
    nh = len(M.HATCH_SEEDS)
    return {"complete": False,
            "scope": f"Alleen {C['name']} (blad p.{C['page']}). Semi-automatisch: alle gesloten vakken met zaadpunt (binnenzijde getekende lijn), "
                     f"{nh} arcering(en) en wandstroken. Classificatie visueel gelezen op contactbladen. Andere verdiepingen staan in eigen datasets "
                     "(bg, f1-f4); samen nog niet compleet.",
            "floors_covered": [f"{FLOOR} (grotendeels, deels onopgelost)"],
            "counts": counts,
            "traced": [f"{len(won)} woningen (indexnummers visueel gelezen)"] + ([f"{len(berg)} bergingen"] if berg else ["geen bergingen op dit blad"]) +
                      ["buitenruimten, daken, vides, trappen/liften, bedrijfs-/179-vakken (labels visueel gelezen)",
                       f"{nh} arcering(en) 'niet in de splitsing betrokken' (diagonaaldetectie)", "wandstroken tussen dubbele lijnen",
                       f"labelposities: {measured} van {len(lbl)} GEMETEN als tekstcluster, rest benaderd rond het zaadpunt"],
            "not_traced": C["not_traced"] + COMMON_NOT_TRACED +
                          [f"exacte tekstpositie van {len(lbl) - measured} labels (benaderd; tekst raakt lijnen of is meerregelig)",
                           "nummercontrole over alle bladen: zie data/inventory/number_check.json"]}


def build(scan_path=None):
    A, scan_sha = None, None
    if scan_path and scan_path != "none" and os.path.exists(scan_path):
        from PIL import Image
        import numpy as np
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(scan_path).convert("L")
        assert im.size == NATIVE, im.size
        A = np.array(im) < BM.INK_SUPPORT_THRESHOLD
        scan_sha = hashlib.sha256(open(scan_path, "rb").read()).hexdigest()
    OUT = os.path.join(ROOT, "data", C["out"])
    JS_OUT = os.path.join(ROOT, "pilot", C["js"])
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    old_ink = {e["id"]: e.get("ink_support") for e in old.get("edges", [])}
    if scan_sha is None:
        scan_sha = (old.get("sources") or [{}])[0].get("scan_sha256")
    seg = json.load(open(os.path.join(ROOT, "data", "inventory", C["seg"])))
    lp = os.path.join(ROOT, "data", "inventory", C["labels"])
    lm = json.load(open(lp))["labels"] if os.path.exists(lp) else {}
    reg = json.load(open(REG_JSON)) if os.path.exists(REG_JSON) else None
    B = FloorBuilder(A, old_ink)
    okey, seg_meta = B.add_segments_floor(seg, lm)
    pts = [B.pos[v] for o in B.objects for v in o["geometry"]["rings"][0]]
    regions = [{"id": M.REGION_ID, "name": M.REGION_NAME, "region_px": list(M.REGION_PX), "floor_id": FLOOR,
                "fit_px": [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)],
                "columns_from_detector": 0, "method": "semi-automatische segmentatie (binnenzijde lijn) + visuele review", "local_crop_scale": 0.25}]
    overlays = []
    if reg and FLOOR in reg.get("floors", {}):
        r = reg["floors"][FLOOR]
        overlays.append({"id": f"ovl_plan_{FLOOR}_jpg", "frame_id": FRAME, "image": C["overlay"], "public": True,
                         "size_px": r["image_size"], "image_to_native_affine": r["image_to_native_affine"],
                         "method": r["method"], "ecc_correlation": r["ecc_correlation"],
                         "note": "Eerder gepubliceerde lage-resolutie (≈0,24x) referentie; geen nieuwe bronpublicatie."})
    seg_ids = {o for o, _ in seg_meta}
    data = {
        "schema_version": BM.SCHEMA_VERSION, "dataset_version": C["version"], "generated": "2026-11-21",
        "sources": [{
            "id": SOURCE, "title": f"Splitsingsakte 2006, tekenblad {C['name']} (ondersplitsingstekening woningen + bergingen)",
            "document": "1050_96739052_Splitsingsakte_+_tekeningen.pdf", "page": C["page"], "drawing_sheet": C["sheet"],
            "author": "W. Grandia BV, project 2273", "native_size_px": list(NATIVE), "dpi": 200, "raster_only": True,
            "scan_sha256": scan_sha, "pdf_extract_sha256": (old.get("sources") or [{}])[0].get("pdf_extract_sha256"),
            "privacy_class": "private_deed_drawing", "publish_native_raster": False,
            "note": f"Bladtitel '{C['title_txt']}, Schaal 1 a 200' gelezen; bladnummer {C['sheet']} afgeleid uit de volgorde. Native raster blijft lokaal."}] + BM.EXTRA_SOURCES,
        "calibrations": [calibration_block()],
        "frames": [{"id": FRAME, "source_id": SOURCE, "floor_id": FLOOR, "unit": "px_native", "width_px": NATIVE[0],
                    "height_px": NATIVE[1], "axis_x": "right", "axis_y": "down",
                    "orientation": "scan_as_is_not_north_up", "calibration_ids": [CAL]}],
        "floors": [{"id": FLOOR, "name": C["name"], "level": C["level"], "source_ids": [SOURCE]}],
        "regions": regions, "reference_overlays": overlays,
        "objects": B.objects, "vertices": B.vertices, "edges": B.edges, "labels": B.labels,
        "connections": [],
        "legal_splits": legal_splits(),
        "legal_split_ui": {"enabled": True,
                           "reason": "Gedeeltelijk: lidmaatschap per vak afgeleid uit indexnummers (181-356, 179, omcirkeld 180) + MVGM-stukken en akte-tekst; splitsingsgrenzen zelf niet als lijn getekend. Zekerheid per vak zichtbaar."},
        "memberships": _memberships(seg_meta),
        "legacy_links": [],
        "coverage": coverage_block(B, seg, lm),
        "review_log": C["review"],
    }
    assert seg_ids <= {o["id"] for o in B.objects}
    with open(OUT, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    with open(JS_OUT, "w") as f:
        f.write(f"// gegenereerd door model/tools/build_floor.py --floor {FLOOR}\nwindow.{C['js_var']} = ")
        json.dump(data, f, ensure_ascii=False)
        f.write(";\n")
    return data


def _memberships(seg_meta):
    old = BM.TRACES, BM.LEGAL_SPLITS
    BM.TRACES, BM.LEGAL_SPLITS = [], legal_splits()
    try:
        return BM.memberships(None, seg_meta)
    finally:
        BM.TRACES, BM.LEGAL_SPLITS = old


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", required=True, choices=sorted(FLOORS))
    ap.add_argument("--scan", default=None, help="lokale bronscan (standaard page-8X.png); 'none' = inktsteun uit vorige build")
    a = ap.parse_args()
    configure(a.floor)
    d = build(a.scan or f"/workspace/vve-source-audit/page-{C['page']}.png")
    weak = [e for e in d["edges"] if e["ink_support"] and e["role"] == "wall_inner_face" and e["ink_support"]["fraction"] < 0.9]
    print(C["out"], len(d["objects"]), "objects", len(d["edges"]), "edges;", len(weak), "space edges ink<0.9")
