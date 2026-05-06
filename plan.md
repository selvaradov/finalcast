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
- **per_paper**: 912 records, 2015–2022 + 2024–2025 — mean, SD, bands, quartiles per paper
- **paper_numbers**: 1326 records, 2005–2025 — candidate count per paper per year
- **paper_aliases**: 95 canonical papers mapped from ~400 name variants

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

### Other planned features (not yet implemented)

- [ ] Ability shift comparison: "If you were one tier higher, your P(1st) would go from X% to Y%"
- [ ] Risk profile: P(dropping below 2.1) — downside risk framing
- [ ] Head-to-head paper comparison in Explorer
- [ ] Interactive hero graph on landing page (stretch goal)
- [ ] Deploy to GitHub Pages
- [ ] Mobile responsiveness pass

---

## Data Quality & Pipeline Fixes

Execution order: Problem 5 (feminist theory) → Problem 3 (aliases) → Problem 1 (2024/25) → Problem 2 (earlier years) → Problem 6 (dedup).

### Problem 1: 2024/2025 per-paper extraction is incomplete — RESOLVED

**Root cause**: Token limit truncation + prompt not emphasizing multi-section structure.

**Fix applied** (`llm_extract.py`):
- Rewrote PER_PAPER_PROMPT to explicitly instruct extraction of ALL per-paper tables across multiple sections
- Added per-section max_tokens config: `per_paper` → 64000 tokens (vs 16000 default)
- Converted `call_llm` to streaming API (required for >10 min operations at 64k tokens)
- Re-extracted 2024 and 2025

**Result**: Coverage by paper count: 87–88%. Population-weighted coverage: **99.3%** (all uncovered papers have n≤2, so they represent <1% of candidate-paper-sittings).
- 2024: 9 papers missing, all n≤2
- 2025: 8 papers missing, all n≤2

### Problem 2: Earlier years have minor gaps — RESOLVED

**Fix applied**:
- Re-extracted 2020 per_paper with improved prompt → all n>2 papers now captured
- Merged "Feminism and Philosophy" into "Feminist Theory" alias (same paper, code 198, renamed over time)
- Merged "Special Subject in Politics: CPE" into "Comparative Political Economy" alias (same paper, different era naming)

**Remaining gaps** (all genuine — suppressed in source or not in per-paper table):
- 2016: 11 papers missing, 4 with n=4–5 (politics papers not in per-paper table in that era's format), rest n≤3
- 2019: 7 papers missing, largest is Feminist Theory n=4 (likely suppressed), rest n≤2
- 2020: 9 papers missing, all n≤2

### Problem 3: Alias mismatches (paper_numbers vs per_paper) — RESOLVED

Economics papers (Econometrics, Game Theory, Mathematical Methods, Philosophy and Economics of the Environment) consistently appear in per_paper stats but NOT in paper_numbers for 2015–2019.

**Investigation result**: These are NOT alias issues. The paper_numbers tables in 2015–2017 reports only listed Philosophy and Politics papers (100/200-series codes). Economics papers (300-series) were not included in candidate count tables until 2018. For 2018–2019, a handful of newer economics papers (Behavioural Economics, Finance) aren't in paper_numbers because they weren't reported there either. All raw names across all years ARE properly aliased — verified with diagnostic script.

Remaining mismatches after fixes (all genuine data gaps, not fixable):
- 2015 (7): economics papers not in paper_numbers table
- 2016 (4): same
- 2017 (4): same
- 2018 (3): Behavioural & Experimental Economics, Econometrics, Game Theory — not in paper_numbers
- 2019 (11): various economics papers + Environmental Economics special subject + Special Subjects in Philosophy catch-all

**Fix** (completed):
- [x] Wrote diagnostic scripts (`tmp_diagnose_aliases.py`, `tmp_unaliased_names.py`) to check all raw names
- [x] Confirmed all raw names are in the alias_map — no missing aliases
- [x] Removed incorrect "297. Special subject in Politics" → Feminist Theory alias (fixed in Problem 5)
- [x] Added new alias variants for CPE and ISC with "297. Special subject in Politics:" prefix
- [x] Re-ran `python build_canonical.py` and verified with `python audit_data_gaps.py`

### Problem 4: `web/data.json` pipeline — FIXED

`bundle_web_data()` in `analysis.py` now produces all 15 keys the web tool needs, and the runner writes directly to `web/data.json`. Pipeline is deterministic: `python analysis.py` → `web/data.json`.

### Problem 5: Feminist Theory — split paper with divergent sigma

**Findings**: "Feminist Theory" exists as two separate canonical papers:
- `Special Subject in Philosophy: Feminist Theory` — fitted sigma=1.18 (1 year, n=19)
- `Special Subject in Politics: Feminist Theory` — fitted sigma=4.38 (2 years, n=80)

These are the **same exam paper** taken by candidates from different degree routes (PPE vs HP). The subject tag reflects which route reports it, not different content or marking.

The sigma discrepancy (1.18 vs 4.38) is a small-n MLE artefact: with only 19 observations spread across 2 bands (8 in ≥70, 10 in 60–69, 1 in 50–59), the optimiser finds an implausibly tight distribution. σ=1.18 is not credible for any exam.

**Additional issue**: The 2019 per_paper data contains TWO records for "Special Subject in Politics: Feminist Theory" (n=24 and n=44). The n=44 record is almost certainly **misattributed** — paper_numbers shows "International Security and Conflict" at n=44 for 2019, while Feminist Theory (Phil) has n=4. The n=44 record's stats (mean=66.1, sd=3.5, max=73) are likely International Security's data.

**Fix**:
- [x] Verify 2019 misattribution by checking the raw PDF (the n=44 record with mean=66.1 should be International Security)
  - Confirmed: paper_numbers shows ISC at n=44, CPE at n=24 for 2019. The two "297. Special subject in Politics" records were ISC and CPE, not Feminist Theory.
- [x] Merge both papers into one canonical name in `paper_aliases.json` → "Special Subject: Feminist Theory"
- [x] Fix the 2019 misattributed record — raw data corrected to use specific paper names (CPE n=24, ISC n=44)
- [x] Removed ambiguous "297. Special subject in Politics" → Feminist Theory alias (was incorrect for 2019)
- [ ] Re-fit the merged paper — combined data: 2022 n=19+12=31 → should give a more reliable sigma estimate
- [ ] Document in methodology: small-n papers (n<30 per pool) produce unreliable sigma estimates; merging cross-route pools is necessary

**Implications for fitting reliability**: When the same paper is split into sub-pools of n<20, the MLE fitting is unreliable. This suggests we should:
1. Always merge cross-route/cross-subject instances of identical papers
2. Flag papers with n_total < 30 as having uncertain sigma estimates
3. Consider whether other papers have similar splits (check "Special Subjects in Philosophy (other)" catch-all)

### Problem 6: Duplicate per_paper records (no deduplication) — RESOLVED

**Findings**: `build_canonical.py` does NOT deduplicate per_paper records (line 111: "no dedup needed" — but this is wrong). 29 (year, paper, gender) groups have duplicates, totalling 79 records that should collapse to 29. These fall into 5 distinct categories:

**Category 1: Component papers (16 groups)** — Papers with separate Essay/Exam/Coursework stats plus a Combined aggregate. All three/four records share the same n (same candidates, different assessment components).
- Jurisprudence: (Combined), (Essay), (Exam) in 2016, 2020–2022, 2024–2025
- Environmental Economics: (Combined), (Coursework), (Exam), (Exam old syllabus) in 2024–2025
- Labour Economics and Inequality: base + (A16893H1), (A16894H1) in 2025 (assessment codes)
- **Fix**: Keep only the "Combined"/base record (it represents the final mark the student receives). The component marks aren't what gets classified.

**Category 2: Old/new regs (5 groups)** — Same paper offered under transitional regulations alongside current regs. The "old regs" cohort is tiny (n=7–12) vs the main cohort (n=98–138).
- Theory of Politics 2019: n=98 (main) + n=20 (code 114) + n=7 (old regs)
- Macroeconomics 2019: n=137 (main) + n=7 (old regs)
- Microeconomics 2019: n=135 (main) + n=8 (old regs)
- Quantitative Economics 2020: n=138 (main) + n=12 (old syllabus)
- International Relations 2021: n=121 (main) + n=7 (old syllabus)
- **Fix**: Keep the largest-n record only. The old-regs cohort is a remnant sitting the same exam under a legacy code. Including both inflates the pooled n and may skew the distribution (old-regs cohorts often have different ability profiles — e.g. Microeconomics old regs has mean=59.3 vs 64.4 for main).

**Category 3: Route splits (2 groups)** — Same paper reported separately for PPE route (code 114) and HP route (code 203). Different candidate pools sitting the same paper.
- Theory of Politics 2017: n=37 (code 203/PPE) + n=93 (code 114/HP)
- Theory of Politics 2018: n=28 (code 203) + n=85 (code 114)
- **Fix**: Keep the largest-n record (the main PPE cohort, code 114, which has the more representative distribution). The smaller route pool is a subset with different selection effects.

**Category 4: Exact duplicates (3 groups)** — Same paper extracted under two name variants with identical stats.
- Early Modern Philosophy 2018: "Early Modern Philosophy" and "Early Modern Philosophy (129)"
- Comparative Demographic Systems 2018: "CDS (pre-2016 see 315)" and "Comparative Demographic Systems"
- Sociology of Post-Industrial Societies 2018: two abbreviation variants
- **Fix**: Keep either (they're identical).

**Category 5: Cross-route merges (1 group)** — Same paper reported by Phil and Pol departments with different n (different route pools). Created by the Problem 5 Feminist Theory merge.
- Feminist Theory 2022: n=19 (Phil route) + n=12 (Pol route)
- **Fix**: Keep the largest-n record for fitting. Ideally these would be combined (n=31, weighted mean), but that requires recomputing stats from band data. For now, largest-n is adequate.

**Dedup priority rules** (for `build_canonical.py`):
1. Discard component records: if raw name contains "(Essay)", "(Exam)", "(Coursework)", or matches an assessment code pattern like `(A\d+H\d+)`, discard in favour of the base/Combined record
2. Discard old regs: if raw name contains "(old regs)" or "(old syllabus)", discard
3. Among remaining duplicates: prefer record with bands data over one without; then prefer highest n
4. Exact ties: keep first encountered

**Fix** (implemented in `build_canonical.py`):
- [x] Added `deduplicate_per_paper()` implementing the priority rules above
- [x] Preserves raw names (`_raw_name`) through the pipeline for component detection
- [x] Result: 912 → 852 records (60 duplicates removed, zero duplicate groups remain)
- [x] Added `reliable` flag to paper fits: requires n_total ≥ 30 AND σ ≥ 2.0
- [x] Kingmaker analysis now filters on reliability (removed spurious "Politics in Europe" σ=16.33 from n=11)
- [x] 53/79 fitted papers are reliable; 26 flagged as low-confidence