/**
 * PPE Finals — Grade Prior Calculator
 * Main application logic.
 */

const App = (() => {
  let DATA = null;
  let selectedPapers = new Map(); // name -> paper data
  let currentStep = 1;

  // ── Bootstrap ──────────────────────────────────────────────────

  async function init() {
    const resp = await fetch('data.json');
    DATA = await resp.json();
    buildPaperPicker();
    wireEvents();
    updateSelectionCount();
  }

  // ── Paper picker ───────────────────────────────────────────────

  function difficultyBadge(paper) {
    const sigma = paper.sigma;
    if (sigma >= 10.2) return { label: 'Kingmaker', cls: 'badge-kingmaker' };
    if (sigma >= 7)    return { label: 'Hard', cls: 'badge-hard' };
    if (sigma >= 5)    return { label: 'Moderate', cls: 'badge-moderate' };
    return { label: 'Gentle', cls: 'badge-gentle' };
  }

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
          <h3>${subj} (${papers.length})</h3>
          ${papers.map(([name, p]) => {
            const badge = difficultyBadge(p);
            return `
              <label class="paper-item" data-name="${name}" data-subject="${subj}">
                <input type="checkbox">
                <span class="paper-name">${name}</span>
                <span class="paper-badge ${badge.cls}">${badge.label}</span>
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
  }

  function updateSelectionCount() {
    document.getElementById('selected-count').textContent = selectedPapers.size;
    document.getElementById('btn-to-ability').disabled = selectedPapers.size !== 8;
  }

  // ── Search ─────────────────────────────────────────────────────

  function onSearch(e) {
    const q = e.target.value.toLowerCase().trim();
    document.querySelectorAll('.paper-item').forEach(el => {
      const name = el.dataset.name.toLowerCase();
      el.classList.toggle('hidden', q !== '' && !name.includes(q));
    });
  }

  // ── Step navigation ────────────────────────────────────────────

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

  // ── Ability slider ─────────────────────────────────────────────

  function updateAbilityReadout() {
    const pct = +document.getElementById('ability-slider').value;
    document.getElementById('ability-pct').textContent = pct + 'th';
    const shift = Engine.norminv(pct / 100) * DATA.sigma_ability;
    document.getElementById('ability-shift').textContent =
      (shift >= 0 ? '+' : '') + shift.toFixed(1);

    document.querySelectorAll('.preset-btn').forEach(btn => {
      btn.classList.toggle('active', +btn.dataset.pct === pct);
    });
  }

  // ── Simulation ─────────────────────────────────────────────────

  function runSimulation() {
    const papers = Array.from(selectedPapers.entries()).map(([name, p]) => ({
      name, subject: p.subject, mu: p.mu, sigma: p.sigma
    }));
    const pct = +document.getElementById('ability-slider').value;
    const results = Engine.simulate(papers, DATA.sigma_ability, pct, 100000);
    renderResults(results, papers);
  }

  // ── Results rendering ──────────────────────────────────────────

  const CLASS_COLORS = {
    '1st':  '#9BE564',
    '2.1':  '#7FA7FF',
    '2.2':  '#F2C14E',
    '3rd':  '#CFC8B8',
    'Pass': '#8F8A7C',
    'Fail': '#5A564C'
  };

  const CLASS_ORDER = ['1st', '2.1', '2.2', '3rd', 'Pass', 'Fail'];

  function renderResults(results, papers) {
    renderHeadline(results);
    renderDonut(results);
    renderTable(results);
    renderContext(results, papers);
  }

  function renderHeadline(results) {
    const el = document.getElementById('result-headline');
    const top = CLASS_ORDER.find(c => results[c] > 0.01) || '2.1';
    const pct = (results[top] * 100);
    const lo = Math.max(0, pct - 3).toFixed(0);
    const hi = Math.min(100, pct + 3).toFixed(0);
    el.innerHTML = `
      <div class="big-number">~${lo}–${hi}% chance of a ${top}</div>
      <div class="range-text">Based on historical priors for your paper choices · uncertainty roughly ±3pp</div>`;
  }

  function renderDonut(results) {
    const canvas = document.getElementById('result-chart');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    canvas.width = 300 * dpr;
    canvas.height = 300 * dpr;
    ctx.scale(dpr, dpr);
    canvas.style.width = '300px';
    canvas.style.height = '300px';

    const cx = 150, cy = 150, R = 120, r = 65;
    ctx.clearRect(0, 0, 300, 300);

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
        ctx.fillStyle = '#0F2A1F';
        ctx.font = 'bold 13px Inter, system-ui, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(cls, tx, ty);
      }
      angle += sweep;
    }

    ctx.fillStyle = '#133526';
    ctx.beginPath();
    ctx.arc(cx, cy, r - 1, 0, 2 * Math.PI);
    ctx.fill();
  }

  function renderTable(results) {
    const el = document.getElementById('result-table');
    const classStyle = cls => {
      if (cls === '1st') return 'class-first';
      if (cls === '2.1') return 'class-21';
      if (cls === '2.2') return 'class-22';
      return 'class-low';
    };

    const rows = CLASS_ORDER.filter(c => results[c] >= 0.001).map(cls => {
      const pct = results[cls] * 100;
      return `<tr>
        <td class="${classStyle(cls)}">${cls}</td>
        <td>${pct.toFixed(1)}%</td>
        <td>${Math.max(0, pct - 3).toFixed(0)}–${Math.min(100, pct + 3).toFixed(0)}%</td>
      </tr>`;
    }).join('');

    el.innerHTML = `<table>
      <thead><tr><th>Class</th><th>Estimate</th><th>Range (±3pp)</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  function renderContext(results, papers) {
    const el = document.getElementById('context-panels');
    const panels = [];

    // Route detection
    const route = Engine.detectRoute(papers);
    const routeData = DATA.route_summary[route];
    if (routeData) {
      panels.push(`
        <div class="context-card">
          <h3>Your route: ${route}</h3>
          <div class="context-value">${routeData['1st']}% Firsts historically</div>
          <div class="context-note">vs your estimated ${(results['1st'] * 100).toFixed(0)}% — ${
            results['1st'] * 100 > routeData['1st'] ? 'above' : 'below'
          } the route average</div>
        </div>`);
    }

    // Best swap suggestion
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

  // ── Events ─────────────────────────────────────────────────────

  function wireEvents() {
    document.getElementById('paper-search').addEventListener('input', onSearch);

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
  }

  // ── Public ─────────────────────────────────────────────────────

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
