(() => {
  'use strict';
  const saving=new WeakSet(),revisions=new WeakMap(),drafts=new Set();
  const here=()=>location.pathname+location.search+location.hash;
  const user=document.body.dataset.userId||'guest',key='mlo.navigation.'+user;
  function read(){try{return JSON.parse(sessionStorage.getItem(key)||'{}');}catch{return {};}}
  function store(value){try{sessionStorage.setItem(key,JSON.stringify(value));}catch{}}
  function safe(value){try{const url=new URL(value,location.origin);if(url.origin!==location.origin||url.username||url.password||url.href.length>2400||/^\/(?:api|static|login|logout|signup|password-reset|verify-email)(?:\/|$)/.test(url.pathname))return null;return url.pathname+url.search+url.hash;}catch{return null;}}
  function remember(destination){const target=safe(destination);if(!target||target===here())return;const data=read();data[target]={url:here(),y:scrollY,time:Date.now()};const recent=Object.entries(data).sort((a,b)=>b[1].time-a[1].time).slice(0,40);store(Object.fromEntries(recent));}
  document.addEventListener('click',e=>{const link=e.target.closest('a[href]');if(link&&e.button===0&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&!e.altKey&&!link.target&&!link.download)remember(link.href);},true);
  function fallback(form){if(form?.dataset.saveFallback)return safe(form.dataset.saveFallback);const p=location.pathname;
    if(/^\/life\/tasks\/\d+$/.test(p))return '/life/tasks';if(/^\/life\/notes\/\d+$/.test(p))return '/life/notes';
    if(p==='/finance/budget')return '/finance';if(p.startsWith('/finance/transactions/'))return '/finance/transactions';if(p.startsWith('/finance/'))return '/finance';
    if(/^\/(expenses|courses|items|classes|jobs|events)\//.test(p))return '/'+p.split('/')[1];
    if(/^\/sections\/\d+$/.test(p))return new URLSearchParams(location.search).get('view')==='settings'?p:'/life/spaces';if(p.startsWith('/life/calendars'))return '/life/calendars';if(p==='/life/onboarding')return '/settings';
    if(p.startsWith('/life/study'))return '/life/study';if(p==='/settings')return '/life';if(p.startsWith('/account'))return '/settings';return '/life';
  }
  function feedback(form,text,error=false){let n=form.querySelector('[data-form-feedback]');if(!n){n=document.createElement('p');n.dataset.formFeedback='';n.className='product-feedback record-wide';form.prepend(n);}n.setAttribute('role',error?'alert':'status');n.classList.toggle('is-error',error);n.textContent=text;if(error){n.tabIndex=-1;n.focus();}}
  function go(url,y=0){const target=safe(url)||'/life';try{sessionStorage.setItem(key+'.restore',JSON.stringify({url:target,y}));}catch{}location.assign(target);}
  try{const restored=JSON.parse(sessionStorage.getItem(key+'.restore')||'null');if(restored?.url===here()){sessionStorage.removeItem(key+'.restore');requestAnimationFrame(()=>scrollTo({top:restored.y,behavior:'instant'}));}}catch{}
  function samePage(url){try{const target=new URL(url,location.origin);return target.pathname===location.pathname;}catch{return false;}}
  async function closeInline(form,redirect){const details=form.closest('details');if(!details)return false;details.open=false;details.querySelector('summary')?.focus();window.MLOTasks?.notify('Saved.');
    try{const response=await fetch(redirect||location.href,{credentials:'same-origin'});if(!response.ok||new URL(response.url).pathname==='/login')return true;const doc=new DOMParser().parseFromString(await response.text(),'text/html');for(const selector of ['.mlo-page-head h1','.mlo-page-head>div>p']){const old=document.querySelector(selector),next=doc.querySelector(selector);if(old&&next)old.textContent=next.textContent;}const fresh=[...doc.querySelectorAll('form')].find(f=>f.getAttribute('action')===form.getAttribute('action'));if(!fresh)return true;const section=form.closest('.mlo-surface,.card'),newSection=fresh.closest('.mlo-surface,.card');const target=section&&newSection?section:details,newTarget=section&&newSection?newSection:fresh.closest('details');if(newTarget){newTarget.querySelectorAll('details[open]').forEach(d=>d.open=false);if(newTarget.tagName==='DETAILS')newTarget.open=false;target.replaceWith(newTarget);newTarget.querySelector('summary')?.focus({preventScroll:true});}}
    catch{}return true;
  }
  async function finish(form,options={}){
    drafts.delete(form);const dialog=form?.closest('dialog');if(dialog){dialog.close();return;}
    const overlay=form?.closest('[role=dialog]');if(overlay){overlay.closest('[data-global-capture-dialog]')?.setAttribute('hidden','');return;}
    if(form?.closest('details')&&(!options.redirect||samePage(options.redirect))){await closeInline(form,options.redirect);return;}
    const entry=read()[here()];const previous=entry&&Date.now()-entry.time<43200000&&safe(entry.url);
    go(previous||options.fallback||fallback(form),previous?entry.y:0);
  }
  window.MLOSave={finish,remember,safe};
  function isSave(form,button){button ||= form.querySelector('button[type=submit],button:not([type]),input[type=submit]');return form.hasAttribute('data-save-return')||/^save\b/i.test((button?.matches('input')?button.value:button?.textContent||'').trim());}
  document.addEventListener('input',e=>{const f=e.target.closest('form');if(!f)return;revisions.set(f,(revisions.get(f)||0)+1);if(!f.matches('[data-note-editor],[data-budget-form]')&&(f.matches('[data-protect-draft],[data-enhanced-form]')||[...f.querySelectorAll('button')].some(b=>/^save\b/i.test(b.textContent.trim()))))drafts.add(f);});
  document.addEventListener('submit',async event=>{
    const form=event.target;
    if(!form.closest('[data-app-layout]')||event.defaultPrevented||form.method.toLowerCase()!=='post'||form.enctype==='multipart/form-data'||form.matches('[data-note-editor],[data-budget-form]')||['/login','/signup'].includes(new URL(form.action).pathname)||form.closest('[data-onboarding]'))return;
    event.preventDefault();if(saving.has(form))return;saving.add(form);const submitted=revisions.get(form)||0,returnAfter=isSave(form,event.submitter);const buttons=[...form.querySelectorAll('button[type=submit],button:not([type])')],body=new FormData(form);if(event.submitter?.name)body.append(event.submitter.name,event.submitter.value);for(const b of buttons)b.disabled=true;feedback(form,'Saving…');
    try{const response=await fetch(form.action,{method:'POST',body,headers:{Accept:'application/json','X-MLO-Enhanced':'1'},credentials:'same-origin'});if(response.status===401||(response.redirected&&new URL(response.url).pathname==='/login'))throw Error('Your session expired. Sign in in another tab, then retry. Your edits are still here.');
      const json=(response.headers.get('content-type')||'').includes('application/json'),data=json?await response.json():null;
      if(!response.ok){let message=typeof data?.detail==='string'?data.detail:'';if(!json)message=new DOMParser().parseFromString(await response.text(),'text/html').querySelector('.error-state p,[role=alert]')?.textContent||'';throw Error(message||'Unable to save. Check the form and try again.');}
      if(data?.version&&form.elements.base_version)form.elements.base_version.value=data.version;
      if((revisions.get(form)||0)!==submitted){feedback(form,'Saved. Newer changes are unsaved.');return;}drafts.delete(form);
      const redirect=data?.redirect||(response.redirected?response.url:null);
      if(returnAfter){await finish(form,{redirect});return;}
      if(redirect){remember(redirect);location.assign(redirect);return;}if(json){feedback(form,'Saved.');return;}location.reload();
    }catch(error){feedback(form,error.message,true);}finally{saving.delete(form);for(const b of buttons)b.disabled=false;}
  });
  window.addEventListener('beforeunload',e=>{if(drafts.size){e.preventDefault();e.returnValue='';}});
  for(const a of document.querySelectorAll('.sidebar-nav a.active,.sidebar-foot a.active'))a.setAttribute('aria-current','page');
  for(const region of document.querySelectorAll('.overflow-x-auto,.table-region'))if(region.scrollWidth>region.clientWidth){region.tabIndex=0;region.setAttribute('role','region');if(!region.hasAttribute('aria-label'))region.setAttribute('aria-label','Scrollable table');}
})();
