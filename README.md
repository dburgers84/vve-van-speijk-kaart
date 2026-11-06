# Interactieve verdiepingenkaart – VvE Van Speijk (Suydersee Veste, Dronten)

Losse webapp (HTML + vanilla JavaScript + SVG). Geen build-stap, geen npm, geen internet nodig.

## Openen
- Dubbelklik `index.html` (werkt via `file://` in Chrome, Edge, Firefox en Safari), of
- start een lokale server: `cd kaart_3verd && python3 -m http.server 8000` → http://localhost:8000/

## Functies
- Tabs **BG / 1e / 2e / 3e / 4e**, met per tab het aantal woningen. Maisonnettes (2e+3e en 3e+4e) staan op **elke** verdieping die ze beslaan, met een gestippelde rand en het label "2e+3e".
- Elke woning toont haar huisnummer op de plattegrond. De Kiel staat er als `K64`, Schans als `173`. Kleur: blauw = Schans, oranje = De Kiel.
- Klikken of tikken opent het detailpaneel: straat, huisnummer, postcode, etage(s), index nieuw/oud, bouwnummer, berging (met knop "toon"), BAG-oppervlakte, bouwjaar, gebruiksdoel, BAG-id met link, energielabel (Huispedia), opmerkingen en bronnen.
- Zoeken op huisnummer (`173`, `Kiel 64`, `k64`, `schans 101`), op indexnummer (`225`), op berging (`berging 308`) of op het naam van een ruimte (`lift`, `daktuin`).
- In- en uitzoomen met de knoppen + / − / ⤢, met het muiswiel of met een pinch op touch. Slepen verschuift de kaart.
- Lagen aan/uit: ondergrond (splitsingstekening), gemeenschappelijke ruimten, foto's, looproute, BAG-pandcontouren, BAG-adrespunten.
- Foto's: rode rondjes zijn wandelfoto's met een **geschatte** positie (geen GPS). Blauwe punten zijn GPS-foto's; de cirkel toont de GPS-nauwkeurigheid en het streepje de kijkrichting.
- Deeplink: `index.html#K64`, `#S173`, `#1-BRG-C` (bergingsblok), `#GPS_IMG_6071`.

## Inbouwen in een website
**A. iframe (eenvoudigst)**: kopieer de map naar de webserver en zet in de pagina:
```html
<iframe src="/vve-kaart/index.html#S173" style="width:100%;height:80vh;border:0" title="Plattegrond VvE"></iframe>
```
Bij een klik stuurt de kaart `postMessage({type:'vve:select', id, kind})` naar de bovenliggende pagina, bijvoorbeeld om een meldingsformulier te openen:
```js
window.addEventListener('message', e => { if (e.data && e.data.type === 'vve:select') console.log(e.data.id); });
```
**B. Direct in een pagina**: kopieer `css/`, `js/`, `img/`, `photos/` en zet in de pagina:
```html
<link rel="stylesheet" href="/vve-kaart/css/style.css">
<div id="vve-app" data-base="/vve-kaart/" data-floor="1" style="height:80vh"></div>
<script src="/vve-kaart/js/data.js"></script>
<script src="/vve-kaart/js/app.js"></script>
```
JavaScript-API: `VVEKaart.select('K64')`, `VVEKaart.setFloor(2)`, `VVEKaart.search('schans 1')`, `VVEKaart.data`. Het event `vve:select` (CustomEvent) wordt op `#vve-app` afgevuurd.

## Bestanden
| Pad | Inhoud |
|---|---|
| `index.html`, `css/style.css`, `js/app.js` | De app |
| `js/data.js` | Alle data ingebed (`window.VVE_DATA`), zodat het ook via `file://` werkt |
| `data/units.json` | 85 woningen + meta (georeferentie, verdiepingen). Dezelfde data als in data.js |
| `data/common.json` | Gemeenschappelijke ruimten (entrees, liften, bergingsblokken, daktuin, galerijen) + context (Aldi, Jumbo, Vomar) |
| `data/photos.json` | 41 fotomarkers (38 wandelfoto's + 3 GPS-foto's) |
| `data/bag_panden_plan.json` | BAG-pandcontouren omgerekend naar tekeningcoördinaten |
| `data/sources.md` | Alle bronnen, wat gelukt en mislukt is, en de herkomst van de data |
| `img/plan_*.jpg` | Ondergrond per verdieping (splitsingstekening akte 2006, pag. 81–85) |
| `photos/` | Verkleinde foto's (max. 640 px) |
| `build/` | Python-scripts + ruwe downloads (`raw/`) om de data opnieuw te genereren |

### Datamodel (`units.json` → `units[]`)
`id` (`S173`/`K64`), `straat`, `huisnr`, `postcode`, `index_nieuw`, `index_oud`, `bouwnr`, `etage_akte`, `etages` (["2e","3e"]), `floors` ([2,3]), `meerlaags`, `berging{index,etage,blok}`, `bag{verblijfsobject_id, nummeraanduiding_id, oppervlakte_m2, bouwjaar, gebruiksdoel, status, pand_id, rd, wgs84, url}`, `openbaar{energielabel, soort_huispedia, url}`, `geometry{"1":[[x,y],…]}` (tekeningcoördinaten, viewBox 30 0 1300 1132), `placement` (`confirmed`), `notes[]`, `bronnen[]`.

## Betrouwbaarheid
- **Woningposities: confirmed**. Elk indexnummer staat op de splitsingstekening; de contouren zijn met de hand overgetrokken (±1–3 m). Geen enkele woning is gegokt.
- **Gemeenschappelijke ruimten**: entrees, liften en bergingsblokken staan op de tekening (`confirmed`). De daktuin- en dakpadzones en één lift op de 2e zijn **geschat**.
- **Wandelfoto's**: positie geschat uit de route-log, ±5–15 m. De foto's hebben geen EXIF/GPS.
- **GPS-foto's**: EXIF-positie met een opgegeven fout van ±4,7 m tot ±15 m. Ze zijn op straatniveau genomen, dus de verdieping is onbekend (ze staan op BG en 1e).
- **BAG-bouwjaar** 1963/1991 bij De Kiel 46–84 en 49/61/63 is het bouwjaar van het hele pand met winkels; zie de opmerking per woning.
- **Energielabel** komt van Huispedia en is niet gecontroleerd in EP-Online.
- De tekening is schematisch en niet op schaal te gebruiken.

## Privacy bij online zetten
De map `photos/` bevat foto's van de wandeling en uit Twinq-meldingen. Bekijk of verwijder ze voordat de kaart publiek online gaat (zet dan de laag "Foto's" uit, of haal de foto-items uit `js/data.js`). Er staan geen namen van bewoners in de data.

## Later uitbreiden
- **Lichtpunten/armaturen**: `vve_analyse/lichtpunten.json` en `wandeling_aldi_kiel/armaturen.json` kunnen als extra laag (tekeningcoördinaten) toegevoegd worden, met dezelfde aanpak als de foto's.
- **Live kaartlagen**: zet BAG/WFS of PDOK-luchtfoto (WMTS) om via `meta.georef.transform` (RD → tekening).
- **Melding vanuit een object**: gebruik het `vve:select`-event of de postMessage om een (Twinq-)meldingsformulier voor te vullen met adres en object-id.
- Opnieuw genereren: `cd build && python3 fit2.py && python3 build_data.py`. Daarvoor moeten de paginabeelden in `/tmp/big-00{0..4}r.png` staan, gemaakt met `pdfimages -f 81 -l 85 -j` uit de splitsingsakte en 90° gedraaid; zie `build/grid.py`.
