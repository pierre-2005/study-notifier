(() => {
  'use strict';
  const root=document.querySelector('[data-study-planner]');if(!root)return;
  const form=root.querySelector('[data-planner-preferences]'),container=root.querySelector('[data-availability-windows]');
  const initial=JSON.parse(document.getElementById('planner-preferences').textContent),status=root.querySelector('[data-planner-status]');
  const days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let windows=initial.windows.map(w=>({...w})),preview=null,busy=false;
  function paintWindows(){container.innerHTML=windows.map((w,i)=>`<div class="availability-window" data-window="${i}"><label><span class="sr-only">Day for window ${i+1}</span><select data-window-field="weekday">${days.map((d,n)=>`<option value="${n}" ${w.weekday===n?'selected':''}>${d}</option>`).join('')}</select></label><label><span class="sr-only">Start for window ${i+1}</span><input type="time" required data-window-field="start" value="${esc(w.start)}"></label><span aria-hidden="true">–</span><label><span class="sr-only">End for window ${i+1}</span><input type="time" required data-window-field="end" value="${esc(w.end)}"></label><button type="button" class="product-icon-button" data-remove-window="${i}" aria-label="Remove window ${i+1}">×</button></div>`).join('');}
  Object.entries(initial).forEach(([key,value])=>{if(key==='windows')return;const field=form.elements[key];if(!field)return;if(field.type==='checkbox')field.checked=value;else{if(field.tagName==='SELECT'&&![...field.options].some(o=>o.value===String(value)))field.add(new Option(value,value));field.value=value;}});
  paintWindows();
  const feedback=message=>{status.textContent=message;status.scrollIntoView({block:'nearest'});};
  function invalidate(){preview=null;root.querySelector('[data-plan-apply]').disabled=true;}
  async function request(path,method='POST',body){const response=await fetch('/life/study/planner'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});if(!response.headers.get('content-type')?.includes('application/json'))throw Error('Sign in again to update your plan.');const result=await response.json();if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:result.detail?.[0]?.msg||'Check the planner settings.');return result;}
  function payload(){const fd=new FormData(form);return {windows,...Object.fromEntries(['block_minutes','break_minutes','daily_minutes','default_minutes','horizon_days'].map(k=>[k,Number(fd.get(k))])),automatic:fd.get('automatic')==='on'};}
  async function action(fn){if(busy)return;busy=true;root.setAttribute('aria-busy','true');try{await fn();}catch(error){feedback(error.message);}finally{busy=false;root.removeAttribute('aria-busy');}}
  async function save(){if(!form.reportValidity())throw Error('Check your available hours.');if(!windows.length)throw Error('Add at least one availability window.');await request('/preferences','PUT',payload());}
  form.addEventListener('input',e=>{const row=e.target.closest('[data-window]');if(row&&e.target.dataset.windowField){const key=e.target.dataset.windowField;windows[Number(row.dataset.window)][key]=key==='weekday'?Number(e.target.value):e.target.value;}invalidate();});
  form.addEventListener('click',e=>{const remove=e.target.closest('[data-remove-window]');if(remove){windows.splice(Number(remove.dataset.removeWindow),1);paintWindows();invalidate();}});
  root.querySelector('[data-add-window]').addEventListener('click',()=>{if(windows.length>=28){feedback('Use up to 28 windows.');return;}windows.push({weekday:5,start:'09:00',end:'12:00'});paintWindows();invalidate();container.lastElementChild.querySelector('select').focus();});
  form.addEventListener('submit',e=>{e.preventDefault();action(async()=>{await save();feedback('Availability saved.');window.MLOSave?.finish(form);});});
  function render(plan){const panel=root.querySelector('[data-plan-output]');panel.hidden=false;root.querySelector('[data-plan-totals]').textContent=`${plan.blocks.length} sessions · ${Math.round(plan.minutes/60*10)/10} hours`;root.querySelector('[data-plan-warnings]').innerHTML=plan.warnings.map(w=>`<p class="product-notice">${esc(w)}</p>`).join('');
    const groups=new Map();for(const block of plan.blocks){const date=new Date(block.start),key=date.toLocaleDateString(undefined,{timeZone:plan.timezone,weekday:'long',month:'short',day:'numeric'});if(!groups.has(key))groups.set(key,[]);groups.get(key).push(block);}
    const clock=value=>new Date(value).toLocaleTimeString(undefined,{timeZone:plan.timezone,hour:'2-digit',minute:'2-digit'});
    root.querySelector('[data-plan-days]').innerHTML=[...groups].map(([day,blocks])=>`<section class="planner-day"><h3>${esc(day)}</h3>${blocks.map(b=>`<div class="planner-proposal"><time>${esc(clock(b.start))}<small>${esc(clock(b.end))}</small></time><a href="/life/tasks/${b.task_id}">${esc(b.title)}</a><span>${b.minutes} min</span></div>`).join('')}</section>`).join('')||'<p class="mlo-subtle">No new sessions fit these settings.</p>';
    root.querySelector('[data-plan-unplaced]').innerHTML=plan.unplaced.length?`<section class="planner-unplaced"><h3>Needs attention <span>${plan.unplaced.length}</span></h3>${plan.unplaced.map(t=>`<div><a href="/life/tasks/${t.task_id}">${esc(t.title)}</a><small>${esc(t.reason)} · ${t.minutes} min remaining</small></div>`).join('')}</section>`:'';
    root.querySelector('[data-plan-apply]').disabled=false;panel.scrollIntoView({block:'start',behavior:'instant'});
  }
  root.querySelector('[data-plan-preview]').onclick=()=>action(async()=>{await save();feedback('Finding time around your commitments…');preview=await request('/preview');render(preview);feedback('Preview ready. No calendar events have been changed by this preview.');});
  root.querySelector('[data-plan-dismiss]').onclick=()=>{root.querySelector('[data-plan-output]').hidden=true;invalidate();root.querySelector('[data-plan-preview]').focus();};
  root.querySelector('[data-plan-apply]').onclick=()=>action(async()=>{if(!preview)throw Error('Generate a new preview first.');await request('/apply','POST',{preview_id:preview.preview_id});location.reload();});
  root.querySelector('[data-plan-undo]')?.addEventListener('click',()=>action(async()=>{await request('/undo','POST',{preview_id:root.dataset.lastRevision});location.reload();}));
  root.querySelector('[data-plan-clear]')?.addEventListener('click',()=>action(async()=>{await request('/clear');location.reload();}));
  root.querySelectorAll('[data-plan-pin]').forEach(button=>button.onclick=()=>action(async()=>{await request('/blocks/'+button.dataset.planPin,'PUT',{pinned:button.dataset.pinned!=='true'});location.reload();}));
  document.addEventListener('mlo:task-updated',()=>{invalidate();feedback('Task updated. Generate a fresh preview to include the change.');});
})();
