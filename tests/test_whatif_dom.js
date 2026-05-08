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
  moveTo() {} lineTo() {} stroke() {} setLineDash() {} setTransform() {}
  save() {} restore() {} translate() {} rotate() {} quadraticCurveTo() {}
  bezierCurveTo() {} rect() {} clip() {} createLinearGradient() {
    return { addColorStop() {} };
  }
  measureText() { return { width: 0 }; }
  set fillStyle(v) {} set font(v) {} set textAlign(v) {} set textBaseline(v) {}
  set strokeStyle(v) {} set lineWidth(v) {} set globalAlpha(v) {}
  set lineCap(v) {} set lineJoin(v) {} set shadowBlur(v) {} set shadowColor(v) {}
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

  const whatifBtn = document.getElementById('btn-whatif');
  assert(whatifBtn !== null, 'What-if button exists in step 3');

  whatifBtn.click();
  await new Promise(r => setTimeout(r, 100));

  const whatifSection = document.getElementById('step-whatif');
  assert(whatifSection.classList.contains('active-section'), 'Step 4 section is active');

  const step4Indicator = document.querySelector('.step[data-step="4"]');
  assert(step4Indicator.classList.contains('active'), 'Step 4 indicator is active');

  const rows = document.querySelectorAll('.whatif-row');
  assert(rows.length === 8, `8 paper rows rendered (got ${rows.length})`);

  // Inputs start empty
  const inputs = document.querySelectorAll('.whatif-mark-input');
  const allEmpty = Array.from(inputs).every(i => i.value === '');
  assert(allEmpty, 'All mark inputs start empty');

  // No rows are fixed initially
  assert(document.querySelectorAll('.whatif-row.fixed').length === 0, 'No rows are fixed initially');

  // Status shows simulated state for unfixed papers
  const firstStatus = document.querySelector('.whatif-status[data-idx="0"]');
  assert(firstStatus.textContent.includes('simulated'), 'Status shows simulated initially');

  // Focus does NOT prefill (user should type fresh)
  const firstInput = document.querySelector('.whatif-mark-input[data-idx="0"]');
  firstInput.dispatchEvent(new window.Event('focus', { bubbles: true }));
  await new Promise(r => setTimeout(r, 50));
  const firstRow = rows[0];
  assert(!firstRow.classList.contains('fixed'), 'Row not fixed on mere focus');

  // Type a value to fix
  firstInput.value = '65';
  firstInput.dispatchEvent(new window.Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 50));
  assert(firstRow.classList.contains('fixed'), 'Row fixed after typing');

  // Status updates with percentile info
  assert(firstStatus.textContent.includes('%ile'), 'Status shows percentile after fixing');

  // Padlock icon appears
  const lockIcon = document.querySelector('.whatif-lock-icon[data-idx="0"]');
  assert(lockIcon.textContent !== '', 'Lock icon appears when fixed');

  // Clear button resets
  const clearBtn = document.querySelector('.whatif-clear-btn[data-idx="0"]');
  clearBtn.click();
  await new Promise(r => setTimeout(r, 50));
  assert(!firstRow.classList.contains('fixed'), 'Row unfixed after clear');
  assert(firstInput.value === '', 'Input cleared');
  assert(firstStatus.textContent.includes('simulated'), 'Status shows simulated after clear');
  assert(lockIcon.textContent === '', 'Lock icon gone after clear');

  // Fix again for simulation test
  firstInput.value = '55';
  firstInput.dispatchEvent(new window.Event('input', { bubbles: true }));
  await new Promise(r => setTimeout(r, 50));
  assert(firstRow.classList.contains('fixed'), 'Row re-fixed after typing');

  // Run simulation
  document.getElementById('btn-whatif-run').click();
  await new Promise(r => setTimeout(r, 1500));

  const resultsDiv = document.getElementById('whatif-results');
  assert(resultsDiv.style.display !== 'none', 'Results visible after simulation');
  assert(resultsDiv.innerHTML.includes('whatif-table'), 'Results contain paper table');

  // Input table hidden after calculation
  const papersDiv = document.getElementById('whatif-papers');
  assert(papersDiv.style.display === 'none', 'Input table hidden after calculation');

  // Heading changes to the answer
  const heading = document.getElementById('whatif-heading');
  assert(!heading.textContent.includes('What do you need'), 'Heading changes from question to answer');

  // Input subheader hidden, result subheader shown
  assert(document.getElementById('whatif-subheader').style.display === 'none', 'Input subheader hidden');
  assert(document.getElementById('whatif-result-subheader').style.display !== 'none', 'Result subheader visible');

  // Explanation text populated
  const explanation = document.getElementById('whatif-explanation');
  assert(explanation.textContent.length > 0, 'Explanation text populated in result subheader');

  // Table has 8 rows
  const tableRows = resultsDiv.querySelectorAll('.whatif-table tbody tr');
  assert(tableRows.length === 8, `Results table has 8 rows (got ${tableRows.length})`);

  // Fixed paper annotated in results
  assert(resultsDiv.innerHTML.includes('fixed'), 'Fixed paper annotated in results table');

  // "← Change marks" returns to input mode
  document.getElementById('btn-whatif-back-input').click();
  await new Promise(r => setTimeout(r, 50));
  assert(papersDiv.style.display !== 'none', 'Papers visible after back to input');
  assert(heading.textContent.includes('What do you need'), 'Heading reverts to question');
  assert(document.getElementById('whatif-subheader').style.display !== 'none', 'Input subheader visible again');
  assert(document.getElementById('whatif-result-subheader').style.display === 'none', 'Result subheader hidden again');

  // "← Results" returns to step 3
  document.getElementById('btn-back-results').click();
  const resultsSection = document.getElementById('step-results');
  assert(resultsSection.classList.contains('active-section'), 'Back results returns to step 3');

  // Max 7 fixed
  whatifBtn.click();
  await new Promise(r => setTimeout(r, 100));
  for (let i = 0; i < 8; i++) {
    const inp = document.querySelector(`.whatif-mark-input[data-idx="${i}"]`);
    inp.value = String(60 + i);
    inp.dispatchEvent(new window.Event('input', { bubbles: true }));
  }
  await new Promise(r => setTimeout(r, 50));
  const fixedCount = document.querySelectorAll('.whatif-row.fixed').length;
  assert(fixedCount <= 7, `Max 7 papers fixed (got ${fixedCount})`);

  console.log('-'.repeat(60));
  if (failures === 0) {
    console.log('All what-if DOM tests passed!');
  } else {
    console.log(`${failures} test(s) failed.`);
    process.exitCode = 1;
  }

  dom.window.close();
}, 100);
