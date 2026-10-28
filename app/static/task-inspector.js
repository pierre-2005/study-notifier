(() => {
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let panel=null,controller=null,returnFocus=null,revision=null,selectedId=null;
  const labels={todo:'To do',doing:'In progress',blocked:'Blocked',done:'Done'};
  function close(){controller?.abort();panel?.close();}
  async function open(id,trigger){
    controller?.abort();controller=new AbortController();selectedId=id;
    if(!panel){
      panel=document.createElement('dialog');panel.className='task-inspector';panel.setAttribute('aria-labelledby','inspector-title');
      panel.innerHTML='<header><span>Task</span><button type="button" data-inspector-close aria-label="Close task preview">×</button></header><div data-inspector-body></div>';
      document.body.append(panel);panel.querySelector('[data-inspector-close]').onclick=close;
      panel.addEventListener('close',()=>{controller?.abort();panel.remove();panel=null;returnFocus?.isConnected&&returnFocus.focus();});
      panel.addEventListener('click',e=>{if(e.target===panel&&e.clientX<panel.getBoundingClientRect().left)close();});
    }
    returnFocus=trigger||returnFocus;
    panel.querySelector('[data-inspector-body]').innerHTML='<h2 id="inspector-title">Loading task…</h2><p role="status">Loading…</p>';
    if(!panel.open)panel.showModal();
    try{
      const r=await fetch(`/api/v4/tasks/${id}`,{credentials:'same-origin',signal:controller.signal});
      if(!r.ok)throw Error(r.status===404?'Task not found.':'Could not load this task. Sign in again or retry.');
      const data=await r.json();if(selectedId!==id||!panel)return;paint(data);
    }catch(error){if(error.name!=='AbortError'&&panel)panel.querySelector('[data-inspector-body]').innerHTML=`<h2 id="inspector-title">Task unavailable</h2><p role="alert">${esc(error.message)}</p><a href="/life/tasks/${id}" data-no-preview>Open task page</a>`;}
  }
  function paint(data){
    const t=data.task;revision=t.updated_at;
    panel.querySelector('[data-inspector-body]').innerHTML=`<div class="inspector-project">${esc(data.project_name||'Personal task')}</div><h2 id="inspector-title">${esc(t.title)}</h2><form class="mlo-form" data-inspector-form><fieldset ${data.can_edit?'':'disabled'}><label>Task name<input name="title" required maxlength="240" value="${esc(t.title)}"></label><div class="inspector-fields"><label>Status<select name="status">${Object.entries(labels).map(([v,l])=>`<option value="${v}" ${t.status===v?'selected':''}>${l}</option>`).join('')}</select></label><label>Due date<input name="due_on" type="date" value="${esc(t.due_on)}"></label><label>Priority<select name="priority">${['low','normal','high','urgent'].map(v=>`<option value="${v}" ${t.priority===v?'selected':''}>${v[0].toUpperCase()+v.slice(1)}</option>`).join('')}</select></label><label>Estimate, minutes<input name="estimated_minutes" type="number" min="0" max="100000" value="${t.estimated_minutes}"></label></div><label>Notes<textarea name="description" rows="8" maxlength="10000">${esc(t.description)}</textarea></label><label>Repeat<select name="recurrence">${['none','daily','weekly','monthly'].map(v=>`<option value="${v}" ${t.recurrence===v?'selected':''}>${v==='none'?'Never':v[0].toUpperCase()+v.slice(1)}</option>`).join('')}</select></label></fieldset><p role="status" aria-live="polite" data-inspector-status>${data.can_edit?'':'Read-only project'}</p><div class="mlo-form-footer"><a href="/life/tasks/${t.id}" data-no-preview>Open full page ↗</a>${data.can_edit?'<button type="submit" class="mlo-btn mlo-primary">Save changes</button>':''}</div></form>${data.children.length?`<section class="inspector-subtasks"><h3>Subtasks</h3>${data.children.map(c=>`<a href="/life/tasks/${c.id}">${esc(c.title)}<small>${labels[c.status]}</small></a>`).join('')}</section>`:''}`;
    panel.querySelector('form').addEventListener('submit',async e=>{
      e.preventDefault();const button=e.target.querySelector('button[type=submit]');if(!button||button.disabled)return;button.disabled=true;
      const fd=new FormData(e.target),body=Object.fromEntries(fd);body.estimated_minutes=Number(body.estimated_minutes);body.due_on=body.due_on||null;body.expected_updated_at=revision;
      try{
        const response=await fetch(`/api/v4/tasks/${t.id}`,{method:'PATCH',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),result=await response.json();
        if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Check the task fields and try again.');
        document.dispatchEvent(new CustomEvent('mlo:task-updated',{detail:result.task}));
        if(!panel)return;
        paint(result);panel.querySelector('[data-inspector-status]').textContent='Saved.';
        panel.querySelector('[type=submit]')?.focus();
        document.querySelectorAll(`[data-task-id="${t.id}"] .mlo-task-name`).forEach(link=>{link.textContent=result.task.title;link.classList.toggle('is-done',result.task.status==='done');});
      }catch(error){if(panel){panel.querySelector('[data-inspector-status]').textContent=error.message;button.disabled=false;}}
    });
  }
  document.addEventListener('click',e=>{
    const link=e.target.closest('a[href]');if(!link||link.hasAttribute('data-no-preview')||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||e.button!==0)return;
    const match=link.getAttribute('href').match(/^\/life\/tasks\/(\d+)$/);if(!match)return;
    e.preventDefault();open(Number(match[1]),link);
  });
})();
