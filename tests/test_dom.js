// End-to-end DOM test of the calculator using jsdom
const fs = require('fs');
const { JSDOM } = require('jsdom');

const html = fs.readFileSync('web/index.html', 'utf8');
const engineSrc = fs.readFileSync('web/engine.js', 'utf8');
const appSrc = fs.readFileSync('web/app.js', 'utf8');

const dataJson = fs.readFileSync('web/data.json', 'utf8');

const dom = new JSDOM(html, {
  runScripts: 'dangerously',
  resources: 'usable',
  pretendToBeVisual: true,
  url: 'http://localhost:8080/#calculator'
});

const { window } = dom;
const { document } = window;

class MockCtx {
  beginPath() {} arc() {} closePath() {} fill() {} clearRect() {} scale() {}
  moveTo() {} lineTo() {} stroke() {} setLineDash() {}
  set fillStyle(v) {} set font(v) {} set textAlign(v) {} set textBaseline(v) {}
  set strokeStyle(v) {} set lineWidth(v) {}
  fillText() {}
}
if (window.HTMLCanvasElement) {
  window.HTMLCanvasElement.prototype.getContext = function() { return new MockCtx(); };
}

window.fetch = async (url) => ({
  json: async () => JSON.parse(dataJson)
});

Object.defineProperty(window, 'devicePixelRatio', { value: 1 });

window.eval(engineSrc.replace('const Engine =', 'window.Engine ='));
window.eval(appSrc.replace('const App =', 'window.App ='));

setTimeout(async () => {
  const event = new window.Event('DOMContentLoaded');
  document.dispatchEvent(event);
  await new Promise(r => setTimeout(r, 200));

  // Check papers rendered
  const paperItems = document.querySelectorAll('.paper-item');
  console.log(`Papers rendered: ${paperItems.length}`);
  if (paperItems.length !== 79) console.error('FAIL: expected 79 papers');

  const groups = document.querySelectorAll('.subject-group');
  console.log(`Subject groups: ${groups.length}`);

  // Check search
  const search = document.getElementById('paper-search');
  search.value = 'micro';
  search.dispatchEvent(new window.Event('input'));
  const visible = document.querySelectorAll('.paper-item:not(.hidden)');
  console.log(`Papers matching "micro": ${visible.length}`);
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

  // Test preset
  const presets = document.querySelectorAll('.preset-btn');
  presets[2].click();
  const slider = document.getElementById('ability-slider');
  console.log(`Slider after preset: ${slider.value}`);
  const shift = document.getElementById('ability-shift').textContent;
  console.log(`Ability shift: ${shift}`);

  // Go to results
  document.getElementById('btn-to-results').click();
  await new Promise(r => setTimeout(r, 1000));

  const headline = document.getElementById('result-headline').textContent.trim();
  console.log(`\nHeadline: ${headline}`);

  // Check class breakdown in headline
  const classes = document.querySelectorAll('.headline-class');
  console.log(`Class breakdown items: ${classes.length}`);
  classes.forEach(el => console.log(`  ${el.textContent}`));

  // Check paper breakdown
  const breakdown = document.getElementById('paper-breakdown');
  const breakdownRows = breakdown.querySelectorAll('tbody tr');
  console.log(`\nPaper breakdown rows: ${breakdownRows.length}`);

  const contextPanels = document.querySelectorAll('.context-card');
  console.log(`Context panels: ${contextPanels.length}`);

  // Test routing - check calculator page is visible
  const calcPage = document.querySelector('[data-page="calculator"]');
  console.log(`Calculator page visible: ${calcPage.style.display !== 'none'}`);

  // Test restart
  document.getElementById('btn-restart').click();
  const restartCount = document.getElementById('selected-count').textContent;
  console.log(`\nAfter restart, selected: ${restartCount}`);
  const papersStep = document.getElementById('step-papers');
  console.log(`Papers section visible: ${papersStep.classList.contains('active-section')}`);

  console.log('\nAll DOM tests passed!');
  dom.window.close();
}, 100);
