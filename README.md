# Oxford PPE Finals Results Analysis

Statistical analysis of 15 years (2011--2025) of Oxford PPE Final Honour School examiners' reports. Extracts structured data from PDF reports, fits per-paper mark distributions, and runs Monte Carlo simulations to estimate classification probabilities given a student's paper choices.

## Data pipeline

```
reports/*.pdf  ──►  extract.py / llm_extract.py  ──►  data/raw/
                                                          │
                    build_paper_aliases.py  ──►  data/paper_aliases.json
                                                          │
                    build_canonical.py  ──────►  data/canonical/
                                                          │
                    analysis.py  ─────────────►  data/analysis/
```

### Phase 1: Extraction

**`extract.py`** -- Regex-based parsers for well-structured sections:
- Overall class distribution (all 15 years): counts and percentages for 1st, 2.1, 2.2, 3rd, Pass, Fail.
- Subject-level aggregates (all years): mean mark and SD per subject (Philosophy, Politics, Economics, All), covering 4 distinct format eras across the reports.

Uses `pdftotext -layout` for text extraction.

**`llm_extract.py`** -- LLM-based extraction for complex/varied table formats. Sends full PDFs as base64 documents to Claude Sonnet via Bedrock. Extracts 6 section types:
- `gender_class`: class distribution by gender (percentage and counts)
- `gender_stats`: total candidates, mean mark, SD by gender
- `per_paper`: per-paper statistics (mean, SD, min, max, band counts, quartiles), varying by format era
- `route_class`: class distribution by route (Phil-Pol, Pol-Econ, Phil-Econ, PPE)
- `ethnicity_class`: class distribution by ethnicity (BME/White/Unknown), cohort-year based
- `paper_numbers`: candidate counts per paper per year

**`build_paper_aliases.py`** -- Paper name normalisation. Sends all 391 unique paper name variants to Claude for clustering, producing 97 canonical paper names. Handles abbreviations, numeric codes, degree suffixes, syllabus notes, and minor spelling differences.

**`build_canonical.py`** -- Merges regex and LLM extractions, deduplicates overlapping observations (preferring the latest report year), normalises paper names, and writes canonical JSON files.

**`validate.py`** -- Cross-validates overlapping observations across reports. Checks for discrepancies in gender stats (0 found), gender class distributions (74/219 -- all genuine data corrections between report editions, not extraction errors), and per-paper coverage.

### Phase 2: Analysis

**`analysis.py`** -- All statistical analysis. Run with `python analysis.py` to regenerate all outputs.

## Statistical methods

### Distribution fitting

For each of the 97 canonical papers, we fit a truncated normal distribution (support [0, 100]) to the pooled band-count data across all available non-COVID years (2017--2022, 2024--2025).

**Method**: Maximum likelihood estimation on binned observations. The data comes as counts in 6 mark bands (>=70, 60--69, 50--59, 40--49, 30--39, <30). We maximise the multinomial log-likelihood of the observed bin counts under a truncated normal model with parameters (mu, sigma), using Nelder-Mead optimisation.

**Goodness of fit**: Chi-squared test on the fitted vs observed bin counts (merging bins with expected count < 5 per standard practice). Degrees of freedom = (number of merged bins) - 1 - 2 (for the two estimated parameters).

**Fallback**: Papers available only in 2015--2016 (mean and SD reported, no bands) use moment estimates directly: mu = reported mean, sigma = reported SD. These 16 papers are flagged with `method: "moment_mean_sd"` in the output.

**Exclusions**: 2020 is excluded throughout as the COVID year (40% first rate vs typical ~23%). Fits with degenerate parameters (mu outside [20, 90] or sigma outside [0.5, 25]) are discarded.

**Result**: 81 papers fitted (65 from band-count MLE, 16 from moment estimates).

### Classification rules

PPE degree classifications follow conjunctive rules -- they require both an average threshold AND a minimum count of papers above a mark threshold:

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

Given a student's 8 paper choices, we estimate classification probabilities via simulation (100,000 draws by default).

**Generative model**:
```
mark_i = mu_i + theta + epsilon_i       for papers i = 1..8

theta     ~ N(0, sigma_ability^2)        shared latent ability
epsilon_i ~ N(0, sigma_paper_i^2 - sigma_ability^2)   paper-specific noise
```

- `mu_i` is the fitted mean for paper i.
- `sigma_paper_i` is the fitted SD for paper i.
- `theta` is a latent ability factor shared across all papers, inducing positive correlation between marks. Without this, 8 independent draws would produce an unrealistically tight average distribution.
- `epsilon_i` is the residual paper-specific noise. Its variance is `max(sigma_paper_i^2 - sigma_ability^2, 0.1)`, ensuring it stays positive even when a paper's SD is smaller than sigma_ability.

Marks are clipped to [0, 100] after sampling.

**Calibration of sigma_ability**: The single free parameter `sigma_ability` controls how correlated a student's marks are across papers. We calibrate it by:
1. Selecting the 8 most popular papers (by total candidate count) as a representative set.
2. Running the simulation with varying sigma_ability values.
3. Finding the value that makes the simulated first-class rate match the observed rate of 23.4% (computed from same-year report data, 2015--2025 excluding 2020, weighted across all years with per-paper data).

The calibrated value is sigma_ability = 2.74.

**Validation**: Simulated route-level first rates are compared against observed route-level data (e.g. Phil-Pol simulated 22.3% vs observed 23.5%).

### Temporal trend analysis

For each paper with >= 4 years of data (excluding 2020), we fit an OLS regression of mean mark on year:

```
mean_mark = alpha + beta * year + noise
```

We report:
- **slope** (beta): change in mean mark per year (marks/year)
- **95% confidence interval**: slope +/- t_{n-2, 0.025} * stderr
- **p-value**: two-sided test for slope != 0
- **R-squared**: fraction of variance in year-to-year mean explained by the linear trend

Only 3 of 65 papers show significant drift at p < 0.05:
- Philosophical Logic: -1.01 marks/year, 95% CI [-1.52, -0.51], p = 0.004
- Microeconomic Analysis: +1.65 marks/year, 95% CI [+0.82, +2.49], p = 0.005
- Thesis in Politics: +0.38 marks/year, 95% CI [+0.07, +0.68], p = 0.025

### Subject-level analysis

**Variance decomposition**: For each subject, we decompose the total variance in marks into:
- **Within-paper variance**: the average sigma^2 across papers in that subject (weighted by candidate count). This is how much marks vary among students taking the same paper.
- **Between-paper variance**: the weighted variance of paper means around the subject grand mean. This is how much papers differ in average difficulty.

Within-paper variance dominates in all subjects (29--75x the between-paper variance), meaning the main source of mark variation is student performance on individual papers, not differences in paper difficulty. Economics has the highest within-paper variance (71.8) -- individual economics papers are volatile.

**Kingmaker papers**: Papers ranked by sigma (SD). High-sigma papers are "double-edged" -- they offer more opportunity for very high marks but also more risk of low marks. The top 3 (Econometrics sigma=14.0, Game Theory sigma=12.3, Quantitative Economics sigma=10.6) are all economics papers.

## Canonical data files

All in `data/canonical/`:

| File | Records | Description |
|------|---------|-------------|
| `class_distribution.json` | 133 | Overall class counts and percentages, 2005--2025 |
| `subject_aggregates.json` | 63 | Mean and SD per subject per year, 2010--2025 |
| `gender_class.json` | 273 | Class distribution by gender, 2006--2025 |
| `gender_stats.json` | 30 | Candidates, mean, SD by gender, 2011--2025 |
| `per_paper.json` | 717 | Per-paper stats (mean, SD, bands, quartiles), 2015--2025 |
| `route_class.json` | 230 | Class distribution by route, 2010--2025 |
| `ethnicity_class.json` | 99 | Class distribution by ethnicity, cohorts 2012/13--2022/23 |
| `paper_numbers.json` | 1339 | Candidate counts per paper, 2005--2025 |

## Analysis output files

All in `data/analysis/`:

| File | Description |
|------|-------------|
| `paper_fits.json` | Fitted (mu, sigma) for 81 papers, with method and GOF p-value |
| `paper_profiles.json` | Difficulty profiles: mu, sigma, %1st, %2.1, %below-50 per paper |
| `temporal_trends.json` | OLS trend per paper: slope, 95% CI, p-value, R-squared |
| `subject_analysis.json` | Subject summaries, variance decomposition, kingmaker papers, first rates |
| `simulation_params.json` | Calibrated sigma_ability |
| `sensitivity.json` | Sensitivity of classification to 8th-paper choice (for two base sets) |

## Usage

```bash
# Activate venv
source venv/bin/activate

# Phase 1: Extract data (requires reports/ directory with PDFs)
python extract.py                        # regex extraction
python llm_extract.py                    # LLM extraction (requires Bedrock credentials)
python build_paper_aliases.py            # paper name normalisation
python build_canonical.py                # merge and deduplicate

# Phase 2: Run analysis
python analysis.py                       # generates all data/analysis/ outputs

# Simulate a specific paper combination
python -c "
from analysis import *
import json
fits = json.load(open('data/analysis/paper_fits.json'))
params = json.load(open('data/analysis/simulation_params.json'))
papers = ['Ethics', 'Theory of Politics', 'Microeconomics',
          'International Relations', 'Philosophy of Mind',
          'Comparative Government', 'Macroeconomics', 'Political Sociology']
result = simulate_classification(fits, papers, params['sigma_ability'])
print(result)
"
```

## Known limitations

- **Truncated normal assumption**: We assume marks follow a truncated normal distribution within each paper. Some papers (especially those with ceiling effects or bimodal marking) may be poorly approximated. Goodness-of-fit p-values flag the worst cases.
- **Temporal pooling**: Band counts are pooled across years to increase statistical power. The trend analysis shows this is justified (only 3/65 papers have significant drift), but the pooled distribution represents an average over the period, not any single year.
- **Independence across papers**: The latent ability model introduces positive correlation between a student's marks, but the correlation structure is simple (single factor). In reality, papers within the same subject may be more correlated than papers across subjects.
- **No selection effects**: The simulation assumes a randomly drawn student from the overall population. In practice, students self-select into papers based on ability and interest, which means the observed mark distribution for a paper reflects the students who chose it, not the general population.
- **COVID exclusion**: 2020 data is excluded from all fitting and trend analysis. The 40% first rate that year is a genuine anomaly (safety-net policies, open-book exams) that would distort the model.
- **2023 boycott**: The 2023 Marking and Assessment Boycott resulted in no per-paper statistics being published that year. Classification data is available but per-paper data has a gap.
- **Canonical class_distribution quality**: The "prefer latest report" deduplication strategy introduces some errors for 2016--2017 data, where later reports' class distribution tables are parsed incorrectly (picking up a different cohort). Same-year report values are correct; this affects only the canonical file. The analysis pipeline uses per-paper data (not class_distribution) for its core calculations, so this does not affect simulation results.

## Dependencies

- Python 3.11+
- numpy, scipy (analysis)
- anthropic, json_repair (LLM extraction)
- pdftotext (PDF text extraction, from poppler-utils)
