(() => {
  'use strict';
  function refresh(details){details.querySelectorAll('[data-phone-qr]').forEach(img=>{const url=new URL(img.src);url.searchParams.set('refresh',Date.now());img.src=url.href;});}
  document.querySelectorAll('[data-phone-pair]').forEach(details=>details.addEventListener('toggle',()=>{if(details.open)refresh(details);}));
  document.addEventListener('click',async e=>{const copy=e.target.closest('[data-copy-topic]'),refreshButton=e.target.closest('[data-refresh-pair]');if(refreshButton){refresh(refreshButton.closest('[data-phone-pair]'));return;}if(!copy)return;const region=copy.closest('[data-phone-pair],main'),status=region.querySelector('[data-phone-feedback]');
    try{await navigator.clipboard.writeText(copy.dataset.copyTopic);status.textContent='Copied. Paste it into ntfy.';}
    catch{const field=[...region.querySelectorAll('input')].find(input=>input.value===copy.dataset.copyTopic);field?.focus();field?.select();status.textContent='Select Copy from the selection menu, then paste into ntfy.';}
  });
})();
