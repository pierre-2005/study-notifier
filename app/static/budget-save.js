// Preserve edited budget values if the backend has a transient failure.
(() => {
  const form = document.querySelector('[data-budget-save-form]');
  if (!form || !window.fetch) return;
  const feedback = form.querySelector('[data-budget-feedback]');
  let saving = false;
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (saving) return;
    saving = true;
    const submit = form.querySelector('button[type="submit"]');
    if (submit) { submit.disabled = true; submit.textContent = 'Saving…'; }
    if (feedback) { feedback.hidden = false; feedback.textContent = 'Saving budget…'; }
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Accept':'application/json'},
        body: new FormData(form),
      });
      if (response.redirected && new URL(response.url).pathname.startsWith('/login')) {
        location.assign(response.url); return;
      }
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.detail || 'Unable to save budget.');
      if (feedback) feedback.textContent = 'Budget saved. Updating totals…';
      location.assign('/finance/budget?saved=1');
    } catch (error) {
      if (feedback) { feedback.hidden = false; feedback.textContent = error.message || 'Unable to save. Your entries are still here.'; }
      saving = false;
      if (submit) { submit.disabled = false; submit.textContent = 'Save budget'; }
    }
  });
})();
