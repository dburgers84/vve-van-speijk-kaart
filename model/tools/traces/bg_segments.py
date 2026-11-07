"""BG overige delen: zaadpunten + classificatie voor tools/segment_bg.py (akte 2006 p.81, native px).

Elke SEED heeft een VASTE sleutel (sNNN, eenmalig uitgedeeld 2026-11-07); de geometrie wordt
reproduceerbaar uit de lokale scan afgeleid (data/inventory/bg_segments_p81.json).
kind:
  commercial_unit                    1 label 'bedrijfs-ruimte' (template-match, visueel steekproef)
  commercial_multi_unresolved        >=2 labels in één gesloten vlak: tussenwanden deels/niet getekend
  commercial_large_region_unresolved zeer groot vlak (>~790 m2) met 1 gevonden label: aantal eenheden niet vastgesteld
  wall_band                          strook tussen dubbele lijnen (getekende wanddikte), geen ruimte
  unlabeled_space / unresolved_space geen leesbaar label / functie onbekend
  overige                            handmatig gelezen label (zie LABEL)
Label-bboxen 'bedrijfs-ruimte' komen uit template-matching (score erbij); handmatige labels visueel gelezen.
"""
PREFIX = "bg_seg"
REGION_ID = "reg_bg_seg"
REGION_NAME = "BG overige delen (semi-automatische segmentatie, binnenzijde lijn)"
REGION_PX = (0, 350, 7118, 7600)
INK_THRESHOLD = 200
CLOSE_PX_SMALL, CLOSE_PX_LARGE = 5, 25
EPS_SMALL, EPS_LARGE = 1.5, 2.5
HATCH_WIN, HATCH_DENSITY = 81, 0.12
HATCH_SEEDS = [
    ("h1", (1000, 1900), "Gearceerd vlak linksboven (legenda: 'niet in de splitsing betrokken')"),
    ("h2", (3100, 6600), "Gearceerd vlak onderaan (legenda: 'niet in de splitsing betrokken')"),
]
CUTS = [
    ("bgB", (527, 2594), (890, 2594), "Gestippelde lijn tussen vak-180 en container-ruimte (kern B); als grens gebruikt, GEEN wand/deur geclaimd"),
    ("bgC_ls", (4562, 2606), (4702, 2606), "Bovenlijn LS-ruimte (kern C) onderbroken in scan; hersteld langs getekende lijn"),
    ("bgC_lt", (4568, 2683), (4700, 2683), "Scheidingslijn LS-ruimte/trafo ruimte (kern C) onderbroken in scan; hersteld langs getekende lijn"),
]
LEGEND_BBOX = (700, 850, 890, 1235)
# omcirkelde 180 (visueel bevestigd; bbox ca. template 60x130 px)
IDX180 = {"s039": (3740, 1940, 3800, 2070), "s052": (633, 2495, 693, 2625), "s061": (4513, 2657, 4573, 2787)}
CU_SRC = "Gebruiker (eerder bevestigd; data/sources.md): alle containerruimtes zijn omgebouwd tot fietsenberging"
CURRENT_USE = {"s061": ("fietsenberging", CU_SRC, "user_confirmed"), "s052b": ("fietsenberging", CU_SRC, "user_confirmed")}
# kernen (gemeenschappelijke woonkernen) en hun vakken
CORES = {"A": ["s038", "s039", "s042", "s043", "s044", "s045", "s046", "s047"],
         "B": ["s049", "s050", "s052", "s052b", "s055", "s056"],
         "C": ["s061", "s066", "sC_ls", "sC_trafo"],
         "E": ["s118", "s119", "s121", "s122"]}
CORE_HAS_180 = {"A": "s039", "B": "s052", "C": "s061"}   # kern E: geen 180 gevonden
# (key, seed_xy, kind, label_literal, label_bbox, note, bedrijf_label_hits[x0,y0,x1,y1,score], idx179_hits)
SEEDS = [
    ('s000', (2667, 637), 'wall_band', None, None, None, [], []),
    ('s001', (3090, 614), 'wall_band', None, None, None, [], []),
    ('s002', (3359, 777), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3416, 907, 3470, 1017, 0.694]], [[3295, 1225]]),
    ('s003', (3459, 609), 'wall_band', None, None, None, [], []),
    ('s004', (3718, 608), 'wall_band', None, None, None, [], []),
    ('s005', (4030, 605), 'wall_band', None, None, None, [], []),
    ('s006', (4256, 784), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[4374, 979, 4428, 1089, 0.676]], []),
    ('s007', (4281, 603), 'wall_band', None, None, None, [], []),
    ('s008', (5115, 677), 'wall_band', None, None, None, [], []),
    ('s009', (5717, 671), 'wall_band', None, None, None, [], []),
    ('s010', (5954, 668), 'wall_band', None, None, None, [], []),
    ('s011', (6171, 797), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[6264, 872, 6318, 982, 0.724]], []),
    ('s012', (6274, 665), 'wall_band', None, None, None, [], []),
    ('s018', (3934, 840), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3933, 1030, 3987, 1140, 0.659]], []),
    ('s019', (4860, 827), 'wall_band', None, None, None, [], []),
    ('s020', (4992, 811), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[5083, 890, 5137, 1000, 0.723]], []),
    ('s022', (5435, 1088), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[5525, 884, 5579, 994, 0.701]], [[5607, 879]]),
    ('s023', (5866, 1096), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[5895, 878, 5949, 988, 0.684]], []),
    ('s024', (2185, 1394), 'wall_band', None, None, None, [], []),
    ('s025', (4955, 1229), 'wall_band', None, None, None, [], []),
    ('s026', (2139, 1435), 'unlabeled_space', None, None, 'Smalle strook (~1,7 m) bovenin blok; geen label gevonden', [], []),
    ('s027', (2980, 1586), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2791, 1043, 2845, 1153, 0.645]], []),
    ('s028', (5870, 1559), 'wall_band', None, None, None, [], []),
    ('s029', (2145, 1697), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2129, 1933, 2183, 2043, 0.69]], []),
    ('s030', (2437, 1609), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2550, 1652, 2604, 1762, 0.672]], []),
    ('s031', (3108, 1753), 'wall_band', None, None, None, [], []),
    ('s032', (4973, 1685), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[5091, 1634, 5145, 1744, 0.671]], []),
    ('s033', (5416, 1691), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[5534, 1626, 5588, 1736, 0.694]], [[5616, 1621]]),
    ('s034', (5898, 1684), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[6051, 1616, 6105, 1726, 0.696]], []),
    ('s035', (6557, 1664), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[6731, 1604, 6785, 1714, 0.705]], []),
    ('s036', (6936, 1782), 'wall_band', None, None, None, [], []),
    ('s037', (2519, 1853), 'wall_band', None, None, None, [], []),
    ('s038', (3600, 1982), 'unlabeled_space', None, None, "Vak naast GEM./lift; tekst 'CVZ kast' staat links buiten de kern, toewijzing niet bewezen", [], []),
    ('s039', (3759, 1988), 'entrance_hall', 'entree', (3700, 1950, 3725, 2010), 'Label entree + omcirkeld 180', [], []),
    ('s040', (5413, 1818), 'wall_band', None, None, None, [], []),
    ('s041', (3343, 2130), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3352, 2222, 3406, 2332, 1.0]], []),
    ('s042', (3557, 2071), 'meter_cupboard_common', 'GEM.', (3520, 2040, 3560, 2120), None, [], []),
    ('s043', (3618, 2107), 'lift_shaft', 'lift', (3600, 2040, 3625, 2085), None, [], []),
    ('s044', (3688, 2071), 'unlabeled_space', None, None, 'Vak tussen lift en trap; geen label', [], []),
    ('s045', (3729, 2194), 'unresolved_space', None, None, 'Vak onder de diagonale (snij)lijn van de trap; functie niet uit tekening af te leiden', [], []),
    ('s046', (3757, 2104), 'stair', 'trap', (3735, 2040, 3765, 2090), None, [], []),
    ('s047', (3785, 2039), 'unlabeled_space', None, None, 'Smalle strook (~0,45 m) naast trap; wand of schacht niet bewezen', [], []),
    ('s048', (3802, 2191), 'wall_band', None, None, None, [], []),
    ('s049', (298, 2545), 'entrance_hall', 'entree', (300, 2490, 330, 2570), None, [], []),
    ('s050', (422, 2499), 'stair', 'trap', (400, 2530, 430, 2580), None, [], []),
    ('s052', (582, 2523), 'unlabeled_space', None, None, 'Vak met omcirkeld 180, boven de gestippelde lijn (CUT bgB); functie niet gelabeld', [], []),
    ('s054', (3952, 2577), 'commercial_large_region_unresolved', 'bedrijfs-ruimte', None, None, [[3356, 2666, 3410, 2776, 0.727]], []),
    ('s055', (383, 2642), 'hall', 'hal', (330, 2640, 355, 2690), None, [], []),
    ('s056', (519, 2627), 'lift_shaft', 'lift', (465, 2610, 490, 2650), None, [], []),
    ('s057', (999, 2661), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[995, 2831, 1049, 2941, 0.662]], []),
    ('s058', (1295, 2647), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[1289, 2831, 1343, 2941, 0.675]], []),
    ('s059', (1611, 2613), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[1659, 2830, 1713, 2940, 0.718]], []),
    ('s060', (2162, 2717), 'commercial_multi_unresolved', 'bedrijfs-ruimte', None, None, [[2131, 2829, 2185, 2939, 0.753], [2130, 2378, 2184, 2488, 0.638]], []),
    ('s061', (4462, 2666), 'container_room', 'container-ruimte', (4440, 2700, 4510, 2810), 'Omcirkeld 180 in dit vak', [], []),
    ('s062', (261, 2855), 'wall_band', None, None, None, [], []),
    ('s063', (261, 2916), 'wall_band', None, None, None, [], []),
    ('s064', (718, 2891), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[553, 2831, 607, 2941, 0.634]], []),
    ('s065', (1888, 2963), 'wall_band', None, None, None, [], []),
    ('s066', (4469, 2880), 'unlabeled_space', None, None, 'Vak onder containerruimte (kern C); geen label', [], []),
    ('s067', (4418, 3034), 'wall_band', None, None, None, [], []),
    ('s068', (4421, 3329), 'wall_band', None, None, None, [], []),
    ('s069', (267, 3512), 'wall_band', None, None, None, [], []),
    ('s070', (1688, 3558), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[1520, 3484, 1574, 3594, 0.747]], []),
    ('s071', (267, 3701), 'wall_band', None, None, None, [], []),
    ('s072', (1894, 3635), 'wall_band', None, None, None, [], []),
    ('s073', (2184, 3779), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2121, 3483, 2175, 3593, 0.81]], []),
    ('s074', (4425, 3667), 'wall_band', None, None, None, [], []),
    ('s075', (269, 3834), 'wall_band', None, None, None, [], []),
    ('s076', (4428, 3921), 'wall_band', None, None, None, [], []),
    ('s077', (271, 4109), 'wall_band', None, None, None, [], []),
    ('s078', (359, 4159), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[452, 4019, 506, 4129, 0.586]], []),
    ('s079', (1602, 4084), 'commercial_multi_unresolved', 'bedrijfs-ruimte', None, None, [[560, 3565, 614, 3675, 0.622], [1018, 5283, 1072, 5393, 0.562]], [[1600, 4909]]),
    ('s080', (3967, 4062), 'commercial_large_region_unresolved', 'bedrijfs-ruimte', None, None, [[3364, 3407, 3418, 3517, 0.855]], [[3907, 3395]]),
    ('s081', (2318, 4381), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2190, 4166, 2244, 4276, 0.634]], []),
    ('s082', (3341, 4369), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3152, 4305, 3206, 4415, 0.739]], []),
    ('s083', (4431, 4232), 'wall_band', None, None, None, [], []),
    ('s084', (275, 4411), 'wall_band', None, None, None, [], []),
    ('s085', (362, 4459), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[454, 4322, 508, 4432, 0.672]], []),
    ('s086', (277, 4716), 'wall_band', None, None, None, [], []),
    ('s087', (563, 4623), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[457, 4619, 511, 4729, 0.708]], []),
    ('s088', (2069, 4720), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2193, 4610, 2247, 4720, 0.683]], []),
    ('s089', (3299, 4727), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3154, 4625, 3208, 4735, 0.703]], []),
    ('s090', (3939, 4781), 'unlabeled_space', None, None, 'Vak in gestippelde strook langs expeditie gang', [], []),
    ('s091', (4143, 4773), 'stair', 'trap', (4165, 4700, 4195, 4740), 'Label trap + looppijl + snijlijn; geen afzonderlijke treden getekend', [], []),
    ('s092', (4245, 4779), 'unlabeled_space', None, None, 'Vak in gestippelde strook langs expeditie gang', [], []),
    ('s093', (4299, 4768), 'unlabeled_space', None, None, 'Vak in gestippelde strook langs expeditie gang', [], []),
    ('s094', (4434, 4662), 'wall_band', None, None, None, [], []),
    ('s100', (2363, 4969), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2196, 4910, 2250, 5020, 0.611]], []),
    ('s101', (3321, 4945), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3156, 4928, 3210, 5038, 0.639]], []),
    ('s102', (3498, 4850), 'service_corridor', 'expeditie gang', (3540, 4835, 3730, 4870), None, [], []),
    ('s106', (3909, 5161), 'wall_band', None, None, None, [], []),
    ('s108', (325, 5347), 'unlabeled_space', None, None, 'Klein vak naast pilotkern; niet in pilottrace', [], []),
    ('s112', (417, 5377), 'unlabeled_space', None, None, 'Klein vak naast pilotkern; niet in pilottrace', [], []),
    ('s115', (1933, 5389), 'service_corridor', 'expeditie gang', (1440, 5385, 1620, 5420), 'L-vormige gang (horizontaal + verticaal tussen blokken)', [], []),
    ('s116', (2337, 5308), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2199, 5204, 2253, 5314, 0.705]], []),
    ('s118', (1303, 5516), 'technical_room', 'trafo ruimte', (1250, 5440, 1300, 5510), None, [], []),
    ('s119', (1304, 5596), 'technical_room', 'LS-ruimte', (1250, 5540, 1300, 5610), None, [], []),
    ('s120', (1615, 5429), 'wall_band', None, None, None, [], []),
    ('s121', (1647, 5505), 'stair', 'trap', (1660, 5620, 1700, 5650), 'Trap met looppijl en gestippelde bordesvakken; geen treden', [], []),
    ('s122', (1742, 5447), 'cross_marked_cell', None, None, 'Vak met kruis (X) naast trap; betekenis niet in legenda (sparing/vide/schacht?)', [], []),
    ('s123', (2083, 5500), 'unlabeled_space', None, None, 'Vak binnen blok; geen label', [], []),
    ('s124', (2353, 5567), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2206, 5801, 2260, 5911, 0.66]], []),
    ('s125', (681, 5797), 'wall_band', None, None, None, [], []),
    ('s126', (916, 5644), 'commercial_multi_unresolved', 'bedrijfs-ruimte', None, None, [[735, 5577, 789, 5687, 0.647], [452, 5450, 506, 5560, 0.616]], []),
    ('s127', (3915, 5773), 'wall_band', None, None, None, [], []),
    ('s128', (1620, 5872), 'commercial_large_region_unresolved', 'bedrijfs-ruimte', None, None, [[1326, 6699, 1380, 6809, 0.899]], []),
    ('s129', (3394, 5855), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[3164, 5643, 3218, 5753, 0.631]], []),
    ('s130', (291, 6010), 'wall_band', None, None, None, [], []),
    ('s131', (3748, 6170), 'service_corridor', 'expeditie gang', (3400, 6150, 3570, 6185), None, [], []),
    ('s132', (293, 6281), 'wall_band', None, None, None, [], []),
    ('s133', (2397, 6203), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2208, 6101, 2262, 6211, 0.665]], []),
    ('s134', (293, 6436), 'wall_band', None, None, None, [], []),
    ('s135', (447, 6524), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[440, 6265, 494, 6375, 0.638]], []),
    ('s136', (2391, 6491), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2211, 6402, 2265, 6512, 0.713]], []),
    ('s137', (2381, 6756), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2214, 6698, 2268, 6808, 0.933]], []),
    ('s138', (298, 6894), 'wall_band', None, None, None, [], []),
    ('s139', (374, 6926), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[444, 6783, 498, 6893, 0.89]], []),
    ('s140', (2384, 7050), 'commercial_unit', 'bedrijfs-ruimte', None, None, [[2217, 6989, 2271, 7099, 0.685]], []),
    ('s141', (544, 7369), 'round_element_part', None, None, 'Helft van rond element op hoek De Kajuit; betekenis onbekend', [], []),
    ('s142', (656, 7367), 'round_element_part', None, None, 'Helft van rond element op hoek De Kajuit; betekenis onbekend', [], []),
    ('s143', (2114, 7355), 'passage_or_overhang_unresolved', 'DE KAJUIT', (1600, 7330, 1760, 7370), 'Strook tussen dunne gevellijn (met kolommen) en dikke buitenlijn; straatnaam erin: overbouwde passage of luifel? niet bewezen', [], []),
    ('s052b', (630, 2690), 'container_room', 'container-ruimte', (780, 2640, 830, 2760), 'Onder de gestippelde lijn (CUT bgB)', [], []),
    ('sC_ls', (4630, 2645), 'technical_room', 'LS-ruimte', (4600, 2615, 4680, 2680), None, [], []),
    ('sC_trafo', (4585, 2700), 'technical_room', 'trafo ruimte', (4600, 2720, 4660, 2810), None, [], []),
]
