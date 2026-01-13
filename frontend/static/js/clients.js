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

  const grid = document.getElementById('clientsGrid');
  // modal fields (clients are added/edited via modal on dashboard or clients page)
  const provider = document.getElementById('modalProvider');
  const clientName = document.getElementById('modalClientName');
  const tenantId = document.getElementById('modalTenantId');
  const tenantIdField = document.getElementById('tenantIdField');
  const subscriptionId = document.getElementById('modalSubscriptionId');
  const subscriptionIdField = document.getElementById('subscriptionIdField');
  const resourceGroup = document.getElementById('modalResourceGroup');
  const resourceGroupField = document.getElementById('resourceGroupField');
  const clientId = document.getElementById('modalClientId');
  const clientSecret = document.getElementById('modalClientSecret');

  let clients = [];
  let filteredClients = [];
  let currentPage = 1;
  let itemsPerPageValue = 12;
  
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
      // Log Azure clients specifically to verify metadata
      clients.filter(c => c.metadata_json?.provider === 'azure').forEach(c => {
        console.log(`Azure client ${c.name} (ID: ${c.id}) metadata:`, c.metadata_json);
      });
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

  function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const providerFilter = document.getElementById('providerFilter').value;
    
    filteredClients = clients.filter(c => {
      const meta = c.metadata_json || {};
      const provider = meta.provider || 'aws';
      const name = (c.name || '').toLowerCase();
      
      // Apply search filter
      const matchesSearch = name.includes(searchTerm);
      
      // Apply provider filter
      const matchesProvider = providerFilter === 'all' || provider === providerFilter;
      
      return matchesSearch && matchesProvider;
    });
    
    currentPage = 1; // Reset to first page when filters change
    renderClients();
  }

  function renderPagination() {
    const totalItems = filteredClients.length;
    const totalPages = itemsPerPageValue === 'all' ? 1 : Math.ceil(totalItems / itemsPerPageValue);
    
    const paginationTop = document.getElementById('paginationTop');
    const paginationBottom = document.getElementById('paginationBottom');
    const controlsTop = document.getElementById('paginationControlsTop');
    const controlsBottom = document.getElementById('paginationControlsBottom');
    
    // Show/hide pagination
    if (totalPages <= 1 || itemsPerPageValue === 'all') {
      paginationTop.style.display = 'none';
      paginationBottom.style.display = 'none';
      return;
    }
    
    paginationTop.style.display = 'block';
    paginationBottom.style.display = 'flex';
    
    // Build pagination HTML
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
      <a class="page-link" href="#" data-page="${currentPage - 1}" style="background: #0d1117; border-color: #30363d; color: #e6edf3;">Previous</a>
    </li>`;
    
    // Page numbers
    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    if (startPage > 1) {
      paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="1" style="background: #0d1117; border-color: #30363d; color: #e6edf3;">1</a></li>`;
      if (startPage > 2) {
        paginationHTML += `<li class="page-item disabled"><span class="page-link" style="background: #0d1117; border-color: #30363d; color: #7d8590;">...</span></li>`;
      }
    }
    
    for (let i = startPage; i <= endPage; i++) {
      paginationHTML += `<li class="page-item ${i === currentPage ? 'active' : ''}">
        <a class="page-link" href="#" data-page="${i}" style="background: ${i === currentPage ? '#1f6feb' : '#0d1117'}; border-color: #30363d; color: #e6edf3;">${i}</a>
      </li>`;
    }
    
    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        paginationHTML += `<li class="page-item disabled"><span class="page-link" style="background: #0d1117; border-color: #30363d; color: #7d8590;">...</span></li>`;
      }
      paginationHTML += `<li class="page-item"><a class="page-link" href="#" data-page="${totalPages}" style="background: #0d1117; border-color: #30363d; color: #e6edf3;">${totalPages}</a></li>`;
    }
    
    // Next button
    paginationHTML += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
      <a class="page-link" href="#" data-page="${currentPage + 1}" style="background: #0d1117; border-color: #30363d; color: #e6edf3;">Next</a>
    </li>`;
    
    controlsTop.innerHTML = paginationHTML;
    controlsBottom.innerHTML = paginationHTML;
  }

  function renderClients() {
    // Update stats (based on filtered results)
    const awsClients = filteredClients.filter(c => (c.metadata_json?.provider || 'aws') === 'aws');
    const azureClients = filteredClients.filter(c => c.metadata_json?.provider === 'azure');
    const gcpClients = filteredClients.filter(c => c.metadata_json?.provider === 'gcp');
    
    document.getElementById('totalClients').textContent = clients.length;
    document.getElementById('awsCount').textContent = awsClients.length;
    document.getElementById('azureCount').textContent = azureClients.length;
    document.getElementById('gcpCount').textContent = gcpClients.length;
    
    // Update results info
    const totalItems = filteredClients.length;
    document.getElementById('totalCount').textContent = clients.length;
    document.getElementById('showingCount').textContent = totalItems;
    
    grid.innerHTML = '';
    
    if(clients.length === 0){
      const col = document.createElement('div');
      col.className = 'col-12';
      col.innerHTML = `
        <div class="empty-state">
          <i class="bi bi-cloud-slash"></i>
          <h4 class="text-white mb-3">No Clients Found</h4>
          <p class="text-muted mb-4">Get started by adding your first cloud provider integration</p>
          <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#clientModal">
            <i class="bi bi-plus-circle-fill me-2"></i>Add Your First Client
          </button>
        </div>`;
      grid.appendChild(col);
      return;
    }
    
    if(filteredClients.length === 0){
      const col = document.createElement('div');
      col.className = 'col-12';
      col.innerHTML = `
        <div class="empty-state">
          <i class="bi bi-search"></i>
          <h4 class="text-white mb-3">No Clients Found</h4>
          <p class="text-muted mb-4">No clients match your search criteria. Try adjusting your filters.</p>
          <button id="clearFiltersBtn" class="btn btn-outline-secondary">
            <i class="bi bi-x-circle me-1"></i>Clear Filters
          </button>
        </div>`;
      grid.appendChild(col);
      renderPagination();
      return;
    }
    
    // Calculate pagination
    const startIndex = itemsPerPageValue === 'all' ? 0 : (currentPage - 1) * itemsPerPageValue;
    const endIndex = itemsPerPageValue === 'all' ? filteredClients.length : startIndex + itemsPerPageValue;
    const paginatedClients = filteredClients.slice(startIndex, endIndex);
    
    paginatedClients.forEach((c, idx) => {
      const meta = c.metadata_json || {};
      const providerName = meta.provider || 'aws';
      
      const col = document.createElement('div');
      col.className = 'col-md-6 col-lg-4';
      col.innerHTML = `
        <div class="client-card">
          <span class="provider-badge ${providerName}">${providerName.toUpperCase()}</span>
          
          <div class="client-card-header">
            <div class="client-card-icon icon-${providerName}"><i class="bi bi-cloud-fill"></i></div>
            <h5 class="client-card-title">${c.name}</h5>
          </div>
          
          <div class="client-card-meta">
            <div class="meta-item">
              <div class="meta-label">Client ID</div>
              <div class="meta-value">${mask(meta.clientId || '')}</div>
            </div>
            <div class="meta-item">
              <div class="meta-label">Secret</div>
              <div class="meta-value">${mask(meta.clientSecret || '')}</div>
            </div>
          </div>
          
          <div class="client-card-actions">
            <button class="action-btn btn btn-sm btn-outline-light admin-only" data-act="edit" data-id="${c.id}" title="Edit">
              <i class="bi bi-pencil-fill"></i> Edit
            </button>
            <button class="action-btn btn btn-sm btn-outline-primary" data-act="metrics" data-id="${c.id}" title="View Metrics">
              <i class="bi bi-graph-up"></i> Metrics
            </button>
            <button class="action-btn btn btn-sm btn-outline-success" data-act="chat" data-id="${c.id}" title="Open Chat">
              <i class="bi bi-chat-dots-fill"></i> Chat
            </button>
            <button class="action-btn btn btn-sm btn-outline-danger admin-only" data-act="delete" data-id="${c.id}" title="Delete">
              <i class="bi bi-trash-fill"></i> Delete
            </button>
          </div>
        </div>`;
      grid.appendChild(col);
    });
    
    renderPagination();
  }

  async function render(){
    await loadClients();
    filteredClients = [...clients];
    renderClients();
  }

  // Respond to external updates (e.g. modal on dashboard saved a client)
  window.addEventListener('clients-updated', render);

  // Filter and pagination event listeners
  document.getElementById('searchInput').addEventListener('input', applyFilters);
  document.getElementById('providerFilter').addEventListener('change', applyFilters);
  document.getElementById('itemsPerPage').addEventListener('change', (e) => {
    itemsPerPageValue = e.target.value === 'all' ? 'all' : parseInt(e.target.value);
    currentPage = 1;
    renderClients();
  });
  
  document.getElementById('clearFilters').addEventListener('click', () => {
    document.getElementById('searchInput').value = '';
    document.getElementById('providerFilter').value = 'all';
    applyFilters();
  });
  
  // Pagination clicks
  document.addEventListener('click', (e) => {
    if (e.target.closest('.page-link') && e.target.dataset.page) {
      e.preventDefault();
      const page = parseInt(e.target.dataset.page);
      if (page >= 1 && page <= Math.ceil(filteredClients.length / itemsPerPageValue)) {
        currentPage = page;
        renderClients();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }
    // Handle clear filters in empty state
    if (e.target.id === 'clearFiltersBtn' || e.target.closest('#clearFiltersBtn')) {
      document.getElementById('searchInput').value = '';
      document.getElementById('providerFilter').value = 'all';
      applyFilters();
    }
  });

  function reset(){
    if(document.getElementById('modalClientForm')) document.getElementById('modalClientForm').reset();
    // Clear Azure-specific fields
    if(tenantId) tenantId.value = '';
    if(subscriptionId) subscriptionId.value = '';
    if(resourceGroup) resourceGroup.value = '';
    window.editingClientId = null;
    const modalTitle = document.getElementById('clientModalLabel');
    if(modalTitle) modalTitle.textContent = 'Add Client';
    // Reset provider to default and trigger field visibility
    if(provider) provider.value = 'aws';
    if(window.toggleAzureModalFields) window.toggleAzureModalFields();
  }

  grid.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if(!btn) return;
    const act = btn.dataset.act;
    const id = Number(btn.dataset.id);
    
    if(act === 'edit'){
      const client = clients.find(c => c.id === id);
      if (!client) return;
      
      console.log('Editing client:', client);
      const meta = client.metadata_json || {};
      if(provider) provider.value = meta.provider || 'aws';
      if(clientName) clientName.value = client.name;
      if(clientId) clientId.value = meta.clientId || '';
      if(clientSecret) clientSecret.value = meta.clientSecret || '';
      
      // Handle Azure fields
      if(tenantId) {
        tenantId.value = meta.tenantId || '';
        console.log('Set tenantId field to:', tenantId.value);
      }
      if(subscriptionId) {
        subscriptionId.value = meta.subscriptionId || '';
        console.log('Set subscriptionId field to:', subscriptionId.value, '(from meta:', meta.subscriptionId, ')');
      }
      if(resourceGroup) {
        resourceGroup.value = meta.resourceGroup || '';
        console.log('Set resourceGroup field to:', resourceGroup.value);
      }
      console.log('All Azure fields populated - tenantId:', meta.tenantId, 'subscriptionId:', meta.subscriptionId, 'resourceGroup:', meta.resourceGroup);
      
      // Trigger field visibility toggle based on provider
      if(window.toggleAzureModalFields) {
        setTimeout(() => window.toggleAzureModalFields(), 10);
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
      
      if (meta.provider === 'azure') {
        details += `Tenant ID: ${meta.tenantId || 'N/A'}\n`;
        details += `Subscription ID: ${meta.subscriptionId || 'N/A'}\n`;
        details += `Resource Group: ${meta.resourceGroup || 'N/A'}\n`;
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
