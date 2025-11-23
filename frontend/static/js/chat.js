(function(){
  // chat.js — lightweight client-side chat with optional WebSocket support
  // Usage: chat.html?idx=<clientIndex>&ws=<ws_url>

  function qs(key){
    const p = new URLSearchParams(location.search);
    return p.get(key);
  }

  function loadClients(){
    try{const s=localStorage.getItem('clients');return s?JSON.parse(s):[]}catch(e){return []}
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

  const idx = parseInt(qs('idx')||'0',10);
  const wsUrl = qs('ws');

  const clients = loadClients();
  const client = clients[idx] || (clients.length?clients[0]:null);
  const clientLabel = client? (client.name || client.id || `client-${idx}`) : 'Unknown client';

  chatTitle.textContent = `Chat — ${clientLabel}`;
  chatSub.textContent = client? `Client: ${clientLabel}` : 'No client found in localStorage';

  const chatKey = client? `chat_${client.id||idx}` : `chat_orphan`;

  function loadMessages(){
    try{const s=localStorage.getItem(chatKey);return s?JSON.parse(s):[]}catch(e){return []}
  }
  function saveMessages(msgs){localStorage.setItem(chatKey, JSON.stringify(msgs));}

  function renderMessages(){
    const msgs = loadMessages();
    chatWindow.innerHTML = '';
    msgs.forEach(m=>{
      const el = document.createElement('div');
      el.className = m.dir === 'out' ? 'text-end' : 'text-start';
      const b = document.createElement('div');
      b.className = m.dir === 'out' ? 'msg-out' : 'msg-in';
      b.textContent = m.text;
      const t = document.createElement('div');
      t.className = 'text-muted small mt-1';
      t.textContent = formatTime(m.ts);
      el.appendChild(b);
      el.appendChild(t);
      chatWindow.appendChild(el);
    });
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  // Synthetic realtime simulation (used when no ws URL provided)
  let simTimer = null;
  function startSimulation(){
    if(simTimer) return;
    simTimer = setInterval(()=>{
      const msgs = loadMessages();
      const sample = [
        'Heartbeat OK',
        'CPU spike observed',
        'New alert: high latency',
        'Sync complete',
        'Provisioning finished',
        'Disk pressure > 80%'
      ];
      const text = sample[Math.floor(Math.random()*sample.length)];
      msgs.push({dir:'in', text: `[${clientLabel}] ${text}`, ts: Date.now()});
      saveMessages(msgs);
      renderMessages();
    }, 7000 + Math.floor(Math.random()*6000));
  }
  function stopSimulation(){ if(simTimer){clearInterval(simTimer); simTimer=null;} }

  // WebSocket support
  let socket = null;
  function setWsState(connected){
    const dot = wsStatus.querySelector('.status-dot');
    if(connected){wsStatus.innerHTML = '<span class="status-dot status-online"></span> connected'; connectBtn.classList.add('d-none'); disconnectBtn.classList.remove('d-none');}
    else {wsStatus.innerHTML = '<span class="status-dot status-offline"></span> disconnected'; connectBtn.classList.remove('d-none'); disconnectBtn.classList.add('d-none');}
  }

  function connectWebSocket(url){
    try{
      socket = new WebSocket(url);
      setWsState(false);
      socket.addEventListener('open', ()=>{ setWsState(true); stopSimulation(); });
      socket.addEventListener('message', e=>{
        const msgs = loadMessages();
        msgs.push({dir:'in', text: e.data, ts: Date.now()});
        saveMessages(msgs);
        renderMessages();
      });
      socket.addEventListener('close', ()=>{ setWsState(false); socket=null; startSimulation(); });
      socket.addEventListener('error', ()=>{ setWsState(false); });
    }catch(err){ setWsState(false); socket=null; startSimulation(); }
  }
  function disconnectWebSocket(){ if(socket){socket.close(); socket=null;} setWsState(false); startSimulation(); }

  // wire buttons
  connectBtn.addEventListener('click', ()=>{
    if(wsUrl){ connectWebSocket(wsUrl); } else { startSimulation(); setWsState(false); connectBtn.classList.add('d-none'); disconnectBtn.classList.remove('d-none'); }
  });
  disconnectBtn.addEventListener('click', ()=>{ disconnectWebSocket(); });

  // send messages
  chatForm.addEventListener('submit', (ev)=>{
    ev.preventDefault();
    const text = chatInput.value.trim();
    if(!text) return;
    const msgs = loadMessages();
    msgs.push({dir:'out', text:text, ts:Date.now()});
    saveMessages(msgs);
    renderMessages();
    chatInput.value = '';
    // if ws connected, forward
    if(socket && socket.readyState===WebSocket.OPEN){
      socket.send(text);
    }
  });

  // initialize
  renderMessages();
  if(wsUrl){ connectWebSocket(wsUrl); } else { startSimulation(); }

  // respond to external updates (other tabs) — keep chat in sync
  window.addEventListener('storage', (e)=>{
    if(e.key === chatKey || e.key === 'clients'){
      renderMessages();
    }
  });

})();
