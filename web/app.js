const App = (() => {
  let DATA = null;
  let selectedPapers = new Map();
  let currentStep = 1;

  // ── Router ──────────────────────────────────────────────────

  const PAGES = ['landing', 'calculator', 'explorer', 'overview', 'methodology'];

  function navigate(page, pushState = true) {
    if (!PAGES.includes(page)) page = 'landing';

    document.querySelectorAll('.page-section').forEach(el => {
      el.style.display = el.dataset.page === page ? '' : 'none';
    });

    document.querySelectorAll('.nav-link').forEach(el => {
      el.classList.toggle('active', el.dataset.page === page);
    });

    if (pushState) {
      const hash = page === 'landing' ? '' : '#' + page;
      if (window.location.hash !== hash) {
        history.pushState(null, '', hash || window.location.pathname + window.location.search);
      }
    }

    if (page === 'explorer' && DATA) Explorer.init(DATA);
    if (page === 'overview' && DATA) Overview.init(DATA);

    window.scrollTo(0, 0);
  }

  function routeFromHash() {
    const hash = window.location.hash.replace('#', '');
    return PAGES.includes(hash) ? hash : 'landing';
  }

  // ── URL state ─────────────────────────────────────────────

  function saveStateToURL() {
    const params = new URLSearchParams();
    if (selectedPapers.size > 0) {
      params.set('papers', Array.from(selectedPapers.keys()).join('|'));
    }
    const ability = document.getElementById('ability-slider')?.value;
    if (ability && ability !== '50') {
      params.set('ability', ability);
    }
    const qs = params.toString();
    const newURL = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
    history.replaceState(null, '', newURL);
  }

  function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);

    const papersParam = params.get('papers');
    if (papersParam && DATA) {
      const names = papersParam.split('|');
      selectedPapers.clear();
      for (const name of names) {
        if (DATA.paper_catalogue[name] && selectedPapers.size < 8) {
          selectedPapers.set(name, DATA.paper_catalogue[name]);
        }
      }
      syncPickerToSelection();
    }

    const ability = params.get('ability');
    if (ability) {
      const slider = document.getElementById('ability-slider');
      slider.value = Math.max(5, Math.min(95, +ability));
      updateAbilityReadout();
    }

    if (selectedPapers.size === 8) {
      const page = routeFromHash();
      if (page === 'calculator') {
        goToStep(3);
      }
    }
  }

  function syncPickerToSelection() {
    document.querySelectorAll('.paper-item').forEach(el => {
      const name = el.dataset.name;
      const cb = el.querySelector('input');
      if (selectedPapers.has(name)) {
        cb.checked = true;
        el.classList.add('selected');
      } else {
        cb.checked = false;
        el.classList.remove('selected');
      }
    });
    updateSelectionCount();
  }

  // ── Bootstrap ─────────────────────────────────────────────

  async function init() {
    const resp = await fetch('data.json');
    DATA = await resp.json();
    drawHeroChart();
    buildPaperPicker();
    wireEvents();
    updateSelectionCount();
    loadStateFromURL();

    navigate(routeFromHash(), false);
  }

  function drawHeroChart() {
    const canvas = document.getElementById('hero-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = 320, h = 140;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const mu = 64, sigma = 8;
    const xMin = 35, xMax = 90;
    const points = [];
    for (let x = xMin; x <= xMax; x += 0.5) {
      const z = (x - mu) / sigma;
      const y = Math.exp(-0.5 * z * z);
      points.push([x, y]);
    }
    const maxY = 1;
    const px = x => ((x - xMin) / (xMax - xMin)) * (w - 40) + 20;
    const py = y => h - 20 - (y / maxY) * (h - 30);

    ctx.beginPath();
    ctx.moveTo(px(xMin), py(0));
    for (const [x, y] of points) ctx.lineTo(px(x), py(y));
    ctx.lineTo(px(xMax), py(0));
    ctx.closePath();
    ctx.fillStyle = 'rgba(91,155,245,0.08)';
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i < points.length; i++) {
      const [x, y] = points[i];
      if (i === 0) ctx.moveTo(px(x), py(y));
      else ctx.lineTo(px(x), py(y));
    }
    ctx.strokeStyle = 'rgba(232,229,220,0.6)';
    ctx.lineWidth = 2;
    ctx.stroke();

    const thresholds = [
      { x: 50, label: '50', color: 'rgba(232,97,77,0.5)' },
      { x: 60, label: '60', color: 'rgba(240,199,94,0.4)' },
      { x: 70, label: '70', color: 'rgba(91,155,245,0.5)' }
    ];
    for (const t of thresholds) {
      ctx.beginPath();
      ctx.moveTo(px(t.x), py(0));
      ctx.lineTo(px(t.x), py(0.85));
      ctx.strokeStyle = t.color;
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = t.color;
      ctx.font = '11px Inter, system-ui';
      ctx.textAlign = 'center';
      ctx.fillText(t.label, px(t.x), py(0) + 12);
    }
  }

  // ── Paper picker ──────────────────────────────────────────

  function difficultyBadge(paper) {
    const sigma = paper.sigma;
    if (sigma >= 10.2) return { label: 'Kingmaker', cls: 'badge-kingmaker' };
    if (sigma >= 7)    return { label: 'Hard', cls: 'badge-hard' };
    if (sigma >= 5)    return { label: 'Moderate', cls: 'badge-moderate' };
    return { label: 'Gentle', cls: 'badge-gentle' };
  }

  const BADGE_TOOLTIPS = {
    'badge-gentle': 'Gentle: σ < 5 — low variance, predictable outcomes',
    'badge-moderate': 'Moderate: σ 5–7 — typical spread',
    'badge-hard': 'Hard: σ 7–10 — wide spread, less predictable',
    'badge-kingmaker': 'Kingmaker: σ ≥ 10 — can swing your class either way'
  };

  function buildPaperPicker() {
    const container = document.getElementById('paper-lists');
    const subjects = ['Philosophy', 'Politics', 'Economics'];
    const catalogue = DATA.paper_catalogue;

    const sorted = {};
    for (const subj of subjects) {
      sorted[subj] = Object.entries(catalogue)
        .filter(([, p]) => p.subject === subj)
        .sort((a, b) => a[0].localeCompare(b[0]));
    }

    container.innerHTML = subjects.map(subj => {
      const papers = sorted[subj];
      return `
        <div class="subject-group" data-subject="${subj}">
          <h3>${subj} <span class="subject-count">(${papers.length})</span> <span class="subject-selected-count" data-subject="${subj}"></span></h3>
          ${papers.map(([name, p]) => {
            const badge = difficultyBadge(p);
            return `
              <label class="paper-item" data-name="${name}" data-subject="${subj}">
                <input type="checkbox">
                <span class="paper-name">${name}</span>
                <span class="paper-badge ${badge.cls}" title="${BADGE_TOOLTIPS[badge.cls]}">${badge.label}</span>
                <span class="paper-stats">μ${p.mu.toFixed(0)} σ${p.sigma.toFixed(1)}</span>
              </label>`;
          }).join('')}
        </div>`;
    }).join('');

    container.querySelectorAll('.paper-item input').forEach(cb => {
      cb.addEventListener('change', onPaperToggle);
    });
  }

  function onPaperToggle(e) {
    const label = e.target.closest('.paper-item');
    const name = label.dataset.name;
    const paper = DATA.paper_catalogue[name];

    if (e.target.checked) {
      if (selectedPapers.size >= 8) {
        e.target.checked = false;
        return;
      }
      selectedPapers.set(name, paper);
      label.classList.add('selected');
    } else {
      selectedPapers.delete(name);
      label.classList.remove('selected');
    }
    updateSelectionCount();
    saveStateToURL();
  }

  function updateSelectionCount() {
    document.getElementById('selected-count').textContent = selectedPapers.size;
    document.getElementById('btn-to-ability').disabled = selectedPapers.size !== 8;

    const counts = { Philosophy: 0, Politics: 0, Economics: 0 };
    for (const [, p] of selectedPapers) {
      counts[p.subject]++;
    }
    document.querySelectorAll('.subject-selected-count').forEach(el => {
      const subj = el.dataset.subject;
      el.textContent = counts[subj] > 0 ? `· ${counts[subj]} selected` : '';
    });

    renderSelectedSummary();
  }

  function renderSelectedSummary() {
    const el = document.getElementById('selected-summary');
    if (selectedPapers.size === 0) {
      el.innerHTML = '';
      return;
    }
    const items = Array.from(selectedPapers.entries()).map(([name, p]) => {
      const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';
      return `<span class="selected-chip"><span class="subject-dot subject-dot--${subjectCls}"></span>${name}</span>`;
    });
    el.innerHTML = `<div class="selected-chips">${items.join('')}</div>`;
  }

  function onSearch(e) {
    const q = e.target.value.toLowerCase().trim();
    document.querySelectorAll('.paper-item').forEach(el => {
      const name = el.dataset.name.toLowerCase();
      el.classList.toggle('hidden', q !== '' && !name.includes(q));
    });
  }

  // ── Step navigation ───────────────────────────────────────

  function goToStep(n) {
    currentStep = n;
    document.querySelectorAll('.step').forEach(el => {
      const s = +el.dataset.step;
      el.classList.toggle('active', s === n);
      el.classList.toggle('completed', s < n);
    });
    document.querySelectorAll('.step-section').forEach(el => {
      el.classList.remove('active-section');
    });
    const ids = { 1: 'step-papers', 2: 'step-ability', 3: 'step-results' };
    document.getElementById(ids[n]).classList.add('active-section');

    if (n === 3) runSimulation();
  }

  // ── Ability slider ────────────────────────────────────────

  function updateAbilityReadout() {
    const pct = +document.getElementById('ability-slider').value;
    document.getElementById('ability-pct').textContent = pct + 'th';
    const theta = Engine.norminv(pct / 100);
    const typicalSigma = 7;
    const shift = typicalSigma * Math.sqrt(DATA.rho) * theta;
    document.getElementById('ability-shift').textContent =
      (shift >= 0 ? '+' : '') + shift.toFixed(1);

    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.classList.toggle('active', +btn.dataset.pct === pct);
    });
    saveStateToURL();
  }

  // ── Simulation ────────────────────────────────────────────

  function runSimulation() {
    document.getElementById('result-headline').innerHTML =
      '<div class="range-text">Simulating…</div>';

    setTimeout(() => {
      const papers = Array.from(selectedPapers.entries()).map(([name, p]) => ({
        name, subject: p.subject, mu: p.mu, sigma: p.sigma
      }));
      const pct = +document.getElementById('ability-slider').value;
      const results = Engine.simulate(papers, DATA.rho, pct, 50000);
      renderResults(results, papers, pct);
    }, 16);
  }

  // ── Results rendering ─────────────────────────────────────

  const CLASS_COLORS = {
    '1st':  '#5b9bf5',
    '2.1':  '#e8e5dc',
    '2.2':  '#f0c75e',
    '3rd':  '#9a978e',
    'Pass': '#5e5c56',
    'Fail': '#3a3836'
  };

  const CLASS_ORDER = ['1st', '2.1', '2.2', '3rd', 'Pass', 'Fail'];

  function renderResults(results, papers, pct) {
    renderHeadline(results);
    renderDonut(results);
    renderPaperBreakdown(papers, pct);
    renderContext(results, papers);
  }

  function renderHeadline(results) {
    const el = document.getElementById('result-headline');
    const top = CLASS_ORDER.find(c => results[c] > 0.01) || '2.1';
    const pctVal = (results[top] * 100);
    const lo = Math.max(0, pctVal - 3).toFixed(0);
    const hi = Math.min(100, pctVal + 3).toFixed(0);

    const breakdown = CLASS_ORDER
      .filter(c => results[c] >= 0.001)
      .map(cls => {
        const p = (results[cls] * 100).toFixed(1);
        const style = cls === '1st' ? 'class-first' : cls === '2.1' ? 'class-21' : cls === '2.2' ? 'class-22' : 'class-low';
        return `<span class="headline-class ${style}">${cls}: ${p}%</span>`;
      }).join('');

    el.innerHTML = `
      <div class="big-number">~${lo}–${hi}% chance of a ${top}</div>
      <div class="headline-breakdown">${breakdown}</div>
      <div class="range-text">Based on historical priors for your paper choices · uncertainty roughly ±3pp</div>`;
  }

  function renderDonut(results) {
    const canvas = document.getElementById('result-chart');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const size = 260;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';

    const cx = size / 2, cy = size / 2, R = 110, r = 55;
    ctx.clearRect(0, 0, size, size);

    let angle = -Math.PI / 2;
    for (const cls of CLASS_ORDER) {
      const pct = results[cls];
      if (pct < 0.001) continue;
      const sweep = pct * 2 * Math.PI;
      ctx.beginPath();
      ctx.arc(cx, cy, R, angle, angle + sweep);
      ctx.arc(cx, cy, r, angle + sweep, angle, true);
      ctx.closePath();
      ctx.fillStyle = CLASS_COLORS[cls];
      ctx.fill();

      if (pct >= 0.04) {
        const mid = angle + sweep / 2;
        const lr = (R + r) / 2;
        const tx = cx + Math.cos(mid) * lr;
        const ty = cy + Math.sin(mid) * lr;
        ctx.fillStyle = '#1a1a1e';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(cls, tx, ty);
      }
      angle += sweep;
    }

    ctx.fillStyle = '#222228';
    ctx.beginPath();
    ctx.arc(cx, cy, r - 1, 0, 2 * Math.PI);
    ctx.fill();
  }

  function renderPaperBreakdown(papers, pct) {
    const el = document.getElementById('paper-breakdown');
    const metrics = Engine.paperMetrics(papers, DATA.rho, pct);

    const rows = metrics
      .sort((a, b) => b.pAbove70 - a.pAbove70)
      .map(m => {
        const subjectCls = m.subject === 'Philosophy' ? 'phil' : m.subject === 'Politics' ? 'pol' : 'econ';
        const barWidth = Math.max(0, Math.min(100, m.shiftedMu));
        const riskLabel = m.pBelow50 > 0.10 ? 'high risk'
                        : m.pBelow50 > 0.03 ? 'some risk' : '';
        const riskCls = m.pBelow50 > 0.10 ? 'risk-high'
                      : m.pBelow50 > 0.03 ? 'risk-some' : '';

        return `<tr>
          <td><span class="subject-dot subject-dot--${subjectCls}"></span>${m.name}</td>
          <td class="breakdown-mark">
            <div class="mark-bar-wrap">
              <div class="mark-bar" style="width:${barWidth}%"></div>
              <div class="mark-threshold" style="left:50%"></div>
              <div class="mark-threshold mark-threshold--first" style="left:70%"></div>
            </div>
            ~${m.shiftedMu.toFixed(0)}
          </td>
          <td>${riskLabel ? `<span class="risk-badge ${riskCls}">${riskLabel}</span>` : '—'}</td>
          <td>${(m.pAbove70 * 100).toFixed(0)}%</td>
          <td class="breakdown-sigma">σ = ${m.sigmaEps.toFixed(1)}</td>
        </tr>`;
      }).join('');

    el.innerHTML = `
      <h3>Paper-by-paper breakdown</h3>
      <p class="breakdown-note">Expected marks at your ability level · P(70+) is the chance of a First-class mark on each paper</p>
      <table class="breakdown-table">
        <thead><tr><th>Paper</th><th>Expected mark</th><th>Below-50 risk</th><th>P(70+)</th><th>Spread</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }

  function renderContext(results, papers) {
    const el = document.getElementById('context-panels');
    const panels = [];

    const route = Engine.detectRoute(papers);
    const routeData = DATA.route_summary[route];
    if (routeData) {
      panels.push(`
        <div class="context-card">
          <h3>Your route: ${route}</h3>
          <div class="context-value">${routeData['1st']}% Firsts historically</div>
          <div class="context-note">Historical average for all ${route} students</div>
        </div>`);
    }

    // What-if: compare to default papers at same ability
    const pct = +document.getElementById('ability-slider').value;
    const defaultPapers = DEFAULT_PAPERS
      .filter(name => DATA.paper_catalogue[name])
      .map(name => ({ name, subject: DATA.paper_catalogue[name].subject, mu: DATA.paper_catalogue[name].mu, sigma: DATA.paper_catalogue[name].sigma }));

    if (defaultPapers.length === 8) {
      const isDefault = DEFAULT_PAPERS.every(n => selectedPapers.has(n));
      if (!isDefault) {
        const defaultResults = Engine.simulate(defaultPapers, DATA.rho, pct, 20000);
        const diff = ((results['1st'] - defaultResults['1st']) * 100);
        const sign = diff >= 0 ? '+' : '';
        panels.push(`
          <div class="context-card">
            <h3>Compared to typical papers</h3>
            <div class="context-value">${sign}${diff.toFixed(1)}pp on First rate</div>
            <div class="context-note">Your papers vs the typical 8 (Micro, Macro, Ethics, IR, QE, BPG, K&R, Theory of Politics) at the same ability level</div>
          </div>`);
      }
    }

    const swap = findBestSwap(papers);
    if (swap) {
      panels.push(`
        <div class="context-card">
          <h3>Swap suggestion</h3>
          <div class="context-value">
            ${swap.out} <span class="swap-arrow">→</span> ${swap.in}
          </div>
          <div class="context-note">${swap.delta > 0 ? '+' : ''}${(swap.delta * 100).toFixed(1)}pp on First rate · small effect, not guaranteed</div>
        </div>`);
    }

    el.innerHTML = panels.join('');
  }

  function findBestSwap(papers) {
    const selectedNames = new Set(papers.map(p => p.name));
    const baseline = DATA.marginal_baseline.baseline_p_first;

    function marginalValue(name) {
      const d = DATA.paper_catalogue[name];
      return d.p_first_as_8th !== undefined ? d.p_first_as_8th : baseline;
    }

    let worstSelected = null;
    for (const p of papers) {
      const v = marginalValue(p.name);
      if (!worstSelected || v < worstSelected.value) {
        worstSelected = { name: p.name, value: v };
      }
    }

    let bestCandidate = null;
    for (const [name, data] of Object.entries(DATA.paper_catalogue)) {
      if (selectedNames.has(name)) continue;
      const remaining = papers.filter(p => p.name !== worstSelected.name);
      const subjects = new Set([...remaining.map(p => p.subject), data.subject]);
      if (subjects.size < 2) continue;
      const v = marginalValue(name);
      if (!bestCandidate || v > bestCandidate.value) {
        bestCandidate = { name, value: v };
      }
    }

    if (!worstSelected || !bestCandidate) return null;
    const delta = bestCandidate.value - worstSelected.value;
    if (delta <= 0.005) return null;
    return { out: worstSelected.name, in: bestCandidate.name, delta };
  }

  // ── Methodology modal ─────────────────────────────────────

  function openMethodologyModal() {
    document.getElementById('methodology-modal').style.display = 'flex';
  }

  function closeMethodologyModal() {
    document.getElementById('methodology-modal').style.display = 'none';
  }

  // ── Events ────────────────────────────────────────────────

  const DEFAULT_PAPERS = [
    'Microeconomics', 'Macroeconomics', 'Ethics',
    'International Relations', 'Quantitative Economics',
    'British Politics and Government since 1900',
    'Knowledge and Reality', 'Theory of Politics'
  ];

  function selectDefaults() {
    selectedPapers.clear();
    document.querySelectorAll('.paper-item').forEach(el => {
      el.classList.remove('selected');
      el.querySelector('input').checked = false;
    });
    for (const name of DEFAULT_PAPERS) {
      const paper = DATA.paper_catalogue[name];
      if (paper) {
        selectedPapers.set(name, paper);
        const el = document.querySelector(`.paper-item[data-name="${name}"]`);
        if (el) {
          el.classList.add('selected');
          el.querySelector('input').checked = true;
        }
      }
    }
    updateSelectionCount();
    saveStateToURL();
  }

  function wireEvents() {
    document.getElementById('paper-search').addEventListener('input', onSearch);
    document.getElementById('btn-defaults').addEventListener('click', selectDefaults);

    document.getElementById('btn-to-ability').addEventListener('click', () => goToStep(2));
    document.getElementById('btn-back-papers').addEventListener('click', () => goToStep(1));
    document.getElementById('btn-to-results').addEventListener('click', () => goToStep(3));
    document.getElementById('btn-back-ability').addEventListener('click', () => goToStep(2));
    document.getElementById('btn-restart').addEventListener('click', () => {
      selectedPapers.clear();
      document.querySelectorAll('.paper-item').forEach(el => {
        el.classList.remove('selected');
        el.querySelector('input').checked = false;
      });
      document.getElementById('ability-slider').value = 50;
      updateAbilityReadout();
      updateSelectionCount();
      saveStateToURL();
      goToStep(1);
    });

    document.querySelectorAll('.step').forEach(el => {
      el.addEventListener('click', () => {
        const s = +el.dataset.step;
        if (s < currentStep) goToStep(s);
        if (s === 2 && selectedPapers.size === 8) goToStep(2);
      });
    });

    const slider = document.getElementById('ability-slider');
    slider.addEventListener('input', updateAbilityReadout);

    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        slider.value = btn.dataset.pct;
        updateAbilityReadout();
      });
    });

    updateAbilityReadout();

    // Methodology modal
    document.getElementById('methodology-link').addEventListener('click', (e) => {
      e.preventDefault();
      openMethodologyModal();
    });

    document.getElementById('modal-close').addEventListener('click', closeMethodologyModal);

    document.getElementById('methodology-modal').addEventListener('click', (e) => {
      if (e.target === e.currentTarget) closeMethodologyModal();
    });

    document.getElementById('modal-to-full').addEventListener('click', () => {
      closeMethodologyModal();
    });

    // Hash routing
    window.addEventListener('hashchange', () => {
      navigate(routeFromHash(), false);
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMethodologyModal();
    });
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
