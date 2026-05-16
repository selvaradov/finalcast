# Finalcast — Oxford PPE Results

Analysis of 15 years of PPE FHS outcomes (2011-2025), estimating classification probabilities given a student's paper choices.

**Explore the data and simulate your own papers [here](https://selvaradov.github.io/finalcast)**.

Data extraction and coding by Claude; it's possible that there are errors (particularly in data extraction) -- although I
have manually verified some results and they seem broadly reasonable.

The remainder of this README describes the implementation details. For an overview of the key findings, look at the
[PDF report](output/report.pdf).

## Data pipeline

```
reports/*.pdf  ──►  llm_extract.py  ──►  data/raw/
                                            │
                    build_paper_aliases.py  ──►  data/paper_aliases.json
                                            │
                    build_canonical.py  ──────►  data/canonical/
                                            │
                    analysis.py  ─────────────►  data/analysis/
                                            │
                    visualise.py  ────────────►  output/charts/ + output/tables/
```

### Phase 1: Extraction

**`llm_extract.py`** -- Sends full PDFs as base64 documents to Claude Sonnet via Bedrock. Extracts 8 section types:
- `class_distribution`: overall class distribution (counts and percentages by year)
- `subject_aggregates`: mean and SD per subject (Philosophy, Politics, Economics)
- `gender_class`: class distribution by gender
- `gender_stats`: total candidates, mean mark, SD by gender
- `per_paper`: per-paper statistics (mean, SD, min, max, band counts, quartiles)
- `route_class`: class distribution by route (Phil-Pol, Pol-Econ, Phil-Econ, PPE)
- `ethnicity_class`: class distribution by ethnicity (BME/White/Unknown)
- `paper_numbers`: candidate counts per paper per year

Uses `json_repair` for robust parsing of LLM JSON output.

**`build_paper_aliases.py`** -- Paper name normalisation. Sends all unique paper name variants to Claude for clustering, producing ~95 canonical paper names from ~400 variants.

**`build_canonical.py`** -- Deduplicates overlapping observations across reports (preferring the latest report year), normalises paper names, deduplicates per_paper records (removes component splits, old-regs duplicates, route splits), and writes canonical JSON files.

**`validate.py`** -- Cross-validates overlapping observations across reports.

**`validate_data.py`** -- Post-build validation suite: alias completeness, population-weighted coverage, dedup integrity, fit reliability flags, data sanity checks. Run after any pipeline change.

**`audit_data_gaps.py`** -- Detailed coverage audit comparing paper_numbers vs per_paper, with alias mismatch detection and raw extraction analysis.

### Phase 2: Analysis

**`analysis.py`** -- All statistical analysis. Run `python analysis.py` to regenerate all outputs.

**`visualise.py`** -- Charts and summary tables. Run `python visualise.py` to regenerate.

## Statistical methods

### Distribution fitting

For each of the 97 canonical papers, we fit a truncated normal distribution (support [0, 100]) to the pooled band-count data across all available non-COVID years (2017--2022, 2024--2025).

**Method**: Maximum likelihood estimation on binned observations. The data comes as counts in 6 mark bands (>=70, 60--69, 50--59, 40--49, 30--39, <30). We maximise the multinomial log-likelihood of the observed bin counts under a truncated normal model with parameters (mu, sigma), using Nelder-Mead optimisation.

**Goodness of fit**: Chi-squared test on the fitted vs observed bin counts (merging bins with expected count < 5). Degrees of freedom = (merged bins) - 1 - 2 (for estimated parameters).

**Fallback**: Papers with only mean and SD (2015--2016, no bands) use moment estimates. Flagged as `method: "moment_mean_sd"`.

**Exclusions**: 2020 excluded (COVID). Degenerate fits (mu outside [20, 90] or sigma outside [0.5, 25]) discarded.

**Result**: 79 papers fitted (63 from band-count MLE, 16 from moment estimates). 53 flagged as reliable (n_total >= 30 and sigma >= 2.0); 26 flagged low-confidence.

### Classification rules

PPE degree classifications follow conjunctive rules:

| Class | Average | Additional requirement |
|-------|---------|----------------------|
| 1st   | >= 68.5 | >= 2 marks of 70+, no mark below 50 |
| 2.1   | >= 59.0 | >= 3 marks of 60+ |
| 2.2   | >= 49.0 | >= 3 marks of 50+ |
| 3rd   | >= 40.0 | >= 3 marks of 40+ |
| Pass  | >= 30.0 | -- |
| Fail  | < 30.0  | -- |

All eight papers count equally. The "N marks above X" conditions matter for borderline candidates: a student with average 69 can miss a 1st if they have a sub-50 mark or only one mark of 70+.

### Monte Carlo simulation

Given a student's 8 paper choices, we estimate classification probabilities via simulation (50,000 draws).

**Generative model** (proportional ability loading):
```
mark_i = mu_i + lambda_i * theta + epsilon_i       for papers i = 1..8

lambda_i  = sigma_i * sqrt(rho)          ability loading (proportional to paper spread)
epsilon_i ~ N(0, sigma_i^2 * (1 - rho))  residual exam-day noise
theta     = norminv(percentile)           standardised ability (fixed, not random)
```

- `theta` is a standardised latent ability factor set by the student's self-assessed percentile.
- `lambda_i` scales with paper sigma: high-variance papers are more sensitive to ability.
- All paper pairs have implied correlation `rho`.
- Marks clipped to [0, 100].

The proportional loading addresses a key flaw of the additive model (constant shift regardless of paper sigma), which attributed only 4% of high-variance paper spread to ability and gave implausible tail risk for strong students.

**Calibration**: rho = 0.196, calibrated via binary search to match the observed 23.2% first-class rate for the 8 most popular papers (2015--2025 excluding 2020).

**Validation**: Simulated route-level first rates compared against observed data (e.g. Phil-Pol simulated 22.3% vs observed 23.5%). At 95th percentile, P(any paper below 50) is ~2% for a kingmaker-heavy combo (vs ~15% under the old additive model).

### Temporal trend analysis

OLS regression of mean mark on year for each paper with >= 4 years of data (excluding 2020). Reports slope, 95% CI, p-value, R-squared.

7 of 64 papers show significant drift (p < 0.05):
- Quantitative Economics: +0.55 marks/year, p = 0.001
- Microeconomic Analysis: +1.65 marks/year, p = 0.005
- Political Thought: Plato to Rousseau: +0.24 marks/year, p = 0.006
- Political Thought: Bentham to Weber: +0.35 marks/year, p = 0.010
- Philosophical Logic: -0.63 marks/year, p = 0.015
- Politics in South Asia: +0.47 marks/year, p = 0.016
- Public Economics: +0.26 marks/year, p = 0.036

### Subject-level analysis

**Variance decomposition**: within-paper variance dominates in all subjects (29--75x between-paper). Economics within-paper var = 71.8 vs Philosophy 30.2. The wide economics SD is individual paper spread, not differences in paper difficulty.

**Kingmaker papers** (sigma >= 10, one full grade class width): Econometrics (sigma=14.0), Game Theory (sigma=12.3), Quantitative Economics (sigma=10.7) -- all economics.

## Data files

### Canonical data (`data/canonical/`)

| File | Records | Description |
|------|---------|-------------|
| `class_distribution.json` | ~147 | Overall class counts and percentages, 2005--2025 |
| `subject_aggregates.json` | ~63 | Mean and SD per subject per year |
| `gender_class.json` | 273 | Class distribution by gender, 2006--2025 |
| `gender_stats.json` | 30 | Candidates, mean, SD by gender, 2011--2025 |
| `per_paper.json` | 852 | Per-paper stats (deduplicated), 2015--2025 |
| `route_class.json` | 230 | Class distribution by route, 2010--2025 |
| `ethnicity_class.json` | 99 | Class distribution by ethnicity |
| `paper_numbers.json` | 1326 | Candidate counts per paper, 2005--2025 |

### Analysis outputs (`data/analysis/`)

| File | Description |
|------|-------------|
| `paper_fits.json` | Fitted (mu, sigma) for 79 papers, with method, GOF p-value, and reliability flag |
| `paper_profiles.json` | Difficulty profiles: mu, sigma, %1st, %2.1, %below-50, reliable |
| `temporal_trends.json` | OLS trend per paper: slope, 95% CI, p-value, R-squared |
| `subject_analysis.json` | Subject summaries, variance decomposition, kingmaker papers |
| `simulation_params.json` | Calibrated sigma_ability (additive model, used in analysis pipeline) |
| `sensitivity.json` | Sensitivity of classification to 8th-paper choice |

### Visualisations (`output/`)

| File | Description |
|------|-------------|
| `charts/gender_gap_time_series.png` | First-class rate by gender, 2006--2025 |
| `charts/popularity_vs_difficulty.png` | Mean and SD vs candidate count by subject |
| `charts/kingmaker_papers.png` | Risk/reward scatter: mean vs spread |
| `tables/subject_summary.md` | Subject means, SDs, variance decomposition |
| `tables/paper_rankings.md` | Top/bottom papers by mean, sigma, %1st |
| `tables/temporal_trends.md` | Significant and near-significant trends |
| `tables/popularity_difficulty.md` | Correlation statistics |

### Phase 3: Web tool

**`web/`** -- Finalcast interactive tool. A static site with a chalkboard aesthetic, using a minimal build step for copy management.

Four pages, hash-routed:

- **Calculator** (`#calculator`) -- Pick 8 papers, set ability percentile, get classification probabilities via Monte Carlo simulation. Features: "use typical papers" quick-start, paper swap suggestions, what-if comparison vs default papers, per-paper breakdown with P(70+) and below-50 risk, conditional marks mode ("what do I need?").
- **Explorer** (`#explorer`) -- Interactive scatter plot (mean vs spread, bubble size = popularity). Click any paper for a profile card with stats, temporal trends, and candidate sparkline. Filter by subject, sort by various metrics. Temporal trends section shows significant score drift and popularity shifts.
- **Overview** (`#overview`) -- First-class rate time series, gender gap chart, subject comparison, classification breakdown, score trends (3 significant papers), popularity growth rates. COVID 2020 and kingmaker callouts. Table of contents for in-page navigation.
- **Methodology** (`#methodology`) -- Full model description with KaTeX rendering (copyable math).

Key files:
- `web/data.json` -- Pre-computed bundle (~61KB, generated by `analysis.py`): 79 papers with fits + reliability flags, route/subject summaries, popularity time series, gender/class distributions, per-paper mean time series
- `web/engine.js` -- Monte Carlo simulation engine (classify, simulate with proportional loading, paperMetrics, simulateConditional, findThreshold, markContext)
- `web/app.js` -- Application logic, routing, URL state persistence
- `web/explorer.js` -- Explorer page (Chart.js scatter, paper profiles, filtering, temporal trends)
- `web/overview.js` -- Overview page (Chart.js time series, bar charts, popularity trends)
- `web/copy/*.md` -- Editable prose content for each page (methodology, overview, explorer, landing, calculator)
- `web/build.py` -- Syncs copy from .md files into index.html (`python web/build.py`)
- `web/style.css` -- Chalkboard theme: SVG displacement filter for hand-drawn borders, Fredericka the Great display font, Caveat for chalk labels, noise texture overlay, vignette

**Important**: `web/index.html` is a build artefact (gitignored) — never edit it directly. All text copy lives in `web/copy/*.md` and structural HTML in `web/template.html`. Run `python web/build.py` to generate `index.html` from the template. Deployment is handled by GitHub Actions (`.github/workflows/deploy.yml`), which runs the build step and publishes the `web/` directory to GitHub Pages.

Visual design:
- Dark chalkboard background with SVG feTurbulence noise overlay
- Hand-drawn border effect via SVG displacement filter on `::before` pseudo-elements
- Fredericka the Great for hero heading, Caveat for chalk-style labels, Inter for body
- Cards are transparent (no background fill) — just chalk borders on the board

Paper selections + ability are encoded in URL query params for sharing (e.g. `?papers=Micro|Macro|...&ability=75`).

Serve locally: `cd web && python -m http.server 8080`

## Usage

```bash
source venv/bin/activate

# Phase 1: Extract (requires reports/ and Bedrock credentials)
python llm_extract.py
python build_paper_aliases.py
python build_canonical.py

# Phase 2: Analyse
python analysis.py               # also writes web/data.json
python visualise.py

# Validate
python validate_data.py          # post-build checks (coverage, dedup, reliability)
python validate_data.py --quick  # just coverage + dedup

# Phase 3: Web tool (run after clone)
python web/build.py              # build index.html from template + copy/*.md
python web/serve.py              # dev server with live reload on :8000
```

## Known limitations

See `notes/model_limitations.md` for quantitative analysis of the two main modelling limitations.

- **Truncated normal assumption**: UK marks are asymmetric (compressed 58–68, ceiling ~75–80). The fitted model overstates Q3 by 2–4 marks for kingmaker papers (e.g. Econometrics: fitted Q3=74.7 vs observed 70.5). Band-level P(>=70) is well-calibrated (within 1–3pp), but the within-band distribution is wrong — the conditional mean E\[mark | mark>=70\] is ~79 in the model vs ~72–73 in reality. Net impact on First rates: ~1–2pp overestimate for kingmaker-heavy combos.
- **Single-factor correlation**: The latent ability model assumes constant ρ=0.196 across all paper pairs. Same-subject papers are likely more correlated (ρ≈0.3–0.5). A two-factor model (global + per-subject) gives substantially different conditional results — e.g. P(First) at the 95th percentile drops from 84% to 61% for the popular 8 combo under ρ_within=0.30. Population-level rates are stable (~23%) across all scenarios. The model is under-identified without individual-level data.
- **Selection effects**: The simulation assumes a random student. Self-selection into papers means observed distributions reflect who chose the paper. Plausible magnitude: ±1–3 marks on paper means, ±2–3pp on classification probabilities. See `notes/selection_and_ability.md`.
- **Temporal pooling**: Pooled across years. Justified by trend analysis (7/64 significant, all modest slopes), but represents an average, not any single year.
- **COVID exclusion**: 2020 excluded (40% first rate from safety-net policies).
- **2023 boycott**: No per-paper statistics published that year.

## Dependencies

- Python 3.11+
- numpy, scipy, matplotlib
- anthropic, json_repair (LLM extraction)
