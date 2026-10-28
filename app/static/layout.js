/* MLO 3.3: persisted, account-scoped layout editor. Native drag handles + touch controls. */
(() => {
  'use strict';
  const nav = document.querySelector('[data-custom-nav]');
  const grid = document.querySelector('[data-widget-grid]');
  if (!nav && !grid) return;

  const initialNav = [...document.querySelectorAll('[data-nav-group] [data-nav-key]')].map(e => e.dataset.navKey);
  const initialWidgets = [...document.querySelectorAll('[data-widget-grid] [data-widget]')].map(e => e.dataset.widget);
  const defaults = () => ({nav_order: [...initialNav], widget_order: [...initialWidgets], nav_labels: {}, nav_hidden: [], widget_hidden: [],widget_sizes: {}});
  const prefs = defaults();
  let navEditing = false;
  let widgetEditing = false;
  let pending = null;
  let inflight = null;
  let dirty = false;
  let dragElement = null;
  let dragGroup = null;
  const status = document.querySelector('[data-layout-status]');
  const navItems = () => [...document.querySelectorAll('[data-nav-group] [data-nav-key]')];
  const widgets = () => [...document.querySelectorAll('[data-widget-grid] [data-widget]')];
  const ordered = (values, available) => [...new Set([...(Array.isArray(values) ? values : []), ...available])].filter(k => available.includes(k));
  const currentNavKeys = () => navItems().map(e => e.dataset.navKey);
  const currentWidgetKeys = () => widgets().map(e => e.dataset.widget);
  const setStatus = (message, error = false) => {if(status) {status.textContent = message;status.classList.toggle('mlo-error',error);}};

  async function flush() {
    clearTimeout(pending);
    if (inflight) {dirty = true; return;}
    const payload = JSON.stringify(prefs);
    setStatus('Saving…');
    try {
      inflight = fetch('/life/layout', {method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:payload});
      const response = await inflight;
      if (!response.ok) throw new Error('HTTP ' + response.status);
      setStatus('Saved');
    } catch (error) {
      setStatus('Could not save layout. Try again.',true);
      console.error('MLO layout save:',error);
      dirty = false;
    } finally {
      inflight = null;
      if(dirty){dirty=false;queueSave();}
    }
  }
  function queueSave() {setStatus('Unsaved changes');clearTimeout(pending);pending=setTimeout(flush,250);}
  function orderDom(items, key, parent) {
    items.sort((a,b) => prefs[key].indexOf(a.dataset[key==='widget_order'?'widget':'navKey']) - prefs[key].indexOf(b.dataset[key==='widget_order'?'widget':'navKey']));
    items.forEach(el=>parent.append(el));
  }
  function normalize() {
    prefs.nav_order=ordered(prefs.nav_order,currentNavKeys());
    prefs.widget_order=ordered(prefs.widget_order,currentWidgetKeys());
    prefs.nav_hidden=prefs.nav_hidden.filter(k=>currentNavKeys().includes(k));
    prefs.widget_hidden=prefs.widget_hidden.filter(k=>currentWidgetKeys().includes(k));
  }
  function render() {
    normalize();
    document.querySelectorAll('[data-nav-group]').forEach(group=>orderDom([...group.querySelectorAll('[data-nav-key]')], 'nav_order', group));
    if(grid)orderDom(widgets(),'widget_order',grid);
    for(const el of navItems()) {
      const key=el.dataset.navKey;
      const label=el.querySelector('[data-nav-label]');
      if(label)label.textContent=prefs.nav_labels[key]||el.dataset.navDefault;
      el.title=prefs.nav_labels[key]||el.dataset.navDefault;
      el.hidden=prefs.nav_hidden.includes(key) && !navEditing;
      el.draggable=false;
      const handle=el.querySelector('.mlo-nav-drag');
      if(handle){handle.draggable=navEditing;handle.setAttribute('aria-hidden',String(!navEditing));}
    }
    for(const el of widgets()) {
      el.hidden=prefs.widget_hidden.includes(el.dataset.widget) && !widgetEditing;
      el.classList.toggle('mlo-widget-inactive',prefs.widget_hidden.includes(el.dataset.widget) && widgetEditing);
      el.draggable=false;
      const size=prefs.widget_sizes?.[el.dataset.widget];
      if(size)el.dataset.widgetWidth=String(size);else delete el.dataset.widgetWidth;
      const handle=el.querySelector('.mlo-widget-handle');
      if(handle){handle.draggable=widgetEditing;handle.tabIndex=widgetEditing?0:-1;handle.title=widgetEditing?'Drag to move; or use arrow keys':'Arrange dashboard to move widgets';}
    }
    if(navEditing)renderNavEditor();
    if(widgetEditing)renderWidgetEditor();
  }
  function move(orderName,id,relative,withinGroup=null) {
    const order = prefs[orderName];
    const keys = withinGroup ? [...withinGroup.querySelectorAll('[data-nav-key]')].map(el=>el.dataset.navKey) : order;
    const ix=keys.indexOf(id), dest=keys[ix+relative];
    if(ix<0||!dest)return;
    const from=order.indexOf(id),to=order.indexOf(dest);
    order.splice(from,1);order.splice(to,0,id);
    render();queueSave();
  }
  function moveTo(orderName,id,dest) {
    if(id===dest)return;
    const order=prefs[orderName];
    order.splice(order.indexOf(id),1);
    order.splice(order.indexOf(dest),0,id);
    render();queueSave();
  }
  const el=(tag,cls='',text='') => {const node=document.createElement(tag);node.className=cls;node.textContent=text;return node;};
  const button=(label,action,disabled=false)=>{const b=el('button','',label);b.type='button';b.disabled=disabled;b.addEventListener('click',action);return b;};
  function renderWidgetEditor() {
    const list=document.querySelector('[data-widget-toggles]');if(!list)return;
    list.replaceChildren();
    const rows=widgets();
    for(const item of rows) {
      const id=item.dataset.widget, title=item.querySelector('h2')?.textContent?.trim()||id;
      const row=el('div','mlo-toggle-widget');
      const check=document.createElement('input');check.type='checkbox';check.checked=!prefs.widget_hidden.includes(id);check.setAttribute('aria-label',`Show ${title}`);
      check.addEventListener('change',()=>{prefs.widget_hidden=prefs.widget_hidden.filter(k=>k!==id);if(!check.checked)prefs.widget_hidden.push(id);render();queueSave();});
      const name=el('span','',title);
      const up=button('↑',()=>move('widget_order',id,-1),rows.indexOf(item)===0);up.setAttribute('aria-label',`Move ${title} up`);
      const down=button('↓',()=>move('widget_order',id,1),rows.indexOf(item)===rows.length-1);down.setAttribute('aria-label',`Move ${title} down`);
      const sizes=document.createElement('select');
      sizes.setAttribute('aria-label',`Width for ${title}`);
      for(const [value,label] of [['','Default'],['4','Small'],['6','Medium'],['8','Large'],['12','Full width']]){
        const opt=document.createElement('option');opt.value=value;opt.textContent=label;sizes.append(opt);
      }
      sizes.value=String(prefs.widget_sizes?.[id]||'');
      sizes.addEventListener('change',()=>{if(sizes.value)prefs.widget_sizes[id]=Number(sizes.value);else delete prefs.widget_sizes[id];render();queueSave();});
      row.append(check,name,sizes,up,down);list.append(row);
    }
  }
  function renderNavEditor() {
    const list=document.querySelector('[data-nav-editor-list]');if(!list)return;
    list.replaceChildren();
    for(const group of document.querySelectorAll('[data-nav-group]')) {
      const rows=[...group.querySelectorAll('[data-nav-key]')];
      if(!rows.length)continue;
      list.append(el('div','mlo-nav-edit-group',group.dataset.navGroup==='spaces'?'My spaces':'Navigation'));
      for(const item of rows) {
        const id=item.dataset.navKey, def=item.dataset.navDefault;
        const row=el('div','mlo-nav-edit-item');
        const check=document.createElement('input');check.type='checkbox';check.checked=!prefs.nav_hidden.includes(id);check.setAttribute('aria-label',`Show ${def}`);
        check.onchange=()=>{prefs.nav_hidden=prefs.nav_hidden.filter(k=>k!==id);if(!check.checked)prefs.nav_hidden.push(id);render();queueSave();};
        const input=document.createElement('input');input.type='text';input.maxLength=36;input.value=prefs.nav_labels[id]||def;input.setAttribute('aria-label',`Rename ${def}`);
        input.addEventListener('change',()=>{const text=input.value.trim().slice(0,36);if(text&&text!==def)prefs.nav_labels[id]=text;else delete prefs.nav_labels[id];render();queueSave();});
        const up=button('↑',()=>move('nav_order',id,-1,group),rows.indexOf(item)===0);up.setAttribute('aria-label',`Move ${def} up`);
        const down=button('↓',()=>move('nav_order',id,1,group),rows.indexOf(item)===rows.length-1);down.setAttribute('aria-label',`Move ${def} down`);
        row.append(check,input,up,down);list.append(row);
      }
    }
  }
  function setNavEditing(enabled) {
    navEditing=enabled;
    const panel=document.querySelector('[data-nav-settings]');if(panel)panel.hidden=!enabled;
    document.querySelectorAll('[data-nav-group]').forEach(g=>g.classList.toggle('is-reordering',enabled));
    render();
  }
  function setWidgetEditing(enabled) {
    widgetEditing=enabled;
    const panel=document.querySelector('[data-widget-settings]');if(panel)panel.hidden=!enabled;
    if(grid)grid.classList.toggle('is-reordering',enabled);
    document.querySelector('[data-dashboard-edit]')?.setAttribute('aria-expanded',String(enabled));
    render();
  }
  document.addEventListener('mlo:sidebar-collapsed',()=>{if(navEditing)setNavEditing(false);});
  document.querySelector('[data-nav-edit]')?.addEventListener('click',()=>setNavEditing(!navEditing));
  document.querySelectorAll('[data-nav-edit-close]').forEach(b=>b.addEventListener('click',()=>setNavEditing(false)));
  document.querySelector('[data-nav-reset]')?.addEventListener('click',()=>{prefs.nav_order=[...initialNav];prefs.nav_labels={};prefs.nav_hidden=[];render();queueSave();});
  document.querySelector('[data-dashboard-edit]')?.addEventListener('click',()=>setWidgetEditing(!widgetEditing));
  document.querySelector('[data-dashboard-done]')?.addEventListener('click',()=>setWidgetEditing(false));
  document.querySelector('[data-widget-reset]')?.addEventListener('click',()=>{prefs.widget_order=[...initialWidgets];prefs.widget_hidden=[];prefs.widget_sizes={};render();queueSave();});
  document.addEventListener('click',e=>{
    if(navEditing && e.target.closest('[data-nav-key]'))e.preventDefault();
  });
  document.addEventListener('dragstart',e=>{
    const handle=e.target.closest('.mlo-widget-handle,.mlo-nav-drag');
    if(!handle)return;
    dragElement=handle.closest('[data-widget],[data-nav-key]');
    dragGroup=dragElement?.parentElement||null;
    if(!dragElement||(dragElement.hasAttribute('data-widget')?!widgetEditing:!navEditing)){e.preventDefault();return;}
    e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain','mlo-layout');
    dragElement.classList.add('mlo-dragging');
  });
  document.addEventListener('dragover',e=>{
    const target=e.target.closest('[data-widget],[data-nav-key]');
    if(!dragElement||!target||dragElement===target||target.parentElement!==dragGroup)return;
    e.preventDefault();e.dataTransfer.dropEffect='move';target.classList.add('mlo-dragover');
  });
  document.addEventListener('dragleave',e=>{const target=e.target.closest('[data-widget],[data-nav-key]');if(target&&!target.contains(e.relatedTarget))target.classList.remove('mlo-dragover');});
  document.addEventListener('drop',e=>{
    const target=e.target.closest('[data-widget],[data-nav-key]');
    if(!dragElement||!target||target===dragElement||target.parentElement!==dragGroup)return;
    e.preventDefault();
    moveTo(dragElement.hasAttribute('data-widget')?'widget_order':'nav_order',dragElement.dataset.widget||dragElement.dataset.navKey,target.dataset.widget||target.dataset.navKey);
    document.querySelectorAll('.mlo-dragover').forEach(node=>node.classList.remove('mlo-dragover'));
  });
  document.addEventListener('dragend',()=>{dragElement?.classList.remove('mlo-dragging');dragElement=null;dragGroup=null;document.querySelectorAll('.mlo-dragover').forEach(node=>node.classList.remove('mlo-dragover'));});
  document.addEventListener('keydown',e=>{
    if(!widgetEditing||!e.target.closest('.mlo-widget-handle')||!['ArrowUp','ArrowDown'].includes(e.key))return;
    e.preventDefault();const id=e.target.closest('[data-widget]').dataset.widget;
    move('widget_order',id,e.key==='ArrowUp'?-1:1);
    // DOM nodes are preserved during reordering so focus remains on the dragged handle.
  });
  const quickTimer=document.querySelector('[data-quick-timer]');
  if(quickTimer){
    const form=quickTimer.closest('[data-widget]').querySelector('[data-mini-minutes]');
    const output=quickTimer.querySelector('[data-mini-clock]');
    quickTimer.querySelectorAll('[data-focus-adjust]').forEach(b=>b.addEventListener('click',()=>{
      const minutes=Math.min(180,Math.max(5,Number(form.value)+Number(b.dataset.focusAdjust)));
      form.value=String(minutes);output.textContent=minutes+' min';
    }));
  }
  (async()=>{
    try {
      const response=await fetch('/life/layout',{credentials:'same-origin',cache:'no-store'});
      if(!response.ok)throw new Error('HTTP '+response.status);
      const loaded=await response.json();
      for(const key of Object.keys(prefs))if(Object.hasOwn(loaded,key)&&loaded[key]!==null)prefs[key]=loaded[key];
    } catch(error){console.warn('Layout defaults loaded',error);}
    render();
  })();
})();
