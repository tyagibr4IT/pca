// Dashboard quick stats and user info
const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';

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
  const signOut = document.getElementById('signOut');
  const welcomeText = document.getElementById('welcomeText');

  const user = await loadCurrentUser();
  if(user){
    // Populate navbar dropdown
    document.getElementById('navUsername').textContent = user.username || 'User';
    document.getElementById('dropdownUsername').textContent = user.username || 'User';
    document.getElementById('dropdownRole').textContent = `Role: ${user.role || 'member'}`;
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
