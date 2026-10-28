(() => {
  'use strict';
  let pendingDrafts=new Set();
  const saving=new WeakSet();
  document.addEventListener('input',event=>{
    const form=event.target.closest('form');
    if(form?.matches('[data-protect-draft], [data-enhanced-form]')&&!form.matches('[data-note-editor],[data-budget-form]'))pendingDrafts.add(form);
  });
  function feedback(form,message,error=false){
    let node=form.querySelector('[data-form-feedback]');if(!node){node=document.createElement('p');node.dataset.formFeedback='';node.className='product-feedback record-wide';form.prepend(node);}
    node.setAttribute('role',error?'alert':'status');node.classList.toggle('is-error',error);node.textContent=message;node.tabIndex=-1;if(error)node.focus();
  }
  document.addEventListener('submit',async event=>{
    const form=event.target;
    if(!form.closest('[data-app-layout]')||event.defaultPrevented||form.method.toLowerCase()!=='post'||form.enctype==='multipart/form-data'||form.matches('[data-note-editor],[data-budget-form]')||['/login','/signup'].includes(new URL(form.action).pathname)||form.closest('[data-onboarding]'))return;
    // Component handlers receive submit first and can opt out by preventing it.
    event.preventDefault();if(saving.has(form))return;
    saving.add(form);const buttons=[...form.querySelectorAll('button[type=submit],button:not([type])')];
    const body=new FormData(form);if(event.submitter?.name)body.append(event.submitter.name,event.submitter.value);
    for(const button of buttons)button.disabled=true;
    feedback(form,'Saving…');
    try{
      const response=await fetch(form.action,{method:'POST',body,headers:{Accept:'application/json'}});
      if(response.status===401)throw new Error('Your session expired. Sign in in another tab, then retry. Your edits are still here.');
      const url=new URL(response.url);
      if(response.redirected&&url.pathname==='/login')throw new Error('Your session expired. Sign in in another tab, then retry. Your edits are still here.');
      const json=(response.headers.get('content-type')||'').includes('application/json');
      const payload=json?await response.json():null;
      if(!response.ok){
        let message=typeof payload?.detail==='string'?payload.detail:'';
        if(!json){const doc=new DOMParser().parseFromString(await response.text(),'text/html');message=doc.querySelector('.error-state p,[role=alert]')?.textContent||'';}
        throw new Error(message||'Unable to save. Check the form and try again.');
      }
      pendingDrafts.delete(form);
      if(response.redirected){window.location.assign(response.url);return;}
      if(json){feedback(form,'Saved.');if(payload?.version&&form.elements.base_version)form.elements.base_version.value=payload.version;return;}
      window.location.reload();
    }catch(error){feedback(form,error.message,true);}finally{saving.delete(form);for(const button of buttons)button.disabled=false;}
  });
  window.addEventListener('beforeunload',event=>{if(pendingDrafts.size){event.preventDefault();event.returnValue='';}});
  for(const link of document.querySelectorAll('.sidebar-nav a.active,.sidebar-foot a.active'))link.setAttribute('aria-current','page');
  for(const region of document.querySelectorAll('.overflow-x-auto,.table-region')){if(region.scrollWidth>region.clientWidth){region.tabIndex=0;region.setAttribute('role','region');if(!region.hasAttribute('aria-label'))region.setAttribute('aria-label','Scrollable table');}}
})();
