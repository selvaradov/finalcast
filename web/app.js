const App = (() => {
  let DATA = null;
  let selectedPapers = new Map();
  let currentStep = 1;
  let restoringState = false;

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
      const keepParams = page === 'calculator';
      const search = keepParams ? window.location.search : '';
      const url = window.location.pathname + search + (hash || '');
      if (window.location.hash !== hash || (!keepParams && window.location.search)) {
        history.pushState(null, '', url);
      }
    }

    if (page === 'explorer' && DATA) Explorer.init(DATA);
    if (page === 'overview' && DATA) Overview.init(DATA);
    if (page === 'methodology') wireMethodologyToc();

    window.scrollTo(0, 0);
  }

  function routeFromHash() {
    const hash = window.location.hash.replace('#', '');
    return PAGES.includes(hash) ? hash : 'landing';
  }

  // ── URL state ─────────────────────────────────────────────

  function saveStateToURL() {
    if (restoringState) return;
    const params = new URLSearchParams();
    if (selectedPapers.size > 0) {
      params.set('papers', Array.from(selectedPapers.keys()).join('|'));
    }
    const ability = document.getElementById('ability-slider')?.value;
    if (ability && ability !== '50') {
      params.set('ability', ability);
    }
    if (currentStep > 1) {
      params.set('step', currentStep);
    }
    // Persist what-if fixed marks
    const fixedRows = document.querySelectorAll('.whatif-row.fixed');
    if (fixedRows.length > 0) {
      const papers = Array.from(selectedPapers.keys());
      const parts = [];
      fixedRows.forEach(row => {
        const idx = +row.dataset.idx;
        const mark = row.querySelector('.whatif-mark-input').value.trim();
        if (mark && papers[idx]) {
          parts.push(papers[idx] + ':' + mark);
        }
      });
      if (parts.length > 0) {
        params.set('whatif', parts.join('|'));
      }
    }
    const qs = params.toString();
    const newURL = window.location.pathname + (qs ? '?' + qs : '') + window.location.hash;
    history.replaceState(null, '', newURL);
  }

  function loadStateFromURL() {
    restoringState = true;
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

    const step = +(params.get('step') || 0);
    const whatifParam = params.get('whatif');

    restoringState = false;

    if (selectedPapers.size === 8 && step >= 2) {
      const page = routeFromHash();
      if (page !== 'calculator') {
        navigate('calculator', true);
      }
      if (step === 4) {
        goToStep(4);
        if (whatifParam) {
          restoreWhatIfMarks(whatifParam);
          runWhatIfSimulation();
        }
      } else {
        goToStep(step);
      }
    }
  }

  function restoreWhatIfMarks(whatifParam) {
    const papers = Array.from(selectedPapers.keys());
    const entries = whatifParam.split('|');
    for (const entry of entries) {
      const colonIdx = entry.lastIndexOf(':');
      if (colonIdx === -1) continue;
      const name = entry.slice(0, colonIdx);
      const mark = entry.slice(colonIdx + 1);
      const idx = papers.indexOf(name);
      if (idx === -1 || isNaN(+mark)) continue;

      const row = document.querySelector(`.whatif-row[data-idx="${idx}"]`);
      if (!row) continue;
      const input = row.querySelector('.whatif-mark-input');
      input.value = mark;
      row.classList.add('fixed');
      row.querySelector('.whatif-lock-icon').textContent = '\u{1F512}';
      updateMarkStatus(idx);
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
    restoringState = true;
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
    // Canvas is larger than the border box — extra bleed for particles
    const bleed = 24;
    const innerW = 360, innerH = 180;
    const w = innerW + bleed * 2, h = innerH + bleed * 2;
    const backingW = Math.max(1, Math.round(w * dpr));
    const backingH = Math.max(1, Math.round(h * dpr));
    canvas.width = backingW;
    canvas.height = backingH;
    ctx.setTransform(backingW / w, 0, 0, backingH / h, 0, 0);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';

    const mu = 64, sigma = 8;
    const xMin = 42, xMax = 86;
    const baseline = bleed + innerH - 28;
    const topPad = bleed + 20;
    const pad = bleed + 20;
    const plotW = innerW - 40;
    const px = x => pad + ((x - xMin) / (xMax - xMin)) * plotW;
    const maxDeform = 2;
    const py = y => baseline - Math.min(y, maxDeform) * (baseline - topPad);

    function gauss(x) {
      const z = (x - mu) / sigma;
      return Math.exp(-0.5 * z * z);
    }

    // Displacement array — spring physics
    const N = 120;
    const xs = [];
    for (let i = 0; i < N; i++) xs.push(xMin + (xMax - xMin) * i / (N - 1));
    const displacement = new Float64Array(N);
    const velocity = new Float64Array(N);
    const stiffness = 0.14;
    const damping = 0.72;

    let mouseX = -1, mouseY = -1;
    let mouseDown = false;
    let animating = false;

    // Chalk dust particles
    const particles = [];
    const MAX_PARTICLES = 60;

    function spawnDust(cx, cy, amount) {
      for (let i = 0; i < amount; i++) {
        if (particles.length >= MAX_PARTICLES) particles.shift();
        particles.push({
          x: cx + (Math.random() - 0.5) * 12,
          y: cy + (Math.random() - 0.5) * 8,
          vx: (Math.random() - 0.5) * 1.5,
          vy: -Math.random() * 1.2 - 0.3,
          life: 1.0,
          size: Math.random() * 2 + 0.5
        });
      }
    }

    function getDeformedY(i) {
      const baseY = gauss(xs[i]);
      return Math.max(0, baseY + displacement[i]);
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);

      // Filled area under curve, split by class bands
      const bands = [
        { from: xMin, to: 50, color: 'rgba(232,97,77,0.06)' },
        { from: 50, to: 60, color: 'rgba(240,199,94,0.06)' },
        { from: 60, to: 70, color: 'rgba(232,229,220,0.05)' },
        { from: 70, to: xMax, color: 'rgba(91,155,245,0.08)' }
      ];
      for (const band of bands) {
        ctx.beginPath();
        ctx.moveTo(px(band.from), py(0));
        for (let i = 0; i < N; i++) {
          if (xs[i] < band.from) continue;
          if (xs[i] > band.to) break;
          ctx.lineTo(px(xs[i]), py(getDeformedY(i)));
        }
        ctx.lineTo(px(band.to), py(0));
        ctx.closePath();
        ctx.fillStyle = band.color;
        ctx.fill();
      }

      // Curve stroke
      ctx.beginPath();
      for (let i = 0; i < N; i++) {
        const x = px(xs[i]), y = py(getDeformedY(i));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = 'rgba(232,229,220,0.7)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Threshold lines — from baseline up to the curve
      const thresholds = [
        { x: 50, color: 'rgba(232,97,77,0.4)' },
        { x: 60, color: 'rgba(240,199,94,0.3)' },
        { x: 70, color: 'rgba(91,155,245,0.45)' }
      ];
      for (const t of thresholds) {
        const i = Math.round((t.x - xMin) / (xMax - xMin) * (N - 1));
        const curveY = py(getDeformedY(i));
        ctx.beginPath();
        ctx.moveTo(px(t.x), py(0));
        ctx.lineTo(px(t.x), curveY);
        ctx.strokeStyle = t.color;
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Class labels — centered between thresholds, below baseline
      const labels = [
        { text: '3rd', from: xMin, to: 50, color: 'rgba(232,97,77,0.5)' },
        { text: '2.2', from: 50, to: 60, color: 'rgba(240,199,94,0.5)' },
        { text: '2.1', from: 60, to: 70, color: 'rgba(232,229,220,0.5)' },
        { text: '1st', from: 70, to: xMax, color: 'rgba(91,155,245,0.6)' }
      ];
      ctx.font = '14px Caveat, cursive';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      for (const l of labels) {
        const cx = px((l.from + l.to) / 2);
        ctx.fillStyle = l.color;
        ctx.fillText(l.text, cx, baseline + 5);
      }

      // Chalk dust — fuzzy particles
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        const r = p.size * 2.5;
        const alpha = p.life * 0.5;
        if (alpha < 0.001) continue;
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
        grad.addColorStop(0, `rgba(232,229,220,${alpha})`);
        grad.addColorStop(0.4, `rgba(232,229,220,${alpha * 0.5})`);
        grad.addColorStop(1, 'rgba(232,229,220,0)');
        ctx.fillStyle = grad;
        ctx.fillRect(p.x - r, p.y - r, r * 2, r * 2);
      }

      // Custom cursor — small chalk dot
      if (mouseX >= 0) {
        const cr = 4;
        const cgrad = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, cr);
        cgrad.addColorStop(0, 'rgba(232,229,220,0.8)');
        cgrad.addColorStop(0.5, 'rgba(232,229,220,0.3)');
        cgrad.addColorStop(1, 'rgba(232,229,220,0)');
        ctx.fillStyle = cgrad;
        ctx.fillRect(mouseX - cr, mouseY - cr, cr * 2, cr * 2);
      }
    }

    function physics() {
      const influence = mouseDown ? 120 : 90;
      const strength = mouseDown ? 0.8 : 0.5;

      let totalDisturb = 0;
      for (let i = 0; i < N; i++) {
        let target = 0;
        if (mouseX >= 0) {
          const ptX = px(xs[i]);
          const ptY = py(gauss(xs[i]));
          const dx = ptX - mouseX;
          const dy = ptY - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < influence) {
            const factor = (1 - dist / influence);
            const pull = (mouseY - ptY) / (baseline - topPad);
            target = pull * factor * factor * strength;
          }
        }
        const force = -stiffness * (displacement[i] - target);
        velocity[i] = (velocity[i] + force) * damping;
        displacement[i] += velocity[i];
        totalDisturb += Math.abs(velocity[i]);
      }

      // Spawn dust where the curve is being disturbed most
      if (mouseX >= 0 && totalDisturb > 0.02) {
        const closestI = Math.round((mouseX - pad) / plotW * (N - 1));
        if (closestI >= 0 && closestI < N) {
          const cy = py(getDeformedY(Math.max(0, Math.min(N - 1, closestI))));
          spawnDust(mouseX, cy, mouseDown ? 3 : 1);
        }
      }

      // Update particles
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.04;
        p.life -= 0.02;
        if (p.life <= 0) particles.splice(i, 1);
      }
    }

    function tick() {
      physics();
      draw();
      const moving = displacement.some((d, i) => Math.abs(d) > 0.0005 || Math.abs(velocity[i]) > 0.0005);
      if (moving || mouseX >= 0 || particles.length > 0) {
        animating = true;
        requestAnimationFrame(tick);
      } else {
        animating = false;
      }
    }

    function startAnim() {
      if (!animating) {
        animating = true;
        requestAnimationFrame(tick);
      }
    }

    canvas.addEventListener('mousemove', e => {
      const rect = canvas.getBoundingClientRect();
      mouseX = (e.clientX - rect.left) * (w / rect.width);
      mouseY = (e.clientY - rect.top) * (h / rect.height);
      startAnim();
    });

    canvas.addEventListener('mousedown', () => { mouseDown = true; });
    canvas.addEventListener('mouseup', () => { mouseDown = false; });

    canvas.addEventListener('mouseleave', () => {
      mouseX = -1;
      mouseY = -1;
      mouseDown = false;
      startAnim();
    });

    canvas.addEventListener('touchmove', e => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const touch = e.touches[0];
      mouseX = (touch.clientX - rect.left) * (w / rect.width);
      mouseY = (touch.clientY - rect.top) * (h / rect.height);
      mouseDown = true;
      startAnim();
    }, { passive: false });

    canvas.addEventListener('touchend', () => {
      mouseX = -1;
      mouseY = -1;
      mouseDown = false;
      startAnim();
    });

    draw();

    // Page-load flourish: up, down below, settle — 2 cycles then done
    setTimeout(() => {
      let t = 0;
      const totalFrames = 90;
      const amp = 0.15;
      function flourishTick() {
        t++;
        if (t > totalFrames) {
          for (let i = 0; i < N; i++) displacement[i] = 0;
          draw();
          return;
        }
        const progress = t / totalFrames;
        const envelope = amp * (1 - progress) * (1 - progress);
        const wave = Math.sin(progress * Math.PI * 4);
        for (let i = 0; i < N; i++) {
          const center = N / 2;
          const dist = (i - center) / (N / 2);
          const shape = Math.exp(-dist * dist * 3);
          displacement[i] = wave * envelope * shape;
        }
        if (t === 8) spawnDust(px(mu), py(getDeformedY(Math.round(N / 2))), 2);
        if (t === 30) spawnDust(px(mu), py(getDeformedY(Math.round(N / 2))), 2);
        physics();
        draw();
        requestAnimationFrame(flourishTick);
      }
      flourishTick();
    }, 800);
  }

  // ── Paper picker ──────────────────────────────────────────

  function difficultyBadge(paper) {
    const sigma = paper.sigma;
    if (sigma >= 10.2) return { label: 'Kingmaker', cls: 'badge-kingmaker' };
    if (sigma >= 7)    return { label: 'Volatile', cls: 'badge-volatile' };
    if (sigma >= 5)    return { label: 'Moderate', cls: 'badge-moderate' };
    return { label: 'Predictable', cls: 'badge-predictable' };
  }

  const BADGE_TOOLTIPS = {
    'badge-predictable': 'Predictable: σ < 5 — tight spread, outcomes cluster near the mean',
    'badge-moderate': 'Moderate: σ 5–7 — typical spread',
    'badge-volatile': 'Volatile: σ 7–10 — wide spread, harder to predict your mark',
    'badge-kingmaker': 'Kingmaker: σ ≥ 10 — can swing your class up or down'
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
    const ids = { 1: 'step-papers', 2: 'step-ability', 3: 'step-results', 4: 'step-whatif' };
    document.getElementById(ids[n]).classList.add('active-section');

    if (n === 3) runSimulation();
    if (n === 4) initWhatIf();
    saveStateToURL();
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
    document.body.style.cursor = 'wait';

    setTimeout(() => {
      const papers = Array.from(selectedPapers.entries()).map(([name, p]) => ({
        name, subject: p.subject, mu: p.mu, sigma: p.sigma
      }));
      const pct = +document.getElementById('ability-slider').value;
      const results = Engine.simulate(papers, DATA.rho, pct, 50000);
      renderResults(results, papers, pct);
      document.body.style.cursor = '';
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
    const pctVal = Math.round(results[top] * 100);

    const breakdown = CLASS_ORDER
      .filter(c => results[c] >= 0.001)
      .map(cls => {
        const p = (results[cls] * 100).toFixed(1);
        const style = cls === '1st' ? 'class-first' : cls === '2.1' ? 'class-21' : cls === '2.2' ? 'class-22' : 'class-low';
        return `<span class="headline-class ${style}">${cls}: ${p}%</span>`;
      }).join('');

    el.innerHTML = `
      <div class="big-number">~${pctVal}% chance of a ${top}</div>
      <div class="headline-breakdown">${breakdown}</div>
      <div class="range-text">Uncertainty ±3pp · based on model limitations (distributional assumptions, single ability factor, selection effects)</div>`;
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

  // ── What-if: conditional marks ─────────────────────────────

  let lastUnconditionalResults = null;

  function initWhatIf() {
    const container = document.getElementById('whatif-papers');
    const papers = Array.from(selectedPapers.entries());
    const pct = +document.getElementById('ability-slider').value;

    container.innerHTML = papers.map(([name, p], idx) => {
      const metrics = Engine.paperMetrics([{ name, subject: p.subject, mu: p.mu, sigma: p.sigma }], DATA.rho, pct);
      const expectedMark = Math.round(metrics[0].shiftedMu);
      const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';
      return `
        <div class="whatif-row" data-idx="${idx}" data-expected="${expectedMark}">
          <span class="whatif-paper-name"><span class="subject-dot subject-dot--${subjectCls}"></span>${name}</span>
          <div class="whatif-input-group">
            <span class="whatif-lock-icon" data-idx="${idx}"></span>
            <input type="text" class="whatif-mark-input" data-idx="${idx}" value="" placeholder="${expectedMark}">
            <button class="whatif-clear-btn" data-idx="${idx}" title="Clear — return to simulated">&#xd7;</button>
          </div>
          <span class="whatif-status" data-idx="${idx}"><span class="whatif-status-sim">simulated each draw</span></span>
        </div>`;
    }).join('');

    container.querySelectorAll('.whatif-mark-input').forEach(input => {
      input.addEventListener('input', onWhatIfMarkChange);
      input.addEventListener('focus', onWhatIfFocus);
    });
    container.querySelectorAll('.whatif-clear-btn').forEach(btn => {
      btn.addEventListener('click', onWhatIfClear);
    });

    document.getElementById('whatif-results').style.display = 'none';
    document.getElementById('whatif-papers').style.display = '';
    document.getElementById('whatif-subheader').style.display = '';
    document.getElementById('whatif-result-subheader').style.display = 'none';
    document.getElementById('whatif-heading').textContent = 'What do you need?';
  }

  function onWhatIfFocus(e) {
    const row = e.target.closest('.whatif-row');
    if (!row.classList.contains('fixed')) {
      e.target.select();
    }
  }

  function onWhatIfClear(e) {
    const idx = +e.target.dataset.idx;
    const row = document.querySelector(`.whatif-row[data-idx="${idx}"]`);
    const input = row.querySelector('.whatif-mark-input');
    input.value = '';
    row.classList.remove('fixed');
    const statusEl = row.querySelector('.whatif-status');
    statusEl.innerHTML = '<span class="whatif-status-sim">simulated each draw</span>';
    row.querySelector('.whatif-lock-icon').textContent = '';
    saveStateToURL();
  }

  function onWhatIfMarkChange(e) {
    const idx = +e.target.dataset.idx;
    const row = e.target.closest('.whatif-row');
    const val = e.target.value.trim();

    if (val === '') {
      row.classList.remove('fixed');
      const statusEl = row.querySelector('.whatif-status');
      statusEl.innerHTML = '<span class="whatif-status-sim">simulated each draw</span>';
      row.querySelector('.whatif-lock-icon').textContent = '';
      saveStateToURL();
      return;
    }

    const fixedCount = document.querySelectorAll('.whatif-row.fixed').length;
    if (!row.classList.contains('fixed') && fixedCount >= 7) {
      e.target.value = '';
      return;
    }

    row.classList.add('fixed');
    row.querySelector('.whatif-lock-icon').textContent = '\u{1F512}';
    updateMarkStatus(idx);
    saveStateToURL();
  }

  function updateMarkStatus(idx) {
    const papers = Array.from(selectedPapers.entries());
    const [, p] = papers[idx];
    const input = document.querySelector(`.whatif-mark-input[data-idx="${idx}"]`);
    const statusEl = document.querySelector(`.whatif-status[data-idx="${idx}"]`);
    const mark = +input.value;
    const pct = +document.getElementById('ability-slider').value;

    if (isNaN(mark) || mark < 0 || mark > 100) {
      statusEl.innerHTML = '';
      return;
    }

    const ctx = Engine.markContext(mark, p.mu, p.sigma, DATA.rho, pct);
    const labelCls = 'whatif-status--' + ctx.label.replace(/\s+/g, '-');
    statusEl.innerHTML = `<span class="whatif-status-pctile">${ctx.percentile}th %ile</span><br><span class="whatif-status-label ${labelCls}">${ctx.label}</span>`;
  }

  function runWhatIfSimulation() {
    const papers = Array.from(selectedPapers.entries()).map(([name, p]) => ({
      name, subject: p.subject, mu: p.mu, sigma: p.sigma
    }));
    const pct = +document.getElementById('ability-slider').value;

    const fixedMarks = new Map();
    document.querySelectorAll('.whatif-row.fixed').forEach(row => {
      const idx = +row.dataset.idx;
      const mark = +row.querySelector('.whatif-mark-input').value;
      if (!isNaN(mark) && mark >= 0 && mark <= 100) {
        fixedMarks.set(idx, mark);
      }
    });

    if (fixedMarks.size === 0) {
      document.getElementById('whatif-results').innerHTML =
        '<p class="whatif-hint">Enter a mark on at least one paper to see conditional results.</p>';
      document.getElementById('whatif-results').style.display = '';
      return;
    }

    document.body.style.cursor = 'wait';

    setTimeout(() => {
      const { distribution } = Engine.simulateConditional(papers, fixedMarks, DATA.rho, pct, 50000);
      const threshold = Engine.findThreshold(papers, fixedMarks, DATA.rho, "1st", 0.5, 12000);

      const freeIndices = [];
      for (let i = 0; i < papers.length; i++) {
        if (!fixedMarks.has(i)) freeIndices.push(i);
      }

      const resultsEl = document.getElementById('whatif-results');
      renderWhatIfResults(distribution, threshold, papers, fixedMarks, freeIndices, pct);
      showWhatIfResultsMode(threshold, distribution, freeIndices.length);
      resultsEl.style.display = '';
      document.body.style.cursor = '';
      saveStateToURL();
    }, 16);
  }

  function showWhatIfResultsMode(threshold, distribution, freeCount) {
    document.getElementById('whatif-papers').style.display = 'none';
    document.getElementById('whatif-subheader').style.display = 'none';
    document.getElementById('whatif-result-subheader').style.display = '';

    const heading = document.getElementById('whatif-heading');
    const explanation = document.getElementById('whatif-explanation');

    if (threshold !== null) {
      heading.textContent = `You'd need the ~${threshold}th percentile`;
      explanation.textContent = `To have a ≥50% chance of a First, assuming the same performance level across your ${freeCount} free papers, given the marks you entered.`;
    } else if (distribution['1st'] < 0.01) {
      heading.textContent = 'A First looks unlikely';
      explanation.textContent = `With these fixed marks, even the 95th percentile on remaining papers doesn't give a ≥50% chance of a First.`;
    } else {
      const top = CLASS_ORDER.find(c => distribution[c] > 0.01) || '2.1';
      heading.textContent = `~${Math.round(distribution[top] * 100)}% chance of a ${top}`;
      explanation.textContent = `With the marks you've entered held fixed and remaining papers simulated at the selected percentile.`;
    }
  }

  function showWhatIfInputMode() {
    document.getElementById('whatif-papers').style.display = '';
    document.getElementById('whatif-subheader').style.display = '';
    document.getElementById('whatif-result-subheader').style.display = 'none';
    document.getElementById('whatif-results').style.display = 'none';
    document.getElementById('whatif-heading').textContent = 'What do you need?';
    saveStateToURL();
  }

  function renderWhatIfResults(distribution, threshold, papers, fixedMarks, freeIndices, pct) {
    const el = document.getElementById('whatif-results');

    const CLASS_ORDER_LOCAL = ['1st', '2.1', '2.2', '3rd', 'Pass', 'Fail'];
    const breakdown = CLASS_ORDER_LOCAL
      .filter(c => distribution[c] >= 0.001)
      .map(cls => {
        const p = (distribution[cls] * 100).toFixed(1);
        const style = cls === '1st' ? 'class-first' : cls === '2.1' ? 'class-21' : cls === '2.2' ? 'class-22' : 'class-low';
        return `<span class="headline-class ${style}">${cls}: ${p}%</span>`;
      }).join('');

    const top = CLASS_ORDER_LOCAL.find(c => distribution[c] > 0.01) || '2.1';
    const pctVal = Math.round(distribution[top] * 100);

    const theta = Engine.norminv(pct / 100);
    const sqrtRho = Math.sqrt(DATA.rho);

    let thresholdTheta = null;
    if (threshold !== null) {
      thresholdTheta = Engine.norminv(threshold / 100);
    }

    // Classification breakdown card
    let classificationHtml = `
      <div class="whatif-secondary">
        <h3>Classification probabilities at the ${pct}th percentile</h3>
        <div class="headline-breakdown">${breakdown}</div>
        <p class="whatif-secondary-note">Holding your entered marks fixed and simulating the rest at your selected ability level, the model assigns these probabilities to each classification. Estimates are approximate (±3pp from model limitations).</p>
      </div>`;

    // Build results table
    const tableRows = papers.map((p, i) => {
      const subjectCls = p.subject === 'Philosophy' ? 'phil' : p.subject === 'Politics' ? 'pol' : 'econ';
      const isFixed = fixedMarks.has(i);

      let markCol = '';
      let neededCol = '';

      if (isFixed) {
        const mark = fixedMarks.get(i);
        const ctx = Engine.markContext(mark, p.mu, p.sigma, DATA.rho, pct);
        markCol = `${mark} <span class="whatif-table-note">(fixed, ${ctx.percentile}th %ile)</span>`;
        neededCol = '—';
      } else {
        const currentMark = Math.round(p.mu + p.sigma * sqrtRho * theta);
        markCol = `~${currentMark}`;
        if (thresholdTheta !== null) {
          neededCol = '~' + Math.round(p.mu + p.sigma * sqrtRho * thresholdTheta);
        } else {
          neededCol = '—';
        }
      }

      return `<tr class="${isFixed ? 'whatif-table-fixed' : ''}">
        <td><span class="subject-dot subject-dot--${subjectCls}"></span>${p.name}</td>
        <td class="whatif-table-mark">${markCol}</td>
        <td class="whatif-table-mark">${neededCol}</td>
      </tr>`;
    }).join('');

    el.innerHTML = `
      ${classificationHtml}
      <table class="whatif-table">
        <thead><tr>
          <th>Paper</th>
          <th>At selected percentile (${pct}th)</th>
          <th>${threshold !== null ? `Needed for First (${threshold}th %ile)` : 'Needed for First'}</th>
        </tr></thead>
        <tbody>${tableRows}</tbody>
      </table>
    `;
  }

  // ── Methodology TOC ────────────────────────────────────────

  let methTocWired = false;

  function wireMethodologyToc() {
    if (methTocWired) return;
    methTocWired = true;
    Overview.wireTocNav('.methodology-toc');
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
    document.getElementById('btn-whatif').addEventListener('click', () => goToStep(4));
    document.getElementById('btn-back-results').addEventListener('click', () => goToStep(3));
    document.getElementById('btn-whatif-run').addEventListener('click', runWhatIfSimulation);
    document.getElementById('btn-whatif-back-input').addEventListener('click', showWhatIfInputMode);
    document.getElementById('btn-restart-2').addEventListener('click', () => {
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
    document.getElementById('btn-restart-3').addEventListener('click', () => {
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
      const page = routeFromHash();
      if (page !== 'calculator' && window.location.search) {
        history.replaceState(null, '', window.location.pathname + window.location.hash);
      }
      navigate(page, false);
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeMethodologyModal();
    });
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
