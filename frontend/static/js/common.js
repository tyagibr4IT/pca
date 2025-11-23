// Common frontend helpers (sign out handler)
document.addEventListener('DOMContentLoaded', () => {
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
});
