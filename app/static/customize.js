(() => {
  'use strict';
  const nav = document.querySelector('[data-custom-nav]');
  const dashboard = document.querySelector('[data-widget-grid]');
  if (!nav && !dashboard) return;
  const preferences = {nav_order: [],widget_order: [],nav_labels: {},nav_hidden: [],widget_hidden: []};
  let isEditingNav = false, isEditingWidgets = false, saveTimer = null;
  const valid = (arr) => Array.isArray(arr) ? arr.filter(x => typeof x === 'string') : [];
  const allNav = () => [...document.querySelectorAll('[data-nav-group] [data-nav-key]')];
  const allWidgets = () => [...document.querySelectorAll('[data-widget-grid] [data-widget]')];
  const keepOrder = (order,keys) => [...order.filter(key => keys.includes(key)),...keys.filter(key => !order.includes(key))];
  const navKeys = () => allNav().map(e => e.dataset.navKey);
  const widgetKeys = () => allWidgets().map(e => e.dataset.widget);
  const save = () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try {
        const response = await fetch('/life/layout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(preferences),credentials:'same-origin'});
        if(!response.ok) throw new Error('Save failed');
      } catch(err) {
        console.error('Layout save failed',err);
        const status=document.querySelector('[data-layout-status]');
        if(status)status.textContent='Could not save changes. Reload and try again.';
      }
    },150);
  };
  function reorder() {
    for (const group of document.querySelectorAll('[data-nav-group]')) {
      const children=[...group.querySelectorAll('[data-nav-key]')];
      children.sort((a,b)=>preferences.nav_order.indexOf(a.dataset.navKey)-preferences.nav_order.indexOf(b.dataset.navKey));
      for(const child of children)group.appendChild(child);
    }
    if(dashboard){const children=allWidgets().sort((a,b)=>preferences.widget_order.indexOf(a.dataset.widget)-preferences.widget_order.indexOf(b.dataset.widget));children.forEach(child=>dashboard.appendChild(child));}
  }
  function paint() {
    preferences.nav_order = keepOrder(valid(preferences.nav_order),navKeys());
    preferences.widget_order = keepOrder(valid(preferences.widget_order),widgetKeys());
    reorder();
    allNav().forEach(el => {
      const key=el.dataset.navKey;
      const label=el.querySelector('[data-nav-label]');
      if(label)label.textContent=preferences.nav_labels[key] || el.dataset.navDefault;
      el.hidden=preferences.nav_hidden.includes(key) && !isEditingNav;
      el.draggable=isEditingNav;
    });
    allWidgets().forEach(el => {
      el.hidden=preferences.widget_hidden.includes(el.dataset.widget);
      el.draggable=isEditingWidgets;
      const handle=el.querySelector('.mlo-widget-handle');
      if(handle)handle.tabIndex=isEditingWidgets?0:-1;
    });
    if(isEditingNav)buildNavEditor();
    if(isEditingWidgets)buildWidgetEditor();
  }
  function moveKey(list,key,direction) {
    const index=list.indexOf(key), newIndex=index+direction;
    if(index<0 || newIndex<0 || newIndex>=list.length)return;
    [list[index],list[newIndex]]=[list[newIndex],list[index]];
    paint();save();
  }
  function buildNavEditor() {
    const list=document.querySelector('[data-nav-editor-list]');
    if(!list)return;
    list.replaceChildren();
    const grouped=[['Navigation',allNav().filter(el=>el.closest('[data-nav-group]').dataset.navGroup==='core')],['My spaces',allNav().filter(el=>el.closest('[data-nav-group]').dataset.navGroup==='spaces')]];
    for(const [title,rows] of grouped) {
      if(!rows.length)continue;
      const h=document.createElement('div');h.className='mlo-nav-edit-group';h.textContent=title;list.append(h);
      for(const el of rows) {
        const key=el.dataset.navKey;
        const item=document.createElement('div');item.className='mlo-nav-edit-item';
        const input=document.createElement('input');input.type='text';input.maxLength=36;input.value=preferences.nav_labels[key] || el.dataset.navDefault;input.setAttribute('aria-label',`Rename ${el.dataset.navDefault}`);
        input.addEventListener('change',()=>{let value=input.value.trim().slice(0,36);if(value && value!==el.dataset.navDefault)preferences.nav_labels[key]=value;else delete preferences.nav_labels[key];paint();save();});
        const hide=document.createElement('input');hide.type='checkbox';hide.checked=!preferences.nav_hidden.includes(key);hide.setAttribute('aria-label',`Show ${el.dataset.navDefault}`);hide.addEventListener('change',()=>{preferences.nav_hidden=preferences.nav_hidden.filter(k=>k!==key);if(!hide.checked)preferences.nav_hidden.push(key);paint();save();});
        const left=document.createElement('button');left.type='button';left.textContent='↑';left.setAttribute('aria-label',`Move ${el.dataset.navDefault} up`);left.onclick=()=>moveKey(preferences.nav_order,key,-1);
        const right=document.createElement('button');right.type='button';right.textContent='↓';right.setAttribute('aria-label',`Move ${el.dataset.navDefault} down`);right.onclick=()=>moveKey(preferences.nav_order,key,1);
        item.append(hide,input,left,right);list.append(item);
      }
    }
  }
  function buildWidgetEditor() {
    const list=document.querySelector('[data-widget-toggles]');if(!list)return;
    list.replaceChildren();
    for(const el of allWidgets()) {
      const id=el.dataset.widget;
      const label=document.createElement('label');label.className='mlo-toggle-widget';
      const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=!preferences.widget_hidden.includes(id);
      checkbox.onchange=()=>{preferences.widget_hidden=preferences.widget_hidden.filter(x=>x!==id);if(!checkbox.checked)preferences.widget_hidden.push(id);paint();save();};
      const name=document.createElement('span');name.textContent=el.querySelector('h2')?.textContent || id;
      const up=document.createElement('button');up.type='button';up.textContent='↑';up.setAttribute('aria-label',`Move ${name.textContent} up`);up.onclick=()=>moveKey(preferences.widget_order,id,-1);
      const down=document.createElement('button');down.type='button';down.textContent='↓';down.setAttribute('aria-label',`Move ${name.textContent} down`);down.onclick=()=>moveKey(preferences.widget_order,id,1);
      label.append(checkbox,name,up,down);list.append(label);
    }
  }
  async function load() {
    try {
      const response=await fetch('/life/layout',{credentials:'same-origin',cache:'no-store'});
      if(!response.ok)throw new Error('Layout unavailable');
      Object.assign(preferences, await response.json());
    } catch(err){console.warn('Using default layout',err);}
    paint();
  }
  document.querySelector('[data-nav-edit]')?.addEventListener('click',()=>{
    isEditingNav=!isEditingNav;
    document.querySelector('[data-nav-settings]').hidden=!isEditingNav;
    nav?.classList.toggle('is-reordering',isEditingNav);
    paint();
  });
  document.querySelectorAll('[data-nav-edit-close]').forEach(button=>button.addEventListener('click',()=>{
    isEditingNav=false;document.querySelector('[data-nav-settings]').hidden=true;nav?.classList.remove('is-reordering');paint();
  }));
  document.querySelector('[data-nav-reset]')?.addEventListener('click',()=>{
    preferences.nav_order=navKeys();preferences.nav_hidden=[];preferences.nav_labels={};paint();save();
  });
  document.querySelector('[data-dashboard-edit]')?.addEventListener('click',e=>{
    isEditingWidgets=!isEditingWidgets;
    const panel=document.querySelector('[data-widget-settings]');if(panel)panel.hidden=!isEditingWidgets;
    dashboard.classList.toggle('is-reordering',isEditingWidgets);
    e.currentTarget.setAttribute('aria-expanded',String(isEditingWidgets));paint();
  });
  document.querySelector('[data-dashboard-done]')?.addEventListener('click',()=>{
    isEditingWidgets=false;document.querySelector('[data-widget-settings]').hidden=true;
    dashboard.classList.remove('is-reordering');paint();
  });
  document.querySelector('[data-widget-reset]')?.addEventListener('click',()=>{
    preferences.widget_order=widgetKeys();preferences.widget_hidden=[];paint();save();
  });
  let dragging=null;
  document.addEventListener('dragstart',e=>{
    const item=e.target.closest('[data-widget],[data-nav-key]');
    if(!item || !(item.matches('[data-widget]')?isEditingWidgets:isEditingNav))return;
    dragging=item;
    e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain','mlo-item');item.classList.add('mlo-dragging');
  });
  document.addEventListener('dragover',e=>{
    const target=e.target.closest('[data-widget],[data-nav-key]');
    if(!dragging || !target || dragging===target)return;
    if(dragging.hasAttribute('data-widget')!==target.hasAttribute('data-widget'))return;
    if(dragging.hasAttribute('data-nav-key') && dragging.parentElement!==target.parentElement)return;
    e.preventDefault();e.dataTransfer.dropEffect='move';
  });
  document.addEventListener('drop',e=>{
    const target=e.target.closest('[data-widget],[data-nav-key]');
    if(!dragging || !target || dragging===target || dragging.parentElement!==target.parentElement)return;
    e.preventDefault();
    const keyname=dragging.hasAttribute('data-widget')?'widget':'nav';
    const key=keyname==='widget'?'widget_order':'nav_order';
    const id=dragging.dataset[keyname==='widget'?'widget':'navKey'];
    const destination=target.dataset[keyname==='widget'?'widget':'navKey'];
    preferences[key]=preferences[key].filter(x=>x!==id);
    preferences[key].splice(preferences[key].indexOf(destination),0,id);
    paint();save();
  });
  document.addEventListener('dragend',()=>{
    dragging?.classList.remove('mlo-dragging');dragging=null;
  });
  document.addEventListener('keydown',e=>{
    const handle=e.target.closest('.mlo-widget-handle');
    if(!handle || !isEditingWidgets || !['ArrowUp','ArrowDown'].includes(e.key))return;
    e.preventDefault();
    const key=handle.closest('[data-widget]')?.dataset.widget;
    if(key)moveKey(preferences.widget_order,key,e.key==='ArrowUp'?-1:1);
  });
  document.querySelectorAll('[data-quick-timer]').forEach(timer=>{
    const output=timer.querySelector('[data-mini-clock]');const form=timer.closest('[data-widget]').querySelector('[data-mini-minutes]');
    for(const btn of timer.querySelectorAll('[data-focus-adjust]'))btn.addEventListener('click',()=>{
      const duration=Math.min(180,Math.max(5,Number(form.value)+Number(btn.dataset.focusAdjust)));
      form.value=String(duration);output.textContent=duration+' min';
    });
  });
  load();
})();
