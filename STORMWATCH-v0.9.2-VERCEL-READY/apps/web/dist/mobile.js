/* STORMWATCH v0.9.3 - phone-only view controller; desktop app behavior unchanged. */
(() => {
'use strict';
const mq=window.matchMedia('(max-width:760px)');
const body=document.body;
const app=document.getElementById('app');
const workarea=app?.querySelector('.workarea');
if(!workarea)return;
const nav=document.createElement('nav');nav.className='mobile-nav';nav.setAttribute('aria-label','Mobile STORMWATCH navigation');
const destinations=[
 ['map','⌖','MAP'],['storms','◉','STORMS'],['models','╱','MODELS'],['weather','☁','WEATHER'],['layers','▧','LAYERS'],['recon','✈','RECON'],['info','ⓘ','INFO']
];
for(const [id,icon,label] of destinations){
 const button=document.createElement('button');button.type='button';button.className='mobile-nav-button'+(['models','weather'].includes(id)?' mode-live-only':'');
 button.dataset.panel=id;button.setAttribute('aria-label',label==='INFO'?'Storm information':label);
 button.innerHTML=`<span class="mobile-icon" aria-hidden="true">${icon}</span><span>${label}</span>`;nav.append(button);
}
app.append(nav);
const scrim=document.createElement('div');scrim.className='mobile-scrim';scrim.setAttribute('aria-hidden','true');app.append(scrim);
for(const [selector,title] of [['.leftsidebar','Close controls'],['.rightsidebar','Close storm information']]){
 const panel=workarea.querySelector(selector),heading=panel?.querySelector('.panel-heading');
 if(!heading)continue;
 const close=document.createElement('button');close.className='mobile-sheet-close';close.type='button';close.setAttribute('aria-label',title);close.textContent='×';
 heading.append(close);close.addEventListener('click',closePanels);
}
const replay=document.createElement('button');replay.type='button';replay.className='mini mobile-replay-toggle';replay.textContent='◷ REPLAY';
replay.setAttribute('aria-label','Show or hide timeline');replay.setAttribute('aria-expanded','false');
workarea.querySelector('.map-modes')?.prepend(replay);
const setNavActive=(id)=>{
 for(const button of nav.querySelectorAll('.mobile-nav-button')){
  const active=button.dataset.panel===id;
  button.classList.toggle('active',active);
  if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
 }
};
function closePanels(){body.classList.remove('mobile-sheet-open');delete body.dataset.mobileSheet;setNavActive('map');}
function hideReplay(){body.classList.remove('mobile-timeline-open');replay.classList.remove('active');replay.setAttribute('aria-expanded','false');}
function openDestination(id){
 if(!mq.matches)return;
 if(id==='map'){closePanels();return;}
 if(['weather','models'].includes(id)&&body.classList.contains('archive-mode'))return;
 hideReplay();
 if(id==='info')body.dataset.mobileSheet='right';
 else{
  body.dataset.mobileSheet='left';
  const worktab=workarea.querySelector(`[data-workspace-tab="${id}"]`);
  if(worktab)worktab.click();
 }
 body.classList.add('mobile-sheet-open');setNavActive(id);
}
nav.addEventListener('click',e=>{
 const button=e.target.closest('[data-panel]');if(!button)return;
 if(body.classList.contains('mobile-sheet-open') && button.classList.contains('active')){closePanels();return;}
 openDestination(button.dataset.panel);
});
scrim.addEventListener('click',closePanels);
replay.addEventListener('click',()=>{if(!mq.matches)return;closePanels();const on=body.classList.toggle('mobile-timeline-open');replay.classList.toggle('active',on);replay.setAttribute('aria-expanded',String(on));});
workarea.querySelector('#stormList')?.addEventListener('click',e=>{if(e.target.closest('[data-storm]')&&mq.matches)requestAnimationFrame(closePanels)});
for(const id of ['archiveMode','liveMode']){
 document.getElementById(id)?.addEventListener('click',()=>{closePanels();hideReplay();});
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mq.matches){if(body.classList.contains('mobile-sheet-open'))closePanels();else hideReplay();}});
window.addEventListener('resize',()=>{if(!mq.matches){closePanels();hideReplay();}},{passive:true});
// A small mobile zoom convenience. Existing one-finger pan/tap stays delegated to app.js.
// Suppress legacy single-finger panning events while a two-finger gesture is active.
const canvas=document.getElementById('earthCanvas');
if(canvas){
 const points=new Map();let pinchDistance=0;let pinched=false;
 canvas.style.touchAction='none';
 function distance(){const [a,b]=[...points.values()];return a&&b?Math.hypot(a.x-b.x,a.y-b.y):0;}
 canvas.addEventListener('pointerdown',e=>{
  if(e.pointerType!=='touch'||!mq.matches)return;
  points.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(points.size===2){pinchDistance=distance();pinched=true;e.stopImmediatePropagation();canvas.setPointerCapture(e.pointerId);}
 },true);
 canvas.addEventListener('pointermove',e=>{
  if(e.pointerType!=='touch'||!mq.matches)return;
  if(points.has(e.pointerId))points.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(points.size>=2){
   e.stopImmediatePropagation();e.preventDefault();
   const d=distance();if(pinchDistance>0&&d>0&&typeof state!=='undefined'&&typeof render==='function'){
    const scale=Math.max(.88,Math.min(1.12,d/pinchDistance));
    if(Math.abs(scale-1)>.008){state.zoom=Math.max(.55,Math.min(95,state.zoom*scale));render();}
   }
   pinchDistance=d;
  }else if(pinched){e.stopImmediatePropagation();}
 },true);
 const end=e=>{
  if(e.pointerType!=='touch')return;
  const wasPinched=pinched;if(wasPinched)e.stopImmediatePropagation();
  points.delete(e.pointerId);
  if(points.size<2)pinchDistance=0;
  if(points.size===0)pinched=false;
 };
 canvas.addEventListener('pointerup',end,true);canvas.addEventListener('pointercancel',end,true);
}
setNavActive('map');
// Fit the entire orthographic globe to the narrow phone viewport on first load.
if(mq.matches && typeof state!=='undefined' && typeof render==='function' && state.zoom>=1 && state.zoom<=1.03) {
  state.zoom=.77;
  requestAnimationFrame(render);
}
document.getElementById('resetView')?.addEventListener('click',()=>{
  if(mq.matches && typeof state!=='undefined' && typeof render==='function') {
    state.zoom=.77;
    requestAnimationFrame(render);
  }
});
})();
