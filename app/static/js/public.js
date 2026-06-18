function formatApiError(detail) {
  if (!detail) return 'Ошибка отправки';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg || JSON.stringify(e)).join('; ');
  }
  return String(detail);
}

function extractRuPhoneDigits(value) {
  let digits = String(value || '').replace(/\D/g, '');
  if (!digits) return '';

  if (digits.startsWith('8')) {
    digits = '7' + digits.slice(1);
  } else if (!digits.startsWith('7')) {
    digits = '7' + digits;
  }

  return digits.slice(0, 11);
}

function formatRuPhone(value) {
  const digits = extractRuPhoneDigits(value);
  if (!digits) return '';

  const national = digits.slice(1);
  let result = '+7';

  if (!national.length) return '+7 (';

  result += ' (' + national.slice(0, 3);
  if (national.length < 3) return result;

  result += ')';
  if (national.length === 3) return result + ' ';

  result += ' ' + national.slice(3, 6);
  if (national.length <= 6) return result;

  result += '-' + national.slice(6, 8);
  if (national.length <= 8) return result;

  return result + '-' + national.slice(8, 10);
}

function isRuPhoneComplete(value) {
  return extractRuPhoneDigits(value).length === 11;
}

function initPhoneInput(input) {
  if (!input || input.dataset.phoneMask) return;
  input.dataset.phoneMask = '1';
  input.setAttribute('inputmode', 'tel');
  input.setAttribute('autocomplete', 'tel');

  const applyMask = () => {
    input.value = formatRuPhone(input.value);
  };

  input.addEventListener('input', applyMask);

  input.addEventListener('focus', () => {
    if (!input.value.trim()) input.value = '+7 (';
  });

  input.addEventListener('blur', () => {
    if (input.value === '+7 (' || input.value === '+7') input.value = '';
  });

  input.addEventListener('paste', (e) => {
    e.preventDefault();
    const pasted = (e.clipboardData || window.clipboardData).getData('text') || '';
    input.value = formatRuPhone(pasted);
  });
}

function initPhoneInputs() {
  document.querySelectorAll('input[type="tel"][name="phone"]').forEach(initPhoneInput);
}

function getValidatedPhone(rawPhone, messageEl) {
  if (isRuPhoneComplete(rawPhone)) return formatRuPhone(rawPhone);
  messageEl.className = 'form-message error';
  messageEl.textContent = 'Введите номер телефона полностью, например +7 (999) 000-00-00';
  return null;
}

function setLeadFormMode(mode) {
  const normalized = mode === 'project' ? 'project' : 'product';
  const form = document.getElementById('leadForm');
  const modeField = document.getElementById('lead_form_mode');
  const title = document.getElementById('leadModalTitle');
  const subtitle = document.getElementById('leadModalSub');
  const productChip = document.getElementById('leadProductChip');

  if (modeField) modeField.value = normalized;

  document.querySelectorAll('.lead-form-tab').forEach(tab => {
    const active = tab.dataset.formMode === normalized;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', active ? 'true' : 'false');
  });

  document.querySelectorAll('[data-form-panel]').forEach(panel => {
    panel.classList.toggle('hidden', panel.dataset.formPanel !== normalized);
  });

  if (normalized === 'project') {
    if (title) title.textContent = 'Заявка на проект СПС';
    if (subtitle) subtitle.textContent = 'Опишите объект и систему — подготовим предложение по проекту';
    if (productChip) {
      productChip.textContent = 'Проект: встроенные системы пожаротушения';
      productChip.classList.remove('hidden');
    }
    const productField = form?.querySelector('[name="product_name"]');
    const productIdField = form?.querySelector('[name="product_id"]');
    if (productField) productField.value = 'Проект СПС / встроенные системы';
    if (productIdField) productIdField.value = '';
  } else if (title && subtitle) {
    const productName = form?.querySelector('[name="product_name"]')?.value || '';
    title.textContent = productName ? 'Заказ модели' : 'Заявка на расчёт';
    subtitle.textContent = productName
      ? 'Укажите контакты — менеджер уточнит детали заказа'
      : 'Оставьте контакты — менеджер подберёт комплект';
    if (productChip) {
      if (productName && productName !== 'Проект СПС / встроенные системы') {
        productChip.textContent = productName;
        productChip.classList.remove('hidden');
      } else {
        productChip.textContent = '';
        productChip.classList.add('hidden');
      }
    }
  }
}

function openLeadModal(options = {}) {
  const modal = document.getElementById('leadModal');
  const form = document.getElementById('leadForm');
  const title = document.getElementById('leadModalTitle');
  if (!modal || !form) return;

  const {
    productId = '',
    productName = '',
    objectType = '',
    formMode = 'product',
  } = options;

  form.reset();
  initPhoneInputs();

  const productField = form.querySelector('[name="product_name"]');
  const productIdField = form.querySelector('[name="product_id"]');
  const objectTypeField = form.querySelector('[name="object_type"]');

  if (productField) productField.value = productName || '';
  if (productIdField) productIdField.value = productId || '';
  if (objectTypeField && objectType) objectTypeField.value = objectType;

  setLeadFormMode(formMode === 'project' ? 'project' : 'product');

  if (formMode !== 'project' && productName) {
    const productChip = document.getElementById('leadProductChip');
    if (productChip) {
      productChip.textContent = productName;
      productChip.classList.remove('hidden');
    }
    if (title) title.textContent = 'Заказ модели';
  }

  const msg = document.getElementById('formMessage');
  if (msg) {
    msg.className = 'form-message';
    msg.textContent = '';
  }

  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';

  const firstInput = form.querySelector('input:not([type="hidden"]):not([name="website"])');
  if (firstInput) firstInput.focus();
}

function closeLeadModal() {
  const modal = document.getElementById('leadModal');
  if (!modal) return;
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
}

async function trackProductClick(productId) {
  if (!productId) return;
  try {
    await fetch('/api/public/track/click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ product_id: productId }),
    });
  } catch (_) {}
}

async function submitLead(payload, messageEl) {
  messageEl.className = 'form-message';
  messageEl.textContent = '';

  try {
    const res = await fetch('/api/public/leads', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': window.CSRF_TOKEN || '',
      },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(formatApiError(data.detail));
    messageEl.className = 'form-message success';
    messageEl.textContent = data.message || 'Спасибо! Менеджер свяжется с вами.';
    return true;
  } catch (err) {
    messageEl.className = 'form-message error';
    messageEl.textContent = typeof err.message === 'string' ? err.message : 'Не удалось отправить заявку';
    return false;
  }
}

function initProductCarousel() {
  const viewport = document.getElementById('productCarouselViewport');
  const track = document.getElementById('productCarouselTrack');
  if (!viewport || !track) return;

  let autoScroll = true;
  let isDragging = false;
  let dragMoved = false;
  let activePointer = null;
  let startX = 0;
  let scrollStart = 0;
  let resumeTimer = null;
  const speed = 0.65;

  const halfWidth = () => track.scrollWidth / 2;

  const normalizeScroll = () => {
    const half = halfWidth();
    if (half <= 0) return;
    while (viewport.scrollLeft >= half) viewport.scrollLeft -= half;
    while (viewport.scrollLeft < 0) viewport.scrollLeft += half;
  };

  const pauseAuto = (resumeMs = 5000) => {
    autoScroll = false;
    if (resumeTimer) clearTimeout(resumeTimer);
    resumeTimer = setTimeout(() => {
      autoScroll = true;
    }, resumeMs);
  };

  const onPointerDown = (e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    if (e.target.closest('.carousel-order')) return;

    isDragging = true;
    dragMoved = false;
    activePointer = e.pointerId;
    startX = e.clientX;
    scrollStart = viewport.scrollLeft;
    autoScroll = false;
    viewport.classList.add('is-dragging');
    viewport.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e) => {
    if (!isDragging || e.pointerId !== activePointer) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 5) dragMoved = true;
    viewport.scrollLeft = scrollStart - dx;
    normalizeScroll();
    if (dragMoved) e.preventDefault();
  };

  const endDrag = (e) => {
    if (!isDragging || e.pointerId !== activePointer) return;
    isDragging = false;
    activePointer = null;
    viewport.classList.remove('is-dragging');
    if (viewport.hasPointerCapture?.(e.pointerId)) {
      viewport.releasePointerCapture(e.pointerId);
    }
    normalizeScroll();
    pauseAuto(4500);
    if (dragMoved) {
      setTimeout(() => { dragMoved = false; }, 0);
    }
  };

  viewport.addEventListener('pointerdown', onPointerDown);
  viewport.addEventListener('pointermove', onPointerMove);
  viewport.addEventListener('pointerup', endDrag);
  viewport.addEventListener('pointercancel', endDrag);

  viewport.addEventListener('click', (e) => {
    if (!dragMoved) return;
    e.preventDefault();
    e.stopPropagation();
  }, true);

  const tick = () => {
    if (autoScroll && !isDragging && halfWidth() > viewport.clientWidth) {
      viewport.scrollLeft += speed;
      normalizeScroll();
    }
    requestAnimationFrame(tick);
  };

  requestAnimationFrame(tick);
}

document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/public/track/view', { method: 'POST', credentials: 'same-origin' }).catch(() => {});

  initPhoneInputs();
  initProductCarousel();

  document.querySelectorAll('.lead-form-tab').forEach(tab => {
    tab.addEventListener('click', () => setLeadFormMode(tab.dataset.formMode || 'product'));
  });

  document.querySelectorAll('[data-open-lead]').forEach(button => {
    button.addEventListener('click', async (e) => {
      e.preventDefault();
      const productId = button.dataset.productId || '';
      const productName = button.dataset.productName || '';
      const objectType = button.dataset.objectType || '';
      const formMode = button.dataset.formMode || 'product';
      if (productId) await trackProductClick(productId);
      openLeadModal({ productId, productName, objectType, formMode });
    });
  });

  document.querySelectorAll('.faq-item').forEach(item => {
    item.addEventListener('toggle', () => {
      if (!item.open) return;
      document.querySelectorAll('.faq-item').forEach(other => {
        if (other !== item) other.open = false;
      });
    });
  });

  const leadModal = document.getElementById('leadModal');
  if (leadModal) {
    leadModal.addEventListener('click', (e) => {
      if (e.target === leadModal) closeLeadModal();
    });
    leadModal.querySelectorAll('[data-close-modal]').forEach(btn => {
      btn.addEventListener('click', closeLeadModal);
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLeadModal();
  });

  const form = document.getElementById('leadForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msg = document.getElementById('formMessage');
    const fd = new FormData(form);

    if (!fd.get('privacy')) {
      msg.className = 'form-message error';
      msg.textContent = 'Подтвердите согласие с политикой конфиденциальности';
      return;
    }

    const formMode = fd.get('form_mode') || 'product';
    let comment = null;
    let productName = fd.get('product_name') || null;

    if (formMode === 'project') {
      const projectDetails = [
        'Тип заявки: проект СПС / встроенные системы',
        fd.get('project_company') ? `Компания: ${fd.get('project_company')}` : '',
        fd.get('project_name') ? `Объект: ${fd.get('project_name')}` : '',
        fd.get('project_system') ? `Система: ${fd.get('project_system')}` : '',
        fd.get('project_stage') ? `Этап: ${fd.get('project_stage')}` : '',
        fd.get('project_area') ? `Площадь/зоны: ${fd.get('project_area')}` : '',
        fd.get('project_address') ? `Адрес: ${fd.get('project_address')}` : '',
      ].filter(Boolean);
      const projectComment = (fd.get('project_comment') || '').trim();
      comment = [
        projectDetails.join('\n'),
        projectComment ? `Описание задачи:\n${projectComment}` : '',
      ].filter(Boolean).join('\n\n') || null;
      productName = productName || 'Проект СПС / встроенные системы';
    } else {
      const objectDetails = [
        fd.get('object_type') ? `Тип объекта: ${fd.get('object_type')}` : '',
        fd.get('area') ? `Площадь: ${fd.get('area')} м²` : '',
        fd.get('quantity') ? `Количество: ${fd.get('quantity')}` : '',
        fd.get('need_delivery') ? `Доставка/монтаж: ${fd.get('need_delivery')}` : '',
      ].filter(Boolean);
      const rawComment = (fd.get('comment') || '').trim();
      comment = [
        objectDetails.length ? 'Данные для подбора:\n' + objectDetails.join('\n') : '',
        rawComment ? 'Комментарий клиента:\n' + rawComment : '',
      ].filter(Boolean).join('\n\n') || null;
    }

    const phone = getValidatedPhone(fd.get('phone'), msg);
    if (!phone) return;

    const payload = {
      name: fd.get('name'),
      phone,
      email: fd.get('email') || null,
      product_id: fd.get('product_id') || null,
      product_name: productName,
      comment,
      website: fd.get('website') || null,
    };

    const ok = await submitLead(payload, msg);
    if (ok) {
      form.reset();
      setTimeout(closeLeadModal, 1400);
    }
  });
});
