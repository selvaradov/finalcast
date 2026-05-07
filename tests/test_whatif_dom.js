// DOM test for the what-if (step 4) flow using jsdom
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

let failures = 0;
function assert(condition, msg) {
  if (!condition) {
    console.error(`  FAIL: ${msg}`);
    failures++;
  } else {
    console.log(`  PASS: ${msg}`);
  }
}

setTimeout(async () => {
  const event = new window.Event('DOMContentLoaded');
  document.dispatchEvent(event);
  await new Promise(r => setTimeout(r, 200));

  console.log('What-if DOM tests:');
  console.log('-'.repeat(60));

  // Select 8 papers and go to results
  const picks = [
    'Microeconomics', 'Macroeconomics', 'Ethics',
    'International Relations', 'Quantitative Economics',
    'British Politics and Government since 1900',
    'Knowledge and Reality', 'Theory of Politics'
  ];

  for (const name of picks) {
    const item = document.querySelector(`.paper-item[data-name="${name}"] input`);
    item.checked = true;
    item.dispatchEvent(new window.Event('change', { bubbles: true }));
  }

  document.getElementById('btn-to-ability').click();
  document.getElementById('btn-to-results').click();
  await new Promise(r => setTimeout(r, 500));

  // Step 4 button should exist
  const whatifBtn = document.getElementById('btn-whatif');
  assert(whatifBtn !== null, 'What-if button exists in step 3');

  // Click what-if button to go to step 4
  whatifBtn.click();
  await new Promise(r => setTimeout(r, 100));

  const whatifSection = document.getElementById('step-whatif');
  assert(whatifSection.classList.contains('active-section'), 'Step 4 section is active');

  // Check step indicator shows step 4
  const step4Indicator = document.querySelector('.step[data-step="4"]');
  assert(step4Indicator.classList.contains('active'), 'Step 4 indicator is active');

  // Check 8 paper rows rendered
  const rows = document.querySelectorAll('.whatif-row');
  assert(rows.length === 8, `8 paper rows rendered (got ${rows.length})`);

  // Check all mark inputs start disabled
  const inputs = document.querySelectorAll('.whatif-mark-input');
  const allDisabled = Array.from(inputs).every(i => i.disabled);
  assert(allDisabled, 'All mark inputs start disabled');

  // Lock one paper
  const firstCheck = document.querySelector('.whatif-check[data-idx="0"]');
  firstCheck.checked = true;
  firstCheck.dispatchEvent(new window.Event('change', { bubbles: true }));

  const firstInput = document.querySelector('.whatif-mark-input[data-idx="0"]');
  assert(!firstInput.disabled, 'First input enabled after locking');

  const firstRow = rows[0];
  assert(firstRow.classList.contains('fixed'), 'First row has fixed class');

  // Set mark and check context updates
  firstInput.value = '55';
  firstInput.dispatchEvent(new window.Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 50));

  const context = document.querySelector('.whatif-context[data-idx="0"]');
  assert(context.textContent.includes('percentile'), 'Context shows percentile info');

  // Run simulation
  document.getElementById('btn-whatif-run').click();
  await new Promise(r => setTimeout(r, 1500));

  const resultsDiv = document.getElementById('whatif-results');
  assert(resultsDiv.style.display !== 'none', 'Results div is visible');
  assert(resultsDiv.innerHTML.includes('big-number'), 'Results contain headline');

  // Mark below 50 should show constraint warning
  firstInput.value = '45';
  firstInput.dispatchEvent(new window.Event('input', { bubbles: true }));
  document.getElementById('btn-whatif-run').click();
  await new Promise(r => setTimeout(r, 1500));
  assert(resultsDiv.innerHTML.includes('whatif-constraint--warning'), 'Below-50 constraint warning shown');

  // Go back to results
  document.getElementById('btn-back-results').click();
  const resultsSection = document.getElementById('step-results');
  assert(resultsSection.classList.contains('active-section'), 'Back button returns to step 3');

  // Reference card should show previous results
  await new Promise(r => setTimeout(r, 600));
  whatifBtn.click();
  await new Promise(r => setTimeout(r, 100));
  const refCard = document.querySelector('.whatif-ref-card');
  assert(refCard !== null, 'Reference card shows previous results');
  assert(refCard.textContent.includes('chance of a'), 'Reference card has result text');

  console.log('-'.repeat(60));
  if (failures === 0) {
    console.log('All what-if DOM tests passed!');
  } else {
    console.log(`${failures} test(s) failed.`);
    process.exitCode = 1;
  }

  dom.window.close();
}, 100);
