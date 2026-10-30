(() => {
  'use strict';
  function safeLink(value) {
    try { const url = new URL(value, location.origin); return ['https:','http:','mailto:'].includes(url.protocol) ? url.href : null; } catch { return null; }
  }
  function inline(parent,text) {
    const pattern=/(\*\*([^*]+)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^\s)]+)\))/g;
    let start=0, match;
    while((match=pattern.exec(text))) {
      parent.append(document.createTextNode(text.slice(start,match.index)));
      if(match[2]||match[3]) {const node=document.createElement(match[2]?'strong':'code');node.textContent=match[2]||match[3];parent.append(node);}
      else {const url=safeLink(match[5]);if(url){const link=document.createElement('a');link.href=url;link.rel='noopener noreferrer';link.textContent=match[4];parent.append(link);}else parent.append(document.createTextNode(match[0]));}
      start=pattern.lastIndex;
    }
    parent.append(document.createTextNode(text.slice(start)));
  }
  function preview(target,text) {
    const fragment=document.createDocumentFragment();let code=null,list=null;
    for(const line of text.split('\n')) {
      if(line.startsWith('```')){list=null;if(code){code=null;}else{const pre=document.createElement('pre');code=document.createElement('code');pre.append(code);fragment.append(pre);}continue;}
      if(code){code.append(document.createTextNode(line+'\n'));continue;}
      const heading=/^(#{1,6})\s+(.*)$/.exec(line),bullet=/^\s*[-*]\s+(.*)$/.exec(line);
      if(bullet){if(!list){list=document.createElement('ul');fragment.append(list);}const li=document.createElement('li');const check=/^\[([ xX])\]\s*(.*)$/.exec(bullet[1]);if(check){li.className='note-check';li.textContent=(check[1].trim()?'☑ ':'☐ ');inline(li,check[2]);}else inline(li,bullet[1]);list.append(li);continue;}
      list=null;if(!line.trim()){const space=document.createElement('div');space.className='note-paragraph-gap';fragment.append(space);continue;}
      const node=document.createElement(heading?'h'+Math.min(6,heading[1].length+1):'p');inline(node,heading?heading[2]:line);fragment.append(node);
    }
    target.replaceChildren(fragment);
  }
  for(const reader of document.querySelectorAll('[data-note-reader]')) preview(reader,reader.querySelector('[data-note-source]').textContent);
  const form=document.querySelector('[data-note-editor]');if(!form)return;
  const body=form.elements.body,status=form.querySelector('[data-note-status]'),canvas=form.querySelector('[data-note-canvas]'),output=form.querySelector('[data-note-preview]'),save=form.querySelector('[type=submit]');
  let dirty=false,saving=false,generation=0,mode='write';
  form.querySelector('[data-note-toolbar]').hidden=false;
  function changed(){dirty=true;generation++;status.textContent='Unsaved changes';if(mode!=='write')preview(output,body.value);}
  form.addEventListener('input',changed);
  form.addEventListener('click',e=>{
    const view=e.target.closest('[data-note-view]');
    if(view){mode=view.dataset.noteView;canvas.dataset.view=mode;form.querySelector('.note-write').hidden=mode==='preview';output.hidden=mode==='write';for(const button of form.querySelectorAll('[data-note-view]'))button.setAttribute('aria-pressed',String(button===view));if(mode!=='write')preview(output,body.value);}
    const format=e.target.closest('[data-note-format]');if(!format)return;
    const start=body.selectionStart,end=body.selectionEnd,selected=body.value.slice(start,end)||'text';
    const wrappers={bold:['**','**'],heading:['## ',''],list:['- ',''],check:['- [ ] ',''],link:['[','](https://example.com)'],code:['`','`']};const [left,right]=wrappers[format.dataset.noteFormat];
    body.setRangeText(left+selected+right,start,end,'select');body.focus();changed();
  });
  form.addEventListener('submit',async e=>{
    e.preventDefault();if(saving)return;if(!form.reportValidity())return;saving=true;save.disabled=true;const submitted=generation;status.textContent='Saving…';
    try{
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});
      if(response.status===401)throw new Error('Your session expired. Sign in in another tab, then retry. Your edits are still here.');
      if(response.redirected||!(response.headers.get('content-type')||'').includes('application/json'))throw new Error('Sign in in another tab, then retry. Your draft is still here.');
      const result=await response.json();if(!response.ok)throw new Error(result.detail||'Unable to save. Please retry.');
      form.elements.base_version.value=result.version;dirty=generation!==submitted;status.textContent=dirty?'Saved. Newer changes are unsaved.':'Saved';if(!dirty)window.MLOSave?.finish(form);
    }catch(error){status.textContent=error.message;}finally{saving=false;save.disabled=false;}
  });
  form.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();form.requestSubmit();}});
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
})();
