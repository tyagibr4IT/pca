// clients-modal.js
// Handles Add Client modal on dashboard (stores to localStorage for demo)
document.addEventListener('DOMContentLoaded', () => {
  const modalEl = document.getElementById('clientModal');
  if(!modalEl) return; // nothing to do

  const provider = document.getElementById('modalProvider');
  const clientName = document.getElementById('modalClientName');
  const clientId = document.getElementById('modalClientId');
  const clientSecret = document.getElementById('modalClientSecret');
  const saveBtn = document.getElementById('modalSaveClient');
  const testBtn = document.getElementById('modalTestConn');

  const bsModal = new bootstrap.Modal(modalEl);

  function loadClients(){
    try{ return JSON.parse(localStorage.getItem('clients')||'[]') }catch(e){return []}
  }
  function saveClients(list){ localStorage.setItem('clients', JSON.stringify(list)) }

  function resetForm(){ provider.value='aws'; clientName.value=''; clientId.value=''; clientSecret.value=''; }

  saveBtn.addEventListener('click', () => {
    if(!clientName.value.trim()){
      alert('Please provide a name for the client.');
      return;
    }
    const list = loadClients();
    list.push({ provider: provider.value, name: clientName.value.trim(), clientId: clientId.value.trim(), clientSecret: clientSecret.value.trim() });
    saveClients(list);
    bsModal.hide();
    resetForm();
    // if on clients page, try to re-render table by dispatching an event
    window.dispatchEvent(new Event('clients-updated'));
  });

  testBtn.addEventListener('click', () => {
    const old = testBtn.innerHTML;
    testBtn.disabled = true;
    testBtn.innerHTML = 'Testing...';
    setTimeout(() => { testBtn.disabled = false; testBtn.innerHTML = old; alert('Connection appears valid (demo)'); }, 700);
  });

  // Clear form when modal hidden
  modalEl.addEventListener('hidden.bs.modal', resetForm);
});
