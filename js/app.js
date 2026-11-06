/* VvE Van Speijk – interactieve SVG-plattegrond (v2, opnieuw opgebouwd). Vanilla JS, geen build-stap.
   Embed: <div id="vve-app"></div> + js/data.js + js/app.js (+ css/style.css).
   API: VVEKaart.select(id), .setFloor(n), .search(q), .onMelding(fn), .data
   Events op #vve-app: 'vve:select' {id,kind,data} en 'vve:melding' {id,kind,adres,verdieping,naam}; in een iframe ook postMessage. */
(function(){
'use strict';
var D=window.VVE_DATA; if(!D){console.error('VVE_DATA ontbreekt (laad js/data.js eerst)');return;}
var NS='http://www.w3.org/2000/svg';
var root=document.getElementById('vve-app'); if(!root){root=document.createElement('div');root.id='vve-app';document.body.appendChild(root);}
var base=(root.getAttribute('data-base')||'');
var VB=D.meta.viewbox, FN={0:'BG',1:'1e',2:'2e',3:'3e',4:'4e'};
var TYPES={};D.meta.types.forEach(function(t){TYPES[t.id]=t;});
var COMMON_TYPES=['lift','trap','entree','galerij','meterkast','hydrofoor','sprinkler','technisch','fietsenberging','daktuin','niet-vve'];
var state={floor:+(root.getAttribute('data-floor')||1),sel:null,refOpacity:.35,
  layers:{woningen:true,labels:true,common:true,bergingen:true,daken:true,walk:true,route:true,gps:true,meldingen:true,panden:false,ref:false},
  types:{},view:{x:VB[0],y:VB[1],w:VB[2],h:VB[3]}};
COMMON_TYPES.forEach(function(t){state.types[t]=true;});
try{var qf=new URLSearchParams(location.search).get('verdieping');if(qf!=null&&qf!==''&&!isNaN(+qf))state.floor=+qf;}catch(_){}
var meldCb=[];

function el(tag,attrs,parent,ns){var e=ns?document.createElementNS(NS,tag):document.createElement(tag);if(attrs)for(var k in attrs){if(k==='text')e.textContent=attrs[k];else if(k==='html')e.innerHTML=attrs[k];else e.setAttribute(k,attrs[k]);}if(parent)parent.appendChild(e);return e;}
function sv(tag,attrs,parent){return el(tag,attrs,parent,true);}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function pts(P){return P.map(function(p){return p[0]+','+p[1];}).join(' ');}
function bbox(P){var a=[1e9,1e9,-1e9,-1e9];P.forEach(function(p){a[0]=Math.min(a[0],p[0]);a[1]=Math.min(a[1],p[1]);a[2]=Math.max(a[2],p[0]);a[3]=Math.max(a[3],p[1]);});return a;}
function center(P){var b=bbox(P);return[(b[0]+b[2])/2,(b[1]+b[3])/2];}
function uLabel(u){return (u.straat==='Schans'?'':'K')+u.huisnr;}

/* ---------- indexen ---------- */
var byId={};
D.units.forEach(function(u){byId[u.id]={kind:'unit',obj:u};});
D.features.forEach(function(f){byId[f.id]={kind:'common',obj:f};});
D.bergingen.forEach(function(b){byId[b.id]={kind:'berging',obj:b};});
D.blokken.forEach(function(b){byId[b.id]={kind:'blok',obj:b};});
D.photos.forEach(function(p){byId[p.id]={kind:'photo',obj:p};});
D.meldingen.forEach(function(m){byId[m.id]={kind:'melding',obj:m};});
D.context.forEach(function(c){byId[c.id]={kind:'context',obj:c};});
var bergByIndex={};D.bergingen.forEach(function(b){bergByIndex[b.index]=b;});
function meldingenVoor(id){return D.meldingen.filter(function(m){return m.units.indexOf(id)>=0||m.features.indexOf(id)>=0||m.bergingen.indexOf(id)>=0;});}
function geomOf(id,floor){var r=byId[id];if(!r)return null;var o=r.obj;
  if(r.kind==='unit'){var g=o.geometry[String(floor)];return g?{floor:floor,poly:g}:{floor:o.floors[0],poly:o.geometry[String(o.floors[0])]};}
  if(o.poly)return{floor:o.floor,poly:o.poly}; if(o.point)return{floor:o.floor||0,poly:[o.point,o.point]};return null;}
// plek van een melding = eerste gekoppelde object met geometrie
D.meldingen.forEach(function(m){var ids=m.features.concat(m.bergingen,m.units);for(var i=0;i<ids.length;i++){var g=geomOf(ids[i]);if(g){m._floor=g.floor;m._pt=center(g.poly);break;}}});

/* ---------- layout ---------- */
root.innerHTML='';
var top=el('header',{'class':'vve-top'},root);
el('h1',{html:'VvE Van Speijk <small>Suydersee Veste · Dronten</small>'},top);
var floorsEl=el('div',{'class':'vve-floors',role:'tablist','aria-label':'Verdieping'},top);
D.meta.floors.forEach(function(f){
  var n=D.units.filter(function(u){return u.floors.indexOf(f.n)>=0;}).length;
  var b=el('button',{role:'tab','data-f':f.n,title:f.titel,html:esc(f.naam)+(n?'<small>'+n+'</small>':'')},floorsEl);
  b.onclick=function(){setFloor(f.n);};});
var searchWrap=el('div',{'class':'vve-search'},top);
var input=el('input',{type:'search',placeholder:'Zoek: 173, Kiel 64, lift, hydrofoor, berging 308, melding 384979…','aria-label':'Zoeken'},searchWrap);
var results=el('div',{'class':'vve-results'},searchWrap);
var main=el('div',{'class':'vve-main'},root);
var wrap=el('div',{'class':'vve-mapwrap'},main);
var svg=sv('svg',{viewBox:VB.join(' '),preserveAspectRatio:'xMidYMid meet','aria-label':'Plattegrond'},wrap);
var defs=sv('defs',{},svg);
defs.innerHTML='<pattern id="p-trap" width="3" height="3" patternUnits="userSpaceOnUse"><rect width="3" height="3" fill="#e8d9ef"/><line x1="0" y1="0" x2="0" y2="3" stroke="#7d3c98" stroke-width=".7"/></pattern>'+
 '<pattern id="p-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#eeeeee"/><line x1="0" y1="0" x2="0" y2="6" stroke="#9e9e9e" stroke-width="1.2"/></pattern>'+
 '<pattern id="p-dak" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="10" height="10" fill="#eceef0"/><line x1="0" y1="0" x2="0" y2="10" stroke="#d5d8dc" stroke-width="1"/></pattern>'+
 '<pattern id="p-groen" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#e5f3dc"/><circle cx="4" cy="4" r="1" fill="#8fc274"/></pattern>';
var G={};['ref','pand','outline','dak','berg','units','feat','sym','lbl','ctx','route','walk','gps','meld'].forEach(function(k){G[k]=sv('g',{'class':'g-'+k},svg);});
var badge=el('div',{'class':'vve-floorbadge'},wrap);
var zoom=el('div',{'class':'vve-zoom'},wrap);
[['+','Inzoomen',function(){zoomBy(1/1.4);}],['−','Uitzoomen',function(){zoomBy(1.4);}],['⤢','Passend maken',function(){fitFloor();}]].forEach(function(z){var b=el('button',{title:z[1],'aria-label':z[1],text:z[0]},zoom);b.onclick=z[2];});
var legend=el('div',{'class':'vve-legend'},wrap);
var panel=el('aside',{'class':'vve-panel empty'},main);
el('div',{'class':'vve-foot',html:'Schematische SVG-plattegrond, overgetrokken van de splitsingstekening (akte 2006) + huisnummerlijst; geen maatvoering. BAG via PDOK (Kadaster), peildatum '+esc(D.meta.peildatum)+'. Foto’s: wandeling 06-11-2026 en Twinq-meldingen. Zie data/sources.md.'},root);
var lb=el('div',{'class':'vve-lightbox',hidden:''},document.body);

/* ---------- legenda & lagen ---------- */
function buildLegend(){
  legend.innerHTML='';
  var d=el('details',(window.innerWidth>1800&&window.innerHeight>1000?{open:''}:{}),legend); el('summary',{text:'Legenda & lagen'},d);
  var sw=function(t){var s=el('span',{'class':'sw sw-'+t});s.style.background=TYPES[t]?TYPES[t].kleur:'#ccc';return s;};
  el('h4',{text:'Woningen'},d);
  ['woning-schans','woning-kiel'].forEach(function(t){var r=el('div',{'class':'row'},d);r.appendChild(sw(t));el('span',{text:TYPES[t].label},r);});
  el('div',{'class':'row',html:'<span class="sw" style="background:#fff;border-style:dashed"></span><span>Gestippeld = maisonnette (meerdere etages)</span>'},d);
  el('h4',{text:'Gemeenschappelijk & technisch'},d);
  COMMON_TYPES.forEach(function(t){var lab=el('label',{'class':'row'},d);var cb=el('input',{type:'checkbox'},lab);cb.checked=state.types[t];lab.appendChild(sw(t));el('span',{text:TYPES[t].label},lab);
    cb.onchange=function(){state.types[t]=cb.checked;render();};});
  el('h4',{text:'Lagen'},d);
  [['woningen','Woningen'],['labels','Huisnummers & labels'],['common','Gemeenschappelijke ruimten'],['bergingen','Bergingen (1e verd.)'],['daken','Daken'],
   ['meldingen','Twinq-meldingen met foto’s'],['gps','GPS-foto’s (Twinq)'],['walk','Wandelfoto’s (positie geschat)'],['route','Looproute wandeling'],['panden','BAG-pandcontouren'],['ref','Referentie: scan splitsingstekening']].forEach(function(l){
    var lab=el('label',{},d); var cb=el('input',{type:'checkbox'},lab); cb.checked=state.layers[l[0]]; el('span',{text:l[1]},lab);
    cb.onchange=function(){state.layers[l[0]]=cb.checked;render();};});
  var op=el('label',{'class':'row'},d);el('span',{text:'Dekking scan'},op);var r=el('input',{type:'range',min:'0.1',max:'0.9',step:'0.05'},op);r.value=state.refOpacity;
  r.oninput=function(){state.refOpacity=+r.value;var im=G.ref.querySelector('image');if(im)im.setAttribute('opacity',r.value);};
  el('div',{'class':'row',html:'<span class="mk mk-meld">!</span><span>Melding met foto (Twinq)</span>'},d);
  el('div',{'class':'row',html:'<span class="mk mk-gps"></span><span>GPS-foto (cirkel = GPS-nauwkeurigheid)</span>'},d);
  el('div',{'class':'row',html:'<span class="mk mk-walk"></span><span>Wandelfoto (positie geschat ±5–15 m)</span>'},d);
}

/* ---------- view ---------- */
function applyView(){var v=state.view;svg.setAttribute('viewBox',[v.x,v.y,v.w,v.h].join(' '));}
function fitFloor(){var P=[];D.outlines[String(state.floor)].forEach(function(r){P=P.concat(r);});if(!P.length){state.view={x:VB[0],y:VB[1],w:VB[2],h:VB[3]};}else{var b=bbox(P),m=30;state.view={x:b[0]-m,y:b[1]-m,w:b[2]-b[0]+2*m,h:b[3]-b[1]+2*m};}applyView();}
function svgPoint(cx,cy){var m=svg.getScreenCTM();if(!m)return{x:0,y:0};var p=svg.createSVGPoint();p.x=cx;p.y=cy;return p.matrixTransform(m.inverse());}
function zoomBy(f,cx,cy){var v=state.view;var c=(cx==null)?{x:v.x+v.w/2,y:v.y+v.h/2}:svgPoint(cx,cy);
  var nw=Math.min(Math.max(v.w*f,40),VB[2]*2.5);f=nw/v.w;state.view={x:c.x-(c.x-v.x)*f,y:c.y-(c.y-v.y)*f,w:v.w*f,h:v.h*f};applyView();}
function centerOn(P){var b=bbox(P),cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;var w=Math.max(260,(b[2]-b[0])*4),h=w*VB[3]/VB[2];state.view={x:cx-w/2,y:cy-h/2,w:w,h:h};applyView();}
wrap.addEventListener('wheel',function(e){e.preventDefault();zoomBy(e.deltaY>0?1.15:1/1.15,e.clientX,e.clientY);},{passive:false});
var ptrs={},drag=null,moved=false;
wrap.addEventListener('pointerdown',function(e){ptrs[e.pointerId]={x:e.clientX,y:e.clientY};moved=false;
  drag=Object.keys(ptrs).length===1?{x:e.clientX,y:e.clientY,v:Object.assign({},state.view)}:null;});
wrap.addEventListener('pointermove',function(e){if(!ptrs[e.pointerId])return;var prev=ptrs[e.pointerId];ptrs[e.pointerId]={x:e.clientX,y:e.clientY};var ids=Object.keys(ptrs);
  if(ids.length===2){var a=ptrs[ids[0]],b=ptrs[ids[1]];var pa=ids[0]==e.pointerId?prev:a,pb=ids[1]==e.pointerId?prev:b;
    var d0=Math.hypot(pa.x-pb.x,pa.y-pb.y),d1=Math.hypot(a.x-b.x,a.y-b.y);if(d0>0&&d1>0)zoomBy(d0/d1,(a.x+b.x)/2,(a.y+b.y)/2);moved=true;return;}
  if(!drag)return;var dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4){moved=true;wrap.classList.add('dragging');}
  if(!moved)return;var m=svg.getScreenCTM();var s=m?m.a:1;state.view.x=drag.v.x-dx/s;state.view.y=drag.v.y-dy/s;applyView();});
function up(e){delete ptrs[e.pointerId];if(!Object.keys(ptrs).length){drag=null;wrap.classList.remove('dragging');}}
wrap.addEventListener('pointerup',up);wrap.addEventListener('pointercancel',up);
function onTap(node,fn,label){node.addEventListener('click',function(e){e.stopPropagation();if(moved)return;fn();});
  node.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}});node.setAttribute('tabindex','0');if(label)node.setAttribute('aria-label',label);}

/* ---------- render ---------- */
function clear(g){while(g.firstChild)g.removeChild(g.firstChild);}
function isSel(id){return state.sel&&state.sel.id===id;}
function relSel(id){if(!state.sel)return false;var s=state.sel;
  if(s.kind==='melding')return s.obj.units.indexOf(id)>=0||s.obj.features.indexOf(id)>=0||s.obj.bergingen.indexOf(id)>=0;
  if(s.kind==='unit'){var b=bergByIndex[s.obj.berging.index];return b&&b.id===id;}
  if(s.kind==='berging')return s.obj.eigenaar===id; if(s.kind==='blok')return byId[id]&&byId[id].kind==='berging'&&byId[id].obj.blok===s.id;return false;}
function text(g,x,y,t,cls,size){var e=sv('text',{x:x,y:y,'class':cls,'font-size':size},g);e.textContent=t;return e;}
var SHORT={lift:'Lift',trap:'Trap',entree:'Entree',meterkast:'MK',hydrofoor:'Hydrofoor',sprinkler:'Sprinkler',technisch:'Techn.',fietsenberging:'Fietsen',galerij:'',daktuin:'Daktuin','niet-vve':'Niet VvE'};
function render(){
  Object.keys(G).forEach(function(k){clear(G[k]);});
  var f=state.floor, F=D.meta.floors.filter(function(x){return x.n===f;})[0];
  Array.prototype.forEach.call(floorsEl.children,function(b){var a=+b.getAttribute('data-f')===f;b.classList.toggle('active',a);b.setAttribute('aria-selected',a);});
  var nU=D.units.filter(function(u){return u.floors.indexOf(f)>=0;});
  badge.textContent=F.titel+' · '+nU.length+' woning'+(nU.length===1?'':'en')+(f===0?' · entrees, liften, meterkasten, techniek':'');
  if(state.layers.ref){var im=sv('image',{x:VB[0],y:VB[1],width:VB[2],height:VB[3],preserveAspectRatio:'none',opacity:state.refOpacity},G.ref);im.setAttribute('href',base+F.img);}
  if(state.layers.panden)D.panden.forEach(function(p){p.rings.forEach(function(r){sv('polygon',{points:pts(r),'class':'pand'+(p.complex?' complex':'')},G.pand);});});
  // gebouwcontour (overgetrokken + BAG)
  var d='';(D.outlines[String(f)]||[]).forEach(function(r){d+='M'+r.map(function(p){return p[0]+','+p[1];}).join('L')+'Z';});
  sv('path',{d:d,'class':'outline','fill-rule':'evenodd'},G.outline);
  // daken + gemeenschappelijk
  D.features.filter(function(c){return c.floor===f;}).forEach(function(c){
    if(c.type==='dak'){if(!state.layers.daken)return;}else{if(!state.layers.common||!state.types[c.type])return;}
    var g=(c.type==='dak'||c.type==='daktuin'||c.type==='niet-vve'||c.type==='galerij')?G.dak:G.feat;
    var p=sv('polygon',{points:pts(c.poly),'class':'c-poly t-'+c.type+(c.conf!=='tekening'?' conf-'+c.conf:'')+(isSel(c.id)?' sel':'')+(relSel(c.id)?' rel':'')},g);
    p.style.setProperty('--c',TYPES[c.type].kleur);
    sv('title',{text:c.name+(c.portaal?' – '+c.portaal:'')},p);onTap(p,function(){select(c.id,true);},c.name);
    var b=bbox(c.poly),w=b[2]-b[0],h=b[3]-b[1],cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;
    if(c.type==='lift'){sv('path',{d:'M'+b[0]+','+b[1]+'L'+b[2]+','+b[3]+'M'+b[2]+','+b[1]+'L'+b[0]+','+b[3],'class':'lift-x'},G.sym);}
    if(state.layers.labels&&SHORT[c.type]){var s=Math.min(7,Math.max(3,Math.min(w,h)/(c.type==='meterkast'?2.2:3.2)));var t=SHORT[c.type];
      if(t.length*s*.6>w&&h>w){var e=text(G.lbl,cx,cy,t,'c-lbl',s);e.setAttribute('transform','rotate(-90 '+cx+' '+cy+')');}
      else if(t.length*s*.55<=w+2||c.type==='meterkast')text(G.lbl,cx,cy,t,'c-lbl',s);}
  });
  // bergingen
  if(f===1&&state.layers.bergingen){
    D.bergingen.forEach(function(b){var p=sv('polygon',{points:pts(b.poly),'class':'c-poly t-berging'+(isSel(b.id)?' sel':'')+(relSel(b.id)?' rel':'')},G.berg);p.style.setProperty('--c',TYPES.berging.kleur);
      sv('title',{text:b.name+(b.eigenaar?' – '+byId[b.eigenaar].obj.adres:'')},p);onTap(p,function(){select(b.id,true);},b.name);
      if(state.layers.labels){var bb=bbox(b.poly),w=bb[2]-bb[0],h=bb[3]-bb[1];var e=text(G.lbl,(bb[0]+bb[2])/2,(bb[1]+bb[3])/2,String(b.index),'b-lbl',Math.min(4.2,Math.max(w,h)/3.4));if(h>w*1.3)0;}});
  }
  // woningen
  if(state.layers.woningen)nU.forEach(function(u){var P=u.geometry[String(f)];
    var p=sv('polygon',{points:pts(P),'class':'u-poly '+(u.straat==='Schans'?'schans':'kiel')+(u.meerlaags?' multi':'')+(isSel(u.id)?' sel':'')+(relSel(u.id)?' rel':'')},G.units);
    sv('title',{text:u.adres+(u.meerlaags?' ('+u.etages.join('+')+')':'')},p);onTap(p,function(){select(u.id,true);},u.adres);
    if(state.layers.labels){var b=bbox(P),w=b[2]-b[0],h=b[3]-b[1],s=Math.max(7,Math.min(15,Math.min(w,h)/2.6));var c=[(b[0]+b[2])/2,(b[1]+b[3])/2];
      var e=text(G.lbl,c[0],c[1],uLabel(u),'u-lbl',s);if(h>w*1.6&&w<s*2.6)e.setAttribute('transform','rotate(-90 '+c[0]+' '+c[1]+')');
      if(u.meerlaags)text(G.lbl,c[0],c[1]+s*.95,u.etages.join('+'),'u-lbl2',s*.55);}
  });
  if(f===0&&state.layers.labels)D.context.forEach(function(c){var g=sv('g',{'class':'ctx'},G.ctx);sv('circle',{cx:c.point[0],cy:c.point[1],r:5,'class':'ctx-pt '+c.type},g);
    text(g,c.point[0]+8,c.point[1]+4,c.name,'ctx-lbl',11);onTap(g,function(){select(c.id,true);},c.name);});
  // wandelfoto's + route
  var walk=D.photos.filter(function(p){return !p.gps&&p.floor===f;});
  if(state.layers.route&&walk.length>1)sv('polyline',{points:pts(walk.map(function(p){return p.point;})),'class':'route'},G.route);
  if(state.layers.walk)walk.forEach(function(p){var g=sv('g',{'class':'ph walk'+(isSel(p.id)?' sel':'')},G.walk);
    sv('circle',{cx:p.point[0],cy:p.point[1],r:4.2,'class':'dot'},g);sv('title',{text:p.label+' (positie geschat)'},g);onTap(g,function(){select(p.id,true);},p.label);});
  // GPS-foto's (straatniveau: getoond op BG en 1e)
  if(state.layers.gps&&f<=1)D.photos.filter(function(p){return p.gps;}).forEach(function(p){var g=sv('g',{'class':'ph gps'+(isSel(p.id)?' sel':'')},G.gps);
    if(p.radius_plan)sv('circle',{cx:p.point[0],cy:p.point[1],r:p.radius_plan,'class':'acc'},g);
    if(p.richting_graden!=null){var a=dirToPlan(p.richting_graden);sv('line',{x1:p.point[0],y1:p.point[1],x2:p.point[0]+Math.cos(a)*20,y2:p.point[1]+Math.sin(a)*20,'class':'dir'},g);}
    sv('circle',{cx:p.point[0],cy:p.point[1],r:5,'class':'dot'},g);sv('title',{text:p.label+' (GPS ±'+p.nauwkeurigheid_m+' m)'},g);onTap(g,function(){select(p.id,true);},p.label);});
  // meldingen
  if(state.layers.meldingen)D.meldingen.forEach(function(m){if(m._floor!==f||!m._pt)return;var g=sv('g',{'class':'meld'+(isSel(m.id)?' sel':'')},G.meld);
    var x=m._pt[0],y=m._pt[1];sv('path',{d:'M'+x+','+y+'l-6,-11a7,7 0 1,1 12,0z','class':'pin'},g);text(g,x,y-14.5,'!','pin-t',8);
    sv('title',{text:'Melding '+m.verzoek+': '+m.onderwerp},g);onTap(g,function(){select(m.id,true);},'Melding '+m.verzoek);});
  buildPanel();
}
function dirToPlan(deg){var T=D.meta.georef.transform;var r=deg*Math.PI/180;var dx=Math.sin(r),dy=Math.cos(r);if(T.mirror)dy=-dy;var x=T.zr*dx-T.zi*dy,y=T.zi*dx+T.zr*dy;return Math.atan2(y,x);}

/* ---------- paneel ---------- */
function row(k,v){return v==null||v===''?'':'<tr><td>'+esc(k)+'</td><td>'+v+'</td></tr>';}
function link(id,txt){return '<a href="#'+esc(id)+'" data-go="'+esc(id)+'">'+esc(txt||id)+'</a>';}
function srcList(arr){return '<ul class="src">'+arr.filter(Boolean).map(function(s){var m=String(s).match(/(https?:\/\/\S+)/);return '<li>'+(m?esc(s.replace(m[1],''))+'<a href="'+esc(m[1])+'" target="_blank" rel="noopener">'+esc(m[1])+'</a>':esc(s))+'</li>';}).join('')+'</ul>';}
var CONF={tekening:['confirmed','op tekening'],afgeleid:['estimated','afgeleid (andere verdieping)'],geschat:['estimated','geschat'],bag_point:['confirmed','BAG-adrespunt']};
function chip(c){var x=CONF[c]||['estimated',c];return '<span class="chip '+x[0]+'">'+esc(x[1])+'</span>';}
var galleries=[];
function gallery(items){ // items: [{src,thumb,caption}]
  if(!items.length)return '';var gi=galleries.length;galleries.push(items);
  return '<div class="gal">'+items.map(function(it,i){return '<button class="th" data-gal="'+gi+'" data-i="'+i+'" title="'+esc(it.caption)+'"><img loading="lazy" src="'+esc(base+it.thumb)+'" alt="'+esc(it.caption)+'"></button>';}).join('')+'</div>';}
function meldItems(m){return m.fotos.map(function(f,i){return{src:f.src,thumb:f.thumb,caption:'Melding '+m.verzoek+' ('+m.datum+'): '+m.onderwerp+' – foto '+(i+1)+'/'+m.fotos.length};});}
function meldBlock(id){var ms=meldingenVoor(id);if(!ms.length)return '';
  return '<h4>Twinq-meldingen ('+ms.length+')</h4>'+ms.map(function(m){return '<div class="mcard"><div>'+link(m.id,'#'+m.verzoek)+' · '+esc(m.datum)+' · <b>'+esc(m.onderwerp)+'</b> <small>'+esc(m.status||'')+'</small></div>'+gallery(meldItems(m))+'</div>';}).join('');}
function meldButton(){return '<button class="vve-melden" data-melden>Melding maken voor dit object</button>';}
function nabijHtml(ids){return ids&&ids.length?ids.map(function(i){return link(i,byId[i].obj.adres);}).join(', '):'';}
function buildPanel(){
  galleries=[];var s=state.sel; panel.classList.toggle('empty',!s);
  if(!s){panel.innerHTML='<h2>Kies een object</h2><div class="sub">Klik op een woning, lift, meterkast, berging, foto of melding – of zoek.</div>'+summaryHtml();wirePanel();return;}
  var h='<button class="close" aria-label="Sluiten">×</button>',o=s.obj;
  if(s.kind==='unit'){var u=o,b=bergByIndex[u.berging.index];
    h+='<h2>'+esc(u.adres)+'</h2><div class="sub">'+esc(u.postcode)+' '+esc(u.woonplaats)+' · '+chip('tekening')+'</div><table>'+
      row('Etage(s)','<span class="floorlinks">'+u.floors.map(function(f){return '<button data-floor="'+f+'">'+FN[f]+'</button>';}).join('')+'</span>'+(u.meerlaags?' maisonnette':''))+
      row('Index nieuw / oud',u.index_nieuw+' / '+u.index_oud)+row('Bouwnummer',esc(u.bouwnr))+
      row('Berging',b?link(b.id,'berging '+u.berging.index)+' (1e verd., '+esc(u.berging.blok)+')':esc(u.berging.index))+
      row('Oppervlakte (BAG)',u.bag.oppervlakte_m2+' m²')+row('Bouwjaar (BAG)',esc(u.bag.bouwjaar))+row('Gebruiksdoel (BAG)',esc(u.bag.gebruiksdoel))+row('Status (BAG)',esc(u.bag.status))+
      row('BAG-verblijfsobject','<a href="'+esc(u.bag.url)+'" target="_blank" rel="noopener">'+esc(u.bag.verblijfsobject_id)+'</a>')+row('BAG-pand',esc(u.bag.pand_id))+
      row('WGS84',u.bag.wgs84.join(', '))+
      row('Energielabel',u.openbaar.energielabel?esc(u.openbaar.energielabel)+' <small>(Huispedia, niet geverifieerd)</small>':'<small>niet gevonden</small>')+
      row('Type (Huispedia)',esc(u.openbaar.soort_huispedia||''))+'</table>'+meldBlock(u.id)+meldButton();
    if(u.notes.length)h+='<h4>Opmerkingen</h4><ul>'+u.notes.map(function(n){return '<li>'+esc(n)+'</li>';}).join('')+'</ul>';
    h+='<h4>Bronnen</h4>'+srcList(u.bronnen);
  } else if(s.kind==='common'){var c=o;
    h+='<h2>'+esc(c.name)+'</h2><div class="sub">'+esc(c.type_label)+' · '+esc(c.floor_name)+' · '+chip(c.conf)+'</div><table>'+
      row('Portaal',esc(c.portaal||''))+row('Nabij',nabijHtml(c.nabij))+row('Oppervlakte (schematisch)',c.opp_m2?'≈ '+c.opp_m2+' m²':'')+
      row('Op tekening 2006',c.tekening_label?esc(c.tekening_label):'')+'</table>'+(c.info?'<p class="info">'+esc(c.info)+'</p>':'')+meldBlock(c.id)+meldButton()+'<h4>Bron</h4>'+srcList([c.bron]);
  } else if(s.kind==='berging'){var bb=o,ow=bb.eigenaar&&byId[bb.eigenaar].obj;
    h+='<h2>'+esc(bb.name)+'</h2><div class="sub">Privéberging · 1e verdieping · '+chip('tekening')+'</div><table>'+
      row('Hoort bij',ow?link(ow.id,ow.adres):'<small>onbekend</small>')+row('Blok',link(bb.blok,byId[bb.blok].obj.name))+row('Oppervlakte (schematisch)','≈ '+bb.opp_m2+' m²')+'</table>'+meldBlock(bb.id)+meldButton()+'<h4>Bron</h4>'+srcList([bb.bron]);
  } else if(s.kind==='blok'){var bl=o,cs=D.bergingen.filter(function(x){return x.blok===bl.id;}).sort(function(a,b){return a.index-b.index;});
    h+='<h2>'+esc(bl.name)+'</h2><div class="sub">Bergingenblok · 1e verdieping</div><ul class="cols">'+cs.map(function(x){return '<li>'+link(x.id,String(x.index))+' → '+(x.eigenaar?link(x.eigenaar,byId[x.eigenaar].obj.adres):'?')+'</li>';}).join('')+'</ul>'+meldBlock(bl.id);
  } else if(s.kind==='photo'){var p=o,m=p.melding&&byId[p.melding]?byId[p.melding].obj:null;
    h+='<h2>'+esc(p.label)+'</h2><div class="sub">'+(p.gps?'<span class="chip gps">GPS (Twinq-foto)</span>':'<span class="chip estimated">positie geschat</span>')+' · '+esc(FN[p.floor])+'</div>'+
      gallery([{src:p.file,thumb:p.file,caption:p.label}])+'<table>'+row('Tijd',esc(p.tijd))+row('Positie',esc(p.nauwkeurigheid))+
      (p.gps?row('GPS',p.lat+', '+p.lon)+row('Kijkrichting',p.richting_graden+'°')+row('Melding',m?link(m.id,'#'+m.verzoek+' '+m.onderwerp):''):'')+row('Notitie',esc(p.notitie||''))+'</table>'+
      (m?'<h4>Alle foto’s van melding '+m.verzoek+'</h4>'+gallery(meldItems(m)):'')+'<h4>Bron</h4>'+srcList([p.bron]);
  } else if(s.kind==='melding'){var M=o,objs=M.units.concat(M.features,M.bergingen);
    h+='<h2>Melding '+esc(M.verzoek)+'</h2><div class="sub">'+esc(M.datum)+' · '+esc(M.type||'')+' · '+esc(M.status||'')+'</div><p><b>'+esc(M.onderwerp)+'</b></p><p>'+esc(M.omschrijving)+'</p>'+
      gallery(meldItems(M))+'<table>'+row('Opdracht',esc(M.opdracht||''))+row('Gekoppeld aan',objs.map(function(i){var r=byId[i];return link(i,r.obj.adres||r.obj.name);}).join(', ')||'<small>locatie onbekend</small>')+
      row('Locatie',M.locatie?chip(M.locatie==='adres'?'tekening':'geschat').replace('op tekening','adres in melding'):'')+row('Toelichting locatie',esc(M.locatie_toelichting||''))+
      row('GPS-foto’s',(M.gps_fotos||[]).map(function(i){return link(i,i);}).join(', '))+'</table><h4>Bron</h4>'+srcList([M.bron+' – contactgegevens verwijderd']);
  } else if(s.kind==='context'){h+='<h2>'+esc(o.name)+'</h2><div class="sub">'+chip(o.conf)+'</div><p>'+esc(o.info||'')+'</p>'+srcList([o.bron]);}
  panel.innerHTML=h;wirePanel();
}
function wirePanel(){
  var c=panel.querySelector('.close');if(c)c.onclick=function(){state.sel=null;try{history.replaceState(null,'',location.pathname+location.search);}catch(_){}render();};
  Array.prototype.forEach.call(panel.querySelectorAll('[data-floor]'),function(b){b.onclick=function(){setFloor(+b.getAttribute('data-floor'));};});
  Array.prototype.forEach.call(panel.querySelectorAll('[data-go]'),function(a){a.onclick=function(e){e.preventDefault();select(a.getAttribute('data-go'));};});
  Array.prototype.forEach.call(panel.querySelectorAll('[data-gal]'),function(b){b.onclick=function(){openLB(+b.getAttribute('data-gal'),+b.getAttribute('data-i'));};});
  var mb=panel.querySelector('[data-melden]');if(mb)mb.onclick=function(){melden();};
}
function summaryHtml(){
  var by={};D.units.forEach(function(u){by[u.straat]=(by[u.straat]||0)+1;});
  var cnt={};D.features.forEach(function(f){cnt[f.type]=(cnt[f.type]||0)+1;});
  var los=D.meldingen.filter(function(m){return m._pt==null;});
  return '<table>'+Object.keys(by).map(function(k){return row(k,by[k]+' woningen');}).join('')+row('Totaal',D.units.length+' woningen')+row('Bergingen',D.bergingen.length)+
    ['lift','trap','meterkast','hydrofoor','sprinkler','fietsenberging','technisch'].map(function(t){return row(TYPES[t].label,cnt[t]||0);}).join('')+
    row('Twinq-meldingen met foto',D.meldingen.length+' ('+D.meldingen.reduce(function(a,m){return a+m.fotos.length;},0)+' foto’s)')+'</table>'+
    '<h4>Meldingen zonder vaste plek op de kaart</h4><ul>'+los.map(function(m){return '<li>'+link(m.id,'#'+m.verzoek)+' '+esc(m.onderwerp)+(m.locatie_toelichting?' <small>('+esc(m.locatie_toelichting)+')</small>':'')+'</li>';}).join('')+'</ul>'+
    '<p><small>Fietsenbergingen heten op de tekening van 2006 “containerruimte”; ze zijn allemaal omgebouwd tot fietsenberging.</small></p>';
}
/* ---------- lightbox ---------- */
var lbState=null;
function openLB(gi,i){lbState={items:galleries[gi],i:i};drawLB();lb.hidden=false;document.addEventListener('keydown',lbKey);}
function closeLB(){lb.hidden=true;lbState=null;document.removeEventListener('keydown',lbKey);}
function lbKey(e){if(e.key==='Escape')closeLB();else if(e.key==='ArrowRight')step(1);else if(e.key==='ArrowLeft')step(-1);}
function step(d){if(!lbState)return;var n=lbState.items.length;lbState.i=(lbState.i+d+n)%n;drawLB();}
function drawLB(){var it=lbState.items[lbState.i],n=lbState.items.length;
  lb.innerHTML='<div class="lb-in"><img src="'+esc(base+it.src)+'" alt="'+esc(it.caption)+'"><div class="lb-cap">'+esc(it.caption)+' · <a href="'+esc(base+it.src)+'" target="_blank" rel="noopener">open</a></div></div>'+
    '<button class="lb-x" aria-label="Sluiten">×</button>'+(n>1?'<button class="lb-p" aria-label="Vorige">‹</button><button class="lb-n" aria-label="Volgende">›</button>':'');
  lb.querySelector('.lb-x').onclick=closeLB;var p=lb.querySelector('.lb-p'),q=lb.querySelector('.lb-n');if(p){p.onclick=function(e){e.stopPropagation();step(-1);};q.onclick=function(e){e.stopPropagation();step(1);};}
  lb.onclick=function(e){if(e.target===lb)closeLB();};}

/* ---------- selectie, melding, zoeken ---------- */
function emit(name,detail){try{root.dispatchEvent(new CustomEvent(name,{detail:detail,bubbles:true}));}catch(_){}
  try{if(window.parent!==window)window.parent.postMessage(Object.assign({type:name},detail,{data:undefined}),'*');}catch(_){}}
function select(id,noCenter){
  var r=byId[id];if(!r)return;state.sel={kind:r.kind,id:id,obj:r.obj};var o=r.obj,P=null;
  if(r.kind==='unit'){if(o.floors.indexOf(state.floor)<0)state.floor=o.floors[0];P=o.geometry[String(state.floor)];}
  else if(r.kind==='melding'){if(o._floor!=null){state.floor=o._floor;P=[o._pt,o._pt];}}
  else if(r.kind==='photo'){if(!(o.gps&&state.floor<=1))state.floor=o.floor;P=[o.point,o.point];}
  else{if(o.floor!=null)state.floor=o.floor;P=o.poly||(o.point?[o.point,o.point]:null);}
  render();if(!noCenter&&P)centerOn(P);
  try{history.replaceState(null,'','#'+id);}catch(_){}
  emit('vve:select',{id:id,kind:r.kind,data:o});
}
function melden(){var s=state.sel;if(!s)return;var o=s.obj;
  var det={id:s.id,kind:s.kind,naam:o.adres||o.name||o.label||s.id,adres:o.adres||(o.eigenaar&&byId[o.eigenaar]?byId[o.eigenaar].obj.adres:null)||(o.nabij&&o.nabij[0]?'nabij '+byId[o.nabij[0]].obj.adres:null),
    verdieping:FN[state.floor],portaal:o.portaal||null,type:o.type||s.kind,link:location.href.split('#')[0]+'#'+s.id};
  emit('vve:melding',det);meldCb.forEach(function(f){try{f(det);}catch(_){}});
  if(!meldCb.length&&window.parent===window){var t='Melding voor: '+det.naam+'\nVerdieping: '+det.verdieping+(det.portaal?'\nPortaal: '+det.portaal:'')+(det.adres?'\nAdres: '+det.adres:'')+'\nKaart: '+det.link;
    try{navigator.clipboard.writeText(t);}catch(_){}
    alert('Meldingsformulier is nog niet gekoppeld (koppeling Twinq volgt).\nDeze gegevens staan op het klembord:\n\n'+t);}
}
function setFloor(f){state.floor=f;render();fitFloor();}
function norm(s){return String(s).toLowerCase().replace(/\bde\s+/g,'').replace(/[’']/g,'').replace(/\s+/g,' ').trim();}
function search(q){q=norm(q);if(!q)return[];var out=[];
  var num=(q.match(/\d+/)||[])[0];var str=q.replace(/\d+/g,'').replace(/\b(index|nr\.?|nummer)\b/g,'').trim();
  if(/berging/.test(q)&&num){var b=bergByIndex[+num];if(b)out.push({id:b.id,t:b.name,s:'1e · '+(b.eigenaar?byId[b.eigenaar].obj.adres:''),score:9});str=str.replace('berging','').trim();}
  if(/melding|verzoek/.test(q)||(num&&num.length===6)){D.meldingen.forEach(function(m){if(!num||m.verzoek.indexOf(num)===0)out.push({id:m.id,t:'Melding '+m.verzoek,s:m.onderwerp,score:8});});}
  D.units.forEach(function(u){var s=norm(u.straat),score=0;if(/berging|melding/.test(q))return;
    if(num&&String(u.huisnr)===num)score+=3;if(num&&String(u.index_nieuw)===num)score+=1;if(num&&score===0)return;
    if(str){if(s.indexOf(str)===0||(str==='k'&&s==='kiel')||(str==='s'&&s==='schans'))score+=(num?2:1);else if(num)score=0;else return;}
    if(score>0)out.push({id:u.id,t:u.adres,s:u.etages.join('+')+' · berging '+u.berging.index,score:score});});
  if(str&&str.length>=3&&!/berging \d/.test(q)){D.features.forEach(function(c){if(c.type==='dak')return;var hay=norm(c.name+' '+c.type_label+' '+(c.portaal||'')+' '+(c.tekening_label||''));
      if(hay.indexOf(str)>=0)out.push({id:c.id,t:c.name,s:c.floor_name+(c.portaal?' · '+c.portaal:''),score:.5});});
    D.meldingen.forEach(function(m){if(norm(m.onderwerp+' '+m.omschrijving).indexOf(str)>=0)out.push({id:m.id,t:'Melding '+m.verzoek,s:m.onderwerp,score:.3});});
    D.blokken.forEach(function(b){if(norm(b.name).indexOf(str)>=0)out.push({id:b.id,t:b.name,s:'1e',score:.4});});}
  return out.sort(function(a,b){return b.score-a.score;}).slice(0,40);}
var cur=[],curSel=0;
function showResults(){results.innerHTML='';if(!cur.length){results.style.display=input.value?'block':'none';if(input.value)el('div',{html:'<span>Geen resultaat</span>'},results);return;}
  results.style.display='block';cur.forEach(function(r,i){var d=el('div',{'class':i===curSel?'sel':'',html:'<span>'+esc(r.t)+'</span><small>'+esc(r.s)+'</small>'},results);d.onmousedown=function(e){e.preventDefault();pick(r);};});}
function pick(r){results.style.display='none';input.blur();select(r.id);}
input.addEventListener('input',function(){cur=search(input.value);curSel=0;showResults();});
input.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){curSel=Math.min(curSel+1,cur.length-1);showResults();e.preventDefault();}else if(e.key==='ArrowUp'){curSel=Math.max(curSel-1,0);showResults();e.preventDefault();}else if(e.key==='Enter'&&cur[curSel]){pick(cur[curSel]);}else if(e.key==='Escape'){results.style.display='none';}});
input.addEventListener('blur',function(){setTimeout(function(){results.style.display='none';},150);});

/* ---------- init ---------- */
buildLegend();render();fitFloor();
var h0=decodeURIComponent((location.hash||'').slice(1));if(h0)select(h0);
window.addEventListener('hashchange',function(){var h=decodeURIComponent(location.hash.slice(1));if(h&&(!state.sel||state.sel.id!==h))select(h);});
window.VVEKaart={select:select,setFloor:setFloor,data:D,search:search,onMelding:function(fn){meldCb.push(fn);}};
})();
