# Datamodel v2 – brongetrouwe plattegrond (in opbouw)

Status: **onvolledig**. Alleen het BG (blad p.81) is gedaan:
- **handmatig:** 2 kernen en 1 bedrijfsruimte;
- **semi-automatisch:** de rest van het BG (gesloten vakken op de binnenzijde van de getekende lijn, arceringen, wandstroken en visueel gecontroleerde kolomsymbolen). Een deel daarvan is expliciet **onopgelost**.

De 1e t/m 4e verdieping zijn nog niet getraceerd. De huidige kaart (`index.html`, `js/`, `svg/`) blijft de referentie. Viewer: `model/pilot/`, online `/dev/model/pilot/`.

## Inhoud
| Pad | Wat |
|---|---|
| `schema/vve-plan-v2.schema.json` | JSON Schema (draft 2020-12) |
| `validate.py` | Validator (stdlib; gebruikt `jsonschema` als dat er is) |
| `tests/test_validate.py` | Unittests (dataset + negatieve gevallen) en `tests/fixtures/stable_ids_v0.1.json` (ids mogen niet verdwijnen) |
| `tools/traces/bg_core.py`, `tools/traces/bg_kiel.py` | Handmatige traces in **native scanpixels** van akte 2006 p.81 |
| `tools/traces/bg_segments.py` + `tools/segment_bg.py` | Vaste zaadpunten en classificatie per vak; segmentatie uit de lokale scan → `data/inventory/bg_segments_p81.json` |
| `data/inventory/columns_review_p81.json` | Visuele controle van alle 269 kolomkandidaten op p.81 (247 symbool / 12 onzeker / 10 afgekeurd) |
| `data/inventory/calibration_p81.json` | Metingen aan schaalbalk en cm-liniaal + vergelijking met nominaal |
| `tools/build_model.py` | Bouwt `data/bg.v2.json` + `pilot/pilot_data.js` (inktsteun per zijde uit lokale scan, of hergebruik met `--scan none`) |
| `tools/detect_columns.py` | Kolomkandidaten (holle vierkanten) per blad → `data/inventory/columns_auto_all.json` |
| `tools/register_plan_jpg.py` | Registreert de al gepubliceerde `img/plan_*.jpg` op het native frame → `data/inventory/registration_plan_jpg.json` |
| `tools/build_tile_register.py` | Werkregister per tile (alle 5 bladen) → `data/inventory/tile_register.json` |
| `run_checks.sh` (geen privébron nodig; segmentatie en kolomreview worden hergebruikt) | Reproduceer-, validatie- en testcheck zonder privébron |
| `pilot/index.html` | Viewer: klikbare ruimtes/bouwdetails/zijden, popup met bronlabel vs huidig gebruik, relatieve coördinaten, afgeleide maten, buren, verbindingen, juridische lidmaatschappen |

## Kernregels
- Per bronblad één frame (`px_native`). Elke vertex heeft `x_px,y_px`, `x_rel,y_rel` en `floor_id`.
- Vaste ids; een gedeelde grens is precies één edge.
- Zijmaat: `source` | `derived` | `unknown`. Op het BG staan geen maten, dus alle lengtes zijn `derived`.
- **Kalibratie:** gebaseerd op de schaalbalk van het hoofdplan ('Begane grond, Schaal 1 a 200', 0–10 m = 387 px → 0,02584 m/px) en de cm-liniaal (78,47 px/cm → 0,02549 m/px bij 1:200).
  - We gebruiken het midden: 0,02566 m/px (≈ +1,0 % t.o.v. de oude nominale 0,0254).
  - Beide controles liggen langs native **y**. De **x-as is niet onafhankelijk gecontroleerd** (isotroop aangenomen).
  - Onzekerheid per zijde: ±0,7 % (y) / ±1,6 % (x), plus de afleestolerantie van beide eindpunten.
- Grenzen:
  - handmatige traces: hartlijn (bij een dubbele gevellijn de binnenlijn);
  - segmenten: de binnenzijde van de getekende lijn. Er ligt dus een wandstrook tussen buren en er zijn geen gedeelde zijden.
- `source_label_text` (bron) en `current_use` (nu, met bron) staan in aparte velden.
- Een `door` mag alleen als er een deurblad of draaicirkel getekend is. Een onderbroken lijn wordt `opening_candidate`.
- Juridisch:
  - De hoofdsplitsing omvat het hele complex: A-179 Winkels + A-180 Woningen.
  - De ondersplitsing (85 woningen + 91 bergingen) ligt **genest binnen A-180**; het is geen apart gebied ernaast.
  - Lidmaatschap per vak is `probable`/`uncertain` en afgeleid uit indexnummers (179: 5×, omcirkeld 180: 5×) en labels. Er zijn geen getekende splitsingsgrenzen.
  - Gearceerd = 'niet in de splitsing betrokken' (legenda).
  - A-2 (titelblok) vs A-180 (MVGM): **onopgelost**.
- `current_use` voor containerruimtes = fietsenberging, `user_confirmed`: de gebruiker heeft bevestigd dat alle containerruimtes zijn omgebouwd. Het bronlabel blijft `container-ruimte`.
- Privacy: native scan en uitsneden blijven lokaal (`model/pilot/local/`, git-ignored). Online staat alleen de eerder gepubliceerde `img/plan_bg.jpg` als overlay.
