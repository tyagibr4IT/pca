/**
 * Frontend configuration for API endpoints.
 * 
 * Automatically detects environment and sets appropriate API base URLs.
 * 
 * Environment Detection:
 *   - localhost/127.0.0.1: Development mode (localhost:8000)
 *   - Azure/Production: Uses relative paths or window.location.origin
 * 
 * Usage:
 *   Import at top of HTML before other scripts:
 *   <script src="./js/config.js"></script>
 * 
 * Access in other scripts:
 *   window.APP_CONFIG.API_BASE
 *   window.APP_CONFIG.WS_BASE
 */

(function() {
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  const isLocal = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '';
  
  let apiBase, wsBase;
  
  if (isLocal) {
    // Local development - use localhost:8001
    apiBase = 'http://localhost:8001/api';
    wsBase = 'ws://localhost:8001/api';
  } else {
    // Production/Azure - use current origin or relative path
    const origin = window.location.origin;
    apiBase = `${origin}/api`;
    wsBase = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${hostname}/api`;
  }
  
  // Global configuration object
  window.APP_CONFIG = {
    API_BASE: apiBase,
    WS_BASE: wsBase,
    isLocal: isLocal
  };
  
  console.log('APP_CONFIG initialized:', window.APP_CONFIG);
})();
