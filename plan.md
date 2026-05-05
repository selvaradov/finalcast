# PPE Finals Results Analysis — Project Plan

## Goal

Extract 15 years of Oxford PPE Final Honour School examiners' report data (2011–2025) into structured JSON, analyse mark distributions, and build an interactive web tool where a student enters their paper choices and sees an estimated prior distribution over degree classifications.

---

## Phase 1: Data Extraction — COMPLETE

15 PDF reports extracted via hybrid approach: regex parsers (`extract.py`) for class distribution and subject aggregates; LLM extraction (`llm_extract.py`, Claude Sonnet via Bedrock) for 6 other section types. Paper names normalised from 391 variants to 97 canonical papers (`build_paper_aliases.py`). All data merged and deduplicated into `data/canonical/` via `build_canonical.py`.

### Canonical data inventory
- **class_distribution**: 133 records, 2005–2025 — counts + pct for each class by year
- **subject_aggregates**: 63 records, 2010–2025 — mean + SD per subject (Phil/Pol/Econ/All) by year
- **gender_stats**: 30 records, 2011–2025 — n + mean + SD by gender by year
- **gender_class**: 273 records, 2006–2025 — class distribution by gender (pct and sometimes counts)
- **route_class**: 230 records, 2010–2025 (gap 2012–2015) — class distribution by route
- **ethnicity_class**: 99 records, cohorts 2012/13–2022/23 — class distribution by ethnicity
- **per_paper**: 717 records, 2015–2022 + 2024–2025 — mean, SD, bands, quartiles per paper
- **paper_numbers**: 1339 records, 2005–2025 — candidate count per paper per year
- **paper_aliases**: 97 canonical papers mapped from 391 name variants

### Phase 1 remaining
- [x] Re-extract class_distribution via LLM (fixed 2016/2017/2019 errors from regex parser)
- [x] Migrate subject_aggregates to LLM extraction
- [x] Remove regex dependency from build_canonical.py — now fully LLM-based
- [ ] Manual verification spot-checks

### Format reference

Detailed format documentation for each data type is preserved below for reference during debugging or re-extraction.

<details>
<summary>Per-paper statistics format eras</summary>

| Era | Years | Format | Key columns |
|-----|-------|--------|-------------|
| A | 2011–2014 | No per-paper stats table. Subject-level averages in prose only. | Subject mean, SD |
| B | 2015–2016 | Simple table: paper name, average, SD, highest, lowest. | mean, SD, min, max |
| C | 2017–2018 | Rich table with numeric codes. Bands as percentages, quartiles. | n, 6 bands, Q1/Q2/Q3, mean, SD |
| D | 2019–2022 | Named papers, bands as counts (2020+) or percentages (2019). | n, 6 bands, Q1/Q2/Q3, mean, SD, max, min |
| E | 2023 | Empty (Marking and Assessment Boycott). | — |
| F | 2024–2025 | Gender-disaggregated. Separate stats and bands tables. | n, mean, SD, max, min, bands — all by gender |

**Note on 2020:** COVID year — 40% firsts vs typical ~23%. Excluded from all fitting and trend analysis.
</details>

<details>
<summary>Structural data format eras</summary>

| Data type | Years available | Format notes |
|-----------|----------------|--------------|
| Overall class distribution | 2011–2025 | Horizontal table (early) → vertical list (2024+) |
| Class distribution by gender | All years | Percentage table (early) → nested list (2024+) |
| Class distribution by route | 2011, 2019–2025 | Gap 2012–2018; percentages (2011) then counts+pct |
| Paper candidate numbers | All years | Paper × year table, names change over time |
| Branch-level aggregates | 2011–2025 | Percentages (all years) + mean/SD (2016+) |
| Class distribution by ethnicity | 2017–2025 | Cohort-year based, BME/White/Unknown |
| Gender statistics | All years | Prose (early) → small table → "see Section 3" (2024+) |
</details>

<details>
<summary>Known complications</summary>

- 2012 dropped the route/combination table
- 2017–2018 use numeric paper codes (need code→name mapping)
- 2023 missing per-paper statistics (boycott)
- Paper name normalisation: abbreviations, codes, degree suffixes, old regs
- HP candidates bundled into Politics numbers in early years
- 2024–2025: multiple assessment codes per paper (old/new regs)
</details>

---

## Phase 2: Analysis

All analysis code in `analysis.py`; outputs in `data/analysis/`. Run `python analysis.py` to regenerate.

### Classification rules

| Class | Average | Additional requirement |
|-------|---------|----------------------|
| 1st   | >= 68.5 | >= 2 marks of 70+, no mark below 50 |
| 2.1   | >= 59.0 | >= 3 marks of 60+ |
| 2.2   | >= 49.0 | >= 3 marks of 50+ |
| 3rd   | >= 40.0 | >= 3 marks of 40+ |
| Pass  | >= 30.0 | — |
| Fail  | < 30.0  | — |

### Completed
- [x] A1. Distribution fitting: truncated normal via MLE on pooled band data (excluding 2020). 81 papers fitted (65 bands, 16 moment estimates).
- [x] A4. Paper difficulty profiles: mu, sigma, %1st, %<50 for all papers.
- [x] A5. Temporal trends: OLS regression with 95% CIs and p-values. 3/65 papers significant (p<0.05): Philosophical Logic −1.0/yr, Microeconomic Analysis +1.65/yr, Thesis in Politics +0.38/yr.
- [x] A6. Kingmaker papers: Econometrics (σ=14.0), Game Theory (σ=12.3), Quantitative Economics (σ=10.6).
- [x] B7–9. Subject analysis: variance decomposition, weighted means/SDs, first rates by subject.
- [x] C10–11. Classification function with exact conjunctive rules, unit-tested.
- [x] D12–13. Monte Carlo engine: proportional ability loading model, ρ=0.196 calibrated to ~23% first rate (see `notes/ability_model.md`).
- [x] D14. Route validation: simulated vs observed first rates within ~1–3pp.
- [x] D15. Sensitivity analysis: 8th-paper effect ranges ~19–32% first rate.

### TODO — current sprint

#### Data quality fix
- [x] Re-extract class_distribution via LLM and rebuild canonical — fixed 2016 (5%→16%), 2017 (10%→23%), 2019 (40%→23%)
- [x] Migrate all extraction to LLM, remove regex dependency from canonical build

#### Analysis
- [x] E16. Gender gap time series: persistent ~8-10pp gap (M > F), no clear closing trend. One reversal (2011).
- [x] F21. Popularity vs difficulty: popular papers are slightly harder (r=-0.28, p=0.013) AND more volatile (r=0.32, p=0.004).

#### Visualisation & summary tables
- [x] K32. Gender gap time series chart
- [x] K33. Paper popularity vs difficulty scatter (mean and SD), coloured by subject
- [x] K34. Subject-level summary table
- [x] K35. Paper difficulty ranking table
- [x] K36. Temporal trends summary table
- [x] K37. Kingmaker papers chart

### TODO — later

#### Further analysis
- [x] A2. Validate pooled fit against individual years — 15/222 paper-years fail (vs 11 expected by chance). Pooled fit adequate.
- [x] A3. Asymmetry check — 3/60 papers significantly skewed, mean |Bowley skew|=0.14. Truncated normal adequate.
- [x] J29. Marginal paper value — supervised dissertation best (+5.4pp), Finance worst (−3.3pp). Range ~20–29% first rate.
- [x] J31. Bootstrap CIs — P(1st) = 23.2% [21.2%, 26.0%] for default papers. 200 bootstrap resamples.
- [x] F20. Paper popularity time series (share-based, current papers only) — 9 growing, 22 declining. Niche papers losing share to a few growing ones.
- [x] F22. Subject market share — stable: Econ ~33%, Phil ~30%, Pol ~36%.
- [x] H25. COVID 2020 — per-paper means barely shifted (+0.3 marks) despite first rate doubling (23%→40%). Anomaly was at classification stage, not marking.
- [x] H26. 2023 boycott — no significant residual in 2024 (p=0.10).
- [x] I27+I28. Web bundle — 81-paper catalogue with fits, profiles, marginal values, route summaries, aliases.
- [ ] E17. Gender gap by route
- [ ] E18. Per-paper gender analysis (2024–2025)
- [ ] E19. Gender-disaggregated simulation
- [ ] G23. Ethnicity attainment gap over time
- [ ] G24. Compare PPE ethnicity gaps to university-wide — needs external data, probably infeasible
- [ ] J30. Correlation structure validation — infeasible without individual-level data; see notes/selection_and_ability.md

---

## Phase 3: Web Tool — IMPLEMENTED

Static site (HTML + CSS + JS) with chalkboard aesthetic. All data pre-computed and bundled as JSON (`web/data.json`, ~59KB). No backend — runs entirely in the browser.

### Build pipeline

- `python web/build.py` — fills `template.html` copy placeholders from `web/copy/*.md` → produces `index.html`
- `python web/serve.py` — dev server with live reload (watches .js, .css, .md, template.html)
- `python analysis.py` — regenerates `web/data.json` from canonical data

### Architecture

- Hash-routed SPA: `#calculator`, `#explorer`, `#overview`, `#methodology`
- Chart.js for all interactive charts
- KaTeX for math rendering (copyable)
- URL query params for shareable state (`?papers=A|B|...&ability=75`)
- SVG feTurbulence/feDisplacementMap for hand-drawn border effects
- Copy source of truth: `web/copy/*.md` → `template.html` placeholders → `index.html`

### Pages — all implemented

1. **Calculator** — Paper picker (grouped by subject, searchable), ability slider, Monte Carlo results (50k draws), paper swap suggestions, what-if comparison vs typical papers, per-paper breakdown
2. **Explorer** — Scatter plot (mean vs volatility, bubble size = popularity), paper profiles with sparkline, kingmaker list, trend badges on cards, filter by subject, sort/search
3. **Overview** — First-class rate (with COVID expandable), gender gap, subject comparison, classification breakdown, score trends, popularity trends. Sticky full-width ToC with scroll-spy.
4. **Methodology** — Full model description with KaTeX-rendered math

### What-if: implemented
- **Comparison to typical papers:** "At your ability level, if you'd picked the 8 most popular papers instead, your P(1st) would be X% (currently Y%)."
- **Best swap suggestion:** Pre-computed marginal paper values identify the single swap with highest P(1st) impact.

### What-if: Conditional marks mode (next to implement)

**Use case**: "I'm taking these 8 papers. Assume Ethics and Nic Eth are quite mid and Micro Analysis goes badly. What do I need in the other papers to get a First?"

The value is NOT just "what average do you need" (trivial arithmetic) — it's:
1. Contextualising qualitative language ("mid", "badly") into paper-specific marks and percentiles
2. Showing what percentile the remaining papers need to be at
3. Accounting for conjunctive rules (2 marks of 70+, no mark below 50) not just the 68.5 average

**Design:**

- In Calculator, after selecting papers + ability, user can optionally **fix marks** on any subset of papers (1–7; at least 1 must remain free)
- Each fixable paper gets a mark input (number field or slider) with contextual info:
  - "55 = 30th percentile for this paper" (derived from fitted distribution)
  - Qualitative label: "well below average" / "below average" / "average" / "above average" / "strong"
- Fixed marks are **not** simulated — they're treated as constants
- Remaining (free) papers are still simulated via the proportional loading model, conditioned on the same latent ability θ

**Output — "what do I need?" framing:**

Rather than just showing P(First) given fixed marks, answer the question inversely:
- "To have a ≥50% chance of a First, you need to perform at roughly the **Xth percentile** across your remaining papers"
- Show this as a binary search over θ (or equivalently, over the ability slider)
- Also show: "That translates to roughly [mark₁, mark₂, ...] in your free papers" (expected marks at that percentile for each paper)
- And: "Key constraint: you need 2+ marks of 70. At this level, P(getting 2+ of 70) in your free papers = Y%"

**Implementation approach:**

1. UI: Add a "Fix marks" toggle/section below paper picker. When active, each selected paper shows a mark input (disabled by default, click to fix).
2. Engine: New function `simulateConditional(papers, fixedMarks, ability, nDraws)`:
   - For each draw: set fixed papers to their fixed marks, simulate free papers as normal
   - Classify as usual, return distribution
3. Threshold search: Binary search over ability percentile to find where P(target_class) crosses 50% (or user-chosen threshold)
4. Display: Show both the "given these marks, here's your distribution" AND the "here's what you need" inverse framing

**Stretch features:**
- Preset mark suggestions: "quite mid" = paper mean, "badly" = mean − 1σ, "well" = mean + 1σ
- "What if I ace one paper?" — show impact of moving a free paper to 75+
- Shareable URL: `?papers=A|B|...&fixed=A:55,B:60&ability=75`

### Popularity trends chart — rethink

Current: horizontal bar showing total pp change in share of sittings. The chart fits OLS to each paper's share over all available years (2023 excluded — no data due to boycott). "Change" = slope × time span. Significance test uses OLS standard error on slope.

Problem: doesn't show absolute sizes, hard to interpret without context.

Options:
- Sized-dot scatter (x = avg share, y = change pp, radius = latest n)
- Arrow chart: start-share → end-share
- Slope chart: first-year share vs last-year share

### Other planned features (not yet implemented)

- [ ] Ability shift comparison: "If you were one tier higher, your P(1st) would go from X% to Y%"
- [ ] Risk profile: P(dropping below 2.1) — downside risk framing
- [ ] Head-to-head paper comparison in Explorer
- [ ] Interactive hero graph on landing page (stretch goal)
- [ ] Deploy to GitHub Pages
- [ ] Mobile responsiveness pass

---

## Data Quality & Pipeline Fixes

### Problem 1: 2024/2025 per-paper extraction is incomplete (59% miss rate)

**Findings** (see `audit_data_gaps.py` for full audit):

The LLM extraction for 2024 and 2025 only captured ~34 of ~70 papers each year. The missed papers include very large ones (Theory of Politics n=112, Quantitative Economics n=110, Political Sociology n=87).

**Root cause**: The 2024–2025 reports split per-paper stats across multiple tables/sections. The LLM is extracting only one section (the gender-disaggregated table, which covers ~34 papers with All/M/F breakdowns). A second section with aggregated stats for remaining papers (especially Philosophy and Politics) is being missed entirely.

Evidence:
- Captured papers: 12 Econ, 9 Pol, 5 Phil
- Missed papers: 5 Econ, 17 Pol, 21 Phil
- Not an n-threshold issue: papers with n=112, 110, 87 are missed
- Some missed papers (Phil Logic n=9, Thesis in Politics n=11) likely have only aggregate stats because small n prevents gender disaggregation

**Fix needed in `llm_extract.py`**:
- [ ] Strengthen the per_paper prompt to explicitly mention that 2024–2025 reports have MULTIPLE sections with per-paper stats (likely Section 2 and Section 3, or by subject area)
- [ ] Tell the LLM to look for ALL tables with paper-level statistics, not just the first/largest one
- [ ] For papers with small n that aren't gender-disaggregated, emit a single gender="All" row
- [ ] Re-run extraction for 2024 and 2025: `python llm_extract.py --year 2024 --section per_paper` and same for 2025
- [ ] Run `python audit_data_gaps.py` to verify improvement

**Also**: Phil Logic 2025 has a record but mean=None — the LLM saw the paper but didn't extract its stats. The data exists in the report (n=7, mean=64.1, SD=5.1).

### Problem 2: Earlier years have minor gaps

2016–2022 have 7–20% miss rates, mostly papers with n ≤ 5 where stats are suppressed. A few anomalies:
- 2019: Missing "Special Subject in Politics: International Security and Conflict" (n=44) and "Comparative Political Economy" (n=24)
- 2020: Missing "Comparative Political Economy" (n=22)

These are worth re-extracting too, but lower priority than the 2024/2025 gap.

### Problem 3: Alias mismatches (paper_numbers vs per_paper)

Some papers appear in per_paper but NOT in paper_numbers for certain years (e.g. Econometrics, Game Theory in 2015–2019). Possibly these are Economics papers reported in the per-paper stats table but listed under a different name in the paper_numbers table.

- [ ] Investigate and fix alias mapping for these papers

### Problem 4: `web/data.json` pipeline — FIXED

`bundle_web_data()` in `analysis.py` now produces all 15 keys the web tool needs, and the runner writes directly to `web/data.json`. Pipeline is deterministic: `python analysis.py` → `web/data.json`.