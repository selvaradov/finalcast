const Explorer = (() => {
  let scatterChart = null;
  let initialized = false;
  let currentFilter = 'all';
  let currentSort = 'name';

  const SUBJECT_COLORS = {
    Philosophy: '#5b9bf5',
    Politics: '#e8614d',
    Economics: '#f0c75e'
  };

  function init(DATA) {
    if (initialized) return;
    initialized = true;

    buildScatterChart(DATA);
    buildTrends(DATA);
    buildPaperList(DATA);
    wireExplorerEvents(DATA);
  }

  function buildScatterChart(DATA) {
    const catalogue = DATA.paper_catalogue;
    const popularity = DATA.paper_popularity || {};

    const datasets = ['Philosophy', 'Politics', 'Economics'].map(subj => {
      const points = Object.entries(catalogue)
        .filter(([, p]) => p.subject === subj)
        .map(([name, p]) => {
          const popData = popularity[name] || {};
          const years = Object.keys(popData).map(Number);
          const recentYears = years.filter(y => y >= 2019 && y !== 2023);
          const avgPop = recentYears.length > 0
            ? recentYears.reduce((s, y) => s + popData[y], 0) / recentYears.length
            : 0;
          return { x: p.mu, y: p.sigma, name, avgPop, r: Math.max(4, Math.min(14, Math.sqrt(avgPop) * 1.5)) };
        });

      return {
        label: subj,
        data: points,
        backgroundColor: SUBJECT_COLORS[subj] + '99',
        borderColor: SUBJECT_COLORS[subj],
        borderWidth: 1,
        pointRadius: points.map(p => p.r),
        pointHoverRadius: points.map(p => p.r + 3),
      };
    });

    const ctx = document.getElementById('scatter-chart');
    scatterChart = new Chart(ctx, {
      type: 'scatter',
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: '#e8e5dc', font: { family: "'Caveat', cursive", size: 16, weight: 700 } }
          },
          tooltip: {
            mode: 'nearest',
            intersect: true,
            backgroundColor: '#222228',
            titleColor: '#e8e5dc',
            bodyColor: '#9a978e',
            borderColor: 'rgba(232,229,220,0.12)',
            borderWidth: 1,
            titleFont: { family: "'Caveat', cursive", size: 16, weight: 700 },
            bodyFont: { family: "'Inter', system-ui", size: 12 },
            padding: 12,
            callbacks: {
              title: (items) => items[0]?.raw?.name || '',
              label: (item) => {
                const d = item.raw;
                return [
                  `Mean: ${d.x.toFixed(1)}  σ: ${d.y.toFixed(1)}`,
                  d.avgPop > 0 ? `~${Math.round(d.avgPop)} candidates/year (recent avg)` : ''
                ].filter(Boolean);
              }
            }
          }
        },
        scales: {
          x: {
            title: { display: true, text: 'Mean mark (μ)', color: '#9a978e', font: { family: "'Inter', system-ui", size: 13 } },
            grid: { color: 'rgba(232,229,220,0.06)' },
            ticks: { color: '#9a978e', font: { size: 11 } },
            min: 55,
            max: 75
          },
          y: {
            title: { display: true, text: 'Volatility (σ)', color: '#9a978e', font: { family: "'Inter', system-ui", size: 13 } },
            grid: { color: 'rgba(232,229,220,0.06)' },
            ticks: { color: '#9a978e', font: { size: 11 } },
            min: 0,
            max: 16
          }
        },
        onClick: (evt, elements) => {
          if (elements.length > 0) {
            const el = elements[0];
            const point = scatterChart.data.datasets[el.datasetIndex].data[el.index];
            showProfile(point.name, DATA);
          }
        }
      }
    });
  }

  function buildTrends(DATA) {
    const el = document.getElementById('trends-section');
    if (!el) return;

    const catalogue = DATA.paper_catalogue;
    const popularity = DATA.paper_popularity || {};

    const withTrend = Object.entries(catalogue)
      .filter(([, p]) => p.trend_slope !== undefined)
      .sort((a, b) => a[1].trend_p - b[1].trend_p);

    const significant = withTrend.filter(([, p]) => p.trend_p < 0.05);
    const nearSig = withTrend.filter(([, p]) => p.trend_p >= 0.05 && p.trend_p < 0.15);

    const trendRow = (name, p) => {
      const dir = p.trend_slope > 0 ? 'easier' : 'harder';
      const arrow = p.trend_slope > 0 ? '↑' : '↓';
      const cls = p.trend_slope > 0 ? 'trend-up' : 'trend-down';
      const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';
      return `
        <div class="trend-row ${cls}" data-name="${name}">
          <span class="subject-dot subject-dot--${subjectCls}"></span>
          <span class="trend-name">${name}</span>
          <span class="trend-arrow">${arrow}</span>
          <span class="trend-slope">${p.trend_slope > 0 ? '+' : ''}${p.trend_slope.toFixed(2)} marks/yr</span>
          <span class="trend-dir">(${dir})</span>
          <span class="trend-p">p=${p.trend_p.toFixed(3)}</span>
        </div>`;
    };

    let popHtml = '';
    const popEntries = Object.entries(popularity);
    if (popEntries.length > 0) {
      const recent = popEntries
        .map(([name, years]) => {
          const y2025 = years['2025'] || 0;
          const y2019 = years['2019'] || years['2018'] || 0;
          const change = y2019 > 0 ? ((y2025 - y2019) / y2019 * 100) : 0;
          return { name, y2025, y2019, change, subject: catalogue[name]?.subject };
        })
        .filter(d => d.y2019 > 10 && d.subject);

      recent.sort((a, b) => b.change - a.change);
      const growing = recent.slice(0, 5);
      const declining = recent.slice(-5).reverse();

      popHtml = `
        <div class="trend-popularity">
          <h3>Popularity shifts (2019 → 2025)</h3>
          <div class="pop-cols">
            <div class="pop-col">
              <h4 class="pop-col-title pop-growing">Growing</h4>
              ${growing.map(d => {
                const subjectCls = d.subject === 'Philosophy' ? 'phil' : d.subject === 'Politics' ? 'pol' : 'econ';
                return `<div class="pop-row">
                  <span class="subject-dot subject-dot--${subjectCls}"></span>
                  <span class="pop-name">${d.name}</span>
                  <span class="pop-change pop-up">+${Math.round(d.change)}%</span>
                </div>`;
              }).join('')}
            </div>
            <div class="pop-col">
              <h4 class="pop-col-title pop-declining">Declining</h4>
              ${declining.map(d => {
                const subjectCls = d.subject === 'Philosophy' ? 'phil' : d.subject === 'Politics' ? 'pol' : 'econ';
                return `<div class="pop-row">
                  <span class="subject-dot subject-dot--${subjectCls}"></span>
                  <span class="pop-name">${d.name}</span>
                  <span class="pop-change pop-down">${Math.round(d.change)}%</span>
                </div>`;
              }).join('')}
            </div>
          </div>
        </div>`;
    }

    el.innerHTML = `
      <div class="trend-group">
        <h3>Significant score trends</h3>
        ${significant.map(([n, p]) => trendRow(n, p)).join('')}
      </div>
      ${nearSig.length > 0 ? `
        <div class="trend-group trend-group--near">
          <h3>Near-significant (p &lt; 0.15)</h3>
          ${nearSig.map(([n, p]) => trendRow(n, p)).join('')}
        </div>` : ''}
      ${popHtml}
    `;

    el.querySelectorAll('.trend-row').forEach(row => {
      row.addEventListener('click', () => showProfile(row.dataset.name, DATA));
    });
  }

  function showProfile(name, DATA) {
    const p = DATA.paper_catalogue[name];
    if (!p) return;

    const el = document.getElementById('paper-profile');
    const badge = diffBadge(p.sigma);
    const popData = (DATA.paper_popularity || {})[name] || {};
    const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';

    const popYears = Object.keys(popData).sort();
    let popHtml = '';
    if (popYears.length > 0) {
      const sparkData = popYears.map(y => popData[y]);
      const sparkMax = Math.max(...sparkData);
      popHtml = `
        <div class="profile-pop">
          <h4>Candidates over time</h4>
          <div class="sparkline">
            ${popYears.map((y, i) => {
              const h = Math.max(4, (sparkData[i] / sparkMax) * 60);
              const isRecent = +y >= 2020;
              return `<div class="spark-bar-wrap" title="${y}: ${sparkData[i]}">
                <div class="spark-bar ${isRecent ? 'spark-recent' : ''}" style="height:${h}px"></div>
                <span class="spark-year">${y.slice(2)}</span>
              </div>`;
            }).join('')}
          </div>
        </div>`;
    }

    let trendHtml = '';
    if (p.trend_slope !== undefined) {
      const dir = p.trend_slope > 0 ? 'getting easier' : 'getting harder';
      const sig = p.trend_p < 0.05 ? 'significant' : 'marginal';
      trendHtml = `<div class="profile-trend">Trend: ${p.trend_slope > 0 ? '+' : ''}${p.trend_slope.toFixed(2)} marks/year (${dir}, ${sig} p=${p.trend_p.toFixed(3)})</div>`;
    }

    el.innerHTML = `
      <div class="profile-header">
        <span class="subject-dot subject-dot--${subjectCls}"></span>
        <h3>${name}</h3>
        <span class="paper-badge ${badge.cls}">${badge.label}</span>
      </div>
      <div class="profile-stats">
        <div class="profile-stat">
          <div class="profile-stat-value">${p.mu.toFixed(1)}</div>
          <div class="profile-stat-label">mean mark</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-value">${p.sigma.toFixed(1)}</div>
          <div class="profile-stat-label">volatility (sd)</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-value">${p.pct_first.toFixed(0)}%</div>
          <div class="profile-stat-label">get a First</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-value">${p.pct_21.toFixed(0)}%</div>
          <div class="profile-stat-label">get a 2.1</div>
        </div>
        <div class="profile-stat">
          <div class="profile-stat-value">${p.pct_below_50.toFixed(1)}%</div>
          <div class="profile-stat-label">below 50</div>
        </div>
      </div>
      ${trendHtml}
      ${popHtml}
    `;

    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function diffBadge(sigma) {
    if (sigma >= 10.2) return { label: 'Kingmaker', cls: 'badge-kingmaker' };
    if (sigma >= 7)    return { label: 'Volatile', cls: 'badge-volatile' };
    if (sigma >= 5)    return { label: 'Moderate', cls: 'badge-moderate' };
    return { label: 'Predictable', cls: 'badge-predictable' };
  }

  function buildPaperList(DATA) {
    renderPaperList(DATA, 'all', 'name');
  }

  function renderPaperList(DATA, filterSubject, sortKey) {
    const el = document.getElementById('explorer-paper-list');
    let papers = Object.entries(DATA.paper_catalogue);

    if (filterSubject !== 'all') {
      papers = papers.filter(([, p]) => p.subject === filterSubject);
    }

    const searchVal = (document.getElementById('explorer-search')?.value || '').toLowerCase().trim();
    if (searchVal) {
      papers = papers.filter(([name]) => name.toLowerCase().includes(searchVal));
    }

    const sorters = {
      name: (a, b) => a[0].localeCompare(b[0]),
      mu: (a, b) => b[1].mu - a[1].mu,
      sigma: (a, b) => b[1].sigma - a[1].sigma,
      pct_first: (a, b) => b[1].pct_first - a[1].pct_first
    };
    papers.sort(sorters[sortKey] || sorters.name);

    el.innerHTML = papers.map(([name, p]) => {
      const badge = diffBadge(p.sigma);
      const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';
      return `
        <div class="explorer-paper-card" data-name="${name}">
          <div class="explorer-card-header">
            <span class="subject-dot subject-dot--${subjectCls}"></span>
            <span class="explorer-card-name">${name}</span>
            <span class="paper-badge ${badge.cls}">${badge.label}</span>
          </div>
          <div class="explorer-card-stats">
            <span>μ = ${p.mu.toFixed(1)}</span>
            <span>σ = ${p.sigma.toFixed(1)}</span>
            <span>${p.pct_first.toFixed(0)}% First</span>
          </div>
        </div>`;
    }).join('');

    el.querySelectorAll('.explorer-paper-card').forEach(card => {
      card.addEventListener('click', () => showProfile(card.dataset.name, DATA));
    });
  }

  function wireExplorerEvents(DATA) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentFilter = btn.dataset.subject;
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b === btn));
        filterScatter(DATA, currentFilter);
        renderPaperList(DATA, currentFilter, currentSort);
      });
    });

    document.querySelectorAll('.sort-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        currentSort = btn.dataset.sort;
        document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('active', b === btn));
        renderPaperList(DATA, currentFilter, currentSort);
      });
    });

    document.getElementById('explorer-search')?.addEventListener('input', () => {
      renderPaperList(DATA, currentFilter, currentSort);
    });
  }

  function filterScatter(DATA, subject) {
    if (!scatterChart) return;
    scatterChart.data.datasets.forEach(ds => {
      const visible = subject === 'all' || ds.label === subject;
      ds.hidden = !visible;
    });
    scatterChart.update();
  }

  return { init, showProfile };
})();
