// clients-modal.js
// Handles Add/Edit Client modal - integrates with backend API and test endpoint
(function(){
  const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';
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
  const gcpJsonField = document.getElementById('gcpJsonField');
  const gcpJsonFile = document.getElementById('modalGcpJsonFile');
  const gcpJsonPreview = document.getElementById('gcpJsonPreview');
  const projectIdField = document.getElementById('projectIdField');
  const projectIdEl = document.getElementById('modalProjectId');
  const clientIdEl = document.getElementById('modalClientId');
  const clientSecretEl = document.getElementById('modalClientSecret');
  const awsAwsField = document.getElementById('awsAwsField');
  const awsSecretField = document.getElementById('awsSecretField');

  // Store parsed GCP JSON
  let gcpJsonData = null;

  function getToken(){
    try { return localStorage.getItem('token'); } catch(e){ return null; }
  }

  function toggleProviderFields(){
    if(!providerSel) return;
    const provider = providerSel.value;
    
    // Show/hide Azure fields
    const showAzure = provider === 'azure';
    if(tenantIdField) tenantIdField.style.display = showAzure ? 'block' : 'none';
    if(subscriptionIdField) subscriptionIdField.style.display = showAzure ? 'block' : 'none';
    if(resourceGroupField) resourceGroupField.style.display = showAzure ? 'block' : 'none';
    
    // Show/hide GCP fields
    const showGcp = provider === 'gcp';
    if(gcpJsonField) gcpJsonField.style.display = showGcp ? 'block' : 'none';
    if(projectIdField) projectIdField.style.display = showGcp ? 'block' : 'none';
    
    // Show/hide AWS/Azure credential fields
    const showCredentials = provider !== 'gcp';
    if(awsAwsField) awsAwsField.style.display = showCredentials ? 'block' : 'none';
    if(awsSecretField) awsSecretField.style.display = showCredentials ? 'block' : 'none';
    
    // Reset GCP data on provider change
    if(provider !== 'gcp'){
      gcpJsonData = null;
      if(gcpJsonFile) gcpJsonFile.value = '';
      if(gcpJsonPreview) gcpJsonPreview.style.display = 'none';
      if(projectIdEl) projectIdEl.value = '';
    }
  }

  // Handle GCP JSON file upload
  if(gcpJsonFile){
    gcpJsonFile.addEventListener('change', async function(e){
      const file = e.target.files[0];
      if(!file) return;
      
      try{
        const content = await file.text();
        gcpJsonData = JSON.parse(content);
        
        // Validate required fields
        if(!gcpJsonData.project_id || !gcpJsonData.private_key || !gcpJsonData.client_email){
          throw new Error('Invalid GCP service account JSON. Missing required fields.');
        }
        
        // Auto-fill project ID
        if(projectIdEl) projectIdEl.value = gcpJsonData.project_id;
        
        // Show preview
        if(gcpJsonPreview){
          gcpJsonPreview.textContent = `✓ Loaded: ${gcpJsonData.client_email}`;
          gcpJsonPreview.style.display = 'block';
        }
        
        console.log('GCP JSON loaded successfully:', gcpJsonData.project_id);
      } catch(err){
        alert('Error parsing GCP JSON: ' + err.message);
        gcpJsonData = null;
        if(gcpJsonFile) gcpJsonFile.value = '';
        if(gcpJsonPreview) gcpJsonPreview.style.display = 'none';
        if(projectIdEl) projectIdEl.value = '';
      }
    });
  }

  // Expose globally for clients.js to trigger after setting provider value
  window.toggleAzureModalFields = toggleProviderFields;

  if(providerSel){
    providerSel.addEventListener('change', toggleProviderFields);
    toggleProviderFields();
  }

  // Reset and show appropriate fields when modal opens
  if(modalEl){
    modalEl.addEventListener('show.bs.modal', function(){
      // Small delay to ensure provider value is set first (in case of edit)
      setTimeout(toggleProviderFields, 10);
    });
  }

  if(saveBtn){
    const newSave = saveBtn.cloneNode(true);
    saveBtn.parentNode.replaceChild(newSave, saveBtn);
    newSave.addEventListener('click', async function(){
      const name = (clientNameEl?.value || '').trim();
      const provider = providerSel?.value || '';
      
      if(!name){ alert('Client name is required'); return; }
      if(!provider){ alert('Provider is required'); return; }
      
      let metadata = { provider };
      
      if(provider === 'gcp'){
        // GCP provider
        if(!gcpJsonData){
          alert('GCP service account JSON file is required');
          return;
        }
        metadata.serviceAccountJson = JSON.stringify(gcpJsonData);
        metadata.projectId = gcpJsonData.project_id;
      } else if(provider === 'azure'){
        // Azure provider
        const tenantId = (tenantIdEl?.value || '').trim();
        const subscriptionId = (subscriptionIdEl?.value || '').trim();
        const resourceGroup = (resourceGroupEl?.value || '').trim();
        const clientId = (clientIdEl?.value || '').trim();
        const clientSecret = (clientSecretEl?.value || '').trim();
        
        if(!tenantId){ alert('Tenant ID is required for Azure'); return; }
        if(!subscriptionId){ alert('Subscription ID is required for Azure'); return; }
        if(!clientId || !clientSecret){ alert('Client ID and Secret are required'); return; }
        
        metadata.tenantId = tenantId;
        metadata.subscriptionId = subscriptionId;
        metadata.clientId = clientId;
        metadata.clientSecret = clientSecret;
        if(resourceGroup) metadata.resourceGroup = resourceGroup;
      } else {
        // AWS provider
        const clientId = (clientIdEl?.value || '').trim();
        const clientSecret = (clientSecretEl?.value || '').trim();
        
        if(!clientId || !clientSecret){ alert('Access Key and Secret Key are required'); return; }
        
        metadata.clientId = clientId;
        metadata.clientSecret = clientSecret;
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

