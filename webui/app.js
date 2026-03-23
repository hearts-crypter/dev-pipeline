const API = '';

function setToast(html, kind = 'muted') {
  const el = document.getElementById('toast');
  el.className = kind;
  el.innerHTML = html;
}

function statusBadge(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

async function jget(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

let _projects = [];
const STATUS_RANK = {active: 0, paused: 1, blocked: 2, stopped: 3, finished: 4};
const PRIORITY_RANK = {high: 0, medium: 1, low: 2};

function sortedAndFilteredProjects(items) {
  const filter = document.getElementById('statusFilter')?.value || 'all';
  const sortMode = document.getElementById('sortMode')?.value || 'status_then_name';

  let out = [...items];
  if (filter !== 'all') out = out.filter(p => p.status === filter);

  if (sortMode === 'name') {
    out.sort((a, b) => a.name.localeCompare(b.name));
  } else if (sortMode === 'priority_then_name') {
    out.sort((a, b) => (PRIORITY_RANK[a.priority] ?? 99) - (PRIORITY_RANK[b.priority] ?? 99) || a.name.localeCompare(b.name));
  } else {
    out.sort((a, b) => (STATUS_RANK[a.status] ?? 99) - (STATUS_RANK[b.status] ?? 99) || a.name.localeCompare(b.name));
  }

  return out;
}

async function refreshProjects() {
  const data = await jget('/projects');
  _projects = data.projects || [];
  const tbody = document.getElementById('projects');
  const detailSel = document.getElementById('detailProject');
  tbody.innerHTML = '';
  detailSel.innerHTML = '';

  const rows = sortedAndFilteredProjects(_projects);

  for (const p of rows) {
    const tr = document.createElement('tr');
    let repoCell = `<button id="pubReq-${p.id}">Request GitHub Publish</button>`;
    if (p.repo_url) {
      if (p.repo_private === false) {
        repoCell = `<a href="${p.repo_url}" target="_blank" rel="noopener noreferrer"><button>GitHub</button></a> <span class="badge active">Public</span>`;
      } else if (p.repo_private === true) {
        repoCell = `<a href="${p.repo_url}" target="_blank" rel="noopener noreferrer"><button>GitHub</button></a> <button id="visPub-${p.id}">Make Public</button>`;
      } else {
        repoCell = `<a href="${p.repo_url}" target="_blank" rel="noopener noreferrer"><button>GitHub</button></a> <span class="muted">visibility unknown</span>`;
      }
    }

    const lockText = p.lock_mode ? 'locked' : 'free';

    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${p.name}</td>
      <td>${statusBadge(p.status)}</td>
      <td>${lockText}</td>
      <td>${p.next_milestone || ''}</td>
      <td>${repoCell}</td>
      <td>
        <select id="sel-${p.id}">
          <option>active</option><option>paused</option><option>blocked</option><option>stopped</option><option>finished</option>
        </select>
        <button id="btn-${p.id}">Set</button>
        <button id="lockToggle-${p.id}">${p.lock_mode === 'manual' ? 'Unlock' : 'Lock'}</button>
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

    const reqBtn = document.getElementById(`pubReq-${p.id}`);
    if (reqBtn) {
      reqBtn.onclick = async () => {
        const out = await fetch(`/projects/${p.id}/publish-request`, {
          method: 'POST',
          headers: {'content-type':'application/json'},
          body: JSON.stringify({source: 'webui'})
        }).then(r => r.json());

        const result = out?.result || {};
        const repoUrl = result.repo_url || out?.queued?.repo_url;
        if (out?.ok && repoUrl) {
          setToast(`✅ Published successfully: <a href="${repoUrl}" target="_blank" rel="noopener noreferrer">${repoUrl}</a>`, 'ok');
        } else if (out?.ok) {
          setToast('✅ Publish request succeeded.', 'ok');
        } else {
          const err = result.error || JSON.stringify(out);
          setToast(`❌ Publish failed: ${err}`, 'err');
        }

        document.getElementById('controlStatus').textContent = 'Publish action: ' + JSON.stringify(out);
        await refreshAll();
      };
    }

    const visBtn = document.getElementById(`visPub-${p.id}`);
    if (visBtn) {
      visBtn.onclick = async () => {
        if (!confirm(`Make ${p.name} GitHub repo public?`)) return;
        const out = await fetch(`/projects/${p.id}/repo-visibility`, {
          method: 'POST',
          headers: {'content-type':'application/json'},
          body: JSON.stringify({visibility: 'public', source: 'webui'})
        }).then(r => r.json());

        const result = out?.result || {};
        if (out?.ok) {
          const url = result.repo_url || p.repo_url;
          setToast(`✅ Repo is now public: <a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`, 'ok');
        } else {
          setToast(`❌ Visibility change failed: ${result.error || JSON.stringify(out)}`, 'err');
        }
        document.getElementById('controlStatus').textContent = 'Visibility action: ' + JSON.stringify(out);
        await refreshAll();
      };
    }

    const toggleBtn = document.getElementById(`lockToggle-${p.id}`);
    toggleBtn.onclick = async () => {
      const isManualLocked = p.lock_mode === 'manual';
      const endpoint = isManualLocked ? 'lock-stop' : 'lock-start';
      const body = isManualLocked
        ? {owner: 'webui', force: true}
        : {owner: 'webui', ttl_minutes: 120};

      const out = await fetch(`/projects/${p.id}/${endpoint}`, {
        method: 'POST', headers: {'content-type':'application/json'},
        body: JSON.stringify(body)
      }).then(r => r.json());

      if (out.ok && !isManualLocked) {
        setToast(`🔒 Lock enabled for ${p.name}`, 'ok');
      } else if (out.ok && isManualLocked) {
        setToast(`🔓 Unlocked ${p.name}`, 'ok');
      } else {
        setToast(`❌ Lock toggle failed: ${JSON.stringify(out)}`, 'err');
      }
      await refreshAll();
    };

    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.id})`;
    detailSel.appendChild(opt);
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

async function refreshPublishRequests() {
  const items = await jget('/logs/publish-requests?limit=20');
  document.getElementById('publishRequests').textContent = JSON.stringify(items, null, 2);
}

function fmtList(title, items, mapFn) {
  if (!items || !items.length) return `<p><b>${title}:</b> none</p>`;
  const lis = items.slice(-8).reverse().map(mapFn).join('');
  return `<p><b>${title}:</b></p><ul>${lis}</ul>`;
}

async function refreshProjectDetail() {
  const sel = document.getElementById('detailProject');
  if (!sel.value) return;
  const detail = await jget(`/projects/${sel.value}/timeline?limit=50`);
  const p = detail.project;
  const t = detail.timeline;

  const html = `
    <p><b>${p.name}</b> (${p.id})</p>
    <p>Status: ${statusBadge(p.status)} | Priority: ${p.priority}</p>
    <p>Next milestone: ${p.next_milestone || 'unspecified'}</p>
    <p>Notify: ${p.owner_notify_email || 'n/a'}</p>
    ${fmtList('Status changes', t.status_events, e => `<li>${e.changed_at || ''}: ${e.old_status} → ${e.new_status}</li>`) }
    ${fmtList('Notifications', t.notifications, n => `<li>${n.sent_at || ''}: ${n.status} (${(n.milestones||[]).join(', ') || 'n/a'})</li>`) }
    ${fmtList('Runs', t.runs, r => `<li>${r.run_at || ''}: active=${r.active_projects}, actions=${(r.actions||[]).length}</li>`) }
  `;
  document.getElementById('projectDetail').innerHTML = html;
}

async function refreshAll() {
  await Promise.all([refreshProjects(), refreshRuns(), refreshNotifications(), refreshPublishRequests()]);
  await refreshProjectDetail();
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

document.getElementById('runRepoProc').onclick = async () => {
  const out = await fetch('/runs/process-repo-requests', {method: 'POST'}).then(r => r.json());
  document.getElementById('controlStatus').textContent = 'Repo processing: ' + JSON.stringify(out);
  await refreshAll();
};


document.getElementById('loadDetail').onclick = async () => {
  await refreshProjectDetail();
};

document.getElementById('sendTest').onclick = async () => {
  const id = document.getElementById('detailProject').value;
  if (!id) return;
  const out = await fetch(`/projects/${id}/email-test`, {
    method: 'POST',
    headers: {'content-type':'application/json'},
    body: JSON.stringify({})
  }).then(r => r.json());
  document.getElementById('controlStatus').textContent = 'Test email: ' + JSON.stringify(out);
  await refreshAll();
};

document.getElementById('statusFilter').onchange = () => refreshProjects();
document.getElementById('sortMode').onchange = () => refreshProjects();

refreshAll().catch(e => {
  document.getElementById('controlStatus').textContent = String(e);
  setToast(`❌ ${String(e)}`, 'err');
});
