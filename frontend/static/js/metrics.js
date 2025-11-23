// Simple metrics page script — reads client index from query and renders placeholder metrics
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const idx = params.has('idx') ? Number(params.get('idx')) : null;
  const title = document.getElementById('metricsTitle');
  const sub = document.getElementById('metricsSub');
  const clientInfo = document.getElementById('clientInfo');
  const metricsContent = document.getElementById('metricsContent');
  const metricsTable = document.getElementById('metricsTable');

  function loadClients(){
    try{
      return JSON.parse(localStorage.getItem('clients')||'[]');
    }catch(e){return []}
  }

  const clients = loadClients();
  const client = (idx !== null && clients[idx]) ? clients[idx] : null;

  if(!client){
    title.innerText = 'Metrics';
    sub.innerText = 'Client not found — go back to the clients list.';
    clientInfo.innerHTML = '<p class="text-muted">No client selected or client index invalid.</p>';
    return;
  }

  // Wire the chat button (if present) to open chat for this client
  const chatBtn = document.getElementById('openChatBtn');
  if(chatBtn){
    chatBtn.href = `./chat.html?idx=${idx}`;
  }

  title.innerText = `Metrics — ${client.name}`;
  sub.innerText = `Provider: ${client.provider.toUpperCase()} • Client ID: ${client.clientId}`;

  clientInfo.innerHTML = `
    <p><strong>Name:</strong> ${client.name}</p>
    <p><strong>Provider:</strong> ${client.provider.toUpperCase()}</p>
    <p><strong>Client ID:</strong> ${client.clientId}</p>
  `;

  metricsContent.innerHTML = '<p class="text-muted">Showing last 20 sample metric points.</p>';

  // generate 20 sample metric rows (timestamps + mixed metric values)
  const now = Date.now();
  const rows = [];
  const metricTypes = ['cpu','memory','errors','network','storage'];
  for(let i=0;i<20;i++){
    const ts = new Date(now - (19-i)*60000); // minutes
    const type = metricTypes[i % metricTypes.length];
    let value;
    switch(type){
      case 'cpu':
        value = (Math.random()*70 + 10).toFixed(1) + '%';
        break;
      case 'memory':
        value = Math.floor(Math.random()*4096 + 256) + ' MB';
        break;
      case 'errors':
        value = Math.floor(Math.random()*5) + ' /min';
        break;
      case 'network':
        value = Math.floor(Math.random()*900 + 10) + ' Mbps';
        break;
      case 'storage':
        value = Math.floor(Math.random()*8000 + 50) + ' GB';
        break;
      default:
        value = (Math.random()*100).toFixed(2);
    }
    rows.push({ts: ts.toLocaleString(), metric: `sample.${type}`, value});
  }

  metricsTable.innerHTML = rows.map(r => `
    <tr>
      <td>${r.ts}</td>
      <td>${r.metric}</td>
      <td>${r.value}</td>
    </tr>
  `).join('');

  // populate quick panels with sample aggregates (set both top and grid panels)
  const cpuEl = document.getElementById('metricCpu');
  const memEl = document.getElementById('metricMem');
  const errEl = document.getElementById('metricErr');
  const cpuTopEl = document.getElementById('metricCpuTop');
  const memTopEl = document.getElementById('metricMemTop');
  const errTopEl = document.getElementById('metricErrTop');
  const vmsEl = document.getElementById('metricVMs');
  const dbEl = document.getElementById('metricDBs');
  const storageEl = document.getElementById('metricStorage');
  const netEl = document.getElementById('metricNet');
  const alertsEl = document.getElementById('metricAlerts');

  const cpuVal = (Math.random() * 80 + 10).toFixed(1) + '%';
  const memVal = Math.floor(Math.random() * 4096 + 256) + ' MB';
  const errVal = String(Math.floor(Math.random() * 5)) + ' /min';
  const vmsVal = String(Math.floor(Math.random() * 200 + 1));
  const dbVal = String(Math.floor(Math.random() * 20 + 0));
  const storageVal = Math.floor(Math.random() * 8000 + 50) + ' GB';
  const netVal = String(Math.floor(Math.random() * 1000 + 10)) + ' Mbps';
  const alertsVal = String(Math.floor(Math.random() * 8));

  if (cpuEl) cpuEl.innerText = cpuVal;
  if (cpuTopEl) cpuTopEl.innerText = cpuVal;
  if (memEl) memEl.innerText = memVal;
  if (memTopEl) memTopEl.innerText = memVal;
  if (errEl) errEl.innerText = errVal;
  if (errTopEl) errTopEl.innerText = errVal;
  if (vmsEl) vmsEl.innerText = vmsVal;
  if (dbEl) dbEl.innerText = dbVal;
  if (storageEl) storageEl.innerText = storageVal;
  if (netEl) netEl.innerText = netVal;
  if (alertsEl) alertsEl.innerText = alertsVal;

  // render small sparklines in the cards using Chart.js (if available)
  function makeSparkline(canvasId, values, color){
    const c = document.getElementById(canvasId);
    if(!c || typeof Chart === 'undefined') return null;
    // ensure a fixed height for small sparkline
    c.width = 140; c.height = 40;
    const ctx = c.getContext('2d');
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: values.map((_,i)=>i+1),
        datasets: [{
          data: values,
          borderColor: color || '#4dc9f6',
          backgroundColor: 'rgba(0,0,0,0)',
          fill: false,
          tension: 0.3,
          pointRadius: 0
        }]
      },
      options: {
        responsive: false,
        maintainAspectRatio: false,
        plugins: {legend:{display:false}},
        scales: {
          x: {display:false},
          y: {display:false}
        },
        elements: {line:{borderWidth:2}}
      }
    });
  }

  // generate sparkline data arrays for different metric types
  function sampleArray(len, min, max, round){
    const a = [];
    for(let i=0;i<len;i++){
      const v = Math.random()*(max-min)+min;
      a.push(round?Math.round(v):parseFloat(v.toFixed(1)));
    }
    return a;
  }

  // draw charts for each metric card if chart canvas exists
  makeSparkline('chartCpu', sampleArray(12,10,90,false),'#f97066');
  makeSparkline('chartMem', sampleArray(12,200,4096,true),'#6be5b4');
  makeSparkline('chartErr', sampleArray(12,0,6,true),'#ffd166');
  makeSparkline('chartVMs', sampleArray(12,1,200,true),'#9ab2ff');
  makeSparkline('chartDBs', sampleArray(12,0,20,true),'#b49cff');
  makeSparkline('chartStorage', sampleArray(12,10,8000,true),'#ffb3c6');
  makeSparkline('chartNet', sampleArray(12,5,1000,true),'#6dcff6');
  makeSparkline('chartAlerts', sampleArray(12,0,12,true),'#ff9f43');
});
