const API = '';

function statusBadge(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

async function jget(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function refreshProjects() {
  const data = await jget('/projects');
  const tbody = document.getElementById('projects');
  tbody.innerHTML = '';

  for (const p of data.projects || []) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${p.name}</td>
      <td>${statusBadge(p.status)}</td>
      <td>${p.next_milestone || ''}</td>
      <td>
        <select id="sel-${p.id}">
          <option>active</option><option>paused</option><option>blocked</option><option>stopped</option><option>finished</option>
        </select>
        <button id="btn-${p.id}">Set</button>
      </td>
    `;
    tbody.appendChild(tr);
    document.getElementById(`sel-${p.id}`).value = p.status;
    document.getElementById(`btn-${p.id}`).onclick = async () => {
      const status = document.getElementById(`sel-${p.id}`).value;
      await fetch(`/projects/${p.id}/status`, {
        method: 'PATCH',
        headers: {'content-type':'application/json'},
        body: JSON.stringify({status, note: 'webui update'})
      });
      await refreshAll();
    };
  }
}

async function refreshRuns() {
  const runs = await jget('/logs/runs?limit=20');
  document.getElementById('runs').textContent = JSON.stringify(runs, null, 2);
}

async function refreshNotifications() {
  const items = await jget('/logs/notifications?limit=20');
  document.getElementById('notifications').textContent = JSON.stringify(items, null, 2);
}

async function refreshAll() {
  await Promise.all([refreshProjects(), refreshRuns(), refreshNotifications()]);
}

document.getElementById('runSweep').onclick = async () => {
  const out = await fetch('/runs/sweep', {method: 'POST'}).then(r => r.json());
  document.getElementById('controlStatus').textContent = 'Sweep done: ' + JSON.stringify(out);
  await refreshAll();
};

document.getElementById('runNotify').onclick = async () => {
  const out = await fetch('/runs/milestones-notify', {method: 'POST'}).then(r => r.json());
  document.getElementById('controlStatus').textContent = 'Notify done: ' + JSON.stringify(out);
  await refreshAll();
};

refreshAll().catch(e => {
  document.getElementById('controlStatus').textContent = String(e);
});
