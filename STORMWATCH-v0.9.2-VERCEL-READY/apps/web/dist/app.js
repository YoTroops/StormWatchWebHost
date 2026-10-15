/* STORMWATCH offline-capable cartographic client. Data read exclusively from the local API. */
'use strict';
const $ = (id) => document.getElementById(id);
const state = {
  mode:'LIVE',projection:'globe',center:[-80,22],zoom:1.02,
  layers:{markers:true,track:true,cone:true,recon:true,uas:true,grid:true,radar:true,aircraft:true,models:true},
  detailEnabled:false,osmTiles:new Map(),osmQueue:[],osmActive:0,osmVisible:new Set(),osmTileErrors:0,osmZoom:3,detailLoaded:false,
  mappedSat:null,mappedSatImage:null,mappedSatLoading:false,mappedSatPending:false,mappedSatOpacity:.70,
  coasts:[],lands:[],storms:[],archives:[],selected:null,archive:null,live:null,
  recon:null,uas:null,forecast:null,models:null,modelsStorm:null,modelsLoading:false,modelsSerial:0,selectedModels:new Set(["nhc","hafsa","hafsb","gfs","ecmwf","google","aifs"]),modelMetric:"wind_kt",step:0,playing:false,playTimer:null,
  activePoints:[],hover:null,drawHits:[],sourceError:null,refreshInProgress:false,satellite:null,satelliteLoading:false,satellitePending:false,radar:null,radarImage:null,radarLoading:false,radarPending:false,radarOpacity:.66,radarRegion:"gulf",reconStatus:null,aircraft:null,aircraftLoading:false,tealAircraft:[],tealLoading:false
};
let toastTimeout=null;
const canvas=$('earthCanvas'),ctx=canvas.getContext('2d');
const rad=Math.PI/180;
const finite=(x)=>Number.isFinite(x);
const esc=(x)=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safeLink=(url)=>{try {let u=new URL(url);return u.protocol==='https:'&&['www.nhc.noaa.gov','www.weather.gov'].includes(u.hostname)?u.href:null;}catch{return null}};
function notify(message){const t=$('toast');t.textContent=message;t.classList.add('show');clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>t.classList.remove('show'),4200);}
async function api(path, options){const ctrl=new AbortController();const timer=setTimeout(()=>ctrl.abort(),35000);try{const res=await fetch(path,{...options,signal:ctrl.signal});if(!res.ok){const t=await res.text();throw Error(`${res.status}: ${t.slice(0,180)}`)}return await res.json();}finally{clearTimeout(timer)}}
function isoFmt(v,short=false){if(!v)return '—';const d=new Date(v);if(isNaN(+d))return String(v);return short?d.toLocaleString('en-US',{month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'UTC'})+'Z':d.toISOString().replace('T',' ').slice(0,16)+' UTC';}
function coords(lat,lon){return `${Math.abs(lat).toFixed(2)}°${lat>=0?'N':'S'}  ${Math.abs(lon).toFixed(2)}°${lon>=0?'E':'W'}`}
function catLabel(p){return p.category?'CAT '+p.category:(p.classification || p.status || 'TROPICAL CYCLONE')}
function qualityChip(v){const kind=['UNAVAILABLE','STALE'].includes(v)?'status-unavailable':v==='ARCHIVED'?'status-archive':'';return `<div class="inspector-status ${kind}">${esc(v||'UNAVAILABLE')}</div>`}
function stat(label,value,unit='',hot=false){return `<div class="stat-card"><div class="stat-label">${esc(label)}</div><div class="stat-value ${hot?'hot':''}">${esc(value??'—')}<small>${esc(unit)}</small></div></div>`}
function detail(k,v){return `<div class="detail-line"><span>${esc(k)}</span><span>${esc(v)}</span></div>`}
function aSource(url,text='OPEN OFFICIAL NHC SOURCE ↗'){const x=safeLink(url);return x?`<a class="source-link" href="${esc(x)}" target="_blank" rel="noopener noreferrer">${esc(text)}</a>`:''}

// STORMWATCH v0.9 UI workspaces: keep provider controls mounted so live refresh state is preserved.
let activeWorkspace='storms';
function switchWorkspace(name){
 const allowed=['storms','models','weather','layers','recon'];
 if(!allowed.includes(name))return;
 if(state.mode==='ARCHIVE'&&['models','weather'].includes(name))name='storms';
 activeWorkspace=name;
 document.querySelectorAll('[data-workspace-tab]').forEach(button=>{
  const on=button.dataset.workspaceTab===name;
  button.classList.toggle('active',on);
  button.setAttribute('aria-selected',on?'true':'false');
  button.tabIndex=on?0:-1;
 });
 document.querySelectorAll('.workspace-pane').forEach(panel=>{
  panel.hidden=panel.dataset.workspace!==name;
 });
 const scroller=document.querySelector('.side-content');if(scroller)scroller.scrollTop=0;
 // Canvas-based model chart has no layout until its workspace is shown.
 if(name==='models'&&state.mode==='LIVE'){drawModelChart();}
}

function setMode(mode){
 stop();state.mode=mode;state.step=0;state.selected=null;state.forecast=null;state.models=null;state.modelsStorm=null;state.modelsSerial++;state.activePoints=[];
 $('archiveMode').classList.toggle('active',mode==='ARCHIVE');$('liveMode').classList.toggle('active',mode==='LIVE');
 document.body.classList.toggle('archive-mode', mode==='ARCHIVE');
 switchWorkspace('storms');
 document.querySelectorAll('.mode-live-only').forEach(el=>{el.hidden=mode==='ARCHIVE';});
 renderModels();
 if(mode==='ARCHIVE'){$('modalBackdrop').classList.add('hidden');$('mapInfo').hidden=true;}
 if(mode==='ARCHIVE'){state.mappedSatImage=null;$('mappedSatStatus').textContent='OFF IN ARCHIVE';}else if($('mappedSatEnabled').checked){loadMappedSatellite();}
 if(mode==='LIVE'&&!state.aircraft)loadAircraft();
 $('stormSectionName').textContent=mode==='LIVE'?'CURRENT NHC CYCLONES':'HISTORICAL CYCLONES';
 $('timelineHeading').textContent=mode==='LIVE'?'OBSERVATION TIMELINE':'HISTORICAL REPLAY';
 renderStorms();showEmptyInspector();refreshTimeline();render();
 if(mode==='LIVE'&&!state.live)loadLive();
}
function renderStorms(){
 const items=state.mode==='LIVE'?state.storms:state.archives;
 const q=$('stormSearch').value.toLowerCase();const filtered=items.filter(s=>`${s.name} ${s.id} ${s.year||''}`.toLowerCase().includes(q));
 $('stormCount').textContent=items.length;
 if(!filtered.length){$('stormList').innerHTML=`<div class="empty-list">${state.mode==='LIVE'?(state.sourceError?'NHC live source is unavailable or stale. Active storm status cannot be confirmed.':items.length?'No storms match the filter.':'No active storms reported by NHC.'):'No matching archived storm.'}</div>`;return;}
 $('stormList').innerHTML=filtered.map(s=>{
   const selected=state.selected?.id===s.id;
   const hot=s.category>=3;
   return `<button class="storm-item ${selected?'selected':''}" data-storm="${esc(s.id)}"><div class="storm-row"><div class="storm-main"><span class="storm-symbol">${state.mode==='LIVE'?'◉':'↺'}</span><div><div class="storm-name">${esc(s.name)}</div><div class="storm-type">${esc(s.id)} ${s.year?`· ${s.year}`:''}</div></div></div><span class="storm-category ${hot?'hot':''}">${esc(state.mode==='LIVE'?catLabel(s):s.dataset==='HURDAT2_BEST_TRACK'?'HURDAT2':'ADVISORY')}</span></div><div class="storm-details">${state.mode==='LIVE'?`${esc(s.wind_kt??'—')} KT · ${esc(s.quality)} · ${esc(s.basin)}`:`${esc(s.point_count)} verified positions · ${esc(s.basin)}`}</div></button>`
 }).join('');
 document.querySelectorAll('[data-storm]').forEach(el=>el.addEventListener('click',()=>selectStorm(el.dataset.storm)));
}
async function loadArchives(sync=false){
 try{
  if(sync)notify('Requesting NOAA HURDAT2 archive (up to 12 MB per basin).');
  const res=await api('/api/storms/historical'+(sync?'?sync=true':''));state.archives=res.storms;renderStorms();updateTelemetry();
  if(sync)notify(`${res.storms.length} official historical storms available. Select a storm to replay.`);
  if(!state.selected&&state.mode==='ARCHIVE'&&res.storms.length)await selectStorm(res.storms.some(x=>x.id==='AL142024')?'AL142024':res.storms[0].id);
 }catch(e){notify('Historical archive error: '+e.message.slice(0,90));}
}
async function loadLive(){
 if(state.refreshInProgress)return;state.refreshInProgress=true;
 try{
  const result=await api('/api/storms/live');state.live=result;state.storms=result.storms||[];
  state.sourceError=result.availability==='AVAILABLE'?null:(result.error||'Last cached response has not been reverified');
  $('connectionLabel').textContent=result.availability==='AVAILABLE'?'NHC SOURCE CONNECTED':result.availability==='STALE'?'NHC CACHE STALE':'NHC FEED UNAVAILABLE';
  $('nhcChecked').textContent='CHECKED '+isoFmt(result.checked_utc,true);
  $('statusDot').className='live-dot '+(result.availability==='AVAILABLE'?'ok':'error');
  if(state.mode==='LIVE'){renderStorms();if(state.selected){const newSelected=state.storms.find(x=>x.id===state.selected.id);if(newSelected){state.selected=newSelected;renderInspector()}else{state.selected=null;state.models=null;renderModels();showEmptyInspector();}}}
  updateTelemetry();render();
 }catch(e){state.sourceError=e.message;$('nhcChecked').textContent='CHECK FAILED';$('connectionLabel').textContent='NHC REQUEST FAILED';$('statusDot').className='live-dot error';notify('Live feed unavailable. Archive remains available.');}
 finally{state.refreshInProgress=false}
}
function cleanSatelliteURL(v){try{const u=new URL(v);return u.protocol==='https:'&&u.hostname==='cdn.star.nesdis.noaa.gov'&&u.pathname.startsWith('/GOES19/ABI/CONUS/')&&u.pathname.endsWith('-1250x750.jpg')?u.href:null;}catch{return null}}
async function loadSatellite(){
 if(state.mode!=='LIVE')return;
 if(state.satelliteLoading){state.satellitePending=true;return;}state.satelliteLoading=true;
 const channel=$('satelliteChannel').value;
 $('satelliteStatus').textContent='CHECKING';$('satelliteStatus').className='sat-status';
 try{
  const d=await api('/api/satellite/latest?channel='+encodeURIComponent(channel));
  if(channel!==$('satelliteChannel').value||state.mode!=='LIVE')return;
  const url=d.quality!=='UNAVAILABLE'?cleanSatelliteURL(d.image_url):null;
  state.satellite=d;
  if(!url){$('satelliteImage').hidden=true;$('satelliteEmpty').hidden=false;
   $('satelliteEmpty').textContent='NOAA IMAGE UNAVAILABLE — storm archive and globe remain usable.';
   $('satelliteMeta').textContent='Checked '+isoFmt(d.checked_utc)+' · no verified image received.';
   $('satelliteExpand').disabled=true;$('satelliteStatus').textContent='UNAVAILABLE';$('satelliteStatus').className='sat-status problem';
  }else{
   const image=$('satelliteImage');image.hidden=false;$('satelliteEmpty').hidden=true;
   image.onerror=()=>{state.satellite={...state.satellite,quality:'UNAVAILABLE'};updateTelemetry();$('satelliteEmpty').textContent='Image unavailable at NOAA CDN (metadata received).';$('satelliteEmpty').hidden=false;image.hidden=true;$('satelliteExpand').disabled=true;$('satelliteStatus').textContent='IMAGE FAILED';$('satelliteStatus').className='sat-status problem';};
   image.onload=()=>{$('satelliteEmpty').hidden=true;$('satelliteExpand').disabled=false;};
   if(image.src!==url)image.src=url;
   $('satelliteStatus').textContent=d.quality;$('satelliteStatus').className='sat-status '+(['LIVE','DELAYED'].includes(d.quality)?'available':'problem');
   $('satelliteMeta').textContent=`OBSERVED ${isoFmt(d.observed_utc)} · ${d.quality} · CHECKED ${isoFmt(d.checked_utc,true)}`;
   $('satelliteExpand').disabled=false;
  }
  updateTelemetry();
 }catch(e){state.satellite={quality:'UNAVAILABLE'};$('satelliteStatus').textContent='UNAVAILABLE';$('satelliteStatus').className='sat-status problem';$('satelliteEmpty').hidden=false;$('satelliteEmpty').textContent='Satellite feed unavailable.';$('satelliteImage').hidden=true;$('satelliteExpand').disabled=true;updateTelemetry();}
 finally{state.satelliteLoading=false;if(state.satellitePending){state.satellitePending=false;loadSatellite()}}
}
function expandSatellite(){
 const d=state.satellite,url=cleanSatelliteURL(d?.image_url);if(!url||$('satelliteImage').hidden)return;
 $('modalBackdrop').classList.remove('hidden');$('modalBody').innerHTML=`<img class="satellite-large" src="${esc(url)}" alt="NOAA GOES-19 CONUS satellite preview"/><p class="satellite-large-caption">${esc(d.channel_label)} · OBSERVED ${esc(isoFmt(d.observed_utc))} · ${esc(d.quality)}. NOAA/NESDIS STAR preview, not a map overlay.</p><a class="source-link" href="${esc(d.source_url)}" target="_blank" rel="noopener noreferrer">OFFICIAL NOAA/NESDIS IMAGE PAGE ↗</a>`;
}
async function selectStorm(id){
 stop();state.step=0;state.forecast=null;state.models=null;state.modelsStorm=null;state.modelsSerial++;renderModels();
 const list=state.mode==='LIVE'?state.storms:state.archives;
 const selected=list.find(x=>x.id===id);if(!selected)return;
 state.selected={...selected};state.activePoints=[];
 if(state.mode==='ARCHIVE'){
   try{const detail=await api('/api/storms/historical/'+encodeURIComponent(id));
    if(state.selected?.id!==id)return;
    state.archive=detail;state.activePoints=detail.points;
    state.step=0;focusOn(detail.points[0].lon,detail.points[0].lat,1.12);
    $('mapTitle').textContent='HURRICANE '+detail.name;
    $('mapSubtitle').textContent=detail.dataset==='HURDAT2_BEST_TRACK'?'NOAA/NHC post-analysis best-track observations': 'NHC archived advisory snapshots · NOT best-track data';
   }catch(e){notify('Archive source unavailable: '+e.message.slice(0,100));}
 }else{
   state.archive=null;focusOn(selected.lon,selected.lat,1.2);
   $('mapTitle').textContent=selected.name.toUpperCase()+' · '+catLabel(selected);
   $('mapSubtitle').textContent='NHC current advisory · '+isoFmt(selected.time);
   loadModels(id);
   if(selected.cone_kmz||selected.track_kmz){
     api('/api/storms/'+encodeURIComponent(selected.id)+'/forecast').then(data=>{if(state.selected?.id===id){state.forecast=data;render();}}).catch(e=>notify('Forecast overlay not available: '+e.message.slice(0,80)));
   }
 }
 renderStorms();refreshTimeline();renderInspector();render();
}
function showEmptyInspector(){$('inspector').innerHTML='<div class="inspector-blank"><span class="radar-ring">◎</span><h3>Awaiting selection</h3><p>Choose a cyclone, aircraft observation, or research trajectory to inspect source-verified measurements.</p></div>';}
function renderInspector(){
 const s=state.selected;if(!s){showEmptyInspector();return}
 if(state.mode==='ARCHIVE'&&state.archive){
  const d=state.archive,p=state.activePoints[state.step];if(!p)return;
  const label=d.dataset==='HURDAT2_BEST_TRACK'?'NHC HURDAT2 BEST TRACK':'NHC ADVISORY SNAPSHOT';
  $('inspector').innerHTML=`<div class="inspector-eyebrow">${esc(label)}</div><div class="inspector-title">${esc(d.name)} <small style="font-size:14px;color:#698ba0">${esc(d.year)}</small></div><div class="inspector-sub">${esc(d.id)} · ${esc(d.basin)}</div>${qualityChip('ARCHIVED')}
  <div class="stat-grid">${stat('MAX SUSTAINED WIND',p.wind_kt,'kt',p.category>=3)}${stat('CENTRAL PRESSURE',p.pressure_hpa,'hPa')}${stat('CLASSIFICATION',catLabel(p),'')}${stat('TRACK POSITIONS',d.points.length,'pts')}</div>
  <div class="detail-heading">SELECTED OBSERVATION</div>${detail('Observed at',isoFmt(p.time))}${detail('Position',coords(p.lat,p.lon))}${detail('Record type',d.dataset==='HURDAT2_BEST_TRACK'?'Post-analysis best track':'Archived NHC advisory')}${detail('Wind status',p.wind_mph!=null?'Derived kt from advisory mph':'Official HURDAT2 kt')}${detail('Source',d.provider)}
  ${aSource(p.source_url||d.source_url)}<div class="detail-heading">INTENSITY EVOLUTION</div><canvas id="intensityChart" class="mini-chart"></canvas><p class="inspector-note">${esc(d.note||'Observations retain original valid times and are not forecast tracks.')}</p><button id="syncArchive" class="detail-btn">↻ SYNC COMPLETE NHC HURDAT2 TRACKS</button>`;
  $('syncArchive').addEventListener('click',()=>loadArchives(true));drawMiniChart(d.points,state.step,'wind_kt');
 }else{
  $('inspector').innerHTML=`<div class="inspector-eyebrow">NHC CURRENT TROPICAL CYCLONE</div><div class="inspector-title">${esc(s.name)}</div><div class="inspector-sub">${esc(s.id)} · ${esc(s.basin)}</div>${qualityChip(s.quality)}
    <div class="stat-grid">${stat('MAX SUSTAINED WIND',s.wind_kt,'kt',s.category>=3)}${stat('MINIMUM PRESSURE',s.pressure_hpa,'hPa')}${stat('CLASSIFICATION',catLabel(s),'')}${stat('FORWARD SPEED',s.motion_mph,'mph')}</div>
    <div class="detail-heading">LATEST OFFICIAL ADVISORY</div>${detail('Position',coords(s.lat,s.lon))}${detail('Advisory issued',isoFmt(s.time))}${detail('Motion heading',s.motion_deg!=null?s.motion_deg+'°':'—')}${detail('Data quality',s.quality)}${detail('Provider',s.provider)}
    ${aSource(s.source_url)} ${aSource(s.forecast_url,'NHC FORECAST GRAPHICS ↗')}
    <p class="inspector-note">Forecast cone and track (when available) are separate official guidance layers, not observations.</p>`;
 }
}
function drawMiniChart(points,index,key){const cv=$('intensityChart');if(!cv)return;cv.width=540;cv.height=170;const c=cv.getContext('2d'),vals=points.map(x=>x[key]).filter(finite);if(vals.length<2)return;const min=Math.min(...vals)-4,max=Math.max(...vals)+4;
 const xy=i=>[28+(i/(points.length-1))*(cv.width-43),cv.height-22-((points[i][key]-min)/(max-min))*(cv.height-38)];
 c.strokeStyle='#244b60';c.lineWidth=1;for(let t=0;t<4;t++){const y=20+t*40;c.beginPath();c.moveTo(27,y);c.lineTo(525,y);c.stroke()}
 c.strokeStyle='#4fcfe9';c.lineWidth=3;c.beginPath();points.forEach((p,i)=>{if(!finite(p[key]))return;const [x,y]=xy(i);i?c.lineTo(x,y):c.moveTo(x,y)});c.stroke();
 const [x,y]=xy(Math.max(0,Math.min(index,points.length-1)));c.fillStyle='#ffba71';c.beginPath();c.arc(x,y,5,0,Math.PI*2);c.fill();
 c.fillStyle='#aacadd';c.font='12px monospace';c.fillText(Math.round(max)+' kt',5,14);c.fillText(Math.round(min)+' kt',5,160);
}
function refreshTimeline(){
 const pts=state.mode==='ARCHIVE'?state.activePoints:[];
 const has=pts.length>0;const last=Math.max(0,pts.length-1);state.step=Math.min(state.step,last);
 $('timelineRange').max=last;$('timelineRange').value=state.step;$('timelineRange').disabled=!has;
 $('playPause').disabled=!has;$('skipBack').disabled=!has;$('skipForward').disabled=!has;
 $('timelinePoint').textContent=has?`POINT ${state.step+1} / ${pts.length}`:'NO REPLAY DATA';
 $('timelineTime').textContent=has?isoFmt(pts[state.step].time):state.mode==='LIVE'?'LATEST OFFICIAL ADVISORY':'—';
 $('timelineStart').textContent=has?isoFmt(pts[0].time,true):'START —';$('timelineEnd').textContent=has?isoFmt(pts[last].time,true):'END —';
}
function seek(index){state.step=Math.max(0,Math.min(index,state.activePoints.length-1));refreshTimeline();renderInspector();render();}
function stop(){state.playing=false;clearInterval(state.playTimer);state.playTimer=null;$('playPause').textContent='▶';}
function play(){if(!state.activePoints.length)return;if(state.playing){stop();return}state.playing=true;$('playPause').textContent='Ⅱ';if(state.step===state.activePoints.length-1)state.step=0;
 state.playTimer=setInterval(()=>{if(state.step>=state.activePoints.length-1){stop();return}seek(state.step+1)},Number($('playbackSpeed').value));}
function focusOn(lon,lat,zoom){state.center=[lon,lat];state.zoom=zoom;render();}
function updateTelemetry(){
 const available=state.live?.availability==='AVAILABLE';
 const rec=state.reconStatus?.quality||state.recon?.quality||'NOT CHECKED';
 const badge=(value)=>`<span class="chip ${['AVAILABLE','LIVE','ARCHIVED'].includes(value)?'':'warn'}">${esc(value)}</span>`;
 $('sourceTelemetry').innerHTML=`<div class="tele-row"><span>Live storm feed</span>${badge(state.live?.availability||'NOT CHECKED')}</div><div class="tele-row"><span>Historical archive</span>${badge(state.archives.length?'ARCHIVED':'UNAVAILABLE')}</div>${state.mode==='LIVE'?`<div class="tele-row"><span>Forecast models</span>${badge(state.models?.quality||'NOT CHECKED')}</div><div class="tele-row"><span>GOES satellite</span>${badge(state.satellite?.quality||'NOT CHECKED')}</div><div class="tele-row"><span>NWS radar mosaic</span>${badge(state.radar?.quality||'NOT CHECKED')}</div><div class="tele-row"><span>NOAA aircraft ADS-B</span>${badge(state.aircraft?.quality||'NOT CHECKED')}</div>`:''}<div class="tele-row"><span>Recon observations</span>${badge(rec)}</div><div class="tele-row"><span>UAS import</span>${badge(state.uas?'USER DATA':'NO DATA')}</div>`;
}
function aircraftDisplay(a){
 const age=Math.max(0,Math.round(a.age_seconds||0));
 const data=`${esc(a.registration)} · ${esc(a.callsign||'no callsign')} · ${age}s old · ${esc(a.quality)}`;
 return `<button class="aircraft-item" data-aircraft="${esc(a.icao_hex)}"><span><strong>${esc(a.name)} · ${esc(a.registration)}</strong><small>${data}</small></span><em class="${a.quality==='LIVE'?'':'delay'}">${esc(a.quality)}</em></button>`;
}
function renderAircraftList(){
 const d=state.aircraft,all=[...(d?.aircraft||[]),...state.tealAircraft];
 $('aircraftStatus').textContent=d?.quality||'NOT CHECKED';
 $('aircraftStatus').className='sat-status '+(d?.quality==='AVAILABLE'?'available':'problem');
 $('aircraftList').innerHTML=(d?.aircraft?.length ? d.aircraft.map(aircraftDisplay).join('')
   :`<div class="aircraft-empty">${d?.quality==='UNAVAILABLE'?'ADS-B source unavailable.':
    'No recent NOAA aircraft positions reported. No flight/mission status is inferred.'}</div>`);
 document.querySelectorAll('[data-aircraft]').forEach(el=>el.onclick=()=>{
   const record=all.find(a=>a.icao_hex===el.dataset.aircraft);if(record)selectAircraft(record);
 });
 updateTelemetry();render();
}
async function loadAircraft(){
 if(state.mode!=='LIVE'||state.aircraftLoading)return;
 state.aircraftLoading=true;
 try{state.aircraft=await api('/api/aircraft/noaa');renderAircraftList()}
 catch(e){state.aircraft={quality:'UNAVAILABLE',aircraft:[]};renderAircraftList()}
 finally{state.aircraftLoading=false}
}
async function lookupTeal(){
 if(state.mode!=='LIVE'||state.tealLoading)return;
 const code=$('tealCallsign').value.trim().toUpperCase();
 if(!/^TEAL[0-9]{1,3}$/.test(code)){$('tealResult').textContent='Enter an exact callsign such as TEAL21.';return}
 state.tealLoading=true;$('tealResult').textContent='Checking public ADS-B sighting…';
 try{
   const d=await api('/api/aircraft/teal?callsign='+encodeURIComponent(code));
   state.tealAircraft=d.aircraft||[];
   $('tealResult').textContent=d.quality==='UNAVAILABLE'?'Source unavailable. Mission status unknown.':
     !state.tealAircraft.length?'No recent sighting for '+code+'. This does not rule out a flight.':
     'Sighting found. Callsign and mission association NOT verified. Select marker on map.';
   renderAircraftList();
 }catch(e){state.tealAircraft=[];$('tealResult').textContent='Lookup failed. No position verified.'}
 finally{state.tealLoading=false}
}
function selectAircraft(a){
 if(state.mode!=='LIVE')return;
 focusOn(a.lon,a.lat,1.6);
 $('inspector').innerHTML=`<div class="inspector-eyebrow">PUBLIC AIRCRAFT POSITION · ADS-B</div><div class="inspector-title">${esc(a.name)}</div><div class="inspector-sub">${esc(a.registration)} · ${esc(a.callsign||'CALLSIGN UNKNOWN')}</div>${qualityChip(a.quality)}
 <div class="stat-grid">${stat('BAROMETRIC ALT',a.altitude_ft,'ft')}${stat('GROUND SPEED',a.groundspeed_kt,'kt')}${stat('TRACK HEADING',a.heading_deg,'°')}${stat('MISSION STATUS','NOT VERIFIED')}</div>
 <div class="detail-heading">OBSERVED AIRCRAFT POSITION</div>${detail('Observed UTC',isoFmt(a.observed_utc))}${detail('Coordinates',coords(a.lat,a.lon))}${detail('Age when checked',a.age_seconds+' seconds')}${detail('Type',a.aircraft_type)}${detail('Identity',a.identity_verified?'Known NOAA registration':'Unconfirmed TEAL callsign candidate')}
 <p class="inspector-note">This is an individual public ADS-B sighting, not a continuous flight path. No hurricane mission or current tasking is inferred. Aircraft may be absent due to ADS-B coverage gaps.</p><a class="source-link" href="https://www.adsb.lol/docs/open-data/api/" target="_blank" rel="noopener noreferrer">PUBLIC ADS-B PROVIDER ↗</a>`;
}
async function loadReconStatus(){
 try{const d=await api('/api/recon/status');state.reconStatus=d;
  $('reconLatestStatus').textContent=d.quality==='UNAVAILABLE'?'No verified recent HDOB':`${d.quality} · ${isoFmt(d.last_observation_utc,true)} · ${d.point_count} observations`;
  updateTelemetry();
 }catch(e){state.reconStatus={quality:'UNAVAILABLE'};$('reconLatestStatus').textContent='Recon bulletin check unavailable';updateTelemetry()}
}
async function loadRecon(live){
 try{notify(live?'Fetching the most recent public HDOB bulletin…':'Loading archived official HDOB fixture…');
 const d=await api(live?'/api/recon/latest':'/api/recon/fixture');state.recon=d;
 if(d.points?.length){focusOn(d.points[Math.floor(d.points.length/2)].lon,d.points[Math.floor(d.points.length/2)].lat,1.42);}
 $('inspector').innerHTML=`<div class="inspector-eyebrow">HURRICANE HUNTERS // HDOB</div><div class="inspector-title">AIRCRAFT RECON</div><div class="inspector-sub">${esc(d.mission)} · ${esc(d.points.length)} verified observations</div>${qualityChip(d.quality)}<div class="stat-grid">${stat('HDOB OBSERVATIONS',d.points.length,'pts')}${stat('MAX FLIGHT WIND',Math.max(...d.points.map(x=>x.wind_kt??0)),'kt')}${stat('START TIME',d.points[0].time.slice(11,16),'UTC')}${stat('FINISH TIME',d.points.at(-1).time.slice(11,16),'UTC')}</div><div class="detail-heading">SOURCE AND ATTRIBUTION</div>${detail('Product',d.source_kind)}${detail('Observation date',d.points[0].time.slice(0,10))}${detail('Mission ID',d.mission)}${detail('Aircraft position', 'Historical HDOB fix')}${aSource(d.source_url)}<p class="inspector-note">${esc(d.note)}</p>`;
 updateTelemetry();render();notify('HDOB observations mapped. Aircraft positions are not a live ADS-B feed.');
 }catch(e){notify('Recon unavailable: '+e.message.slice(0,160));}
}
async function onUasFile(file){if(!file)return;const form=new FormData();form.append('file',file);
 try{const d=await api('/api/uas/upload',{method:'POST',body:form});state.uas=d;const p=d.points[Math.floor(d.points.length/2)];focusOn(p.lon,p.lat,1.45);updateTelemetry();notify(`Imported ${d.points.length} user-supplied UAS observations. Not NOAA-verified.`);}catch(e){notify('CSV rejected: '+e.message.slice(0,170));}
}
function project(lon,lat,w,h){const [clon,clat]=state.center;let delta=(lon-clon)*rad;delta=Math.atan2(Math.sin(delta),Math.cos(delta));const phi=lat*rad,phi0=clat*rad;
 if(state.projection==='globe'){
  const cosc=Math.sin(phi0)*Math.sin(phi)+Math.cos(phi0)*Math.cos(phi)*Math.cos(delta);
  if(cosc<.008)return null;
  const r=Math.min(w*.58,h*.76)*state.zoom;
  return [w*.53 + r*Math.cos(phi)*Math.sin(delta),h*.50-r*(Math.cos(phi0)*Math.sin(phi)-Math.sin(phi0)*Math.cos(phi)*Math.cos(delta)),cosc];
 }
 const scale=(w/290)*state.zoom;
 const dx=((lon-clon+540)%360)-180;
 return [w*.5+dx*scale,h*.50-(lat-clat)*scale,1];
}
function drawLine(points,w,h,stroke='#5ac8e5',lineWidth=2,dashed=false,close=false,fill=null){
 if(!points||!points.length)return;
 let prev=null,active=false,polyPath=[];
 ctx.beginPath();for(const coord of points){const p=project(coord[0],coord[1],w,h);
   if(!p){active=false;prev=null;continue}
   if(active && Math.abs(p[0]-prev[0])+Math.abs(p[1]-prev[1])>Math.max(w,h)*.6){active=false;}
   if(active)ctx.lineTo(p[0],p[1]);else ctx.moveTo(p[0],p[1]);prev=p;active=true;polyPath.push(p);
 }
 if(close&&polyPath.length===points.length)ctx.closePath();
 if(fill){ctx.fillStyle=fill;ctx.fill()}
 ctx.lineWidth=lineWidth;ctx.strokeStyle=stroke;ctx.setLineDash(dashed?[7,6]:[]);ctx.stroke();ctx.setLineDash([]);
}
function drawLand(w,h){
 for(const polygon of state.lands)drawLine(polygon,w,h,'#22536a',.7,false,true,'#112e43');
 for(const seg of state.coasts)drawLine(seg,w,h,'#2e6d7d',.82);
}
function drawGrid(w,h){if(!state.layers.grid)return;ctx.save();
 for(let lat=-60;lat<=75;lat+=15){const arr=[];for(let lon=-180;lon<=180;lon+=3)arr.push([lon,lat]);drawLine(arr,w,h,'#255069',.48)}
 for(let lon=-180;lon<180;lon+=20){const arr=[];for(let lat=-85;lat<=85;lat+=3)arr.push([lon,lat]);drawLine(arr,w,h,'#255069',.5)}
 ctx.restore()}
function globeBackground(w,h){
 ctx.clearRect(0,0,w,h);const back=ctx.createLinearGradient(0,0,w,h);back.addColorStop(0,'#061522');back.addColorStop(.54,'#081d31');back.addColorStop(1,'#061522');ctx.fillStyle=back;ctx.fillRect(0,0,w,h);
 // Cartographic radial rings are navigation aids, not atmospheric observations.
 const r=Math.min(w*.58,h*.76)*state.zoom,cx=w*.53,cy=h*.5;
 if(state.projection==='globe'){
  let glow=ctx.createRadialGradient(cx,cy,r*.72,cx,cy,r*1.35);glow.addColorStop(0,'#103c5600');glow.addColorStop(.73,'#226a9a23');glow.addColorStop(.85,'#3b9bcc20');glow.addColorStop(1,'#0d395500');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(cx,cy,r*1.36,0,Math.PI*2);ctx.fill();
  let ocean=ctx.createRadialGradient(cx-r*.27,cy-r*.27,r*.05,cx,cy,r);ocean.addColorStop(0,'#123c56');ocean.addColorStop(.6,'#0a2b43');ocean.addColorStop(.98,'#061c32');ocean.addColorStop(1,'#071928');ctx.fillStyle=ocean;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#346e8a';ctx.lineWidth=1.4;ctx.stroke();ctx.save();ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.clip();
 }else{
  ctx.fillStyle='#0b273b';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#1b415a';ctx.strokeRect(0,0,w,h);
 }
}
// Model guidance: every polyline comes from a real NHC public ATCF A-deck row.
// In particular, HAFS-A != HAFS-AI. No interpolation, no forecast placeholders.
const modelColors={nhc:'#ffbd69',hafsa:'#6ef2c8',hafsb:'#40a9fb',gfs:'#f2967d',ecmwf:'#c8a2ff',google:'#f5d56a',gencast:'#e1a1df',aigfs:'#86bfff',aigefs:'#a5d29d',aifs:'#f08dd0',hafsai:'#8e9ba9'};
function drawModels(w,h){
 if(state.mode!=='LIVE'||!state.layers.models||!state.models||state.modelsStorm!==state.selected?.id)return;
 for(const model of state.models.models||[]){
   if(model.availability!=='AVAILABLE'||!state.selectedModels.has(model.id)||model.points.length<2)continue;
   const color=modelColors[model.id]||'#a2c4d4';
   drawLine(model.points.map(p=>[p.lon,p.lat]),w,h,color,2.4,model.family==='ai');
   for(const p of model.points){if(p.tau_hours===0||p.tau_hours%24)continue;
     const screen=project(p.lon,p.lat,w,h);if(!screen)continue;
     ctx.fillStyle=color;ctx.beginPath();ctx.arc(screen[0],screen[1],3,0,2*Math.PI);ctx.fill();
     state.drawHits.push({x:screen[0],y:screen[1],r:8,kind:'model',id:model.id,tau:p.tau_hours});
   }
 }
}
function drawModelChart(){
 const cv=$('modelsIntensityChart');if(!cv)return;
 const width=Math.max(220,Math.floor(cv.getBoundingClientRect().width||280));cv.width=width*2;cv.height=164*2;
 const c=cv.getContext('2d');c.scale(2,2);const h=164, metric=state.modelMetric;
 c.fillStyle='#0b2334';c.fillRect(0,0,width,h);
 const chosen=state.mode==='LIVE'&&state.models?.models?.filter(m=>m.availability==='AVAILABLE'&&state.selectedModels.has(m.id))||[];
 const all=chosen.flatMap(m=>m.points.filter(p=>p[metric]!=null).map(p=>({x:p.tau_hours,y:p[metric]})));
 if(!all.length){c.font='11px monospace';c.fillStyle='#8da9be';c.fillText('No verified intensity data for selection',8,80);return;}
 let min=Math.min(...all.map(p=>p.y)),max=Math.max(...all.map(p=>p.y));
 if(min===max){min-=5;max+=5}else{const pad=(max-min)*.12;min-=pad;max+=pad}
 const maxTau=Math.max(24,...all.map(p=>p.x));const X=t=>30+t/maxTau*(width-44),Y=y=>h-23-(y-min)/(max-min)*(h-36);
 c.strokeStyle='#284b60';c.fillStyle='#8ba9bc';c.font='9px monospace';
 for(let k=0;k<=4;k++){const y=12+k*(h-34)/4;c.beginPath();c.moveTo(30,y);c.lineTo(width-8,y);c.stroke();c.fillText(String(Math.round(max-k*(max-min)/4)),2,y+3)}
 for(let t=0;t<=maxTau;t+=24){const x=X(t);c.fillText('+'+t+'h',x-9,h-7)}
 for(const m of chosen){const vals=m.points.filter(p=>p[metric]!=null);if(vals.length<2)continue;
 c.strokeStyle=modelColors[m.id]||'#b1cddb';c.lineWidth=2;c.setLineDash(m.family==='ai'?[4,3]:[]);
 c.beginPath();vals.forEach((p,i)=>i?c.lineTo(X(p.tau_hours),Y(p[metric])):c.moveTo(X(p.tau_hours),Y(p[metric])));c.stroke();c.setLineDash([])}
}
function renderModels(){
 const list=$('modelList'),status=$('modelsStatus'),note=$('modelMeta'),cycle=$('modelCycle');
 if(!list)return;
 if(state.mode!=='LIVE'){list.replaceChildren();status.textContent='ARCHIVED';note.textContent='Live model guidance unavailable in archive.';drawModelChart();return}
 const d=state.models;
 status.textContent=state.modelsLoading?'LOADING':d?.quality||'SELECT STORM';
 if(!d){list.innerHTML='<div class="aircraft-empty">Select a current NHC storm to load verified forecast guidance.</div>';note.textContent='Forecasts are model guidance, not observations.';cycle.innerHTML='<option value="">Latest matching cycle</option>';drawModelChart();return}
 const previous=cycle.value;
 cycle.innerHTML=d.available_cycles?.length?d.available_cycles.map(c=>`<option value="${esc(c)}">${esc(isoFmt(c))}</option>`).join(''):'<option value="">No forecast cycles</option>';
 cycle.value=(d.available_cycles||[]).includes(d.cycle_utc)?d.cycle_utc:previous;
 note.textContent=d.error?`Source unavailable: ${d.error}`:d.cycle_utc?`INIT ${isoFmt(d.cycle_utc)} · ${d.available_models} verified models · ${d.cycle_age_hours}h since initialization`:'No public A-deck forecast cycle verified for selected storm.';
 list.innerHTML=(d.models||[]).map(m=>{
  const good=m.availability==='AVAILABLE',checked=good&&state.selectedModels.has(m.id);
  return `<label class="model-row ${good?'':'model-missing'}" title="${esc(m.note)}"><input type="checkbox" data-model="${esc(m.id)}" ${checked?'checked':''} ${good?'':'disabled'}><i style="background:${modelColors[m.id]||'#889cad'}"></i><span><strong>${esc(m.name)}</strong><small>${good?esc(m.aid_used)+' · '+m.points.length+' steps · '+(m.max_wind_kt??'—')+' kt peak':m.id==='hafsai'?'NO VERIFIED HAFS-AI FEED':'NOT IN PUBLIC DECK'}</small></span><em>${esc(m.family==='ai'?'AI':m.family==='official'?'NHC':'NWP')}</em></label>`
 }).join('');
 list.querySelectorAll('[data-model]').forEach(input=>input.addEventListener('change',()=>{input.checked?state.selectedModels.add(input.dataset.model):state.selectedModels.delete(input.dataset.model);render();drawModelChart()}));
 drawModelChart();render();
}
async function loadModels(id,cycle){
 if(state.mode!=='LIVE'||state.selected?.id!==id)return;
 const serial=++state.modelsSerial;
 state.modelsLoading=true;$('modelsStatus').textContent='LOADING';
 try{
  const path='/api/models/'+encodeURIComponent(id)+(cycle?'?cycle='+encodeURIComponent(cycle):'');
  const d=await api(path);if(serial!==state.modelsSerial||state.selected?.id!==id||state.mode!=='LIVE')return;
  state.models=d;state.modelsStorm=id;
 }catch(e){if(serial!==state.modelsSerial)return;state.models=null;notify('Forecast guidance not available: '+e.message.slice(0,95))}
 finally{if(serial===state.modelsSerial){state.modelsLoading=false;renderModels()}}
}
function drawForecast(w,h){if(!state.forecast)return;
 if(state.layers.cone){
  for(const f of state.forecast.layers?.cone?.features||[]){const g=f.geometry;if(g.type==='Polygon'){for(const ring of g.coordinates)drawLine(ring,w,h,'#e9b16d',1.2,false,true,'#f7b86620');}}
 }
 if(state.layers.track){for(const f of state.forecast.layers?.track?.features||[]){const g=f.geometry;if(g.type==='LineString')drawLine(g.coordinates,w,h,'#f9b767',2,true);}}
}
function dot(x,y,r,color,label,sub,pick){
 const glow=ctx.createRadialGradient(x,y,1,x,y,r*4);glow.addColorStop(0,color+'50');glow.addColorStop(1,color+'00');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(x,y,r*4,0,Math.PI*2);ctx.fill();
 ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#d5f8ff';ctx.lineWidth=1.4;ctx.stroke();
 if(label){ctx.font='bold 12px "IBM Plex Mono",monospace';ctx.fillStyle='#e0f5ff';ctx.shadowColor='#030b18';ctx.shadowBlur=5;ctx.fillText(label,x+13,y-5);ctx.shadowBlur=0;
  if(sub){ctx.fillStyle='#94b8c9';ctx.font='10px "IBM Plex Mono",monospace';ctx.fillText(sub,x+13,y+10)}}
 if(pick)state.drawHits.push({x,y,r:Math.max(12,r+6),kind:pick.kind,index:pick.index,id:pick.id});
}
function drawTrack(w,h){
 const pts=state.activePoints;
 if(pts.length&&state.mode==='ARCHIVE'){
  const coords2=pts.slice(0,state.step+1).map(p=>[p.lon,p.lat]);
  if(state.layers.track){drawLine(pts.map(p=>[p.lon,p.lat]),w,h,'#486f87',1.7,true);drawLine(coords2,w,h,'#5ee4ec',3.1)}
  if(state.layers.markers){pts.forEach((p,i)=>{const xy=project(p.lon,p.lat,w,h);if(!xy)return;if(i===state.step)dot(xy[0],xy[1],7,'#63f0eb',null,null,{kind:'track',index:i});else if(i<=state.step){ctx.fillStyle='#6fc9d7';ctx.beginPath();ctx.arc(xy[0],xy[1],2.8,0,Math.PI*2);ctx.fill();state.drawHits.push({x:xy[0],y:xy[1],r:8,kind:'track',index:i})}})}
 }
 if(state.mode==='LIVE'&&state.layers.markers){
  for(const s of state.storms){const p=project(s.lon,s.lat,w,h);if(!p)continue;dot(p[0],p[1],s.id===state.selected?.id?8:6,s.category>=3?'#ffba78':'#53d6ee',s.name.toUpperCase(),`${s.wind_kt||'—'} KT / ${s.quality}`,{kind:'live',id:s.id});}
 }
}
function drawRecon(w,h){if(!state.layers.recon||!state.recon)return;
 const points=state.recon.points;
 for(let i=1;i<points.length;i++){
   const a=points[i-1],b=points[i];const wind=b.wind_kt;
   const color=finite(wind)?wind>=65?'#fb8d64':wind>=35?'#fbc16e':'#c4a7fa':'#aab6cb';
   drawLine([[a.lon,a.lat],[b.lon,b.lat]],w,h,color,3);
 }
 points.forEach((p,i)=>{const xy=project(p.lon,p.lat,w,h);if(!xy)return;ctx.beginPath();ctx.arc(xy[0],xy[1],i===points.length-1?4.5:2.4,0,Math.PI*2);ctx.fillStyle='#d4a5ff';ctx.fill();state.drawHits.push({x:xy[0],y:xy[1],r:8,kind:'recon',index:i})});
}
function drawAircraft(w,h){
 if(state.mode!=='LIVE'||!state.layers.aircraft)return;
 const all=[...(state.aircraft?.aircraft||[]),...state.tealAircraft];
 all.forEach((a,index)=>{
  const pos=project(a.lon,a.lat,w,h);if(!pos)return;
  dot(pos[0],pos[1],5,a.quality==='LIVE'?'#a5ebfa':'#efbf80',
    a.callsign||a.registration, `${a.quality} · ${a.registration}`, {kind:'aircraft',index});
 });
}
function drawUas(w,h){if(!state.layers.uas||!state.uas)return;
 const pts=state.uas.points;drawLine(pts.map(p=>[p.lon,p.lat]),w,h,'#46dabd',3);
 for(let i=0;i<pts.length;i+=Math.max(1,Math.floor(pts.length/1000))){const p=pts[i],xy=project(p.lon,p.lat,w,h);if(xy){ctx.fillStyle='#6bf8d0';ctx.fillRect(xy[0]-2,xy[1]-2,4,4);state.drawHits.push({x:xy[0],y:xy[1],r:7,kind:'uas',index:i})}}
}

// NWS/MRMS IMAGE SERVICE. A requested time inside the NOAA service window is not
// a verified acquisition time, and image pixels are never interpreted as measurements.
const radarBoxes={gulf:[-100,14,-77,34],southeast:[-91,23,-73,39],caribbean:[-88,10,-60,28],conus:[-125,23,-66,50]};
const radarCenters={gulf:[-88.5,24],southeast:[-82,31],caribbean:[-74,19],conus:[-95.5,36.5]};
async function loadRadar(){
 if(state.mode!=='LIVE')return;
 if(state.radarLoading){state.radarPending=true;return;}
 state.radarLoading=true;
 const region=$('radarRegion').value, offset=Number($('radarOffset').value);
 // Never continue displaying an older raster while a new timestamp or provider
 // freshness state is being checked. That can look like live precipitation.
 state.radarImage=null;render();
 $('radarStatus').textContent='CHECKING';$('radarStatus').className='radar-status';
 try{
  const data=await api('/api/radar/status');state.radar=data;
  if(data.quality==='UNAVAILABLE')throw Error(data.error||'No NWS radar time window');
  // Disable unsafe "currently raining" appearance when upstream data is stale.
  if(data.quality==='STALE'){
   $('radarMeta').textContent=`NWS RADAR STALE — overlay hidden. Latest service window ended ${isoFmt(data.coverage_window_end_utc,true)}; this is NOT a verified scan time. Check official NWS radar.`;
   $('radarStatus').textContent='STALE · HIDDEN';$('radarStatus').className='radar-status problem';
   updateTelemetry();render();return;
  }
  const start=Date.parse(data.coverage_window_start_utc),end=Date.parse(data.coverage_window_end_utc);
  if(!Number.isFinite(start)||!Number.isFinite(end)||end-offset*60000<start)throw Error('Selected time is outside NWS radar window');
  const requested=new Date(end-offset*60000).toISOString();
  $('radarMeta').textContent=`${data.quality==='DELAYED'?'DELAYED RADAR · ':''}NWS WINDOW: ${isoFmt(data.coverage_window_start_utc,true)} — ${isoFmt(data.coverage_window_end_utc,true)}. REQUESTED ${isoFmt(requested,true)}; scan acquisition time not independently verified. Echoes do not guarantee rain at ground level.`;
  $('radarStatus').textContent='LOADING IMAGE';
  const image=new Image();
  await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('Official NWS radar PNG unavailable'));image.src=`/api/radar/image?region=${encodeURIComponent(region)}&minutes_ago=${offset}&v=${end}&alignment=2`;});
  if(region!==$('radarRegion').value||offset!==Number($('radarOffset').value)||state.mode!=='LIVE')return;
  state.radarImage=image;state.radarRegion=region;
  $('radarStatus').textContent=data.quality;
  $('radarStatus').className='radar-status'+(data.quality==='DELAYED'?' problem':'');
  updateTelemetry();render();
 }catch(e){state.radarImage=null;state.radar={quality:'UNAVAILABLE'};
  $('radarMeta').textContent='NWS radar unavailable: '+e.message.slice(0,125)+' · No substitute or simulated reflectivity is displayed.';
  $('radarStatus').textContent='UNAVAILABLE';$('radarStatus').className='radar-status problem';updateTelemetry();render();
 }finally{state.radarLoading=false;if(state.radarPending){state.radarPending=false;loadRadar()}}
}
function radarTri(img,src,dest){
 const [a,b,c]=src,[A,B,C]=dest;
 const det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1]);if(Math.abs(det)<.001)return;
 const aa=((B[0]-A[0])*(c[1]-a[1])-(C[0]-A[0])*(b[1]-a[1]))/det;
 const bb=((B[1]-A[1])*(c[1]-a[1])-(C[1]-A[1])*(b[1]-a[1]))/det;
 const cc=((C[0]-A[0])*(b[0]-a[0])-(B[0]-A[0])*(c[0]-a[0]))/det;
 const dd=((C[1]-A[1])*(b[0]-a[0])-(B[1]-A[1])*(c[0]-a[0]))/det;
 const ee=A[0]-aa*a[0]-cc*a[1],ff=A[1]-bb*a[0]-dd*a[1];
 ctx.save();ctx.beginPath();ctx.moveTo(...A);ctx.lineTo(...B);ctx.lineTo(...C);ctx.closePath();ctx.clip();
 ctx.transform(aa,bb,cc,dd,ee,ff);
 // Draw only the source triangle's small bounding rectangle. Rendering the
 // entire source bitmap for every triangle was needlessly expensive and could
 // freeze the map with radar, satellite, and road tiles enabled together.
 const x0=Math.max(0,Math.floor(Math.min(a[0],b[0],c[0]))-1);
 const y0=Math.max(0,Math.floor(Math.min(a[1],b[1],c[1]))-1);
 const x1=Math.min(img.width,Math.ceil(Math.max(a[0],b[0],c[0]))+1);
 const y1=Math.min(img.height,Math.ceil(Math.max(a[1],b[1],c[1]))+1);
 if(x1>x0&&y1>y0)ctx.drawImage(img,x0,y0,x1-x0,y1-y0,x0,y0,x1-x0,y1-y0);
 ctx.restore();
}
function drawRadar(w,h){
 if(state.mode!=='LIVE'||!state.layers.radar||!state.radarImage||!['AVAILABLE','DELAYED'].includes(state.radar?.quality))return;
 const image=state.radarImage,bbox=radarBoxes[state.radarRegion];if(!bbox)return;
 ctx.save();ctx.globalAlpha=state.radarOpacity;
 const [xmin,ymin,xmax,ymax]=bbox;
 // Source export is EPSG:4326, with geographic coordinates linearly spaced in each axis.
 // Reproject image in small triangular mesh cells through the same globe/map projection
 // used for storm markers. No misleading stretched rectangular globe overlay.
 const nx=24,ny=18,dx=image.width/nx,dy=image.height/ny;
 const pos=(i,j)=>project(xmin+(xmax-xmin)*i/nx,ymax-(ymax-ymin)*j/ny,w,h);
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
  const a=pos(i,j),b=pos(i+1,j),c=pos(i,j+1),d=pos(i+1,j+1);
  if(!a||!b||!c||!d)continue;
  // Prevent triangles that bridge the map seam or the hidden hemisphere.
  if(Math.hypot(a[0]-b[0],a[1]-b[1])>w*.42||Math.hypot(a[0]-c[0],a[1]-c[1])>h*.42)continue;
  const s=[i*dx,j*dy],t=[(i+1)*dx,j*dy],u=[i*dx,(j+1)*dy],v=[(i+1)*dx,(j+1)*dy];
  radarTri(image,[s,t,u],[a,b,c]);radarTri(image,[v,u,t],[d,c,b]);
 }
 ctx.restore();
}
// OSM raster street cartography. Browser requests only viewport tiles (not prefetch),
// uses HTTP cache, keeps attribution visible and does not download offline packs.
const TILE_SIZE=256, TILE_CAP=28, TILE_CACHE_CAP=100;
const tileLon=(x,z)=>x/Math.pow(2,z)*360-180;
const tileLat=(y,z)=>Math.atan(Math.sinh(Math.PI*(1-2*y/Math.pow(2,z))))/rad;
function tileZoom(w,h){
 const pxPerDegree=state.projection==='globe'?Math.min(w*.58,h*.76)*state.zoom*rad:(w/290)*state.zoom;
 return Math.max(2,Math.min(13,Math.round(Math.log2(pxPerDegree*360/256))));
}
function createTileCandidates(w,h,z){
 const n=2**z,cx=(state.center[0]+180)/360*n,
   cy=(1-Math.asinh(Math.tan(Math.max(-85,Math.min(85,state.center[1]))*rad))/Math.PI)/2*n;
 const rx=Math.min(13,Math.ceil(w/210)+2),ry=Math.min(13,Math.ceil(h/210)+2),items=[];
 for(let ty=Math.max(0,Math.floor(cy)-ry);ty<=Math.min(n-1,Math.floor(cy)+ry);ty++)for(let tx=Math.floor(cx)-rx;tx<=Math.floor(cx)+rx;tx++){
   const worldX=((tx%n)+n)%n;
   // Deduplicate wrapped low-zoom tiles (world wraps naturally in the map projection).
   const key=`${z}/${worldX}/${ty}`;
   if(items.some(i=>i.key===key))continue;
   const lon=tileLon(tx+.5,z),lat=tileLat(ty+.5,z);
   const pc=project(lon,lat,w,h), corners=[[tx,ty],[tx+1,ty],[tx,ty+1],[tx+1,ty+1]]
     .map(([x,y])=>project(tileLon(x,z),tileLat(y,z),w,h));
   const near=([x,y])=>x>=-40&&x<=w+40&&y>=-40&&y<=h+40;
   if(!((pc&&near(pc))||corners.some(p=>p&&near(p))))continue;
   const dist=pc?Math.hypot(pc[0]-w*.5,pc[1]-h*.5):w;
   items.push({key,z,x:worldX,tx,y:ty,dist});
 }
 return items.sort((a,b)=>a.dist-b.dist).slice(0,TILE_CAP);
}
let renderRequested=false;
function scheduleMapRender(){if(renderRequested)return;renderRequested=true;requestAnimationFrame(()=>{renderRequested=false;render();});}
function drainTileQueue(){
 if(!state.detailEnabled)return;
 while(state.osmActive<3&&state.osmQueue.length){
  const t=state.osmQueue.shift();if(!state.osmVisible.has(t.key))continue;
  const record=state.osmTiles.get(t.key);if(record?.status!=='queued')continue;
  state.osmActive++;record.status='loading';
  const image=new Image();image.crossOrigin='anonymous';image.referrerPolicy='strict-origin-when-cross-origin';
  image.onload=()=>{record.status='ready';record.image=image;state.detailLoaded=true;state.osmActive--;scheduleMapRender();drainTileQueue()};
  image.onerror=()=>{record.status='failed';state.osmTileErrors++;state.osmActive--;scheduleMapRender();drainTileQueue()};
  image.src=`https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`;
 }
}
function drawGeoMesh(img,bbox,w,h,alpha=1,nx=5,ny=5){
 const [xmin,ymin,xmax,ymax]=bbox;
 ctx.save();ctx.globalAlpha=alpha;
 const src=(i,j)=>[img.width*i/nx,img.height*j/ny];
 const pos=(i,j)=>project(xmin+(xmax-xmin)*i/nx,ymax-(ymax-ymin)*j/ny,w,h);
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
  const A=pos(i,j),B=pos(i+1,j),C=pos(i,j+1),D=pos(i+1,j+1);
  if(!A||!B||!C||!D)continue;
  if(Math.hypot(A[0]-B[0],A[1]-B[1])>w*.42||Math.hypot(A[0]-C[0],A[1]-C[1])>h*.42)continue;
  radarTri(img,[src(i,j),src(i+1,j),src(i,j+1)],[A,B,C]);
  radarTri(img,[src(i+1,j+1),src(i,j+1),src(i+1,j)],[D,C,B]);
 }
 ctx.restore();
}
function drawMercatorTile(img,t,w,h,alpha){
 const z=t.z,nx=4,ny=4;
 ctx.save();ctx.globalAlpha=alpha;
 const uv=(i,j)=>[img.width*i/nx,img.height*j/ny];
 const pos=(i,j)=>project(tileLon(t.tx+i/nx,z),tileLat(t.y+j/ny,z),w,h);
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
  const a=pos(i,j),b=pos(i+1,j),c=pos(i,j+1),d=pos(i+1,j+1);
  if(!a||!b||!c||!d)continue;
  if(Math.hypot(a[0]-b[0],a[1]-b[1])>w*.42||Math.hypot(a[0]-c[0],a[1]-c[1])>h*.42)continue;
  radarTri(img,[uv(i,j),uv(i+1,j),uv(i,j+1)],[a,b,c]);
  radarTri(img,[uv(i+1,j+1),uv(i,j+1),uv(i+1,j)],[d,c,b]);
 }
 ctx.restore();
}
function drawStreetTiles(w,h){
 $('mapAttribution').hidden=!state.detailEnabled;
 const status=$('mapDetailStatus');
 if(!state.detailEnabled){status.textContent='OFFLINE COASTLINES · DETAIL OFF';return;}
 const z=tileZoom(w,h);state.osmZoom=z;$('mapZoomLevel').textContent='ZOOM '+z;
 const tiles=createTileCandidates(w,h,z);
 state.osmVisible=new Set(tiles.map(t=>t.key));
 state.osmQueue=state.osmQueue.filter(t=>state.osmVisible.has(t.key));
 for(const t of tiles){
  let record=state.osmTiles.get(t.key);
  if(!record){record={status:'queued'};state.osmTiles.set(t.key,record);state.osmQueue.push(t)}
  if(record.status!=='ready')continue;
  ctx.save();ctx.filter='invert(1) hue-rotate(180deg) saturate(.72) brightness(.91)';
  drawMercatorTile(record.image,t,w,h,state.mappedSatImage&&state.mode==='LIVE'&&$('mappedSatEnabled').checked?.42:.87);
  ctx.restore();
 }
 // An in-memory LRU eviction prevents long browsing sessions retaining every tile.
 if(state.osmTiles.size>TILE_CACHE_CAP){for(const [key,rec] of state.osmTiles){if(state.osmTiles.size<=TILE_CACHE_CAP)break;if(!state.osmVisible.has(key)&&rec.status!=='loading')state.osmTiles.delete(key)}}
 const ready=tiles.filter(t=>state.osmTiles.get(t.key)?.status==='ready').length;
 status.textContent=ready?`OSM DETAIL Z${z} · ${ready}/${tiles.length} visible tiles`:
   state.osmTileErrors?'OSM MAP TILES UNAVAILABLE · OFFLINE COASTLINES SHOWN':'LOADING OSM CITY / ROAD LABELS…';
 drainTileQueue();
}
function drawMappedSatellite(w,h){
 if(state.mode!=='LIVE'||!$('mappedSatEnabled').checked||!state.mappedSatImage)return;
 const bounds=radarBoxes[state.mappedSat?.region];if(!bounds)return;
 drawGeoMesh(state.mappedSatImage,bounds,w,h,state.mappedSatOpacity,22,15);
}
async function loadMappedSatellite(){
 if(state.mode!=='LIVE'||!$('mappedSatEnabled').checked)return;
 if(state.mappedSatLoading){state.mappedSatPending=true;return;}
 state.mappedSatLoading=true;
 const channel=$('mappedSatChannel').value,region=$('mappedSatRegion').value;
 const status=$('mappedSatStatus');status.textContent='CHECKING NOAA GEOGRAPHIC SERVICE…';status.classList.remove('unavailable');
 try{
  const d=await api(`/api/satellite/map/status?channel=${encodeURIComponent(channel)}`);
  if(d.quality==='UNAVAILABLE')throw Error('NOAA nowCOAST projected layer unavailable');
  const image=new Image();
  await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=()=>reject(Error('NOAA image request failed'));
    image.src=`/api/satellite/map/image?channel=${encodeURIComponent(channel)}&region=${encodeURIComponent(region)}&v=${Date.now()>>>18}`;});
  if(state.mode!=='LIVE'||!$('mappedSatEnabled').checked||channel!==$('mappedSatChannel').value||region!==$('mappedSatRegion').value)return;
  state.mappedSat={...d,region};state.mappedSatImage=image;
  status.textContent=`NOAA ${d.layer_name} · ${d.quality} · CHECKED ${isoFmt(d.checked_utc,true)}. Individual pixel capture times unverified.`;
  render();
 }catch(e){state.mappedSatImage=null;state.mappedSat={quality:'UNAVAILABLE'};
  status.textContent=`UNAVAILABLE: ${e.message}. No satellite simulation shown.`;status.classList.add('unavailable');render();
 }finally{state.mappedSatLoading=false;if(state.mappedSatPending){state.mappedSatPending=false;loadMappedSatellite()}}
}
function render(){const rect=canvas.getBoundingClientRect(),w=rect.width,h=rect.height;if(!w||!h)return;const dpr=Math.min(window.devicePixelRatio||1,window.innerWidth<800?1.5:2);
 if(canvas.width!==Math.floor(w*dpr)||canvas.height!==Math.floor(h*dpr)){canvas.width=Math.floor(w*dpr);canvas.height=Math.floor(h*dpr)}
 ctx.setTransform(dpr,0,0,dpr,0,0);state.drawHits=[];
 globeBackground(w,h);drawLand(w,h);drawMappedSatellite(w,h);drawStreetTiles(w,h);drawGrid(w,h);drawRadar(w,h);drawForecast(w,h);drawModels(w,h);drawTrack(w,h);drawRecon(w,h);drawUas(w,h);drawAircraft(w,h);
 if(state.projection==='globe')ctx.restore();
 const modeName=state.mode==='LIVE'?'REAL-TIME MONITOR':'HISTORICAL REPLAY';
 $('mapBasin').textContent=state.selected?.basin?.toUpperCase()||'ATLANTIC / EAST PACIFIC';
 if(!state.selected){$('mapTitle').textContent=state.mode==='LIVE'?'LIVE TROPICAL CYCLONES':'ATLANTIC BASIN';$('mapSubtitle').textContent=state.mode==='LIVE'?'NHC positions as supplied by the official active storm feed':'Select a cyclone to explore verified historical observations.'}
}
function showHit(hit){if(hit.kind==='track'){seek(hit.index);return}
 if(hit.kind==='live'){selectStorm(hit.id);return}
 if(hit.kind==='model'){const m=state.models?.models.find(a=>a.id===hit.id),p=m?.points.find(a=>a.tau_hours===hit.tau);if(m&&p){$('mapInfo').hidden=false;$('mapInfo').textContent=`${m.name} · +${p.tau_hours}h · ${isoFmt(p.valid_utc)} · ${coords(p.lat,p.lon)} · ${p.wind_kt??'—'} kt · ${p.pressure_hpa??'—'} hPa (GUIDANCE)`;}return}
 if(hit.kind==='recon'){const p=state.recon.points[hit.index];$('mapInfo').hidden=false;$('mapInfo').textContent=`HDOB ${isoFmt(p.time)} · ${coords(p.lat,p.lon)} · FL wind ${p.wind_kt??'—'} kt`;return}
 if(hit.kind==='aircraft'){const a=[...(state.aircraft?.aircraft||[]),...state.tealAircraft][hit.index];if(a)selectAircraft(a);return}
 if(hit.kind==='uas'){const p=state.uas.points[hit.index];$('mapInfo').hidden=false;$('mapInfo').textContent=`USER CSV ${isoFmt(p.time)} · ${coords(p.lat,p.lon)} · wind ${p.wind_kt??'—'} kt`;return}}
let drag=null;
canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,clon:state.center[0],clat:state.center[1],moved:false};canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{
 const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;
 const localHit=state.drawHits.find(h=>Math.hypot(h.x-x,h.y-y)<h.r);
 canvas.style.cursor=localHit?'pointer':drag?'grabbing':'grab';
 if(localHit?.kind==='track'){const p=state.activePoints[localHit.index];$('mouseCoordinates').textContent=coords(p.lat,p.lon)}
 else if(localHit?.kind==='model'){const m=state.models?.models.find(a=>a.id===localHit.id),p=m?.points.find(a=>a.tau_hours===localHit.tau);if(p)$('mouseCoordinates').textContent=m.name+' +'+p.tau_hours+'h / '+coords(p.lat,p.lon)}
 else if(localHit?.kind==='live'){const p=state.storms.find(s=>s.id===localHit.id);if(p)$('mouseCoordinates').textContent=coords(p.lat,p.lon)}
 else $('mouseCoordinates').textContent='DRAG / ZOOM / SELECT';
 if(drag){const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>3)drag.moved=true;
 state.center=[((drag.clon-dx/Math.max(200,rect.width)*110/state.zoom+540)%360)-180,Math.max(-78,Math.min(78,drag.clat+dy/Math.max(200,rect.height)*85/state.zoom))];scheduleMapRender()}
});
canvas.addEventListener('pointerup',e=>{if(!drag)return;const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;if(!drag.moved){const nearest=state.drawHits.map(h=>({...h,dist:Math.hypot(h.x-x,h.y-y)})).sort((a,b)=>a.dist-b.dist)[0];if(nearest&&nearest.dist<=nearest.r)showHit(nearest);else $('mapInfo').hidden=true}drag=null});
canvas.addEventListener('wheel',e=>{e.preventDefault();state.zoom=Math.max(.55,Math.min(95,state.zoom*(e.deltaY>0?.90:1.10)));scheduleMapRender()},{passive:false});
canvas.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){state.center[0]-=5;render()}else if(e.key==='ArrowRight'){state.center[0]+=5;render()}else if(e.key==='+'||e.key==='='){state.zoom=Math.min(95,state.zoom*1.15);render()}});
$('detailedMapToggle').onclick=()=>{state.detailEnabled=!state.detailEnabled;
 $('detailedMapToggle').textContent=state.detailEnabled?'◈ DETAIL ON':'◇ DETAIL OFF';
 $('detailedMapToggle').classList.toggle('active',state.detailEnabled);if(!state.detailEnabled){state.osmQueue.length=0;state.osmVisible.clear();}scheduleMapRender()};
$('mappedSatEnabled').onchange=()=>{if($('mappedSatEnabled').checked)loadMappedSatellite();else{state.mappedSatImage=null;$('mappedSatStatus').textContent='OFF';render();}};
$('mappedSatChannel').onchange=()=>{state.mappedSatImage=null;if($('mappedSatEnabled').checked)loadMappedSatellite();else render()};
$('mappedSatRegion').onchange=()=>{state.mappedSatImage=null;if($('mappedSatEnabled').checked)loadMappedSatellite();else render()};
$('mappedSatOpacity').oninput=e=>{state.mappedSatOpacity=Number(e.target.value)/100;render()};
$('aircraftRefresh').onclick=loadAircraft;$('tealLookup').onclick=lookupTeal;
$('tealCallsign').addEventListener('keydown',e=>{if(e.key==='Enter')lookupTeal()});
$('radarRegion').onchange=()=>{state.radarImage=null;loadRadar()};$('radarOffset').onchange=()=>{state.radarImage=null;loadRadar()};$('radarRefresh').onclick=loadRadar;$('radarFocus').onclick=()=>{const c=radarCenters[$('radarRegion').value];focusOn(c[0],c[1],1.35)};$('radarOpacity').oninput=e=>{state.radarOpacity=Number(e.target.value)/100;render()};
document.querySelectorAll('[data-workspace-tab]').forEach(button=>{
   button.addEventListener('click',()=>switchWorkspace(button.dataset.workspaceTab));
   button.addEventListener('keydown',event=>{
     if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
     const tabs=[...document.querySelectorAll('[data-workspace-tab]')].filter(x=>!x.hidden&&getComputedStyle(x).display!=='none');
     const i=tabs.indexOf(button);if(i<0)return;
     event.preventDefault();
     const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(i+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
     switchWorkspace(tabs[next].dataset.workspaceTab);tabs[next].focus();
   });
 });
 document.querySelectorAll('[data-open-workspace]').forEach(button=>button.addEventListener('click',()=>switchWorkspace(button.dataset.openWorkspace)));
 $('focusSelected').onclick=()=>{if(state.mode==='ARCHIVE'&&state.archive?.points?.length){const p=state.archive.points[state.step]||state.archive.points[0];focusOn(p.lon,p.lat,Math.max(1.15,state.zoom));}else if(state.selected&&finite(state.selected.lon)&&finite(state.selected.lat)){focusOn(state.selected.lon,state.selected.lat,Math.max(1.15,state.zoom));}else notify('Choose a storm from STORMS first.');};
 $('satelliteChannel').onchange=()=>loadSatellite();$('satelliteRefresh').onclick=()=>loadSatellite();$('satelliteExpand').onclick=expandSatellite;
function exportModelCsv(){
 if(state.mode!=='LIVE'||!state.models?.available_models||state.modelsStorm!==state.selected?.id){notify('No verified forecast aid records to export.');return}
 const header=['storm_id','model_id','model_name','source_atcf_technique','initialized_utc','valid_utc','lead_hours','latitude','longitude','max_wind_kt','min_pressure_hpa'];
 const csvCell=value=>'"'+String(value??'').replaceAll('"','""')+'"';
 const lines=[header.join(',')];
 for(const m of state.models.models){if(m.availability!=='AVAILABLE')continue;
   for(const p of m.points)lines.push([state.selected.id,m.id,m.name,p.aid,state.models.cycle_utc,p.valid_utc,p.tau_hours,p.lat,p.lon,p.wind_kt,p.pressure_hpa].map(csvCell).join(','));}
 if(lines.length===1){notify('No verified forecast aid records to export.');return}
 const blob=new Blob([lines.join('\r\n')+'\r\n'],{type:'text/csv;charset=utf-8'});
 const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`stormwatch_${state.selected.id}_${state.models.cycle_utc.slice(0,13).replace(/[-T:]/g,'')}_aids.csv`;
 document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
 notify(`Exported ${lines.length-1} verified forecast-aid points. Source: NHC public A-deck.`);
}
$('modelExport').onclick=exportModelCsv;
$('modelRefresh').onclick=()=>{if(state.selected)loadModels(state.selected.id)};
 $('modelCycle').onchange=()=>{if(state.selected)loadModels(state.selected.id,$('modelCycle').value)};
 $('modelMetric').onchange=e=>{state.modelMetric=e.target.value;drawModelChart()};
 $('archiveMode').onclick=()=>setMode('ARCHIVE');$('liveMode').onclick=()=>setMode('LIVE');
$('stormSearch').addEventListener('input',renderStorms);
for(const el of document.querySelectorAll('[data-layer]'))el.addEventListener('change',e=>{state.layers[e.target.dataset.layer]=e.target.checked;render()});
for(const el of document.querySelectorAll('[data-view]'))el.addEventListener('click',e=>{state.projection=e.currentTarget.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b===e.currentTarget));render()});
$('zoomIn').onclick=()=>{state.zoom=Math.min(95,state.zoom*1.2);render()};$('zoomOut').onclick=()=>{state.zoom=Math.max(.55,state.zoom/1.2);render()};
$('resetView').onclick=()=>{state.center=[-80,22];state.zoom=1.02;render()};
$('timelineRange').oninput=e=>seek(Number(e.target.value));$('playPause').onclick=play;$('skipBack').onclick=()=>seek(state.step-1);$('skipForward').onclick=()=>seek(state.step+1);$('playbackSpeed').onchange=()=>{if(state.playing){stop();play()}};
$('reconButton').onclick=()=>loadRecon(false);$('reconLiveButton').onclick=()=>loadRecon(true);$('uasFile').onchange=e=>onUasFile(e.target.files[0]);
$('sourceStatusButton').onclick=async()=>{$('modalBackdrop').classList.remove('hidden');try{const d=await api('/api/health');$('modalBody').innerHTML=`<p style="font-size:12px;color:#b9d4e8">Provider freshness and failures are tracked separately. A server health check does not verify NOAA connectivity.</p><pre class="modal-pre">${esc(JSON.stringify(d,null,2))}</pre><button class="detail-btn" id="refreshSources">↻ REFRESH LIVE FEED</button><button class="detail-btn" id="refreshHURDAT">↓ SYNC NHC ARCHIVE</button>`;$('refreshSources').onclick=()=>{loadLive();$('modalBackdrop').classList.add('hidden')};$('refreshHURDAT').onclick=()=>{loadArchives(true);$('modalBackdrop').classList.add('hidden')};}catch(e){$('modalBody').textContent=e.message}};
$('closeModal').onclick=()=>$('modalBackdrop').classList.add('hidden');$('modalBackdrop').onclick=e=>{if(e.target===$('modalBackdrop'))$('modalBackdrop').classList.add('hidden')};
let layoutChartTimer;const layoutUpdate=()=>{scheduleMapRender();clearTimeout(layoutChartTimer);layoutChartTimer=setTimeout(drawModelChart,150)};window.addEventListener('resize',layoutUpdate);if(window.ResizeObserver)new ResizeObserver(layoutUpdate).observe($('mapArea'));
setInterval(()=>{$('utcClock').textContent=new Date().toISOString().slice(11,19)+' UTC'},1000);
setInterval(()=>{if(document.hidden)return;loadLive();if(state.mode==='LIVE'){if(state.selected)loadModels(state.selected.id);loadSatellite();if(state.layers.radar)loadRadar();if($('mappedSatEnabled').checked)loadMappedSatellite();loadAircraft();}loadReconStatus()},300000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){loadLive();if(state.mode==='LIVE'){if(state.selected)loadModels(state.selected.id);loadSatellite();if(state.layers.radar)loadRadar();if($('mappedSatEnabled').checked)loadMappedSatellite();loadAircraft();}loadReconStatus()}});
async function init(){
 try{const r=await Promise.all([fetch('/static/coastlines.json'),fetch('/static/landpolygons.json')]);state.coasts=await r[0].json();state.lands=await r[1].json()}catch(e){notify('Offline cartography assets unavailable')}
 render();loadLive();loadArchives();
 // Nonessential imagery and reconnaissance requests start after the first map frame.
 setTimeout(()=>{if(document.hidden)return;loadSatellite();if(state.layers.radar)loadRadar();loadAircraft();loadReconStatus()},900);
 // WebSocket is a service heartbeat, not evidence that NHC/ADS-B data is live.
 let retry=3000;
 const connect=()=>{let ws;try{ws=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/ws');ws.onopen=()=>{retry=3000};ws.onmessage=e=>{try{const msg=JSON.parse(e.data);if(msg.event==='source_update'){if(msg.source==='NHC')loadLive();if(msg.source==='SATELLITE'){loadSatellite();if(state.mode==='LIVE'&&$('mappedSatEnabled').checked)loadMappedSatellite();}if(msg.source==='RADAR'&&state.mode==='LIVE'&&state.layers.radar)loadRadar();if(msg.source==='AIRCRAFT'&&state.mode==='LIVE')loadAircraft();if(msg.source==='RECON')loadReconStatus()}}catch(err){}};ws.onerror=()=>ws.close();ws.onclose=()=>{setTimeout(connect,retry);retry=Math.min(retry*2,60000)};}catch(e){setTimeout(connect,retry)}};connect();
}
init();
