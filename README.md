# Interactieve plattegrond – VvE Van Speijk (Suydersee Veste, Dronten)

**Live:** https://dburgers84.github.io/vve-van-speijk-kaart/ · **Preview (`dev`):** https://dburgers84.github.io/vve-van-speijk-kaart/dev/

Losse webapp (HTML + vanilla JavaScript + SVG). Geen build-stap, geen npm. Werkt ook via `file://`.

## Versie 2 – opnieuw opgebouwd als SVG
De plattegrond is **vanaf nul opgebouwd als schone SVG** (geen gescande tekening meer als basis). Alle vormen zijn met de hand overgetrokken van de splitsingstekening (akte 2006, pag. 81–85) op een rooster van 10 tekeningeenheden (≈ 1,6 m).
- **Gebouwcontour** per verdieping: BG en 1e = BAG-pandcontouren (plint), 2e–4e = samengevoegd uit woningen, kernen en daken.
- **85 woningen** met huisnummer (`173` = Schans, `K64` = De Kiel); maisonnettes gestippeld op elke etage die ze beslaan.
- **Gemeenschappelijk en technisch, elk als eigen type** met kleur, label en filter in de legenda:
  lift (met kruis), trap/trappenhuis, entree/hal, galerij/gang/overloop, **meterkast** (incl. GEM, flatkast, CVZ-kast, E-kast, gaskasten en de mk’s per woning), **hydrofoor**, **sprinklerruimte**, technisch (LS-ruimte/trafo/schacht), **fietsenberging**, daktuin/dakpad, dak (installatiezone), niet in de splitsing.
- **Fietsenbergingen:** op de tekening van 2006 heten deze ruimten “containerruimte”. Ze zijn allemaal omgebouwd tot fietsenberging en staan daarom zo op de kaart. In het detailpaneel staat: “voormalige containerruimte, nu fietsenberging”.
- **91 bergingen** (index 266–356) als losse vakjes op de 1e verdieping, elk gekoppeld aan de eigen woning.
- **Twinq-meldingen met foto’s** (24 meldingen, 41 foto’s) als oranje speld op het object. Klik op een melding, woning of ruimte en je ziet thumbnails; klik op een thumbnail voor de grote foto (lightbox, pijltjestoetsen).
- **GPS-foto’s** (3, uit Twinq-meldingen) met de cirkel voor de GPS-nauwkeurigheid en de kijkrichting. Ze staan standaard aan; de bewoner heeft bevestigd dat de posities kloppen.
- **Wandelfoto’s** (06-11-2026) met de route. De positie is **geschat** (±5–15 m), want de foto’s hebben geen GPS. Klik op een marker om de foto te zien.
- **Referentie:** de scan van de splitsingstekening staat standaard uit en is aan te zetten als ondergrond (met schuif voor de dekking), om de tekening te controleren.
- Lagen aan/uit, zoom (knoppen, muiswiel, pinch) en slepen, zoeken, deeplinks.

### Betrouwbaarheid per object
`op tekening` = staat zo op de splitsingstekening · `afgeleid` = doorgetrokken van een andere verdieping (bijv. lift op 3e/4e) · `geschat` = staat niet op de tekening (wandeling of opgave van een bewoner). Geschatte en afgeleide vormen hebben een stippelrand.

## Zoeken
`173`, `Kiel 64`, `k64`, `lift`, `hydrofoor`, `meterkast`, `fietsenberging`, `berging 308`, `melding 384979`, `lekkage`.

## Deeplinks
`#S173`, `#K64`, `#BRG-308` (berging), `#1-BRG-C` (blok), `#BG-OOST-HYD` (hydrofoor), `#M384979` (melding), `#GPS_IMG_6071`, `#08a_daktuin` (wandelfoto). Verdieping kiezen: `?verdieping=2`.

## Inbouwen in een website
**iframe:**
```html
<iframe src="https://dburgers84.github.io/vve-van-speijk-kaart/?verdieping=1#S173" style="width:100%;height:80vh;border:0" title="Plattegrond VvE"></iframe>
<script>
window.addEventListener('message', e => {
  if (e.data?.type === 'vve:select')  console.log('gekozen', e.data.id, e.data.kind);
  if (e.data?.type === 'vve:melding') openMeldformulier(e.data); // {id, kind, naam, adres, verdieping, portaal, type, link}
});
</script>
```
**Direct in de pagina:** kopieer `css/ js/ img/ photos/` en zet `<div id="vve-app" data-base="/vve-kaart/" data-floor="1"></div>` met `js/data.js` en `js/app.js` erbij.
JavaScript-API: `VVEKaart.select(id)`, `.setFloor(n)`, `.search(q)`, `.onMelding(fn)`, `.data`. De CustomEvents `vve:select` en `vve:melding` worden op `#vve-app` afgevuurd.
De knop **“Melding maken voor dit object”** stuurt `vve:melding` met adres, verdieping, portaal en een deeplink. Zonder koppeling worden die gegevens naar het klembord gekopieerd. De Twinq-koppeling zelf moet nog gebouwd worden.

## Bestanden
| Pad | Inhoud |
|---|---|
| `index.html`, `css/style.css`, `js/app.js` | De app (de SVG wordt per verdieping uit de data getekend) |
| `js/data.js` | Alle data ingebed (`window.VVE_DATA`), **gegenereerd** |
| `svg/verdieping_*.svg` | Statische SVG per verdieping (voor hergebruik/print), **gegenereerd** |
| `data/units.json` | 85 woningen + BAG/Huispedia + contour per etage |
| `data/common.json` | Gemeenschappelijke en technische ruimten (type, portaal, betrouwbaarheid, nabije woningen) |
| `data/plan.json` | Bergingen (91 vakjes), bergingenblokken, daken, gebouwcontouren |
| `data/meldingen.json` | Twinq-meldingen met foto’s en koppeling aan woning/ruimte/berging |
| `data/photos.json` | Wandelfoto’s (geschat) + GPS-foto’s |
| `img/meldingen/` (+ `t/` thumbnails) | Foto’s uit Twinq-meldingen, max. 1280 px, zonder EXIF |
| `photos/` | Wandelfoto’s en GPS-foto’s (max. 640 px, zonder EXIF) |
| `img/plan_*.jpg` | Referentiescan splitsingstekening (alleen voor de laag “Referentie”) |
| `build/` | `features.py` (alle overgetrokken ruimten), `build_meldingen.py`, `build_v2.py`, `crop.py` (rooster-uitsneden om over te trekken) |

## Opnieuw genereren
```bash
pip install shapely pillow
python3 build/build_meldingen.py   # alleen op de box met /workspace/twinq
python3 build/build_v2.py          # js/data.js, data/*.json, svg/*.svg
```
Een ruimte toevoegen of corrigeren: pas `build/features.py` aan. Coördinaten lees je af met `python3 build/crop.py 1e x0 y0 x1 y1 5` (uitsnede met rooster in tekeningeenheden).

## Privacy
- Meldingen: alleen onderwerp en omschrijving. Namen, telefoonnummers en e-mailadressen zijn eruit gehaald, en eigenaren staan er niet in.
- Meldingen over het **interieur van een privéwoning** (6 stuks) en schermafbeeldingen zijn niet opgenomen; zie `EXCL` in `build/build_meldingen.py`.
- Foto’s zijn opnieuw opgeslagen zonder EXIF. De GPS-positie staat alleen in `photos.json` bij de 3 GPS-foto’s.
- Dit is een **publieke** repository. Haal eerst foto’s weg als er iets niet online mag.

## Bekende beperkingen
Zie `data/sources.md` → “Open punten v2”.
