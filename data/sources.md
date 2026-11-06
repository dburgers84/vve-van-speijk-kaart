# Bronnen – kaart VvE Van Speijk (Suydersee Veste, Dronten)

Peildatum: **6 november 2026** (Europe/Amsterdam). Alle bestandspaden zijn relatief ten opzichte van `/workspace/`.

## Primair (eigen documenten)
| Bron | Gebruik | Status |
|---|---|---|
| `twinq_fin/docs/plattegronden/1050_104418631_Huisnummering_+_bergingen.pdf` (Excel-export 30-11-2021, 2 pag.) | Complete lijst: index oud/nieuw, bouwnr, adres, huisnr, etage, bergingsindex. **85 woningen**, 100% in `units.json` | gelukt |
| `twinq_fin/docs/plattegronden/1050_96739052_Splitsingsakte_+_tekeningen.pdf`, pag. 81–85 (W. Grandia BV, splitsingstekening 2006: BG, 1e, 2e, 3e, 4e verd./daken; 200 dpi) | Plaatsing: elk indexnummer (181–265) afgelezen op de tekening; contouren handmatig overgetrokken. Ook: bergingsblokken (266–356), liften/trappen/entrees (index 180 = gemeenschappelijk), "niet in de splitsing betrokken". Ondergrond `img/plan_*.jpg` | gelukt |
| `vve_analyse/wandeling_aldi_kiel/` (38 foto's + `log.json`, 06-11-2026) | Fotomarkers + looproute (positie **geschat**, geen GPS) | gelukt (0 van 38 met GPS) |
| `twinq/attachments/384979/IMG_8612.jpeg`, `twinq/attachments/350105/IMG_6071.JPG`, `IMG_6072.JPG` | GPS-EXIF-foto's (iPhone) → markers met nauwkeurigheidscirkel | gelukt (3 foto's) |
| Overige beelden gescand op EXIF/GPS (856 bestanden in /workspace + 9 in ~/Downloads) | 8 Twinq-foto's hebben GPS-velden, maar leeg (NaN); de rest heeft geen GPS | info |

## Openbare bronnen
| Bron | URL | Gebruik | Status |
|---|---|---|---|
| BAG WFS (Kadaster via PDOK), laag `bag:verblijfsobject` | https://service.pdok.nl/lv/bag/wfs/v2_0 | Per woning: verblijfsobject-id, oppervlakte (m²), bouwjaar, gebruiksdoel, status, pand-id, adrespunt (RD). Alle 85 adressen gevonden | gelukt |
| BAG WFS, laag `bag:pand` | idem | Pandcontouren (laag "BAG-pandcontouren") + georeferentie-controle | gelukt |
| PDOK Locatieserver v3.1 | https://api.pdok.nl/bzk/locatieserver/search/v3_1/free | Postcodes, nummeraanduiding-id, WGS84-coördinaten; controle straatnamen (BAG-naam is **"Schans"**, niet "De Schans") | gelukt |
| BAG-viewer (links per woning) | https://bagviewer.kadaster.nl/lvbag/bag-viewer/?objectId=… | Link in detailpaneel | link |
| Huispedia (per adres) | https://huispedia.nl/dronten/{postcode}/{straat}/{nr} | Energielabel (82 van 85 gevonden: 79×A, 2×B, 1×A+), woningtype. **Niet geverifieerd in EP-Online** | gelukt (85 pagina's opgehaald) |
| Huispedia / Seeki (Schans 169) | https://huispedia.nl/dronten/8254kr/schans/169 , https://seeki.eu/nl/nederland/flevoland/dronten/l--schans-169-3221496 | Complexnaam "Suydersee Veste", bouwjaar 2006, centrale entree met postvakken, lift, bergingen op 1e verdieping | gelukt |
| ALDI | https://www.aldi.nl/supermarkt/dronten/de-schans-51/3187698.html | Aldi = Schans 51, 8254 KN (BAG: 1294 m², pand 0303100000584907) | gelukt |
| openingstijden.nl / supermarktenoverzicht.nl | https://www.openingstijden.nl/Aldi/Dronten/Schans-51/ , https://supermarktenoverzicht.nl/dronten | Jumbo = De Binnenloop 10, Vomar = De Kajuit 1 (contextlabels BG) | gelukt |
| OpenStreetMap Overpass | overpass-api.de, overpass.kumi.systems | Gebouwcontouren | **mislukt** (geen verbinding vanaf de box); niet nodig: BAG-panden zijn de officiële contouren |
| Satelliet/luchtfoto | `vve_analyse/plan/sat.png` (bestaand), PDOK Luchtfoto WMTS als toekomstige laag | Niet gebruikt in de kaart (geen live tegels nodig) | n.v.t. |
| Funda / Google Maps | – | Niet gescraped; Google Maps alleen voor oriëntatie | n.v.t. |
| EP-Online (officiële energielabels) | https://www.ep-online.nl | Vereist API-sleutel; niet gebruikt | niet geprobeerd |

## Georeferentie (tekening ↔ RD/WGS84)
Gelijkvormigheidstransformatie (schaal, rotatie, spiegeling, verschuiving), robuust gefit op 85 BAG-adrespunten ↔ woningcentra op de tekening. Mediane afwijking ≈ 8 m: BAG-adrespunten liggen vaak bij het portiek in plaats van in de woning. Controle: BAG-pandcontouren vallen visueel binnen enkele meters op de tekening. Schaal ≈ 6,08 tekeningeenheden per meter. Gebruikt voor: GPS-fotomarkers, BAG-pandlaag, BAG-adrespunten en contextpunten (Aldi/Jumbo/Vomar).

## Aanvulling: De Rede
BAG heeft **De Rede 59–141 (oneven, 8254 KB)**: 42 woningen in dezelfde panden (o.a. 0303100000586451). Dat zijn er precies zoveel als het gat in de bouwnummers van de huisnummerlijst (bouwnr. 80–121). Ze staan **niet** in de huisnummering van VvE Van Speijk en zitten dus niet in `units.json`. Waarschijnlijk is dit een andere VvE of een ander deel van de Suydersee Veste; dat is niet nagegaan.

## Versie 2 (06-11-2026): SVG opnieuw opgebouwd
| Wat | Bron | Methode |
|---|---|---|
| Liften, trappen, entrees/hallen, meterkasten (GEM/flatkast/CVZ/E-kast/gaskasten/mk), hydrofoor, sprinklerruimte, LS/trafo, schachten | Splitsingstekening akte 2006 pag. 81–85 | Met de hand overgetrokken op een rooster van 10 eenheden (`build/crop.py`) → `build/features.py` |
| Fietsenbergingen | Tekening (label “containerruimte”) + opgave bewoner 06-11-2026 | Alle containerruimtes zijn omgebouwd tot fietsenberging; het tekeninglabel staat in `tekening_label` |
| 91 bergingvakjes | Tekening pag. 82 (nummers afgelezen) + huisnummerlijst (bergingsindex → woning) | Per rij gelijk verdeeld; volgorde zoals op de tekening |
| Daken 2e–4e | Tekening pag. 83–85 | Overgetrokken op het overzicht (±1–2 m) |
| Gebouwcontour | BG/1e: BAG-panden (complex); 2e–4e: unie van woningen/kernen/daken (shapely) | `build/build_v2.py` |
| Twinq-meldingen met foto’s | `/workspace/twinq/requests.json` + `twinq/attachments/<verzoek>/` | 24 meldingen / 41 foto’s opgenomen, 6 meldingen (interieur woning) en schermafbeeldingen niet; contactgegevens verwijderd; koppeling met de hand op basis van adres of omschrijving (`LINK` in `build/build_meldingen.py`) |
| GPS-foto’s | EXIF van 3 Twinq-foto’s | Ongewijzigd, standaard zichtbaar (bewoner bevestigt de posities) |

### Open punten v2
- **Hydrofoor bij portaal Schans 143/145 (naast de Aldi):** wandelfoto 04 toont een “deur hydrofoor in de fietsenstalling”. Op de tekening staan de hydrofoor en de sprinklerruimte alleen bij **portaal Schans 75-99 (oost)**. Bij de Aldi staat nu een *geschatte* hydrofoor-deur (`BG-198-HYD-W`). Graag ter plekke bevestigen.
- **Liften op 3e/4e** en de lift/trap van portaal De Kiel 49/61/63 op de 2e zijn *afgeleid* (doorgetrokken), niet afzonderlijk op de tekening gecontroleerd.
- **Bergingvakjes** zijn per rij gelijk verdeeld; de werkelijke maten kunnen afwijken. Bergingen 313 en een paar andere hebben geen eigenaar in de huisnummerlijst.
- **Daktuin- en dakpadzones** op de 1e zijn nog geschat (uit de vorige versie).
- **9 meldingen zonder vaste plek** (lift niet genoemd, “hal naar de lift”, gevel algemeen, enz.). Ze staan in het startpaneel.
- Trappen en liften van bedrijfsruimten (Aldi/winkels) zijn niet getekend.
- Wandelfoto’s: de positie blijft geschat (geen EXIF).

## Contour-correctie (06-11-2026, feedback preview)
| Wat | Detail |
|---|---|
| Probleem | Complexcontour (uit BAG-panden) stond ~1,8° gedraaid t.o.v. de handgetekende units/ruimtes; op 2e–4e ontbrak de complexcontour (alleen losse dak-/woningfragmenten). |
| Oplossing | BAG-ringen in `build/build_v2.py` roteren met **−1,76°** rond het zwaartepunt van de units (BG+1e) en verschuiven met **(+2, −6)** tekeningeenheden. Dezelfde complexvoetafdruk (tekening + gecorrigeerde BAG) wordt op **alle** verdiepingen (BG–4e) als contour getoond. Bronbestand `data/bag_panden_plan.json` blijft ongecorrigeerd; correctie gebeurt bij elke build. |
| Labels | Alle openbare/gemeenschappelijke ruimtes krijgen een zichtbaar label (o.a. galerij/gang/hal, HF, Spr., Lift, Trap, MK, Fietsen, Daktuin). |

## BG-uitlijning + tekening-control (06-11-2026)
| Wat | Detail |
|---|---|
| BG fijn-align | Alle BG-features en BG-unitpolygonen: **−0,25°** (met de klok mee) rond BG-zwaartepunt + verschuiving **(+1,0, +5,0)** tekeningeenheden (≈ **+0,7 / +3,3 px** bij schaal 1,5). Gemeten aan scanwanden portaal Oost/Aldi (feature-randen stonden ~3–6 eenheden te hoog). |
| BAG-contour | Licht bijgesteld naar **−1,85° / tx +1,5 / ty −5** (was −1,76° / +2 / −6). |
| UI | Duidelijke control **“Originele tekening”**: knop rechtsboven bij zoom + checkbox + dekkingsschuif linksonder (altijd zichtbaar, niet alleen in ingeklapte legenda). Per verdieping `img/plan_{bg,1e,2e,3e,4e}.jpg` (akte 2006 pag. 81–85). |
