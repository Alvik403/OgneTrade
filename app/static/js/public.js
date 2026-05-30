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

function setProductWidgetOpen(widget, open) {
  if (!widget) return;
  const head = widget.querySelector('.product-widget-head');
  const details = widget.querySelector('.product-widget-details');
  const toggleBtn = widget.querySelector('[data-toggle-product]');
  const isOpen = open ?? !widget.classList.contains('is-expanded');

  if (isOpen) {
    document.querySelectorAll('.product-widget.is-expanded').forEach(other => {
      if (other !== widget) setProductWidgetOpen(other, false);
    });
  }

  widget.classList.toggle('is-expanded', isOpen);
  if (head) head.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  if (details) details.hidden = !isOpen;
  if (toggleBtn) toggleBtn.textContent = isOpen ? 'Свернуть' : 'Подробнее';
}

function openLeadModal(options = {}) {
  const modal = document.getElementById('leadModal');
  const form = document.getElementById('leadForm');
  const title = document.getElementById('leadModalTitle');
  if (!modal || !form) return;

  const { productId = '', productName = '', objectType = '' } = options;

  form.reset();
  initPhoneInputs();

  const productField = form.querySelector('[name="product_name"]');
  const productIdField = form.querySelector('[name="product_id"]');
  const objectTypeField = form.querySelector('[name="object_type"]');
  const productChip = document.getElementById('leadProductChip');
  const subtitle = document.getElementById('leadModalSub');

  if (productField) productField.value = productName || '';
  if (productIdField) productIdField.value = productId || '';
  if (objectTypeField && objectType) objectTypeField.value = objectType;

  if (productChip) {
    if (productName) {
      productChip.textContent = productName;
      productChip.classList.remove('hidden');
    } else {
      productChip.textContent = '';
      productChip.classList.add('hidden');
    }
  }

  if (title) {
    title.textContent = productName ? 'Заказ модели' : 'Заявка на расчёт';
  }
  if (subtitle) {
    subtitle.textContent = productName
      ? 'Укажите контакты — менеджер уточнит детали заказа'
      : 'Оставьте контакты — менеджер подберёт комплект';
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

document.addEventListener('DOMContentLoaded', () => {
  fetch('/api/public/track/view', { method: 'POST', credentials: 'same-origin' }).catch(() => {});

  initPhoneInputs();

  document.querySelectorAll('[data-open-lead]').forEach(button => {
    button.addEventListener('click', async (e) => {
      e.preventDefault();
      const productId = button.dataset.productId || '';
      const productName = button.dataset.productName || '';
      const objectType = button.dataset.objectType || '';
      if (productId) await trackProductClick(productId);
      openLeadModal({ productId, productName, objectType });
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

  document.querySelectorAll('.product-widget').forEach(widget => {
    const head = widget.querySelector('.product-widget-head');
    const toggleBtn = widget.querySelector('[data-toggle-product]');

    head?.addEventListener('click', (e) => {
      if (e.target.closest('[data-open-lead]') || e.target.closest('[data-toggle-product]')) return;
      setProductWidgetOpen(widget);
    });

    head?.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      e.preventDefault();
      setProductWidgetOpen(widget);
    });

    toggleBtn?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      setProductWidgetOpen(widget);
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

    const objectDetails = [
      fd.get('object_type') ? `Тип объекта: ${fd.get('object_type')}` : '',
      fd.get('area') ? `Площадь: ${fd.get('area')} м²` : '',
      fd.get('quantity') ? `Количество: ${fd.get('quantity')}` : '',
      fd.get('need_delivery') ? `Доставка/монтаж: ${fd.get('need_delivery')}` : '',
    ].filter(Boolean);
    const rawComment = (fd.get('comment') || '').trim();
    const comment = [
      objectDetails.length ? 'Данные для подбора:\n' + objectDetails.join('\n') : '',
      rawComment ? 'Комментарий клиента:\n' + rawComment : '',
    ].filter(Boolean).join('\n\n') || null;

    const phone = getValidatedPhone(fd.get('phone'), msg);
    if (!phone) return;

    const payload = {
      name: fd.get('name'),
      phone,
      email: fd.get('email') || null,
      product_id: fd.get('product_id') || null,
      product_name: fd.get('product_name') || null,
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
