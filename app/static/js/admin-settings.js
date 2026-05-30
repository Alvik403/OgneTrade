const ROLE_LABELS = {
  super_admin: 'Администратор',
  manager: 'Менеджер',
};

const CONTACT_FIELDS = ['phone', 'email', 'address', 'whatsapp', 'telegram'];

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function showMessage(el, text, type) {
  if (!el) return;
  el.className = 'form-message settings-message' + (type ? ' ' + type : '');
  el.textContent = text;
}

function setBlockOpen(block, open) {
  if (!block) return;
  block.classList.toggle('is-expanded', open);
  const trigger = block.querySelector(':scope > .settings-block-trigger, :scope > .settings-pane-trigger');
  if (trigger) trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
  const content = block.querySelector(':scope > .settings-block-content, :scope > .settings-pane-content');
  if (content) content.hidden = !open;
}

function syncSettingsAccordionState() {
  document.querySelectorAll('.settings-block, .settings-pane').forEach(block => {
    const open = block.classList.contains('is-expanded');
    const content = block.querySelector(':scope > .settings-block-content, :scope > .settings-pane-content');
    if (content) content.hidden = !open;
  });
}

function initSettingsAccordion() {
  document.querySelectorAll('.settings-block-trigger').forEach(btn => {
    btn.addEventListener('click', () => {
      const block = btn.closest('.settings-block');
      if (!block) return;
      setBlockOpen(block, !block.classList.contains('is-expanded'));
    });
  });

  document.querySelectorAll('.settings-pane-trigger').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const pane = btn.closest('.settings-pane');
      if (!pane) return;
      setBlockOpen(pane, !pane.classList.contains('is-expanded'));
    });
  });
}

function openSettingsBlock(id) {
  const block = document.getElementById(id);
  if (!block) return;
  setBlockOpen(block, true);
  block.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function openSiteSection(paneId) {
  openSettingsBlock('settings-site');
  if (paneId) openSettingsBlock(paneId);
}

async function loadSettings() {
  const res = await adminFetch('/api/admin/settings');
  if (!res.ok) return;
  const data = await res.json();
  const c = data.contacts || {};
  const n = data.notifications || {};

  const fieldMap = {
    phone: c.phone,
    email: c.email,
    address: c.address,
    whatsapp: c.whatsapp,
    telegram: c.telegram,
  };

  CONTACT_FIELDS.forEach(k => {
    const el = document.getElementById(k === 'telegram' ? 'site_telegram' : k);
    if (el) el.value = fieldMap[k] || '';
  });

  const notifyFields = [
    ['smtp_host', n.smtp_host || ''],
    ['smtp_port', n.smtp_port || 587],
    ['smtp_user', n.smtp_user || ''],
    ['smtp_password', n.smtp_password || ''],
    ['smtp_from', n.smtp_from || ''],
    ['telegram_bot_token', n.telegram_bot_token || ''],
    ['telegram_chat_id', n.telegram_chat_id || ''],
  ];

  notifyFields.forEach(([id, value]) => {
    const el = document.getElementById(id);
    if (el) el.value = value;
  });
}

async function loadUsers() {
  const tbody = document.getElementById('usersTable');
  if (!tbody) return;

  try {
    const res = await adminFetch('/api/admin/users');
    const users = await res.json();
    if (!res.ok || !Array.isArray(users)) {
      tbody.innerHTML = '<tr><td colspan="3" class="users-empty">Не удалось загрузить пользователей</td></tr>';
      return;
    }

    if (!users.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="users-empty">Пользователей пока нет</td></tr>';
      return;
    }

    tbody.innerHTML = users.map(u => {
      const statusClass = u.is_active ? 'status-active' : 'status-inactive';
      const isSelf = u.id === window.CURRENT_USER?.id;
      const roleClass = u.role === 'super_admin' ? 'role-picker--admin' : 'role-picker--manager';
      const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => (
        `<option value="${value}"${u.role === value ? ' selected' : ''}>${escapeHtml(label)}</option>`
      )).join('');
      return `
        <tr>
          <td>
            <div class="user-cell">
              <strong>${escapeHtml(u.full_name)}${isSelf ? ' <span class="user-self-tag">(вы)</span>' : ''}</strong>
              <span>${escapeHtml(u.email)}</span>
            </div>
          </td>
          <td>
            <div class="role-picker ${roleClass}">
              <select
                class="role-picker-select"
                data-user-id="${escapeHtml(u.id)}"
                data-prev-role="${escapeHtml(u.role)}"
                aria-label="Роль пользователя ${escapeHtml(u.full_name)}"
                ${isSelf ? 'disabled title="Смените свою роль через другого администратора"' : ''}
              >${roleOptions}</select>
            </div>
          </td>
          <td><span class="status-badge ${statusClass}">${u.is_active ? 'Активен' : 'Отключён'}</span></td>
        </tr>`;
    }).join('');
  } catch (_) {
    tbody.innerHTML = '<tr><td colspan="3" class="users-empty">Не удалось загрузить пользователей</td></tr>';
  }
}

function syncRolePickerStyle(select) {
  const picker = select?.closest('.role-picker');
  if (!picker) return;
  picker.classList.remove('role-picker--admin', 'role-picker--manager');
  picker.classList.add(select.value === 'super_admin' ? 'role-picker--admin' : 'role-picker--manager');
}

async function updateUserRole(select) {
  const userId = select.dataset.userId;
  const prevRole = select.dataset.prevRole;
  const role = select.value;
  if (!userId || role === prevRole) return;

  select.disabled = true;
  const msg = document.getElementById('usersMsg');
  showMessage(msg, 'Сохранение роли...', '');

  const res = await adminFetch(`/api/admin/users/${userId}`, {
    method: 'PATCH',
    body: { role },
  });

  select.disabled = false;

  if (res.ok) {
    select.dataset.prevRole = role;
    syncRolePickerStyle(select);
    showMessage(msg, 'Роль обновлена', 'success');
    loadUsers();
    return;
  }

  select.value = prevRole;
  syncRolePickerStyle(select);
  let detail = 'Не удалось изменить роль';
  try {
    const data = await res.json();
    if (typeof data.detail === 'string') detail = data.detail;
  } catch (_) {}
  showMessage(msg, detail, 'error');
}

document.getElementById('usersTable')?.addEventListener('change', (e) => {
  const select = e.target.closest('.role-picker-select');
  if (!select || select.disabled) return;
  syncRolePickerStyle(select);
  updateUserRole(select);
});

document.getElementById('settingsForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('settingsMsg');
  const fd = new FormData(e.target);
  const body = {
    contacts: {
      phone: fd.get('phone'),
      email: fd.get('email'),
      address: fd.get('address'),
      whatsapp: fd.get('whatsapp'),
      telegram: fd.get('telegram'),
    },
    notifications: {
      smtp_host: fd.get('smtp_host'),
      smtp_port: Number(fd.get('smtp_port')),
      smtp_user: fd.get('smtp_user'),
      smtp_password: fd.get('smtp_password'),
      smtp_from: fd.get('smtp_from'),
      smtp_use_tls: true,
      telegram_bot_token: fd.get('telegram_bot_token'),
      telegram_chat_id: fd.get('telegram_chat_id'),
    },
  };

  const res = await adminFetch('/api/admin/settings', { method: 'PUT', body });
  showMessage(msg, res.ok ? 'Настройки сохранены' : 'Ошибка сохранения', res.ok ? 'success' : 'error');
  if (res.ok) openSiteSection();
});

document.getElementById('testNotify')?.addEventListener('click', async () => {
  const msg = document.getElementById('settingsMsg');
  openSiteSection('settings-notify');
  showMessage(msg, 'Отправка теста...', '');
  const res = await adminFetch('/api/admin/settings/test-notify', { method: 'POST' });
  const data = await res.json();
  showMessage(
    msg,
    `Тест: Email — ${data.email ? 'OK' : 'нет'}, Telegram — ${data.telegram ? 'OK' : 'нет'}`,
    res.ok ? 'success' : 'error',
  );
});

document.getElementById('userForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = document.getElementById('usersMsg');
  const fd = new FormData(e.target);

  const res = await adminFetch('/api/admin/users', {
    method: 'POST',
    body: {
      email: fd.get('email'),
      full_name: fd.get('full_name'),
      password: fd.get('password'),
      role: fd.get('role'),
    },
  });

  if (res.ok) {
    e.target.reset();
    showMessage(msg, 'Пользователь добавлен', 'success');
    openSettingsBlock('settings-users');
    loadUsers();
    return;
  }

  let detail = 'Не удалось создать пользователя';
  try {
    const data = await res.json();
    if (typeof data.detail === 'string') detail = data.detail;
  } catch (_) {}
  showMessage(msg, detail, 'error');
});

loadSettings();
loadUsers();
initSettingsAccordion();
syncSettingsAccordionState();

if (window.location.hash === '#settings-users') {
  openSettingsBlock('settings-users');
}
