// Admin user management - stores demo users in localStorage under key 'users'
(function(){
  const STORAGE_KEY = 'users';

  function qs(id){ return document.getElementById(id); }

  function loadUsers(){
    try{ return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
    catch(e){ return []; }
  }

  function saveUsers(users){
    localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
    window.dispatchEvent(new Event('users-updated'));
  }

  function render(){
    const tbody = qs('usersTable');
    const users = loadUsers();
    tbody.innerHTML = '';
    if(users.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="4" class="text-muted">No users yet. Click Add User to create one.</td>';
      tbody.appendChild(tr);
      return;
    }

    users.forEach((u, idx)=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.role)}</td>
        <td>${escapeHtml(u.assignedClient || '-')}</td>
        <td>
          <button class="btn btn-sm btn-outline-light me-1" data-action="edit" data-idx="${idx}" title="Edit">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M12.146.146a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-9.793 9.793a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168L12.146.146zM11.207 2L3 10.207V12h1.793L14 3.793 11.207 2z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-action="assign" data-idx="${idx}" title="Assign Role">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M8 0a5 5 0 0 0-5 5v1H2a2 2 0 0 0-2 2v4.5A1.5 1.5 0 0 0 1.5 14H6v-1.5A2.5 2.5 0 0 1 8.5 10H10V5a5 5 0 0 0-2-4z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-light me-1" data-action="assignClient" data-idx="${idx}" title="Assign Client">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M6 8c1.657 0 3-1.567 3-3.5S7.657 1 6 1 3 2.567 3 4.5 4.343 8 6 8zm4.5 1a3.5 3.5 0 0 0-3.5 3.5V14h7v-1.5A3.5 3.5 0 0 0 10.5 9zM6 9a4 4 0 0 0-4 4v1h8v-1a4 4 0 0 0-4-4z"/></svg>
          </button>
          <button class="btn btn-sm btn-outline-danger" data-action="delete" data-idx="${idx}" title="Delete">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5.5 5.5a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5zm5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0v-6a.5.5 0 0 1 .5-.5z"/><path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9.5A1.5 1.5 0 0 1 11.5 15h-7A1.5 1.5 0 0 1 3 13.5V4H2.5a1 1 0 1 1 0-2H5l.5-1h5l.5 1h2.5a1 1 0 0 1 1 1zM4.118 4L4 13.5a.5.5 0 0 0 .5.5h7a.5.5 0 0 0 .5-.5L11.882 4H4.118z"/></svg>
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function openAssignClientModal(idx){
    // populate client select from localStorage 'clients' key
    const sel = qs('clientSelect');
    sel.innerHTML = '<option value="">— None —</option>';
    try{
      const clients = JSON.parse(localStorage.getItem('clients') || '[]');
      clients.forEach((c)=>{
        const opt = document.createElement('option');
        opt.value = c.id || c.idx || c.name || c.email || c.clientId || c.name;
        opt.textContent = c.name || c.title || opt.value;
        sel.appendChild(opt);
      });
    }catch(e){/* ignore */}
    qs('clientIndex').value = idx;
    const modalEl = document.getElementById('clientModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function openRoleModal(idx){
    const users = loadUsers();
    const u = users[idx];
    if(!u) return;
    qs('roleSelect').value = u.role || 'user';
    qs('roleIndex').value = idx;
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

  function openEdit(idx){
    const users = loadUsers();
    const u = users[idx];
    if(!u) return;
    qs('userName').value = u.name;
    qs('userEmail').value = u.email;
    qs('userRole').value = u.role || 'user';
    qs('userIndex').value = idx;
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function removeUser(idx){
    const users = loadUsers();
    if(idx < 0 || idx >= users.length) return;
    if(!confirm('Delete user "' + (users[idx].name || users[idx].email) + '"?')) return;
    users.splice(idx,1);
    saveUsers(users);
    render();
  }

  function handleTableClick(e){
    const btn = e.target.closest('button');
    if(!btn) return;
    const action = btn.dataset.action;
    const idx = parseInt(btn.dataset.idx,10);
    if(action === 'edit') openEdit(idx);
    if(action === 'delete') removeUser(idx);
    if(action === 'assign') openRoleModal(idx);
    if(action === 'assignClient') openAssignClientModal(idx);
  }

  function handleSubmit(e){
    e.preventDefault();
    const name = qs('userName').value.trim();
    const email = qs('userEmail').value.trim();
    const role = qs('userRole').value;
    if(!name || !email){
      alert('Name and email are required');
      return;
    }
    const users = loadUsers();
    const idx = qs('userIndex').value;
    if(idx === ''){
      users.push({name,email,role});
    } else {
      users[parseInt(idx,10)] = {name,email,role};
    }
    saveUsers(users);
    render();
    const modalEl = document.getElementById('userModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
  }

  function handleRoleSubmit(e){
    e.preventDefault();
    const role = qs('roleSelect').value;
    const idx = parseInt(qs('roleIndex').value,10);
    const users = loadUsers();
    if(typeof idx === 'number' && idx >= 0 && idx < users.length){
      users[idx].role = role;
      saveUsers(users);
      render();
    }
    const modalEl = document.getElementById('roleModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
  }

  function handleClientSubmit(e){
    e.preventDefault();
    const sel = qs('clientSelect');
    const selectedText = sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : '';
    const selectedVal = sel.value;
    const idx = parseInt(qs('clientIndex').value,10);
    const users = loadUsers();
    if(typeof idx === 'number' && idx >=0 && idx < users.length){
      users[idx].assignedClient = selectedVal ? selectedText : '';
      saveUsers(users);
      render();
    }
    const modalEl = document.getElementById('clientModal');
    const modal = bootstrap.Modal.getInstance(modalEl);
    if(modal) modal.hide();
  }

  function seedIfEmpty(){
    const users = loadUsers();
    if(users.length === 0){
      users.push({name:'Alice Admin', email:'alice@example.com', role:'admin'});
      users.push({name:'Bob User', email:'bob@example.com', role:'user'});
      saveUsers(users);
    }
  }

  // init
  document.addEventListener('DOMContentLoaded', ()=>{
    seedIfEmpty();
    render();
    qs('addUserBtn').addEventListener('click', openAdd);
    qs('usersTable').addEventListener('click', handleTableClick);
    qs('userForm').addEventListener('submit', handleSubmit);
    const roleForm = document.getElementById('roleForm');
    if(roleForm) roleForm.addEventListener('submit', handleRoleSubmit);
    const clientForm = document.getElementById('clientForm');
    if(clientForm) clientForm.addEventListener('submit', handleClientSubmit);

    // allow other pages to trigger a re-render when users change
    window.addEventListener('users-updated', render);
    window.addEventListener('storage', (ev)=>{
      if(ev.key === STORAGE_KEY) render();
    });
  });

})();
