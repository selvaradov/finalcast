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

Static site (HTML + CSS + JS) with chalkboard aesthetic. All data pre-computed and bundled as JSON (`web/data.json`, ~59KB). No backend — runs entirely in the browser. Minimal build step: `python web/build.py` syncs copy from `web/copy/*.md` into `index.html`.

### Architecture

- Hash-routed SPA: `#calculator`, `#explorer`, `#overview`, `#methodology`
- Chart.js for all interactive charts
- KaTeX for math rendering (copyable)
- URL query params for shareable state (`?papers=A|B|...&ability=75`)
- SVG feTurbulence/feDisplacementMap for hand-drawn border effects

### Pages — all implemented

1. **Calculator** — Paper picker (grouped by subject, searchable), ability slider, Monte Carlo results (50k draws), paper swap suggestions, what-if comparison vs typical papers, per-paper breakdown
2. **Explorer** — Scatter plot (mean vs volatility), paper profiles, temporal trends (significant + near-sig), popularity shifts, filter/sort/search
3. **Overview** — First-class rate time series, gender gap, subject comparison, classification breakdown, score trends chart, popularity growth rates, COVID/kingmaker callouts, ToC
4. **Methodology** — Full model description with KaTeX-rendered math

### What-if: implemented
- **Comparison to typical papers:** "At your ability level, if you'd picked the 8 most popular papers instead, your P(1st) would be X% (currently Y%)."
- **Best swap suggestion:** Pre-computed marginal paper values identify the single swap with highest P(1st) impact.

### What-if: planned ideas (not yet implemented)

1. **Fix marks on some papers:** Student enters estimated marks for 1–3 papers. Simulation conditions on those marks and simulates only the remaining papers.
2. **Ability shift comparison:** "If you were one tier higher, your P(1st) would go from X% to Y%."
3. **Best possible 8 papers at your level:** Paper combination that maximises P(1st).
4. **Risk profile:** P(dropping below 2.1) — downside risk framing.
5. **Subject-lock comparison:** How route choice interacts with ability.
6. **Mark threshold analysis:** How many 70+ marks needed for a realistic First shot.

### Remaining TODOs
- [ ] Interactive hero graph on landing page (stretch goal)
- [ ] Head-to-head paper comparison in Explorer
- [ ] Deploy to GitHub Pages
- [ ] Mobile responsiveness pass