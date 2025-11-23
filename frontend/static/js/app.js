// Small demo JS to wire chat button and show a mock response
document.addEventListener('DOMContentLoaded', () => {
  const askBtn = document.getElementById('askBtn');
  const q = document.getElementById('q');
  const resp = document.getElementById('resp');

  askBtn.addEventListener('click', async () => {
    const question = q.value.trim();
    if(!question){
      resp.textContent = 'Please type a question first.';
      return;
    }

    resp.textContent = 'Thinking...';
    resp.classList.remove('alert-danger');
    resp.classList.add('alert-secondary');

    // Demo: call backend API if available, otherwise mock
    try{
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question })
      });
      if(r.ok){
        const j = await r.json();
        resp.classList.remove('alert-secondary');
        resp.classList.add('alert-success');
        resp.textContent = j.answer || JSON.stringify(j, null, 2);
      } else {
        resp.classList.remove('alert-secondary');
        resp.classList.add('alert-danger');
        resp.textContent = 'Server responded: ' + r.status;
      }
    }catch(e){
      // fallback mock
      resp.classList.remove('alert-secondary');
      resp.classList.add('alert-info');
      resp.textContent = 'Mock response: We received your question — "' + question + '".';
    }
  });
});