"""4e verdieping en daken (akte 2006 p.85, '4e Verdieping en daken Schaal 1 a 200'): zaadpunten + classificatie voor tools/segment_bg.py --floor 4e.

Op dit blad alleen de bovenste laag van woningen 256-259 (ook op p84) plus daken; geen nieuwe woningnummers.

Sleutels sNNN eenmalig uitgedeeld op 2026-11-21 (rij van 150 px, dan x) en blijven vast. Classificatie VISUEEL gelezen
op contactbladen (geen OCR). Tuple: (key, seed_xy, kind, label_literal, index_number, has_179, note)
"""
PREFIX = "f4_seg"
FLOOR = "4e"
PAGE = 85
NATIVE = (7084, 10039)
REGION_ID = "reg_f4_seg"
REGION_NAME = "4e verdieping en daken (semi-automatische segmentatie, binnenzijde lijn)"
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
CUTS = []
LEGEND_BBOX = None
IDX180 = {}
IDX180_KEYS = ['s001', 's003', 's011', 's019', 's033']   # vakken met een omcirkelde 180 zonder eigen indexnummer
SEEDS = [
    ('s000', (1844, 2416), 'roof', 'None', None, False, 'Dakvlak (helft van blok met s001, dunne deellijn); omcirkeld 180 staat in buurvak s001'),
    ('s001', (2182, 2433), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s002', (3288, 3247), 'roof', 'None', None, False, "Dakvlak met kleine opbouwen (helft van blok met s003); grenst aan vak '179' (s018)"),
    ('s003', (3533, 2922), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone; omcirkeld 180 in het vak'),
    ('s004', (3593, 2044), 'roof', 'dak lifthuis', None, False, 'Dak lifthuis'),
    ('s005', (3325, 2176), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s006', (3510, 2183), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s007', (3590, 2136), 'unlabeled_space', None, None, False, 'Klein vak met gestippeld vierkant op dak, geen label'),
    ('s008', (3329, 2345), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s009', (3508, 2315), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s010', (3336, 2472), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s011', (681, 2681), 'roof', 'None', None, False, 'Dakvlak met installatiesymbolen; omcirkeld 180 in het vak'),
    ('s012', (487, 2674), 'unlabeled_space', None, None, False, 'Vak met gestippelde deellijn en X-vak, geen label'),
    ('s013', (3335, 2627), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s014', (699, 2919), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone (helft van blok met s011; 180 staat in buurvak)'),
    ('s015', (3339, 2776), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s016', (3345, 2923), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s017', (6384, 3030), 'roof', 'dak', None, True, "Vak '179' met label 'dak'"),
    ('s018', (3318, 3072), 'a179_region_unresolved', None, None, True, "Vak '179' met gestippeld kruis (vide/opening?); label niet gelezen"),
    ('s019', (2177, 3429), 'roof', 'None', None, False, "Dakvlak met kleine opbouwen; omcirkeld 180 in het vak"),
    ('s020', (1211, 3521), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s021', (1349, 3503), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s022', (1530, 3501), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s023', (1671, 3484), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s024', (1800, 3500), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s025', (1962, 3481), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s026', (2078, 3480), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s027', (2263, 3479), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s028', (3345, 3499), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s029', (1697, 3771), 'roof', 'None', None, False, 'Dak + indicatieve installatiezone (helft van blok met s019; 180 staat in buurvak)'),
    ('s030', (3344, 3654), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s031', (3351, 3797), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s032', (5080, 6217), 'roof', 'dak', None, False, 'Dak + indicatieve installatiezone (helft van blok met s033; 180 staat in buurvak)'),
    ('s033', (5335, 6301), 'roof', 'None', None, False, 'Dakvlak met installatiesymbolen; omcirkeld 180 in het vak'),
    ('s034', (399, 5879), 'apartment_dwelling', 'woning', '259', False, None),
    ('s035', (5328, 5859), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s036', (398, 6255), 'apartment_dwelling', 'woning', '258', False, None),
    ('s037', (5334, 6154), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s038', (399, 6485), 'apartment_dwelling', 'woning', '257', False, None),
    ('s039', (5334, 6443), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
    ('s040', (408, 6851), 'apartment_dwelling', 'woning', '256', False, None),
    ('s041', (5337, 6735), 'roof_symbol', None, None, False, 'Klein rechthoekig symbool op dak (opbouw/installatie?), geen label'),
]
