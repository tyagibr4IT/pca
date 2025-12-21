// Common frontend helpers (sign out handler)
document.addEventListener('DOMContentLoaded', () => {
  // Simple session guard: only allow login page without token
  try {
    const path = (location.pathname || '').toLowerCase();
    const isLoginPage = /\/login(\.html)?\/?$/.test(path);
    const token = localStorage.getItem('token');
    if (!isLoginPage && !token) {
      // Not on login and no session -> redirect
      window.location.href = './login.html';
      return;
    }
    // If on login page but already logged in, optionally go to clients
    if (isLoginPage && token) {
      // quick sanity check by calling /auth/me; ignore failures
      fetch('http://localhost:8000/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      }).then(r => {
        if (r.ok) {
          window.location.href = './clients.html';
        }
      }).catch(()=>{});
    }
  } catch (_) { /* ignore */ }
  function signOut(e){
    e && e.preventDefault();
    try{ localStorage.removeItem('token'); }catch(e){}
    // redirect to login
    window.location.href = './login.html';
  }

  // attach to sidebar signout links
  document.querySelectorAll('.sidebar-signout').forEach(el => el.addEventListener('click', signOut));

  // attach to any element with id 'signOut' (existing navbar button)
  const btn = document.getElementById('signOut');
  if(btn) btn.addEventListener('click', signOut);

  // Auto-refresh access token before expiry (simple interval)
  const API_BASE = 'http://localhost:8000/api';
  const REFRESH_INTERVAL_MS = 12 * 60 * 1000; // refresh every 12 minutes
  function scheduleRefresh(){
    const token = localStorage.getItem('token');
    if(!token) return; // no token, skip
    setInterval(async () => {
      const current = localStorage.getItem('token');
      if(!current) return;
      try{
        const resp = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: current })
        });
        if(resp.status === 401){
          // token invalid/expired, redirect to login
          signOut();
          return;
        }
        if(resp.ok){
          const data = await resp.json();
          if(data && data.access_token){
            localStorage.setItem('token', data.access_token);
          }
        }
      }catch(err){
        console.error('Token refresh failed:', err);
      }
    }, REFRESH_INTERVAL_MS);
  }

  scheduleRefresh();
});
