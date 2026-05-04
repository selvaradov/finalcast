# Oxford PPE Finals Results Analysis

Statistical analysis of 15 years (2011--2025) of Oxford PPE Final Honour School examiners' reports. Extracts structured data from PDF reports, fits per-paper mark distributions, and runs Monte Carlo simulations to estimate classification probabilities given a student's paper choices.

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

**`build_paper_aliases.py`** -- Paper name normalisation. Sends all 391 unique paper name variants to Claude for clustering, producing 97 canonical paper names.

**`build_canonical.py`** -- Deduplicates overlapping observations across reports (preferring the latest report year), normalises paper names, and writes canonical JSON files.

**`validate.py`** -- Cross-validates overlapping observations across reports.

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

**Result**: 81 papers fitted (65 from band-count MLE, 16 from moment estimates).

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

Given a student's 8 paper choices, we estimate classification probabilities via simulation (100,000 draws).

**Generative model**:
```
mark_i = mu_i + theta + epsilon_i       for papers i = 1..8

theta     ~ N(0, sigma_ability^2)        shared latent ability
epsilon_i ~ N(0, sigma_paper_i^2 - sigma_ability^2)   paper-specific noise
```

- `theta` is a latent ability factor inducing positive correlation between marks.
- `epsilon_i` variance is `max(sigma_paper_i^2 - sigma_ability^2, 0.1)`.
- Marks clipped to [0, 100].

**Calibration**: sigma_ability = 2.74, calibrated to match the observed 23.4% first-class rate (2015--2025 excluding 2020).

**Validation**: Simulated route-level first rates compared against observed data (e.g. Phil-Pol simulated 22.3% vs observed 23.5%).

### Temporal trend analysis

OLS regression of mean mark on year for each paper with >= 4 years of data (excluding 2020). Reports slope, 95% CI, p-value, R-squared.

3 of 65 papers show significant drift (p < 0.05):
- Philosophical Logic: -1.01 marks/year, 95% CI [-1.52, -0.51], p = 0.004
- Microeconomic Analysis: +1.65 marks/year, 95% CI [+0.82, +2.49], p = 0.005
- Thesis in Politics: +0.38 marks/year, 95% CI [+0.07, +0.68], p = 0.025

### Subject-level analysis

**Variance decomposition**: within-paper variance dominates in all subjects (29--75x between-paper). Economics within-paper var = 71.8 vs Philosophy 30.2. The wide economics SD is individual paper volatility, not differences in paper difficulty.

**Kingmaker papers**: Econometrics (sigma=14.0), Game Theory (sigma=12.3), Quantitative Economics (sigma=10.6) -- all economics.

## Data files

### Canonical data (`data/canonical/`)

| File | Records | Description |
|------|---------|-------------|
| `class_distribution.json` | ~147 | Overall class counts and percentages, 2005--2025 |
| `subject_aggregates.json` | ~63 | Mean and SD per subject per year |
| `gender_class.json` | 273 | Class distribution by gender, 2006--2025 |
| `gender_stats.json` | 30 | Candidates, mean, SD by gender, 2011--2025 |
| `per_paper.json` | 717 | Per-paper stats, 2015--2025 |
| `route_class.json` | 230 | Class distribution by route, 2010--2025 |
| `ethnicity_class.json` | 99 | Class distribution by ethnicity |
| `paper_numbers.json` | 1339 | Candidate counts per paper, 2005--2025 |

### Analysis outputs (`data/analysis/`)

| File | Description |
|------|-------------|
| `paper_fits.json` | Fitted (mu, sigma) for 81 papers, with method and GOF p-value |
| `paper_profiles.json` | Difficulty profiles: mu, sigma, %1st, %2.1, %below-50 |
| `temporal_trends.json` | OLS trend per paper: slope, 95% CI, p-value, R-squared |
| `subject_analysis.json` | Subject summaries, variance decomposition, kingmaker papers |
| `simulation_params.json` | Calibrated sigma_ability |
| `sensitivity.json` | Sensitivity of classification to 8th-paper choice |

### Visualisations (`output/`)

| File | Description |
|------|-------------|
| `charts/gender_gap_time_series.png` | First-class rate by gender, 2006--2025 |
| `charts/popularity_vs_difficulty.png` | Mean and SD vs candidate count by subject |
| `charts/kingmaker_papers.png` | Risk/reward scatter: mean vs volatility |
| `tables/subject_summary.md` | Subject means, SDs, variance decomposition |
| `tables/paper_rankings.md` | Top/bottom papers by mean, sigma, %1st |
| `tables/temporal_trends.md` | Significant and near-significant trends |
| `tables/popularity_difficulty.md` | Correlation statistics |

## Usage

```bash
source venv/bin/activate

# Phase 1: Extract (requires reports/ and Bedrock credentials)
python llm_extract.py
python build_paper_aliases.py
python build_canonical.py

# Phase 2: Analyse
python analysis.py
python visualise.py
```

## Known limitations

- **Truncated normal assumption**: May poorly approximate papers with ceiling effects or bimodal marking. GOF p-values flag the worst cases.
- **Temporal pooling**: Pooled across years. Justified by trend analysis (3/65 significant), but represents an average, not any single year.
- **Single-factor correlation**: The latent ability model assumes one shared factor. Same-subject papers may be more correlated in reality.
- **Selection effects**: The simulation assumes a random student. Self-selection into papers means observed distributions reflect who chose the paper.
- **COVID exclusion**: 2020 excluded (40% first rate from safety-net policies).
- **2023 boycott**: No per-paper statistics published that year.

## Dependencies

- Python 3.11+
- numpy, scipy, matplotlib
- anthropic, json_repair (LLM extraction)
