(() => {
  'use strict';
  // Fast task feedback, rolled back on errors; traditional forms work with JS disabled.
  document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-inline-task]');
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector('.mlo-check');
    const row = form.closest('.mlo-task');
    const name = row?.querySelector('.mlo-task-name');
    const next = form.querySelector('[name=status]').value;
    button.disabled = true;
    button.classList.toggle('is-done', next === 'done');
    button.textContent = next === 'done' ? '✓' : '';
    name?.classList.toggle('is-done', next === 'done');
    try {
      const resp = await fetch(form.action,{method:'POST',headers:{'X-MLO-Action':'fetch'},body:new FormData(form),credentials:'same-origin'});
      if (!resp.ok) throw new Error(`Save failed (${resp.status})`);
      form.querySelector('[name=status]').value = next === 'done' ? 'todo' : 'done';
      document.dispatchEvent(new CustomEvent('mlo:task-saved'));
    } catch (err) {
      button.classList.toggle('is-done', next !== 'done');
      button.textContent = next !== 'done' ? '✓' : '';
      name?.classList.toggle('is-done', next !== 'done');
      alert(`Couldn't save the task. ${err.message}. Try again.`);
    } finally { button.disabled = false; }
  });
  // Quick capture: save without a navigation; retain full form fallback when JS is off.
  document.addEventListener('submit', async (event) => {
    const form=event.target.closest('[data-quick-form]');
    if(!form) return;
    event.preventDefault();
    const input=form.querySelector('[name=title]');
    const button=form.querySelector('[type=submit]');
    const title=input.value.trim();
    if(!title) return;
    button.disabled=true;button.classList.add('mlo-saving');
    try {
      const response=await fetch(form.action,{method:'POST',credentials:'same-origin',headers:{'X-MLO-Action':'fetch'},body:new FormData(form)});
      if(!response.ok)throw new Error(`Save failed (${response.status})`);
      const item=await response.json();
      input.value='';
      const board=document.querySelector('.mlo-board-column');
      const taskSurface=document.querySelector('.mlo-surface:has(.mlo-task)') || document.querySelector('.mlo-two-thirds > .mlo-surface') || document.querySelector('.mlo-two > .mlo-surface');
      if(board){
        const a=document.createElement('a');a.href=`/life/tasks/${item.id}`;a.className='mlo-board-ticket';a.textContent=title;board.prepend(a);
      }else if(taskSurface){
        const row=document.createElement('div');row.className='mlo-task';row.dataset.taskId=String(item.id);
        const toggle=document.createElement('form');toggle.method='post';toggle.action=`/life/tasks/${item.id}/status`;toggle.dataset.inlineTask='';
        const status=document.createElement('input');status.type='hidden';status.name='status';status.value='done';toggle.append(status);
        const next=document.createElement('input');next.type='hidden';next.name='next_page';next.value=location.pathname+location.search;toggle.append(next);
        const check=document.createElement('button');check.type='submit';check.className='mlo-check';check.title='Complete task';check.setAttribute('aria-label',`Complete ${title}`);toggle.append(check);
        const main=document.createElement('div');main.className='mlo-task-main';const link=document.createElement('a');link.className='mlo-task-name';link.href=`/life/tasks/${item.id}`;link.textContent=title;main.append(link);
        const arrow=document.createElement('a');arrow.className='mlo-task-arrow';arrow.href=link.href;arrow.textContent='↗';arrow.setAttribute('aria-label','Open task');
        row.append(toggle,main,arrow);
        const initial=taskSurface.querySelector('.mlo-task,.mlo-empty');
        if(initial?.classList.contains('mlo-empty'))initial.remove();
        const first=taskSurface.querySelector('.mlo-task');
        if(first)first.before(row);else taskSurface.append(row);
      }
      const stat=document.querySelector('.mlo-stat strong');
      if(stat){const value=parseInt(stat.textContent,10);if(Number.isFinite(value))stat.textContent=String(value+1);}
      input.focus();
    } catch(err){alert(`Couldn't save your task. ${err.message}`);}
    finally {button.disabled=false;button.classList.remove('mlo-saving');}
  });
  const select = document.querySelector('[data-focus-duration]');
  const clock = document.querySelector('[data-focus-clock]');
  if (select && clock) select.addEventListener('change',()=>{clock.textContent=`${String(select.value).padStart(2,'0')}:00`;const kind=document.querySelector('[data-focus-kind]');if(kind)kind.value=select.value==='5'?'break':'focus';});
})();
if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
  window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js').catch(()=>{}));
}
// Connectivity cue only: edits still need server connectivity in this release.
(() => {
  const banner=document.createElement('div');
  banner.className='mlo-offline-banner';banner.textContent='You are offline. Saved information may be unavailable and changes will not sync.';
  banner.setAttribute('role','status');
  document.body.appendChild(banner);
  function update(){banner.hidden=navigator.onLine;}
  window.addEventListener('online',update);window.addEventListener('offline',update);update();
})();
