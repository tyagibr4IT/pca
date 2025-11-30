// clients-modal.js
// Handles Add/Edit Client modal - integrates with backend API and test endpoint
(function(){
  const API_BASE = 'http://localhost:8000/api';
  const modalEl = document.getElementById('clientModal');
  const saveBtn = document.getElementById('modalSaveClient');
  const testBtn = document.getElementById('modalTestConn');
  const providerSel = document.getElementById('modalProvider');
  const clientNameEl = document.getElementById('modalClientName');
  const tenantIdEl = document.getElementById('modalTenantId');
  const tenantIdField = document.getElementById('tenantIdField');
  const clientIdEl = document.getElementById('modalClientId');
  const clientSecretEl = document.getElementById('modalClientSecret');

  function getToken(){
    try { return localStorage.getItem('token'); } catch(e){ return null; }
  }

  function toggleAzureFields(){
    if(!providerSel || !tenantIdField) return;
    tenantIdField.style.display = providerSel.value === 'azure' ? 'block' : 'none';
  }

  if(providerSel){
    providerSel.addEventListener('change', toggleAzureFields);
    toggleAzureFields();
  }

  if(saveBtn){
    const newSave = saveBtn.cloneNode(true);
    saveBtn.parentNode.replaceChild(newSave, saveBtn);
    newSave.addEventListener('click', async function(){
      const name = (clientNameEl?.value || '').trim();
      const provider = providerSel?.value || '';
      const tenantId = (tenantIdEl?.value || '').trim();
      const clientId = (clientIdEl?.value || '').trim();
      const clientSecret = (clientSecretEl?.value || '').trim();
      if(!name){ alert('Client name is required'); return; }
      if(!provider){ alert('Provider is required'); return; }
      if(provider === 'azure' && !tenantId){ alert('Tenant ID is required for Azure'); return; }
      if(!clientId || !clientSecret){ alert('Client ID and Secret are required'); return; }

      const metadata = { provider, clientId, clientSecret };
      if(provider === 'azure') metadata.tenantId = tenantId;

      const token = getToken();
      if(!token){ alert('Not authenticated'); return; }

      try{
        const id = window.editingClientId;
        const url = id ? `${API_BASE}/clients/${id}` : `${API_BASE}/clients/`;
        const method = id ? 'PUT' : 'POST';
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ name, metadata_json: metadata })
        });
        if(!res.ok){
          const txt = await res.text();
          throw new Error(`Save failed: ${res.status} ${txt}`);
        }
        document.dispatchEvent(new CustomEvent('clients-updated'));
        const bsModal = bootstrap.Modal.getInstance(modalEl);
        if(bsModal) bsModal.hide();
      } catch(err){
        console.error('Error saving client', err);
        alert('Error saving client: ' + (err.message || err));
      }
    });
  }

  if(testBtn){
    const newTest = testBtn.cloneNode(true);
    testBtn.parentNode.replaceChild(newTest, testBtn);
    newTest.addEventListener('click', async function(){
      const token = getToken();
      if(!token){ alert('Not authenticated'); return; }
      const id = window.editingClientId;
      if(!id){
        alert('Save the client first, then test the connection.');
        return;
      }
      try{
        const res = await fetch(`${API_BASE}/clients/${id}/test`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if(!res.ok){
          throw new Error(data?.detail || `Test failed: ${res.status}`);
        }
        const msg = data.ok ? `Success: ${data.details || 'Credentials valid'}` : `Failed: ${data.details || 'Invalid credentials'}`;
        alert(msg);
      } catch(err){
        console.error('Test connection error', err);
        alert('Error testing connection: ' + (err.message || err));
      }
    });
  }
})();
