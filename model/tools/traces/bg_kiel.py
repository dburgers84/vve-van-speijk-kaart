"""Brontrace regio 2: BG kern De Kiel (container/trap/lift/flatkast/entree 180) + aangrenzende bedrijfsruimte.

Bron: akte 2006 p.81, native scanpixels (zie bg_core.py voor conventies).
Dubbellijnige gevel bovenzijde (y≈654 buiten / 668 binnen): ruimtegrenzen op de BINNENlijn;
de gevelwand zelf is een apart element met getekende dikte. Overige wanden: hartlijn.
Afgelezen op 2x-rasteruitsneden; per lijn gecontroleerd met inktprofiel.
"""
PREFIX = "bg_kiel"
REGION_ID = "reg_bg_kiel"
REGION_NAME = "BG kern De Kiel + aangrenzende bedrijfsruimte"
REGION_PX = (6440, 560, 7020, 1260)

VERTICES = {
    "C1": (6490, 668), "C2": (6634, 668), "S2": (6838, 668), "L2": (6914, 668), "F2": (6963, 668),
    "E4": (6914, 717), "E5": (6963, 717),
    "E1": (6634, 760), "E2": (6838, 760), "E3": (6914, 760),
    "C3": (6490, 829), "E7": (6634, 829), "E6": (6963, 829),
    "G1": (6963, 840), "G2": (6963, 880),
    "B3": (6963, 1206), "B4": (6490, 1206),
    # liftkooi-symbool
    "LC1": (6843, 682), "LC2": (6891, 682), "LC3": (6891, 755), "LC4": (6843, 755),
    # trap-looplijn/pijl
    "ST1": (6685, 688), "ST2": (6722, 688),
}

SPACES = [
    ("container", "container_room", ["C1", "C2", "E1", "E7", "C3"], "container-ruimte", (6535, 685, 6580, 790), "source_label"),
    ("trap", "stair", ["C2", "S2", "E2", "E1"], "trap", (6700, 712, 6760, 745), "source_label"),
    ("lift", "lift_shaft", ["S2", "L2", "E4", "E3", "E2"], "lift", (6845, 680, 6872, 722), "source_label"),
    ("flatkast", "meter_cupboard_common", ["L2", "F2", "E5", "E4"], "flatkast", (6921, 414, 6945, 470), "probable_assignment"),
    ("entree", "entrance_hall", ["E1", "E2", "E3", "E4", "E5", "E6", "E7"], "entree", (6915, 730, 6937, 790), "source_label"),
    ("bedrijf1", "commercial_unit", ["C3", "E7", "E6", "G1", "G2", "B3", "B4"], "bedrijfs-ruimte", (6690, 870, 6745, 960), "source_label"),
]

EDGE_ROLES = {
    ("G1", "G2"): "virtual_opening",
    ("C2", "C1"): "wall_inner_face", ("C2", "S2"): "wall_inner_face", ("L2", "S2"): "wall_inner_face", ("F2", "L2"): "wall_inner_face",
    ("E6", "G1"): "facade", ("B3", "G2"): "facade", ("B3", "B4"): "facade", ("E5", "E6"): "facade", ("E5", "F2"): "facade",
    ("C1", "C3"): "wall_drawn", ("B4", "C3"): "wall_drawn_thin",
}

LINES = [
    ("lift_car", "lift_car_symbol", ["LC1", "LC2", "LC3", "LC4", "LC1"], "Liftkooi-symbool binnen schacht"),
    ("trap_walkline", "stair_walkline_symbol", ["ST1", "ST2"], "Looplijn/pijl trap (gestippeld bordes; geen afzonderlijke treden)"),
]

CURRENT_USE = {
    "container": ("fietsenberging", "opgave bewoner 06-11-2026; zie data/sources.md (alle containerruimtes omgebouwd)", "probable"),
}

ELEMENTS = [
    ("gevel_noord", "facade_wall_double_line", [(6490, 654), (6963, 654), (6963, 668), (6490, 668)],
     "Gevelwand als dubbele lijn (buiten y≈654, binnen y≈668): getekende dikte ≈14 px", "source"),
    ("kolom_wand_rect", "column", [(6629, 814), (6640, 814), (6640, 840), (6629, 840)],
     "Rechthoekige kolom in wand container/entree–bedrijfsruimte (getekend, niet vierkant)", "source"),
    ("kozijn_zuid", "facade_frame_strip", [(6492, 1200), (6963, 1200), (6963, 1212), (6492, 1212)],
     "Gevel/kozijnstrook bedrijfsruimte zuidzijde: dubbele lijn met stijlen", "source"),
]

EXTRA_LABELS = [
    ("180", "index_number_candidate", (6880, 770, 6915, 820), ["entree"], "uncertain",
     "Omcirkeld 180 in entree; komt op elke gemeenschappelijke kern voor; betekenis niet uit dit blad bewezen"),
    ("water, KPN, UPC", "note", (6950, 414, 6993, 621), ["flatkast"], "uncertain",
     "Tekst buiten gevel met aanwijslijn richting kastje rechtsboven"),
]

CONNECTIONS = [
    ("conn_entree_buiten", "opening_candidate", ("G1", "G2"), ["bedrijf1", "exterior"], "uncertain",
     "Onderbreking in gevellijn x≈6963, y≈840–880 (geen deurblad/draaicirkel getekend); type doorgang onbekend."),
]

LEGACY = [
    ("BG-K49-ENT", "entree", "same_function_candidate"), ("BG-K49-LIFT", "lift", "same_function_candidate"),
    ("BG-K49-TRAP", "trap", "same_function_candidate"), ("BG-K49-FIETS", "container", "same_function_candidate"),
    ("BG-K49-MK", "flatkast", "same_function_candidate"),
]

_H, _O = "ls_hoofdsplitsing", "ls_ondersplitsing_woningen"
_AKTE = "Akte ondersplitsing 2006 (visueel gelezen): entrees, liften/trappen, technische ruimten behoren tot de gemeenschap"
LEGAL = {
    "entree": [(_H, "private", "A-180", "probable", "Indexnummer 180 (omcirkeld) staat in deze ruimte; A-180 = Woningen volgens MVGM-begroting hoofdsplitsing"),
               (_O, "common", None, "probable", _AKTE)],
    "trap": [(_H, "private", "A-180", "uncertain", "Zelfde kern als index 180"), (_O, "common", None, "probable", _AKTE)],
    "lift": [(_H, "private", "A-180", "uncertain", "Zelfde kern als index 180"), (_O, "common", None, "probable", _AKTE)],
    "container": [(_O, "common", None, "uncertain", "Containerruimte in woonkern; niet expliciet per ruimte bewezen")],
    "flatkast": [(_O, "common", None, "uncertain", "Flatkast in woonkern")],
    "bedrijf1": [(_H, "private", "A-179", "uncertain", "Label 'bedrijfs-ruimte'; index 179 staat in naburige bedrijfsruimten van hetzelfde blok, niet in deze; A-179 = Winkels (commerciële ruimten) volgens MVGM-begroting"),
                 (_O, "excluded", None, "uncertain", "Commerciële ruimte; ondersplitsing betreft woningen + bergingen")],
}
