// Admin user management - integrated with backend API
(function(){
  const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';
  function getAuthHeaders(){
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }
  let users = [];
  let clients = [];
  let filteredUsers = [];
  
  // Pagination
  let currentPage = 1;
  const usersPerPage = 10;
  
  // Client modal state
  let clientModalState = {
    userId: null,
    currentPage: 1,
    filter: 'all',
    search: '',
    cloudType: '',
    totalClients: 0,
    clientsPerPage: 10,
    selectedClients: {} // { clientId: permission }
  };

  function qs(id){ return document.getElementById(id); }

  async function loadUsers(){
    try {
      const response = await fetch(`${API_BASE}/users/`, { headers: getAuthHeaders() });
      if (response.status === 401) {
        location.href = './login.html';
        return [];
      }
      if (!response.ok) throw new Error('Failed to load users');
      users = await response.json();
      return users;
    } catch (error) {
      console.error('Error loading users:', error);
      users = [];
      return [];
    }
  }

  async function loadClients(){
    try {
      const response = await fetch(`${API_BASE}/clients/`, { headers: getAuthHeaders() });
      if (response.status === 401) {
        location.href = './login.html';
        return [];
      }
      if (!response.ok) throw new Error('Failed to load clients');
      clients = await response.json();
      return clients;
    } catch (error) {
      console.error('Error loading clients:', error);
      clients = [];
      return [];
    }
  }

  async function render(){
    const tbody = qs('usersTable');
    console.log('render() called, loading users...');
    await loadUsers();
    console.log('Users loaded:', users.length);
    
    // Apply filters
    applyFilters();
    console.log('Filtered users:', filteredUsers.length);
    
    // Paginate
    const startIndex = (currentPage - 1) * usersPerPage;
    const endIndex = startIndex + usersPerPage;
    const paginatedUsers = filteredUsers.slice(startIndex, endIndex);
    
    tbody.innerHTML = '';
    if(filteredUsers.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="text-muted text-center py-4">No users found. Try adjusting your filters or add a new user.</td>';
      tbody.appendChild(tr);
      updatePaginationInfo();
      return;
    }

    paginatedUsers.forEach((u)=>{
      const tr = document.createElement('tr');
      const initials = u.username ? u.username.substring(0, 2).toUpperCase() : 'U';
      const status = u.status || 'active'; // Default to active if not set
      
      // Get current user role
      const currentUser = window.loadCurrentUser ? window.loadCurrentUser() : null;
      const currentUserRole = currentUser ? currentUser.role : null;
      
      // Members should see no action buttons at all
      const showActions = currentUserRole !== 'member';
      
      // Build assigned clients display
      let assignedClientsHtml = '';
      if (u.assigned_clients && u.assigned_clients.length > 0) {
        const firstTwo = u.assigned_clients.slice(0, 2);
        assignedClientsHtml = firstTwo.map(c => `<span class="badge bg-secondary me-1">${escapeHtml(c.name)}</span>`).join('');
        
        if (u.assigned_clients.length > 2) {
          assignedClientsHtml += `<button class="btn btn-sm btn-link p-0 text-decoration-none" data-action="assignClient" data-id="${u.id}" style="font-size: 0.75rem;">+${u.assigned_clients.length - 2} more</button>`;
        }
      } else {
        assignedClientsHtml = '<span class="text-muted">None</span>';
      }
      
      tr.innerHTML = `
        <td>
          <div class="user-info">
            <div class="user-avatar">${initials}</div>
            <div class="user-details">
              <p class="user-name">${escapeHtml(u.username)}</p>
              <p class="user-email">${escapeHtml(u.email)}</p>
            </div>
          </div>
        </td>
        <td><span class="role-badge ${escapeHtml(u.role)}">${escapeHtml(u.role)}</span></td>
        <td>
          <span class="status-badge ${status}">
            <span class="status-indicator"></span>
            ${status.charAt(0).toUpperCase() + status.slice(1)}
          </span>
        </td>
        <td>${assignedClientsHtml}</td>
        <td class="text-end">
          ${showActions && window.PermissionManager?.hasPermission('users.edit') ? `
          <button class="btn btn-sm action-btn" data-action="edit" data-id="${u.id}" title="Edit User">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-9.793 9.793a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168L12.146.146zM11.207 2L3 10.207V12h1.793L14 3.793 11.207 2z"/></svg>
          </button>
          ` : ''}
          ${showActions && window.PermissionManager?.hasPermission('users.manage_roles') ? `
          <button class="btn btn-sm action-btn" data-action="assign" data-id="${u.id}" title="Change Role">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0a5 5 0 0 0-5 5v1H2a2 2 0 0 0-2 2v4.5A1.5 1.5 0 0 0 1.5 14H6v-1.5A2.5 2.5 0 0 1 8.5 10H10V5a5 5 0 0 0-2-4z"/></svg>
          </button>
          ` : ''}
          ${showActions && window.PermissionManager?.hasPermission('clients.assign') ? `
          <button class="btn btn-sm action-btn" data-action="assignClient" data-id="${u.id}" title="Assign Client">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M6 8c1.657 0 3-1.567 3-3.5S7.657 1 6 1 3 2.567 3 4.5 4.343 8 6 8zm4.5 1a3.5 3.5 0 0 0-3.5 3.5V14h7v-1.5A3.5 3.5 0 0 0 10.5 9zM6 9a4 4 0 0 0-4 4v1h8v-1a4 4 0 0 0-4-4z"/></svg>
          </button>
          ` : ''}
          ${showActions && window.PermissionManager?.hasPermission('permissions.manage') && u.id !== 1 ? `
          <button class="btn btn-sm action-btn" data-action="managePermissions" data-id="${u.id}" title="Manage Permissions">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 1a2 2 0 0 1 2 2v4H6V3a2 2 0 0 1 2-2zm3 6V3a3 3 0 0 0-6 0v4a2 2 0 0 0-2 2v5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/></svg>
          </button>
          ` : ''}
          ${showActions && window.PermissionManager?.hasPermission('users.delete') ? `
          <button class="btn btn-sm action-btn delete" data-action="delete" data-id="${u.id}" title="Delete User">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5zm5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9.5A1.5 1.5 0 0 1 11.5 15h-7A1.5 1.5 0 0 1 3 13.5V4H2.5a1 1 0 1 1 0-2H5l.5-1h5l.5 1h2.5a1 1 0 0 1 1 1zM4.118 4L4 13.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5L11.882 4H4.118z"/></svg>
          </button>
          ` : ''}
        </td>
      `;
      tbody.appendChild(tr);
    });
    
    updatePaginationInfo();
  }

  async function openAssignClientModal(id){
    const user = users.find(u => u.id === id);
    if(!user) return;
    
    // Check if current user can assign to this user
    const currentUser = await window.loadCurrentUser();
    if(currentUser && currentUser.role !== 'superadmin'){
      // Admins can only assign to members
      if(user.role === 'admin' || user.role === 'superadmin'){
        alert('Admins can only assign clients to members, not to other admins.');
        return;
      }
    }
    
    clientModalState = {
      userId: id,
      currentPage: 1,
      filter: 'all',
      search: '',
      cloudType: '',
      totalClients: 0,
      clientsPerPage: 10,
      selectedClients: {}
    };
    
    qs('clientUserId').value = id;
    qs('clientSearchInput').value = '';
    qs('filterAll').checked = true;
    qs('cloudAll').checked = true;
    
    await loadClientModalPage();
    
    const modalEl = document.getElementById('clientModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }
  
  async function loadClientModalPage() {
    const container = qs('clientPermissionsList');
    const loadingDiv = qs('clientsLoading');
    const noClientsDiv = qs('noClientsFound');
    
    // Show loading
    container.innerHTML = '';
    loadingDiv.style.display = 'block';
    noClientsDiv.style.display = 'none';
    
    try {
      const offset = (clientModalState.currentPage - 1) * clientModalState.clientsPerPage;
      const response = await fetch(
        `${API_BASE}/users/${clientModalState.userId}/available-clients?` +
        `filter=${clientModalState.filter}&` +
        `search=${encodeURIComponent(clientModalState.search)}&` +
        `cloud_type=${clientModalState.cloudType}&` +
        `limit=${clientModalState.clientsPerPage}&` +
        `offset=${offset}`,
        { headers: getAuthHeaders() }
      );
      
      if (!response.ok) throw new Error('Failed to load clients');
      
      const data = await response.json();
      clientModalState.totalClients = data.total;
      
      loadingDiv.style.display = 'none';
      
      if (data.clients.length === 0) {
        noClientsDiv.style.display = 'block';
        updateClientPagination();
        return;
      }
      
      renderClientPermissionsList(data.clients);
      updateClientPagination();
      
    } catch (error) {
      console.error('Error loading clients:', error);
      loadingDiv.style.display = 'none';
      noClientsDiv.style.display = 'block';
      noClientsDiv.textContent = 'Error loading clients';
    }
  }
  
  function renderClientPermissionsList(clientsList) {
    const container = qs('clientPermissionsList');
    container.innerHTML = '';
    
    clientsList.forEach(client => {
      const isChecked = clientModalState.selectedClients.hasOwnProperty(client.id) 
        ? true 
        : client.assigned;
      const permission = clientModalState.selectedClients[client.id] || client.permission;
      
      // Get provider badge styling
      const providerBadge = {
        'aws': '<span class="badge bg-warning text-dark ms-2">AWS</span>',
        'azure': '<span class="badge bg-info text-dark ms-2">Azure</span>',
        'gcp': '<span class="badge bg-success ms-2">GCP</span>'
      }[client.provider] || `<span class="badge bg-secondary ms-2">${client.provider || 'Unknown'}</span>`;
      
      const itemDiv = document.createElement('div');
      itemDiv.className = `client-permission-item ${isChecked ? 'selected' : ''}`;
      itemDiv.innerHTML = `
        <div class="form-check">
          <input class="form-check-input" type="checkbox" value="${client.id}" id="client-${client.id}" ${isChecked ? 'checked' : ''}>
          <label class="form-check-label" for="client-${client.id}">
            ${escapeHtml(client.name)}${providerBadge}
          </label>
        </div>
        <select class="permission-select" data-client-id="${client.id}" ${!isChecked ? 'disabled' : ''}>
          <option value="viewer" ${permission === 'viewer' ? 'selected' : ''}>Viewer</option>
          <option value="editor" ${permission === 'editor' ? 'selected' : ''}>Editor</option>
          <option value="approver" ${permission === 'approver' ? 'selected' : ''}>Approver</option>
        </select>
      `;
      
      const checkbox = itemDiv.querySelector('.form-check-input');
      const selectBox = itemDiv.querySelector('.permission-select');
      
      checkbox.addEventListener('change', function() {
        const clientId = parseInt(this.value, 10);
        selectBox.disabled = !this.checked;
        itemDiv.classList.toggle('selected', this.checked);
        
        if (this.checked) {
          clientModalState.selectedClients[clientId] = selectBox.value;
        } else {
          delete clientModalState.selectedClients[clientId];
        }
      });
      
      selectBox.addEventListener('change', function() {
        const clientId = parseInt(this.dataset.clientId, 10);
        if (checkbox.checked) {
          clientModalState.selectedClients[clientId] = this.value;
        }
      });
      
      // Initialize state
      if (isChecked) {
        clientModalState.selectedClients[client.id] = permission;
      }
      
      container.appendChild(itemDiv);
    });
  }
  
  function updateClientPagination() {
    const total = clientModalState.totalClients;
    const currentPage = clientModalState.currentPage;
    const perPage = clientModalState.clientsPerPage;
    
    const startIndex = (currentPage - 1) * perPage + 1;
    const endIndex = Math.min(currentPage * perPage, total);
    const totalPages = Math.ceil(total / perPage);
    
    qs('clientPaginationInfo').textContent = total > 0 
      ? `Showing ${startIndex}-${endIndex} of ${total}`
      : 'No clients';
    
    qs('clientPrevPage').disabled = currentPage === 1;
    qs('clientNextPage').disabled = currentPage >= totalPages;
  }
  
  function clientPrevPage() {
    if (clientModalState.currentPage > 1) {
      clientModalState.currentPage--;
      loadClientModalPage();
    }
  }
  
  function clientNextPage() {
    const totalPages = Math.ceil(clientModalState.totalClients / clientModalState.clientsPerPage);
    if (clientModalState.currentPage < totalPages) {
      clientModalState.currentPage++;
      loadClientModalPage();
    }
  }
  
  function onClientFilterChange() {
    const selectedFilter = document.querySelector('input[name="clientFilter"]:checked');
    if (selectedFilter) {
      clientModalState.filter = selectedFilter.value;
      clientModalState.currentPage = 1;
      loadClientModalPage();
    }
  }
  
  function onClientSearchChange() {
    clientModalState.search = qs('clientSearchInput').value;
    clientModalState.currentPage = 1;
    loadClientModalPage();
  }
  
  function onCloudTypeChange() {
    const selectedRadio = document.querySelector('input[name="cloudTypeFilter"]:checked');
    clientModalState.cloudType = selectedRadio ? selectedRadio.value : '';
    clientModalState.currentPage = 1;
    loadClientModalPage();
  }

  function openRoleModal(id){
    const user = users.find(u => u.id === id);
    if(!user) return;
    qs('roleSelect').value = user.role || 'member';
    qs('roleIndex').value = id;
    const modalEl = document.getElementById('roleModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  async function openPermissionsModal(userId){
    const user = users.find(u => u.id === userId);
    if(!user) return;
    
    qs('permUserId').value = userId;
    qs('permUserName').textContent = user.username;
    qs('permUserRole').textContent = user.role || 'member';
    
    // Load user's effective permissions
    try {
      const response = await fetch(`${API_BASE}/permissions/user/${userId}/effective`, {
        headers: getAuthHeaders()
      });
      
      if(!response.ok) throw new Error('Failed to load permissions');
      
      const data = await response.json();
      
      // Display role permissions (read-only)
      const rolePermsContainer = qs('userRolePermissions');
      if(data.role_permissions.length === 0){
        rolePermsContainer.innerHTML = '<div class="text-muted small">No role permissions</div>';
      } else {
        rolePermsContainer.innerHTML = data.role_permissions
          .map(p => `<span class="badge bg-secondary me-1 mb-1">${escapeHtml(p)}</span>`)
          .join('');
      }
      
      // Display user-specific permissions (editable)
      const userPermsContainer = qs('userSpecificPermissions');
      if(data.user_specific_permissions.length === 0){
        userPermsContainer.innerHTML = '<div class="text-muted small">No additional permissions</div>';
      } else {
        userPermsContainer.innerHTML = data.user_specific_permissions
          .map(p => `
            <span class="badge bg-primary me-1 mb-1">
              ${escapeHtml(p)}
              <button type="button" class="btn-close btn-close-white btn-sm ms-1" 
                      onclick="revokeUserPermission(${userId}, '${escapeHtml(p)}')" 
                      style="font-size: 0.6rem; vertical-align: middle;"></button>
            </span>
          `)
          .join('');
      }
      
      // Load available permissions
      const availResponse = await fetch(`${API_BASE}/permissions/available`, {
        headers: getAuthHeaders()
      });
      
      if(!availResponse.ok) throw new Error('Failed to load available permissions');
      
      const allPerms = await availResponse.json();
      const availablePerms = allPerms.filter(p => 
        !data.role_permissions.includes(p.name) && 
        !data.user_specific_permissions.includes(p.name)
      );
      
      const availContainer = qs('availablePermissions');
      if(availablePerms.length === 0){
        availContainer.innerHTML = '<div class="text-muted small">No additional permissions available</div>';
      } else {
        // Group by resource
        const grouped = {};
        availablePerms.forEach(p => {
          if(!grouped[p.resource]) grouped[p.resource] = [];
          grouped[p.resource].push(p);
        });
        
        let html = '';
        for(const [resource, perms] of Object.entries(grouped)){
          html += `<div class="mb-2"><h6 class="text-uppercase text-muted" style="font-size: 0.7rem">${escapeHtml(resource)}</h6>`;
          perms.forEach(p => {
            html += `
              <button type="button" class="btn btn-sm btn-outline-primary me-1 mb-1" 
                      onclick="grantUserPermission(${userId}, '${escapeHtml(p.name)}')">
                ${escapeHtml(p.name)}
              </button>
            `;
          });
          html += '</div>';
        }
        availContainer.innerHTML = html;
      }
      
    } catch(error){
      console.error('Error loading permissions:', error);
      alert('Failed to load user permissions');
      return;
    }
    
    const modalEl = document.getElementById('permissionsModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  window.grantUserPermission = async function(userId, permissionName){
    try {
      const response = await fetch(`${API_BASE}/permissions/user/${userId}/grant`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify([permissionName])
      });
      
      if(!response.ok) throw new Error('Failed to grant permission');
      
      // Reload the modal
      await openPermissionsModal(userId);
    } catch(error){
      console.error('Error granting permission:', error);
      alert('Failed to grant permission');
    }
  };

  window.revokeUserPermission = async function(userId, permissionName){
    if(!confirm(`Remove permission "${permissionName}"?`)) return;
    
    try {
      const response = await fetch(`${API_BASE}/permissions/user/${userId}/revoke`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify([permissionName])
      });
      
      if(!response.ok) throw new Error('Failed to revoke permission');
      
      // Reload the modal
      await openPermissionsModal(userId);
    } catch(error){
      console.error('Error revoking permission:', error);
      alert('Failed to revoke permission');
    }
  };

  function escapeHtml(s){
    if(!s && s !== 0) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function openAdd(){
    qs('userForm').reset();
    qs('userIndex').value = '';
    qs('modalTitle').textContent = 'Add User';
    qs('userPassword').required = true;
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function openEdit(id){
    const user = users.find(u => u.id === id);
    if(!user) return;
    qs('userName').value = user.username;
    qs('userEmail').value = user.email;
    qs('userRole').value = user.role || 'member';
    qs('userStatus').value = user.status || 'active';
    qs('userPassword').value = '';
    qs('userPassword').required = false;
    qs('userIndex').value = id;
    qs('modalTitle').textContent = 'Edit User';
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }
  
  function applyFilters(){
    const searchTerm = qs('searchInput').value.toLowerCase();
    const roleFilter = qs('roleFilter').value;
    const statusFilter = qs('statusFilter').value;
    
    filteredUsers = users.filter(u => {
      const matchesSearch = !searchTerm || 
        u.username.toLowerCase().includes(searchTerm) || 
        u.email.toLowerCase().includes(searchTerm);
      const matchesRole = !roleFilter || u.role === roleFilter;
      const matchesStatus = !statusFilter || (u.status || 'active') === statusFilter;
      
      return matchesSearch && matchesRole && matchesStatus;
    });
    
    currentPage = 1; // Reset to first page when filtering
  }
  
  function updatePaginationInfo(){
    const totalUsers = filteredUsers.length;
    const startIndex = (currentPage - 1) * usersPerPage + 1;
    const endIndex = Math.min(currentPage * usersPerPage, totalUsers);
    const totalPages = Math.ceil(totalUsers / usersPerPage);
    
    qs('paginationInfo').textContent = totalUsers > 0 
      ? `Showing ${startIndex}-${endIndex} of ${totalUsers} users`
      : 'No users to display';
    
    // Update pagination controls
    qs('prevPage').disabled = currentPage === 1;
    qs('nextPage').disabled = currentPage >= totalPages;
    
    // Generate page numbers
    const pageNumbersContainer = qs('pageNumbers');
    pageNumbersContainer.innerHTML = '';
    
    if(totalPages > 1){
      for(let i = 1; i <= totalPages; i++){
        if(i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)){
          const btn = document.createElement('button');
          btn.className = `page-number ${i === currentPage ? 'active' : ''}`;
          btn.textContent = i;
          btn.onclick = () => goToPage(i);
          pageNumbersContainer.appendChild(btn);
        } else if(i === currentPage - 2 || i === currentPage + 2){
          const span = document.createElement('span');
          span.textContent = '...';
          span.style.padding = '0.4rem 0.5rem';
          span.style.color = '#8b92a7';
          pageNumbersContainer.appendChild(span);
        }
      }
    }
  }
  
  function goToPage(page){
    currentPage = page;
    render();
  }
  
  function nextPage(){
    const totalPages = Math.ceil(filteredUsers.length / usersPerPage);
    if(currentPage < totalPages){
      currentPage++;
      render();
    }
  }
  
  function prevPage(){
    if(currentPage > 1){
      currentPage--;
      render();
    }
  }
  
  function togglePasswordVisibility(){
    const passwordInput = qs('userPassword');
    const button = qs('togglePassword');
    if(passwordInput.type === 'password'){
      passwordInput.type = 'text';
      button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M13.359 11.238C15.06 9.72 16 8 16 8s-3-5.5-8-5.5a7.028 7.028 0 0 0-2.79.588l.77.771A5.944 5.944 0 0 1 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.134 13.134 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755-.165.165-.337.328-.517.486l.708.709z"/>
        <path d="M11.297 9.176a3.5 3.5 0 0 0-4.474-4.474l.823.823a2.5 2.5 0 0 1 2.829 2.829l.822.822zm-2.943 1.299.822.822a3.5 3.5 0 0 1-4.474-4.474l.823.823a2.5 2.5 0 0 0 2.829 2.829z"/>
        <path d="M3.35 5.47c-.18.16-.353.322-.518.487A13.134 13.134 0 0 0 1.172 8l.195.288c.335.48.83 1.12 1.465 1.755C4.121 11.332 5.881 12.5 8 12.5c.716 0 1.39-.133 2.02-.36l.77.772A7.029 7.029 0 0 1 8 13.5C3 13.5 0 8 0 8s.939-1.721 2.641-3.238l.708.709zm10.296 8.884-12-12 .708-.708 12 12-.708.708z"/>
      </svg>`;
    } else {
      passwordInput.type = 'password';
      button.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
        <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/>
        <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/>
      </svg>`;
    }
  }

  async function removeUser(id){
    const user = users.find(u => u.id === id);
    if(!user) return;
    if(!confirm('Delete user "' + (user.username || user.email) + '"?')) return;
    
    try {
      const response = await fetch(`${API_BASE}/users/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
      if (response.status === 401) { location.href = './login.html'; return; }
      if (!response.ok) throw new Error('Failed to delete user');
      await render();
    } catch (error) {
      console.error('Error deleting user:', error);
      alert('Failed to delete user');
    }
  }

  function handleTableClick(e){
    const btn = e.target.closest('button');
    if(!btn) return;
    const action = btn.dataset.action;
    const id = parseInt(btn.dataset.id,10);
    if(action === 'edit') openEdit(id);
    if(action === 'delete') removeUser(id);
    if(action === 'assign') openRoleModal(id);
    if(action === 'assignClient') openAssignClientModal(id);
    if(action === 'managePermissions') openPermissionsModal(id);
  }

  async function handleSubmit(e){
    e.preventDefault();
    const name = qs('userName').value.trim();
    const email = qs('userEmail').value.trim();
    const password = qs('userPassword').value;
    const role = qs('userRole').value;
    const status = qs('userStatus').value;
    
    if(!name || !email){
      alert('Username and email are required');
      return;
    }
    
    const id = qs('userIndex').value;
    
    try {
      if(id === ''){
        // Create new user - password is required
        if(!password){
          alert('Password is required for new users');
          return;
        }
        const response = await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            tenant_id: 1,
            username: name,
            email,
            password,
            role,
            status
          })
        });
        if (response.status === 401) { location.href = './login.html'; return; }
        if (!response.ok) throw new Error('Failed to create user');
      } else {
        // Update existing user - password is optional
        const updateData = { username: name, email, role, status };
        if(password) {
          updateData.password = password; // Only include if provided
        }
        const response = await fetch(`${API_BASE}/users/${id}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(updateData)
        });
        if (response.status === 401) { location.href = './login.html'; return; }
        if (!response.ok) throw new Error('Failed to update user');
      }
      
      await render();
      const modalEl = document.getElementById('userModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if(modal) modal.hide();
    } catch (error) {
      console.error('Error saving user:', error);
      alert('Failed to save user');
    }
  }

  async function handleRoleSubmit(e){
    e.preventDefault();
    const role = qs('roleSelect').value;
    const id = parseInt(qs('roleIndex').value,10);
    
    try {
      const response = await fetch(`${API_BASE}/users/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ role })
      });
      if (response.status === 401) { location.href = './login.html'; return; }
      if (!response.ok) throw new Error('Failed to update role');
      
      await render();
      const modalEl = document.getElementById('roleModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if(modal) modal.hide();
    } catch (error) {
      console.error('Error updating role:', error);
      alert('Failed to update role');
    }
  }

  async function handleClientSubmit(e){
    e.preventDefault();
    
    const userId = parseInt(qs('clientUserId').value, 10);
    
    // Get all selected clients from state
    const permissions = Object.entries(clientModalState.selectedClients).map(([clientId, permission]) => ({
      client_id: parseInt(clientId, 10),
      permission: permission
    }));
    
    try {
      const response = await fetch(`${API_BASE}/users/${userId}/client-permissions`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ permissions })
      });
      
      if (response.status === 401) { location.href = './login.html'; return; }
      if (!response.ok) throw new Error('Failed to assign clients');

      await render();
      const modalEl = document.getElementById('clientModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if(modal) modal.hide();
    } catch (error) {
      console.error('Error assigning clients:', error);
      alert('Failed to assign clients');
    }
  }

  async function seedIfEmpty(){
    await loadUsers();
    if(users.length === 0){
      try {
        await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            tenant_id: 1,
            username: 'Alice Admin',
            email: 'alice@example.com',
            role: 'admin'
          })
        });
        await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            tenant_id: 1,
            username: 'Bob User',
            email: 'bob@example.com',
            role: 'member'
          })
        });
      } catch (error) {
        console.error('Error seeding users:', error);
      }
    }
  }

  // Helper function to debounce search input
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // Initialize on page load
  document.addEventListener('DOMContentLoaded', async ()=>{
    // Initialize permissions first
    if (window.PermissionManager) {
      await window.PermissionManager.initializePermissions();
    }
    
    // Load current user info for navbar dropdown
    await window.loadCurrentUser();
    
    await seedIfEmpty();
    filteredUsers = [...users]; // Initialize filtered users
    await render();
    
    qs('addUserBtn').addEventListener('click', openAdd);
    qs('usersTable').addEventListener('click', handleTableClick);
    qs('userForm').addEventListener('submit', handleSubmit);
    
    // Search and filter events
    qs('searchInput').addEventListener('input', render);
    qs('roleFilter').addEventListener('change', render);
    qs('statusFilter').addEventListener('change', render);
    
    // Pagination events
    qs('prevPage').addEventListener('click', prevPage);
    qs('nextPage').addEventListener('click', nextPage);
    
    // Client modal filter radio buttons
    const clientFilterRadios = document.querySelectorAll('input[name="clientFilter"]');
    clientFilterRadios.forEach(radio => {
      radio.addEventListener('change', onClientFilterChange);
    });
    
    // Client modal search input with debouncing
    const clientSearchInput = document.getElementById('clientSearchInput');
    if (clientSearchInput) {
      clientSearchInput.addEventListener('input', debounce(onClientSearchChange, 300));
    }
    
    // Client modal cloud type filter radio buttons
    const cloudTypeRadios = document.querySelectorAll('input[name="cloudTypeFilter"]');
    cloudTypeRadios.forEach(radio => {
      radio.addEventListener('change', onCloudTypeChange);
    });
    
    // Client modal pagination buttons
    const clientPrevBtn = document.getElementById('clientPrevPage');
    const clientNextBtn = document.getElementById('clientNextPage');
    if (clientPrevBtn) clientPrevBtn.addEventListener('click', clientPrevPage);
    if (clientNextBtn) clientNextBtn.addEventListener('click', clientNextPage);
    
    // Password toggle
    qs('togglePassword').addEventListener('click', togglePasswordVisibility);
    
    const roleForm = document.getElementById('roleForm');
    if(roleForm) roleForm.addEventListener('submit', handleRoleSubmit);
    const clientForm = document.getElementById('clientForm');
    if(clientForm) clientForm.addEventListener('submit', handleClientSubmit);

    // allow other pages to trigger a re-render when users change
    window.addEventListener('users-updated', render);
  });

})();
