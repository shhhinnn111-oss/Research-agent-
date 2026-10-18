/* ============================================================
   Khyber Pakhtunkhwa Security Atlas — SATP edition
   Vanilla JS + Leaflet. Data: SATP Khyber Pakhtunkhwa datasheets
   (nine datasets, 2000–2026) + optional GTD incident pins.
   ============================================================ */
(() => {
'use strict';

// ---------------------------------------------------------------- constants
const SERIES = [
  {id:'fatalities', name:'Fatalities',            color:'#b3242f', unit:'killed',      axis:'right', key:'total'},
  {id:'incidents',  name:'Terrorism incidents',    color:'#0d6b3f', unit:'incidents',   axis:'left',  key:'incidents'},
  {id:'major',      name:'Major incidents',        color:'#d98a00', unit:'incidents',   axis:'left',  key:'incidents'},
  {id:'suicide',    name:'Suicide attacks',        color:'#6b4bb5', unit:'incidents',   axis:'left',  key:'incidents'},
  {id:'explosions', name:'Explosions',             color:'#e0b400', unit:'incidents',   axis:'left',  key:'incidents'},
  {id:'arrests',    name:'Arrests',                color:'#118a7a', unit:'people',      axis:'left',  key:'arrested'},
  {id:'arms',       name:'Arms recoveries',        color:'#5c8a1f', unit:'recoveries',  axis:'left',  key:'recoveries'},
  {id:'surrender',  name:'Surrenders',             color:'#b03a86', unit:'people',      axis:'left',  key:'surrendered'}
];
const SERIES_BY_ID = Object.fromEntries(SERIES.map(s => [s.id, s]));

const CATS = [
  {id:'ied',      label:'Bomb / IED',      color:'#e07a00'},
  {id:'armed',    label:'Armed assault',   color:'#1c7fb8'},
  {id:'suicide',  label:'Suicide bombing', color:'#c8102e'},
  {id:'targeted', label:'Targeted killing',color:'#a4238a'},
  {id:'rocket',   label:'Rocket / mortar', color:'#c9a200'},
  {id:'kidnap',   label:'Kidnapping',      color:'#7b3fb0'},
  {id:'sabotage', label:'Sabotage',        color:'#4f7d16'},
  {id:'drone',    label:'Drone strike',    color:'#5d6f8c'},
  {id:'other',    label:'Other',           color:'#7f8f86'}
];
const CAT_BY_ID = Object.fromEntries(CATS.map(c => [c.id, c]));

const RAMP = ['#cde3c3','#e8eec2','#f7e29a','#f3c65e','#e99a3f','#d0603a','#9c2530'];
const FATA = new Set(['Bajaur','Khyber','Kurram','Mohmand','North Waziristan','Orakzai','South Waziristan']);
const SATP_ALIAS = {
  'D. I. Khan':'Dera Ismail Khan', 'Battagram':'Batagram', 'Buner':'Buner', 'Tor Ghar':'Tor Ghar',
  'Chitral Lower':'Chitral', 'Chitral Upper':'Chitral',
  'Kohistan Lower':'Kohistan', 'Kohistan Upper':'Kohistan', 'Kolai Palas Kohistan':'Kohistan'
};
const SPLIT_PARENT = new Set(['Chitral Lower','Chitral Upper','Kohistan Lower','Kohistan Upper','Kolai Palas Kohistan']);
const YEARS = Array.from({length:27}, (_,i) => 2000 + i);
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

// ---------------------------------------------------------------- state
const OFFLINE = !!window.__ATLAS__;

const state = {
  satp:null, byYear:{}, districts:[], districtByName:{}, geoFeatures:[], outline:null, neighbours:null,
  gtdStats:null, incidents:[], incidentsLoaded:false, incidentsPromise:null,
  years:new Set(YEARS), spanMode:true, spanEnd:2026, lastYearClick:2026,
  year:2026, allYears:true, series:new Set(['fatalities','incidents','major','suicide']),
  cats:new Set(CATS.map(c=>c.id)), minKilled:0,
  ov:{districts:true, borders:true, fata:true, pins:true, heat:false, neighbours:false},
  shade:'gtd_n',
  tab:'year', district:null, incident:null, search:'',
  playing:false, playTimer:null, server:false, status:null, fetchedAt:null,
  tlCollapsed:false, tlLabels:true,
  fontScale:1, layout:'full'
};

// ---------------------------------------------------------------- utils
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const num = n => (n==null?0:Math.round(n)).toLocaleString('en-US');
const esc = s => String(s==null?'':s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp = (v,a,b) => Math.max(a, Math.min(b, v));
const sum = (arr, f) => arr.reduce((s,x)=>s+(f?f(x):x||0), 0);
const pct = (a,b) => (b ? ((a-b)/b*100) : null);
const signed = v => v>0 ? '+'+v : String(v);
const fmtDate = iso => { const [y,m,d] = iso.split('-'); return +d + ' ' + MONTHS[+m-1] + ' ' + y; };
const shortDate = iso => { const [y,m,d] = iso.split('-'); return +d + ' ' + MONTHS[+m-1] + ' ' + y.slice(2); };
const fmtPct = v => v==null ? '—' : (v>0?'+':'')+v.toFixed(0)+'%';

function toast(msg, ms=3200){
  const t = $('#toast');
  t.textContent = msg; t.hidden = false;
  clearTimeout(t._to); t._to = setTimeout(()=>{ t.hidden = true; }, ms);
}
function debounce(fn, ms){ let t; return (...a)=>{ clearTimeout(t); t = setTimeout(()=>fn(...a), ms); }; }

// ---------------------------------------------------------------- data
function seriesRows(){ return state.satp.province_data; }

function buildYearIndex(){
  const pd = seriesRows();
  const get = (id, y) => (pd[id] || []).find(r => r.year === y) || null;
  state.byYear = {};
  YEARS.forEach(y => {
    state.byYear[y] = {
      year: y,
      fatalities: get('fatalities', y) || {incidents:0,civilians:0,security:0,militants:0,ns:0,total:0},
      incidents:  get('incidents', y)  || {incidents:0},
      major:      get('major', y)      || {incidents:0,killed:0,injured:0},
      suicide:    get('suicide', y)    || {incidents:0,killed:0,injured:0},
      explosions: get('explosions', y) || {incidents:0,killed:0,injured:0},
      arrests:    get('arrests', y)    || {incidents:0,arrested:0},
      arms:       get('arms', y)       || {recoveries:0},
      surrender:  get('surrender', y)  || {incidents:0,surrendered:0}
    };
  });
}

/** the years currently selected, ascending */
function selectedYears(){ return YEARS.filter(y => state.years.has(y)); }
function isContiguous(){ const ys = selectedYears(); return ys.length > 0 && ys[ys.length-1] - ys[0] + 1 === ys.length; }
function selectionIsAll(){ return state.years.size === YEARS.length; }

/** short label for a selection: 2015 · 2000–26 · 9 years · 2009, 2014… */
function selLabel(){
  const ys = selectedYears();
  if(!ys.length) return 'no years';
  if(ys.length === YEARS.length) return '2000–2026';
  if(ys.length === 1) return String(ys[0]);
  if(isContiguous()) return ys[0] + '–' + String(ys[ys.length-1]).slice(2);
  return ys.length + ' years';
}

/** longer label used in the header and the legend */
function selLong(){
  const ys = selectedYears();
  if(!ys.length) return 'no years selected';
  if(ys.length === YEARS.length) return 'all years · 2000–2026';
  if(ys.length === 1) return String(ys[0]);
  if(isContiguous()) return ys[0] + '–' + ys[ys.length-1];
  if(ys.length <= 4) return ys.join(', ');
  return ys.length + ' years · ' + ys[0] + ' to ' + ys[ys.length-1];
}

/** rows for the current selection */
function periodRows(){ return selectedYears().map(y => state.byYear[y]); }

function periodTotals(){
  const rows = periodRows();
  const t = {
    fatalities:{total:0,civilians:0,security:0,militants:0,ns:0,incidents:0},
    incidents:0, major:{incidents:0,killed:0,injured:0}, suicide:{incidents:0,killed:0},
    explosions:{incidents:0,killed:0}, arrests:{arrested:0,incidents:0},
    arms:{recoveries:0}, surrender:{surrendered:0,incidents:0}
  };
  rows.forEach(r => {
    for(const k of ['total','civilians','security','militants','ns','incidents']) t.fatalities[k] += r.fatalities[k]||0;
    t.incidents += r.incidents.incidents||0;
    t.major.incidents += r.major.incidents||0; t.major.killed += r.major.killed||0; t.major.injured += r.major.injured||0;
    t.suicide.incidents += r.suicide.incidents||0; t.suicide.killed += r.suicide.killed||0;
    t.explosions.incidents += r.explosions.incidents||0; t.explosions.killed += r.explosions.killed||0;
    t.arrests.arrested += r.arrests.arrested||0; t.arrests.incidents += r.arrests.incidents||0;
    t.arms.recoveries += r.arms.recoveries||0;
    t.surrender.surrendered += r.surrender.surrendered||0; t.surrender.incidents += r.surrender.incidents||0;
  });
  return t;
}

function seriesValue(id, row){
  if(!row) return 0;
  switch(id){
    case 'fatalities': return row.fatalities.total;
    case 'incidents':  return row.incidents.incidents;
    case 'major':      return row.major.incidents;
    case 'suicide':    return row.suicide.incidents;
    case 'explosions': return row.explosions.incidents;
    case 'arrests':    return row.arrests.arrested;
    case 'arms':       return row.arms.recoveries;
    case 'surrender':  return row.surrender.surrendered;
    default: return 0;
  }
}

// ---------------------------------------------------------------- district values
function gtdDistrictValue(name, field){
  const d = state.gtdStats && state.gtdStats[name];
  if(!d) return 0;
  let v = 0;
  for(const y of Object.keys(d)){
    if(!state.years.has(+y)) continue;
    const row = d[y] || {};
    v += (field === 'n' ? row.n : field === 'k' ? row.k : row.j) || 0;
  }
  return v;
}

function satpDistrictRow(name, year){
  const districts = state.satp.districts || {};
  const key = SATP_ALIAS[name] || name;
  const rec = districts[key];
  if(!rec || !rec.fatalities) return null;
  return rec.fatalities.find(r => r.year === year) || null;
}

function satpDistrictAgg(name){
  const key = SATP_ALIAS[name] || name;
  const rec = (state.satp.districts || {})[key];
  if(!rec || !rec.fatalities) return null;
  const rows = rec.fatalities.filter(r => state.years.has(r.year));
  return {
    total: sum(rows, r=>r.total), civilians: sum(rows, r=>r.civilians),
    security: sum(rows, r=>r.security), militants: sum(rows, r=>r.militants),
    incidents: sum(rows, r=>r.incidents), years: rows.length
  };
}

function hasSatpDistricts(){ return Object.keys(state.satp.districts || {}).length > 0; }

function districtValue(name){
  if(state.shade.startsWith('satp') && hasSatpDistricts()){
    const a = satpDistrictAgg(name);
    if(!a) return null;
    return state.shade === 'satp_civ' ? a.civilians
      : state.shade === 'satp_sf' ? a.security
      : state.shade === 'satp_mil' ? a.militants
      : state.shade === 'satp_inc' ? a.incidents : a.total;
  }
  const field = state.shade === 'gtd_k' ? 'k' : 'n';
  return gtdDistrictValue(name, field);
}

function shadeInfo(){
  const satp = state.shade.startsWith('satp');
  const usingSatp = satp && hasSatpDistricts();
  const labels = {
    satp_total:'SATP fatalities', satp_civ:'SATP civilians killed', satp_sf:'SATP security forces killed',
    satp_mil:'SATP militants killed', satp_inc:'SATP incidents of killing',
    gtd_n:'GTD incidents', gtd_k:'GTD fatalities'
  };
  if(satp && !usingSatp){
    return { label:'GTD incidents', source:'GTD incident record', usingSatp:false, pending:true };
  }
  return {
    label: labels[state.shade] || 'Intensity',
    source: usingSatp ? 'SATP district datasheets' : 'GTD incident record',
    usingSatp,
    pending: false
  };
}

// ---------------------------------------------------------------- map
let map, dLayer, fataLayer, labelLayer, pinLayer, heatLayer, neighbourLayer, vectorLayer, baseLayers = {}, currentBase = 'google';
let districtRenderer, overlayRenderer;
let tileErr = 0, hatchDefs = null;

function creditFor(key){
  return {
    google:'Basemap © Google · Map data © Google', googleSat:'Imagery © Google', googleHybrid:'Imagery © Google',
    googleTerrain:'Basemap © Google', cartoLight:'© OpenStreetMap · © CARTO', cartoDark:'© OpenStreetMap · © CARTO',
    osm:'© OpenStreetMap contributors', vector:'Offline vector basemap'
  }[key] || '';
}

function googleLayer(lyrs, label){
  return L.tileLayer('https://mt{s}.google.com/vt/lyrs=' + lyrs + '&x={x}&y={y}&z={z}&hl=en', {
    subdomains:['0','1','2','3'], maxZoom:20, attribution:'© Google', label
  });
}

function initMap(){
  map = L.map('map', {
    zoomControl:false, minZoom:6, maxZoom:15, preferCanvas:false,
    maxBounds:[[28.5,61.5],[39.5,79.5]], maxBoundsViscosity:.25, zoomSnap:.25
  });
  map.attributionControl.setPrefix(false);
  L.control.zoom({position:'topright'}).addTo(map);

  baseLayers = {
    google: googleLayer('m'),
    googleSat: googleLayer('s'),
    googleHybrid: googleLayer('y'),
    googleTerrain: googleLayer('p'),
    cartoLight: L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:19,attribution:'© OpenStreetMap · © CARTO'}),
    cartoDark: L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{subdomains:'abcd',maxZoom:19,attribution:'© OpenStreetMap · © CARTO'}),
    osm: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap contributors'})
  };
  Object.values(baseLayers).forEach(l => l.on('tileerror', onTileError));

  districtRenderer = L.svg({padding:.45});
  overlayRenderer = L.svg({padding:.45});

  vectorLayer = makeVectorLayer();
  if(vectorLayer) baseLayers.vector = vectorLayer; else {
    const opt = $('#basemap option[value="vector"]'); if(opt) opt.remove();
  }
  setBasemap(!!window.__ATLAS__ && vectorLayer ? 'vector' : 'google');

  // neighbouring regions (optional, under the province)
  if(state.neighbours){
    neighbourLayer = L.geoJSON(state.neighbours, {
      style:{color:'#a9c3a8', weight:1, fillColor:'#e4eee0', fillOpacity:.6, dashArray:'2 4'},
      interactive:false
    });
    if(state.ov.neighbours) neighbourLayer.addTo(map);
  }

  if(state.outline){
    L.geoJSON(state.outline, {style:{color:'#0d6b3f', weight:2.4, opacity:.75, fill:false}, interactive:false}).addTo(map);
  }

  buildDistrictLayer();
  buildFataLayer();

  labelLayer = L.layerGroup().addTo(map);
  pinLayer = L.layerGroup();
  map.on('zoomend', ()=>{ renderLabels(); if(state.ov.heat) buildHeat(); });
  map.on('moveend', debounce(()=>renderLabels(), 80));
  try{ map.fitBounds(L.geoJSON(state.outline).getBounds(), {padding:[24,24]}); }catch(e){ map.setView([34.2,71.6],7); }
}

function outlineGeom(){
  if(!state.outline) return null;
  return state.outline.type === 'FeatureCollection' ? (state.outline.features[0] || {}).geometry : state.outline.geometry;
}

function buildDistrictLayer(){
  if(dLayer) map.removeLayer(dLayer);
  dLayer = L.geoJSON({type:'FeatureCollection', features:state.geoFeatures}, {
    renderer:districtRenderer,
    style:styleDistrict,
    onEachFeature:(f, layer)=>{
      layer.on('click', ()=>{ layer.bringToFront(); selectDistrict(f.properties.name); });
      layer.on('add', ()=>{ if(layer._path) layer._path.style.cursor = 'pointer'; });
      layer.bindTooltip(()=>districtTooltip(f.properties.name), {sticky:true, direction:'top', opacity:1});
      layer.on('mouseout', ()=>layer.closeTooltip());
    }
  });
  if(state.ov.districts) dLayer.addTo(map);
}

function buildFataLayer(){
  if(fataLayer){ map.removeLayer(fataLayer); fataLayer = null; }
  const feats = state.geoFeatures.filter(f => FATA.has(f.properties.name));
  if(!feats.length) return;
  fataLayer = L.geoJSON({type:'FeatureCollection', features:feats}, {
    renderer:overlayRenderer, interactive:false,
    style:{fillColor:'#ffffff', fillOpacity:.001, color:'none'}
  });
  fataLayer.eachLayer(l => {
    l.on('add', ()=>{
      if(!l._path) return;
      injectHatch();
      l._path.setAttribute('fill', 'url(#fataHatch)');
      l._path.setAttribute('fill-opacity', '.38');
      l._path.setAttribute('stroke', 'none');
      l._path.style.pointerEvents = 'none';
    });
  });
  if(state.ov.fata) fataLayer.addTo(map);
}

function injectHatch(){
  if(hatchDefs) return;
  const svg = overlayRenderer && overlayRenderer._container;
  if(!svg) return;
  hatchDefs = document.createElementNS('http://www.w3.org/2000/svg','defs');
  hatchDefs.innerHTML = '<pattern id="fataHatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(38)">' +
    '<rect width="7" height="7" fill="none"></rect>' +
    '<line x1="0" y1="0" x2="0" y2="7" stroke="#0d6b3f" stroke-width="1.15" stroke-opacity=".42"></line></pattern>';
  svg.appendChild(hatchDefs);
}

function styleDistrict(f){
  const p = f.properties;
  const v = districtValue(p.name);
  const idx = v == null ? 0 : binIndex(v, classBreaks().breaks);
  const selected = state.district === p.name;
  const base = RAMP[idx] || RAMP[0];
  return {
    fillColor: base,
    fillOpacity: v == null ? .18 : (selected ? .82 : .7),
    color: selected ? '#d92332' : (FATA.has(p.name) ? 'rgba(13,107,63,.55)' : 'rgba(13,107,63,.32)'),
    weight: selected ? 2 : (FATA.has(p.name) ? 1.3 : 1),
    dashArray: selected ? null : (FATA.has(p.name) ? '4 4' : null)
  };
}

function binIndex(v, edges){
  for(let i = edges.length - 1; i >= 0; i--){ if(v >= edges[i]) return i; }
  return 0;
}

let _breaks = null, _breaksKey = '';
function classBreaks(){
  const key = selectedYears().join(',') + '|' + state.shade + '|' + hasSatpDistricts();
  if(_breaks && _breaksKey === key) return _breaks;
  const vals = state.districts.map(p => districtValue(p.name)).filter(v => v != null && v > 0).sort((a,b)=>a-b);
  let breaks;
  if(!vals.length){
    breaks = [0,1,5,20,60,150,400];
  }else{
    const at = q => vals[clamp(Math.floor(q*(vals.length-1)),0,vals.length-1)];
    breaks = [0, at(.2), at(.4), at(.6), at(.78), at(.91), at(.985)];
    // make strictly increasing
    for(let i=1;i<breaks.length;i++) if(breaks[i] <= breaks[i-1]) breaks[i] = breaks[i-1] + 1;
  }
  const fmt = v => v >= 1000 ? (v/1000>=10 ? Math.round(v/1000)+'k' : (v/1000).toFixed(1)+'k') : String(Math.round(v));
  const labels = [];
  for(let i=0;i<7;i++){
    if(i === 0) labels.push('≤ '+fmt(breaks[1]));
    else if(i === 6) labels.push(fmt(breaks[6])+'+');
    else labels.push(fmt(breaks[i])+'–'+fmt(breaks[i+1]));
  }
  _breaks = {breaks, labels};
  _breaksKey = key;
  return _breaks;
}

function districtTooltip(name){
  const p = state.districtByName[name];
  const satp = satpDistrictAgg(name);
  const gtdN = gtdDistrictValue(name,'n');
  const a = selLabel();
  const rows = [
    ['Period', a],
    ['GTD incidents', num(gtdN)]
  ];
  if(satp) rows.splice(1,0,['SATP killed', num(satp.total)],['SATP incidents', num(satp.incidents)]);
  return '<div style="min-width:160px">' +
    '<div style="font-size:.72rem;font-weight:700">' + esc(p.display) + (FATA.has(name)?' · FATA':'') + '</div>' +
    '<div style="font-size:.5rem;letter-spacing:.09em;text-transform:uppercase;color:#7f978a;margin:.1rem 0 .3rem">' + esc(p.division) + ' Division · HQ ' + esc(p.hq) + '</div>' +
    rows.map(r => '<div style="display:flex;justify-content:space-between;gap:.8rem;font-size:.62rem;color:#2b4635"><span>' + r[0] + '</span><b style="color:#0d6b3f">' + r[1] + '</b></div>').join('') +
    '<div style="font-size:.52rem;color:#7f978a;margin-top:.2rem">' + esc(shadeInfo().label) + ': <b style="color:#10281a">' + (districtValue(name)==null?'no data':num(districtValue(name))) + '</b></div>' +
    '</div>';
}

// ---------------------------------------------------------------- district labels
function renderLabels(){
  if(!labelLayer) return;
  labelLayer.clearLayers();
  if(!state.ov.borders) return;
  const z = map.getZoom();
  if(z < 5.6) return;
  const breaks = classBreaks();
  const placed = [];
  const items = state.districts.map(p => {
    const v = districtValue(p.name);
    return {p, v, pt:map.latLngToContainerPoint([p.cy, p.cx])};
  }).sort((a,b)=>(b.v||0)-(a.v||0));
  const size = map.getSize();
  for(const it of items){
    if(it.pt.x < -30 || it.pt.y < -20 || it.pt.x > size.x + 30 || it.pt.y > size.y + 20) continue;
    if(it.v == null && z < 8) continue;
    if(it.v === 0 && z < 7.5) continue;
    const w = Math.max(46, String(it.p.display).length * 5.4), h = 24;
    const box = {x:it.pt.x - w/2, y:it.pt.y - h/2, w, h};
    if(placed.some(b => !(box.x+box.w < b.x || box.x > b.x+b.w || box.y+box.h < b.y || box.y > b.y+b.h))) continue;
    placed.push(box);
    const idx = it.v == null ? 0 : binIndex(it.v, breaks.breaks);
    const val = it.v == null ? '—' : num(it.v);
    const selected = state.district === it.p.name;
    const icon = L.divIcon({
      className:'district-label' + (idx <= 1 ? ' dim' : '') + (selected ? ' sel' : ''),
      html: '<span>' + esc(it.p.display) + (selected ? ' <i class="selected-tag">selected</i>' : '') + '</span><span class="v">' + val + '</span>',
      iconSize:[w, h], iconAnchor:[w/2, h/2]
    });
    L.marker([it.p.cy, it.p.cx], {icon, interactive:false, keyboard:false}).addTo(labelLayer);
  }
}

// ---------------------------------------------------------------- pins / heat
function loadIncidents(){
  if(state.incidentsPromise) return state.incidentsPromise;
  state.incidentsPromise = (async () => {
    if(window.__ATLAS__ && window.__ATLAS__.incidents){
      state.incidents = window.__ATLAS__.incidents;
    }else{
      const r = await fetch('data/incidents.json');
      state.incidents = await r.json();
    }
    state.incidentsLoaded = true;
    return state.incidents;
  })();
  return state.incidentsPromise;
}

function filteredIncidents(){
  const wide = state.years.size > 6;
  const list = state.incidents.filter(i => {
    if(!state.years.has(i.year)) return false;
    if(!state.cats.has(i.cat)) return false;
    if(i.killed < state.minKilled) return false;
    if(wide && i.killed < 5) return false;   // keep a many-year view light
    return true;
  });
  if(state.search.trim()){
    const q = state.search.trim().toLowerCase();
    return list.filter(i => (i.place+' '+i.district+' '+i.summary+' '+i.actor).toLowerCase().includes(q));
  }
  return list;
}

function buildPins(){
  if(!pinLayer) return;
  pinLayer.clearLayers();
  if(!state.ov.pins) { if(map.hasLayer(pinLayer)) map.removeLayer(pinLayer); return; }
  if(!state.incidentsLoaded) return;
  const list = filteredIncidents();
  for(const i of list){
    const r = clamp(2.6 + Math.sqrt(i.killed) * 1.45, 2.4, 15);
    const c = (CAT_BY_ID[i.cat] || CAT_BY_ID.other).color;
    const mk = L.circleMarker([i.lat, i.lng], {
      radius:r, color:'rgba(16,40,26,.75)', weight:i.killed>=10?1.6:.9,
      fillColor:c, fillOpacity:.9, renderer:overlayRenderer
    });
    mk.bindTooltip('<b>' + esc(i.place || i.district) + '</b> · ' + shortDate(i.date) +
      '<br><span style="color:' + c + '">' + esc((CAT_BY_ID[i.cat]||CAT_BY_ID.other).label) + '</span>' +
      '<div style="color:#5c7767;font-size:.55rem;margin-top:.12rem">' + num(i.killed) + ' killed · ' + num(i.injured) + ' injured</div>',
      {direction:'top', opacity:1});
    mk.on('click', e => { L.DomEvent.stopPropagation(e); state.incident = i.id; setTab('incidents'); });
    mk._inc = i;
    pinLayer.addLayer(mk);
  }
  if(!map.hasLayer(pinLayer)) pinLayer.addTo(map);
}

function buildHeat(){
  if(!state.incidentsLoaded) return;
  const probe = document.createElement('canvas');
  if(!probe.getContext || !probe.getContext('2d')) return;
  if(!state.ov.heat){ if(heatLayer) map.removeLayer(heatLayer); return; }
  const pts = filteredIncidents().map(i => [i.lat, i.lng, clamp((i.killed + i.injured/3) / 20, .15, 1)]);
  if(heatLayer) map.removeLayer(heatLayer);
  heatLayer = L.heatLayer(pts, {radius:22, blur:19, maxZoom:11, minOpacity:.22,
    gradient:{.15:'#7fc4a0',.35:'#ffd23f',.55:'#f2a93b',.75:'#e0632f',1:'#b3242f'}}).addTo(map);
}

// ---------------------------------------------------------------- vector basemap (offline)
function makeVectorLayer(){
  if(!state.outline) return null;
  const W = L.GridLayer.extend({
    createTile(coords){
      const size = this.getTileSize();
      const tile = document.createElement('canvas');
      tile.width = size.x; tile.height = size.y;
      const ctx = tile.getContext('2d');
      if(!ctx) return tile;
      const b = this._tileCoordsToBounds(coords);
      const origin = map.project(b.getNorthWest(), coords.z);
      const P = (lng,lat) => map.project([lat,lng],coords.z).subtract(origin);
      ctx.fillStyle = '#eef5ea'; ctx.fillRect(0,0,size.x,size.y);
      const draw = (geom) => {
        if(!geom) return;
        const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.type === 'MultiPolygon' ? geom.coordinates : [];
        polys.forEach(poly => poly.forEach(ring => {
          ctx.beginPath();
          ring.forEach((c,idx) => { const p = P(c[0],c[1]); idx ? ctx.lineTo(p.x,p.y) : ctx.moveTo(p.x,p.y); });
          ctx.closePath();
        }));
      };
      if(state.neighbours){
        ctx.fillStyle = '#e2ecdd'; ctx.strokeStyle = '#cfe0c9'; ctx.lineWidth = 1;
        state.neighbours.features.forEach(f => { draw(f.geometry); ctx.fill(); ctx.stroke(); });
      }
      const og = outlineGeom();
      ctx.fillStyle = '#f7fbf3'; draw(og); ctx.fill();
      ctx.strokeStyle = 'rgba(13,107,63,.45)'; ctx.lineWidth = 1.4; draw(og); ctx.stroke();
      ctx.fillStyle = 'rgba(92,119,103,.75)'; ctx.font = '9px Candara, Segoe UI, sans-serif';
      for(let lon = Math.ceil(b.getWest()); lon <= b.getEast(); lon++){
        const a = P(lon, b.getNorth());
        if(a.x > 4 && a.x < size.x - 30) ctx.fillText(Math.abs(lon)+'°E', a.x+3, 11);
      }
      return tile;
    }
  });
  return new W({noWrap:true, maxZoom:14, attribution:'Offline vector basemap'});
}

function onTileError(){
  if(currentBase === 'vector') return;
  tileErr++;
  if(tileErr === 6 && currentBase.startsWith('google')){
    toast('Google tiles are unreachable — switched to OpenStreetMap.');
    setBasemap('osm');
  }
}
function setBasemap(key){
  if(OFFLINE && key !== 'vector' && !state.warnedTiles){
    state.warnedTiles = true;
    setTimeout(() => toast('This is the offline edition — network basemaps need a connection. The drawn vector basemap is always available.'), 400);
  }
  if(!baseLayers[key]) return;
  if(baseLayers[currentBase]) map.removeLayer(baseLayers[currentBase]);
  currentBase = key; tileErr = 0;
  baseLayers[key].addTo(map);
  document.body.classList.toggle('basemap-dark', key === 'cartoDark');
  const sel = $('#basemap'); if(sel) sel.value = key;
  const cr = $('#credit'); if(cr) cr.textContent = creditFor(key);
}

// ---------------------------------------------------------------- legend
function renderLegend(){
  const info = shadeInfo();
  const {breaks, labels} = classBreaks();
  $('#lgTitle').textContent = info.label;
  $('#lgClasses').innerHTML = labels.map((l,i) =>
    '<span class="lg-class' + (i===0?' zero':'') + '"><i style="background:' + RAMP[i] + '"></i>' + esc(l) + '</span>'
  ).join('');
  $('#lgSource').textContent = info.usingSatp ? 'SATP · districts' : 'GTD · districts';
  $('#lgNote').textContent = info.pending
    ? 'SATP district series not synced yet — showing the GTD incident record'
    : selLong();
  const tag = $('#mapTag');
  tag.textContent = info.label + ' · ' + selLabel() + ' · ' + info.source;
}

// ---------------------------------------------------------------- header
function renderHeader(){
  const t = periodTotals();
  $('#hsIncidents').textContent = num(t.incidents);
  $('#hsIncidentsLab').textContent = 'incidents · ' + selLabel();
  $('#hsKilled').textContent = num(t.fatalities.total);
  $('#hsCiv').textContent = num(t.fatalities.civilians);
  $('#hsSec').textContent = num(t.fatalities.security);
  $('#hsMil').textContent = num(t.fatalities.militants);
}

// ---------------------------------------------------------------- timeline
let tlTip = null;
function renderTimeline(){
  const host = $('#tlChart');
  if(!host) return;
  const rows = YEARS.map(y => state.byYear[y]);
  const enabled = SERIES.filter(s => state.series.has(s.id));
  const counts = enabled.filter(s => s.axis === 'left');
  const fat = state.series.has('fatalities');

  const W = Math.max(560, host.clientWidth || 900);
  const H = state.tlCollapsed ? 0 : (host.clientHeight || 132);
  if(H <= 0) return;
  const M = {l:34, r:fat?44:12, t:8, b:16};
  const pw = W - M.l - M.r, ph = H - M.t - M.b;
  const bw = pw / rows.length;
  const maxL = Math.max(50, ...counts.map(s => Math.max(...rows.map(r => seriesValue(s.id, r)))));
  const maxR = Math.max(50, ...rows.map(r => r.fatalities.total));
  const fx0 = () => M.l + (selectedYears()[0] - 2000) * bw;
  const fx1 = () => { const ys = selectedYears(); return (ys[ys.length-1] - ys[0] + 1) * bw; };
  const x = y => M.l + (y - 2000 + .5) * bw;
  const yL = v => M.t + ph - (v / maxL) * ph;
  const yR = v => M.t + ph - (v / maxR) * ph;

  let s = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" role="img" aria-label="Yearly record">';
  // gridlines
  for(let i=0;i<=3;i++){
    const gy = M.t + ph * i / 3;
    s += '<line class="tl-grid" x1="' + M.l + '" y1="' + gy + '" x2="' + (W-M.r) + '" y2="' + gy + '"/>';
    s += '<text class="tl-axis" x="' + (M.l-4) + '" y="' + (gy+3) + '" text-anchor="end">' + compact(maxL*(3-i)/3) + '</text>';
    if(fat) s += '<text class="tl-axis" x="' + (W-M.r+5) + '" y="' + (gy+3) + '">' + compact(maxR*(3-i)/3) + '</text>';
  }
  // the selected years sit on a yellow band
  if(state.years.size < YEARS.length){
    rows.forEach((r,i) => {
      if(!state.years.has(r.year)) return;
      s += '<rect class="tl-focus" x="' + (M.l + i*bw) + '" y="' + M.t + '" width="' + bw + '" height="' + ph + '"/>';
    });
    s += '<rect x="' + (fx0()) + '" y="' + (M.t-4) + '" width="' + (fx1()) + '" height="2" rx="1" fill="#d9ad12"/>';
  }

  // bars: terrorism incidents
  if(state.series.has('incidents')){
    rows.forEach((r,i) => {
      const h = (r.incidents.incidents / maxL) * ph;
      s += '<rect class="tl-bar' + (state.years.has(r.year) ? ' on' : '') + '" x="' + (M.l + i*bw + Math.min(2, bw*.12)) + '" y="' + (M.t+ph-h) +
        '" width="' + Math.max(1, bw - Math.min(4, bw*.24)) + '" height="' + Math.max(1,h) + '" rx="' + Math.min(1.5,bw/6) +
        '" data-y="' + r.year + '"><title>' + r.year + ': ' + num(r.incidents.incidents) + ' incidents</title></rect>';
    });
  }
  // lines
  enabled.forEach(se => {
    if(se.id === 'incidents') return;
    const isFat = se.id === 'fatalities';
    let d = '';
    rows.forEach((r,i) => {
      const v = seriesValue(se.id, r);
      const px = x(r.year), py = isFat ? yR(v) : yL(v);
      d += (i ? 'L' : 'M') + px.toFixed(1) + ' ' + py.toFixed(1);
    });
    s += '<path d="' + d + '" fill="none" stroke="' + se.color + '" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"' +
      (se.id === 'arrests' || se.id === 'arms' || se.id === 'surrender' ? ' stroke-dasharray="3 2"' : '') + '/>';
    rows.forEach((r,i) => {
      const v = seriesValue(se.id, r);
      if(!state.tlLabels) return;
      if(v === Math.max(...rows.map(k => seriesValue(se.id,k))) && v > 0){
        const py = isFat ? yR(v) : yL(v);
        s += '<circle cx="' + x(r.year) + '" cy="' + py + '" r="2.4" fill="' + se.color + '"/>';
      }
    });
  });
  // year ticks
  rows.forEach((r,i) => {
    if(r.year % 2 === 0 || r.year === state.year)
      s += '<text class="tl-axis" x="' + x(r.year) + '" y="' + (H-4) + '" text-anchor="middle" fill="' + (state.years.has(r.year)?'#0d6b3f':'#9aae9f') + '">' + (r.year % (bw<17?4:2) === 0 ? "'" + String(r.year).slice(2) : '') + '</text>';
    s += '<rect class="tl-year-hit" data-y="' + r.year + '" x="' + (M.l + i*bw) + '" y="' + M.t + '" width="' + bw + '" height="' + ph + '"/>';
  });
  s += '</svg>';
  host.innerHTML = s;

  host.querySelectorAll('.tl-year-hit').forEach(el => {
    el.addEventListener('click', e => { toggleYear(+el.dataset.y, e.shiftKey); });
    el.addEventListener('mouseenter', () => showTip(+el.dataset.y, host));
    el.addEventListener('mousemove', e => moveTip(e, host));
    el.addEventListener('mouseleave', hideTip);
  });
}

function compact(v){
  if(v >= 1e6) return (v/1e6).toFixed(1)+'M';
  if(v >= 1e3) return (v/1e3 >= 10 ? Math.round(v/1e3)+'k' : (v/1e3).toFixed(1)+'k');
  return String(Math.round(v));
}

function showTip(year, host){
  const r = state.byYear[year];
  if(!r) return;
  if(!tlTip){ tlTip = document.createElement('div'); tlTip.className = 'tl-tip'; }
  tlTip.innerHTML = '<b>' + year + (state.years.has(year) ? ' ✓' : '') + '</b>' + SERIES.filter(s=>state.series.has(s.id)).map(s =>
    '<div class="r"><span>' + s.name + '</span><span>' + num(seriesValue(s.id, r)) + '</span></div>'
  ).join('');
  host.appendChild(tlTip);
  tlTip.hidden = false;
}
function moveTip(e, host){
  if(!tlTip) return;
  const rect = host.getBoundingClientRect();
  tlTip.style.left = (e.clientX - rect.left) + 'px';
  tlTip.style.top = (e.clientY - rect.top - 6) + 'px';
}
function hideTip(){ if(tlTip) tlTip.hidden = true; }

// ---------------------------------------------------------------- inspector
function setTab(tab){
  state.tab = tab;
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  renderInspector();
  if(window.innerWidth <= 1240) document.body.classList.add('insp-open');
}

function renderInspector(){
  const el = $('#inspBody');
  if(state.tab === 'district') return renderDistrictTab(el);
  if(state.tab === 'incidents') return renderIncidentsTab(el);
  if(state.tab === 'sources') return renderSourcesTab(el);
  return renderYearTab(el);
}

function delta(cur, prev){
  if(prev == null || prev === 0) return {txt:'—', cls:'flat'};
  const p = (cur - prev) / prev * 100;
  return {txt: fmtPct(p) + ' vs ' + (state.year-1), cls: p > 0 ? 'up' : p < -1 ? 'down' : 'flat'};
}

function renderYearTab(el){
  const t = periodTotals();
  const single = state.years.size === 1;
  const prev = single ? state.byYear[state.year-1] : null;
  const dK = single ? delta(t.fatalities.total, prev ? prev.fatalities.total : null) : null;
  const dC = single ? delta(t.fatalities.civilians, prev ? prev.fatalities.civilians : null) : null;
  const dS = single ? delta(t.fatalities.security, prev ? prev.fatalities.security : null) : null;
  const dM = single ? delta(t.fatalities.militants, prev ? prev.fatalities.militants : null) : null;

  el.innerHTML =
    '<div class="kicker">' + (single ? 'Year in review' : 'Cumulative record') + '</div>' +
    '<div class="h2">' + esc(selLong()) + '</div>' +
    '<div class="sub">' + (single ? 'single year · SATP datasheets' : state.years.size + ' of 27 years · SATP datasheets') + '</div>' +
    '<div class="kpi-grid" style="margin-top:12px">' +
      kpi('Killed', t.fatalities.total, dK) +
      kpi('Civilians', t.fatalities.civilians, dC) +
      kpi('Security forces', t.fatalities.security, dS) +
      kpi('Militants', t.fatalities.militants, dM) +
    '</div>' +
    '<div class="section"><div class="section-head"><h3>Year matrix</h3><span class="sub">click any cell</span></div>' +
      renderMatrix() + '</div>' +
    '<div class="section"><div class="section-head"><h3>Datasets</h3><span class="sub">' + (single ? 'this year' : 'selected span') + '</span></div>' +
      renderSeriesTable(t) + '</div>' +
    (state.series.has('suicide') || state.series.has('explosions')
      ? '<div class="section"><div class="section-head"><h3>Who was killed</h3><span class="sub">attack type · ' + (single?'year':'span') + '</span></div>' + renderVictimSplit(t) + '</div>'
      : '') +
    '<div class="section"><div class="section-head"><h3>Reading this</h3></div>' +
      '<div class="note">SATP counts militants killed in security operations inside the fatality total, so the bars and the fatality line move apart sharply in years of heavy operations (2009, 2015, 2025). The atlas reports them separately rather than merging them.</div></div>';
  $$('#inspBody .matrix [data-y]').forEach(cell => cell.addEventListener('click', e => toggleYear(+cell.dataset.y, e.shiftKey)));
}

function kpi(label, value, d){
  return '<div class="kpi"><div class="v">' + num(value) + '</div><div class="l">' + label + '</div>' +
    (d ? '<div class="d ' + d.cls + '">' + d.txt + '</div>' : '') + '</div>';
}

function renderMatrix(){
  const rows = SERIES.filter(s => state.series.has(s.id));
  if(!rows.length) return '<div class="empty">No series selected. Turn one on in the left rail.</div>';
  let html = '<div class="matrix-wrap"><table class="matrix"><thead><tr><th></th>';
  YEARS.forEach(y => { html += '<th data-y="' + y + '" class="' + (state.years.has(y)?'in ':'') + (y===state.year?'cur':'') + '">' + String(y).slice(2) + '</th>'; });
  html += '</tr></thead><tbody>';
  rows.forEach(s => {
    const vals = YEARS.map(y => seriesValue(s.id, state.byYear[y]));
    const max = Math.max(1, ...vals);
    html += '<tr><td class="rowlab"><span style="display:inline-block;width:7px;height:7px;border-radius:2px;background:' + s.color + ';margin-right:5px"></span>' + esc(s.name) + '</td>';
    YEARS.forEach((y,i) => {
      const v = vals[i];
      const a = v ? Math.max(.1, Math.pow(v/max, .65)) : 0;
      const bg = v ? 'rgba(240,163,94,' + a.toFixed(2) + ')' : 'transparent';
      html += '<td data-y="' + y + '" class="' + (state.years.has(y)?'in ':'') + (y===state.year?'cur':'') + '" style="background:' + bg + '">' + (v ? compact(v) : '·') + '</td>';
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  return html;
}

function renderSeriesTable(t){
  const rows = SERIES.filter(s => state.series.has(s.id));
  const single = state.years.size === 1;
  const peak = {};
  rows.forEach(s => {
    let best = {y:null, v:-1};
    YEARS.forEach(y => { const v = seriesValue(s.id, state.byYear[y]); if(v > best.v) best = {y, v}; });
    peak[s.id] = best;
  });
  const val = (s) => {
    switch(s.id){
      case 'fatalities': return t.fatalities.total;
      case 'incidents': return t.incidents;
      case 'major': return t.major.incidents;
      case 'suicide': return t.suicide.incidents;
      case 'explosions': return t.explosions.incidents;
      case 'arrests': return t.arrests.arrested;
      case 'arms': return t.arms.recoveries;
      case 'surrender': return t.surrender.surrendered;
    }
    return 0;
  };
  return '<table class="tbl"><thead><tr><th>Series</th><th>' + (single ? state.year : 'span') + '</th><th>Peak year</th><th>Peak</th></tr></thead><tbody>' +
    rows.map(s => '<tr><td><span style="display:inline-block;width:7px;height:7px;border-radius:2px;background:' + s.color + ';margin-right:6px"></span>' + esc(s.name) + '</td>' +
      '<td class="em">' + num(val(s)) + '</td><td>' + peak[s.id].y + '</td><td>' + num(peak[s.id].v) + '</td></tr>').join('') +
    '</tbody></table>';
}

function renderVictimSplit(t){
  const parts = [];
  if(state.series.has('suicide')) parts.push({name:'Suicide attacks', d:t.suicide, k:'killed'});
  if(state.series.has('explosions')) parts.push({name:'Explosions', d:t.explosions, k:'killed'});
  return '<table class="tbl"><thead><tr><th>Type</th><th>Civilians</th><th>Security</th><th>Militants</th><th>Total</th></tr></thead><tbody>' +
    parts.map(p => {
      const rows = periodRows();
      const get = f => sum(rows, r => (r[ p.name==='Suicide attacks' ? 'suicide' : 'explosions' ][f]) || 0);
      return '<tr><td>' + p.name + '</td><td>' + num(get('killed_civ')) + '</td><td>' + num(get('killed_sf')) +
        '</td><td>' + num(get('killed_mil')) + '</td><td class="em">' + num(get('killed')) + '</td></tr>';
    }).join('') + '</tbody></table>';
}

// ---------------------------------------------------------------- district tab
function renderDistrictTab(el){
  if(!state.district){
    const ranked = state.districts.map(p => ({p, v:districtValue(p.name)})).filter(x => x.v != null)
      .sort((a,b) => b.v - a.v).slice(0,12);
    el.innerHTML = '<div class="kicker">District record</div><div class="h2">Choose a district</div>' +
      '<div class="sub">Click any district shape on the map, or start with the highest values.</div>' +
      '<div class="section"><div class="section-head"><h3>Highest now</h3><span class="sub">' + esc(shadeInfo().label) + '</span></div>' +
      '<table class="tbl"><tbody>' + ranked.map((x,i) =>
        '<tr data-d="' + esc(x.p.name) + '" style="cursor:pointer"><td><span class="rank">' + String(i+1).padStart(2,'0') + '</span>' + esc(x.p.display) + '</td><td class="em">' + num(x.v) + '</td></tr>'
      ).join('') + '</tbody></table></div>';
    $$('#inspBody tr[data-d]').forEach(tr => tr.addEventListener('click', () => selectDistrict(tr.dataset.d)));
    return;
  }
  const p = state.districtByName[state.district];
  const satp = satpDistrictAgg(state.district);
  const gtdN = gtdDistrictValue(state.district,'n');
  const gtdK = gtdDistrictValue(state.district,'k');
  const combined = SPLIT_PARENT.has(state.district);

  const series = satp ? districtSpark(state.district) : gtdSpark(state.district);
  el.innerHTML =
    '<div class="dist-head"><div class="dist-emblem">' + esc(p.display.slice(0,1)) + '</div><div>' +
      '<div class="h2" style="font-size:1.22rem">' + esc(p.display) + (FATA.has(state.district) ? '<span class="badge fata">FATA</span>' : '<span class="badge settled">Settled</span>') + '</div>' +
      '<div class="sub">' + esc(p.division) + ' Division · HQ ' + esc(p.hq) + ' · ' + num(Math.round(p.area_km2)) + ' km²</div></div></div>' +
    '<div class="kpi-grid">' +
      '<div class="kpi"><div class="v">' + (satp ? num(satp.total) : '—') + '</div><div class="l">SATP killed · ' + esc(selLabel()) + '</div></div>' +
      '<div class="kpi"><div class="v">' + (satp ? num(satp.incidents) : '—') + '</div><div class="l">SATP killing incidents</div></div>' +
      '<div class="kpi"><div class="v">' + num(gtdN) + '</div><div class="l">GTD incidents · ' + esc(selLabel()) + '</div></div>' +
      '<div class="kpi"><div class="v">' + num(gtdK) + '</div><div class="l">GTD fatalities</div></div>' +
    '</div>' +
    (satp ? '' : '<div class="section"><div class="empty">SATP publishes a yearly sheet for this district, but it has not been downloaded yet. Press <b>Sync SATP</b> with an internet connection to load all ' + (combined?'combined ':'') + 'district series.</div></div>') +
    '<div class="section"><div class="section-head"><h3>' + (satp?'SATP fatalities by year':'GTD incidents by year') + '</h3><span class="sub">' + esc(selLabel()) + '</span></div>' +
      '<div class="spark"><div class="cap">' + (satp?'people killed':'incidents') + '</div>' + series + '</div></div>' +
    (satp ? '<div class="section"><div class="section-head"><h3>Recent years</h3><span class="sub">SATP</span></div>' +
      '<table class="tbl"><thead><tr><th>Year</th><th>Incidents</th><th>Civilians</th><th>Security</th><th>Total</th></tr></thead><tbody>' +
      satpRecent(state.district) + '</tbody></table></div>' : '') +
    '<div class="section"><div class="section-head"><h3>Notes</h3></div><div class="note" style="font-size:9.5px;color:#61798a;line-height:1.6">' +
      (satp
        ? 'District figures are SATP’s own yearly datasheets, compiled from news reports. ' + (combined ? 'SATP reports this district jointly with its pre-split parent, so the same series appears on each part.' : '') +
          ' They count militants killed in operations inside the total.'
        : 'No SATP district series is stored in this build. The map is shading districts from the GTD incident record instead, which is incident-level and ends in 2020.') +
      '</div></div>' +
    '<div class="btnrow"><button class="btn" id="dZoom">Zoom to district</button>' +
      '<a class="btn" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query=' +
        encodeURIComponent(p.hq + ', ' + p.display + ', Khyber Pakhtunkhwa') + '">Google Maps ↗</a></div>' +
    '<div class="btnrow"><a class="btn ghost" target="_blank" rel="noopener" href="' + esc(districtSource(state.district)) + '">SATP district sheet ↗</a></div>';
  $('#dZoom').addEventListener('click', () => {
    const lyr = dLayer.getLayers().find(l => l.feature && l.feature.properties.name === state.district);
    if(lyr) map.fitBounds(lyr.getBounds(), {padding:[40,40], maxZoom:10});
  });
}

function districtSource(name){
  const key = SATP_ALIAS[name] || name;
  const rec = (state.satp.districts || {})[key];
  if(rec && rec.source) return rec.source;
  return 'https://www.satp.org/datasheet/district/pakistan-khyberpakhtunkhwa';
}

function districtSpark(name){
  const key = SATP_ALIAS[name] || name;
  const rec = (state.satp.districts || {})[key];
  const vals = YEARS.map(y => {
    const r = (rec.fatalities || []).find(x => x.year === y);
    return r ? r.total : 0;
  });
  return sparkSvg(vals, '#f0a35e');
}

function gtdSpark(name){
  const d = (state.gtdStats && state.gtdStats[name]) || {};
  const vals = YEARS.map(y => (d[y] && d[y].n) || 0);
  return sparkSvg(vals, '#5aa9e6');
}

function sparkSvg(vals, color){
  const W = 300, H = 58, pad = 3;
  const max = Math.max(1, ...vals);
  const x = i => pad + i / (vals.length - 1) * (W - pad * 2);
  const y = v => H - pad - (v / max) * (H - pad * 2);
  let d = '', area = 'M' + x(0) + ' ' + (H-pad);
  vals.forEach((v,i) => { d += (i?'L':'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); area += 'L' + x(i).toFixed(1) + ' ' + y(v).toFixed(1); });
  area += 'L' + x(vals.length-1) + ' ' + (H-pad) + ' Z';
  const cur = vals[state.year - 2000];
  let bands = '';
  YEARS.forEach((y,i) => {
    if(!state.years.has(y)) return;
    bands += '<rect x="' + (x(i) - (W/(vals.length-1))/2) + '" y="0" width="' + (W/(vals.length-1)) + '" height="' + H + '" fill="#0d6b3f" opacity=".07"/>';
  });
  return '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" role="img">' + bands +
    '<path d="' + area + '" fill="' + color + '22"/>' +
    '<path d="' + d + '" fill="none" stroke="' + color + '" stroke-width="1.5"/>' +
    '<rect x="' + (x(state.year - 2000) - 2) + '" y="0" width="4" height="' + H + '" fill="' + color + '" opacity=".18"/>' +
    '<circle cx="' + x(state.year - 2000) + '" cy="' + y(cur) + '" r="2.6" fill="' + color + '"/>' +
    '</svg>';
}

function satpRecent(name){
  const key = SATP_ALIAS[name] || name;
  const rec = (state.satp.districts || {})[key];
  if(!rec) return '';
  return rec.fatalities.filter(r => r.year >= 2016 && r.year <= state.year).reverse().map(r =>
    '<tr><td>' + r.year + '</td><td>' + num(r.incidents) + '</td><td>' + num(r.civilians) + '</td><td>' + num(r.security) + '</td><td class="em">' + num(r.total) + '</td></tr>'
  ).join('');
}

// ---------------------------------------------------------------- incidents tab
function renderIncidentsTab(el){
  if(state.incident){
    const i = state.incidents.find(x => x.id === state.incident);
    if(i){
      const c = CAT_BY_ID[i.cat] || CAT_BY_ID.other;
      el.innerHTML = '<button class="link" id="incBack" style="margin-bottom:8px">← all incidents</button>' +
        '<div class="kicker">' + esc(c.label) + '</div>' +
        '<div class="h2" style="font-size:1.22rem">' + esc(i.place || i.district) + '</div>' +
        '<div class="sub">' + esc(fmtDate(i.date)) + ' · ' + esc(i.district) + ' District' + (FATA.has(i.district)?' · erstwhile FATA':'') + '</div>' +
        '<div class="kpi-grid" style="margin-top:10px"><div class="kpi"><div class="v">' + num(i.killed) + '</div><div class="l">killed</div></div>' +
        '<div class="kpi"><div class="v">' + num(i.injured) + '</div><div class="l">injured</div></div></div>' +
        '<div class="inc-summary">' + esc(i.summary || 'No summary recorded.') + '</div>' +
        '<dl class="meta"><dt>Actor</dt><dd>' + esc(i.actor || 'Unknown') + '</dd>' +
        '<dt>Target</dt><dd>' + esc(i.target || 'Not recorded') + '</dd>' +
        '<dt>Suicide</dt><dd>' + (i.suicide ? 'Yes' : 'No') + '</dd>' +
        '<dt>Location</dt><dd>' + i.lat.toFixed(4) + ', ' + i.lng.toFixed(4) + ' · ' + esc(i.loc_quality) + '</dd>' +
        '<dt>Record</dt><dd>' + esc(i.src_name || i.src) + '</dd></dl>' +
        ((i.tags || []).length ? '<div class="tagrow">' + i.tags.map(t => '<span class="tag">' + esc(t) + '</span>').join('') + '</div>' : '') +
        (i.url ? '<div class="src-item" style="margin-top:10px"><b>' + esc(i.src_name) + '</b><a href="' + esc(i.url) + '" target="_blank" rel="noopener">Read the reporting ↗</a></div>' :
          '<div class="src-item" style="margin-top:10px"><b>Global Terrorism Database</b><span>START, University of Maryland. Summary adapted from the database entry.</span></div>') +
        '<div class="btnrow"><button class="btn" id="iLocate">Locate on map</button>' +
        '<a class="btn" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(i.lat + ',' + i.lng) + '">Google Maps ↗</a></div>';
      $('#incBack').addEventListener('click', () => { state.incident = null; renderInspector(); });
      $('#iLocate').addEventListener('click', () => { map.setView([i.lat, i.lng], Math.max(map.getZoom(), 10)); });
      return;
    }
  }
  if(!state.incidentsLoaded){
    el.innerHTML = '<div class="kicker">Incident log</div><div class="empty">Loading the GTD incident record…</div>';
    loadIncidents().then(() => renderInspector());
    return;
  }
  const list = filteredIncidents().slice().sort((a,b) => b.killed - a.killed || b.date.localeCompare(a.date)).slice(0, 120);
  el.innerHTML = '<div class="kicker">Incident log</div><div class="h2" style="font-size:18px">' + esc(selLong()) + '</div>' +
    '<div class="sub">' + num(filteredIncidents().length) + ' incidents in view' + (state.years.size>6?' · showing fatalities 5+, deadliest first':' · deadliest first') + '</div>' +
    '<input class="search" id="incSearch" placeholder="Search place, actor, summary…" value="' + esc(state.search) + '">' +
    '<div class="inc-list">' + (list.map(i => {
      const c = CAT_BY_ID[i.cat] || CAT_BY_ID.other;
      return '<div class="inc-row" data-id="' + esc(i.id) + '"><span class="inc-dot" style="background:' + c.color + '"></span>' +
        '<span class="inc-main"><b>' + esc(i.place || i.district) + '</b><span>' + shortDate(i.date) + ' · ' + esc(c.label) + '</span></span>' +
        '<span class="inc-fig"><b>' + num(i.killed) + '</b>killed</span></div>';
    }).join('') || '<div class="empty">No incidents match the current filters.</div>') + '</div>';
  $$('#inspBody .inc-row').forEach(r => r.addEventListener('click', () => { state.incident = r.dataset.id; renderInspector(); }));
  const si = $('#incSearch');
  si.addEventListener('input', debounce(() => { state.search = si.value; renderInspector(); }, 220));
}

// ---------------------------------------------------------------- sources tab
function renderSourcesTab(el){
  const urls = state.satp.source_urls || {};
  const rows = [
    ['Fatalities', urls.fatalities],
    ['Terrorism-related incidents', urls.incidents],
    ['Major incidents', urls.major],
    ['Suicide attacks', urls.suicide],
    ['Explosions', urls.explosions],
    ['Arrests', urls.arrests],
    ['Arms recovery', urls.arms],
    ['Surrenders', urls.surrender],
    ['Other data (catalogue)', urls.other],
    ['District index', urls.districts]
  ].filter(r => r[1]);
  el.innerHTML = '<div class="kicker">Provenance</div><div class="h2" style="font-size:18px">SATP datasheets</div>' +
    '<div class="sub">South Asia Terrorism Portal · Khyber Pakhtunkhwa</div>' +
    '<div class="section"><div class="section-head"><h3>Snapshot</h3><span class="sub" id="srcStatus">' + (state.status && state.status.ok ? 'live' : 'bundled') + '</span></div>' +
    '<table class="tbl"><tbody>' +
      '<tr><td>Data current to</td><td class="em">' + (state.satp.as_of || '—') + '</td></tr>' +
      '<tr><td>Snapshot fetched</td><td>' + (state.satp.fetched_at || '—').replace('T',' ').replace('Z',' UTC') + '</td></tr>' +
      '<tr><td>Fetched by</td><td>' + esc(state.satp.fetched_by || 'bundled snapshot') + '</td></tr>' +
      '<tr><td>District series</td><td>' + Object.keys(state.satp.districts || {}).length + ' loaded</td></tr>' +
      '<tr><td>Update path</td><td>' + (state.server ? 'serve.py · live' : 'static copy') + '</td></tr>' +
    '</tbody></table>' +
    (state.server ? '' : '<div class="note" style="margin-top:.4rem">This copy is being served as static files, so the in-app refresh cannot run. Start it with <code>python3 serve.py</code> to enable one-click SATP synchronisation.</div>') +
    '</div>' +
    '<div class="section"><div class="section-head"><h3>Datasheets</h3><span class="sub">' + rows.length + '</span></div>' +
      rows.map(r => '<div class="src-item"><b>' + esc(r[0]) + '</b><a href="' + esc(r[1]) + '" target="_blank" rel="noopener">' + esc(r[1].replace(/^https?:\/\//,'').slice(0,58)) + ' ↗</a></div>').join('') +
    '</div>' +
    '<div class="section"><div class="section-head"><h3>Other data</h3><span class="sub">SATP catalogue</span></div>' +
      '<div class="cat-toggles">' + (state.satp.province_data.other || []).slice(0, 18).map(o =>
        '<a class="cat" href="' + esc(o.url) + '" target="_blank" rel="noopener">' + esc(o.name.replace(/^Attacks on /,'')) + ' ↗</a>').join('') + '</div>' +
      '<div class="note" style="margin-top:8px">SATP’s “other data” page is a catalogue of attack-type datasheets rather than a time series; the atlas links to them here instead of inventing a series.</div>' +
    '</div>' +
    '<div class="section"><div class="section-head"><h3>Boundaries &amp; incidents</h3></div>' +
      '<div class="src-item"><b>District geometry</b><span>35 current districts (post-2018), including the seven erstwhile FATA agencies.</span></div>' +
      '<div class="src-item"><b>GTD incident record</b><span>6,544 geolocated attacks, 2004–2020, used only for the optional pins and the GTD shading fallback.</span></div>' +
    '</div>';
}

// ---------------------------------------------------------------- orchestration
function syncSelectedPath(){
  if(!dLayer || !dLayer.eachLayer) return;
  dLayer.eachLayer(l => {
    if(!l._path || !l.feature) return;
    const on = l.feature.properties.name === state.district;
    l._path.classList.toggle('district-selected', on);
    if(on){
      l._path.setAttribute('stroke', '#d92332');
      l._path.setAttribute('stroke-width', '2');
      l._path.setAttribute('stroke-opacity', '1');
      if(l.bringToFront) l.bringToFront();
    }
  });
}

function render(){
  _breaks = null;
  paintYearChrome();
  renderHeader();
  renderLegend();
  dLayer.setStyle(styleDistrict);
  syncSelectedPath();
  renderLabels();
  buildPins();
  if(state.ov.heat) buildHeat();
  renderTimeline();
  renderInspector();
  updateHash();
}

function selectOnlyYear(y){
  const v = clamp(Math.round(y), 2000, 2026);
  state.years = new Set([v]);
  state.spanMode = false;
  state.spanEnd = v; state.year = v; state.lastYearClick = v;
  render();
}

function selectSpan(end){
  const v = clamp(Math.round(end), 2000, 2026);
  state.years = new Set(YEARS.filter(y => y <= v));
  state.spanMode = true;
  state.spanEnd = v; state.year = v; state.lastYearClick = v;
  render();
}

function setYears(list){
  const ys = Array.from(new Set(list.filter(y => y >= 2000 && y <= 2026))).sort((a,b)=>a-b);
  if(!ys.length) return toast('Keep at least one year selected.');
  state.years = new Set(ys);
  state.spanMode = false;
  state.year = ys[ys.length-1];
  state.spanEnd = state.year;
  render();
}

function toggleYear(y, shift){
  y = clamp(Math.round(y), 2000, 2026);
  if(!shift && state.years.size === YEARS.length){ return selectOnlyYear(y); }
  if(shift){
    const a = Math.min(state.lastYearClick, y), b = Math.max(state.lastYearClick, y);
    state.years = new Set(YEARS.filter(v => v >= a && v <= b));
    state.spanMode = false;
  }else{
    state.spanMode = false;
    if(state.years.has(y)){
      if(state.years.size === 1) return toast('Keep at least one year selected.');
      state.years.delete(y);
    }else{
      state.years.add(y);
    }
  }
  state.year = Math.max(...state.years);
  state.spanEnd = state.year;
  state.lastYearClick = y;
  render();
}

function buildYearChips(){
  const host = $('#yearChips');
  if(!host) return;
  host.innerHTML = YEARS.map(y =>
    '<button type="button" class="ychip" data-y="' + y + '" aria-pressed="false" title="' + y + ' (shift-click for a range)">' + y + '</button>'
  ).join('');
  $$('#yearChips .ychip').forEach(b => b.addEventListener('click', e => toggleYear(+b.dataset.y, e.shiftKey)));
}

function paintYearChrome(){
  const ys = selectedYears();
  const chips = $$('#yearChips .ychip');
  if(!chips.length) buildYearChips();
  $$('#yearChips .ychip').forEach(b => {
    const y = +b.dataset.y, on = state.years.has(y);
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', String(on));
  });
  $('#yearBig').textContent = selLabel();
  $('#yearSub').textContent = (ys.length === 1 ? 'single year' : ys.length === YEARS.length ? 'all 27 years' : ys.length + ' of 27 years')
    + (state.spanMode && ys.length > 1 && ys.length < YEARS.length ? ' · span' : '');
  const r = $('#yearRange');
  if(r) r.value = state.spanEnd;
  const t = $('#tlSelected');
  if(t) t.textContent = ys.length + '/27 years';
  document.body.classList.toggle('cumulative', state.years.size > 1);
}

function selectDistrict(name){
  state.district = name;
  state.tab = 'district';
  $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === 'district'));
  render();
  map.fitBounds(L.geoJSON({type:'FeatureCollection', features:state.geoFeatures.filter(f => f.properties.name === name)}).getBounds(), {padding:[60,60], maxZoom:10});
}

function encodeYears(){
  const ys = selectedYears();
  if(ys.length === YEARS.length) return 'all';
  const parts = [];
  let i = 0;
  while(i < ys.length){
    let j = i;
    while(j + 1 < ys.length && ys[j+1] === ys[j] + 1) j++;
    parts.push(i === j ? String(ys[i]) : ys[i] + '-' + ys[j]);
    i = j + 1;
  }
  return parts.join(',');
}

function decodeYears(str){
  const out = [];
  String(str || '').split(',').forEach(part => {
    const m = part.match(/^(\d{4})-(\d{4})$/);
    if(m){ for(let y = +m[1]; y <= +m[2]; y++) out.push(y); }
    else if(/^\d{4}$/.test(part)) out.push(+part);
  });
  return out.filter(y => y >= 2000 && y <= 2026);
}

function updateHash(){
  clearTimeout(updateHash._t);
  updateHash._t = setTimeout(() => {
    const p = ['ys=' + encodeYears(), 'tab=' + state.tab, 'lay=' + state.layout, 'fs=' + state.fontScale.toFixed(2)];
    if(state.district) p.push('d=' + encodeURIComponent(state.district));
    try{ history.replaceState(null, '', '#' + p.join('&')); }
    catch(e){ try{ location.hash = p.join('&'); }catch(_){} }
  }, 250);
}

// ---------------------------------------------------------------- sync
async function checkStatus(){
  try{
    const r = await fetch('api/satp/status', {cache:'no-store'});
    if(!r.ok) throw new Error('no api');
    const s = await r.json();
    state.server = true;
    state.status = s;
    paintSync(s);
    if(s.ok && s.fetched_at && state.fetchedAt && s.fetched_at !== state.fetchedAt){
      await loadSatp(true);
      toast('Updated from SATP — data now current to ' + (state.satp.as_of || 'today'));
    }
    if(s.ok) state.fetchedAt = s.fetched_at;
  }catch(e){
    state.server = false;
    paintSync(null);
  }
}

function paintSync(s){
  const chip = $('#syncChip'), txt = $('#syncText'), dot = $('#syncDot');
  chip.classList.remove('live','stale','err','busy');
  if(!s){
    txt.textContent = (OFFLINE ? 'Offline edition · data to ' : 'Bundled snapshot · ') + (state.satp.as_of || '');
    chip.classList.add(OFFLINE ? 'offline' : 'stale');
    $('#btnSync').disabled = false;
    $('#btnSync').title = 'Needs the local server (python3 serve.py) to reach SATP';
    return;
  }
  if(s.busy){ txt.textContent = 'Syncing with SATP…'; chip.classList.add('busy'); $('#btnSync').disabled = true; return; }
  $('#btnSync').disabled = false;
  if(s.last_error){ txt.textContent = 'SATP sync failed — using snapshot'; chip.classList.add('err'); return; }
  const when = (s.fetched_at || '').replace('T',' ').replace('Z','');
  txt.textContent = 'SATP to ' + (s.as_of || '—') + ' · synced ' + when.slice(0,16);
  chip.classList.add('live');
}

async function syncNow(){
  if(!state.server){
    toast('Live sync needs the local server: run “python3 serve.py” in the app folder, then reload.');
    return;
  }
  const btn = $('#btnSync');
  btn.disabled = true;
  try{
    const r = await fetch('api/satp/refresh', {method:'POST'});
    const j = await r.json();
    if(!j.started && j.busy) toast('A sync is already running…');
    else toast('Contacting SATP — this can take a minute.');
    const started = Date.now();
    const poll = setInterval(async () => {
      try{
        const st = await (await fetch('api/satp/status', {cache:'no-store'})).json();
        paintSync(st);
        if(!st.busy || Date.now() - started > 240000){
          clearInterval(poll);
          $('#btnSync').disabled = false;
          if(st.last_error) toast('Sync failed: ' + st.last_error);
          else { await loadSatp(true); toast('SATP data refreshed to ' + (state.satp.as_of || 'the latest date') + '.'); }
        }
      }catch(e){ clearInterval(poll); $('#btnSync').disabled = false; }
    }, 2500);
  }catch(e){
    btn.disabled = false;
    toast('Could not start the sync. Is serve.py running?');
  }
}

async function loadSatp(force){
  try{
    let data;
    if(window.__ATLAS__ && window.__ATLAS__.satp){
      data = window.__ATLAS__.satp;
    }else{
      const r = await fetch('data/satp.json', {cache: force ? 'no-store' : 'default'});
      data = await r.json();
    }
    state.satp = data;
    state.fetchedAt = data.fetched_at || state.fetchedAt;
    const years = new Set();
    Object.values(data.province_data).forEach(list => { if(Array.isArray(list)) list.forEach(r => { if(r && r.year) years.add(r.year); }); });
    buildYearIndex();
    buildSeriesToggles();
    if(hasSatpDistricts() && state.shade === 'gtd_n'){
      state.shade = 'satp_total';
      const sel = $('#shadeMetric'); if(sel) sel.value = 'satp_total';
      if(force) toast('District layer upgraded to the SATP district series.');
    }
    if(force){ render(); }
  }catch(e){
    toast('Could not load the SATP snapshot.');
    console.error(e);
  }
}

// ---------------------------------------------------------------- controls
function buildSeriesToggles(){
  const host = $('#seriesToggles');
  const t = periodTotals();
  host.innerHTML = SERIES.map(s => {
    const on = state.series.has(s.id);
    const v = s.id === 'fatalities' ? t.fatalities.total
      : s.id === 'incidents' ? t.incidents
      : s.id === 'major' ? t.major.incidents
      : s.id === 'suicide' ? t.suicide.incidents
      : s.id === 'explosions' ? t.explosions.incidents
      : s.id === 'arrests' ? t.arrests.arrested
      : s.id === 'arms' ? t.arms.recoveries : t.surrender.surrendered;
    return '<label class="series ' + (on?'':'off') + '" data-s="' + s.id + '">' +
      '<input type="checkbox" ' + (on?'checked':'') + '>' +
      '<span class="swatch" style="background:' + s.color + '"></span>' +
      '<span class="name">' + esc(s.name) + '</span>' +
      '<span class="val" data-v="' + s.id + '">' + compact(v) + '</span>' +
      '<span class="chk"></span></label>';
  }).join('');
  $$('#seriesToggles input').forEach(inp => {
    inp.addEventListener('change', () => {
      const id = inp.closest('.series').dataset.s;
      if(state.series.has(id)){ if(state.series.size === 1){ inp.checked = true; return toast('Keep at least one series on.'); } state.series.delete(id); }
      else state.series.add(id);
      buildSeriesToggles();
      render();
    });
  });
}

function updateSeriesValues(){
  const t = periodTotals();
  SERIES.forEach(s => {
    const el = document.querySelector('.series .val[data-v="' + s.id + '"]');
    if(!el) return;
    const v = s.id === 'fatalities' ? t.fatalities.total
      : s.id === 'incidents' ? t.incidents
      : s.id === 'major' ? t.major.incidents
      : s.id === 'suicide' ? t.suicide.incidents
      : s.id === 'explosions' ? t.explosions.incidents
      : s.id === 'arrests' ? t.arrests.arrested
      : s.id === 'arms' ? t.arms.recoveries : t.surrender.surrendered;
    el.textContent = compact(v);
  });
}

function buildCatToggles(){
  const host = $('#catToggles');
  host.innerHTML = CATS.map(c => {
    const on = state.cats.has(c.id);
    const n = state.incidentsLoaded ? state.incidents.filter(i => i.cat === c.id && state.years.has(i.year)).length : '';
    return '<button class="cat ' + (on?'on':'') + '" data-c="' + c.id + '" type="button" aria-pressed="' + on + '"><i style="background:' + c.color + '"></i>' + esc(c.label) + '<span class="n">' + n + '</span></button>';
  }).join('');
  $$('#catToggles .cat').forEach(b => b.addEventListener('click', () => {
    const id = b.dataset.c;
    if(state.cats.has(id)){ if(state.cats.size === 1) return toast('Keep at least one category on.'); state.cats.delete(id); }
    else state.cats.add(id);
    b.classList.toggle('on'); b.setAttribute('aria-pressed', state.cats.has(id));
    render();
  }));
}

function toggleAllCats(){
  const all = state.cats.size === CATS.length;
  state.cats = new Set(all ? [CATS[0].id] : CATS.map(c => c.id));
  buildCatToggles(); render();
}

function togglePlay(){
  if(state.playing){
    state.playing = false; clearInterval(state.playTimer);
    $('#btnPlay').textContent = '▶ Play years';
    return;
  }
  state.playing = true;
  $('#btnPlay').textContent = '❚❚ Pause';
  let y = 2000;
  selectOnlyYear(2000);
  state.playTimer = setInterval(() => {
    y++;
    if(y > 2026){ clearInterval(state.playTimer); state.playing = false; $('#btnPlay').textContent = '▶ Play years'; return; }
    selectOnlyYear(y);
  }, 780);
}

// ---------------------------------------------------------------- export
function download(name, text, type){
  const a = document.createElement('a');
  a.download = name;
  if(window.URL && URL.createObjectURL && window.Blob){
    const blob = new Blob([text], {type: type || 'text/plain;charset=utf-8'});
    a.href = URL.createObjectURL(blob);
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }else{
    a.href = 'data:' + (type || 'text/plain') + ';charset=utf-8,' + encodeURIComponent(text);
    document.body.appendChild(a); a.click(); a.remove();
  }
}

function csvCell(v){
  const t = String(v == null ? '' : v);
  return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
}

function exportCsv(){
  const head = ['year','terrorism_incidents','killing_incidents','killed','civilians','security_forces','militants','not_specified',
    'major_incidents','major_killed','major_injured','suicide_attacks','suicide_killed','explosions','explosion_killed',
    'arrests','arrest_incidents','arms_recoveries','surrender_incidents','surrendered'];
  const rows = [head.join(',')];
  selectedYears().forEach(y => {
    const r = state.byYear[y];
    rows.push([y, r.incidents.incidents, r.fatalities.incidents, r.fatalities.total, r.fatalities.civilians, r.fatalities.security,
      r.fatalities.militants, r.fatalities.ns, r.major.incidents, r.major.killed, r.major.injured,
      r.suicide.incidents, r.suicide.killed, r.explosions.incidents, r.explosions.killed,
      r.arrests.arrested, r.arrests.incidents, r.arms.recoveries, r.surrender.incidents, r.surrender.surrendered].join(','));
  });
  download('kp-satp-yearly-' + encodeYears().replace(/[,]/g,'_') + '.csv', rows.join('\n'), 'text/csv;charset=utf-8');
  toast('Yearly SATP table downloaded · ' + selectedYears().length + ' years.');
}

function exportIncidentsCsv(){
  if(!state.incidentsLoaded){ toast('The incident layer is still loading.'); return; }
  const head = ['id','date','year','district','place','lat','lng','category','killed','injured','actor','target','summary'];
  const rows = [head.join(',')];
  filteredIncidents()
    .slice().sort((a,b) => b.killed - a.killed || b.date.localeCompare(a.date))
    .forEach(i => rows.push([i.id, i.date, i.year, i.district, i.place, i.lat, i.lng, (CAT_BY_ID[i.cat]||CAT_BY_ID.other).label,
      i.killed, i.injured, i.actor, i.target, i.summary].map(csvCell).join(',')));
  download('kp-incidents-' + encodeYears().replace(/[,]/g,'_') + '.csv', rows.join('\n'), 'text/csv;charset=utf-8');
  toast(rows.length - 1 + ' incidents downloaded.');
}

function exportJson(){
  const t = periodTotals();
  const view = {
    generated: new Date().toISOString(),
    source: state.satp.source,
    as_of: state.satp.as_of,
    selection: { years: selectedYears(), label: selLong() },
    layout: state.layout,
    filters: {
      series: Array.from(state.series), categories: Array.from(state.cats),
      min_fatalities: state.minKilled, shade: state.shade, district: state.district
    },
    totals: t,
    districts: state.districts
      .map(p => ({ name: p.name, display: p.display, fata: FATA.has(p.name), value: districtValue(p.name) }))
      .filter(d => d.value != null)
      .sort((a,b) => b.value - a.value)
  };
  download('kp-atlas-view.json', JSON.stringify(view, null, 2), 'application/json;charset=utf-8');
  toast('Current view downloaded as JSON.');
}

function exportSvg(){
  const svg = $('#tlChart svg');
  if(!svg || state.tlCollapsed){ toast('Show the timeline first, then export its chart.'); return; }
  const clone = svg.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const vb = (svg.getAttribute('viewBox') || '0 0 900 140').split(/\s+/).map(Number);
  clone.setAttribute('width', String(vb[2] || 900));
  clone.setAttribute('height', String(vb[3] || 140));
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = '.tl-axis{font:10px Candara,Segoe UI,sans-serif;fill:#7f978a}' +
    '.tl-grid{stroke:#e2ecdf;stroke-width:1}.tl-bar{fill:#bfe0ca}.tl-bar.on{fill:#2f8f5b}' +
    '.tl-focus{fill:rgba(255,207,51,.22);stroke:rgba(224,180,27,.55)}';
  clone.insertBefore(style, clone.firstChild);
  const text = new XMLSerializer().serializeToString(clone);
  download('kp-atlas-timeline.svg', text, 'image/svg+xml;charset=utf-8');
  toast('Timeline exported as SVG.');
}

function copyLink(){
  const url = location.href;
  const fallback = () => {
    try{
      const ta = document.createElement('textarea');
      ta.value = url; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      document.execCommand && document.execCommand('copy');
      ta.remove();
      toast('Link copied — it restores these years, this district and this layout.');
    }catch(e){ toast('Copy failed. The address bar already holds the shareable link.'); }
  };
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(url).then(
      () => toast('Link copied — it restores these years, this district and this layout.'),
      fallback
    );
  }else fallback();
}

function runExport(action){
  if(action === 'csv') exportCsv();
  else if(action === 'incidents') exportIncidentsCsv();
  else if(action === 'json') exportJson();
  else if(action === 'svg') exportSvg();
  else if(action === 'print') window.print();
  else if(action === 'link') copyLink();
}

// ---------------------------------------------------------------- layout & type
function applyLayout(v){
  const allowed = ['full','wide','focus','maponly'];
  state.layout = allowed.includes(v) ? v : 'full';
  document.body.classList.remove('layout-full','layout-wide','layout-focus','layout-maponly');
  document.body.classList.add('layout-' + state.layout);
  const sel = $('#layoutSel');
  if(sel) sel.value = state.layout;
  try{ localStorage.setItem('kp-layout', state.layout); }catch(e){}
  setTimeout(() => { if(typeof map !== 'undefined' && map) map.invalidateSize(); renderTimeline(); }, 90);
}

const FONT_STEPS = [0.8, 0.9, 1, 1.1, 1.2, 1.3, 1.45];
function applyFont(scale){
  state.fontScale = clamp(Number(scale) || 1, FONT_STEPS[0], FONT_STEPS[FONT_STEPS.length-1]);
  document.documentElement.style.setProperty('--ui', state.fontScale.toFixed(3));
  document.documentElement.style.fontSize = (16 * state.fontScale).toFixed(2) + 'px';
  const val = $('#fsVal');
  if(val) val.textContent = Math.round(state.fontScale * 100) + '%';
  try{ localStorage.setItem('kp-font', String(state.fontScale)); }catch(e){}
  setTimeout(() => { if(typeof map !== 'undefined' && map) map.invalidateSize(); renderTimeline(); }, 90);
}

function stepFont(dir){
  const cur = state.fontScale;
  let idx = FONT_STEPS.findIndex(v => Math.abs(v - cur) < 0.001);
  if(idx < 0) idx = FONT_STEPS.reduce((best,v,i) => Math.abs(v-cur) < Math.abs(FONT_STEPS[best]-cur) ? i : best, 0);
  const next = FONT_STEPS[clamp(idx + dir, 0, FONT_STEPS.length - 1)];
  if(Math.abs(next - cur) < 0.001) return toast(dir > 0 ? 'Largest text size.' : 'Smallest text size.');
  applyFont(next);
}

// ---------------------------------------------------------------- overlays
function applyOverlays(){
  const ids = {districts:'ovDistricts', borders:'ovBorders', fata:'ovFata', pins:'ovPins', heat:'ovHeat', neighbours:'ovNeighbours'};
  Object.entries(ids).forEach(([key,id]) => { const el = $('#' + id); if(el) el.checked = !!state.ov[key]; });
  if(dLayer){ state.ov.districts ? dLayer.addTo(map) : map.removeLayer(dLayer); }
  if(fataLayer){ state.ov.fata ? fataLayer.addTo(map) : map.removeLayer(fataLayer); }
  if(neighbourLayer){ state.ov.neighbours ? neighbourLayer.addTo(map) : map.removeLayer(neighbourLayer); }
  buildPins();
  buildHeat();
  renderLabels();
  $$('.layer').forEach(l => { const i = l.querySelector('input'); l.classList.toggle('on', !!(i && i.checked)); });
  const n = Object.values(state.ov).filter(Boolean).length;
  $('#overlayCount').textContent = n + ' on';
  renderLegend();
}

function setAllLayers(on){
  Object.keys(state.ov).forEach(k => { state.ov[k] = on; });
  applyOverlays();
  toast(on ? 'All six layers on.' : 'Panel layers off — basemap only.');
}

// ---------------------------------------------------------------- controls
function bindControls(){
  buildYearChips();

  $('#yearRange').addEventListener('input', e => selectSpan(+e.target.value));
  $('#yrPrev').addEventListener('click', () => {
    if(state.spanMode && state.years.size > 1) selectSpan(state.spanEnd - 1);
    else selectOnlyYear(state.year - 1);
  });
  $('#yrNext').addEventListener('click', () => {
    if(state.spanMode && state.years.size > 1) selectSpan(state.spanEnd + 1);
    else selectOnlyYear(state.year + 1);
  });
  $('#btnYearsAll').addEventListener('click', () => {
    state.years = new Set(YEARS); state.spanMode = true; state.spanEnd = 2026; state.year = 2026; state.lastYearClick = 2026;
    render();
    toast('All 27 years selected.');
  });
  $('#btnYearsClear').addEventListener('click', () => selectOnlyYear(Math.max(...state.years)));
  $('#btnLatest').addEventListener('click', () => selectOnlyYear(2026));
  $('#btnLast5').addEventListener('click', () => setYears(YEARS.slice(-5)));
  $('#btnPlay').addEventListener('click', togglePlay);

  const ovMap = {ovDistricts:'districts', ovBorders:'borders', ovFata:'fata', ovPins:'pins', ovHeat:'heat', ovNeighbours:'neighbours'};
  Object.entries(ovMap).forEach(([id, key]) => {
    const el = $('#' + id);
    el.addEventListener('change', () => { state.ov[key] = el.checked; applyOverlays(); });
  });
  applyOverlays();
  $('#btnLayersAll').addEventListener('click', () => setAllLayers(true));
  $('#btnLayersMap').addEventListener('click', () => setAllLayers(false));

  $('#shadeMetric').addEventListener('change', e => { state.shade = e.target.value; render(); });
  $('#basemap').addEventListener('change', e => setBasemap(e.target.value));

  $('#btnAllSeries').addEventListener('click', () => {
    if(state.series.size === SERIES.length) state.series = new Set(['fatalities','incidents','major','suicide']);
    else state.series = new Set(SERIES.map(s => s.id));
    buildSeriesToggles(); render();
  });
  $('#btnAllCats').addEventListener('click', toggleAllCats);
  $$('#sevRow button').forEach(b => b.addEventListener('click', () => {
    $$('#sevRow button').forEach(x => x.classList.toggle('active', x === b));
    state.minKilled = +b.dataset.min;
    buildPins();
  }));
  $$('.tab').forEach(t => t.addEventListener('click', () => setTab(t.dataset.tab)));

  $('#btnSync').addEventListener('click', syncNow);
  $('#syncChip').addEventListener('click', () => { if(!state.server) setTab('sources'); });
  $('#btnAbout').addEventListener('click', () => { renderAbout(); $('#aboutModal').hidden = false; });
  $$('#aboutModal [data-close]').forEach(b => b.addEventListener('click', () => { $('#aboutModal').hidden = true; }));

  // export menu
  const menu = $('#exportMenu');
  $('#btnExport').addEventListener('click', e => {
    e.stopPropagation();
    menu.hidden = !menu.hidden;
    $('#btnExport').setAttribute('aria-expanded', String(!menu.hidden));
  });
  $$('#exportMenu [data-export]').forEach(b => b.addEventListener('click', () => {
    menu.hidden = true;
    $('#btnExport').setAttribute('aria-expanded', 'false');
    runExport(b.dataset.export);
  }));
  document.addEventListener('click', e => {
    if(!menu.hidden && !menu.contains(e.target) && e.target !== $('#btnExport')) menu.hidden = true;
  });

  // layout + type
  $('#layoutSel').addEventListener('change', e => { applyLayout(e.target.value); toast('Layout: ' + e.target.options[e.target.selectedIndex].text.replace('Layout · ','')); });
  $('#btnExitMapOnly').addEventListener('click', () => applyLayout('full'));
  $('#fsDown').addEventListener('click', () => stepFont(-1));
  $('#fsUp').addEventListener('click', () => stepFont(1));

  $('#tlToggle').addEventListener('click', () => {
    state.tlCollapsed = !state.tlCollapsed;
    $('#timeline').classList.toggle('collapsed', state.tlCollapsed);
    $('#tlToggle').textContent = state.tlCollapsed ? 'Show' : 'Hide';
    $('#tlToggle').setAttribute('aria-expanded', String(!state.tlCollapsed));
    renderTimeline();
  });
  $('#tlLabels').addEventListener('change', e => { state.tlLabels = e.target.checked; renderTimeline(); });

  $('#btnMobileRail').addEventListener('click', () => document.body.classList.toggle('rail-open'));
  $('#btnMobileInsp').addEventListener('click', () => document.body.classList.toggle('insp-open'));
  $('#btnCloseInsp').addEventListener('click', () => document.body.classList.remove('insp-open'));
  $('#scrim').addEventListener('click', () => document.body.classList.remove('rail-open','insp-open'));

  window.addEventListener('resize', debounce(() => { renderTimeline(); renderLabels(); }, 160));
  window.addEventListener('keydown', e => {
    if(e.key === 'Escape'){ $('#aboutModal').hidden = true; menu.hidden = true; document.body.classList.remove('insp-open','rail-open'); }
    if(e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if(e.key === 'ArrowLeft'){ e.preventDefault(); $('#yrPrev').click(); }
    if(e.key === 'ArrowRight'){ e.preventDefault(); $('#yrNext').click(); }
    if(e.key.toLowerCase() === 'm'){ e.preventDefault(); applyLayout(state.layout === 'maponly' ? 'full' : 'maponly'); }
  });

  setInterval(checkStatus, 60000);
}

function renderAbout(){
  const s = state.satp;
  $('#aboutBody').innerHTML =
    '<p>This atlas is built directly on the nine Khyber Pakhtunkhwa datasheets published by the South Asia Terrorism Portal. Every yearly figure — fatalities, killing incidents, terrorism-related incidents, major incidents, suicide attacks, explosions, arrests, arms recoveries and surrenders — is read from those sheets, not estimated or modelled. The snapshot in this copy is current to <b>' + esc(s.as_of) + '</b>.</p>' +
    '<div class="method-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:12px 0">' +
      [['Terrorism incidents', sum(YEARS.map(y=>state.byYear[y].incidents.incidents))],
       ['People killed', sum(YEARS.map(y=>state.byYear[y].fatalities.total))],
       ['Suicide attacks', sum(YEARS.map(y=>state.byYear[y].suicide.incidents))],
       ['Arrests', sum(YEARS.map(y=>state.byYear[y].arrests.arrested))]]
        .map(x => '<div class="kpi"><div class="v">' + compact(x[1]) + '</div><div class="l">' + x[0] + '</div></div>').join('') +
    '</div>' +
    '<h3>How the data stays current</h3>' +
    '<p>With the local server running (<code>python3 serve.py</code>), the atlas asks SATP for the nine datasheets on start-up when the snapshot is more than twelve hours old, and whenever you press <b>Sync SATP</b>. The server parses the published tables, rewrites <code>data/satp.json</code> and the page reloads the new numbers; a background poll picks up a newer snapshot without a reload. A static copy keeps the bundled snapshot and says so in the header.</p>' +
    '<h3>What the figures count</h3>' +
    '<ul>' +
      '<li><b>Fatalities</b> are SATP’s yearly totals, split into civilians, security forces, militants and “not specified”. Militants killed in security operations are inside the total — that is why the fatality line can rise while incidents fall.</li>' +
      '<li><b>Killing incidents</b> count attacks that killed someone; <b>terrorism-related incidents</b> is the wider count and is always larger.</li>' +
      '<li><b>Major incidents</b> are SATP’s curated subset with high casualties or salience.</li>' +
      '<li><b>District series</b> come from SATP’s per-district fatality datasheets, loaded by the sync. Until they are loaded the map shades districts from the GTD incident record and labels that clearly.</li>' +
    '</ul>' +
    '<h3>Deliberate limits</h3>' +
    '<ul>' +
      '<li>SATP data is compiled from news reports and is explicitly provisional; later revisions change the totals. The snapshot date is shown in the header.</li>' +
      '<li>SATP publishes province-level series, so the map cannot place SATP totals on individual coordinates. The pins are a separate GTD layer, 2004–2020, and are never mixed into the SATP numbers.</li>' +
      '<li>No attempt is made to apportion attacker casualties or to reconcile SATP with other trackers; where sources differ, this atlas does not average them.</li>' +
    '</ul>' +
    '<h3>Basemaps</h3>' +
    '<p>The “Google Maps” options draw Google tile imagery directly in Leaflet (the <code>mt0–mt3.google.com/vt</code> tile service). That is the familiar Google cartography, but it is not the paid Google Maps JavaScript API, so it carries no key quota and can be rate-limited; if tiles fail the atlas switches itself to OpenStreetMap. The offline edition ships a drawn vector basemap (district outlines, province boundary, neighbours, graticule and labels) because imagery cannot be embedded.</p>' +
    '<h3>Years, layers and layouts</h3>' +
    '<p>The year grid is a multi-select: click any years to add or remove them, shift-click to take a range, or drag the slider for a span from 2000. Every figure, shade, matrix cell and timeline bar follows the selection, and selected years are marked in yellow. The six map layers are independent switches; <b>All layers</b> and <b>Map only</b> set them in one go. Four layouts are available — full, map + filters, map + details, and map only, which hides every panel except the map. Text size is adjustable from 80% to 145% with A− / A+, and the whole interface is set in Candara. Export offers the yearly table, the visible incidents, the current view as JSON, the timeline as SVG, a print/PDF pass and a share link.</p>' +
    '<h3>Selection</h3>' +
    '<p>A district you click is outlined in red at 2 px and brought to the front so its record stays visible against its neighbours.</p>';
}

// ---------------------------------------------------------------- boot
async function boot(){
  try{
    const embedded = window.__ATLAS__;
    let satp, districts, outline, neighbours, gtdStats;
    if(embedded){
      satp = embedded.satp; districts = embedded.districts; outline = embedded.outline;
      neighbours = embedded.neighbours; gtdStats = embedded.gtdStats || {};
    }else{
      [satp, districts, outline, gtdStats] = await Promise.all([
        fetch('data/satp.json', {cache:'no-store'}).then(r => r.json()),
        fetch('data/kp_districts.geojson').then(r => r.json()),
        fetch('data/kp_outline.geojson').then(r => r.json()),
        fetch('data/district_stats.json').then(r => r.json()).catch(() => ({}))
      ]);
      try{ neighbours = await fetch('data/neighbours.geojson').then(r => r.json()); }catch(e){}
    }
    state.satp = satp;
    state.gtdStats = gtdStats || {};
    state.outline = outline && outline.features ? outline : outline;   // outline may be a Feature or FeatureCollection
    state.neighbours = neighbours;
    state.geoFeatures = districts.features;
    state.districts = districts.features.map(f => f.properties);
    state.districts.forEach(p => { state.districtByName[p.name] = p; });

    buildYearIndex();
    state.shade = hasSatpDistricts() ? 'satp_total' : 'gtd_n';
    initMap();
    bindControls();
    buildSeriesToggles();
    buildCatToggles();

    // restore a shared view
    const q = new URLSearchParams((location.hash || '').slice(1));
    const ys = q.get('ys');
    const hashYears = ys === 'all' ? YEARS.slice() : (ys ? decodeYears(ys) : []);
    if(hashYears.length){
      state.years = new Set(hashYears);
      state.spanEnd = Math.max(...hashYears);
      state.year = state.spanEnd;
      state.lastYearClick = state.year;
      state.spanMode = isContiguous();
    }
    if(q.get('d') && state.districtByName[q.get('d')]) state.district = q.get('d');
    if(q.get('tab')) state.tab = q.get('tab');
    $$('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === state.tab));

    let savedFont = 1, savedLayout = 'full';
    try{
      savedFont = parseFloat(localStorage.getItem('kp-font')) || 1;
      savedLayout = localStorage.getItem('kp-layout') || 'full';
    }catch(e){}
    if(q.get('fs')) savedFont = parseFloat(q.get('fs')) || savedFont;
    if(q.get('lay')) savedLayout = q.get('lay');
    applyFont(savedFont);
    applyLayout(savedLayout);

    render();
    if(state.district) selectDistrict(state.district);

    // load the optional incident layer after first paint
    loadIncidents().then(() => { buildCatToggles(); if(state.tab === 'incidents') renderInspector(); buildPins(); });
    checkStatus();
  }catch(err){
    console.error(err);
    $('#map').innerHTML = '<div style="padding:2.5rem;color:#2b4635;font:.8rem/1.7 Candara,Segoe UI,sans-serif;max-width:32rem">' +
      '<b>Could not load the atlas data.</b><br>Serve this folder over HTTP — <code>python3 serve.py</code> — or open the single-file offline edition.</div>';
  }
}

document.addEventListener('DOMContentLoaded', boot);
})();
