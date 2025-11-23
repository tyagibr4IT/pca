// Simple dashboard interactivity (demo)
document.addEventListener('DOMContentLoaded', () => {
  const signOut = document.getElementById('signOut');
  const welcomeText = document.getElementById('welcomeText');

  const token = localStorage.getItem('token');
  if(token){
    // demo: show token summary
    welcomeText.textContent = 'Signed in (demo) — token present.';
  } else {
    welcomeText.textContent = 'Not signed in (demo).';
  }

  signOut.addEventListener('click', () => {
    localStorage.removeItem('token');
    location.href = './login.html';
  });
});
