# Datamodel v2 – brongetrouwe plattegrond (pilotfase)

Status: **pilot, onvolledig**. Dit staat los van de huidige kaart (`index.html`, `js/`, `svg/`) en verandert daar niets aan.

## Inhoud
| Pad | Wat |
|---|---|
| `schema/vve-plan-v2.schema.json` | JSON Schema (draft 2020-12) voor de structuur |
| `validate.py` | Validator (stdlib; gebruikt `jsonschema` extra als dat geïnstalleerd is): ids, referenties, x/y-rel-consistentie, ringen, zelfdoorsnijding, overlap, T-knopen, gedeelde edges, maatstatus, adjacency van verbindingen, juridische regels, dekking |
| `tests/test_validate.py` | 24 unittests (pilot geldig + negatieve gevallen) |
| `tools/pilot_trace_bg_core.py` | Handmatige trace in **native scanpixels** van akte 2006 p.81 (BG) |
| `tools/build_pilot.py` | Bouwt dataset + `pilot/pilot_data.js`; meet inktsteun per zijde op de lokale scan |
| `data/pilot-bg-core.v2.json` | Pilotdataset: één gemeenschappelijke kern BG |
| `pilot/index.html` | Losse detailviewer: klikbare objecten/zijden, popup met maatstatus, ondergrond aan/uit |

## Draaien
```bash
python3 model/validate.py model/data/pilot-bg-core.v2.json
python3 -m unittest discover -s model/tests
python3 model/tools/build_pilot.py --scan /pad/naar/page-81.png   # alleen lokaal, scan is privé
```

## Kernregels
- **Coördinaten**: per bronblad één frame (`px_native`, x rechts, y omlaag, scan-oriëntatie). Elke vertex heeft `x_px,y_px` én `x_rel,y_rel` (= px / bladmaat) en `floor_id`. Geen per-object coördinaten.
- **Stabiele ids** voor objecten, vertices en edges; een gedeelde grens is precies één edge die door beide ruimtes wordt gebruikt.
- **Maat per zijde**: `status` = `source` (bronmaat op tekening, met brontekst) | `derived` (berekend via kalibratie) | `unknown` (`length_m: null`). Huidige kalibratie is **nominaal** (1:200 @ 200 dpi ≈ 0,0254 m/px), scanvervorming ongetoetst ⇒ `uncertainty_m: null`, `uncertainty_status: "unknown"`. De validator weigert een onzekerheid bij nominale kalibratie.
- **Juridisch**: `legal_splits` + `memberships` (nullable/`unknown`). Het highlighten staat uit (`legal_split_ui.enabled=false`) zolang de bedoelde twee splitsingen en hun grenzen niet uit een bron zijn bewezen.
- **Privacy**: de native scan en uitsneden blijven lokaal (`model/pilot/local/` staat in `.gitignore`). De repo bevat alleen afgeleide geometrie.
- **Legacy**: `legacy_links` koppelt ids van de huidige kaart (`data/common.json`) als kandidaat aan nieuwe objecten; meldingen/GPS lopen via die ids.
