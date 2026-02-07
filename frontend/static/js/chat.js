(function(){
  /**
   * Chat WebSocket integration with client selection.
   * 
   * This module provides real-time chat functionality via WebSocket connection
   * to the backend API. Users must first select a client from the dropdown
   * before connecting to chat.
   * 
   * Features:
   * - Client dropdown selector (required before chat)
   * - WebSocket connection management
   * - Message history loading
   * - Duplicate message prevention
   * - Auto-reconnect capability
   * 
   * URL Parameters:
   *   id or idx: Optional client ID to auto-select
   * 
   * Usage: chat.html?id=<clientId>
   */

  const API_BASE = window.APP_CONFIG?.API_BASE || 'http://localhost:8000/api';
  const WS_BASE = window.APP_CONFIG?.WS_BASE || 'ws://localhost:8000/api';
  
  function getAuthHeaders(){
    const token = localStorage.getItem('token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  }

  function qs(key){
    const p = new URLSearchParams(location.search);
    return p.get(key);
  }

  /**
   * Show loading spinner overlay.
   * 
   * Displays a centered loading spinner with optional custom text.
   * Used during async operations like fetching clients, connecting WebSocket.
   * 
   * Args:
   *   text: Optional loading message (default: 'Loading...')
   * 
   * Example:
   *   showLoader('Connecting to chat...');
   */
  function showLoader(text = 'Loading...'){
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loaderText');
    if (loader) {
      loaderText.textContent = text;
      loader.classList.add('show');
    }
  }

  /**
   * Hide loading spinner overlay.
   * 
   * Removes the loading spinner from view after async operations complete.
   * 
   * Example:
   *   hideLoader();
   */
  function hideLoader(){
    const loader = document.getElementById('loader');
    if (loader) {
      loader.classList.remove('show');
    }
  }

  /**
   * Load all available clients from API.
   * 
   * Fetches the list of clients/tenants and populates the dropdown selector.
   * Shows loading spinner during fetch operation.
   * 
   * Returns:
   *   Array of client objects or empty array on error
   */
  async function loadClients(){
    showLoader('Loading clients...');
    try{
      const response = await fetch(`${API_BASE}/clients/`, { headers: getAuthHeaders() });
      if (response.status === 401) { 
        hideLoader();
        location.href = './login.html'; 
        return []; 
      }
      if (!response.ok) {
        hideLoader();
        return [];
      }
      const data = await response.json();
      hideLoader();
      return data;
    }catch(e){
      console.error('Error loading clients:', e);
      hideLoader();
      return [];
    }
  }

  /**
   * Load specific client details by ID.
   * 
   * Shows loading spinner during fetch operation.
   * 
   * Args:
   *   id: Client/tenant ID
   * 
   * Returns:
   *   Client object or null if not found
   */
  async function loadClient(id){
    showLoader('Loading client details...');
    try{
      const response = await fetch(`${API_BASE}/clients/${id}`, { headers: getAuthHeaders() });
      if (response.status === 401) { 
        hideLoader();
        location.href = './login.html'; 
        return null; 
      }
      if (!response.ok) {
        hideLoader();
        return null;
      }
      const data = await response.json();
      hideLoader();
      return data;
    }catch(e){
      hideLoader();
      return null;
    }
  }

  function formatTime(ts){
    const d = new Date(ts);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    
    if (isToday) {
      return d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }
    return d.toLocaleDateString([], {month: 'short', day: 'numeric'}) + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  }

  function getInitials(sender){
    if (sender === 'user') return 'U';
    if (sender === 'assistant') return 'AI';
    return sender.charAt(0).toUpperCase();
  }

  const chatWindow = document.getElementById('chatWindow');
  const chatForm = document.getElementById('chatForm');
  const chatInput = document.getElementById('chatInput');
  const wsStatus = document.getElementById('wsStatus');
  const connectBtn = document.getElementById('connectBtn');
  const disconnectBtn = document.getElementById('disconnectBtn');
  const clientSelector = document.getElementById('clientSelector');
  const clientNameDisplay = document.getElementById('clientNameDisplay');
  const sendBtn = document.getElementById('sendBtn');

  let clientId = qs('id') || qs('idx') || null;
  let client = null;
  let ws = null;
  const renderedMessages = new Set();  // Track rendered messages to prevent duplicates
  let allClients = [];
  let isProcessing = false;  // Track if system is processing a message
  let typingIndicatorElement = null;  // Reference to typing indicator in chat
  
  // Pagination variables
  let currentOffset = 0;
  let isLoadingMore = false;
  let hasMoreMessages = true;
  const PAGE_SIZE = 20;

  /**
   * Show inline typing indicator in chat window.
   * 
   * Displays animated dots in the chat window to indicate AI is processing.
   * Also disables input and updates send button state.
   */
  function showTypingIndicator(){
    if(typingIndicatorElement) return; // Already showing
    
    // Create wrapper with avatar
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper assistant';
    wrapper.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(indicator);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    
    typingIndicatorElement = wrapper;
    
    // Disable input and update button
    chatInput.disabled = true;
    chatInput.placeholder = 'Waiting for response...';
    sendBtn.disabled = true;
    sendBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" style="margin-right:4px">
      <path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41zm-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9z"/>
      <path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5.002 5.002 0 0 0 8 3zM3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9H3.1z"/>
    </svg>Sending...`;
  }

  /**
   * Hide inline typing indicator from chat window.
   * 
   * Removes the typing indicator and re-enables input controls.
   */
  function hideTypingIndicator(){
    if(typingIndicatorElement){
      typingIndicatorElement.remove();
      typingIndicatorElement = null;
    }
    
    // Re-enable input and restore button
    chatInput.disabled = false;
    chatInput.placeholder = 'Type your message here...';
    sendBtn.disabled = false;
    sendBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16" style="margin-right:4px">
      <path d="M15.854.146a.5.5 0 0 1 .11.54l-5.819 14.547a.75.75 0 0 1-1.329.124l-3.178-4.995L.643 7.184a.75.75 0 0 1 .124-1.33L15.314.037a.5.5 0 0 1 .54.11ZM6.636 10.07l2.761 4.338L14.13 2.576 6.636 10.07Zm6.787-8.201L1.591 6.602l4.339 2.76 7.494-7.493Z"/>
    </svg>Send`;
  }

  /**
   * Initialize page and populate client dropdown.
   * 
   * Loads all available clients into the dropdown selector.
   * If a client_id is present in URL, auto-selects that client
   * and initializes the chat connection.
   */
  async function init(){
    // Load current user info for navbar dropdown
    await window.loadCurrentUser();
    
    // Load all clients for dropdown
    allClients = await loadClients();
    
    // Populate dropdown
    clientSelector.innerHTML = '<option value="">-- Select a client --</option>';
    allClients.forEach(c => {
      const option = document.createElement('option');
      option.value = c.id;
      option.textContent = `${c.name}`;
      clientSelector.appendChild(option);
    });
    
    // If clientId from URL, auto-select and initialize
    if (clientId) {
      clientSelector.value = clientId;
      await onClientChange();
    } else {
      // No client selected - show message
      updateChatHeader(null);
      disableChat();
    }
  }

  /**
   * Handle client dropdown selection change.
   * 
   * When user selects a client:
   * 1. Updates clientId
   * 2. Updates URL with client_id parameter
   * 3. Loads client details
   * 4. Enables chat and auto-connects WebSocket
   */
  async function onClientChange(){
    const selectedId = clientSelector.value;
    
    if (!selectedId) {
      // No client selected - disable chat
      clientId = null;
      client = null;
      updateChatHeader(null);
      disableChat();
      disconnectWebSocket();
      chatWindow.innerHTML = '';
      return;
    }
    
    // Update clientId
    clientId = selectedId;
    
    // Update URL with client_id (without page reload)
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('id', clientId);
    window.history.pushState({}, '', newUrl);
    
    // Load client details
    client = await loadClient(clientId);
    
    // Update UI
    updateChatHeader(client);
    enableChat();
    
    // Clear old messages and connect to new client's chat
    chatWindow.innerHTML = '';
    renderedMessages.clear();
    currentOffset = 0;
    hasMoreMessages = true;
    disconnectWebSocket();
    connectWebSocket();
  }

  /**
   * Load more chat messages (pagination)
   */
  async function loadMoreMessages(){
    if (!clientId || isLoadingMore || !hasMoreMessages) return;
    
    isLoadingMore = true;
    const previousScrollHeight = chatWindow.scrollHeight;
    
    try {
      const response = await fetch(
        `${API_BASE}/chat/history/${clientId}?limit=${PAGE_SIZE}&offset=${currentOffset}`,
        { headers: getAuthHeaders() }
      );
      
      if (!response.ok) return;
      
      const data = await response.json();
      
      if (data.messages && data.messages.length > 0) {
        // Prepend messages to the beginning
        const fragment = document.createDocumentFragment();
        data.messages.forEach(msg => {
          const key = getMessageKey(msg);
          if (!renderedMessages.has(key)) {
            renderedMessages.add(key);
            const messageElement = createMessageElement(msg);
            fragment.appendChild(messageElement);
          }
        });
        
        chatWindow.insertBefore(fragment, chatWindow.firstChild);
        
        // Maintain scroll position
        chatWindow.scrollTop = chatWindow.scrollHeight - previousScrollHeight;
        
        currentOffset += data.messages.length;
        hasMoreMessages = data.messages.length === PAGE_SIZE;
      } else {
        hasMoreMessages = false;
      }
    } catch (error) {
      console.error('Error loading more messages:', error);
    } finally {
      isLoadingMore = false;
    }
  }
  
  /**
   * Create message element without adding to DOM
   */
  function createMessageElement(msg){
    const wrapper = document.createElement('div');
    wrapper.className = `message-wrapper ${msg.sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = getInitials(msg.sender);
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = msg.message;
    
    const time = document.createElement('div');
    time.className = 'message-time';
    time.textContent = formatTime(msg.timestamp || Date.now());
    
    content.appendChild(bubble);
    content.appendChild(time);
    wrapper.appendChild(avatar);
    wrapper.appendChild(content);
    
    return wrapper;
  }
  
  /**
   * Handle scroll to load more messages
   */
  function handleScroll(){
    // Only load more if we're near the top AND the chat has enough content to scroll
    if (chatWindow.scrollTop < 100 && hasMoreMessages && !isLoadingMore && chatWindow.scrollHeight > chatWindow.clientHeight) {
      loadMoreMessages();
    }
  }

  /**
   * Update chat header with client information.
   * 
   * Args:
   *   clientData: Client object or null if no client selected
   */
  function updateChatHeader(clientData){
    // Dropdown always stays visible so user can change clients anytime
    // Just update the display name next to it
    if (clientData) {
      clientNameDisplay.style.display = 'inline-block';
      clientNameDisplay.textContent = `→ ${clientData.name}`;
    } else {
      clientNameDisplay.style.display = 'none';
      clientNameDisplay.textContent = '';
    }
  }

  /**
   * Disable chat input when no client is selected.
   */
  function disableChat(){
    chatInput.disabled = true;
    chatInput.placeholder = 'Select a client to start chatting...';
    chatForm.querySelector('button[type="submit"]').disabled = true;
    connectBtn.disabled = true;
    disconnectBtn.disabled = true;
  }

  /**
   * Enable chat input when client is selected.
   */
  function enableChat(){
    chatInput.disabled = false;
    chatInput.placeholder = 'Type your message here...';
    chatForm.querySelector('button[type="submit"]').disabled = false;
    connectBtn.disabled = false;
    disconnectBtn.disabled = false;
  }

  function getMessageKey(msg){
    // Create unique key for message to prevent duplicates
    return `${msg.sender}|${msg.message}|${msg.timestamp}`;
  }

  function renderMessage(msg){
    try {
      console.log('renderMessage called with:', msg);
      const key = getMessageKey(msg);
      if(renderedMessages.has(key)){
        console.log('Skipping duplicate message:', key);
        return;  // Skip duplicate
      }
      renderedMessages.add(key);
      
      const messageElement = createMessageElement(msg);
      chatWindow.appendChild(messageElement);
      chatWindow.scrollTop = chatWindow.scrollHeight;
      console.log('Message rendered successfully');
    } catch (error) {
      console.error('Error rendering message:', error, msg);
    }
  }
  function setWsState(connected){
    if(connected){
      wsStatus.className = 'status-badge online';
      wsStatus.innerHTML = '<span class="status-dot status-online"></span>Connected';
      connectBtn.classList.add('d-none');
      disconnectBtn.classList.remove('d-none');
    } else {
      wsStatus.className = 'status-badge offline';
      wsStatus.innerHTML = '<span class="status-dot status-offline"></span>Disconnected';
      connectBtn.classList.remove('d-none');
      disconnectBtn.classList.add('d-none');
    }
  }

  /**
   * Connect to WebSocket for real-time chat.
   * 
   * Establishes WebSocket connection with backend chat API.
   * Shows loading spinner during connection process.
   * Requires clientId to be set (client must be selected).
   * 
   * Connection Flow:
   * 1. Validates clientId exists
   * 2. Creates WebSocket with token authentication
   * 3. Handles open, message, close, and error events
   * 4. Loads chat history on connection
   * 5. Renders incoming messages
   */
  function connectWebSocket(){
    // Validate client is selected
    if (!clientId) {
      console.warn('Cannot connect: No client selected');
      return;
    }
    
    showLoader('Connecting to chat...');
    const token = localStorage.getItem('token') || '';
    const url = `${WS_BASE}/chat/ws/${clientId}?token=${encodeURIComponent(token)}`;
    try{
      ws = new WebSocket(url);
      setWsState(false);
      
      // Set up ALL event listeners BEFORE the connection opens
      // This prevents race condition where history arrives before listener is attached
      ws.addEventListener('message', e=>{
        try {
          console.log('Raw WebSocket message received:', e.data);
          const data = JSON.parse(e.data);
          console.log('Parsed WebSocket message:', data.type, data);
          
          // Handle history load
          if(data.type === 'history'){
            console.log('Loading history with', data.messages?.length || 0, 'messages');
            
            if (!data.messages || !Array.isArray(data.messages)) {
              console.error('Invalid history data:', data);
              return;
            }
            
            renderedMessages.clear();  // Clear tracking when loading history
            chatWindow.innerHTML = '';  // Clear existing messages
            currentOffset = data.messages.length;  // Set offset for pagination
            hasMoreMessages = data.hasMore !== false;  // Check if more messages exist
            
            console.log('Chat window cleared, rendering messages...');
            data.messages.forEach((msg, index) => {
              console.log(`Rendering message ${index + 1}:`, msg);
              // Just render - let renderMessage handle the tracking
              renderMessage({
                message: msg.message,
                sender: msg.sender,
                timestamp: msg.timestamp || Date.now()
              });
            });
            console.log('History rendering complete. Chat window children:', chatWindow.children.length);
            console.log('Pagination state: offset=', currentOffset, 'hasMore=', hasMoreMessages);
            
            // Remove scroll listener temporarily to prevent triggering during initial scroll
            chatWindow.removeEventListener('scroll', handleScroll);
            
            // Scroll to bottom after loading history (use setTimeout to ensure DOM is updated)
            setTimeout(() => {
              chatWindow.scrollTop = chatWindow.scrollHeight;
              console.log('Scrolled to bottom. scrollTop:', chatWindow.scrollTop, 'scrollHeight:', chatWindow.scrollHeight);
              
              // Add scroll listener AFTER scrolling completes (with additional delay)
              setTimeout(() => {
                chatWindow.addEventListener('scroll', handleScroll);
                console.log('Scroll listener attached. Ready for pagination.');
              }, 200);
            }, 100);
            
            return;
          }
        
        // Handle regular message
        if(data.type === 'message'){
          // Render the message first
          renderMessage({
            message: data.message,
            sender: data.sender,
            timestamp: data.timestamp || Date.now()
          });
          
          // If this is a user message and we're waiting for AI response, show typing indicator
          if(data.sender === 'user' && isProcessing){
            showTypingIndicator();
          }
          
          // Hide typing indicator if system/assistant is responding
          if(data.sender === 'assistant' || data.sender === 'system'){
            isProcessing = false;
            hideTypingIndicator();
          }
        }
        } catch (error) {
          console.error('Error handling WebSocket message:', error, e.data);
        }
      });
      
      ws.addEventListener('open', ()=>{
        setWsState(true);
        hideLoader();
        console.log('WebSocket connected');
      });
      
      ws.addEventListener('close', ()=>{
        setWsState(false);
        ws=null;
        hideLoader();
        console.log('WebSocket disconnected');
      });
      
      ws.addEventListener('error', (err)=>{
        setWsState(false);
        hideLoader();
        console.error('WebSocket error:', err);
      });
    }catch(err){
      setWsState(false);
      ws=null;
      hideLoader();
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

  // Wire client selector
  clientSelector.addEventListener('change', onClientChange);

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
      // Set processing flag - typing indicator will show after user message is rendered
      isProcessing = true;
      
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
