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
  const subscriptionIdEl = document.getElementById('modalSubscriptionId');
  const subscriptionIdField = document.getElementById('subscriptionIdField');
  const resourceGroupEl = document.getElementById('modalResourceGroup');
  const resourceGroupField = document.getElementById('resourceGroupField');
  const clientIdEl = document.getElementById('modalClientId');
  const clientSecretEl = document.getElementById('modalClientSecret');

  // Debug: Log element references
  console.log('Modal elements initialized:', {
    providerSel: !!providerSel,
    tenantIdEl: !!tenantIdEl,
    subscriptionIdEl: !!subscriptionIdEl,
    resourceGroupEl: !!resourceGroupEl,
    clientIdEl: !!clientIdEl,
    clientSecretEl: !!clientSecretEl
  });

  function getToken(){
    try { return localStorage.getItem('token'); } catch(e){ return null; }
  }

  function toggleAzureFields(){
    if(!providerSel || !tenantIdField) return;
    const show = providerSel.value === 'azure';
    tenantIdField.style.display = show ? 'block' : 'none';
    if(subscriptionIdField) subscriptionIdField.style.display = show ? 'block' : 'none';
    if(resourceGroupField) resourceGroupField.style.display = show ? 'block' : 'none';
  }

  // Expose globally for clients.js to trigger after setting provider value
  window.toggleAzureModalFields = toggleAzureFields;

  if(providerSel){
    providerSel.addEventListener('change', toggleAzureFields);
    toggleAzureFields();
  }

  // Reset and show appropriate fields when modal opens
  if(modalEl){
    modalEl.addEventListener('show.bs.modal', function(){
      // Small delay to ensure provider value is set first (in case of edit)
      setTimeout(toggleAzureFields, 10);
    });
  }

  if(saveBtn){
    const newSave = saveBtn.cloneNode(true);
    saveBtn.parentNode.replaceChild(newSave, saveBtn);
    newSave.addEventListener('click', async function(){
      const name = (clientNameEl?.value || '').trim();
      const provider = providerSel?.value || '';
      const tenantId = (tenantIdEl?.value || '').trim();
      const subscriptionId = (subscriptionIdEl?.value || '').trim();
      const resourceGroup = (resourceGroupEl?.value || '').trim();
      const clientId = (clientIdEl?.value || '').trim();
      const clientSecret = (clientSecretEl?.value || '').trim();
      if(!name){ alert('Client name is required'); return; }
      if(!provider){ alert('Provider is required'); return; }
      if(provider === 'azure' && !tenantId){ alert('Tenant ID is required for Azure'); return; }
      if(provider === 'azure' && !subscriptionId){ alert('Subscription ID is required for Azure'); return; }
      if(!clientId || !clientSecret){ alert('Client ID and Secret are required'); return; }

      const metadata = { provider, clientId, clientSecret };
      if(provider === 'azure') {
        metadata.tenantId = tenantId;
        metadata.subscriptionId = subscriptionId;
        if(resourceGroup) metadata.resourceGroup = resourceGroup;
      }

      const token = getToken();
      if(!token){ alert('Not authenticated'); return; }

      try{
        const id = window.editingClientId;
        const url = id ? `${API_BASE}/clients/${id}` : `${API_BASE}/clients/`;
        const method = id ? 'PUT' : 'POST';
        const payload = { name, metadata_json: metadata };
        console.log('Saving client with payload:', payload);
        const res = await fetch(url, {
          method,
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
        if(!res.ok){
          const txt = await res.text();
          throw new Error(`Save failed: ${res.status} ${txt}`);
        }
        const savedData = await res.json();
        console.log('Client saved successfully:', savedData);
        // Notify listeners to reload clients (dispatch on window for consistency)
        window.dispatchEvent(new CustomEvent('clients-updated'));
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
