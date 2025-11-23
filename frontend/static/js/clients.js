// Demo client management UI (mock, stores in localStorage)
document.addEventListener('DOMContentLoaded', () => {
  const table = document.getElementById('clientsTable');
  // modal fields (clients are added/edited via modal on dashboard or clients page)
  const provider = document.getElementById('modalProvider');
  const clientName = document.getElementById('modalClientName');
  const clientId = document.getElementById('modalClientId');
  const clientSecret = document.getElementById('modalClientSecret');

  // If URL contains action=add, open the Add Client modal on load
  try{
    const params = new URLSearchParams(window.location.search);
    if(params.get('action') === 'add'){
      const modalEl = document.getElementById('clientModal');
      if(modalEl) new bootstrap.Modal(modalEl).show();
      // remove action param from URL without reloading
      const u = new URL(window.location.href);
      u.searchParams.delete('action');
      history.replaceState(null, '', u.pathname + u.search + u.hash);
    }
  }catch(e){/* ignore */}

  function loadClients(){
    const raw = localStorage.getItem('clients') || '[]';
    const arr = JSON.parse(raw);
    // If no clients stored yet, seed with example/demo data so table isn't empty
    if(!Array.isArray(arr) || arr.length === 0){
      // generate a larger set of demo clients so the page can be scrolled
      const sample = [];
      const providers = ['aws','gcp','azure'];
      for(let i=1;i<=60;i++){
        const p = providers[i % providers.length];
        sample.push({
          provider: p,
          name: `Demo ${p.toUpperCase()} Account ${i}`,
          clientId: `${p}-client-${String(i).padStart(3,'0')}`,
          clientSecret: `${p}-secret-${String(i).padStart(3,'0')}`
        });
      }
      saveClients(sample);
      return sample;
    }
    return arr;
  }

  function saveClients(list){
    localStorage.setItem('clients', JSON.stringify(list));
  }

  function mask(v){
    if(!v) return '';
    return v.length > 6 ? v.slice(0,3) + '•••' + v.slice(-3) : '••••';
  }

  function render(){
    const list = loadClients();
    table.innerHTML = '';
    list.forEach((c, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${c.name}</td>
        <td>${c.provider.toUpperCase()}</td>
        <td>${mask(c.clientId)}</td>
        <td>${mask(c.clientSecret)}</td>
        <td>
          <button class="btn btn-sm btn-outline-light me-1" data-act="edit" data-idx="${idx}" title="Edit" aria-label="Edit">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M12.146.854a.5.5 0 0 1 .708 0l2.292 2.292a.5.5 0 0 1 0 .708L6.953 12.847a.5.5 0 0 1-.168.11l-4 1.5a.5.5 0 0 1-.65-.65l1.5-4a.5.5 0 0 1 .11-.168L12.146.854zM11.207 2L3 10.207V13h2.793L14 4.793 11.207 2z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-act="metrics" data-idx="${idx}" title="View Metrics" aria-label="View Metrics">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8z"/>
              <path d="M8 5.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-act="chat" data-idx="${idx}" title="Open Chat" aria-label="Open Chat">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M8 1a7 7 0 1 0 4.546 12.032L15 15l-1.232-2.232A7 7 0 0 0 8 1zM5 6.5a.5.5 0 0 1 .5-.5H7v1H5.5a.5.5 0 0 1-.5-.5zm2 0a.5.5 0 0 1 .5-.5H9v1H7.5a.5.5 0 0 1-.5-.5z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-danger" data-act="delete" data-idx="${idx}" title="Delete" aria-label="Delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path d="M5.5 5.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5zM8 5.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6A.5.5 0 0 1 8 5.5zm2.5-.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5z"/>
              <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 1 1 0-2h3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3a1 1 0 0 1 1 1zM4.118 4L4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 2a.5.5 0 0 0 0 1H13.5a.5.5 0 0 0 0-1H2.5z"/>
            </svg>
          </button>
        </td>
      `;
      table.appendChild(tr);
    });
  }

  // Respond to external updates (e.g. modal on dashboard saved a client)
  window.addEventListener('clients-updated', render);

  function reset(){
    if(document.getElementById('modalClientForm')) document.getElementById('modalClientForm').reset();
  }

  table.addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if(!btn) return;
    const act = btn.dataset.act;
    const idx = Number(btn.dataset.idx);
    const list = loadClients();
    if(act === 'edit'){
      const c = list[idx];
      // populate modal fields and remove the item so save will re-add
      if(provider) provider.value = c.provider;
      if(clientName) clientName.value = c.name;
      if(clientId) clientId.value = c.clientId;
      if(clientSecret) clientSecret.value = c.clientSecret;
      list.splice(idx,1);
      saveClients(list);
      render();
      // show modal
      const modalEl = document.getElementById('clientModal');
      if(modalEl) new bootstrap.Modal(modalEl).show();
    } else if(act === 'metrics'){
      // navigate to metrics page with client index
      window.location.href = `./metrics.html?idx=${idx}`;
    } else if(act === 'chat'){
      // navigate to chat page for this client
      window.location.href = `./chat.html?idx=${idx}`;
    } else if(act === 'delete'){
      if(confirm('Delete this client?')){
        list.splice(idx,1);
        saveClients(list);
        render();
      }
    }
  });

  render();
});
