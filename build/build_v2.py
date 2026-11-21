"""Bouwt js/data.js (window.VVE_DATA), data/common.json, data/plan.json, data/photos.json en svg/*.svg
uit data/units.json + build/features.py + BAG-panden. Vereist: shapely.  Gebruik: python3 build/build_v2.py"""
import json, os, sys, math, re
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
H=os.path.dirname(os.path.abspath(__file__)); R=os.path.join(H,'..'); sys.path.insert(0,H)
import features as FE
J=lambda p:json.load(open(os.path.join(R,p)))
U=J('data/units.json'); meta=U['meta']; units=U['units']
panden=J('data/bag_panden_plan.json'); photos=J('data/photos.json')
old=open(os.path.join(R,'js/data.js')).read()
oldD=json.loads(old[old.index('{'):old.rindex('}')+1])
context=oldD['context']
EPM=meta['georef']['eenheden_per_meter']
FN={0:'BG',1:'1e',2:'2e',3:'3e',4:'4e'}

TYPES=[  # volgorde = legenda
 ('woning-schans','Woning Schans','#2f7fd8'),('woning-kiel','Woning De Kiel','#e0812b'),
 ('lift','Lift','#8e44ad'),('trap','Trap / trappenhuis','#c39bd3'),('entree','Entree / hal','#e74c3c'),
 ('galerij','Galerij / gang / overloop','#f4d03f'),('looppad','Looppad / pad','#f7c948'),('meterkast','Meterkast / E-kast / gaskast','#2c3e50'),
 ('hydrofoor','Hydrofoor','#00a3a3'),('sprinkler','Sprinklerruimte','#48b5e0'),('technisch','Technisch (trafo/LS/schacht)','#95a5a6'),
 ('fietsenberging','Fietsenberging','#27ae60'),('berging','Berging (privé, 1e verd.)','#c8a165'),
 ('daktuin','Daktuin / dakpad','#6ab04c'),('dak','Dak (installatiezone)','#d5d8dc'),('niet-vve','Niet in de splitsing','#9e9e9e')]
TYPE_LABEL={t:l for t,l,_ in TYPES}

def poly(P): return Polygon(P).buffer(0)

# BG fijn-uitlijning t.o.v. splitsingstekening (akte 2006 pag. 81):
# gemeten aan portaal-Oost/Aldi: feature-randen stonden ~3–6 tekeningeenheden te hoog
# t.o.v. de scanwanden; lichte clockwise-rotatie (~0,25°) voor rest-scheefstand.
# Positieve shapely-rotatie = CCW → hier −0,25° (= 0,25° met de klok mee).
from shapely.affinity import rotate as shp_rotate, translate as shp_translate
_bg_pts=[pt for f in FE.F if f['floor']==0 for pt in f['poly']]
_bg_pivot=(sum(p[0] for p in _bg_pts)/len(_bg_pts), sum(p[1] for p in _bg_pts)/len(_bg_pts))
BG_ALIGN={'rot_deg':-0.30,'tx':1.2,'ty':4.5,'pivot':[round(_bg_pivot[0],2),round(_bg_pivot[1],2)],
          'note':'BG-features/units +1,2 x / +4,5 y tekeningeenheden (~0,8 / 3,0 px@1,5) en −0,30° (klok mee) t.o.v. scan pag. 81'}
def _bg_corr_pts(P):
    g=shp_translate(shp_rotate(Polygon(P), BG_ALIGN['rot_deg'], origin=_bg_pivot), BG_ALIGN['tx'], BG_ALIGN['ty'])
    return [[round(x,1),round(y,1)] for x,y in g.exterior.coords][:-1]
for f in FE.F:
    if f['floor']==0: f['poly']=_bg_corr_pts(f['poly'])
for u in units:
    if '0' in u['geometry']: u['geometry']['0']=_bg_corr_pts(u['geometry']['0'])
print('BG align', BG_ALIGN)

upoly={}
for u in units:
    for f,P in u['geometry'].items(): upoly[(u['id'],int(f))]=poly(P)

def nabij(geom,floor,maxd=14):
    c=[]
    for (uid,f),g in upoly.items():
        if f==floor or (floor==0 and f==1):
            d=g.distance(geom)
            if d<=maxd: c.append((d+(0 if f==floor else 5),uid))
    c.sort(); seen=[]
    for d,uid in c:
        if uid not in seen: seen.append(uid)
    return seen[:6]

feats=[]
for f in FE.F:
    g=poly(f['poly']); d=dict(f)
    d['kind']='common'; d['type_label']=TYPE_LABEL[f['type']]; d['floor_name']=FN[f['floor']]
    d['opp_m2']=round(g.area/EPM/EPM,1)
    if f['type'] not in ('daktuin','niet-vve'): d['nabij']=nabij(g,f['floor'])
    d.setdefault('bron','Splitsingstekening akte 2006 (W. Grandia BV), pag. %d; index 180 = gemeenschappelijk'%(81+f['floor']) if f['conf']!='geschat' else 'Geschat: wandeling 06-11-2026 / opgave bewoner')
    feats.append(d)

owner={u['berging']['index']:u['id'] for u in units}
berg=[]
for b in FE.BERG:
    d=dict(b,kind='berging',type='berging',name='Berging %d'%b['index'],conf='tekening',floor_name='1e',
           eigenaar=owner.get(b['index']),bron='Splitsingstekening akte 2006 pag. 82 + huisnummerlijst (bergingsindex)')
    d['opp_m2']=round(poly(b['poly']).area/EPM/EPM,1)
    berg.append(d)
missing=sorted(set(owner)-{b['index'] for b in berg}); print('bergingen zonder cel:',missing)
blokken=[]
for b in FE.BLOKKEN:
    cs=[poly(x['poly']) for x in berg if x['blok']==b['id']]
    hull=unary_union([c.buffer(.6) for c in cs]).envelope if cs else None
    blokken.append(dict(b,floor=1,poly=[list(map(lambda v:round(v,1),p)) for p in hull.exterior.coords][:-1]))

daken=[]
for fl,L in FE.DAK.items():
    for i,P in enumerate(L):
        daken.append(dict(id=f'{fl}-DAK-{i+1}',floor=fl,type='dak',kind='common',name='Dak (indicatieve installatiezone)',poly=P,conf='tekening',floor_name=FN[fl],
                          type_label=TYPE_LABEL['dak'],bron='Splitsingstekening akte 2006 pag. %d (overgetrokken, ±1 m)'%(81+fl)))

# ---- overlap-clip: daktuin/galerij/looppad/dak mogen niet over woningen/bergingen/solids liggen
SOLID={'lift','trap','entree','meterkast','hydrofoor','sprinkler','technisch','fietsenberging','niet-vve'}
CLIP={'daktuin','galerij','looppad','dak'}
def _rings_of(g):
    out=[]
    if g.is_empty: return out
    gs=list(g.geoms) if isinstance(g,MultiPolygon) else [g]
    for gg in gs:
        if gg.area<8: continue
        gg=gg.simplify(0.4)
        if gg.is_empty or gg.area<8: continue
        out.append([[round(x,1),round(y,1)] for x,y in gg.exterior.coords][:-1])
    return out
def _set_poly(d, rings):
    if not rings:
        d['poly']=[]; d['hidden']=True; return
    # keep largest ring as primary poly; extras as poly_extra (renderer uses poly)
    rings=sorted(rings, key=lambda r: Polygon(r).area, reverse=True)
    d['poly']=rings[0]
    if len(rings)>1: d['poly_extra']=rings[1:]
clipped=0
for fl in range(5):
    solids=[g for (uid,f),g in upoly.items() if f==fl]
    solids+=[poly(b['poly']) for b in berg if b.get('floor',1)==fl]
    solids+=[poly(f['poly']) for f in feats if f['floor']==fl and f['type'] in SOLID and f.get('poly')]
    if not solids: continue
    solid_u=unary_union([s.buffer(0.4,join_style=2) for s in solids if s and not s.is_empty])
    for f in feats+daken:
        if f['floor']!=fl or f['type'] not in CLIP or not f.get('poly'): continue
        g=poly(f['poly'])
        if not g or g.is_empty: continue
        # daktuin/dak also clip against looppad/galerij (pad heeft voorrang)
        extra=[]
        if f['type'] in ('daktuin','dak'):
            extra=[poly(x['poly']) for x in feats if x['floor']==fl and x['type'] in ('looppad','galerij') and x.get('poly')]
        cut=solid_u
        if extra: cut=unary_union([cut]+extra)
        ng=g.difference(cut)
        rings=_rings_of(ng)
        before=g.area; after=sum(Polygon(r).area for r in rings) if rings else 0
        if after+1<before: clipped+=1
        _set_poly(f, rings)
# drop fully clipped
feats[:]=[f for f in feats if f.get('poly')]
daken[:]=[d for d in daken if d.get('poly')]
print('overlap-clip: aangepaste vlakken', clipped, 'features', len(feats), 'daken', len(daken))

def rings(geom):
    out=[]
    gs=geom.geoms if isinstance(geom,MultiPolygon) else [geom]
    for g in gs:
        if g.area<30: continue
        g=g.simplify(0.8)
        out.append([[round(x,1),round(y,1)] for x,y in g.exterior.coords][:-1])
        for h in g.interiors:
            if Polygon(h).area>60: out.append([[round(x,1),round(y,1)] for x,y in h.coords][:-1])
    return out

# BAG-pandcontouren staan ~1,8° scheef t.o.v. de handgetekende units (georef-rest).
# Corrigeer met een kleine rotatie+verschuiving rond het zwaartepunt van de units,
# zodat contour en ingetekende delen uitlijnen. Zelfde correctie op panden[] voor de BAG-laag.
_units01=unary_union([g for (uid,f),g in upoly.items() if f in (0,1)])
_pivot=_units01.centroid
BAG_CORR={'rot_deg':-1.85,'tx':1.5,'ty':-5.0,'pivot':[round(_pivot.x,2),round(_pivot.y,2)],
          'note':'BAG-ringen ~1,8° gedraaid t.o.v. splitsingstekening; fijn-afgesteld voor BG (−1,85° / +1,5 / −5)'}
def _bag_corr(geom):
    return shp_translate(shp_rotate(geom, BAG_CORR['rot_deg'], origin=(_pivot.x,_pivot.y)), BAG_CORR['tx'], BAG_CORR['ty'])
for p in panden:
    p['rings']=[[[round(x,1),round(y,1)] for x,y in _bag_corr(poly(r)).exterior.coords][:-1] for r in p['rings']]
bag_complex=unary_union([poly(r) for p in panden if p.get('complex') for r in p['rings']])

# Complexvoetafdruk (BG+1e, tekening + gecorrigeerde BAG) – op ALLE verdiepingen tonen
# Daktuinen/looppaden (dakpaden) tellen niet mee: die mogen de gevelcontour niet uitsteken.
base_parts=[g for (uid,f),g in upoly.items() if f in (0,1)]
base_parts+=[poly(f['poly']) for f in FE.F if f['floor'] in (0,1) and f['type'] not in ('daktuin','looppad')]
base_parts+=[poly(b['poly']) for b in FE.BERG]
base_parts+=[bag_complex]
complex_foot=unary_union([p.buffer(2.5,join_style=2) for p in base_parts]).buffer(-1.5,join_style=2)

outlines={}
for fl in range(5):
    parts=[g for (uid,f),g in upoly.items() if f==fl]
    parts+=[poly(f['poly']) for f in FE.F if f['floor']==fl and f['type'] not in ('daktuin','looppad')]
    parts+=[poly(b['poly']) for b in FE.BERG if b['floor']==fl]
    parts+=[poly(d['poly']) for d in daken if d['floor']==fl]
    # complexvoetafdruk altijd meenemen (niet opnieuw bufferen); floor-delen licht bufferen
    extras=[p.buffer(2.5,join_style=2) for p in parts]
    m=unary_union(extras+[complex_foot]).buffer(-1.5,join_style=2) if extras else complex_foot
    # BAG/complex vult soms open dakzones; snijd daktuin/looppad uit de gevelcontour
    carve=[poly(f['poly']) for f in FE.F if f['floor']==fl and f['type'] in ('daktuin','looppad')]
    if carve:
        cut=unary_union([c.buffer(0.8,join_style=2) for c in carve])
        m=m.difference(cut)
    outlines[str(fl)]=rings(m)
meta.setdefault('georef',{})['bag_contour_correctie']=BAG_CORR
meta['georef']['bg_tekening_correctie']=BG_ALIGN
print('BAG contour correctie', BAG_CORR, 'outlines', {k:len(v) for k,v in outlines.items()})

# ---- GPS: Twinq-meldingsfoto's met EXIF-GPS blijven zichtbaar (opgave bewoner: posities kloppen)
MREF={'GPS_IMG_8612':'M384979','GPS_IMG_6071':'M350105','GPS_IMG_6072':'M350105'}
for p in photos:
    for k in ('gps_toelichting','gps_afstand_object_m'): p.pop(k,None)
    if p.get('gps'):
        p['gps_status']='GPS (Twinq-meldingsfoto)'; p['melding']=MREF.get(p['id'])
        p['positie']='GPS (EXIF) – bevestigd door bewoner'
    else:
        p['gps_status']='geen'; p['positie']='geschat (route-log)'
meldingen=J('data/meldingen.json')
ids={f['id'] for f in FE.F}|{b['id'] for b in FE.BLOKKEN}|{b['id'] for b in FE.BERG}; uids={u['id'] for u in units}
for m in meldingen:
    for x in m['features']+m['bergingen']: assert x in ids,(m['id'],x)
    for x in m['units']: assert x in uids,(m['id'],x)
    m['gps_fotos']=[p['id'] for p in photos if p.get('melding')==m['id']]
json.dump(photos,open(os.path.join(R,'data/photos.json'),'w'),ensure_ascii=False,indent=1)

meta['versie']='2.0 – SVG-plattegrond opnieuw opgebouwd (06-11-2026)'
meta['types']=[dict(id=t,label=l,kleur=c) for t,l,c in TYPES]
D=dict(meta=meta,meldingen=meldingen,units=units,features=feats+daken,bergingen=berg,blokken=blokken,outlines=outlines,context=context,photos=photos,panden=panden)
json.dump(feats,open(os.path.join(R,'data/common.json'),'w'),ensure_ascii=False,indent=1)
json.dump(dict(bergingen=berg,blokken=blokken,daken=daken,outlines=outlines),open(os.path.join(R,'data/plan.json'),'w'),ensure_ascii=False)
open(os.path.join(R,'js/data.js'),'w').write('/* gegenereerd door build/build_v2.py – niet met de hand wijzigen */\nwindow.VVE_DATA='+json.dumps(D,ensure_ascii=False,separators=(',',':'))+';\n')

# ---- statische SVG per verdieping (voor hergebruik buiten de app)
os.makedirs(os.path.join(R,'svg'),exist_ok=True)
col={t:c for t,_,c in TYPES}
def pts(P): return ' '.join('%s,%s'%(x,y) for x,y in P)
def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;')
for fl in range(5):
    vb=meta['viewbox']; o=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str,vb))}" font-family="Arial,sans-serif">',
       f'<title>VvE Van Speijk – {FN[fl]} (schematisch, akte 2006)</title><rect x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}" fill="#f7f7f4"/>']
    o.append('<path fill="#ffffff" stroke="#1d2330" stroke-width="2.2" fill-rule="evenodd" d="'+' '.join('M'+' L'.join('%s,%s'%(x,y) for x,y in r)+'Z' for r in outlines[str(fl)])+'"/>')
    SHORT={'lift':'Lift','trap':'Trap','entree':'Entree','meterkast':'MK','hydrofoor':'HF','sprinkler':'Spr.','technisch':'Techn.','fietsenberging':'Fietsen','galerij':'Galerij','daktuin':'Daktuin','niet-vve':'Niet VvE'}
    for d in daken+feats:
        if d['floor']!=fl: continue
        o.append(f'<polygon id="{d["id"]}" points="{pts(d["poly"])}" fill="{col[d["type"]]}" fill-opacity="0.55" stroke="#333" stroke-width="0.6"><title>{esc(d["name"])}</title></polygon>')
        if d['type']=='dak': continue
        t=SHORT.get(d['type'],'')
        if d['type']=='galerij':
            n=d['name'].lower(); t='Gang' if 'gang' in n else ('Pad' if 'pad' in n else ('Hal' if 'hal' in n or 'overloop' in n else 'Galerij'))
        if d['type']=='entree' and 'hal' in d['name'].lower(): t='Hal'
        if not t: continue
        g=Polygon(d['poly']).representative_point(); bb=Polygon(d['poly']).bounds
        w,h=bb[2]-bb[0],bb[3]-bb[1]; s=min(8,max(3.2,min(w,h)/2.8))
        o.append(f'<text x="{g.x:.1f}" y="{g.y:.1f}" font-size="{s:.1f}" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="#111" stroke="#fff" stroke-width="1.2" paint-order="stroke">{esc(t)}</text>')
    if fl==1:
        for b in berg: o.append(f'<polygon id="{b["id"]}" points="{pts(b["poly"])}" fill="{col["berging"]}" stroke="#6b4f2a" stroke-width="0.5"><title>{b["name"]}</title></polygon>')
    for u in units:
        P=u['geometry'].get(str(fl))
        if not P: continue
        c=col['woning-kiel' if u['straat']!='Schans' else 'woning-schans']; g=Polygon(P).representative_point()
        o.append(f'<polygon id="{u["id"]}" points="{pts(P)}" fill="{c}" fill-opacity="0.45" stroke="#1d2330" stroke-width="1"><title>{esc(u["adres"])}</title></polygon>')
        o.append(f'<text x="{g.x:.1f}" y="{g.y:.1f}" font-size="13" font-weight="700" text-anchor="middle" dominant-baseline="central">{("K" if u["straat"]!="Schans" else "")}{u["huisnr"]}</text>')
    o.append('</svg>')
    open(os.path.join(R,'svg',f'verdieping_{FN[fl]}.svg'),'w').write('\n'.join(o))
from collections import Counter
print('features',Counter((f['floor'],f['type']) for f in feats))
lifts=[f for f in feats if f['type']=='lift']; traps=[f for f in feats if f['type']=='trap']
print('LIFTEN verdiepingsvlakken', len(lifts), 'TRAPPEN verdiepingsvlakken', len(traps))
# unieke kokers bij benadering: portaal-groep
from collections import defaultdict
shafts=defaultdict(list)
for f in lifts:
    shafts[f.get('portaal') or f['id']].append(f'{FN[f["floor"]]}:{f["id"]}({f.get("conf","?")})')
print('LIFTEN unieke portalen/kokers', len(shafts))
for k,v in shafts.items(): print(' ', (k or '?')[:50], '->', ', '.join(v))

print('bergingen',len(berg),'daken',len(daken),{k:len(v) for k,v in outlines.items()})
print('meldingen',len(meldingen))
