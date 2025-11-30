// Admin user management - integrated with backend API
(function(){
  const API_BASE = 'http://localhost:8000/api';
  function getAuthHeaders(){
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }
  let users = [];
  let clients = [];

  function qs(id){ return document.getElementById(id); }

  async function loadUsers(){
    try {
      const response = await fetch(`${API_BASE}/users/`, { headers: getAuthHeaders() });
      if (!response.ok) throw new Error('Failed to load users');
      users = await response.json();
      return users;
    } catch (error) {
      console.error('Error loading users:', error);
      return [];
    }
  }

  async function loadClients(){
    try {
      const response = await fetch(`${API_BASE}/clients/`, { headers: getAuthHeaders() });
      if (!response.ok) throw new Error('Failed to load clients');
      clients = await response.json();
      return clients;
    } catch (error) {
      console.error('Error loading clients:', error);
      return [];
    }
  }

  async function render(){
    const tbody = qs('usersTable');
    await loadUsers();
    // also load clients to resolve assigned client names
    await loadClients();
    tbody.innerHTML = '';
    if(users.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="5" class="text-muted">No users yet. Click Add User to create one.</td>';
      tbody.appendChild(tr);
      return;
    }

    users.forEach((u)=>{
      const tr = document.createElement('tr');
      const assignedName = (()=>{ const c = clients.find(x => x.id === u.assigned_client_id); return c ? c.name : '-'; })();
      tr.innerHTML = `
        <td>${escapeHtml(u.username)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.role)}</td>
        <td>${escapeHtml(assignedName)}</td>
        <td>
          <button class="btn btn-sm btn-outline-light me-1" data-action="edit" data-id="${u.id}" title="Edit">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-9.793 9.793a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168L12.146.146zM11.207 2L3 10.207V12h1.793L14 3.793 11.207 2z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-action="assign" data-id="${u.id}" title="Assign Role">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0a5 5 0 0 0-5 5v1H2a2 2 0 0 0-2 2v4.5A1.5 1.5 0 0 0 1.5 14H6v-1.5A2.5 2.5 0 0 1 8.5 10H10V5a5 5 0 0 0-2-4z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-action="assignClient" data-id="${u.id}" title="Assign Client">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M6 8c1.657 0 3-1.567 3-3.5S7.657 1 6 1 3 2.567 3 4.5 4.343 8 6 8zm4.5 1a3.5 3.5 0 0 0-3.5 3.5V14h7v-1.5A3.5 3.5 0 0 0 10.5 9zM6 9a4 4 0 0 0-4 4v1h8v-1a4 4 0 0 0-4-4z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${u.id}" title="Delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5zm5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9.5A1.5 1.5 0 0 1 11.5 15h-7A1.5 1.5 0 0 1 3 13.5V4H2.5a1 1 0 1 1 0-2H5l.5-1h5l.5 1h2.5a1 1 0 0 1 1 1zM4.118 4L4 13.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5L11.882 4H4.118z"/></svg>
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function openAssignClientModal(id){
    await loadClients();
    const sel = qs('clientSelect');
    sel.innerHTML = '<option value="">— None —</option>';
    clients.forEach((c)=>{
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
    qs('clientIndex').value = id;
    const modalEl = document.getElementById('clientModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
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

  function escapeHtml(s){
    if(!s && s !== 0) return '';
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function openAdd(){
    qs('userForm').reset();
    qs('userIndex').value = '';
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
    qs('userIndex').value = id;
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
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
  }

  async function handleSubmit(e){
    e.preventDefault();
    const name = qs('userName').value.trim();
    const email = qs('userEmail').value.trim();
    const role = qs('userRole').value;
    if(!name || !email){
      alert('Username and email are required');
      return;
    }
    
    const id = qs('userIndex').value;
    
    try {
      if(id === ''){
        // Create new user - default to tenant 1
        const response = await fetch(`${API_BASE}/users/`, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            tenant_id: 1,
            username: name,
            email,
            role
          })
        });
        if (response.status === 401) { location.href = './login.html'; return; }
        if (!response.ok) throw new Error('Failed to create user');
      } else {
        // Update existing user
        const response = await fetch(`${API_BASE}/users/${id}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify({ username: name, email, role })
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
    const sel = qs('clientSelect');
    const selectedText = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : '';
    const selectedVal = sel.value;
    const id = parseInt(qs('clientIndex').value,10);
    
    try {
      const response = await fetch(`${API_BASE}/users/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ assigned_client_id: selectedVal ? parseInt(selectedVal,10) : null })
      });
      if (response.status === 401) { location.href = './login.html'; return; }
      if (!response.ok) throw new Error('Failed to assign client');

      await render();
      const modalEl = document.getElementById('clientModal');
      const modal = bootstrap.Modal.getInstance(modalEl);
      if(modal) modal.hide();
    } catch (error) {
      console.error('Error assigning client:', error);
      alert('Failed to assign client');
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

  // init
  document.addEventListener('DOMContentLoaded', async ()=>{
    await seedIfEmpty();
    await render();
    qs('addUserBtn').addEventListener('click', openAdd);
    qs('usersTable').addEventListener('click', handleTableClick);
    qs('userForm').addEventListener('submit', handleSubmit);
    const roleForm = document.getElementById('roleForm');
    if(roleForm) roleForm.addEventListener('submit', handleRoleSubmit);
    const clientForm = document.getElementById('clientForm');
    if(clientForm) clientForm.addEventListener('submit', handleClientSubmit);

    // allow other pages to trigger a re-render when users change
    window.addEventListener('users-updated', render);
  });

})();
