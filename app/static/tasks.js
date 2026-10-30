(() => {
  'use strict';
  const busy=new WeakSet(),pending=new Map();
  function begin(id){id=Number(id);let release;const own=new Promise(resolve=>release=resolve),combined=Promise.all([pending.get(id),own]);pending.set(id,combined);combined.then(()=>{if(pending.get(id)===combined)pending.delete(id);});return release;}
  function completion(row,done){
    const check=row.querySelector('.mlo-check');
    if(check){check.classList.toggle('is-done',done);check.textContent='';check.setAttribute('aria-pressed',String(done));check.title=done?'Reopen task':'Complete task';const title=row.querySelector('.mlo-task-name')?.textContent||'task';check.setAttribute('aria-label',`${done?'Reopen':'Complete'} ${title}`);}
    row.querySelector('.mlo-task-name')?.classList.toggle('is-done',done);
    const status=row.querySelector('[data-inline-task] [name=status]');if(status)status.value=done?'todo':'done';
  }
  function counts(delta){document.querySelectorAll('[data-open-task-count]').forEach(n=>{const value=Number(n.textContent);if(Number.isFinite(value))n.textContent=String(Math.max(0,value+delta));});}
  function notify(message,error=false){
    let n=document.getElementById('mlo-notification-toast');if(!n){n=document.createElement('div');n.id='mlo-notification-toast';n.setAttribute('role','status');document.body.append(n);}n.textContent=message;n.classList.toggle('mlo-toast-error',error);n.classList.add('mlo-toast-show');clearTimeout(n._hideTimeout);n._hideTimeout=setTimeout(()=>n.classList.remove('mlo-toast-show'),4000);
  }
  async function json(response){if(!(response.headers.get('content-type')||'').includes('application/json'))throw Error('Sign in again, then retry.');const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:`Unable to save (${response.status}).`);return data;}
  let refreshing=false,refreshAgain=false;
  async function refreshRegion(){
    if(!document.querySelector('[data-task-region]')||document.querySelector('#mlo-v37-board,[data-task-map]'))return;
    if(refreshing){refreshAgain=true;return;}refreshing=true;
    try{const response=await fetch(location.href,{headers:{'X-MLO-Fragment':'tasks'},credentials:'same-origin'});if(!response.ok||new URL(response.url).pathname==='/login')throw Error('Task saved. Reload this view to see it.');const fresh=new DOMParser().parseFromString(await response.text(),'text/html').querySelector('[data-task-region]');if(fresh){document.querySelector('[data-task-region]')?.replaceWith(fresh);document.dispatchEvent(new CustomEvent('mlo:task-region-updated'));}}
    catch(error){notify(error.message,true);}finally{refreshing=false;if(refreshAgain){refreshAgain=false;refreshRegion();}}
  }
  function created(item){counts(1);document.dispatchEvent(new CustomEvent('mlo:task-created',{detail:item}));if(document.querySelector('#mlo-v37-board,[data-task-map]'))return;if(document.querySelector('[data-task-region]')){refreshRegion();return;}
    const surface=document.querySelector('.mlo-widget-tasks');if(!surface)return;surface.querySelector('.mlo-empty')?.remove();const row=document.createElement('div');row.className='mlo-task';row.dataset.taskId=String(item.id);
    const form=document.createElement('form');form.method='post';form.action=`/life/tasks/${item.id}/status`;form.dataset.inlineTask='';for(const [name,value] of Object.entries({status:'done',next_page:location.pathname+location.search})){const input=document.createElement('input');input.type='hidden';input.name=name;input.value=value;form.append(input);}const button=document.createElement('button');button.type='submit';button.className='mlo-check';button.setAttribute('aria-label','Complete '+item.title);button.setAttribute('aria-pressed','false');form.append(button);
    const main=document.createElement('div');main.className='mlo-task-main';const link=document.createElement('a');link.className='mlo-task-name';link.href=`/life/tasks/${item.id}`;link.textContent=item.title;main.append(link);row.append(form,main);const first=surface.querySelector('.mlo-task');if(first)first.before(row);else surface.append(row);
  }
  window.MLOTasks={created,refresh:refreshRegion,notify,begin,settled:id=>pending.get(Number(id))||Promise.resolve(),idle:()=>Promise.all([...pending.values()])};
  document.addEventListener('mlo:task-updated',e=>{const item=e.detail;if(!item?.id)return;document.querySelectorAll(`[data-task-id="${Number(item.id)}"]`).forEach(row=>{if(item.title)row.querySelectorAll('.mlo-task-name').forEach(link=>link.textContent=item.title);if(item.status)completion(row,item.status==='done');});});
  document.addEventListener('submit',async event=>{
    const form=event.target;if(!form.matches('[data-inline-task],[data-quick-form]'))return;event.preventDefault();if(busy.has(form))return;const button=form.querySelector('button[type=submit],button:not([type])');if(!form.reportValidity())return;busy.add(form);button.disabled=true;
    if(form.matches('[data-inline-task]')){
      const row=form.closest('.mlo-task'),release=begin(row.dataset.taskId),next=form.elements.status.value,previous=next!=='done';completion(row,next==='done');button.setAttribute('aria-busy','true');
      try{const item=await json(await fetch(form.getAttribute('action')||form.action,{method:'POST',headers:{'X-MLO-Action':'fetch',Accept:'application/json'},body:new FormData(form),credentials:'same-origin'}));completion(row,item.status==='done');counts(item.open_delta??(item.status==='done'?-1:1));document.dispatchEvent(new CustomEvent('mlo:task-updated',{detail:item}));document.dispatchEvent(new CustomEvent('mlo:task-saved',{detail:item}));}
      catch(error){completion(row,previous);notify(error.message,true);}finally{release();button.removeAttribute('aria-busy');}
    }else{
      const input=form.elements.title,submitted=input.value;
      try{await window.MLOTasks.idle();const item=await json(await fetch(form.getAttribute('action')||form.action,{method:'POST',credentials:'same-origin',headers:{'X-MLO-Action':'fetch',Accept:'application/json'},body:new FormData(form)}));if(input.value===submitted)input.value='';created(item);input.focus();}
      catch(error){notify(error.message,true);}
    }
    busy.delete(form);button.disabled=false;
  });
  const select=document.querySelector('[data-focus-duration]'),clock=document.querySelector('[data-focus-clock]');select?.addEventListener('change',()=>{if(clock)clock.textContent=`${String(select.value).padStart(2,'0')}:00`;const kind=document.querySelector('[data-focus-kind]');if(kind)kind.value=select.value==='5'?'break':'focus';});
  if('serviceWorker' in navigator&&(location.protocol==='https:'||location.hostname==='localhost'))window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js').catch(()=>{}));
  const banner=document.createElement('div');banner.className='mlo-offline-banner';banner.textContent='You are offline. Changes need a connection to save.';banner.setAttribute('role','status');document.body.append(banner);const online=()=>banner.hidden=navigator.onLine;window.addEventListener('online',online);window.addEventListener('offline',online);online();
})();
