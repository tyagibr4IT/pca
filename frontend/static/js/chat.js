(function(){
  // chat.js — WebSocket-based real-time chat integrated with backend API
  // Usage: chat.html?id=<clientId>

  const API_BASE = 'http://localhost:8000/api';
  function getAuthHeaders(){
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }
  const WS_BASE = 'ws://localhost:8000/api';

  function qs(key){
    const p = new URLSearchParams(location.search);
    return p.get(key);
  }

  async function loadClient(id){
    try{
      const response = await fetch(`${API_BASE}/clients/${id}`, { headers: getAuthHeaders() });
      if (response.status === 401) { location.href = './login.html'; return null; }
      if (!response.ok) return null;
      return await response.json();
    }catch(e){return null}
  }

  function formatTime(ts){const d=new Date(ts);return d.toLocaleTimeString();}

  const chatWindow = document.getElementById('chatWindow');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const chatTitle = document.getElementById('chatTitle');
  const chatSub = document.getElementById('chatSub');
  const wsStatus = document.getElementById('wsStatus');
  const connectBtn = document.getElementById('connectBtn');
  const disconnectBtn = document.getElementById('disconnectBtn');

  const clientId = qs('id') || qs('idx') || '1';
  let client = null;
  let ws = null;
  const renderedMessages = new Set();  // Track rendered messages to prevent duplicates

  async function init(){
    client = await loadClient(clientId);
    const clientLabel = client ? client.name : `Client ${clientId}`;
    
    chatTitle.textContent = `Chat — ${clientLabel}`;
    chatSub.textContent = client ? `Client: ${clientLabel}` : `Client ID: ${clientId}`;

    // Auto-connect to WebSocket
    connectWebSocket();
  }

  function getMessageKey(msg){
    // Create unique key for message to prevent duplicates
    return `${msg.sender}|${msg.message}|${msg.timestamp}`;
  }

  function renderMessage(msg){
    const key = getMessageKey(msg);
    if(renderedMessages.has(key)){
      return;  // Skip duplicate
    }
    renderedMessages.add(key);
    
    const el = document.createElement('div');
    el.className = msg.sender === 'user' ? 'text-end' : 'text-start';
    const b = document.createElement('div');
    b.className = msg.sender === 'user' ? 'msg-out' : 'msg-in';
    b.textContent = msg.message;
    const t = document.createElement('div');
    t.className = 'text-muted small mt-1';
    t.textContent = formatTime(msg.timestamp || Date.now());
    el.appendChild(b);
    el.appendChild(t);
    chatWindow.appendChild(el);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
  function setWsState(connected){
    const dot = wsStatus.querySelector('.status-dot');
    if(connected){
      wsStatus.innerHTML = '<span class="status-dot status-online"></span> connected';
      connectBtn.classList.add('d-none');
      disconnectBtn.classList.remove('d-none');
    } else {
      wsStatus.innerHTML = '<span class="status-dot status-offline"></span> disconnected';
      connectBtn.classList.remove('d-none');
      disconnectBtn.classList.add('d-none');
    }
  }

  function connectWebSocket(){
    const token = localStorage.getItem('token') || '';
    const url = `${WS_BASE}/chat/ws/${clientId}?token=${encodeURIComponent(token)}`;
    try{
      ws = new WebSocket(url);
      setWsState(false);
      
      ws.addEventListener('open', ()=>{
        setWsState(true);
        console.log('WebSocket connected');
      });
      
      ws.addEventListener('message', e=>{
        const data = JSON.parse(e.data);
        
        // Handle history load
        if(data.type === 'history'){
          renderedMessages.clear();  // Clear tracking when loading history
          chatWindow.innerHTML = '';  // Clear existing messages
          data.messages.forEach(msg => {
            const key = getMessageKey({
              message: msg.message,
              sender: msg.sender,
              timestamp: msg.timestamp
            });
            renderedMessages.add(key);  // Track historical messages
            renderMessage({
              message: msg.message,
              sender: msg.sender,
              timestamp: msg.timestamp || Date.now()
            });
          });
          return;
        }
        
        // Handle regular message
        if(data.type === 'message'){
          renderMessage({
            message: data.message,
            sender: data.sender,
            timestamp: data.timestamp || Date.now()
          });
        }
      });
      
      ws.addEventListener('close', ()=>{
        setWsState(false);
        ws=null;
        console.log('WebSocket disconnected');
      });
      
      ws.addEventListener('error', (err)=>{
        setWsState(false);
        console.error('WebSocket error:', err);
      });
    }catch(err){
      setWsState(false);
      ws=null;
      console.error('Failed to connect WebSocket:', err);
    }
  }

  function disconnectWebSocket(){
    if(ws){
      ws.close();
      ws=null;
    }
    setWsState(false);
  }

  // wire buttons
  connectBtn.addEventListener('click', ()=>{
    connectWebSocket();
  });
  
  disconnectBtn.addEventListener('click', ()=>{
    disconnectWebSocket();
  });

  // send messages
  chatForm.addEventListener('submit', (ev)=>{
    ev.preventDefault();
    const text = chatInput.value.trim();
    if(!text) return;
    
    chatInput.value = '';
    
    // if ws connected, send to backend (backend will echo back)
    if(ws && ws.readyState===WebSocket.OPEN){
      ws.send(JSON.stringify({
        message: text,
        sender: 'user',
        timestamp: new Date().toISOString()
      }));
    } else {
      // Fallback: render locally if not connected
      renderMessage({
        message: text,
        sender: 'user',
        timestamp: Date.now()
      });
    }
  });

  // initialize
  init();

})();
