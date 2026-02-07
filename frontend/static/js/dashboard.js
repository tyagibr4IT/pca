// Dashboard quick stats and user info
const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize permissions first
  if (window.PermissionManager) {
    await window.PermissionManager.initializePermissions();
  }
  
  const signOut = document.getElementById('signOut');
  const welcomeText = document.getElementById('welcomeText');

  // Use global loadCurrentUser from common.js
  const user = await window.loadCurrentUser();
  if(user){
    welcomeText.textContent = `Welcome, ${user.username}!`;
    
    // Hide admin-only elements if not admin
    if(user.role !== 'admin'){
      document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }
  } else {
    welcomeText.textContent = 'Not signed in.';
  }

  signOut.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    location.href = './login.html';
  });
});
