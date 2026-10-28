(() => {
  'use strict';
  const form = document.querySelector('[data-budget-form]');
  if (!form) return;
  form.noValidate = true;
  const stages = ['income','essentials','flexible','savings','review'];
  const labels = ['Income','Essentials','Flexible spending','Savings','Review'];
  const factors = {'Annually':1,'Quarterly':4,'Semi-annually':2,'Monthly':12,'Biweekly':26,'Weekly':52};
  const feedback = form.querySelector('[data-budget-feedback]');
  const dialog = document.querySelector('[data-budget-dialog]');
  const search = dialog.querySelector('[data-budget-search]');
  const nav = form.querySelector('[data-budget-nav]');
  const next = form.querySelector('[data-budget-next]');
  const back = form.querySelector('[data-budget-back]');
  const save = form.querySelector('[data-budget-save]');
  const quick = document.querySelector('[data-budget-quick]');
  let step = 0, quickMode = false, dirty = false, saving = false, generation = 0, pickerStage = '', pickerOpener;
  const money = value => new Intl.NumberFormat('en-CA',{style:'currency',currency:'CAD'}).format(value);
  function cents(input) {
    let value = input.trim() || '0';
    if (value.startsWith('$')) value = value.slice(1);
    if (!/^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,6})?$/.test(value)) return null;
    value = value.replaceAll(',','');
    const [whole,fraction=''] = value.split('.');
    const result = Number(whole)*100 + Number((fraction+'00').slice(0,2)) + (Number((fraction+'000')[2]) >= 5 ? 1 : 0);
    return Number.isSafeInteger(result) && result <= 99999999999 ? result : null;
  }
  function announce(message,error=false) {
    feedback.hidden = false; feedback.textContent = message;
    feedback.setAttribute('role', error ? 'alert' : 'status');
    feedback.classList.toggle('is-error',error);
  }
  function changed() { dirty=true; generation++; update(); }
  function rows() { return [...form.querySelectorAll('[data-budget-row]')]; }
  function update() {
    const totals={income:0,essentials:0,flexible:0,savings:0};
    const review = form.querySelector('[data-budget-review]'); review.replaceChildren();
    const expenses = new Map(); let invalid = false;
    for (const row of rows()) {
      const amount = row.querySelector('[data-budget-amount]');
      const value=cents(amount.value); amount.setCustomValidity(value===null?'Enter a positive amount or zero, such as 125.50.':'');
      amount.setAttribute('aria-invalid',String(value===null)); invalid ||= value===null;
      const monthly = (value||0)*factors[row.querySelector('[data-budget-frequency]').value]/1200;
      totals[row.dataset.stage]+=monthly;
      row.querySelector('[data-row-monthly]').textContent=value===null?'Check amount':money(monthly)+' / month';
      const name=row.querySelector('[data-category-name]').textContent;
      if (row.dataset.stage==='essentials'||row.dataset.stage==='flexible') expenses.set(name,monthly);
      if (value) {
        const line=document.createElement('div');line.className='budget-review-row';
        const text=document.createElement('span');text.textContent=name;
        const amountText=document.createElement('strong');amountText.textContent=money(monthly)+' / month';
        line.append(text,amountText); review.append(line);
      }
    }
    const out=totals.essentials+totals.flexible+totals.savings;totals.left=totals.income-out;
    for (const target of form.querySelectorAll('[data-budget-total]')) target.textContent=invalid?'Check amounts':money(totals[target.dataset.budgetTotal]);
    for (const target of form.querySelectorAll('[data-allocation]')) target.style.width=(Math.max(totals.income,out)>0?totals[target.dataset.allocation]/Math.max(totals.income,out)*100:0)+'%';
    form.querySelector('[data-budget-health]').textContent=invalid?'Check the highlighted amounts.':totals.left<0?'Your plan allocates '+money(-totals.left)+' more than your income.':dirty?'Unsaved changes.': 'Amounts stay in your draft until you save.';
    const comparison=form.querySelector('[data-budget-comparison]');
    for (const [name] of expenses) if (![...comparison.rows].some(row=>row.dataset.comparisonName===name)) {
      const tr=document.createElement('tr');tr.dataset.comparisonName=name;tr.dataset.actual='0';
      const th=document.createElement('th');th.scope='row';th.textContent=name;
      const planned=document.createElement('td');planned.dataset.comparisonPlan='';
      const actual=document.createElement('td');actual.textContent=money(0);
      const left=document.createElement('td');left.dataset.comparisonLeft='';tr.append(th,planned,actual,left);comparison.append(tr);
    }
    for (const row of comparison.rows) {
      const planned=expenses.get(row.dataset.comparisonName)||0, actual=Number(row.dataset.actual);
      row.hidden=!planned&&!actual;row.querySelector('[data-comparison-plan]').textContent=money(planned);
      row.querySelector('[data-comparison-left]').textContent=money(planned-actual);
    }
    for (const panel of form.querySelectorAll('[data-budget-panel]')) {
      const empty=panel.querySelector('.budget-empty');if(empty) empty.hidden=!!panel.querySelector('[data-budget-row]:not([hidden])');
    }
    if(!review.childElementCount) review.textContent='Your funded categories will appear here.';
  }
  function show(index,focus=true) {
    step=Math.max(0,Math.min(4,index));
    for(const panel of form.querySelectorAll('[data-budget-panel]')) panel.hidden=!quickMode&&panel.dataset.budgetPanel!==stages[step];
    for(const button of nav.querySelectorAll('button')) {
      const current=button.dataset.budgetStep===stages[step]&&!quickMode;
      if(current) button.setAttribute('aria-current','step'); else button.removeAttribute('aria-current');
    }
    nav.hidden=quickMode;back.hidden=quickMode||step===0;next.hidden=quickMode||step===4;save.hidden=!quickMode&&step!==4;
    form.querySelector('[data-budget-position]').textContent=quickMode?'All categories':`Step ${step+1} of 5`;
    quick.textContent=quickMode?'Guided setup':'Quick edit';
    if(focus) form.querySelector(`#heading-${stages[step]}`).focus({preventScroll:false});
  }
  for(const row of rows()) {
    row.hidden=row.dataset.common!=='true';row.querySelector('[data-budget-tools]').hidden=false;
  }
  for(const button of document.querySelectorAll('[data-budget-add]')) button.hidden=false;
  nav.hidden=false;quick.hidden=false;
  nav.addEventListener('click',e=>{const target=e.target.closest('[data-budget-step]');if(target)show(stages.indexOf(target.dataset.budgetStep));});
  next.addEventListener('click',()=>{
    const invalid=form.querySelector(`[data-budget-panel="${stages[step]}"] [aria-invalid="true"]`);
    if(invalid){invalid.focus();invalid.reportValidity();return;}show(step+1);
  });
  back.addEventListener('click',()=>show(step-1));quick.addEventListener('click',()=>{quickMode=!quickMode;show(step);});
  form.addEventListener('input',changed);form.addEventListener('change',changed);
  function pickerOptions() {
    const options=dialog.querySelector('[data-budget-options]');options.replaceChildren();
    const query=search.value.trim().toLocaleLowerCase();
    for(const row of rows().filter(row=>row.hidden&&row.dataset.stage===pickerStage&&row.querySelector('[data-category-name]').textContent.toLocaleLowerCase().includes(query))) {
      const option=document.createElement('button');option.type='button';option.className='budget-category-option';option.textContent=row.querySelector('[data-category-name]').textContent;
      option.addEventListener('click',()=>{row.hidden=false;changed();dialog.close();row.querySelector('[data-budget-amount]').focus();});options.append(option);
    }
  }
  document.addEventListener('click',e=>{
    const add=e.target.closest('[data-budget-add]');if(!add)return;
    pickerStage=add.dataset.budgetAdd;pickerOpener=add;search.value='';pickerOptions();dialog.showModal();search.focus();
  });
  search.addEventListener('input',pickerOptions);
  dialog.querySelector('[data-budget-close]').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>pickerOpener?.focus());
  dialog.querySelector('[data-budget-create]').addEventListener('click',()=>{
    const name=search.value.trim();if(!name){search.setCustomValidity('Enter a category name.');search.reportValidity();return;}search.setCustomValidity('');
    const section=pickerStage==='income'?'custom_income':pickerStage==='savings'?'custom_savings':'expenses';
    const existing=rows().find(row=>row.querySelector('[data-category-name]').textContent.toLocaleLowerCase()===name.toLocaleLowerCase()&&((section==='expenses'&&['essentials','flexible'].includes(row.dataset.stage))||row.dataset.stage===pickerStage));
    if(existing){existing.hidden=false;dialog.close();show(stages.indexOf(existing.dataset.stage));existing.querySelector('[data-budget-amount]').focus();changed();return;}
    const key='custom_'+crypto.randomUUID();
    const row=document.createElement('div');row.className='budget-row';row.dataset.budgetRow='';row.dataset.stage=pickerStage;
    const category=document.createElement('div');category.className='budget-category';const strong=document.createElement('strong');strong.dataset.categoryName='';strong.textContent=name;
    const month=document.createElement('span');month.className='mlo-subtle';month.dataset.rowMonthly='';category.append(strong,month);row.append(category);
    for(const [field,value] of Object.entries({row_key:key,['section__'+key]:section,['name__'+key]:name,['stage__'+key]:pickerStage})){
      const input=document.createElement('input');input.type='hidden';input.name=field;input.value=value;if(field.startsWith('stage__'))input.dataset.rowStage='';row.append(input);
    }
    const label=document.createElement('label');label.textContent='Amount';const input=document.createElement('input');input.name='amount__'+key;input.value='0';input.inputMode='decimal';input.dataset.budgetAmount='';input.setAttribute('aria-label',name+' amount');label.append(input);row.append(label);
    const frequencyLabel=document.createElement('label');frequencyLabel.textContent='Frequency';const select=document.createElement('select');select.name='frequency__'+key;select.dataset.budgetFrequency='';select.setAttribute('aria-label',name+' frequency');
    for(const value of Object.keys(factors)){const option=document.createElement('option');option.textContent=value;option.selected=value==='Monthly';select.append(option);}frequencyLabel.append(select);row.append(frequencyLabel);
    const tools=document.createElement('div');tools.className='budget-row-tools';tools.dataset.budgetTools='';
    for(const action of (section==='expenses'?['move','remove']:['remove'])){const button=document.createElement('button');button.type='button';button.className='mlo-link-btn';button.dataset['budget'+action[0].toUpperCase()+action.slice(1)]='';button.textContent=action==='move'?'Move':'Remove';tools.append(button);}row.append(tools);
    form.querySelector(`[data-budget-rows="${pickerStage}"]`).append(row);dialog.close();changed();input.focus();
  });
  search.addEventListener('input',()=>search.setCustomValidity(''));
  form.addEventListener('click',e=>{
    const remove=e.target.closest('[data-budget-remove]'),move=e.target.closest('[data-budget-move]');
    const row=(remove||move)?.closest('[data-budget-row]');if(!row)return;
    if(remove){row.querySelector('[data-budget-amount]').value='0';row.hidden=true;form.querySelector(`[data-budget-add="${row.dataset.stage}"]`).focus();}
    if(move){const stage=row.dataset.stage==='essentials'?'flexible':'essentials';row.dataset.stage=stage;row.querySelector('[data-row-stage]').value=stage;form.querySelector(`[data-budget-rows="${stage}"]`).append(row);if(!quickMode)show(stages.indexOf(stage));move.focus();}
    changed();
  });
  form.addEventListener('submit',async e=>{
    e.preventDefault();if(saving)return;
    const invalid=form.querySelector('[aria-invalid="true"]');if(invalid){const row=invalid.closest('[data-budget-row]');row.hidden=false;show(stages.indexOf(row.dataset.stage));invalid.focus();invalid.reportValidity();return;}
    saving=true;const submitted=generation;save.disabled=true;save.textContent='Saving…';
    try{
      const response=await fetch(form.action,{method:'POST',body:new FormData(form),headers:{Accept:'application/json'}});
      if(response.status===401)throw new Error('Your session expired. Sign in in another tab, then retry. Your edits are still here.');
      const type=response.headers.get('content-type')||'';
      if(response.redirected||!type.includes('application/json'))throw new Error('Your session may have expired. Sign in in another tab, then retry. Your edits are still here.');
      const payload=await response.json();if(!response.ok)throw new Error(payload.detail||'Unable to save. Please retry.');
      form.elements.revision.value=payload.revision;dirty=generation!==submitted;announce(dirty?'Saved. You have newer unsaved edits.':'Budget saved.');update();
    }catch(error){announce(error.message,true);}finally{saving=false;save.disabled=false;save.textContent='Save budget';}
  });
  window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
  update();show(0,false);
})();
