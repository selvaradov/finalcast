/**
 * PPE Classification Engine
 * Port of analysis.py classify() and simulate_classification() to JS.
 */

const Engine = (() => {

  // Box-Muller transform for normal random variates
  function randn() {
    let u, v, s;
    do {
      u = Math.random() * 2 - 1;
      v = Math.random() * 2 - 1;
      s = u * u + v * v;
    } while (s >= 1 || s === 0);
    return u * Math.sqrt(-2 * Math.log(s) / s);
  }

  // Standard normal CDF (Abramowitz & Stegun approximation)
  function normcdf(x) {
    const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741;
    const a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
    const sign = x < 0 ? -1 : 1;
    x = Math.abs(x) / Math.SQRT2;
    const t = 1.0 / (1.0 + p * x);
    const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return 0.5 * (1.0 + sign * y);
  }

  // Inverse normal CDF (rational approximation, Beasley-Springer-Moro)
  function norminv(p) {
    if (p <= 0) return -Infinity;
    if (p >= 1) return Infinity;
    if (p === 0.5) return 0;

    const a = [-3.969683028665376e+01, 2.209460984245205e+02,
               -2.759285104469687e+02, 1.383577518672690e+02,
               -3.066479806614716e+01, 2.506628277459239e+00];
    const b = [-5.447609879822406e+01, 1.615858368580409e+02,
               -1.556989798598866e+02, 6.680131188771972e+01,
               -1.328068155288572e+01];
    const c = [-7.784894002430293e-03, -3.223964580411365e-01,
               -2.400758277161838e+00, -2.549732539343734e+00,
                4.374664141464968e+00, 2.938163982698783e+00];
    const d = [ 7.784695709041462e-03, 3.224671290700398e-01,
                2.445134137142996e+00, 3.754408661907416e+00];

    const pLow = 0.02425, pHigh = 1 - pLow;
    let q, r;

    if (p < pLow) {
      q = Math.sqrt(-2 * Math.log(p));
      return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
              ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
    } else if (p <= pHigh) {
      q = p - 0.5;
      r = q * q;
      return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
             (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1);
    } else {
      q = Math.sqrt(-2 * Math.log(1 - p));
      return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) /
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1);
    }
  }

  /**
   * Classify 8 marks into a degree class using exact PPE rules.
   */
  function classify(marks) {
    const avg = marks.reduce((a, b) => a + b, 0) / 8;
    const n70 = marks.filter(m => m >= 70).length;
    const n60 = marks.filter(m => m >= 60).length;
    const n50 = marks.filter(m => m >= 50).length;
    const n40 = marks.filter(m => m >= 40).length;
    const anyBelow50 = marks.some(m => m < 50);

    if (avg >= 68.5 && n70 >= 2 && !anyBelow50) return "1st";
    if (avg >= 59.0 && n60 >= 3) return "2.1";
    if (avg >= 49.0 && n50 >= 3) return "2.2";
    if (avg >= 40.0 && n40 >= 3) return "3rd";
    if (avg >= 30.0) return "Pass";
    return "Fail";
  }

  /**
   * Run Monte Carlo simulation for 8 papers.
   * Uses proportional ability loading: λ_i = σ_i × √ρ, ε_i ~ N(0, σ²_i(1-ρ)).
   * Ability θ is fixed at norminv(percentile) (standardised).
   *
   * @param {Object[]} papers - Array of {mu, sigma} for each paper
   * @param {number} rho - Inter-paper correlation (calibrated ~0.196)
   * @param {number} abilityPercentile - Student's self-assessed percentile (0-100)
   * @param {number} nSim - Number of simulations
   * @returns {Object} Classification probabilities
   */
  function simulate(papers, rho, abilityPercentile = 50, nSim = 50000) {
    const theta = norminv(abilityPercentile / 100);
    const sqrtRho = Math.sqrt(rho);
    const sqrt1mRho = Math.sqrt(1 - rho);

    const mus = papers.map(p => p.mu + p.sigma * sqrtRho * theta);
    const sigmaEps = papers.map(p => p.sigma * sqrt1mRho);

    const counts = { "1st": 0, "2.1": 0, "2.2": 0, "3rd": 0, "Pass": 0, "Fail": 0 };

    for (let i = 0; i < nSim; i++) {
      const marks = [];
      for (let j = 0; j < 8; j++) {
        let mark = mus[j] + randn() * sigmaEps[j];
        mark = Math.max(0, Math.min(100, mark));
        marks.push(mark);
      }
      counts[classify(marks)]++;
    }

    const result = {};
    for (const cls of ["1st", "2.1", "2.2", "3rd", "Pass", "Fail"]) {
      result[cls] = counts[cls] / nSim;
    }
    return result;
  }

  /**
   * Detect route from paper subjects.
   */
  function detectRoute(papers) {
    const subjects = new Set(papers.map(p => p.subject).filter(Boolean));
    if (subjects.size === 3) return "PPE";
    if (subjects.has("Philosophy") && subjects.has("Politics")) return "Phil-Pol";
    if (subjects.has("Philosophy") && subjects.has("Economics")) return "Phil-Econ";
    if (subjects.has("Politics") && subjects.has("Economics")) return "Pol-Econ";
    return "PPE";
  }

  function paperMetrics(papers, rho, abilityPercentile) {
    const theta = norminv(abilityPercentile / 100);
    const sqrtRho = Math.sqrt(rho);
    const sqrt1mRho = Math.sqrt(1 - rho);
    return papers.map(p => {
      const shiftedMu = p.mu + p.sigma * sqrtRho * theta;
      const sigmaEps = p.sigma * sqrt1mRho;
      const pBelow50 = normcdf((50 - shiftedMu) / sigmaEps);
      const pAbove70 = 1 - normcdf((70 - shiftedMu) / sigmaEps);
      return {
        name: p.name,
        subject: p.subject,
        shiftedMu,
        sigmaEps,
        pBelow50,
        pAbove70
      };
    });
  }

  /**
   * Simulate with some papers fixed to known marks.
   * @param {Object[]} papers - Array of {mu, sigma} for each paper
   * @param {Map|Object} fixedMarks - index → mark for fixed papers
   * @param {number} rho
   * @param {number} abilityPercentile
   * @param {number} nSim
   * @returns {Object} { distribution, freeMetrics }
   */
  function simulateConditional(papers, fixedMarks, rho, abilityPercentile, nSim = 50000) {
    const theta = norminv(abilityPercentile / 100);
    const sqrtRho = Math.sqrt(rho);
    const sqrt1mRho = Math.sqrt(1 - rho);

    const mus = papers.map(p => p.mu + p.sigma * sqrtRho * theta);
    const sigmaEps = papers.map(p => p.sigma * sqrt1mRho);

    const counts = { "1st": 0, "2.1": 0, "2.2": 0, "3rd": 0, "Pass": 0, "Fail": 0 };

    for (let i = 0; i < nSim; i++) {
      const marks = [];
      for (let j = 0; j < papers.length; j++) {
        if (fixedMarks.has !== undefined ? fixedMarks.has(j) : j in fixedMarks) {
          marks.push(fixedMarks.has !== undefined ? fixedMarks.get(j) : fixedMarks[j]);
        } else {
          let mark = mus[j] + randn() * sigmaEps[j];
          mark = Math.max(0, Math.min(100, mark));
          marks.push(mark);
        }
      }
      counts[classify(marks)]++;
    }

    const distribution = {};
    for (const cls of ["1st", "2.1", "2.2", "3rd", "Pass", "Fail"]) {
      distribution[cls] = counts[cls] / nSim;
    }
    return { distribution };
  }

  /**
   * Binary search over ability percentile to find where P(targetClass) >= targetProb.
   * Returns the percentile needed, or null if not achievable.
   */
  function findThreshold(papers, fixedMarks, rho, targetClass = "1st", targetProb = 0.5, nSim = 15000) {
    let lo = 5, hi = 95;

    const hiResult = simulateConditional(papers, fixedMarks, rho, hi, nSim);
    if (hiResult.distribution[targetClass] < targetProb) return null;

    const loResult = simulateConditional(papers, fixedMarks, rho, lo, nSim);
    if (loResult.distribution[targetClass] >= targetProb) return lo;

    for (let iter = 0; iter < 15; iter++) {
      const mid = (lo + hi) / 2;
      const result = simulateConditional(papers, fixedMarks, rho, mid, nSim);
      if (result.distribution[targetClass] >= targetProb) {
        hi = mid;
      } else {
        lo = mid;
      }
      if (hi - lo < 1) break;
    }
    return Math.round(hi);
  }

  /**
   * Get qualitative label and percentile for a mark on a given paper at a given ability.
   */
  function markContext(mark, mu, sigma, rho, abilityPercentile) {
    const theta = norminv(abilityPercentile / 100);
    const sqrtRho = Math.sqrt(rho);
    const sqrt1mRho = Math.sqrt(1 - rho);
    const shiftedMu = mu + sigma * sqrtRho * theta;
    const sigmaEps = sigma * sqrt1mRho;
    const percentile = Math.round(normcdf((mark - shiftedMu) / sigmaEps) * 100);

    let label;
    if (percentile <= 10) label = 'well below average';
    else if (percentile <= 30) label = 'below average';
    else if (percentile <= 70) label = 'around average';
    else if (percentile <= 90) label = 'above average';
    else label = 'strong';

    return { percentile, label };
  }

  return { classify, simulate, simulateConditional, findThreshold, detectRoute, norminv, normcdf, paperMetrics, markContext };
})();
