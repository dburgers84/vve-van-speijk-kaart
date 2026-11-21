"""2e verdieping (akte 2006 p.83, '2e Verdieping Schaal 1 a 200'): zaadpunten + classificatie voor tools/segment_bg.py --floor 2e.

Sleutels sNNN eenmalig uitgedeeld op 2026-11-21 (rij van 150 px, dan x; s117/s118 later toegevoegd omdat hun vak tot y 8177/8242 loopt)
en blijven vast. Classificatie VISUEEL gelezen op contactbladen (geen OCR). Op dit blad: 44 woningnummers, geen bergingen.
Omcirkeld 180 staat bij de woningen en in de dak-/installatieblokken; 179 in de lange stroken en blokken (commercieel deel).
Tuple: (key, seed_xy, kind, label_literal, index_number, has_179, note)
"""
PREFIX = "f2_seg"
FLOOR = "2e"
PAGE = 83
NATIVE = (7120, 10055)
REGION_ID = "reg_f2_seg"
REGION_NAME = "2e verdieping (semi-automatische segmentatie, binnenzijde lijn)"
REGION_PX = (150, 300, 7000, 8300)
INK_THRESHOLD = 200
LINE_MIN_PX = 31
LINE_GAP_PX = 0
MIN_JOG_AREA_PX2 = 60
HOLE_MIN_PX2 = 400
CLOSE_PX_SMALL, CLOSE_PX_LARGE = 5, 25
EPS_SMALL, EPS_LARGE = 1.5, 2.5
HATCH_MODE = "diagonal"
HATCH_DIAG_LEN = 21
HATCH_WIN, HATCH_DENSITY = 41, 0.03
HATCH_BARRIER_ERODE = 17
HATCH_SEEDS = [
    ("h1", (3034, 6575), "Gearceerd deel van de lange strook (legenda: 'niet in de splitsing betrokken')"),
]
CUTS = []
LEGEND_BBOX = (3586, 6430, 3758, 6724)
IDX180 = {}
IDX180_KEYS = ['s002', 's007', 's012', 's015', 's017', 's023', 's034', 's036', 's045', 's072', 's083', 's102']   # vakken met een omcirkelde 180 zonder eigen indexnummer (daken/kernen/hal)
SEEDS = [
    ('s000', (6312, 729), 'wall_band', None, None, False, None),
    ('s001', (5056, 829), 'unlabeled_space', None, None, False, 'Lange strook langs 179-blok (functie niet gelezen)'),
    ('s002', (6733, 761), 'core_multi_unresolved', None, None, False, 'Lift + mk + trap in één gesloten vlak; omcirkeld 180 in het vak'),
    ('s003', (6858, 636), 'wall_band', None, None, False, None),
    ('s004', (6647, 688), 'stair', 'trap', None, False, None),
    ('s005', (6946, 1624), 'apartment_dwelling', 'woning', '207', False, None),
    ('s006', (6847, 722), 'lift_shaft', 'lift', None, False, None),
    ('s007', (3607, 1267), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s008', (4859, 920), 'wall_band', None, None, False, None),
    ('s009', (5293, 1042), 'a179_region_unresolved', None, None, True, 'Blok met indexnummer 179 (functie/onderverdeling niet gelezen)'),
    ('s010', (6739, 1606), 'apartment_dwelling', 'woning', '206', False, None),
    ('s011', (2405, 1527), 'apartment_dwelling', 'woning', '183', False, None),
    ('s012', (2668, 1551), 'unlabeled_space', None, None, False, 'Klein vak met omcirkeld 180 en gestippeld vierkant tussen woningen 183 en 184'),
    ('s013', (2910, 1514), 'apartment_dwelling', 'woning', '184', False, None),
    ('s014', (707, 2345), 'wall_band', None, None, False, None),
    ('s015', (411, 1991), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s016', (1477, 1529), 'wall_band', None, None, False, None),
    ('s017', (1171, 1727), 'roof', 'dak', None, False, 'Dak; omcirkeld 180 in het vak'),
    ('s018', (1506, 1529), 'wall_band', None, None, False, None),
    ('s019', (1506, 1545), 'cross_marked_cell', None, None, False, None),
    ('s020', (2254, 1655), 'private_outdoor', 'buitenr.', None, False, None),
    ('s021', (2692, 1608), 'unlabeled_space', None, None, False, 'Klein vak met looppijl'),
    ('s022', (3103, 1630), 'private_outdoor', 'buitenr.', None, False, None),
    ('s023', (4273, 2030), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s024', (6355, 1770), 'wall_band', None, None, False, None),
    ('s025', (5995, 1653), 'a179_region_unresolved', None, None, True, 'Blok met indexnummer 179 (functie/onderverdeling niet gelezen)'),
    ('s026', (1526, 1726), 'cross_marked_cell', None, None, False, None),
    ('s027', (1927, 1780), 'private_outdoor', 'buitenr.', None, False, None),
    ('s028', (2140, 1818), 'private_outdoor', 'buitenr.', None, False, None),
    ('s029', (2657, 1679), 'unlabeled_space', None, None, False, None),
    ('s030', (1835, 1941), 'apartment_dwelling', 'woning', '194', False, None),
    ('s031', (2141, 1938), 'apartment_dwelling', 'woning', '195', False, None),
    ('s032', (3361, 2042), 'apartment_dwelling', 'woning', '225', False, 'Lift- en trapsymbolen liggen in hetzelfde gesloten vlak (kern niet gesloten in lijnwerk)'),
    ('s033', (3626, 2064), 'lift_shaft', 'lift', None, False, None),
    ('s034', (3627, 2302), 'unlabeled_space', None, None, False, 'Gang/hal met omcirkeld 180 en twee meterkasten (mk); functie niet als label gelezen'),
    ('s035', (1741, 2478), 'void', 'vide', None, False, None),
    ('s036', (2093, 2453), 'core_multi_unresolved', None, None, False, 'Lift + trap + vide in één gesloten vlak; omcirkeld 180 in het vak'),
    ('s037', (1822, 2418), 'stair', 'trap', None, False, None),
    ('s038', (2092, 2406), 'lift_shaft', 'lift', None, False, None),
    ('s039', (3364, 2307), 'apartment_dwelling', 'woning', '224', False, None),
    ('s040', (1824, 2864), 'apartment_dwelling', 'woning', '197', False, None),
    ('s041', (2242, 2871), 'apartment_dwelling', 'woning', '196', False, None),
    ('s042', (3383, 2488), 'apartment_dwelling', 'woning', '223', False, None),
    ('s043', (347, 2803), 'apartment_dwelling', 'woning', '200', False, None),
    ('s044', (491, 2666), 'unlabeled_space', None, None, False, None),
    ('s045', (593, 2602), 'core_multi_unresolved', None, None, False, 'Trap + lift in één gesloten vlak; omcirkeld 180 in het vak'),
    ('s046', (434, 2574), 'wall_band', None, None, False, None),
    ('s047', (452, 2590), 'lift_shaft', 'lift', None, False, None),
    ('s048', (1054, 2807), 'apartment_dwelling', 'woning', '201', False, None),
    ('s049', (3375, 2643), 'apartment_dwelling', 'woning', '222', False, None),
    ('s050', (3377, 2766), 'apartment_dwelling', 'woning', '221', False, None),
    ('s051', (303, 2998), 'private_outdoor', 'buitenr.', None, False, None),
    ('s052', (1017, 2993), 'private_outdoor', 'buitenr.', None, False, None),
    ('s053', (2010, 2996), 'private_outdoor', 'buitenr.', None, False, None),
    ('s054', (2140, 2990), 'private_outdoor', 'buitenr.', None, False, None),
    ('s055', (3579, 3038), 'apartment_dwelling', 'woning', '220', False, "Omcirkeld '1' in het vak (betekenis niet in legenda gevonden)"),
    ('s056', (3372, 3127), 'commercial_multi_unresolved', None, None, True, "Label 'beheerder' + trap in één gesloten vlak; omcirkeld '1' in het vak"),
    ('s057', (3593, 3365), 'apartment_dwelling', 'woning', '219', False, None),
    ('s058', (3425, 3284), 'unlabeled_space', None, None, False, "Klein vak met looppijl bij label 'trap'"),
    ('s059', (1228, 3809), 'apartment_dwelling', 'woning', '230', False, None),
    ('s060', (1360, 3809), 'apartment_dwelling', 'woning', '231', False, None),
    ('s061', (1534, 3808), 'apartment_dwelling', 'woning', '232', False, None),
    ('s062', (1661, 3803), 'apartment_dwelling', 'woning', '233', False, None),
    ('s063', (1829, 3803), 'apartment_dwelling', 'woning', '234', False, None),
    ('s064', (1957, 3802), 'apartment_dwelling', 'woning', '235', False, None),
    ('s065', (2130, 3803), 'apartment_dwelling', 'woning', '236', False, None),
    ('s066', (2262, 3800), 'apartment_dwelling', 'woning', '237', False, None),
    ('s067', (3385, 3524), 'apartment_dwelling', 'woning', '218', False, None),
    ('s068', (300, 3597), 'private_outdoor', 'buitenr.', None, False, None),
    ('s069', (439, 3656), 'apartment_dwelling', 'woning', '243', False, None),
    ('s070', (3388, 3675), 'apartment_dwelling', 'woning', '217', False, None),
    ('s071', (4122, 3638), 'wall_band', None, None, False, None),
    ('s072', (4276, 3726), 'roof', None, None, False, "Dak-/installatieblok; omcirkeld 180 in het vak (label 'dak' niet gelezen)"),
    ('s073', (3402, 3806), 'apartment_dwelling', 'woning', '216', False, None),
    ('s074', (401, 3904), 'apartment_dwelling', 'woning', '242', False, None),
    ('s075', (2425, 4044), 'wall_band', None, None, False, None),
    ('s076', (3144, 4050), 'wall_band', None, None, False, None),
    ('s077', (445, 4165), 'apartment_dwelling', 'woning', '241', False, None),
    ('s078', (309, 4252), 'private_outdoor', 'buitenr.', None, False, None),
    ('s079', (2607, 4064), 'wall_band', None, None, False, None),
    ('s080', (2564, 4148), 'a179_region_unresolved', None, None, True, 'Lange strook met indexnummer 179'),
    ('s081', (3009, 4235), 'a179_region_unresolved', None, None, True, 'Lange strook met indexnummer 179 (loopt door tot de arcering)'),
    ('s082', (1756, 4862), 'wall_band', None, None, False, None),
    ('s083', (1602, 4453), 'roof', None, None, False, "Dak-/installatieblok; omcirkeld 180 in het vak (label 'dak' niet gelezen)"),
    ('s084', (3526, 4493), 'wall_band', None, None, False, None),
    ('s085', (4215, 4620), 'a179_region_unresolved', None, None, True, 'L-vormig blok met indexnummer 179'),
    ('s086', (167, 4931), 'private_outdoor', 'buitenr.', None, False, None),
    ('s087', (309, 4964), 'apartment_dwelling', 'woning', '245', False, None),
    ('s088', (1455, 4929), 'wall_band', None, None, False, None),
    ('s089', (1609, 5120), 'a179_region_unresolved', None, None, True, 'Strook met indexnummer 179'),
    ('s090', (1746, 4880), 'wall_band', None, None, False, None),
    ('s091', (594, 5073), 'wall_band', None, None, False, None),
    ('s092', (649, 5058), 'lift_shaft', 'lift', None, False, None),
    ('s093', (170, 5150), 'private_outdoor', 'buitenr.', None, False, None),
    ('s094', (313, 5248), 'apartment_dwelling', 'woning', '244', False, None),
    ('s095', (594, 5112), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s096', (714, 5127), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s097', (668, 5160), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s098', (694, 5183), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s099', (708, 5206), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s100', (329, 5935), 'private_outdoor', 'buitenr.', None, False, None),
    ('s101', (469, 5969), 'apartment_dwelling', 'woning', '255', False, None),
    ('s102', (1623, 6227), 'roof', None, None, False, "Dak-/installatieblok; omcirkeld 180 in het vak (label 'dak' niet gelezen)"),
    ('s103', (469, 6177), 'apartment_dwelling', 'woning', '254', False, None),
    ('s104', (1470, 6100), 'wall_band', None, None, False, None),
    ('s105', (332, 6209), 'private_outdoor', 'buitenr.', None, False, None),
    ('s106', (335, 6430), 'private_outdoor', 'buitenr.', None, False, None),
    ('s107', (477, 6567), 'apartment_dwelling', 'woning', '253', False, None),
    ('s108', (481, 6821), 'apartment_dwelling', 'woning', '252', False, None),
    ('s109', (339, 6838), 'private_outdoor', 'buitenr.', None, False, None),
    ('s110', (2961, 7197), 'wall_band', None, None, False, None),
    ('s111', (3014, 7219), 'a179_region_unresolved', None, None, True, "Vak met groot '179' aan het eind van de strook, voorbij de arcering"),
    ('s112', (673, 7565), 'apartment_dwelling', 'woning', '263', False, None),
    ('s113', (808, 7612), 'wall_band', None, None, False, None),
    ('s114', (870, 7586), 'stair', 'trap', None, False, 'Trap bij galerij'),
    ('s115', (941, 7680), 'stair', 'trap', None, False, 'Trap bij galerij'),
    ('s116', (365, 7786), 'unlabeled_space', None, None, False, 'Kleiner vak met dunne lijn bij woning 263 (buitenruimte?), geen label'),
    ('s117', (952, 7886), 'apartment_dwelling', 'woning', '262', False, None),
    ('s118', (680, 8096), 'unlabeled_space', None, None, False, 'Kleiner vak met dunne lijn bij woning 262 (buitenruimte?), geen label'),
]
