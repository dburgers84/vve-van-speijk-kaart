"""Handmatig overgetrokken gemeenschappelijke ruimten, technische ruimten, bergingen en daken.
Coördinaten: tekeningeenheden (viewBox 30 0 1300 1132; ca. 6,08 eenheden per meter), afgelezen op de
splitsingstekening (akte 2006, pag. 81-85) met een rooster van 10 eenheden (zie build/crop.py).
conf: 'tekening' = staat zo op de tekening; 'afgeleid' = doorgetrokken van een andere verdieping;
'geschat' = niet op tekening, positie geschat (wandeling/bewoner)."""

def R(x0,y0,x1,y1): return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
def V(pts):  # coördinaten afgelezen op 1024-px overzicht -> tekeningeenheden
    return [[round(x*1.2695+30,1),round(y*1.2695,1)] for x,y in pts]
def VR(x0,y0,x1,y1): return V([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])

FIETS_NOTE='Voormalige containerruimte (zo genoemd op de splitsingstekening 2006), nu in gebruik als fietsenberging (opgave bewoner, 06-11-2026).'
F=[]
def add(id,floor,type,name,poly,portaal=None,conf='tekening',info=None,**kw):
    d=dict(id=id,floor=floor,type=type,name=name,poly=poly,conf=conf)
    if portaal: d['portaal']=portaal
    if info: d['info']=info
    d.update(kw); F.append(d)

# ------------------------------------------------------------------ BG
P='Portaal De Kiel 49/61/63'
add('BG-K49-MK',0,'meterkast','Meterkast (flatkast, KPN/UPC)',R(101,22,107,31),P)
add('BG-K49-ENT',0,'entree','Entree',R(107,22,128,32),P)
add('BG-K49-LIFT',0,'lift','Lift',R(106,32,122,44),P)
add('BG-K49-TRAP',0,'trap','Trappenhuis',R(106,44,128,75),P)
add('BG-K49-FIETS',0,'fietsenberging','Fietsenberging',R(104,78,130,98),P,info=FIETS_NOTE,tekening_label='containerruimte')

P='Portaal Het Havenplein (De Kiel 64-84 / Schans 177-179)'
add('BG-215-ENT',0,'entree','Entree',[[296,525],[320,525],[320,548],[304,548]],P)
add('BG-215-TRAP',0,'trap','Trap',R(320,525,338,548),P)
add('BG-215-LIFT',0,'lift','Lift',R(320,550,338,560),P)
add('BG-215-MK',0,'meterkast','Meterkasten (GEM gemeenschappelijk, flatkast, CVZ-kast; KPN/UPC/water)',R(320,562,340,573),P)

P='Portaal De Kiel 46-62 (noord)'
add('BG-208-FIETS',0,'fietsenberging','Fietsenberging',R(414,403,450,430),P,info=FIETS_NOTE,tekening_label='containerruimte')
add('BG-208-TRAP',0,'trap','Trap',R(452,382,460,428),P)
add('BG-208-TECH',0,'technisch','LS-ruimte + trafo (netbeheerder)',R(414,383,450,400),P,info='Laagspanning- en trafo-ruimte; waarschijnlijk van de netbeheerder, niet van de VvE.')

P='Portaal Schans 143/145 (naast Aldi)'
add('BG-198-HAL1',0,'entree','Hal',R(386,1017,410,1040),P)
add('BG-198-TRAP',0,'trap','Trap naar 1e / daktuin',R(386,1040,410,1070),P)
add('BG-198-ENT',0,'entree','Entree (hoofddeur naast Aldi, brievenbussen)',R(388,1070,410,1083),P)
add('BG-198-FIETS',0,'fietsenberging','Fietsenberging',R(410,1017,430,1040),P,info=FIETS_NOTE,tekening_label='containerruimte')
add('BG-198-LIFT',0,'lift','Lift',R(411,1040,422,1058),P)
add('BG-198-HAL2',0,'entree','Hal bij lift',R(410,1058,430,1083),P)
add('BG-198-MK',0,'meterkast','Flatkast (KPN & UPC)',R(392,1083,404,1091),P,info='Op de tekening aangeduid onder de entree; exacte plek te bevestigen.')
add('BG-198-HYD-W',0,'hydrofoor','Hydrofoor-deur (gezien op wandeling)',R(464,1055,476,1067),P,conf='geschat',
    info='Grijze dubbele deur met ventilatieroosters, gefotografeerd in de fietsenstalling (wandelfoto 04). Staat niet op de splitsingstekening bij dit portaal; positie geschat. Te bevestigen.')

P='Portaal Schans 75-99 (oost)'
add('BG-OOST-MK1',0,'meterkast','Meterkasten (flatkast + CVZ-kast)',R(766,1013,790,1046),P)
add('BG-OOST-MK2',0,'meterkast','Gemeenschappelijke meterkast (GEM; KPN/UPC/EV)',R(790,1013,800,1036),P)
add('BG-OOST-LIFT',0,'lift','Lift',R(801,1013,811,1034),P)
add('BG-OOST-TRAP1',0,'trap','Trappenhuis',R(812,1001,834,1036),P)
add('BG-OOST-TRAP2',0,'trap','Trap',R(766,1046,790,1068),P)
add('BG-OOST-ENT',0,'entree','Entree',R(766,1068,790,1082),P)
add('BG-OOST-HAL',0,'entree','Hal',R(790,1036,812,1082),P)
add('BG-OOST-FIETS',0,'fietsenberging','Fietsenberging',[[812,1036],[836,1036],[836,1065],[848,1065],[848,1076],[812,1076]],P,info=FIETS_NOTE,tekening_label='containerruimte')
add('BG-OOST-SPR',0,'sprinkler','Sprinklerruimte',R(836,1038,860,1052),P)
add('BG-OOST-HYD',0,'hydrofoor','Hydrofoor',R(848,1052,860,1060),P)
add('BG-OOST-EK',0,'meterkast','E-kast',R(848,1060,860,1068),P)
add('BG-OOST-GAS',0,'meterkast','Gaskasten',R(836,1076,858,1082),P)
add('BG-OOST-TECH',0,'technisch','LS-ruimte + trafo (netbeheerder)',R(843,1006,860,1038),P,info='Laagspanning- en trafo-ruimte; waarschijnlijk van de netbeheerder, niet van de VvE.')

add('BG-NIET',0,'niet-vve','Niet in de splitsing betrokken (gearceerd op tekening)',R(216,805,380,1069),conf='tekening')

# ------------------------------------------------------------------ 1e
P='Portaal De Kiel 49/61/63'
add('1-K49-LIFT',1,'lift','Lift',R(112,34,128,46),P)
add('1-K49-MK',1,'meterkast','Meterkast',R(128,34,136,46),P)
add('1-K49-TRAP',1,'trap','Trappenhuis',R(110,47,128,75),P)
P='Portaal Het Havenplein (De Kiel 64-84 / Schans 177-179)'
add('1-215-LIFT',1,'lift','Lift',R(318,553,335,570),P)
add('1-215-HAL',1,'galerij','Hal / overloop',R(300,550,318,570),P)
add('1-215-TRAP',1,'trap','Trap',R(337,536,372,550),P)
P='Trappenhuis Schans 147-153'
add('1-190-LIFT',1,'lift','Lift',R(367,805,380,818),P)
add('1-190-HAL',1,'galerij','Hal',R(367,818,380,865),P)
add('1-190-TRAP',1,'trap','Trap',R(380,795,392,865),P)
for i,(a,b) in enumerate([(361,804),(361,826),(392,803),(392,826)]):
    add(f'1-190-MK{i+1}',1,'meterkast','Meterkast woning (mk)',R(a,b,a+6,b+5),P)
P='Portaal Schans 143/145 (naast Aldi)'
add('1-198-TRAP1',1,'trap','Trappenhuis naar 2e',R(398,1005,424,1050),P)
add('1-198-TRAP2',1,'trap','Trap vanaf entree (BG)',R(380,1050,398,1062),P)
add('1-198-LIFT',1,'lift','Lift',R(400,1052,412,1070),P)
add('1-198-MK1',1,'meterkast','Meterkast woning (mk)',R(424,1012,430,1018),P)
add('1-198-MK2',1,'meterkast','Meterkast woning (mk)',R(424,1040,430,1046),P)
P='Portaal Schans 75-99 (oost)'
add('1-OOST-LIFT',1,'lift','Lift',R(790,1032,803,1052),P)
add('1-OOST-SCH',1,'technisch','Schacht / vide',R(780,1032,790,1052),P)
add('1-OOST-TRAP1',1,'trap','Trappenhuis',R(805,1030,822,1052),P)
add('1-OOST-TRAP2',1,'trap','Trap vanaf entree (BG)',R(760,1040,778,1080),P)
P='Hal Schans 173/175'
add('1-182-TRAP',1,'trap','Trap naar daktuin',R(245,704,268,717),P)
add('1-182-MK1',1,'meterkast','Meterkast woning (mk)',R(249,687,254,694),P)
add('1-182-MK2',1,'meterkast','Meterkast woning (mk)',R(249,733,254,740),P)
P='Trappenhuis Schans 139/141 (hoek, diagonaal)'
add('1-260-LIFT',1,'lift','Lift',[[1188,1008],[1201,995],[1209,1003],[1196,1016]],P)  # X-schacht op tekening
add('1-260-TRAP',1,'trap','Trappenhuis',[[1198,1020],[1216,1002],[1226,1012],[1208,1030]],P)
add('1-260-MK1',1,'meterkast','Meterkast woning (mk)',[[1219,1001],[1224,996],[1229,1001],[1224,1006]],P)
add('1-260-MK2',1,'meterkast','Meterkast woning (mk)',[[1195,1031],[1200,1026],[1205,1031],[1200,1036]],P)
# Daktuinen/dak + looppaden (1e): op tekening als "dak" / "pad"; polygonen zo dat ze woningen niet bedekken
# (build_v2.py clipt bovendien tegen woningen/bergingen/solids).
add('1-PAD-W',1,'looppad','Pad langs De Kiel 51-59 (west)',[[118,389],[132,389],[172,630],[155,630]],conf='tekening')
add('1-DAK-W',1,'daktuin','Dak west (langs De Kiel 51-59)',R(55,389,118,630),conf='tekening')
add('1-PAD-M',1,'looppad','Pad tussen daken (midden, bij Schans 143-171)',R(350,900,370,960),conf='tekening')
add('1-PAD-M2',1,'looppad','Pad langs dak (midden, zuid)',R(300,960,520,975),conf='tekening')
add('1-DAK-M',1,'daktuin','Dak / daktuin midden (tussen Schans en De Kiel)',R(300,870,520,960),conf='tekening')
add('1-DAK-N',1,'daktuin','Dak / dakpad (noord, bij De Kiel 46-50)',R(395,440,560,545),conf='tekening')
add('1-GANG-C',1,'looppad','Gang bergingen 296-314',R(570,457,690,466))
add('1-GANG-D',1,'looppad','Gang bergingen 315-329',R(671,882,752,893))
add('1-GANG-E',1,'looppad','Gang bergingen 330-356',R(944,883,1080,891))
add('1-GANG-B',1,'looppad','Gang bergingen 266-275',R(257,883,263,970))
add('1-PAD-A',1,'looppad','Pad langs bergingen 276-295',R(114,96,124,362))  # was galerij; expliciet looppad

# ------------------------------------------------------------------ 2e
P='Portaal De Kiel 49/61/63'
add('2-K61-HAL',2,'galerij','Overloop',R(100,12,130,32),P)
add('2-K61-MK',2,'meterkast','Meterkast',R(120,25,127,30),P)
add('2-K61-LIFT',2,'lift','Lift',R(106,33,122,45),P)  # op tekening 2e: label lift-mk
add('2-K61-TRAP',2,'trap','Trappenhuis',R(106,45,125,78),P)  # op tekening 2e: label trap
P='Portaal Het Havenplein (De Kiel 64-84 / Schans 177-179)'
add('2-225-LIFT',2,'lift','Lift',R(318,550,338,565),P)
add('2-225-TRAP',2,'trap','Trap / vide bij lift',R(338,550,355,575),P)
P='Trap Schans 177/179'
add('2-183-TRAP',2,'trap','Trap',R(250,700,270,715),P)
add('2-183-MK1',2,'meterkast','Meterkast woning (mk)',R(241,683,247,690),P)
add('2-183-MK2',2,'meterkast','Meterkast woning (mk)',R(241,727,247,735),P)
P='Trappenhuis Schans 165-171'
add('2-194-LIFT',2,'lift','Lift',R(373,798,385,812),P)
add('2-194-TRAP',2,'trap','Trap',R(380,815,392,855),P)
add('2-194-MK1',2,'meterkast','Meterkast woning (mk)',R(360,795,367,800),P)
add('2-194-MK2',2,'meterkast','Meterkast woning (mk)',R(360,818,367,823),P)
P='Portaal Schans 143/145 (naast Aldi)'
add('2-200-TRAP',2,'trap','Trappenhuis',R(408,998,434,1043),P)
add('2-200-LIFT',2,'lift','Lift',R(408,1045,422,1062),P)
add('2-200-MK1',2,'meterkast','Meterkast woning (mk)',R(432,1003,438,1008),P)
add('2-200-MK2',2,'meterkast','Meterkast woning (mk)',R(432,1036,438,1041),P)
P='Portaal Schans 75-99 (oost)'
add('2-244-LIFT',2,'lift','Lift',R(800,1015,810,1038),P)
add('2-244-SCH',2,'technisch','Schacht',R(793,1018,800,1040),P)
add('2-244-MK',2,'meterkast','Meterkast (mk)',R(795,1009,802,1015),P)
add('2-244-TRAP',2,'trap','Trappenhuis',R(812,1004,830,1040),P)
P='Trappenhuis Schans 139/141 (hoek, diagonaal)'
add('2-262-LIFT',2,'lift','Lift',[[1198,982],[1211,969],[1219,977],[1206,990]],P)  # X-schacht op tekening
add('2-262-TRAP',2,'trap','Trappenhuis',[[1208,994],[1226,976],[1236,986],[1218,1004]],P)
add('2-262-MK1',2,'meterkast','Meterkast woning (mk)',[[1230,979],[1235,974],[1240,979],[1235,984]],P)
add('2-262-MK2',2,'meterkast','Meterkast woning (mk)',[[1204,1006],[1209,1001],[1214,1006],[1209,1011]],P)
add('2-GAL-K',2,'galerij','Galerij De Kiel 64-84 (2e+3e)',R(299,540,618,548))
add('2-GAL-S',2,'galerij','Galerij Schans 115-129',R(620,760,630,952))
add('2-GAL-O',2,'galerij','Galerij Schans 97-113 / 131-137',R(550,995,1160,1003))

# ------------------------------------------------------------------ 3e
add('3-225-LIFT',3,'lift','Lift',R(318,550,338,565),'Portaal Het Havenplein (De Kiel 64-84 / Schans 177-179)')  # schacht met X op tekening 3e
P='Portaal Schans 75-99 (oost)'
add('3-246-LIFT',3,'lift','Lift',R(800,1015,810,1038),P)  # label lift op tekening 3e
add('3-246-TRAP',3,'trap','Trappenhuis',R(812,1004,830,1040),P)  # label trap op tekening 3e
P='Trappenhuis Schans 139/141 (hoek, diagonaal)'
add('3-264-LIFT',3,'lift','Lift',[[1198,982],[1211,969],[1219,977],[1206,990]],P)  # X-schacht op tekening 3e
add('3-264-TRAP',3,'trap','Trappenhuis',[[1208,994],[1226,976],[1236,986],[1218,1004]],P)
add('3-GAL-O',3,'galerij','Galerij Schans 131-141 (3e)',R(759,1003,1170,1012),conf='geschat')
# ------------------------------------------------------------------ 4e
add('4-246-LIFT',4,'lift','Liftopbouw / dak lifthuis',R(800,1015,810,1038),'Portaal Schans 75-99 (oost)')  # schacht/X + dakluik op tekening 4e
add('4-225-LIFT',4,'lift','Dak lifthuis',R(318,550,338,565),'Portaal Het Havenplein (De Kiel 64-84 / Schans 177-179)')  # label "dak lifthuis" op tekening 4e

# ------------------------------------------------------------------ bergingen (individuele cellen, 1e verdieping)
BERG=[]
def cells(blok,idx_list,x0,x1,y0,y1,vertical=False):
    n=len(idx_list)
    for i,ix in enumerate(idx_list):
        if ix is None: continue
        if vertical: a,b=y0+(y1-y0)*i/n,y0+(y1-y0)*(i+1)/n; poly=R(x0,round(a,1),x1,round(b,1))
        else: a,b=x0+(x1-x0)*i/n,x0+(x1-x0)*(i+1)/n; poly=R(round(a,1),y0,round(b,1),y1)
        BERG.append(dict(id=f'BRG-{ix}',index=ix,blok=blok,floor=1,poly=poly))
cells('1-BRG-A',list(range(295,275,-1)),124,150,120,362,vertical=True)
cells('1-BRG-B',[269],236,257,895,907,True); cells('1-BRG-B',[268,267,266],236,257,932,970,True)
cells('1-BRG-B',[275,274,273,272,271,270],263,285,895,970,True)
cells('1-BRG-C',[305,296,297,298,299,300,301,302,303,304],570,690,438,457)
cells('1-BRG-C',[314,306,307,308,309,310,311],570,654,466,489); cells('1-BRG-C',[312,313],666,690,466,489)
cells('1-BRG-D',list(range(322,330)),671,752,865,882); cells('1-BRG-D',list(range(315,322)),671,742,893,915)
cells('1-BRG-E',list(range(343,357)),944,1080,865,882)
cells('1-BRG-E',list(range(330,335)),944,993,891,910); cells('1-BRG-E',list(range(335,343)),1002,1080,891,910)
BLOKKEN=[dict(id='1-BRG-A',name='Bergingen 276-295',range=[276,295]),dict(id='1-BRG-B',name='Bergingen 266-275',range=[266,275]),
 dict(id='1-BRG-C',name='Bergingen 296-314',range=[296,314]),dict(id='1-BRG-D',name='Bergingen 315-329',range=[315,329]),
 dict(id='1-BRG-E',name='Bergingen 330-356',range=[330,356])]

# ------------------------------------------------------------------ daken (niet-woning, indicatieve installatiezones)
DAK={2:[VR(68,95,125,282),VR(167,95,212,282),V([[75,305],[140,305],[195,492],[130,492]]),V([[175,305],[240,305],[262,472],[198,472]]),
        V([[423,335],[565,335],[575,350],[575,450],[540,450],[540,375],[423,375]]),VR(485,500,910,525),VR(485,555,910,578),VR(512,668,866,710),
        V([[165,690],[207,690],[207,740],[185,740],[185,715],[165,715]]),VR(165,800,270,860)],
     3:[VR(55,10,198,60),VR(152,513,200,603),VR(200,602,352,682),VR(290,748,352,866),VR(403,798,520,866),VR(460,490,485,605)],
     4:[VR(343,65,365,92),VR(690,200,843,268),V([[212,430],[466,430],[466,490],[228,490]]),VR(202,597,355,677),VR(398,598,466,747),
        VR(297,745,358,866),VR(578,790,656,872),V([[950,735],[1005,785],[950,838],[893,785]])]}
