/* MLO v3.4: small, progressive interactions. All task changes persist on the server. */
(() => {
  'use strict';
  const qs = (selector, root=document) => root.querySelector(selector);
  const qsa = (selector, root=document) => Array.from(root.querySelectorAll(selector));
  const dialog = qs('[data-global-capture-dialog]');
  const form = qs('[data-global-capture-form]');
  const input = form?.querySelector('[name="title"]');
  let previouslyFocused = null;
  const show = () => {
    if (!dialog) return;
    previouslyFocused = document.activeElement;
    dialog.hidden = false;
    document.body.classList.add('mlo-modal-open');
    input?.focus();
  };
  const hide = () => {
    if (!dialog) return;
    dialog.hidden = true;
    document.body.classList.remove('mlo-modal-open');
    if (previouslyFocused?.isConnected) previouslyFocused.focus();
  };
  qsa('[data-global-capture-open]').forEach(button => button.addEventListener('click', show));
  qsa('[data-global-capture-close]').forEach(button => button.addEventListener('click', hide));
  dialog?.addEventListener('mousedown', event => { if (event.target === dialog) hide(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && dialog && !dialog.hidden) {event.preventDefault();hide();return;}
    if (event.key === 'Tab' && dialog && !dialog.hidden) {
      const focusable=qsa('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)', dialog);
      if (!focusable.length) return;
      if (event.shiftKey && document.activeElement === focusable[0]) {event.preventDefault(); focusable.at(-1).focus();}
      else if (!event.shiftKey && document.activeElement === focusable.at(-1)) {event.preventDefault();focusable[0].focus();}
      return;
    }
    if (!dialog || !dialog.hidden || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.key.toLowerCase() !== 'n') return;
    const element=event.target;
    if (element.closest('input,textarea,select,[contenteditable="true"],[role="dialog"]')) return;
    event.preventDefault();show();
  });
  const toast = (message, error=false) => {
    let node = qs('#mlo-notification-toast');
    if (!node) {node=document.createElement('div');node.id='mlo-notification-toast';node.setAttribute('role','status');node.setAttribute('aria-live','polite');document.body.append(node);}
    node.textContent=message;
    node.classList.toggle('mlo-toast-error',error);
    node.classList.add('mlo-toast-show');
    clearTimeout(node._hideTimeout);
    node._hideTimeout=setTimeout(()=>node.classList.remove('mlo-toast-show'),3600);
  };
  form?.addEventListener('submit',async event => {
    event.preventDefault();
    const title = input?.value.trim();
    if (!title) return;
    const submit=qs('[type="submit"]',form);
    const schedule=qs('[name="schedule"]',form)?.value;
    const due=qs('[name="due_on"]',form);
    const date = new Date();
    if (schedule === 'tomorrow') date.setDate(date.getDate()+1);
    if (due) due.value=schedule==='inbox'?'':`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
    submit.disabled=true;
    try {
      const response=await fetch(form.getAttribute('action') || form.action,{method:'POST',body:new FormData(form),credentials:'same-origin',headers:{'X-MLO-Action':'fetch'}});
      if (!response.ok) throw new Error(`Could not save (${response.status})`);
      const task=await response.json();
      form.reset();
      hide();
      toast('Task added to your list');
      document.dispatchEvent(new CustomEvent('mlo:task-created',{detail:task}));
      // Update the current dashboard immediately without fetching another full page.
      document.querySelectorAll('[data-open-task-count]').forEach(node=>{
        const value=Number(node.textContent.trim());
        if(Number.isFinite(value))node.textContent=String(value+1);
      });
      const card=qs('.mlo-widget-tasks');
      if(card){
        qs('.mlo-empty',card)?.remove();
        const row=document.createElement('div');row.className='mlo-task';row.dataset.taskId=String(task.id);
        const main=document.createElement('div');main.className='mlo-task-main';
        const link=document.createElement('a');link.href=`/life/tasks/${task.id}`;link.className='mlo-task-name';link.textContent=task.title;
        main.append(link);row.append(main);
        const top=qs('.mlo-task',card);
        if(top)top.before(row);else card.append(row);
      }
      // The currently displayed task list must reflect server-side filters and pagination.
      if (location.pathname === '/life/tasks') {
        const params=new URLSearchParams(location.search);
        if (!params.has('q') && !params.has('priority') && !params.has('project') && (!params.has('view') || ['all','open','inbox','today'].includes(params.get('view')))) {
          // Reload only the tasks view; other pages retain their state and UI.
          location.reload();
        }
      }
    } catch(err) { toast(err.message,true); }
    finally {submit.disabled=false;}
  });
  const bulkForm=qs('[data-bulk-form]');
  if (bulkForm) {
    const all=qs('[data-select-page]',bulkForm);
    const selected=qsa('[data-task-select]').filter(box=>!box.disabled);
    const action=qs('[data-bulk-submit]',bulkForm);
    const counter=qs('[data-selected-count]',bulkForm);
    const update=()=>{
      const n=selected.filter(box=>box.checked).length;
      if (counter) counter.textContent=String(n);
      if (action) action.disabled=n===0;
      if (all) {all.checked=n>0 && n===selected.length;all.indeterminate=n>0 && n<selected.length;}
    };
    selected.forEach(box=>box.addEventListener('change',update));
    all?.addEventListener('change',()=>{selected.forEach(box=>{box.checked=all.checked;});update();});
    bulkForm.addEventListener('submit',event=>{if (!selected.some(x=>x.checked)){event.preventDefault();toast('Select at least one task first',true);}});
    update();
  }
})();
