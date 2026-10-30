(() => {
  'use strict';
  const root=document.getElementById('mlo-v37-board');
  if(!root)return;
  const pid=Number(root.dataset.projectId),editable=root.dataset.editable==='true';
  const statuses=[['todo','To do'],['doing','In progress'],['blocked','Blocked'],['done','Done']];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let loadSequence=0;
  let board=JSON.parse(document.getElementById('mlo-board-initial')?.textContent||'null'),query='',busy=false,dragged=null,pointer=null;
  const expanded=new Set();
  const message=document.createElement('p');message.className='v37-message';message.setAttribute('role','status');message.setAttribute('aria-live','polite');root.after(message);
  function flat(){const all=[];function walk(n){all.push(n);n.children.forEach(walk)}if(board)statuses.forEach(([s])=>board.columns[s].forEach(walk));return all}
  const task=id=>flat().find(t=>t.id===Number(id));
  const matches=n=>n.title.toLocaleLowerCase().includes(query.toLocaleLowerCase())||n.children.some(matches);
  function actions(t){return !editable?'':`<details class="v37-task-actions"><summary aria-label="Actions for ${esc(t.title)}">⋯</summary><div class="v37-action-menu"><label>Status<select data-status-task="${t.id}" data-focus="status-${t.id}" aria-label="Status for ${esc(t.title)}">${statuses.map(([s,l])=>`<option value="${s}" ${s===t.status?'selected':''}>${l}</option>`).join('')}</select></label><button type="button" data-parent="${t.id}">Move under a task…</button>${t.parent_id?`<button type="button" data-unnest="${t.id}">Make top-level task</button>`:''}<button type="button" data-add-child="${t.id}">Add subtask</button><div class="v37-reorder"><button type="button" data-up="${t.id}" data-focus="up-${t.id}" aria-label="Move ${esc(t.title)} earlier">↑ Earlier</button><button type="button" data-down="${t.id}" data-focus="down-${t.id}" aria-label="Move ${esc(t.title)} later">↓ Later</button></div></div></details>`}
  function node(t,depth=0){return `<article class="${depth?'v37-child-task':'v37-ticket'}" data-id="${t.id}" ${editable?'draggable="true"':''}><div class="v37-card-head">${editable?`<button class="v37-drag-handle" draggable="true" type="button" aria-label="Drag ${esc(t.title)}; use task actions to reorder with a keyboard" title="Drag task" data-handle="${t.id}">⠿</button><button type="button" class="mlo-check ${t.status==='done'?'is-done':''}" data-toggle="${t.id}" data-focus="toggle-${t.id}" aria-pressed="${t.status==='done'}" aria-label="${t.status==='done'?'Reopen':'Complete'} ${esc(t.title)}">${t.status==='done'?'✓':''}</button>`:''}<a data-focus="open-${t.id}" class="v37-task-title ${t.status==='done'?'v37-done':''}" href="/life/tasks/${t.id}">${esc(t.title)}</a>${actions(t)}</div><div class="v37-task-meta">${t.due_on?`<span>◷ ${esc(t.due_on)}</span>`:''}${['high','urgent'].includes(t.priority)?`<span class="v37-priority">${esc(t.priority)}</span>`:''}${depth?`<span>${esc(statuses.find(([s])=>s===t.status)?.[1])}</span>`:''}</div>${t.children.length?`<details class="v37-subtasks" data-expanded="${t.id}" ${expanded.has(t.id)||query?'open':''}><summary>${t.subtask_done} of ${t.subtask_total} subtasks complete</summary><div class="v37-child-list">${t.children.map(c=>node(c,depth+1)).join('')}</div></details>`:''}</article>`}
  function revealColumn(status){const columns=root.querySelector('.v37-columns'),column=root.querySelector(`[data-column="${status}"]`);if(columns&&column)columns.scrollTo({left:column.offsetLeft-columns.firstElementChild.offsetLeft,behavior:'instant'});}
  function lock(locked){root.querySelectorAll('[data-toggle],[data-up],[data-down],[data-parent],[data-unnest],[data-add-child],[data-handle],select[data-status-task]').forEach(control=>control.disabled=locked);}
  function paint(focusKey=null,columnStatus=null){
    if(!board)return;
    document.querySelectorAll('[data-project-task-total]').forEach(n=>n.textContent=board.total);document.querySelectorAll('[data-project-task-done]').forEach(n=>n.textContent=flat().filter(t=>t.status==='done').length);
    const scrollLeft=root.querySelector('.v37-columns')?.scrollLeft||0;
    root.innerHTML=`<div class="v37-board-top"><label><span class="sr-only">Search project tasks</span><input id="v37-filter" type="search" placeholder="Search tasks…" value="${esc(query)}" autocomplete="off"></label><span class="v37-total">${board.total} tasks</span></div><nav class="v37-column-tabs" aria-label="Board columns">${statuses.map(([s,l])=>`<button type="button" data-column-jump="${s}">${l}<span>${board.columns[s].length}</span></button>`).join('')}</nav><div class="v37-columns">${statuses.map(([s,l])=>{const tasks=board.columns[s].filter(matches);return `<section class="v37-column" data-column="${s}" aria-label="${l}"><header><h3><i class="v37-status-dot ${s}" aria-hidden="true"></i>${l}</h3><span>${tasks.length}</span></header><div class="v37-drop">${tasks.map(t=>node(t)).join('')||'<p class="v37-empty-column">'+(query?'No matches':'No tasks')+'</p>'}</div></section>`}).join('')}</div>`;
    root.querySelector('.v37-columns').scrollLeft=scrollLeft;
    if(columnStatus&&innerWidth<=700)revealColumn(columnStatus);
    root.querySelectorAll('[data-expanded]').forEach(d=>d.addEventListener('toggle',()=>{if(d.open)expanded.add(Number(d.dataset.expanded));else expanded.delete(Number(d.dataset.expanded))}));
    root.querySelectorAll('.v37-task-actions').forEach(d=>d.addEventListener('toggle',()=>{
      if(!d.open)return;
      root.querySelectorAll('.v37-task-actions[open]').forEach(other=>{if(other!==d)other.open=false;});
      const menu=d.querySelector('.v37-action-menu'),bounds=d.querySelector('summary').getBoundingClientRect();
      menu.style.right='auto';menu.style.left=Math.max(8,Math.min(bounds.right-menu.offsetWidth,innerWidth-menu.offsetWidth-8))+'px';
      menu.style.top=Math.max(8,Math.min(bounds.bottom+5,innerHeight-menu.offsetHeight-8))+'px';
    }));
    lock(busy);
    if(focusKey){const focus=root.querySelector(`[data-focus="${CSS.escape(focusKey)}"]`);const actions=focus?.closest('.v37-task-actions');if(actions)actions.open=true;focus?.focus();}
  }
  async function load(focusKey=null){const sequence=++loadSequence;const r=await fetch(`/api/v4/projects/${pid}/board`,{credentials:'same-origin'});if(!r.ok||!r.headers.get('content-type')?.includes('application/json'))throw Error('Could not load the board. Check your connection or sign in again.');const result=await r.json();if(sequence!==loadSequence)return;board=result;paint(focusKey)}
  async function change(kind,body,focusKey){
    if(busy)return;busy=true;root.setAttribute('aria-busy','true');lock(true);message.textContent='Saving…';
    const previous=structuredClone(board),current=task(body.task_id),revision=current?.updated_at,release=window.MLOTasks?.begin(body.task_id);
    if(kind==='move'&&current&&current.status!==body.status){if(!current.parent_id){board.columns[current.status]=board.columns[current.status].filter(n=>n.id!==current.id);board.columns[body.status].push(current);}current.status=body.status;paint(focusKey,current.parent_id?null:body.status);}
    try{
      const r=await fetch(`/api/v4/projects/${pid}/${kind}`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({...body,expected_updated_at:revision})});
      if(!r.headers.get('content-type')?.includes('application/json'))throw Error('Sign in again to save your changes.');
      const data=await r.json();
      if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'The change could not be saved.');
      board=data.board;paint(focusKey,current?.parent_id?null:body.status);message.textContent='Saved.';
    }catch(error){board=previous;paint(focusKey);message.textContent=error.message;try{await load(focusKey)}catch(_){} }
    finally{release?.();busy=false;lock(false);root.removeAttribute('aria-busy');if(focusKey)root.querySelector(`[data-focus="${CSS.escape(focusKey)}"]`)?.focus();}
  }
  root.addEventListener('input',e=>{if(e.target.id!=='v37-filter')return;query=e.target.value;const position=e.target.selectionStart;paint();const input=root.querySelector('#v37-filter');input.focus();input.setSelectionRange(position,position)});
  root.addEventListener('change',e=>{if(e.target.dataset.statusTask)change('move',{task_id:Number(e.target.dataset.statusTask),status:e.target.value},e.target.dataset.focus)});
  function parentDialog(t){
    const dialog=document.createElement('dialog');dialog.className='v37-parent-dialog';
    const descendants=new Set();function walk(n){descendants.add(n.id);n.children.forEach(walk)}walk(t);
    dialog.innerHTML=`<form><h2>Move task</h2><p>${esc(t.title)}</p><label>Parent task<select name="parent"><option value="">No parent</option>${flat().filter(n=>!descendants.has(n.id)).map(n=>`<option value="${n.id}" ${t.parent_id===n.id?'selected':''}>${esc(n.title)}</option>`).join('')}</select></label><div class="mlo-form-footer"><button type="button" data-cancel>Cancel</button><button class="mlo-btn mlo-primary" type="submit">Move task</button></div></form>`;
    document.body.append(dialog);dialog.showModal();
    dialog.querySelector('[data-cancel]').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>dialog.remove());
    dialog.querySelector('form').addEventListener('submit',e=>{e.preventDefault();const value=new FormData(e.target).get('parent');dialog.close();change('nest',{task_id:t.id,parent_id:value?Number(value):null})});
  }
  function addDialog(t){
    const dialog=document.createElement('dialog');dialog.className='v37-parent-dialog';dialog.innerHTML=`<form><h2>Add subtask</h2><label>Task name<input name="title" required maxlength="240" autocomplete="off"></label><p role="alert"></p><div class="mlo-form-footer"><button type="button" data-cancel>Cancel</button><button type="submit" class="mlo-btn mlo-primary">Add subtask</button></div></form>`;document.body.append(dialog);dialog.showModal();dialog.querySelector('input').focus();dialog.querySelector('[data-cancel]').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());
    dialog.querySelector('form').addEventListener('submit',async e=>{e.preventDefault();const button=e.target.querySelector('[type=submit]');if(button.disabled)return;button.disabled=true;const body=new URLSearchParams({title:new FormData(e.target).get('title'),parent_id:t.id,project_id:pid});try{const r=await fetch('/life/tasks',{method:'POST',credentials:'same-origin',headers:{'X-MLO-Action':'fetch'},body});if(!r.ok){const err=await r.json();throw Error(err.detail||'Could not add subtask')}dialog.close();expanded.add(t.id);await load();message.textContent='Subtask added.'}catch(error){e.target.querySelector('[role=alert]').textContent=error.message;button.disabled=false}});
  }
  root.addEventListener('click',e=>{
    const jump=e.target.closest('[data-column-jump]');if(jump){revealColumn(jump.dataset.columnJump);return;}
    const button=e.target.closest('button');if(!button||busy||!editable)return;
    const id=button.dataset.toggle||button.dataset.up||button.dataset.down||button.dataset.parent||button.dataset.unnest||button.dataset.addChild;if(!id)return;
    const t=task(id);if(!t)return;
    if(button.dataset.toggle)change('move',{task_id:t.id,status:t.status==='done'?'todo':'done'},button.dataset.focus);
    else if(button.dataset.parent)parentDialog(t);
    else if(button.dataset.unnest)change('nest',{task_id:t.id,parent_id:null});
    else if(button.dataset.addChild)addDialog(t);
    else {const siblings=flat().filter(n=>n.parent_id===t.parent_id&&n.status===t.status);const index=siblings.findIndex(n=>n.id===t.id);const offset=button.dataset.up?-1:1;if(index+offset<0||index+offset>=siblings.length){message.textContent='This task is already at the edge of the list.';return;}change('move',{task_id:t.id,status:t.status,before_task_id:offset<0?siblings[index-1].id:siblings[index+2]?.id??null},button.dataset.focus);}
  });
  function drop(x,y,id,nest=false){const target=document.elementFromPoint(x,y);const column=target?.closest('[data-column]');if(!column)return;const targetTask=target.closest('[data-id]'),before=targetTask?task(targetTask.dataset.id):null,t=task(id);if(!t||before?.id===t.id)return;if(nest&&before){change('nest',{task_id:t.id,parent_id:before.id});return;}if(before&&before.parent_id!==t.parent_id){message.textContent='Use Move under a task to change this task’s parent.';return;}change('move',{task_id:t.id,status:column.dataset.column,before_task_id:before?.id??null});}
  root.addEventListener('dragstart',e=>{const card=e.target.closest('[data-id]');if(!editable||!card||busy||e.target.closest('input,select,textarea,button:not([data-handle]),summary')){e.preventDefault();return;}dragged=Number(card.dataset.id);e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',String(dragged));root.classList.add('v37-dragging')});
  root.addEventListener('dragover',e=>{if(dragged&&e.target.closest('[data-column]'))e.preventDefault()});
  root.addEventListener('drop',e=>{if(!dragged)return;e.preventDefault();drop(e.clientX,e.clientY,dragged,e.shiftKey);dragged=null;root.classList.remove('v37-dragging')});
  root.addEventListener('dragend',()=>{dragged=null;root.classList.remove('v37-dragging')});
  root.addEventListener('pointerdown',e=>{const handle=e.target.closest('[data-id]');if(e.pointerType==='mouse'||!editable||!handle||busy||e.target.closest('input,select,textarea,button:not([data-handle]),summary'))return;pointer={id:Number(handle.dataset.id),x:e.clientX,y:e.clientY,moved:false,handle,pointerId:e.pointerId};if(e.target.closest('[data-handle]')){pointer.ready=true;handle.setPointerCapture(e.pointerId);}pointer.hold=setTimeout(()=>{if(pointer){pointer.ready=true;handle.setPointerCapture(e.pointerId);root.classList.add('v37-dragging');}},220)});
  function touchScroll(time){
    if(!pointer?.moved)return;
    const columns=root.querySelector('.v37-columns'),bounds=columns.getBoundingClientRect();
    const speed=500*Math.min(32,time-(pointer.lastFrame||time-16))/1000;
    if(pointer.currentX>bounds.right-35)columns.scrollLeft+=speed;
    if(pointer.currentX<bounds.left+35)columns.scrollLeft-=speed;
    pointer.lastFrame=time;pointer.raf=requestAnimationFrame(touchScroll);
  }
  root.addEventListener('pointermove',e=>{if(!pointer)return;if(!pointer.ready){if(Math.hypot(e.clientX-pointer.x,e.clientY-pointer.y)>8){clearTimeout(pointer.hold);pointer=null;}return;}e.preventDefault();pointer.currentX=e.clientX;pointer.moved ||= Math.hypot(e.clientX-pointer.x,e.clientY-pointer.y)>8;if(pointer.moved){root.classList.add('v37-dragging');if(!pointer.raf)pointer.raf=requestAnimationFrame(touchScroll);}});
  root.addEventListener('pointerup',e=>{if(!pointer)return;const p=pointer;clearTimeout(p.hold);cancelAnimationFrame(p.raf);pointer=null;if(p.moved){root.dataset.suppressClick='1';drop(e.clientX,e.clientY,p.id);setTimeout(()=>delete root.dataset.suppressClick,0);}root.classList.remove('v37-dragging')});
  root.addEventListener('pointercancel',()=>{clearTimeout(pointer?.hold);cancelAnimationFrame(pointer?.raf);pointer=null;root.classList.remove('v37-dragging')});
  root.addEventListener('click',e=>{if(root.dataset.suppressClick){e.preventDefault();e.stopImmediatePropagation();}},true);
  document.addEventListener('mlo:task-created',e=>{const item=e.detail;if(Number(item.project_id)!==pid||task(item.id))return;const node={...item,children:[],subtask_total:0,subtask_done:0};const parent=task(item.parent_id);if(parent){parent.children.push(node);expanded.add(parent.id);for(const n of flat()){n.subtask_total=n.children.reduce((s,c)=>s+1+c.subtask_total,0);}}else board.columns.todo.push(node);board.total++;paint(null,'todo');message.textContent='Task added.';});
  document.addEventListener('mlo:task-updated',e=>load(e.detail?.id?'open-'+e.detail.id:null).catch(error=>message.textContent=error.message));
  document.addEventListener('click',e=>{if(!e.target.closest('.v37-task-actions'))root.querySelectorAll('.v37-task-actions[open]').forEach(d=>d.open=false);});
  root.addEventListener('scroll',e=>{if(e.target.classList?.contains('v37-columns'))root.querySelectorAll('.v37-task-actions[open]').forEach(d=>d.open=false);},true);
  if(board)paint();else load().catch(error=>{message.textContent=error.message});
})();
