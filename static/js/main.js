/* ============================================================
   main.js — ApartaSmart shared JS
   ============================================================ */

// ── Flash message auto-dismiss ──────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash-msg');
  flashes.forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      el.style.opacity = '0';
      el.style.transform = 'translateX(100%)';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  // Close button on flash
  document.querySelectorAll('.flash-close').forEach(btn => {
    btn.addEventListener('click', () => btn.closest('.flash-msg').remove());
  });

  // ── Modal helpers ─────────────────────────────────────────
  document.querySelectorAll('[data-modal]').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const id = trigger.getAttribute('data-modal');
      const modal = document.getElementById(id);
      if (modal) modal.classList.add('active');
    });
  });

  document.querySelectorAll('.modal-close, [data-modal-close]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.modal-overlay').classList.remove('active');
    });
  });

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('active');
    });
  });

  // ── Mobile sidebar toggle ─────────────────────────────────
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar   = document.querySelector('.sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // ── Active nav link ───────────────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ── Confirm delete / action ───────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      const msg = el.getAttribute('data-confirm') || 'Are you sure?';
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // ── Table search ──────────────────────────────────────────
  const tableSearch = document.getElementById('tableSearch');
  if (tableSearch) {
    tableSearch.addEventListener('input', () => {
      const q = tableSearch.value.toLowerCase();
      document.querySelectorAll('tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(q) ? '' : 'none';
      });
    });
  }

  // ── Animate stat numbers ──────────────────────────────────
  document.querySelectorAll('.stat-value[data-target]').forEach(el => {
    const target = parseFloat(el.getAttribute('data-target'));
    const isFloat = el.getAttribute('data-float') === 'true';
    let start = 0;
    const duration = 800;
    const step = (timestamp) => {
      if (!start) start = timestamp;
      const progress = Math.min((timestamp - start) / duration, 1);
      const current = progress * target;
      el.textContent = isFloat
        ? '₹' + current.toLocaleString('en-IN', { maximumFractionDigits: 0 })
        : Math.round(current).toLocaleString('en-IN');
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
});

// ── Chart.js defaults ─────────────────────────────────────
if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#94a3b8';
  Chart.defaults.borderColor = 'rgba(99,179,237,0.1)';
  Chart.defaults.font.family = 'Inter';
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
}

// ── Helper: build revenue chart ──────────────────────────
function buildRevenueChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: datasets.map((d, i) => ({
        ...d,
        tension: 0.4,
        fill: i === 0,
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }))
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' }, tooltip: { mode: 'index', intersect: false } },
      scales: {
        x: { grid: { color: 'rgba(99,179,237,0.07)' } },
        y: { grid: { color: 'rgba(99,179,237,0.07)' }, beginAtZero: true,
             ticks: { callback: v => '₹' + v.toLocaleString('en-IN') } }
      }
    }
  });
}

// ── Helper: build doughnut chart ─────────────────────────
function buildDoughnutChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '72%',
      plugins: { legend: { position: 'bottom' } }
    }
  });
}

// ── Helper: build bar chart ───────────────────────────────
function buildBarChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: 'rgba(99,179,237,0.07)' }, beginAtZero: true }
      }
    }
  });
}
