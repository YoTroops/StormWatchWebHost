(() => {
'use strict';
const back=document.getElementById('testerBackdrop'), form=document.getElementById('testerForm'), close=document.getElementById('testerClose'), status=document.getElementById('testerStatus'), submit=document.getElementById('testerSubmit');
if (!back || !form) return;
let previous=null, busy=false;
function show(){if(!back.hidden)return;previous=document.activeElement;back.hidden=false;document.body.style.overflow='hidden';close.focus();}
function hide(){if(busy)return;back.hidden=true;document.body.style.overflow='';if(previous?.isConnected)previous.focus();}
document.querySelectorAll('[data-open-testers]').forEach(b=>b.addEventListener('click',e=>{e.preventDefault();show();}));
close.addEventListener('click',hide);
back.addEventListener('click',e=>{if(e.target===back)hide();});
document.addEventListener('keydown',e=>{
 if(back.hidden)return;
 if(e.key==='Escape'){e.preventDefault();hide();return;}
 if(e.key==='Tab'){
 const nodes=[...back.querySelectorAll('button:not(:disabled), input:not([tabindex="-1"]), select, textarea')].filter(n=>n.getClientRects().length);
 const first=nodes[0],last=nodes[nodes.length-1];
 if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
 else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
 }
});
form.addEventListener('submit',async e=>{
 e.preventDefault(); if(busy)return;
 status.classList.remove('error');status.textContent='';
 const email=form.elements.email.value.trim();
 if(email && !form.elements.email.checkValidity()){status.classList.add('error');status.textContent='Enter a valid email address or leave it blank.';form.elements.email.focus();return;}
 if(!form.elements.feedback.value.trim()){status.classList.add('error');status.textContent='Please describe your feedback.';form.elements.feedback.focus();return;}
 busy=true;submit.disabled=true;submit.textContent='SENDING…';
 const payload=Object.fromEntries(new FormData(form).entries());payload.consent=true;payload.page=location.pathname;
 try{
 const res=await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const result=await res.json();
 if(!res.ok)throw new Error(typeof result.detail==='string'?result.detail:'Something went wrong. Please try again.');
 status.textContent='Feedback sent. Thank you for helping improve STORMWATCH!';form.reset();submit.textContent='FEEDBACK SENT';
 }catch(err){status.classList.add('error');status.textContent=err.message||'Could not send your request. Try again later.';submit.disabled=false;submit.textContent='SEND FEEDBACK ↗';}
 finally{busy=false;}
});
// On secondary pages, the tester link can return to the dashboard and open this form.
if(new URLSearchParams(location.search).get('feedback')==='1' || new URLSearchParams(location.search).get('tester')==='1'){
 const release=document.getElementById('releaseDialogBackdrop');
 if(release && !release.hidden){const observer=new MutationObserver(()=>{if(release.hidden){observer.disconnect();show();}});observer.observe(release,{attributes:true,attributeFilter:['hidden']});}
 else show();
}
})();