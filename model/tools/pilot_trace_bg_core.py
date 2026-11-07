"""Handmatige brontrace (pilot) van één gemeenschappelijke kern, BG, akte 2006 p.81.

Coördinaten zijn NATIVE PIXELS van de bron-JPEG (7118x10099, 200 dpi), x naar rechts,
y naar beneden, in de oriëntatie van de scan (niet gedraaid naar noord).
Waarden zijn visueel afgelezen op 2x-vergrote rasteruitsneden en daarna per lijn
gecontroleerd met een inktprofiel (zie build_pilot.py: ink_support per edge).
Lijnen zijn op de getekende lijn-hartlijn gezet; wanddikte is NIET apart gemodelleerd.
"""

# vertex-id -> (x_px, y_px)
VERTICES = {
    "A": (274, 4834), "B": (387, 4834), "F": (512, 4834), "H": (720, 4834),
    "E": (274, 4988), "D": (360, 4988), "C": (387, 4988), "G": (467, 4988),
    "J": (577, 4988), "I": (720, 4988),
    "K": (577, 5057), "Kr": (720, 5057),
    "M": (274, 5133), "N": (577, 5133), "V": (720, 5131), "W": (780, 5129),
    "T4": (577, 5255), "X": (780, 5255),
    "Y": (274, 5281), "U": (341, 5281), "S": (389, 5281), "R": (452, 5281), "Q": (577, 5281),
    "Y2": (274, 5327), "U2": (341, 5327),
    "S3": (389, 5347), "R2": (452, 5347), "S4": (389, 5373), "U3": (341, 5373),
    "Q2": (577, 5331), "Z1": (684, 5331), "Z3": (766, 5331),
    "Q4": (577, 5432), "Z2": (684, 5432), "Z4": (766, 5432),
    "R3": (452, 5440), "Q3": (577, 5440),
    # lift-kooisymbool (detail binnen schacht)
    "LC1": (592, 5070), "LC2": (700, 5070), "LC3": (700, 5129), "LC4": (592, 5129),
    # traplijn/pijl in trap 180 (looplijn-symbool, onvolledig)
    "ST1": (392, 4922), "ST2": (462, 4922),
    # gevel (lijnobject)
    "FA1": (274, 4834), "FA2": (274, 5440),
}
VERTICES.pop("FA1")  # valt samen met A; gevellijn hergebruikt A

# (object_key, kind, ring of vertex ids, literal label or None, label bbox px, certainty)
SPACES = [
    ("entree",    "entrance_hall", ["A", "B", "C", "D", "E"], "entree", (322, 4880, 352, 4960), "source_label"),
    ("trap180",   "stair",         ["B", "F", "G", "C"], "trap", (414, 4925, 440, 4975), "source_label"),
    ("ne_unlab",  "unknown",       ["F", "H", "I", "J", "G"], None, None, "unresolved"),
    ("gem",       "meter_cupboard_common", ["J", "I", "Kr", "K"], "GEM.", (602, 5020, 672, 5050), "source_label"),
    ("hal",       "hall",          ["E", "D", "C", "G", "J", "K", "N", "M"], "hal", (418, 5045, 436, 5085), "source_label"),
    ("lift",      "lift_shaft",    ["K", "Kr", "V", "N"], "lift", (632, 5082, 660, 5115), "source_label"),
    ("trap2",     "stair",         ["N", "V", "W", "X", "T4"], "trap", (700, 5170, 718, 5215), "source_label"),
    ("container", "container_room",["M", "N", "T4", "Q", "R", "S", "U", "Y"], "container-ruimte", (395, 5150, 455, 5245), "source_label"),
    ("gaskast",   "gas_meter_cupboards", ["Y", "U", "U2", "Y2"], "gaskasten", (215, 5285, 245, 5395), "probable_assignment"),
    ("box_a",     "unknown",       ["U", "S", "S3", "S4", "U3", "U2"], None, None, "unresolved"),
    ("box_b",     "unknown",       ["S", "R", "R2", "S3"], None, None, "unresolved"),
    ("sprinkler", "sprinkler_room",["R", "Q", "Q2", "Q4", "Q3", "R3", "R2"], "sprinkler ruimte", (500, 5310, 550, 5400), "source_label"),
    ("trafo",     "transformer_room", ["Q2", "Z1", "Z2", "Q4"], "trafo ruimte", (610, 5345, 660, 5420), "source_label"),
    ("ls",        "low_voltage_room", ["Z1", "Z3", "Z4", "Z2"], "LS-ruimte", (690, 5345, 750, 5420), "source_label"),
]

# randrol per (ongeordend) vertexpaar; default 'wall_drawn'
EDGE_ROLES = {
    ("D", "E"): "virtual_opening",   # alleen onderbroken stippellijn, geen massieve wand: kandidaat-doorgang entree-hal
    ("C", "D"): "wall_drawn_thin",
    ("S4", "U3"): "wall_drawn_thin", ("U2", "U3"): "wall_drawn_thin", ("S3", "S4"): "wall_drawn_thin",
    ("A", "E"): "facade", ("E", "M"): "facade", ("M", "Y"): "facade", ("Y", "Y2"): "facade",
}

LINES = [
    ("facade_w", "facade_wall", ["A", "E", "M", "Y", "Y2", "FA2"], "Gevellijn langs Schans-zijde (alleen pilottraject)"),
    ("lift_car", "lift_car_symbol", ["LC1", "LC2", "LC3", "LC4", "LC1"], "Liftkooi-symbool binnen schacht"),
    ("trap180_walkline", "stair_walkline_symbol", ["ST1", "ST2"], "Looplijn/pijl trap 180 (treden niet afzonderlijk getraceerd)"),
]

# extra labels zonder eigen ruimte (tekst + aanwijslijn), toegewezen indien aanwijsbaar
EXTRA_LABELS = [
    ("180", "index_number_candidate", (285, 4870, 320, 4940), ["trap180"], "uncertain",
     "Omcirkeld nummer 180 in trapruimte; betekenis (indexnummer hoofdsplitsing/gemeenschap) niet uit dit blad bewezen"),
    ("CVZ kast", "space_name", (620, 4840, 650, 4960), ["gem"], "probable",
     "Aanwijslijn eindigt in bovenste vakken van GEM.-kast"),
    ("flatkast", "space_name", (680, 4840, 710, 4960), ["gem"], "probable",
     "Aanwijslijn eindigt in bovenste vakken van GEM.-kast"),
    ("KPN, UPC, (EV)", "note", (755, 4910, 790, 5100), ["gem"], "uncertain",
     "Tekst rechts naast GEM.; staat buiten pilot-uitsnede-rand"),
    ("hydrofoor", "space_name", (455, 5440, 480, 5560), [], "uncertain",
     "Label met gestippelde contour in/naast sprinklerruimte; object niet apart getraceerd"),
    ("E-kast", "space_name", (405, 5460, 430, 5560), [], "uncertain",
     "Aanwijslijn richting box_a/box_b; toewijzing niet eenduidig"),
    ("UPC", "note", (225, 5040, 250, 5090), [], "uncertain", "Buiten gevel, aanwijslijn naar gevelkast"),
    ("DE SCHANS", "street_name", (40, 4300, 70, 4500), [], "source_label_context",
     "Straatnaam links van gevel (contextlabel, buiten pilot-geometrie)"),
]

# visueel bevestigde verbindingen
CONNECTIONS = [
    ("conn_entree_hal", "opening", ("D", "E"), ["entree", "hal"], "uncertain",
     "Tussen gevel (x≈274) en dunne wand (vanaf x≈358) staat geen massieve wandlijn maar een onderbroken/gestippelde lijn (y≈4985): geïnterpreteerd als open doorgang; betekenis stippellijn niet uit legenda bewezen. Geen deurblad/draaicirkel getekend."),
]

# legacy (huidige SVG-kaart) -> nieuw object; alleen kandidaat-koppeling op functie+ligging
# (legacy_id, new_object_key, relation)
LEGACY = [
    ("BG-OOST-ENT", "entree", "same_space_candidate"), ("BG-OOST-HAL", "hal", "same_space_candidate"),
    ("BG-OOST-LIFT", "lift", "same_space_candidate"),
    ("BG-OOST-TRAP1", "trap180", "same_function_candidate"), ("BG-OOST-TRAP2", "trap2", "same_function_candidate"),
    ("BG-OOST-FIETS", "container", "same_space_candidate"),
    ("BG-OOST-SPR", "sprinkler", "same_space_candidate"), ("BG-OOST-HYD", "sprinkler", "contained_in_candidate"),
    ("BG-OOST-GAS", "gaskast", "same_space_candidate"), ("BG-OOST-EK", "box_b", "uncertain"),
    ("BG-OOST-TECH", "trafo", "part_of_candidate"), ("BG-OOST-TECH", "ls", "part_of_candidate"),
    ("BG-OOST-MK1", "gem", "part_of_candidate"), ("BG-OOST-MK2", "gem", "same_space_candidate"),
]
