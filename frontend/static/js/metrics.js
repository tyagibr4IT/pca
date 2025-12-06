// Metrics page script — fetches real-time cloud metrics from backend API
const API_BASE = 'http://localhost:8000/api';

function getToken(){
  try { return localStorage.getItem('token'); } catch(e){ return null; }
}

function getAuthHeaders(){
  const token = getToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
}

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const clientId = params.has('id') ? Number(params.get('id')) : null;
  const title = document.getElementById('metricsTitle');
  const sub = document.getElementById('metricsSub');
  const clientInfo = document.getElementById('clientInfo');
  const metricsContent = document.getElementById('metricsContent');
  const metricsTable = document.getElementById('metricsTable');

  if(!clientId){
    title.innerText = 'Metrics';
    sub.innerText = 'No client selected — go back to the clients list.';
    clientInfo.innerHTML = '<p class=\"text-muted\">Please select a client to view metrics.</p>';
    return;
  }

  // Wire the chat button to open chat for this client
  const chatBtn = document.getElementById('openChatBtn');
  if(chatBtn){
    chatBtn.href = `./chat.html?id=${clientId}`;
  }

  try {
    // Fetch client details
    const clientRes = await fetch(`${API_BASE}/clients/${clientId}`, { headers: getAuthHeaders() });
    if(!clientRes.ok) throw new Error('Failed to load client');
    const client = await clientRes.json();

    title.innerText = `Metrics — ${client.name}`;
    const provider = (client.metadata_json?.provider || 'unknown').toUpperCase();
    sub.innerText = `Provider: ${provider}`;

    clientInfo.innerHTML = `
      <div class=\"alert alert-info\">
        <strong>${client.name}</strong> (${provider})
      </div>
    `;

    // Fetch resource inventory
    const resourcesRes = await fetch(`${API_BASE}/metrics/resources/${clientId}`, { headers: getAuthHeaders() });
    if(!resourcesRes.ok) throw new Error(`Resources API error: ${resourcesRes.status}`);
    const resources = await resourcesRes.json();

    // Fetch cost analysis
    const costsRes = await fetch(`${API_BASE}/metrics/costs/${clientId}`, { headers: getAuthHeaders() });
    if(!costsRes.ok) throw new Error(`Costs API error: ${costsRes.status}`);
    const costs = await costsRes.json();

    // Fetch recommendations
    const recsRes = await fetch(`${API_BASE}/metrics/recommendations/${clientId}`, { headers: getAuthHeaders() });
    if(!recsRes.ok) throw new Error(`Recommendations API error: ${recsRes.status}`);
    const recs = await recsRes.json();

    // Fetch current metrics
    const metricsRes = await fetch(`${API_BASE}/metrics/current?client_id=${clientId}`, { headers: getAuthHeaders() });
    if(!metricsRes.ok) throw new Error(`Current metrics API error: ${metricsRes.status}`);
    const currentMetrics = await metricsRes.json();

    // Update summary cards
    document.getElementById('metricVMs').innerText = resources.summary?.total_vms || 0;
    document.getElementById('metricDBs').innerText = resources.summary?.total_databases || 0;
    document.getElementById('metricStorage').innerText = resources.summary?.total_storage_buckets || 0;
    
    // Cost display
    document.getElementById('metricCpuTop').innerText = `$${costs.costs_usd?.compute || 0}`;
    document.getElementById('metricMemTop').innerText = `$${costs.costs_usd?.storage || 0}`;
    document.getElementById('metricErrTop').innerText = `$${costs.costs_usd?.total || 0}`;
    
    document.getElementById('metricCpu').innerText = `$${costs.costs_usd?.compute || 0}`;
    document.getElementById('metricMem').innerText = `$${costs.costs_usd?.storage || 0}`;
    document.getElementById('metricErr').innerText = `$${costs.costs_usd?.network || 0}`;
    document.getElementById('metricNet').innerText = `$${costs.costs_usd?.database || 0}`;
    document.getElementById('metricAlerts').innerText = recs.summary?.high_severity || 0;

    // Display resource inventory
    const resourcesError = resources.error ? `<div class=\"alert alert-warning\">Azure fetch note: ${resources.error}</div>` : '';
    metricsContent.innerHTML = `
      <div class=\"row g-3 mb-3\">
        <div class=\"col-md-6\">
          <div class=\"card card-dark p-3\">
            <h6 class=\"mb-2\">Virtual Machines (${resources.summary?.total_vms || 0})</h6>
            ${resourcesError}
            ${resources.resources?.vms?.length > 0 ? `
              <ul class=\"list-unstyled small mb-0\">
                ${resources.resources.vms.map(vm => `
                  <li>• ${vm.id} - ${vm.type || vm.size} (${vm.state})</li>
                `).join('')}
              </ul>
            ` : '<p class=\"text-muted small mb-0\">No VMs found</p>'}
          </div>
        </div>
        <div class=\"col-md-6\">
          <div class=\"card card-dark p-3\">
            <h6 class=\"mb-2\">Databases (${resources.summary?.total_databases || 0})</h6>
            ${resources.resources?.databases?.length > 0 ? `
              <ul class=\"list-unstyled small mb-0\">
                ${resources.resources.databases.map(db => `
                  <li>• ${db.id} - ${db.engine || 'N/A'} (${db.size || db.storage_gb + 'GB'})</li>
                `).join('')}
              </ul>
            ` : '<p class=\"text-muted small mb-0\">No databases found</p>'}
          </div>
        </div>
      </div>
      <div class=\"row g-3 mb-3\">
        <div class=\"col-12\">
          <div class=\"card card-dark p-3\">
            <h6 class=\"mb-2\">Storage (${resources.summary?.total_storage_buckets || 0} buckets/accounts)</h6>
            ${resources.resources?.storage?.length > 0 ? `
              <ul class=\"list-unstyled small mb-0\">
                ${resources.resources.storage.map(s => `
                  <li>• ${s.bucket || s.account} - ${s.size_gb} GB</li>
                `).join('')}
              </ul>
            ` : '<p class=\"text-muted small mb-0\">No storage found</p>'}
          </div>
        </div>
      </div>
      <div class=\"row g-3 mb-3\">
        <div class=\"col-12\">
          <div class=\"card card-dark p-3\">
            <h6 class=\"mb-2\">💰 Cost Breakdown (${costs.period_days || 30} days)</h6>
            <table class=\"table table-sm table-dark mb-0\">
              <tr><td>Compute</td><td class=\"text-end\">$${costs.costs_usd?.compute || 0}</td></tr>
              <tr><td>Storage</td><td class=\"text-end\">$${costs.costs_usd?.storage || 0}</td></tr>
              <tr><td>Network</td><td class=\"text-end\">$${costs.costs_usd?.network || 0}</td></tr>
              <tr><td>Database</td><td class=\"text-end\">$${costs.costs_usd?.database || 0}</td></tr>
              <tr class=\"fw-bold\"><td>Total</td><td class=\"text-end\">$${costs.costs_usd?.total || 0}</td></tr>
              <tr class=\"text-info\"><td>Projected Monthly</td><td class=\"text-end\">$${costs.projected_monthly || 0}</td></tr>
            </table>
          </div>
        </div>
      </div>
      <div class=\"row g-3\">
        <div class=\"col-12\">
          <div class=\"card card-dark p-3\">
            <h6 class=\"mb-2\">💡 Recommendations (${recs.summary?.total_recommendations || 0})</h6>
            <div class=\"alert alert-warning small mb-2\">
              Potential monthly savings: <strong>$${recs.summary?.total_potential_savings_monthly || 0}</strong>
            </div>
            ${recs.recommendations?.length > 0 ? recs.recommendations.map(rec => `
              <div class=\"alert alert-${rec.severity === 'high' ? 'danger' : rec.severity === 'medium' ? 'warning' : 'info'} small mb-2\">
                <strong>${rec.title}</strong><br>
                ${rec.description}<br>
                <em>Action: ${rec.action}</em>
                ${rec.estimated_savings_monthly > 0 ? `<br><span class=\"badge bg-success\">Save $${rec.estimated_savings_monthly}/mo</span>` : ''}
              </div>
            `).join('') : '<p class=\"text-muted small\">No recommendations available</p>'}
          </div>
        </div>
      </div>
    `;

    // Display current metrics table
    if(currentMetrics.items?.length > 0){
      metricsTable.innerHTML = currentMetrics.items.map(m => `
        <tr>
          <td>${m.updated_at || 'N/A'}</td>
          <td>${m.provider}.${m.resource_type}</td>
          <td>${JSON.stringify(m.data)}</td>
        </tr>
      `).join('');
    } else {
      metricsTable.innerHTML = '<tr><td colspan=\"3\" class=\"text-muted text-center\">No metrics data available</td></tr>';
    }

    // Generate sparklines with sample data (can be replaced with real historical data)
    function makeSparkline(canvasId, values, color){
      const c = document.getElementById(canvasId);
      if(!c || typeof Chart === 'undefined') return null;
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

    function sampleArray(len, min, max, round){
      const a = [];
      for(let i=0;i<len;i++){
        const v = Math.random()*(max-min)+min;
        a.push(round?Math.round(v):parseFloat(v.toFixed(1)));
      }
      return a;
    }

    // Draw sparklines (using sample data for now - can fetch historical later)
    makeSparkline('chartCpu', sampleArray(12,10,90,false),'#f97066');
    makeSparkline('chartMem', sampleArray(12,200,4096,true),'#6be5b4');
    makeSparkline('chartErr', sampleArray(12,0,6,true),'#ffd166');
    makeSparkline('chartVMs', sampleArray(12,1,200,true),'#9ab2ff');
    makeSparkline('chartDBs', sampleArray(12,0,20,true),'#b49cff');
    makeSparkline('chartStorage', sampleArray(12,10,8000,true),'#ffb3c6');
    makeSparkline('chartNet', sampleArray(12,5,1000,true),'#6dcff6');
    makeSparkline('chartAlerts', sampleArray(12,0,12,true),'#ff9f43');

  } catch (error) {
    console.error('Error loading metrics:', error);
    clientInfo.innerHTML = `<div class=\"alert alert-danger\">Failed to load metrics: ${error.message}</div>`;
  }
});
