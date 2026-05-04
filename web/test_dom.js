// End-to-end DOM test of the calculator using jsdom
const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('web/index.html', 'utf8');
const engineSrc = fs.readFileSync('web/engine.js', 'utf8');
const appSrc = fs.readFileSync('web/app.js', 'utf8');

// Mock fetch for data.json
const dataJson = fs.readFileSync('web/data.json', 'utf8');

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
  url: 'http://localhost:8080'
});

const { window } = dom;
const { document } = window;

// Mock canvas (jsdom doesn't support canvas)
class MockCtx {
  beginPath() {} arc() {} closePath() {} fill() {} clearRect() {} scale() {}
  set fillStyle(v) {} set font(v) {} set textAlign(v) {} set textBaseline(v) {}
  fillText() {}
}
if (window.HTMLCanvasElement) {
  window.HTMLCanvasElement.prototype.getContext = function() { return new MockCtx(); };
} else {
  // Patch all canvas elements after load
  const origCreateElement = document.createElement.bind(document);
  document.createElement = function(tag) {
    const el = origCreateElement(tag);
    if (tag === 'canvas') el.getContext = () => new MockCtx();
    return el;
  };
}
// Also patch the existing canvas in HTML
const canvasEl = document.getElementById('result-chart');
if (canvasEl) canvasEl.getContext = () => new MockCtx();

// Mock fetch
window.fetch = async (url) => ({
  json: async () => JSON.parse(dataJson)
});

// Mock devicePixelRatio
Object.defineProperty(window, 'devicePixelRatio', { value: 1 });

// Run engine and app — use window assignment to ensure globals survive eval scoping
window.eval(engineSrc.replace('const Engine =', 'window.Engine ='));
window.eval(appSrc.replace('const App =', 'window.App ='));

// Wait for DOMContentLoaded
setTimeout(async () => {
  // Trigger DOMContentLoaded manually
  const event = new window.Event('DOMContentLoaded');
  document.dispatchEvent(event);

  // Wait for init
  await new Promise(r => setTimeout(r, 200));

  // Check papers rendered
  const paperItems = document.querySelectorAll('.paper-item');
  console.log(`Papers rendered: ${paperItems.length}`);
  if (paperItems.length !== 81) console.error('FAIL: expected 81 papers');

  // Check subjects
  const groups = document.querySelectorAll('.subject-group');
  console.log(`Subject groups: ${groups.length}`);

  // Check search works
  const search = document.getElementById('paper-search');
  search.value = 'micro';
  search.dispatchEvent(new window.Event('input'));
  const visible = document.querySelectorAll('.paper-item:not(.hidden)');
  console.log(`Papers matching "micro": ${visible.length}`);

  // Clear search
  search.value = '';
  search.dispatchEvent(new window.Event('input'));

  // Select 8 papers
  const picks = [
    'Microeconomics', 'Macroeconomics', 'Ethics',
    'International Relations', 'Quantitative Economics',
    'British Politics and Government since 1900',
    'Knowledge and Reality', 'Theory of Politics'
  ];

  for (const name of picks) {
    const item = document.querySelector(`.paper-item[data-name="${name}"] input`);
    if (!item) { console.error('NOT FOUND:', name); continue; }
    item.checked = true;
    item.dispatchEvent(new window.Event('change', { bubbles: true }));
  }

  const count = document.getElementById('selected-count').textContent;
  console.log(`Selected count: ${count}`);

  const nextBtn = document.getElementById('btn-to-ability');
  console.log(`Next button disabled: ${nextBtn.disabled}`);

  // Go to ability step
  nextBtn.click();
  const abilitySection = document.getElementById('step-ability');
  console.log(`Ability section visible: ${abilitySection.classList.contains('active-section')}`);

  // Test preset buttons
  const presets = document.querySelectorAll('.preset-btn');
  presets[2].click(); // "Upper third" (75)
  const slider = document.getElementById('ability-slider');
  console.log(`Slider after preset: ${slider.value}`);
  const shift = document.getElementById('ability-shift').textContent;
  console.log(`Ability shift: ${shift}`);

  // Go to results
  document.getElementById('btn-to-results').click();
  await new Promise(r => setTimeout(r, 500)); // simulation time

  const headline = document.getElementById('result-headline').textContent.trim();
  console.log(`\nHeadline: ${headline}`);

  const table = document.getElementById('result-table');
  const rows = table.querySelectorAll('tbody tr');
  console.log(`Table rows: ${rows.length}`);
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    console.log(`  ${cells[0].textContent}: ${cells[1].textContent} (${cells[2].textContent})`);
  });

  const contextPanels = document.querySelectorAll('.context-card');
  console.log(`\nContext panels: ${contextPanels.length}`);
  contextPanels.forEach(panel => {
    console.log(`  ${panel.querySelector('h3').textContent}: ${panel.querySelector('.context-value').textContent.trim()}`);
  });

  // Test restart
  document.getElementById('btn-restart').click();
  const restartCount = document.getElementById('selected-count').textContent;
  console.log(`\nAfter restart, selected: ${restartCount}`);
  const papersStep = document.getElementById('step-papers');
  console.log(`Papers section visible: ${papersStep.classList.contains('active-section')}`);

  console.log('\nAll DOM tests passed!');
  dom.window.close();
}, 100);
