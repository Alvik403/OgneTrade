let trafficChart;
let currentPeriod = '7d';

const PERIOD_LABELS = {
  '6h': 'за последние 6 часов',
  '12h': 'за последние 12 часов',
  '24h': 'за последние 24 часа',
  '7d': 'за последние 7 дней',
  '30d': 'за последние 30 дней',
  '90d': 'за последние 90 дней',
};

const TICK_LIMITS = {
  '6h': 6,
  '12h': 6,
  '24h': 8,
  '7d': 7,
  '30d': 10,
  '90d': 9,
};

function formatNumber(value) {
  return new Intl.NumberFormat('ru-RU').format(value || 0);
}

function renderKpi(summary) {
  document.getElementById('analyticsKpi').innerHTML = `
    <div class="analytics-kpi">
      <span class="analytics-kpi-label">Просмотры</span>
      <strong class="analytics-kpi-value">${formatNumber(summary.views)}</strong>
    </div>
    <div class="analytics-kpi">
      <span class="analytics-kpi-label">Клики по товарам</span>
      <strong class="analytics-kpi-value">${formatNumber(summary.clicks)}</strong>
      <small>${summary.click_rate}% от просмотров</small>
    </div>
    <div class="analytics-kpi">
      <span class="analytics-kpi-label">Заявки</span>
      <strong class="analytics-kpi-value">${formatNumber(summary.leads)}</strong>
      <small>${summary.lead_rate}% от кликов</small>
    </div>
    <div class="analytics-kpi">
      <span class="analytics-kpi-label">Конверсия</span>
      <strong class="analytics-kpi-value">${summary.conversion_rate}%</strong>
      <small>заявки / просмотры</small>
    </div>
    <div class="analytics-kpi accent">
      <span class="analytics-kpi-label">Непрочитанные</span>
      <strong class="analytics-kpi-value">${formatNumber(summary.unread_leads)}</strong>
    </div>`;
}

function renderFunnel(summary) {
  document.getElementById('funnelStats').innerHTML = `
    <div class="funnel-step"><span>Просмотры</span><strong>${formatNumber(summary.views)}</strong></div>
    <div class="funnel-step"><span>Клики</span><strong>${formatNumber(summary.clicks)}</strong><em>${summary.click_rate}%</em></div>
    <div class="funnel-step"><span>Заявки</span><strong>${formatNumber(summary.leads)}</strong><em>${summary.lead_rate}%</em></div>`;
}

function renderTopProducts(items) {
  const el = document.getElementById('topProductsList');
  if (!items.length) {
    el.innerHTML = '<p class="cell-muted">Нет данных за период</p>';
    return;
  }
  const max = Math.max(...items.map(i => i.clicks), 1);
  el.innerHTML = items.map(item => `
    <div class="top-product-row">
      <div class="top-product-head">
        <span>${item.title}</span>
        <strong>${item.clicks}</strong>
      </div>
      <div class="top-product-bar"><span style="width:${Math.round(item.clicks / max * 100)}%"></span></div>
    </div>`).join('');
}

function formatTooltipTitle(label, timestamp) {
  if (!timestamp) return label;
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return label;
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function renderChart(chart, granularity, period, granularityLabel) {
  const ctx = document.getElementById('trafficChart');
  if (trafficChart) trafficChart.destroy();

  const timestamps = chart.timestamps || [];
  const maxTicks = TICK_LIMITS[period] || 8;

  trafficChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: chart.labels,
      datasets: [
        {
          label: 'Просмотры',
          data: chart.views,
          borderColor: '#dc2626',
          backgroundColor: 'rgba(220, 38, 38, 0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: chart.intervals > 20 ? 0 : 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
        {
          label: 'Клики',
          data: chart.clicks,
          borderColor: '#f97316',
          backgroundColor: 'rgba(249, 115, 22, 0.06)',
          fill: false,
          tension: 0.3,
          pointRadius: chart.intervals > 20 ? 0 : 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
        {
          label: 'Заявки',
          data: chart.leads,
          borderColor: '#111827',
          backgroundColor: 'rgba(17, 24, 39, 0.06)',
          fill: false,
          tension: 0.3,
          pointRadius: chart.intervals > 20 ? 0 : 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            title(items) {
              if (!items.length) return '';
              const idx = items[0].dataIndex;
              return formatTooltipTitle(chart.labels[idx], timestamps[idx]);
            },
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0, maxTicksLimit: 6 },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: {
          grid: { display: false },
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: maxTicks,
            font: { size: 11 },
          },
        },
      },
    },
  });

  const intervals = chart.intervals || chart.labels.length;
  document.getElementById('chartGranularityHint').textContent =
    `${granularityLabel || (granularity === 'hour' ? 'по часам' : 'по дням')} · ${intervals} интервалов`;
}

async function loadAnalytics() {
  const res = await adminFetch('/api/admin/analytics/dashboard?period=' + currentPeriod);
  const data = await res.json();

  document.getElementById('analyticsRangeLabel').textContent =
    'Динамика ' + (PERIOD_LABELS[currentPeriod] || '');

  renderKpi(data.summary);
  renderFunnel(data.summary);
  renderTopProducts(data.top_products || []);
  renderChart(data.chart, data.granularity, data.period, data.granularity_label);
}

document.getElementById('periodPills')?.addEventListener('click', (e) => {
  const pill = e.target.closest('.period-pill');
  if (!pill) return;
  document.querySelectorAll('.period-pill').forEach(el => el.classList.remove('active'));
  pill.classList.add('active');
  currentPeriod = pill.dataset.period;
  loadAnalytics();
});

document.getElementById('reloadAnalytics')?.addEventListener('click', loadAnalytics);
loadAnalytics();
