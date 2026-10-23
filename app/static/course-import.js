(() => {
  'use strict';
  const upload = document.querySelector('[data-outline-upload]');
  upload?.addEventListener('submit', () => {
    upload.querySelector('[data-upload-submit]').disabled = true;
    upload.querySelector('[data-upload-status]').textContent = 'Reading your outline… This can take a minute for scanned pages.';
    upload.setAttribute('aria-busy', 'true');
  });
  const root = document.querySelector('[data-outline-review]');
  const source = document.getElementById('outline-data');
  if (!root || !source) return;
  const preview = JSON.parse(source.textContent), form = document.getElementById('outline-review-form');
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rows = preview.rows.map((r, i) => ({...r, source_index:i}));
  const container = root.querySelector('[data-assessment-rows]');
  function paint() {
    container.innerHTML = rows.map((r, i) => `<article class="assessment-row" data-row="${i}">
      <div class="assessment-title"><label><input type="checkbox" data-field="selected" ${r.selected?'checked':''} aria-label="Include assessment ${i+1}"><span>${i+1}</span></label><label class="assessment-name"><span class="sr-only">Assessment title</span><input data-field="title" value="${esc(r.title)}" maxlength="240" aria-label="Assessment ${i+1} title"></label></div>
      <div class="assessment-fields"><label>Type<select data-field="kind">${['assignment','exam','lab'].map(k=>`<option ${r.kind===k?'selected':''} value="${k}">${k[0].toUpperCase()+k.slice(1)}</option>`).join('')}</select></label><label>Due date<input type="date" data-field="due_on" value="${esc(r.due_on)}"></label><label>Time<input type="time" data-field="time" value="${esc(r.time)}"></label><label>Weight %<input type="number" data-field="weight" min="0" max="100" step="0.01" value="${esc(r.weight)}"></label></div>
      ${r.warning?`<p class="assessment-warning">${esc(r.warning)}</p>`:''}
      ${r.evidence?`<button type="button" class="evidence-link" data-evidence="${i}">View source ${esc(r.source_page)} ↗</button><blockquote>${esc(r.evidence)}</blockquote>`:''}</article>`).join('');
    summary();
  }
  function summary() {
    const selected = rows.filter(r=>r.selected), total = selected.reduce((n,r)=>n+Number(r.weight||0),0);
    root.querySelector('[data-weight-summary]').textContent = `${selected.length} selected · ${Number(total.toFixed(2))}% total weight${total>100?' · Check for grouped or duplicate grading rows.':''}`;
  }
  container.addEventListener('input', e => {
    const card=e.target.closest('[data-row]'), field=e.target.dataset.field;
    if (!card||!field) return;
    rows[Number(card.dataset.row)][field] = field==='selected'?e.target.checked:field==='weight'?(e.target.value===''?null:Number(e.target.value)):e.target.value||null;
    summary();
  });
  function page(number) {
    root.querySelectorAll('[data-page]').forEach(p=>p.hidden=Number(p.dataset.page)!==Number(number));
    root.querySelector('[data-source-page]').value=String(number);
  }
  root.querySelector('[data-source-page]').addEventListener('change',e=>page(e.target.value));
  container.addEventListener('click',e=>{
    const button=e.target.closest('[data-evidence]');
    if (!button) return;
    page(rows[Number(button.dataset.evidence)].source_page);
    root.querySelector('.source-evidence').scrollIntoView({block:'nearest',behavior:'instant'});
  });
  root.querySelector('[data-add-assessment]').addEventListener('click',()=>{
    rows.push({title:'',kind:'assignment',due_on:null,time:null,weight:null,selected:true,source_index:null});paint();
    container.lastElementChild.querySelector('[data-field="title"]').focus();
  });
  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const button=form.querySelector('button[type="submit"]'),status=root.querySelector('[data-import-status]');
    if(button.disabled)return;
    const selected=rows.filter(r=>r.selected);
    if(selected.some(r=>!r.title?.trim())){status.textContent='Enter a title for each selected assessment.';return;}
    button.disabled=true;status.textContent='Adding assessments…';
    try{
      const fd=new FormData(form), body={course_name:fd.get('course_name'),course_code:fd.get('course_code'),term:fd.get('term'),rows:selected.map(r=>({title:r.title,kind:r.kind,due_on:r.due_on||null,time:r.time||null,weight:r.weight,source_index:r.source_index}))};
      const response=await fetch(`/life/study/import/${root.dataset.importId}/commit`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const result=await response.json();
      if(!response.ok)throw Error(typeof result.detail==='string'?result.detail:'Check the selected assessment fields.');
      location.href=`/life/study/courses/${result.course_id}`;
    }catch(error){status.textContent=error.message;button.disabled=false;}
  });
  paint();
})();
