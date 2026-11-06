/* VvE Van Speijk – interactieve verdiepingenkaart. Vanilla JS + SVG, geen build-stap.
   Embed: <div id="vve-app"></div> + js/data.js + js/app.js (+ css/style.css).
   API: window.VVEKaart.select('K64'), .setFloor(2); event 'vve:select' op #vve-app en postMessage naar parent (iframe). */
(function(){
'use strict';
var D=window.VVE_DATA; if(!D){console.error('VVE_DATA ontbreekt (laad js/data.js eerst)');return;}
var NS='http://www.w3.org/2000/svg';
var root=document.getElementById('vve-app'); if(!root){root=document.createElement('div');root.id='vve-app';document.body.appendChild(root);}
var base=(root.getAttribute('data-base')||'');
var VB=D.meta.viewbox; // [x,y,w,h]
var state={floor:+(root.getAttribute('data-floor')||1),sel:null,layers:{plan:true,common:true,photos:true,route:true,panden:false,bagpts:false},view:{x:VB[0],y:VB[1],w:VB[2],h:VB[3]}};
var FN={0:'BG',1:'1e',2:'2e',3:'3e',4:'4e'};
function el(tag,attrs,parent,ns){var e=ns?document.createElementNS(NS,tag):document.createElement(tag);if(attrs)for(var k in attrs){if(k==='text')e.textContent=attrs[k];else if(k==='html')e.innerHTML=attrs[k];else e.setAttribute(k,attrs[k]);}if(parent)parent.appendChild(e);return e;}
function sv(tag,attrs,parent){return el(tag,attrs,parent,true);}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function pts(P){return P.map(function(p){return p[0]+','+p[1];}).join(' ');}
function centroid(P){var x=0,y=0;P.forEach(function(p){x+=p[0];y+=p[1];});return[x/P.length,y/P.length];}
function bbox(P){var a=[1e9,1e9,-1e9,-1e9];P.forEach(function(p){a[0]=Math.min(a[0],p[0]);a[1]=Math.min(a[1],p[1]);a[2]=Math.max(a[2],p[0]);a[3]=Math.max(a[3],p[1]);});return a;}
function isLink(s){return /^https?:\/\//.test(s);}
var unitsById={};D.units.forEach(function(u){unitsById[u.id]=u;});
var commonById={};D.common.concat(D.context).forEach(function(c){commonById[c.id]=c;});
var photosById={};D.photos.forEach(function(p){photosById[p.id]=p;});

/* ---------- layout ---------- */
root.innerHTML='';
var top=el('header',{'class':'vve-top'},root);
el('h1',{text:'VvE Van Speijk · Suydersee Veste'},top);
var floorsEl=el('div',{'class':'vve-floors',role:'tablist','aria-label':'Verdieping'},top);
D.meta.floors.forEach(function(f){
  var n=D.units.filter(function(u){return u.floors.indexOf(f.n)>=0;}).length;
  var b=el('button',{role:'tab','data-f':f.n,title:f.titel,html:esc(f.naam)+(n?'<small>'+n+'</small>':'')},floorsEl);
  b.onclick=function(){setFloor(f.n);};
});
var searchWrap=el('div',{'class':'vve-search'},top);
var input=el('input',{type:'search',placeholder:'Zoek huisnummer, straat, index of berging…','aria-label':'Zoeken'},searchWrap);
var results=el('div',{'class':'vve-results'},searchWrap);
var main=el('div',{'class':'vve-main'},root);
var wrap=el('div',{'class':'vve-mapwrap'},main);
var svg=sv('svg',{viewBox:VB.join(' '),preserveAspectRatio:'xMidYMid meet','aria-label':'Plattegrond'},wrap);
var gPlan=sv('g',{},svg),gPand=sv('g',{},svg),gCommon=sv('g',{},svg),gUnits=sv('g',{},svg),gLbl=sv('g',{},svg),gCtx=sv('g',{},svg),gRoute=sv('g',{},svg),gPh=sv('g',{},svg);
var badge=el('div',{'class':'vve-floorbadge'},wrap);
var zoom=el('div',{'class':'vve-zoom'},wrap);
[['+','Inzoomen',function(){zoomBy(1/1.4);}],['−','Uitzoomen',function(){zoomBy(1.4);}],['⤢','Passend maken',function(){resetView();}]].forEach(function(z){var b=el('button',{title:z[1],'aria-label':z[1],text:z[0]},zoom);b.onclick=z[2];});
var legend=el('div',{'class':'vve-legend'},wrap);
var panel=el('aside',{'class':'vve-panel empty'},main);
var foot=el('div',{'class':'vve-foot',html:'Schematisch, op basis van de splitsingstekening (akte 2006) en huisnummerlijst; geen maatvoering. Open data: BAG via PDOK (Kadaster), peildatum '+esc(D.meta.peildatum)+'. Zie data/sources.md.'},root);

/* ---------- legend ---------- */
function buildLegend(){
  legend.innerHTML='';
  var d=el('details',(window.innerWidth>1200?{open:''}:{}),legend); el('summary',{text:'Legenda & lagen'},d);
  [['var(--schans)','Schans (woning)'],['var(--kiel)','De Kiel (woning)'],['#fff','Gestippelde rand = meerlaags (maisonnette)'],['var(--berging)','Bergingen (1e verd.)'],['var(--lift)','Lift / trappenhuis'],['var(--entree)','Entree / hal (BG)'],['var(--dak)','Daktuin / dakpad (geschat)'],['#f1c40f','Galerij'],['#00a0e0','Aldi / winkels (BAG-adrespunt)']].forEach(function(r){
    var row=el('div',{'class':'row'},d); var s=el('span',{'class':'sw'},row); s.style.background=r[0]; if(r[0]==='#fff')s.style.borderStyle='dashed'; el('span',{text:r[1]},row);});
  el('h4',{text:'Lagen'},d);
  [['plan','Ondergrond splitsingstekening'],['common','Gemeenschappelijke ruimten'],['photos','Foto’s (wandeling + GPS)'],['route','Looproute wandeling'],['panden','BAG-pandcontouren'],['bagpts','BAG-adrespunten']].forEach(function(l){
    var lab=el('label',{},d); var cb=el('input',{type:'checkbox'},lab); cb.checked=state.layers[l[0]]; el('span',{text:l[1]},lab);
    cb.onchange=function(){state.layers[l[0]]=cb.checked;render();};});
  var ph=el('div',{'class':'row',html:'<span class="sw" style="background:#1d6fe0;border-radius:50%"></span><span>GPS-foto (cirkel = nauwkeurigheid)</span>'},d);
  el('div',{'class':'row',html:'<span class="sw" style="background:#fff;border:2px solid #c0392b;border-radius:50%"></span><span>Wandelfoto (positie geschat, geen GPS)</span>'},d);
}

/* ---------- view / zoom / pan ---------- */
function applyView(){var v=state.view;svg.setAttribute('viewBox',[v.x,v.y,v.w,v.h].join(' '));}
function resetView(){state.view={x:VB[0],y:VB[1],w:VB[2],h:VB[3]};applyView();}
function svgPoint(cx,cy){var m=svg.getScreenCTM();if(!m)return{x:0,y:0};var p=svg.createSVGPoint();p.x=cx;p.y=cy;return p.matrixTransform(m.inverse());}
function zoomBy(f,cx,cy){var v=state.view;var c=(cx==null)?{x:v.x+v.w/2,y:v.y+v.h/2}:svgPoint(cx,cy);
  var nw=Math.min(Math.max(v.w*f,60),VB[2]*2.5);f=nw/v.w;state.view={x:c.x-(c.x-v.x)*f,y:c.y-(c.y-v.y)*f,w:v.w*f,h:v.h*f};applyView();}
function centerOn(P){var b=bbox(P),cx=(b[0]+b[2])/2,cy=(b[1]+b[3])/2;var w=Math.max(480,(b[2]-b[0])*5),h=w*VB[3]/VB[2];state.view={x:cx-w/2,y:cy-h/2,w:w,h:h};applyView();}
wrap.addEventListener('wheel',function(e){e.preventDefault();zoomBy(e.deltaY>0?1.15:1/1.15,e.clientX,e.clientY);},{passive:false});
var ptrs={},drag=null,moved=false;
wrap.addEventListener('pointerdown',function(e){ptrs[e.pointerId]={x:e.clientX,y:e.clientY};moved=false;
  if(Object.keys(ptrs).length===1){drag={x:e.clientX,y:e.clientY,v:Object.assign({},state.view)};}
  else{drag=null;}});
wrap.addEventListener('pointermove',function(e){if(!ptrs[e.pointerId])return;var prev=ptrs[e.pointerId];ptrs[e.pointerId]={x:e.clientX,y:e.clientY};var ids=Object.keys(ptrs);
  if(ids.length===2){var a=ptrs[ids[0]],b=ptrs[ids[1]];var pa=ids[0]==e.pointerId?prev:a,pb=ids[1]==e.pointerId?prev:b;
    var d0=Math.hypot(pa.x-pb.x,pa.y-pb.y),d1=Math.hypot(a.x-b.x,a.y-b.y);if(d0>0&&d1>0)zoomBy(d0/d1,(a.x+b.x)/2,(a.y+b.y)/2);moved=true;return;}
  if(!drag)return;var dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>4){moved=true;wrap.classList.add('dragging');try{wrap.setPointerCapture(e.pointerId);}catch(_){}}
  if(!moved)return;var m=svg.getScreenCTM();var s=m?m.a:1;state.view.x=drag.v.x-dx/s;state.view.y=drag.v.y-dy/s;applyView();});
function up(e){delete ptrs[e.pointerId];if(!Object.keys(ptrs).length){drag=null;wrap.classList.remove('dragging');}}
wrap.addEventListener('pointerup',up);wrap.addEventListener('pointercancel',up);
// klik op object pas na loslaten zonder slepen
function onTap(node,fn){node.addEventListener('click',function(e){if(moved){e.stopPropagation();return;}e.stopPropagation();fn();});
  node.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();fn();}});node.setAttribute('tabindex','0');}

/* ---------- render ---------- */
function clear(g){while(g.firstChild)g.removeChild(g.firstChild);}
function render(){
  [gPlan,gPand,gCommon,gUnits,gLbl,gCtx,gRoute,gPh].forEach(clear);
  var f=state.floor, F=D.meta.floors.filter(function(x){return x.n===f;})[0];
  Array.prototype.forEach.call(floorsEl.children,function(b){var a=+b.getAttribute('data-f')===f;b.classList.toggle('active',a);b.setAttribute('aria-selected',a);});
  var nU=D.units.filter(function(u){return u.floors.indexOf(f)>=0;});
  badge.textContent=F.titel+' · '+nU.length+' woning'+(nU.length===1?'':'en')+(f===0?' (alleen entrees/gemeenschappelijk; woningen beginnen op 1e)':'');
  if(state.layers.plan){var im=sv('image',{x:VB[0],y:VB[1],width:VB[2],height:VB[3],preserveAspectRatio:'none',opacity:'0.55'},gPlan);im.setAttributeNS('http://www.w3.org/1999/xlink','href',base+F.img);im.setAttribute('href',base+F.img);}
  if(state.layers.panden)D.panden.forEach(function(p){p.rings.forEach(function(r){sv('polygon',{points:pts(r),'class':'pand'+(p.complex?' complex':'')},gPand);});});
  if(state.layers.bagpts)D.units.forEach(function(u){sv('circle',{cx:u.bag_punt_plan[0],cy:u.bag_punt_plan[1],r:3,'class':'bagpt'},gPand);});
  if(state.layers.common){
    D.common.filter(function(c){return c.floor===f;}).forEach(function(c){
      [c.poly].concat(c.extra?[c.extra]:[]).forEach(function(P){var p=sv('polygon',{points:pts(P),'class':'c-poly '+c.type+(state.sel&&state.sel.id===c.id?' sel':''),'aria-label':c.name},gCommon);sv('title',{text:c.name},p);onTap(p,function(){select(c.id);});});
    });
    if(f===0)D.context.forEach(function(c){var g=sv('g',{},gCtx);var p=sv('circle',{cx:c.point[0],cy:c.point[1],r:7,'class':'ctx-pt '+c.type},g);sv('title',{text:c.name},p);sv('text',{x:c.point[0]+10,y:c.point[1]+4,'class':'ctx-lbl',text:c.name},g);onTap(p,function(){select(c.id);});});
  }
  nU.forEach(function(u){
    var P=u.geometry[String(f)];var p=sv('polygon',{points:pts(P),'class':'u-poly '+(u.straat==='Schans'?'schans':'kiel')+(u.meerlaags?' multi':'')+(state.sel&&state.sel.id===u.id?' sel':''),'data-id':u.id,'aria-label':u.adres},gUnits);
    sv('title',{text:u.adres+' · '+u.etages.join(' + ')+' · index '+u.index_nieuw},p);onTap(p,function(){select(u.id);});
    var b=bbox(P),c=centroid(P),w=b[2]-b[0],h=b[3]-b[1];var fs=Math.max(7,Math.min(20,Math.min(w,h)*0.42,w*0.5));
    var t=sv('text',{x:c[0],y:c[1]-(u.meerlaags&&h>26?fs*0.3:0),'class':'u-lbl','font-size':fs.toFixed(1),text:(u.straat==='De Kiel'?'K':'')+u.huisnr},gLbl);
    if(u.meerlaags){sv('text',{x:c[0],y:c[1]+fs*(h>26?0.75:0.9),'class':'u-lbl2','font-size':Math.max(6,fs*0.5).toFixed(1),text:u.etages.join('+')},gLbl);}
  });
  if(state.layers.photos){
    var walk=D.photos.filter(function(p){return p.floor===f&&!p.gps;}).sort(function(a,b){return a.id<b.id?-1:1;});
    if(state.layers.route&&walk.length>1)sv('polyline',{points:pts(walk.map(function(p){return p.point;})),'class':'route'},gRoute);
    D.photos.filter(function(p){return p.floor===f||(p.gps&&f<=1);}).forEach(function(p){
      var g=sv('g',{'class':'ph'+(p.gps?' gps':'')+(state.sel&&state.sel.id===p.id?' sel':'')},gPh);
      if(p.gps&&p.radius_plan)sv('circle',{cx:p.point[0],cy:p.point[1],r:p.radius_plan,'class':'acc'},g);
      if(p.gps&&p.richting_graden!=null){/* kijkrichting: noord in plan = rotatie uit georef */var a=dirToPlan(p.richting_graden);sv('line',{x1:p.point[0],y1:p.point[1],x2:p.point[0]+Math.cos(a)*22,y2:p.point[1]+Math.sin(a)*22,stroke:'#1d6fe0','stroke-width':2.5},g);}
      var c=sv('circle',{cx:p.point[0],cy:p.point[1],r:5,'class':'dot'},g);sv('title',{text:p.id+' – '+p.label+(p.gps?' (GPS)':' (positie geschat)')},c);
      sv('text',{x:p.point[0]+6,y:p.point[1]-5,text:p.gps?'GPS':p.id.split('_')[0]},g);onTap(g,function(){select(p.id);});
    });
  }
  buildPanel();
}
function dirToPlan(deg){/* kompasrichting -> hoek in plan via georef-transformatie */var T=D.meta.georef.transform;var r=deg*Math.PI/180;var dx=Math.sin(r),dy=Math.cos(r);if(T.mirror)dy=-dy;var x=T.zr*dx-T.zi*dy,y=T.zi*dx+T.zr*dy;return Math.atan2(y,x);}

/* ---------- panel ---------- */
function row(k,v){return v==null||v===''?'':'<tr><td>'+esc(k)+'</td><td>'+v+'</td></tr>';}
function srcList(arr){return '<ul>'+arr.map(function(s){var m=s.match(/(https?:\/\/\S+)/);return '<li>'+(m?esc(s.replace(m[1],''))+'<a href="'+esc(m[1])+'" target="_blank" rel="noopener">'+esc(m[1])+'</a>':esc(s))+'</li>';}).join('')+'</ul>';}
function buildPanel(){
  var s=state.sel; panel.classList.toggle('empty',!s);
  if(!s){panel.innerHTML='<h2>Kies een woning</h2><div class="sub">Klik op een woning, gemeenschappelijke ruimte of foto, of zoek op huisnummer.</div>'+summaryHtml();return;}
  var h='<button class="close" aria-label="Sluiten">×</button>';
  if(s.kind==='unit'){var u=s.obj;
    h+='<h2>'+esc(u.adres)+'</h2><div class="sub">'+esc(u.postcode)+' '+esc(u.woonplaats)+' · <span class="chip confirmed">positie bevestigd</span></div><table>'+
      row('Straat',esc(u.straat))+row('Huisnummer',esc(u.huisnr))+
      row('Etage(s)','<span class="floorlinks">'+u.floors.map(function(f){return '<button data-floor="'+f+'">'+FN[f]+'</button>';}).join('')+'</span>'+(u.meerlaags?' maisonnette':''))+
      row('Etage volgens akte',esc(u.etage_akte))+row('Index nieuw / oud',u.index_nieuw+' / '+u.index_oud)+row('Bouwnummer',esc(u.bouwnr))+
      row('Berging','index '+u.berging.index+' (1e verd.) <button data-berging="'+esc(u.berging.blok)+'">toon</button>')+
      row('Oppervlakte (BAG)',u.bag.oppervlakte_m2+' m²')+row('Bouwjaar (BAG)',esc(u.bag.bouwjaar))+row('Gebruiksdoel (BAG)',esc(u.bag.gebruiksdoel))+row('Status (BAG)',esc(u.bag.status))+
      row('BAG-verblijfsobject','<a href="'+esc(u.bag.url)+'" target="_blank" rel="noopener">'+esc(u.bag.verblijfsobject_id)+'</a>')+row('BAG-pand',esc(u.bag.pand_id))+
      row('Coördinaten (WGS84)',u.bag.wgs84.join(', '))+
      row('Energielabel',u.openbaar.energielabel?esc(u.openbaar.energielabel)+' <small>(Huispedia, niet geverifieerd in EP-Online)</small>':'<small>niet gevonden</small>')+
      row('Type (Huispedia)',u.openbaar.soort_huispedia?esc(u.openbaar.soort_huispedia):'')+
      '</table>';
    if(u.notes.length)h+='<h4>Opmerkingen</h4><ul>'+u.notes.map(function(n){return '<li>'+esc(n)+'</li>';}).join('')+'</ul>';
    h+='<h4>Plaatsing</h4><div>'+esc(u.placement_toelichting)+'</div><h4>Bronnen</h4>'+srcList(u.bronnen);
  } else if(s.kind==='common'){var c=s.obj;
    h+='<h2>'+esc(c.name)+'</h2><div class="sub">'+esc(FN[c.floor]||'')+' · <span class="chip '+(c.conf==='confirmed'?'confirmed':'estimated')+'">'+(c.conf==='confirmed'?'op tekening':c.conf==='bag_point'?'BAG-adrespunt':'geschat')+'</span></div>';
    if(c.range){var us=D.units.filter(function(u){return u.berging.index>=c.range[0]&&u.berging.index<=c.range[1];});h+='<h4>Bergingen '+c.range[0]+'–'+c.range[1]+' horen bij</h4><ul>'+us.sort(function(a,b){return a.berging.index-b.berging.index;}).map(function(u){return '<li>'+u.berging.index+' → <a href="#'+u.id+'" data-unit="'+u.id+'">'+esc(u.adres)+'</a></li>';}).join('')+'</ul>';}
    if(c.info)h+='<p>'+esc(c.info)+'</p>'; if(c.bron)h+='<h4>Bron</h4>'+srcList([c.bron]); else h+='<h4>Bron</h4>'+srcList(['Splitsingstekening akte 2006 (index 180 = gemeenschappelijk)']);
  } else if(s.kind==='photo'){var p=s.obj;
    h+='<h2>'+esc(p.id)+'</h2><div class="sub">'+esc(p.label)+' · <span class="chip '+(p.gps?'gps':'estimated')+'">'+esc(p.positie)+'</span></div><img src="'+esc(base+p.file)+'" alt="'+esc(p.label)+'"><table>'+
      row('Verdieping',esc(FN[p.floor]))+row('Tijd',esc(p.tijd))+row('Nauwkeurigheid',esc(p.nauwkeurigheid))+(p.gps?row('GPS',p.lat+', '+p.lon)+row('RD',p.rd.join(', '))+row('Kijkrichting',p.richting_graden+'°'):'')+row('Notitie',esc(p.notitie))+'</table><h4>Bron</h4>'+srcList([p.bron]);
  }
  panel.innerHTML=h;
  panel.querySelector('.close').onclick=function(){state.sel=null;history.replaceState(null,'',location.pathname+location.search);render();};
  Array.prototype.forEach.call(panel.querySelectorAll('[data-floor]'),function(b){b.onclick=function(){setFloor(+b.getAttribute('data-floor'));};});
  Array.prototype.forEach.call(panel.querySelectorAll('[data-berging]'),function(b){b.onclick=function(){select(b.getAttribute('data-berging'));};});
  Array.prototype.forEach.call(panel.querySelectorAll('[data-unit]'),function(a){a.onclick=function(e){e.preventDefault();select(a.getAttribute('data-unit'));};});
}
function summaryHtml(){
  var by={};D.units.forEach(function(u){by[u.straat]=(by[u.straat]||0)+1;});
  var fl=D.meta.floors.map(function(f){return '<tr><td>'+f.titel+'</td><td>'+D.units.filter(function(u){return u.floors.indexOf(f.n)>=0;}).length+'</td></tr>';}).join('');
  return '<table>'+Object.keys(by).map(function(k){return '<tr><td>'+esc(k)+'</td><td>'+by[k]+' woningen</td></tr>';}).join('')+'<tr><td>Totaal</td><td>'+D.units.length+' woningen</td></tr></table><h4>Woningen per verdieping</h4><table>'+fl+'</table><p><small>Maisonnettes tellen mee op elke verdieping die ze beslaan. GPS: '+D.meta.gps.walk_with_gps+' van '+D.meta.gps.walk_photos+' wandelfoto’s had GPS; '+D.meta.gps.images_with_valid_gps_unique+' Twinq-foto’s wel.</small></p>';
}

/* ---------- select / search ---------- */
function select(id,noCenter){
  var u=unitsById[id],c=commonById[id],p=photosById[id];
  if(u){state.sel={kind:'unit',id:id,obj:u};if(u.floors.indexOf(state.floor)<0)state.floor=u.floors[0];}
  else if(c){state.sel={kind:'common',id:id,obj:c};state.floor=c.floor;}
  else if(p){state.sel={kind:'photo',id:id,obj:p};if(!(p.gps&&state.floor<=1))state.floor=p.floor;}
  else return;
  render();
  if(!noCenter){if(u)centerOn(u.geometry[String(state.floor)]);else if(c)centerOn(c.poly||[c.point,[c.point[0]+1,c.point[1]+1]]);else if(p)centerOn([p.point,[p.point[0]+1,p.point[1]+1]]);}
  try{history.replaceState(null,'','#'+id);}catch(_){}
  var det={id:id,kind:state.sel.kind,data:state.sel.obj};
  try{root.dispatchEvent(new CustomEvent('vve:select',{detail:det,bubbles:true}));}catch(_){}
  try{if(window.parent!==window)window.parent.postMessage({type:'vve:select',id:id,kind:det.kind},'*');}catch(_){}
}
function setFloor(f){state.floor=f;if(state.sel&&state.sel.kind==='unit'&&state.sel.obj.floors.indexOf(f)<0){/* selectie blijft bewaard maar is niet zichtbaar */}render();}
function norm(s){return String(s).toLowerCase().replace(/\bde\s+/g,'').replace(/\s+/g,' ').trim();}
function search(q){q=norm(q);if(!q)return[];var out=[];
  var num=(q.match(/\d+/)||[])[0];var str=q.replace(/\d+/g,'').replace(/berging|index|nr\.?/g,'').trim();
  D.units.forEach(function(u){var s=norm(u.straat),score=0;
    if(/berging/.test(q)&&num){if(String(u.berging.index)===num)score=5;}
    else{if(num&&String(u.huisnr)===num)score+=3;if(num&&String(u.index_nieuw)===num)score+=1;if(num&&String(u.huisnr).indexOf(num)===0&&String(u.huisnr)!==num)score+=0.5;
      if(num&&score===0)return;if(str){if(s.indexOf(str)===0||('k'===str&&s==='kiel')||('s'===str&&s==='schans'))score+=(num?2:1);else score=0;}}
    if(score>0)out.push({u:u,score:score});});
  if(!num&&str)D.common.forEach(function(c){if(norm(c.name).indexOf(str)>=0)out.push({c:c,score:0.4});});
  return out.sort(function(a,b){return b.score-a.score||((a.u&&b.u)?a.u.huisnr-b.u.huisnr:0);}).slice(0,30);}
var cur=[],curSel=0;
function showResults(){results.innerHTML='';if(!cur.length){results.style.display=input.value?'block':'none';if(input.value)el('div',{html:'<span>Geen resultaat</span>'},results);return;}
  results.style.display='block';cur.forEach(function(r,i){var d=el('div',{'class':i===curSel?'sel':''},results);
    if(r.u)d.innerHTML='<span>'+esc(r.u.adres)+'</span><small>'+r.u.etages.join('+')+' · idx '+r.u.index_nieuw+' · berging '+r.u.berging.index+'</small>';else d.innerHTML='<span>'+esc(r.c.name)+'</span><small>'+FN[r.c.floor]+'</small>';
    d.onmousedown=function(e){e.preventDefault();pick(r);};});}
function pick(r){results.style.display='none';input.blur();select(r.u?r.u.id:r.c.id);}
input.addEventListener('input',function(){cur=search(input.value);curSel=0;showResults();});
input.addEventListener('keydown',function(e){if(e.key==='ArrowDown'){curSel=Math.min(curSel+1,cur.length-1);showResults();e.preventDefault();}else if(e.key==='ArrowUp'){curSel=Math.max(curSel-1,0);showResults();e.preventDefault();}else if(e.key==='Enter'&&cur[curSel]){pick(cur[curSel]);}else if(e.key==='Escape'){results.style.display='none';}});
input.addEventListener('blur',function(){setTimeout(function(){results.style.display='none';},150);});

/* ---------- init ---------- */
buildLegend();render();
var h0=decodeURIComponent((location.hash||'').slice(1));if(h0)select(h0);
window.addEventListener('hashchange',function(){var h=decodeURIComponent(location.hash.slice(1));if(h&&(!state.sel||state.sel.id!==h))select(h);});
window.VVEKaart={select:select,setFloor:setFloor,data:D,search:search};
})();
