"""Tests for the what-if conditional marks engine (Engine.simulateConditional, findThreshold, markContext)."""
import subprocess
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEST_JS = """
const fs = require('fs');

const engineCode = fs.readFileSync('web/engine.js', 'utf8');
const Engine = (new Function(engineCode.replace('const Engine =', 'return ')))();

const DATA = JSON.parse(fs.readFileSync('web/data.json', 'utf8'));

const paperNames = ['Microeconomics', 'Macroeconomics', 'Ethics',
  'International Relations', 'Quantitative Economics',
  'British Politics and Government since 1900',
  'Knowledge and Reality', 'Theory of Politics'];

const papers = paperNames.map(name => ({
  name, subject: DATA.paper_catalogue[name].subject,
  mu: DATA.paper_catalogue[name].mu,
  sigma: DATA.paper_catalogue[name].sigma
}));

const rho = DATA.rho;
const results = {};

// Test 1: simulateConditional with no fixed marks should match simulate
const unconditional = Engine.simulate(papers, rho, 75, 20000);
const conditionalNone = Engine.simulateConditional(papers, new Map(), rho, 75, 20000);
results.test1_unconditional_first = unconditional['1st'];
results.test1_conditional_none_first = conditionalNone.distribution['1st'];
results.test1_pass = Math.abs(unconditional['1st'] - conditionalNone.distribution['1st']) < 0.04;

// Test 2: Fix one paper to a very high mark — should increase P(1st)
const fixHigh = new Map([[0, 80]]);
const conditionalHigh = Engine.simulateConditional(papers, fixHigh, rho, 75, 20000);
results.test2_fixed_high_first = conditionalHigh.distribution['1st'];
results.test2_pass = conditionalHigh.distribution['1st'] > unconditional['1st'];

// Test 3: Fix one paper below 50 — should make First impossible (conjunctive rule)
const fixLow = new Map([[0, 45]]);
const conditionalLow = Engine.simulateConditional(papers, fixLow, rho, 75, 20000);
results.test3_fixed_low_first = conditionalLow.distribution['1st'];
results.test3_pass = conditionalLow.distribution['1st'] === 0;

// Test 4: markContext gives reasonable output for a mark near the mean
const ctx = Engine.markContext(65, 64, 7, rho, 50);
results.test4_percentile = ctx.percentile;
results.test4_label = ctx.label;
results.test4_pass = ctx.percentile >= 40 && ctx.percentile <= 70 && ctx.label === 'around average';

// Test 5: markContext for a very low mark
const ctxLow = Engine.markContext(45, 64, 7, rho, 50);
results.test5_percentile = ctxLow.percentile;
results.test5_label = ctxLow.label;
results.test5_pass = ctxLow.percentile <= 15 && ctxLow.label === 'well below average';

// Test 6: markContext for a high mark
const ctxHigh = Engine.markContext(78, 64, 7, rho, 50);
results.test6_percentile = ctxHigh.percentile;
results.test6_label = ctxHigh.label;
results.test6_pass = ctxHigh.percentile >= 85 && ctxHigh.label === 'strong';

// Test 7: findThreshold returns null when First is impossible (two marks < 50)
const fixAllLow = new Map([[0, 45], [1, 45]]);
const threshold = Engine.findThreshold(papers, fixAllLow, rho, '1st', 0.5, 5000);
results.test7_threshold = threshold;
results.test7_pass = threshold === null;

// Test 8: findThreshold returns a reasonable percentile with favorable fixed marks
const fixFavorable = new Map([[0, 72], [1, 71]]);
const threshold2 = Engine.findThreshold(papers, fixFavorable, rho, '1st', 0.5, 8000);
results.test8_threshold = threshold2;
results.test8_pass = threshold2 !== null && threshold2 >= 30 && threshold2 <= 95;

// Test 9: Fixing all 7 papers and leaving 1 free still works
const fixSeven = new Map([[0, 70], [1, 68], [2, 65], [3, 66], [4, 72], [5, 64], [6, 69]]);
const conditionalSeven = Engine.simulateConditional(papers, fixSeven, rho, 75, 10000);
results.test9_has_distribution = Object.keys(conditionalSeven.distribution).length === 6;
results.test9_sums_to_one = Math.abs(
  Object.values(conditionalSeven.distribution).reduce((a, b) => a + b, 0) - 1.0
) < 0.001;
results.test9_pass = results.test9_has_distribution && results.test9_sums_to_one;

// Test 10: simulateConditional with high fixed marks should shift distribution toward First
const fixThreeHigh = new Map([[0, 75], [1, 73], [2, 72]]);
const conditionalThreeHigh = Engine.simulateConditional(papers, fixThreeHigh, rho, 50, 20000);
const unconditional50 = Engine.simulate(papers, rho, 50, 20000);
results.test10_conditional_first = conditionalThreeHigh.distribution['1st'];
results.test10_unconditional_first = unconditional50['1st'];
results.test10_pass = conditionalThreeHigh.distribution['1st'] > unconditional50['1st'];

console.log(JSON.stringify(results, null, 2));
"""


def run_tests():
    result = subprocess.run(
        ['node', '-e', TEST_JS],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        print("ERROR running Node.js:")
        print(result.stderr)
        sys.exit(1)

    results = json.loads(result.stdout)

    tests = [
        ("simulateConditional(no fixed) ≈ simulate()", 'test1',
         f"unconditional={results['test1_unconditional_first']:.3f}, "
         f"conditional={results['test1_conditional_none_first']:.3f}"),
        ("Fix high mark → higher P(1st)", 'test2',
         f"P(1st)={results['test2_fixed_high_first']:.3f}"),
        ("Fix <50 → P(1st) = 0 (conjunctive veto)", 'test3',
         f"P(1st)={results['test3_fixed_low_first']:.4f}"),
        ("markContext near mean → 'around average'", 'test4',
         f"pctile={results['test4_percentile']}, label={results['test4_label']}"),
        ("markContext low mark → 'well below average'", 'test5',
         f"pctile={results['test5_percentile']}, label={results['test5_label']}"),
        ("markContext high mark → 'strong'", 'test6',
         f"pctile={results['test6_percentile']}, label={results['test6_label']}"),
        ("findThreshold impossible → null", 'test7',
         f"threshold={results['test7_threshold']}"),
        ("findThreshold achievable → reasonable percentile", 'test8',
         f"threshold={results['test8_threshold']}"),
        ("Fix 7 of 8 papers → valid distribution", 'test9',
         f"sums_to_one={results['test9_sums_to_one']}"),
        ("Fix 3 high marks at median ability → better than unconditional", 'test10',
         f"conditional={results['test10_conditional_first']:.3f}, "
         f"unconditional={results['test10_unconditional_first']:.3f}"),
    ]

    print("What-if engine tests:")
    print("-" * 70)
    all_pass = True
    for desc, key, detail in tests:
        passed = results[f'{key}_pass']
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {desc}")
        print(f"         {detail}")
        if not passed:
            all_pass = False

    print("-" * 70)
    print(f"{'ALL TESTS PASSED' if all_pass else 'SOME TESTS FAILED'}")
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    run_tests()
