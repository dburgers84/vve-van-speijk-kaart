"""3e verdieping (akte 2006 p.84, '3e Verdieping Schaal 1 a 200'): zaadpunten + classificatie voor tools/segment_bg.py --floor 3e.

Woningnummers die ook op p83 staan (216-225, 230-237) zijn vermoedelijk meerlaagse woningen (maisonnettes); 246/247, 256-259, 264/265 beginnen hier.

Sleutels sNNN eenmalig uitgedeeld op 2026-11-21 (rij van 150 px, dan x) en blijven vast. Classificatie VISUEEL gelezen
op contactbladen (geen OCR). Tuple: (key, seed_xy, kind, label_literal, index_number, has_179, note)
"""
PREFIX = "f3_seg"
FLOOR = "3e"
PAGE = 84
NATIVE = (7121, 10045)
REGION_ID = "reg_f3_seg"
REGION_NAME = "3e verdieping (semi-automatische segmentatie, binnenzijde lijn)"
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
HATCH_SEEDS = []
CUTS = [('f3_p1', (757, 4985), (757, 5032), 'Wandlijn galerij/kern 246-247 onderbroken door rond perforatiegat in de scan; hersteld langs de getekende lijn'), ('f3_p2', (757, 5155), (757, 5202), 'Idem, tweede perforatiegat'), ('f3_p2b', (728, 5182), (760, 5182), 'Onderlijn trapkern bij 246 weggevallen in het tweede perforatiegat; hersteld langs de getekende lijn'), ('f3_k', (525, 5183), (548, 5183), 'Linkeronderhoek trapkern 246/247 open door scanuitval; hersteld langs de getekende lijn')]
LEGEND_BBOX = None
IDX180 = {}
IDX180_KEYS = ['s001', 's002', 's006', 's011', 's013', 's026', 's027', 's028', 's029', 's030', 's031', 's032', 's033', 's034', 's048', 's074']   # vakken met een omcirkelde 180 zonder eigen indexnummer
SEEDS = [
    ('s000', (6644, 1779), 'wall_band', None, None, False, None),
    ('s001', (6834, 1174), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s002', (2432, 1540), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s003', (2074, 2837), 'unlabeled_space', None, None, False, 'Groot blok met drie installatiesymbolen en dunne deellijnen; label niet gelezen, geen 180 gevonden'),
    ('s004', (3350, 2018), 'apartment_dwelling', 'woning', '225', False, 'Vide-symbool in hetzelfde gesloten vlak'),
    ('s005', (3398, 2111), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s006', (3609, 2199), 'unlabeled_space', None, None, False, 'Strook met omcirkeld 180 (functie niet gelezen)'),
    ('s007', (3608, 2074), 'unlabeled_space', None, None, False, 'Vak met gestippeld kruis, geen label (vide-symbool?)'),
    ('s008', (3349, 2286), 'apartment_dwelling', 'woning', '224', False, None),
    ('s009', (3521, 2355), 'void', 'vide', None, False, 'Vide'),
    ('s010', (3367, 2465), 'apartment_dwelling', 'woning', '223', False, None),
    ('s011', (3460, 2338), 'unlabeled_space', None, None, False, "Klein vak met draaiboog en omcirkeld 180, onder 'vide'"),
    ('s012', (3481, 2397), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s013', (985, 2843), 'roof', 'None', None, False, "Blok met omcirkeld 180, dunne deellijnen en 'lift-uitl.'; label 'dak' niet gelezen"),
    ('s014', (409, 2515), 'wall_band', None, None, False, None),
    ('s015', (480, 2566), 'lift_overrun', 'lift-uitl.', None, False, 'Liftuitloop (opbouw liftschacht)'),
    ('s016', (3555, 2618), 'apartment_dwelling', 'woning', '222', False, None),
    ('s017', (3552, 2766), 'apartment_dwelling', 'woning', '221', False, None),
    ('s018', (3367, 2901), 'apartment_dwelling', 'woning', '220', False, None),
    ('s019', (3251, 3060), 'unlabeled_space', None, None, False, 'Vak met gestippeld kruis, geen label (vide-symbool?)'),
    ('s020', (3423, 3079), 'commercial_multi_unresolved', None, None, True, "Label 'beheerder' + trap in één gesloten vlak; indexnummer 179"),
    ('s021', (3493, 2929), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s022', (3365, 3357), 'apartment_dwelling', 'woning', '219', False, None),
    ('s023', (3414, 3174), 'unlabeled_space', None, None, False, "Klein vak met draaiboog bij label 'trap'"),
    ('s024', (3484, 3282), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s025', (234, 3680), 'wall_band', None, None, False, None),
    ('s026', (412, 4143), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s027', (1115, 3409), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (naast woning 230-237, bouwnr. 50)'),
    ('s028', (1371, 3481), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 51)'),
    ('s029', (1452, 3408), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 52)'),
    ('s030', (1598, 3413), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 53)'),
    ('s031', (1765, 3336), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 54)'),
    ('s032', (2008, 3434), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 55)'),
    ('s033', (2090, 3365), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 56)'),
    ('s034', (2199, 3410), 'void', 'vide', None, False, 'Vide met omcirkeld 180 (bouwnr. 57)'),
    ('s035', (3555, 3502), 'apartment_dwelling', 'woning', '218', False, None),
    ('s036', (1188, 3793), 'apartment_dwelling', 'woning', '230', False, None),
    ('s037', (1342, 3780), 'apartment_dwelling', 'woning', '231', False, None),
    ('s038', (1494, 3778), 'apartment_dwelling', 'woning', '232', False, None),
    ('s039', (1642, 3784), 'apartment_dwelling', 'woning', '233', False, None),
    ('s040', (1845, 3757), 'apartment_dwelling', 'woning', '234', False, None),
    ('s041', (1938, 3779), 'apartment_dwelling', 'woning', '235', False, None),
    ('s042', (2089, 3782), 'apartment_dwelling', 'woning', '236', False, None),
    ('s043', (2244, 3802), 'apartment_dwelling', 'woning', '237', False, None),
    ('s044', (3551, 3651), 'apartment_dwelling', 'woning', '217', False, None),
    ('s045', (1982, 3707), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s046', (2051, 3645), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s047', (3371, 3787), 'apartment_dwelling', 'woning', '216', False, None),
    ('s048', (2464, 3952), 'unlabeled_space', None, None, False, 'Strook met omcirkeld 180 (label niet gelezen)'),
    ('s049', (3479, 3825), 'unlabeled_space', None, None, False, 'Klein vak met draaiboog (deur), geen label'),
    ('s050', (88, 4888), 'private_outdoor', 'buitenr.', None, False, None),
    ('s051', (268, 4915), 'apartment_dwelling', 'woning', '247', False, 'Lift-/trapkern ligt ernaast (eigen vakken)'),
    ('s052', (268, 5201), 'apartment_dwelling', 'woning', '246', False, 'Gescheiden van de galerij en de trapkern met 4 herstelde lijnen (2 perforatiegaten + scanuitval), zie CUTS'),
    ('s053', (164, 5160), 'private_outdoor', 'buitenr.', None, False, None),
    ('s054', (556, 5130), 'unlabeled_space', None, None, False, 'Klein vak met looppijlen bij de galerij'),
    ('s055', (597, 5013), 'lift_shaft', 'lift', None, False, None),
    ('s056', (690, 5107), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s057', (612, 5131), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s058', (646, 5157), 'stair', 'trap', None, False, 'Trapstrook'),
    ('s059', (288, 5717), 'private_outdoor', 'buitenr.', None, False, None),
    ('s060', (662, 5925), 'apartment_dwelling', 'woning', '259', False, None),
    ('s061', (424, 6206), 'apartment_dwelling', 'woning', '258', False, None),
    ('s062', (237, 6326), 'private_outdoor', 'buitenr.', None, False, None),
    ('s063', (255, 6434), 'private_outdoor', 'buitenr.', None, False, None),
    ('s064', (423, 6454), 'apartment_dwelling', 'woning', '257', False, None),
    ('s065', (662, 6777), 'apartment_dwelling', 'woning', '256', False, None),
    ('s066', (278, 6750), 'private_outdoor', 'buitenr.', None, False, None),
    ('s067', (606, 7522), 'apartment_dwelling', 'woning', '265', False, None),
    ('s068', (860, 7694), 'wall_band', None, None, False, None),
    ('s069', (882, 7846), 'apartment_dwelling', 'woning', '264', False, None),
    ('s070', (773, 7576), 'stair', 'trap', None, False, 'Trap bij galerij'),
    ('s071', (807, 7604), 'stair', 'trap', None, False, 'Trap bij galerij'),
    ('s072', (873, 7640), 'stair', 'trap', None, False, 'Trap bij galerij'),
    ('s073', (296, 7741), 'unlabeled_space', None, None, False, 'Kleiner vak met dunne lijn bij woning 265 (buitenruimte?), geen label'),
    ('s074', (780, 6000), 'gallery', 'galerij', None, False, 'Galerij langs 246-259 naar het trappenhuis bij 264/265; omcirkeld 180 aan beide uiteinden'),
    ('s075', (539, 5120), 'wall_band', None, None, False, None),
]
