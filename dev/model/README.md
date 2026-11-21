# Datamodel v2 – brongetrouwe plattegrond (in opbouw)

Status: **onvolledig**. Gedaan: BG (blad p.81) en, in een eerste versie, de 1e (p.82) en 2e verdieping (p.83).
- **BG handmatig:** 2 kernen en 1 bedrijfsruimte;
- **BG semi-automatisch:** de rest van het BG (gesloten vakken op de binnenzijde van de getekende lijn, arceringen, wandstroken en visueel gecontroleerde kolomsymbolen). Een deel daarvan is expliciet **onopgelost**.
- **1e verdieping (f1-0.1.0), semi-automatisch:** alle 342 gesloten vakken met zaadpunt + 2 arceringen, zelfde lijnwerk; nummers/functies visueel gelezen (38 woningen, alle 91 bergingen 266–356). Labelposities sinds f1-0.2.0 deels gemeten (176 van 286), de rest benaderd; een deel is **onopgelost** (multi-vakken, kernen, buitenruimten met gestippelde onderverdeling).

- **2e verdieping (f2-0.1.0), semi-automatisch:** 119 vakken + 1 arcering; 39 woningen (geen bergingen op dit blad); 109 van 121 labelposities gemeten.

De 3e en 4e verdieping zijn nog niet getraceerd. De huidige kaart (`index.html`, `js/`, `svg/`) blijft de referentie. Viewer: `model/pilot/`, online `/dev/model/pilot/`.

## Inhoud
| Pad | Wat |
|---|---|
| `schema/vve-plan-v2.schema.json` | JSON Schema (draft 2020-12) |
| `validate.py` | Validator (stdlib; gebruikt `jsonschema` als dat er is) |
| `tests/test_validate.py` | Unittests (dataset + negatieve gevallen) en `tests/fixtures/stable_ids_v0.1.json` (ids mogen niet verdwijnen) |
| `tools/traces/bg_core.py`, `tools/traces/bg_kiel.py` | Handmatige traces in **native scanpixels** van akte 2006 p.81 |
| `tools/traces/bg_segments.py` + `tools/segment_bg.py` | Vaste zaadpunten en classificatie per vak; segmentatie uit de lokale scan → `data/inventory/bg_segments_p81.json` |
| `tools/traces/f1_segments.py` + `tools/segment_bg.py --floor 1e` | 1e verdieping: vaste zaadpunten/classificatie (sleutels s000–s341) → `data/inventory/f1_segments_p82.json`. Arcering op p82 via dichtheid van **diagonale** lijnstukken (de dichtheidsmethode van p81 lekte in de dicht beschreven bergingen); omsloten buurvakken worden gaten (binnenringen) |
| `tools/traces/f2_segments.py` + `tools/segment_bg.py --floor 2e` | 2e verdieping: zaadpunten/classificatie (s000–s118) → `data/inventory/f2_segments_p83.json` |
| `tools/build_floor.py --floor 1e\|2e` | Bouwt `data/fN.v2.json` + `pilot/pilot_data_fN.js` met eigen frame (`frm_p8X_native`) en kalibratie (`cal_p8X_controls`) per blad (hergebruikt Builder/maatlogica van `build_model.py`) |
| `tools/measure_labels.py --floor 1e\|2e` | Meet labelposities: inkt-eilanden binnen het vak, gegroepeerd per tekstkolom/-regel; alleen aanvaard als het aantal tekens past bij de gelezen tekst (omcirkelde 180 uitgesloten) → `data/inventory/labels_measured_p8X.json` |
| `data/inventory/calibration_p83.json` | Metingen balk + liniaal op p83 |
| `tests/test_floor2.py` | 2e verdieping + meetfunctie labels |
| `data/inventory/calibration_p82.json` | Metingen balk + liniaal op p82 |
| `tests/test_floor1.py` | Kalibratie p82, dekking (bergingen 266–356, woningenlijst), stabiele sleutels (`tests/fixtures/f1_seg_keys_v0.1.0.json`), juridisch, vloerkeuze viewer, diagonale-arceringdetectie |
| `tools/linework.py` | Bouwlijnen scheiden van tekst/symbolen (gedeeld voor alle bladen): rechte lijnen ≥ 31 px + aangesloten restinkt blijven; losse woorden, cijfers, omcirkelde 180 (gemeten box) en losse stippels vallen weg; `simplify()` verwijdert rafel-hoekjes < 60 px² |
| `tests/test_linework.py` | Regressietests: synthetische tekst/indexcirkel geeft geen wand/gat, onderbroken lijn blijft barrière, indexcirkels zonder hoekpunten/inkepingen in de dataset, stabiele segment-ids sinds v0.3.0 (`tests/fixtures/bg_seg_keys_v0.3.0.json`), afronding met geschatte marge |
| `data/inventory/columns_review_p81.json` | Visuele controle van alle 269 kolomkandidaten op p.81 (247 symbool / 12 onzeker / 10 afgekeurd) |
| `data/inventory/calibration_p81.json` | Metingen aan schaalbalk en cm-liniaal + vergelijking met nominaal |
| `tools/build_model.py` | Bouwt `data/bg.v2.json` + `pilot/pilot_data.js` (inktsteun per zijde uit lokale scan, of hergebruik met `--scan none`) |
| `tools/detect_columns.py` | Kolomkandidaten (holle vierkanten) per blad → `data/inventory/columns_auto_all.json` |
| `tools/register_plan_jpg.py` | Registreert de al gepubliceerde `img/plan_*.jpg` op het native frame → `data/inventory/registration_plan_jpg.json` |
| `tools/build_tile_register.py` | Werkregister per tile (alle 5 bladen) → `data/inventory/tile_register.json` |
| `run_checks.sh` (geen privébron nodig; segmentatie en kolomreview worden hergebruikt) | Reproduceer-, validatie- en testcheck zonder privébron |
| `pilot/index.html` | Viewer met **vloerkeuze** (BG / 1e; `#floor=1e`, laadt alleen de data van die verdieping): klikbare ruimtes/bouwdetails/zijden, popup met bronlabel vs huidig gebruik, relatieve coördinaten, afgeleide maten, buren, verbindingen, juridische lidmaatschappen |

## Kernregels
- Per bronblad één frame (`px_native`). Elke vertex heeft `x_px,y_px`, `x_rel,y_rel` en `floor_id`.
- Vaste ids; een gedeelde grens is precies één edge.
- Zijmaat: `source` | `derived` | `unknown`. Op het BG staan geen maten, dus alle lengtes zijn `derived`.
- **Kalibratie:** gebaseerd op de schaalbalk van het hoofdplan ('Begane grond, Schaal 1 a 200', 0–10 m = 387 px → 0,02584 m/px) en de cm-liniaal (78,47 px/cm → 0,02549 m/px bij 1:200).
  - We gebruiken het midden: 0,02566 m/px (≈ +1,0 % t.o.v. de oude nominale 0,0254).
  - Beide controles liggen langs native **y**. De **x-as is niet onafhankelijk gecontroleerd** (isotroop aangenomen).
  - **Geschatte marge** per zijde (geen gemeten tolerantie): ±0,7 % (y) / ±1,6 % (x) schaalspreiding, plus de afleestolerantie van beide eindpunten.
  - Weergave (`dimension.display`) is afgerond op een stap die bij die marge past: 0,1 m bij een marge van 5–50 cm (bijna alle zijden), 0,01 m alleen bij een marge < 5 cm; de marge wordt naar boven afgerond. Voorbeeld: `≈ 2,9 m (geschatte marge ±0,2 m)`. Oppervlak en omtrek in de viewer krijgen op dezelfde manier een geschatte marge (schaal + randtolerantie).
- Grenzen:
  - handmatige traces: hartlijn (bij een dubbele gevellijn de binnenlijn);
  - segmenten: de binnenzijde van de getekende lijn. Er ligt dus een wandstrook tussen buren en er zijn geen gedeelde zijden.
  - Tekst en symbolen zijn geen grens (sinds bg-0.4.0, `tools/linework.py`). Gestippelde lijnen zijn ook geen grens, tenzij expliciet als CUT met reden (bv. `bgB`); scanuitval in een doorgetrokken lijn alleen via CUT (bv. `bgD_s060`), want streepjeslijnen hebben dezelfde gaten (3–4 px).
- `source_label_text` (bron) en `current_use` (nu, met bron) staan in aparte velden.
- Een `door` mag alleen als er een deurblad of draaicirkel getekend is. Een onderbroken lijn wordt `opening_candidate`.
- **Kalibratie 1e verdieping (p82), eigen meting:** balk '1e Verdieping Schaal 1 a 200' 0–10 m = 393,2 px → 0,025432 m/px; liniaal 78,83 px/cm → 0,025371 m/px (verschil 0,24 %). Gebruikt: 0,025402 m/px. Geschatte marge y = max(halve spreiding 0,12 %, afleestolerantie balkeinden 0,54 %) = ±0,5 %; x = +0,88 % (niet getoetst) = ±1,4 %. De reproductieschaal verschilt per blad (p81-balk 387 px), daarom per blad meten.
- **Kalibratie 2e verdieping (p83):** balk 0–10 m = 397,3 px → 0,025170 m/px; liniaal 78,61 px/cm → 0,025441 m/px; verschil 1,06 % (groter dan op p82, oorzaak onbekend). Gebruikt 0,025305 m/px; geschatte marge y ±0,54 % (= halve spreiding), x ±1,4 %.
- Juridisch:
  - De hoofdsplitsing omvat het hele complex: A-179 Winkels + A-180 Woningen.
  - De ondersplitsing (85 woningen + 91 bergingen) ligt **genest binnen A-180**; het is geen apart gebied ernaast.
  - Lidmaatschap per vak is `probable`/`uncertain` en afgeleid uit indexnummers (179: 5×, omcirkeld 180: 5×) en labels. Er zijn geen getekende splitsingsgrenzen.
  - Gearceerd = 'niet in de splitsing betrokken' (legenda).
  - A-2 (titelblok) vs A-180 (MVGM): **onopgelost**.
- `current_use` voor containerruimtes = fietsenberging, `user_confirmed`: de gebruiker heeft bevestigd dat alle containerruimtes zijn omgebouwd. Het bronlabel blijft `container-ruimte`.
- Juridisch 1e/2e: dak-/installatievakken en kernen met een omcirkelde 180 = A-180 (probable); woning/berging = A-180 (probable) en ondersplitsing privé recht `O-n` (n = indexnummer op de tekening, **geen** kadastrale aanduiding); vakken met 179 = A-179; arcering = buiten beide splitsingen; trappen/liften = gemeenschappelijk (uncertain).
- Privacy: native scan en uitsneden blijven lokaal (`model/pilot/local/`, git-ignored). Online staan alleen de eerder gepubliceerde `img/plan_bg.jpg`, `img/plan_1e.jpg` en `img/plan_2e.jpg` als overlay.
