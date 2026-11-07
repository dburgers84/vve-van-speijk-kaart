# Datamodel v2 – brongetrouwe plattegrond (in opbouw)

Status: **onvolledig**. Alleen BG, twee gemeenschappelijke kernen en één bedrijfsruimte zijn overgetrokken. De huidige kaart (`index.html`, `js/`, `svg/`) blijft de referentie. Viewer: `model/pilot/`, online `/dev/model/pilot/`.

## Inhoud
| Pad | Wat |
|---|---|
| `schema/vve-plan-v2.schema.json` | JSON Schema (draft 2020-12) |
| `validate.py` | Validator (stdlib; gebruikt `jsonschema` als dat er is) |
| `tests/test_validate.py` | Unittests (dataset + negatieve gevallen) en `tests/fixtures/stable_ids_v0.1.json` (ids mogen niet verdwijnen) |
| `tools/traces/bg_core.py`, `tools/traces/bg_kiel.py` | Handmatige traces in **native scanpixels** van akte 2006 p.81 |
| `tools/build_model.py` | Bouwt `data/bg.v2.json` + `pilot/pilot_data.js` (inktsteun per zijde uit lokale scan, of hergebruik met `--scan none`) |
| `tools/detect_columns.py` | Kolomkandidaten (holle vierkanten) per blad → `data/inventory/columns_auto_all.json` |
| `tools/register_plan_jpg.py` | Registreert de al gepubliceerde `img/plan_*.jpg` op het native frame → `data/inventory/registration_plan_jpg.json` |
| `tools/build_tile_register.py` | Werkregister per tile (alle 5 bladen) → `data/inventory/tile_register.json` |
| `run_checks.sh` | Reproduceer-, validatie- en testcheck zonder privébron |
| `pilot/index.html` | Viewer: klikbare ruimtes/bouwdetails/zijden, popup met bronlabel vs huidig gebruik, relatieve coördinaten, afgeleide maten, buren, verbindingen, juridische lidmaatschappen |

## Kernregels
- Per bronblad één frame (`px_native`). Elke vertex heeft `x_px,y_px`, `x_rel,y_rel` en `floor_id`.
- Vaste ids; een gedeelde grens is precies één edge.
- Zijmaat: `source` | `derived` | `unknown`. De huidige kalibratie is nominaal (scanvervorming niet getoetst), dus `uncertainty_m` is altijd `null`. Het blad heeft wel een schaalbalk 0–10 m en een cm-liniaal; die zijn nog niet gemeten.
- `source_label_text` (bron) en `current_use` (nu, met bron) staan in aparte velden.
- Een `door` mag alleen als er een deurblad of draaicirkel getekend is. Een onderbroken lijn wordt `opening_candidate`.
- Juridisch: hoofdsplitsing (A-179 Winkels / A-180 Woningen) en ondersplitsing Woningen. Lidmaatschap per ruimte is `probable`/`uncertain` met bewijs; de grenzen zelf zijn niet als lijn getekend.
- Privacy: native scan en uitsneden blijven lokaal (`model/pilot/local/`, git-ignored). Online staat alleen de eerder gepubliceerde `img/plan_bg.jpg` als overlay.
