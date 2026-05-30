let leads = [];
let activeReadFilter = '';
let clientSearch = '';
let selectedProduct = '';
let expandedLeadId = null;
let suggestTimer;
let suggestRequestId = 0;

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildLeadsUrl() {
  const params = new URLSearchParams();
  if (activeReadFilter === 'true') params.set('read', 'true');
  if (activeReadFilter === 'false') params.set('read', 'false');
  if (clientSearch.trim()) params.set('client', clientSearch.trim());
  if (selectedProduct) params.set('product', selectedProduct);
  const qs = params.toString();
  return '/api/admin/leads' + (qs ? '?' + qs : '');
}

function buildCountsUrl() {
  const params = new URLSearchParams();
  if (clientSearch.trim()) params.set('client', clientSearch.trim());
  if (selectedProduct) params.set('product', selectedProduct);
  const qs = params.toString();
  return '/api/admin/leads/counts' + (qs ? '?' + qs : '');
}

function updateNavUnreadBadge(count) {
  const navBadge = document.getElementById('newLeadsBadge');
  if (!navBadge) return;
  navBadge.textContent = count;
  navBadge.classList.toggle('hidden', !count);
}

function updateTabCounts(data) {
  const unreadBadge = document.getElementById('unreadTabBadge');
  const readBadge = document.getElementById('readTabBadge');
  if (unreadBadge) unreadBadge.textContent = data.unread || 0;
  if (readBadge) readBadge.textContent = data.read || 0;
}

async function refreshNavUnreadCount() {
  try {
    const res = await adminFetch('/api/admin/leads/counts');
    if (!res.ok) return;
    const data = await res.json();
    updateNavUnreadBadge(data.unread || 0);
  } catch (_) {}
}

async function refreshTabCounts() {
  try {
    const res = await adminFetch(buildCountsUrl());
    if (!res.ok) return;
    const data = await res.json();
    updateTabCounts(data);
  } catch (_) {}
}

function showLoadError(message) {
  const empty = document.getElementById('leadsEmpty');
  const container = document.getElementById('leadsContainer');
  if (container) container.innerHTML = '';
  if (!empty) return;
  empty.textContent = message;
  empty.classList.remove('hidden');
}

function hideSuggestions() {
  const box = document.getElementById('searchSuggestions');
  if (box) {
    box.innerHTML = '';
    box.classList.add('hidden');
  }
}

function renderSuggestions(items) {
  const box = document.getElementById('searchSuggestions');
  if (!box) return;

  if (!items.length) {
    hideSuggestions();
    return;
  }

  box.innerHTML = items.map(item => `
    <button type="button" class="search-suggestion-item" data-query="${escapeHtml(item.query)}">
      <span class="search-suggestion-label">${escapeHtml(item.label)}</span>
      ${item.detail ? `<span class="search-suggestion-detail">${escapeHtml(item.detail)}</span>` : ''}
    </button>`).join('');
  box.classList.remove('hidden');

  box.querySelectorAll('.search-suggestion-item').forEach(btn => {
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault();
      applySearchQuery(btn.dataset.query || '');
    });
  });
}

async function fetchSuggestions(query) {
  const trimmed = query.trim();
  if (trimmed.length < 1) {
    hideSuggestions();
    return;
  }

  const requestId = ++suggestRequestId;
  try {
    const res = await adminFetch('/api/admin/leads/suggest?q=' + encodeURIComponent(trimmed));
    if (!res.ok || requestId !== suggestRequestId) return;
    const data = await res.json();
    if (!Array.isArray(data) || requestId !== suggestRequestId) return;
    renderSuggestions(data);
  } catch (_) {
    if (requestId === suggestRequestId) hideSuggestions();
  }
}

function applySearchQuery(value) {
  clientSearch = value;
  const input = document.getElementById('clientSearch');
  if (input) input.value = value;
  hideSuggestions();
  expandedLeadId = null;
  loadClients();
}

function scheduleSuggest() {
  clearTimeout(suggestTimer);
  suggestTimer = setTimeout(() => fetchSuggestions(clientSearch), 200);
}

function renderProductFilter(products) {
  const list = document.getElementById('productFilterList');
  if (!list) return;

  const items = [
    `<li><button type="button" class="product-filter-item${selectedProduct === '' ? ' active' : ''}" data-product="">Все</button></li>`,
    ...products.map(p => `
      <li>
        <button type="button" class="product-filter-item${selectedProduct === p.key ? ' active' : ''}" data-product="${escapeHtml(p.key)}">
          ${escapeHtml(p.name)} <span class="product-filter-count">${p.count}</span>
        </button>
      </li>`),
  ];
  list.innerHTML = items.join('');

  list.querySelectorAll('.product-filter-item').forEach(btn => {
    btn.addEventListener('click', () => {
      selectedProduct = btn.dataset.product ?? '';
      list.querySelectorAll('.product-filter-item').forEach(el => el.classList.remove('active'));
      btn.classList.add('active');
      expandedLeadId = null;
      loadClients();
    });
  });
}

async function loadProductFilters() {
  try {
    const res = await adminFetch('/api/admin/leads/meta/products');
    if (!res.ok) return;
    const data = await res.json();
    if (Array.isArray(data)) renderProductFilter(data);
  } catch (_) {}
}

function renderLeadDetail(lead) {
  const emailHtml = lead.email
    ? `<a class="lead-detail-link" href="mailto:${escapeHtml(lead.email)}">${escapeHtml(lead.email)}</a>`
    : '<span class="lead-detail-empty">—</span>';
  const product = lead.product_name_snapshot?.trim() || '—';
  const message = lead.comment_initial?.trim() || '—';

  return `
    <div class="lead-detail-panel">
      <div class="lead-detail-fields">
        <div class="lead-detail-field">
          <span class="lead-detail-label">Имя</span>
          <span class="lead-detail-value">${escapeHtml(lead.name)}</span>
        </div>
        <div class="lead-detail-field">
          <span class="lead-detail-label">Телефон</span>
          <a class="lead-detail-link lead-detail-value" href="tel:${escapeHtml(lead.phone)}">${escapeHtml(lead.phone)}</a>
        </div>
        <div class="lead-detail-field">
          <span class="lead-detail-label">Email</span>
          ${emailHtml}
        </div>
        <div class="lead-detail-field">
          <span class="lead-detail-label">Товар</span>
          <span class="lead-detail-value">${escapeHtml(product)}</span>
        </div>
      </div>
      <div class="lead-detail-message-block">
        <span class="lead-detail-label">Сообщение</span>
        <div class="lead-detail-message">${escapeHtml(message)}</div>
      </div>
    </div>`;
}

function renderLeadRow(lead) {
  const isExpanded = expandedLeadId === lead.id;
  return `
    <div class="lead-row ${lead.is_read ? 'lead-read' : 'lead-unread'} ${isExpanded ? 'is-expanded' : ''}" data-id="${escapeHtml(lead.id)}">
      <button type="button" class="lead-row-main" data-toggle-lead="${escapeHtml(lead.id)}">
        <span class="read-dot ${lead.is_read ? 'read' : 'unread'}" title="${lead.is_read ? 'Прочитано' : 'Новая'}"></span>
        <span class="lead-row-date">${new Date(lead.created_at).toLocaleString('ru')}</span>
        <span class="lead-row-name">${escapeHtml(lead.name)}</span>
        <span class="lead-row-phone">${escapeHtml(lead.phone)}</span>
        <span class="lead-row-product">${escapeHtml(lead.product_name_snapshot || '—')}</span>
        <span class="lead-row-chevron">${isExpanded ? '▲' : '▼'}</span>
      </button>
      ${isExpanded ? `<div class="lead-row-detail">${renderLeadDetail(lead)}</div>` : ''}
    </div>`;
}

function renderGroupedList(items) {
  const groups = new Map();
  items.forEach(lead => {
    const key = lead.product_name_snapshot?.trim() || 'Без товара';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(lead);
  });
  const sorted = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0], 'ru'));
  return sorted.map(([product, groupLeads]) => `
    <section class="lead-product-group">
      <h3 class="lead-product-group-title">${escapeHtml(product)} <span>${groupLeads.length}</span></h3>
      <div class="leads-list">${groupLeads.map(renderLeadRow).join('')}</div>
    </section>`).join('');
}

function renderLeadsList() {
  const container = document.getElementById('leadsContainer');
  const empty = document.getElementById('leadsEmpty');
  if (!container || !empty) return;

  if (!leads.length) {
    container.innerHTML = '';
    const hasSearch = clientSearch.trim() || selectedProduct;
    empty.textContent = hasSearch
      ? 'Ничего не найдено'
      : activeReadFilter === 'false'
        ? 'Непрочитанных заявок нет'
        : activeReadFilter === 'true'
          ? 'Прочитанных заявок нет'
          : 'Заявок пока нет';
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  container.innerHTML = renderGroupedList(leads);

  container.querySelectorAll('[data-toggle-lead]').forEach(btn => {
    btn.addEventListener('click', () => toggleLead(btn.dataset.toggleLead));
  });
}

async function toggleLead(id) {
  if (expandedLeadId === id) {
    expandedLeadId = null;
    renderLeadsList();
    return;
  }

  const lead = leads.find(l => l.id === id);
  if (lead && !lead.is_read) {
    try {
      const res = await adminFetch('/api/admin/leads/' + id + '/read', { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        const index = leads.findIndex(l => l.id === id);
        if (index >= 0) leads[index] = updated;
      }
    } catch (_) {}
  }

  expandedLeadId = id;
  renderLeadsList();
  await refreshTabCounts();
  await refreshNavUnreadCount();
}

async function loadClients() {
  const container = document.getElementById('leadsContainer');
  const empty = document.getElementById('leadsEmpty');
  if (!container || !empty) return;

  try {
    const res = await adminFetch(buildLeadsUrl());
    const data = await res.json();
    if (!res.ok) {
      showLoadError(typeof data.detail === 'string' ? data.detail : 'Не удалось загрузить заявки');
      return;
    }
    if (!Array.isArray(data)) {
      showLoadError('Некорректный ответ сервера');
      return;
    }

    leads = data;
    if (expandedLeadId && !leads.some(l => l.id === expandedLeadId)) {
      expandedLeadId = null;
    }
    renderLeadsList();
  } catch (_) {
    showLoadError('Не удалось загрузить заявки');
  }

  await refreshTabCounts();
  await refreshNavUnreadCount();
}

let searchTimer;
function scheduleSearchReload() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadClients, 250);
}

document.getElementById('readTabs')?.addEventListener('click', (e) => {
  const tab = e.target.closest('.leads-tab');
  if (!tab) return;
  document.querySelectorAll('.leads-tab').forEach(el => el.classList.remove('active'));
  tab.classList.add('active');
  activeReadFilter = tab.dataset.read ?? '';
  expandedLeadId = null;
  loadClients();
});

document.getElementById('clientSearch')?.addEventListener('input', (e) => {
  clientSearch = e.target.value;
  expandedLeadId = null;
  scheduleSuggest();
  scheduleSearchReload();
});

document.getElementById('clientSearch')?.addEventListener('focus', () => {
  if (clientSearch.trim()) scheduleSuggest();
});

document.getElementById('clientSearch')?.addEventListener('blur', () => {
  setTimeout(hideSuggestions, 150);
});

document.getElementById('clientSearch')?.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') hideSuggestions();
});

document.addEventListener('click', (e) => {
  if (!e.target.closest('.leads-search-combobox')) hideSuggestions();
});

document.getElementById('reloadClients')?.addEventListener('click', async () => {
  await loadProductFilters();
  await loadClients();
});

loadProductFilters();
loadClients();
