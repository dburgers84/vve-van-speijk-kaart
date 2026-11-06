"""Verzamelt Twinq-meldingen met foto's (technisch/gemeenschappelijk) -> img/meldingen/*.jpg (max 1280 px, zonder EXIF),
thumbnails img/meldingen/t/*.jpg (320 px) en data/meldingen.json. Kopieert ook de wandelfoto's naar photos/.
Privacy: contactgegevens (namen/telefoon/e-mail) worden uit de tekst gehaald; meldingen over het interieur van een
privéwoning en schermafbeeldingen worden NIET opgenomen (zie EXCL)."""
import json, os, re, shutil
from PIL import Image, ImageOps
H=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(H,'..')
TW='/workspace/twinq'; WALK='/workspace/vve_analyse/kaart_3verd/photos'
EXCL={'330426':'interieur woning','382452':'interieur woning','389157':'interieur woning','398424':'interieur woning',
      '374040':'schermafbeeldingen interieur woning','380889':'interieur woning'}
# koppeling melding -> objecten op de kaart (handmatig uit onderwerp/toelichting); conf: 'adres' = adres/ruimte staat in de melding,
# 'afgeleid' = ruimte afgeleid uit omschrijving, None = locatie onbekend
LINK={
 '331409':dict(features=[],note='Lift niet genoemd; welke lift is onbekend.'),
 '336642':dict(units=['K64','K66'],features=['2-GAL-K'],conf='adres'),
 '338725':dict(features=['BG-198-FIETS'],conf='afgeleid',note='"Algemene fietsenhok aan de Schans" (naast de Aldi, zie ook verzoek 328961).'),
 '345967':dict(features=['BG-198-ENT'],conf='adres'),
 '350105':dict(units=['S159'],features=['BG-NIET'],conf='adres'),
 '355378':dict(units=['K64','K66'],features=['2-225-LIFT'],conf='adres'),
 '355380':dict(units=['K64','K66'],features=['2-GAL-K'],conf='adres'),
 '370740':dict(features=[],note='"Entreedeur aan de Kiel-zijde": welk portaal is niet vermeld.'),
 '373842':dict(units=['K59'],conf='adres'),
 '376467':dict(features=[],note='"Hal naar de lift": portaal niet vermeld.'),
 '376722':dict(features=['1-BRG-D'],units=['S121','S123','S125','S127','S129'],conf='afgeleid',note='Schuurtjes Schans 121-129 = bergingenblok 315-329 (1e verd.).'),
 '376723':dict(features=[],note='Gevel Schans oneven nummers (algemeen).'),
 '379378':dict(features=[]),
 '379492':dict(features=[],note='Balkon/woning niet vermeld.'),
 '379622':dict(features=[],note='Bergruimte BG naast "de Moellies"; niet op de tekening gevonden.'),
 '381810':dict(units=['S163'],features=['2-200-TRAP','2-200-LIFT'],conf='afgeleid',note='"Hal waar trap en lift zitten, bij nummer 163".'),
 '384107':dict(units=['S79'],bergingen=['BRG-342'],conf='adres'),
 '384979':dict(units=['S117','S119'],conf='adres'),
 '389161':dict(features=['BG-198-ENT','BG-198-HAL1'],conf='afgeleid',note='"Hoofdingang": aangenomen Schans naast de Aldi.'),
 '389162':dict(features=[],note='Welke lift is niet vermeld.'),
 '392912':dict(features=['BG-198-HAL2'],conf='afgeleid',note='"Centrale hal, Schans, BG, voor de lift": aangenomen portaal naast de Aldi.'),
 '392913':dict(features=['3-246-LIFT'],conf='afgeleid',note='"Toegangsdeur lift 3e verdieping, Schans": enige Schans-lift op de 3e in de tekening.'),
 '396038':dict(features=[],note='IJzeren noodtrap De Kiel (straat Het Diep); staat niet als VvE-ruimte op de tekening.'),
 '402058':dict(features=['BG-198-ENT'],conf='adres'),
}
def clean(s):
    s=re.sub(r'(?i)contact\s*:.*$','',s or '',flags=re.S)
    s=re.sub(r'(?i)(monteur|behandelaar)\s*:\s*[^\n]*','',s)
    s=re.sub(r'\b0\d[\d\s-]{7,}\b','[tel. verwijderd]',s); s=re.sub(r'\S+@\S+','[e-mail verwijderd]',s)
    s=re.sub(r'(?i)bonnummer huurder:\s*\d+','',s)
    s=re.sub(r'\s+',' ',s).strip()
    return s[:400]+('…' if len(s)>400 else '')
def onderw(det,L):
    raw=det.get('Onderwerp') or L.get('Onderwerp') or ''; o=clean(raw)
    if len(raw)==40 and not o.endswith(('.','!','?')):
        t=clean(det.get('Toelichting')); o=(t.split('. ')[0])[:90]
    return o
req={x['verzoeknummer']:x for x in json.load(open(f'{TW}/requests.json'))}
od=os.path.join(R,'img/meldingen'); os.makedirs(od+'/t',exist_ok=True)
out=[]; skipped=[]
for d in sorted(os.listdir(f'{TW}/attachments')):
    fs=[f for f in sorted(os.listdir(f'{TW}/attachments/{d}')) if f.lower().endswith(('.jpg','.jpeg','.png'))]
    if not fs: continue
    if d in EXCL: skipped.append((d,EXCL[d],len(fs))); continue
    x=req[d]; det=x.get('detail',{}); L=x.get('list',{})
    fotos=[]
    for i,f in enumerate(fs):
        if 'Scherm' in f: continue
        im=ImageOps.exif_transpose(Image.open(f'{TW}/attachments/{d}/{f}')).convert('RGB')
        name=f'{d}_{i+1}.jpg'
        a=im.copy(); a.thumbnail((1280,1280)); a.save(f'{od}/{name}',quality=78,optimize=True)   # geen EXIF meegeschreven
        t=im.copy(); t.thumbnail((320,320)); t.save(f'{od}/t/{name}',quality=72,optimize=True)
        fotos.append(dict(src=f'img/meldingen/{name}',thumb=f'img/meldingen/t/{name}',orig=f'twinq/attachments/{d}/{f}'))
    lk=LINK.get(d,{})
    out.append(dict(id=f'M{d}',verzoek=d,datum=det.get('Datum') or L.get('Datum'),onderwerp=onderw(det,L),
        omschrijving=clean(det.get('Toelichting')),type=L.get('Type'),status=L.get('Status') or det.get('Status'),
        opdracht=re.sub(r'^\S+\s+','',L.get('Opdracht') or '').strip() or None,
        units=lk.get('units',[]),features=lk.get('features',[]),bergingen=lk.get('bergingen',[]),
        locatie=lk.get('conf'),locatie_toelichting=lk.get('note'),fotos=fotos,bron=f'Twinq verzoek {d} (MVGM-portaal)'))
json.dump(out,open(os.path.join(R,'data/meldingen.json'),'w'),ensure_ascii=False,indent=1)
pd=os.path.join(R,'photos'); os.makedirs(pd,exist_ok=True)
for f in os.listdir(WALK):
    im=Image.open(f'{WALK}/{f}').convert('RGB'); im.save(f'{pd}/{f}',quality=80,optimize=True)  # opnieuw opgeslagen zonder EXIF
print(len(out),'meldingen,',sum(len(m['fotos']) for m in out),'foto\'s; overgeslagen:',skipped)
print('zonder locatie:',[m['verzoek'] for m in out if not (m['units'] or m['features'] or m['bergingen'])])
