// Client management UI - integrated with backend API
const API_BASE = 'http://localhost:8000/api';
function getAuthHeaders(){
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

async function loadCurrentUser(){
  const token = localStorage.getItem('token');
  if(!token) return null;
  try{
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if(res.ok) return await res.json();
  }catch(e){ console.error(e); }
  return null;
}

document.addEventListener('DOMContentLoaded', async () => {
  // Populate navbar dropdown and hide admin-only items
  const user = await loadCurrentUser();
  if(user){
    document.getElementById('navUsername').textContent = user.username || 'User';
    document.getElementById('dropdownUsername').textContent = user.username || 'User';
    document.getElementById('dropdownRole').textContent = `Role: ${user.role || 'member'}`;
    
    if(user.role !== 'admin'){
      document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }
  }

  const table = document.getElementById('clientsTable');
  // modal fields (clients are added/edited via modal on dashboard or clients page)
  const provider = document.getElementById('modalProvider');
  const clientName = document.getElementById('modalClientName');
  const tenantId = document.getElementById('modalTenantId');
  const tenantIdField = document.getElementById('tenantIdField');
  const clientId = document.getElementById('modalClientId');
  const clientSecret = document.getElementById('modalClientSecret');

  let clients = [];
  
  // Use global variable for editing state so modal can access it
  window.editingClientId = null;

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

  async function loadClients(){
    try {
      console.log('Loading clients from:', `${API_BASE}/clients/`);
      console.log('Auth headers:', getAuthHeaders());
      
      const response = await fetch(`${API_BASE}/clients/`, { headers: getAuthHeaders() });
      console.log('Response status:', response.status);
      
      if (response.status === 401) {
        location.href = './login.html';
        return [];
      }
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error('Failed to load clients: ' + response.status);
      }
      clients = await response.json();
      console.log('Loaded clients from API:', clients);
      return clients;
    } catch (error) {
      console.error('Error loading clients:', error);
      console.error('Error stack:', error.stack);
      alert('Failed to load clients: ' + error.message);
      return [];
    }
  }

  async function seedDemoClients() {
    const providers = ['aws','gcp','azure'];
    for(let i=1; i<=10; i++){
      const p = providers[i % providers.length];
      await fetch(`${API_BASE}/clients/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: `Demo ${p.toUpperCase()} Account ${i}`,
          metadata_json: {
            provider: p,
            clientId: `${p}-client-${String(i).padStart(3,'0')}`,
            clientSecret: `${p}-secret-${String(i).padStart(3,'0')}`
          }
        })
      });
    }
  }

  async function deleteClient(id) {
    try {
      const response = await fetch(`${API_BASE}/clients/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (response.status === 401) { location.href = './login.html'; return false; }
      if (!response.ok) throw new Error('Failed to delete client');
      return true;
    } catch (error) {
      console.error('Error deleting client:', error);
      alert('Failed to delete client');
      return false;
    }
  }

  function mask(v){
    if(!v) return '';
    return v.length > 6 ? v.slice(0,3) + '•••' + v.slice(-3) : '••••';
  }

  async function render(){
    await loadClients();
    table.innerHTML = '';
    
    if(clients.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="text-center text-muted">No clients found. Click "Add Client" to create one.</td>';
      table.appendChild(tr);
      return;
    }
    
    clients.forEach((c, idx) => {
      const meta = c.metadata_json || {};
      const provider = meta.provider || 'aws';
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${c.name}</strong></td>
        <td><span class="badge bg-secondary">${provider.toUpperCase()}</span></td>
        <td><code class="text-warning">${mask(meta.clientId || '')}</code></td>
        <td><code class="text-warning">${mask(meta.clientSecret || '')}</code></td>
        <td>
          <button class="btn btn-sm btn-outline-light me-1 admin-only" data-act="edit" data-id="${c.id}" title="Edit" aria-label="Edit">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
              <path d="M12.146.854a.5.5 0 0 1 .708 0l2.292 2.292a.5.5 0 0 1 0 .708L6.953 12.847a.5.5 0 0 1-.168.11l-4 1.5a.5.5 0 0 1-.65-.65l1.5-4a.5.5 0 0 1 .11-.168L12.146.854zM11.207 2L3 10.207V13h2.793L14 4.793 11.207 2z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-outline-info me-1" data-act="view" data-id="${c.id}" title="View Details" aria-label="View Details">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
              <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM8 5.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-act="metrics" data-id="${c.id}" title="View Metrics" aria-label="View Metrics">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
              <path d="M2.5 0a.5.5 0 0 0-.5.5v15a.5.5 0 0 0 .5.5h11a.5.5 0 0 0 .5-.5v-15a.5.5 0 0 0-.5-.5h-11zm3 2h6a.5.5 0 0 1 0 1h-6a.5.5 0 0 1 0-1zm0 2h6a.5.5 0 0 1 0 1h-6a.5.5 0 0 1 0-1zm0 2h4a.5.5 0 0 1 0 1h-4a.5.5 0 0 1 0-1z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-act="chat" data-id="${c.id}" title="Open Chat" aria-label="Open Chat">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
              <path d="M2.678 11.894a1 1 0 0 1 .287.801 10.97 10.97 0 0 1-.398 2c1.395-.323 2.247-.697 2.634-.893a1 1 0 0 1 .71-.074A8.06 8.06 0 0 0 8 14c3.996 0 7-2.807 7-6 0-3.192-3.004-6-7-6S1 4.808 1 8c0 1.468.617 2.83 1.678 3.894z"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-danger admin-only" data-act="delete" data-id="${c.id}" title="Delete" aria-label="Delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
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
    window.editingClientId = null;
    const modalTitle = document.getElementById('clientModalLabel');
    if(modalTitle) modalTitle.textContent = 'Add Client';
  }

  table.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if(!btn) return;
    const act = btn.dataset.act;
    const id = Number(btn.dataset.id);
    
    if(act === 'edit'){
      const client = clients.find(c => c.id === id);
      if (!client) return;
      
      const meta = client.metadata_json || {};
      if(provider) provider.value = meta.provider || 'aws';
      if(clientName) clientName.value = client.name;
      if(clientId) clientId.value = meta.clientId || '';
      if(clientSecret) clientSecret.value = meta.clientSecret || '';
      
      // Handle Azure tenant ID
      if(meta.provider === 'azure' && tenantId && tenantIdField) {
        tenantId.value = meta.tenantId || '';
        tenantIdField.style.display = 'block';
      } else if(tenantIdField) {
        tenantIdField.style.display = 'none';
      }
      
      window.editingClientId = id;
      
      const modalEl = document.getElementById('clientModal');
      const modalTitle = document.getElementById('clientModalLabel');
      if(modalTitle) modalTitle.textContent = 'Edit Client';
      if(modalEl) new bootstrap.Modal(modalEl).show();
      
    } else if(act === 'view'){
      const client = clients.find(c => c.id === id);
      if (!client) return;
      const meta = client.metadata_json || {};
      const providerName = (meta.provider || 'aws').toUpperCase();
      let details = `Client Details:\n\nName: ${client.name}\nProvider: ${providerName}\n`;
      
      if (meta.provider === 'azure' && meta.tenantId) {
        details += `Tenant ID: ${meta.tenantId}\n`;
      }
      
      details += `Client ID: ${meta.clientId || 'N/A'}\nCreated: ${client.created_at || 'N/A'}`;
      alert(details);
      
    } else if(act === 'metrics'){
      window.location.href = `./metrics.html?id=${id}`;
      
    } else if(act === 'chat'){
      window.location.href = `./chat.html?id=${id}`;
      
    } else if(act === 'delete'){
      const client = clients.find(c => c.id === id);
      if(!client) return;
      if(confirm(`Delete client "${client.name}"?\n\nThis action cannot be undone.`)){
        if(await deleteClient(id)) {
          await render();
        }
      }
    }
  });

  // Form submission is handled by clients-modal.js
  // Listen for modal close to reset state
  const modalEl = document.getElementById('clientModal');
  if (modalEl) {
    modalEl.addEventListener('hidden.bs.modal', reset);
  }

  render();
});
