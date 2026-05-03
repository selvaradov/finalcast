# PPE Finals Results Analysis — Project Plan

## Goal

Extract 15 years of Oxford PPE Final Honour School examiners' report data (2011–2025) into structured JSON, analyse mark distributions, and build an interactive web tool where a student enters their paper choices and sees an estimated prior distribution over degree classifications.

---

## Phase 1: Data Extraction

### 1.1 Source material

15 PDF reports in `./reports/`, one per year. All are internal examiners' reports for the FHS of PPE.

### 1.2 Format eras

The report format changes substantially across the 15 years. There are **5 distinct format eras** for per-paper statistics, and **3 eras** for structural/route data.

#### Per-paper statistics formats

| Era | Years | Format | Key columns |
|-----|-------|--------|-------------|
| **A** | 2011–2014 | **No per-paper stats table.** Only aggregate subject-level averages mentioned in prose (e.g. "Philosophy, 65.6; Politics, 65.2; Economics, 64.7"). | Subject mean, SD only (from prose) |
| **B** | 2015–2016 | Simple table, one row per paper: paper name, average mark, standard deviation, highest mark, lowest mark. Grouped by subject (Philosophy / Politics / Economics / Joint School Papers). No paper codes, no bands, no quartiles. | mean, SD, min, max |
| **C** | 2017–2018 | Rich table with numeric paper codes. Columns: Code, Candidates, >=70, >=60, >=50, >=40, >=30, <30, Q1, Median, Q3, Mean, St.Dev. Papers with <=2 candidates suppressed; papers with <=5 show only mean and SD. | n, 6 band percentages, Q1, median, Q3, mean, SD |
| **D** | 2019–2022 | Like era C but with paper names instead of codes, and no quartiles. Columns: Paper, Cands, >=70, >=60, >=50, >=40, >=30, <30, Q1, Median, Q3, Mean, St. Dev, Max, Min. Same suppression rules. | n, 6 band counts, Q1, median, Q3, mean, SD, max, min |
| **E** | 2023 | **Empty.** The section header "3. Statistics by Paper" exists but no table follows (likely due to the Marking and Assessment Boycott that year). | Nothing available |
| **F** | 2024–2025 | Richest format. Per-paper stats broken down by gender. Columns: Paper name, assessment code, gender (F/M), Number of students, Average mark, Standard deviation, Maximum mark, Minimum mark. Also a separate bands-of-marks table by gender with columns: >=70, 60-69, 50-59, 40-49, 30-39, <30, No result. | n, mean, SD, max, min — all by gender. Band counts by gender. |

**Note on 2020:** COVID year. 40% firsts (vs typical ~22%). Data is still present in era D format but outcomes are anomalous.

#### Class distribution & structural data formats

| Data type | Years available | Format notes |
|-----------|----------------|--------------|
| **Overall class distribution** | All years (2011–2025) | Always a table with year columns showing counts and percentages for 1st, 2.1, 2.2, 3rd, etc. Format varies (horizontal table in early years, vertical list in 2024–2025). |
| **Class distribution by gender** | All years | Percentage table (early years) or nested list (2024–2025). Early years give percentages only; later years give both counts and percentages. |
| **Class distribution by route/combination** | 2011 (Phil/Pol, Pol/Econ, Phil/Econ, Tripartite as %). 2012: explicitly dropped ("now laborious to compile"). 2013–2018: not present. 2019–2025: returned as "Classifications broken down by routes through PPE" with Phil-Econ, Pol-Econ, Phil-Pol, PPE categories showing counts and percentages. | Two different formats with a gap. |
| **Paper candidate numbers** | All years | Table of paper names × years, one row per paper. Format and paper names change over time. |
| **Branch-level aggregates** (% papers in each branch, avg mark/SD by branch) | 2011 has branch percentages. 2012–2015: branch percentages only. 2016–2025: both percentages and mean/SD/total by branch, often broken down by gender (2024–2025). | |
| **Class distribution by ethnicity** | 2017–2025 | Landscape table, cohort-year based (year of entry, not exam year). BME/White/Unknown categories. Messy layout. |
| **Average mark and SD by gender** | All years | Either in a small table or in prose text. |

### 1.3 Extraction approach

**Method:** `pdftotext -layout` → regex parsing in Python.

The `-layout` flag produces clean fixed-width column output for all these reports. Each format era needs its own parser, but within an era the format is consistent.

### 1.4 Parser implementation details

We need the following parsers. Each operates on the full text output of `pdftotext -layout` for a single report.

#### Parser 1: Overall class distribution

**Input years:** 2011–2025

**Era A (2011–2018):** Horizontal table. Columns are years. Rows are: I/1st, II.1/2.1, II.2/2.2, III/3rd, Honours Pass, Unclassified, Fail, Total. Each cell has a count and a percentage (sometimes on the same line, sometimes on the next line).

Strategy:
- Find the class distribution table by searching for a line matching `Class` or `I` near the start of Part A.
- The 2011 format has bare class labels (I, II 1, II 2, III) with year columns. Parse column positions from the header row.
- The 2018 format has labelled rows (1st, 2.1, 2.2, 3rd) with percentage on the next line.
- Extract: `{report_year, data_year, class, count, percentage}` tuples.
- Extract **all** year columns, not just the current year. This enables cross-validation.

**Era B (2019–2023):** Vertical table. Rows are year headers with sub-rows for each class. Columns: Class, Number of students (or count), Percentage.

Strategy:
- Find lines with year headers (e.g. "2019") followed by indented class lines.
- Extract all year blocks present in the table.

**Era C (2024–2025):** Like era B but with named classifications ("First Class", "Second Class, Division One", etc.) and "Number of students" / "As a Percentage" column headers.

Strategy:
- Same as era B with adjusted label matching. Extract all year blocks.

#### Parser 2: Class distribution by gender

**Input years:** 2011–2025

**Era A (2011–2018):** Horizontal percentage table. Columns alternate M/F for each year. Rows are class labels.

Strategy:
- Find the gender class distribution table (look for "class distributions by sex" or "by gender").
- Parse the M/F column headers and year row.
- Extract: `{year, gender, class, percentage}`. Counts are available separately (total candidates by gender).
- Total candidate counts and overall average mark/SD by gender are in a separate small table or prose paragraph.

**Era B (2019–2023):** Semi-tabular. Year header, then F/M sub-headers, then class rows with percentages under each.

Strategy:
- Identify year blocks, then gender sub-blocks with class percentages.
- Counts come from a "Total" row.

**Era C (2024–2025):** Nested vertical list: Year → Gender (F/M) → Classification → count + percentage.

Strategy:
- Parse the nested indented structure.

#### Parser 3: Per-paper statistics

**Input years:** 2015–2022, 2024–2025 (skip 2011–2014 and 2023)

**Era B (2015–2016):** Simple 4-column table grouped by subject heading.

Format:
```
Paper                    Average    Standard    Highest    Lowest
                                    Deviation   Mark       Mark
Ethics                   65         6.1         48         83
```

Strategy:
- Find subject headers ("a. Philosophy Papers", "b. Politics Papers", "c. Economics Papers", "d. Joint School Papers").
- Within each section, parse rows with paper name followed by numeric columns.
- Handle "X candidates only" lines (no stats available).
- Extract: `{year, paper_name, subject, mean, sd, max, min}`.

**Era C (2017–2018):** Code-based table with bands and quartiles.

Format:
```
Code  Candidates  >=70  >=60  >=50  >=40  >=30  <30  Q1    Median  Q3    Mean  St.Dev.
101   34          12%   85%   3%                      67.0  65.0    64.0  65.6  3.1
```

Strategy:
- Find the "Statistics by Paper" or "3." section.
- Parse fixed-width columns. The code column is 3-digit numeric (sometimes with a parenthetical suffix like "(FoEA)").
- Band values are percentages (strip %). Some cells are empty (meaning 0%).
- Q1/Median/Q3 are floats. Mean and SD are floats.
- Papers with <=5 candidates only have Mean and SD.
- Papers with <=2 candidates have no stats at all.
- Cross-reference codes with the paper-name table (Section 4) to get names.
- Extract: `{year, paper_code, n, bands: {70+, 60-69, 50-59, 40-49, 30-39, <30}, q1, median, q3, mean, sd}`.

**Era D (2019–2022):** Named paper table with bands, quartiles, max, min.

Format:
```
Paper                    Cands  >=70  >=60  >=50  >=40  >=30  <30  Q1    Median  Q3    Mean  St. Dev  Max  Min
Ethics                   149    23%   68%   9%    0%    0%    0%   69.0  66.0    62.0  65.5  4.5      78   54
```

Strategy:
- Find the stats table. Paper names can wrap to multiple lines.
- Parse: name (may span 2-3 lines), then numeric columns.
- Band values may be percentages (2019 uses "%") or counts (2020–2022 use raw numbers) — need to check each year.
- Extract: `{year, paper_name, n, bands, q1, median, q3, mean, sd, max, min}`.

**Special case — 2019 vs 2020–2022 band format:**
- 2019 uses percentage strings like "23%"
- 2020+ uses integer counts like "25"
- Need to detect which format is used and normalise.

**Era F (2024–2025):** Gender-disaggregated table. Two separate sub-tables:
1. **3a. Average mark, SD, max, min by assessment and gender:** Nested rows — paper name → assessment code → gender (F/M). Columns: Number of students, Average mark, Standard deviation, Maximum mark, Minimum mark.
2. **3b. Bands of marks by assessment and gender:** Same nesting. Columns: Number of students, >=70, 60-69, 50-59, 40-49, 30-39, <30, No result.

Strategy:
- Parse the nested structure: detect paper name lines (left-aligned text with no leading spaces or at column 1), assessment code lines (indented, starting with "A" + digits), gender lines (further indented, "F" or "M").
- Numeric columns are right-aligned; use column position detection from headers.
- Aggregate to paper level (sum across assessment codes if multiple exist for one paper).
- Extract: `{year, paper_name, assessment_code, gender, n, mean, sd, max, min}` and `{year, paper_name, assessment_code, gender, n, bands}`.

#### Parser 4: Paper candidate numbers

**Input years:** 2011–2025

All years have a table of paper names × historical years showing candidate counts. The structure is similar across eras but paper names and groupings evolve.

Strategy:
- Find the "Numbers offering each paper" section (or "Numbers Offering Each Paper").
- Parse subject sub-sections (Philosophy, Politics, Economics).
- Within each, parse paper name (first column, variable width) and year columns (numeric, sometimes with parenthetical HP numbers like "(20)").
- For HP numbers in parentheses, strip them and record only the PPE count.
- Extract **all** year columns (enables cross-validation across reports).
- Extract: `{report_year, data_year, paper_name, subject, n}`.

**Complications:**
- 2011–2014: Politics numbers include HP candidates shown as "(X)" on the next line. Need to subtract or ignore these.
- 2012 note: "this one omits statistics for the number of candidates and the percentage class distributions by combination offered" — but still has the paper numbers table.
- Some papers have bracketed notes like "(old regs)" or "(submission)".

#### Parser 5: Class distribution by route/combination

**Input years:** 2011 (percentage table), 2019–2025 (count + percentage table). Gap for 2012–2018.

**2011 format:** Horizontal percentage table.
```
           1      2(1)     2(2)    3     Hons Pass   Total
Phil/Pol   18.3   78.5     2.2     0     1.1         100
```
- Routes: Phil/Pol, Pol/Econ, Phil/Econ, Tripartite.

**2019–2025 format:** Table with route columns and class rows.
```
Class    Phil-Econ  Pol-Econ  Phil-Pol  PPE
1st      9          23        20        4
         25%        25%       21%       21%
```
- Extract: `{year, route, class, count, percentage}`.
- 2023 has this data despite missing per-paper stats.

#### Parser 6: Branch-level statistics

**Input years:** 2011–2025 (percentages), 2016–2025 (mean/SD/total by branch)

**Branch percentages:** Simple table: branch × year → percentage of papers in that branch.

**Branch mean/SD:** Table with nested structure: year → branch → gender (in later years) → mean, SD, total.

Strategy:
- Find "Statistics by branch" or "Approximate percentages".
- Parse the percentage table (simple columnar data).
- Parse the mean/SD table (more complex, varies by era).
- Extract: `{year, branch, pct_papers}` and `{year, branch, gender?, mean, sd, total}`.

#### Parser 7: Subject-level aggregates (2011–2014 only)

For the early years without per-paper tables, extract subject-level mean and SD from prose text.

Pattern: "The average marks were (YYYY figures in brackets): for all scripts, X.X (Y.Y); for Philosophy, X.X (Y.Y); for Politics, X.X (Y.Y); for Economics, X.X (Y.Y)."

And: "The standard deviations were: for Philosophy X.X; for Politics X.X; for Economics X.X."

Strategy:
- Regex match these patterns in the full text.
- Extract: `{year, subject, mean, sd}`.
- This overlaps with the branch-level parser but is the only source for 2011–2014.

#### Parser 8: Overall gender statistics

**Input years:** 2011–2025

Extract total candidates, average mark, and SD by gender.

**2011–2014:** Prose text. E.g.: "In 2011 103 (45.0%) of the 229 candidates were female... The average mark for female candidates was 65.1 (standard deviation was 5.8) and the average mark for male candidates was 65.2 (standard deviation was 6.1)."

**2015–2018:** Small table:
```
                 2018            2017
             F       M       F       M
Total Cand   79      151     76      162
Avg Mark     64.9    64.6    64.3    65.2
St. Dev.     5.2     6.5     6.9     6.8
```

**2019–2023:** Similar table with "Average" and "St. Dev." rows.

**2024–2025:** "See Section 3, statistics by paper" — need to derive from branch-level gender stats or the gender class distribution counts.

Strategy:
- Try tabular parse first, fall back to prose regex.
- Extract: `{year, gender, total, mean, sd}`.

### 1.5 Output format

All extracted data stored as JSON files in `./data/`. There are two tiers:

**Tier 1 — Raw extractions (all observations, including duplicates from overlapping reports):**

```
data/raw/
  class_distribution.json        # [{report_year, data_year, class, count, pct}, ...]
  class_by_gender.json           # [{report_year, data_year, gender, class, count?, pct}, ...]
  class_by_route.json            # [{report_year, data_year, route, class, count?, pct}, ...]
  class_by_ethnicity.json        # [{report_year, data_year, demographic, class, count, pct}, ...]
  paper_stats.json               # [{report_year, data_year, paper, subject?, n, mean, sd, min?, max?, q1?, median?, q3?, bands?}, ...]
  paper_stats_by_gender.json     # [{report_year, data_year, paper, gender, n, mean, sd, min?, max?}, ...]
  paper_bands_by_gender.json     # [{report_year, data_year, paper, gender, n, bands}, ...]
  paper_candidates.json          # [{report_year, data_year, paper, subject, n}, ...]
  branch_stats.json              # [{report_year, data_year, branch, pct_papers, mean?, sd?, total?, gender?}, ...]
  gender_stats.json              # [{report_year, data_year, gender, total, mean, sd}, ...]
  subject_aggregates.json        # [{report_year, data_year, subject, mean, sd}, ...]
```

**Tier 2 — Canonical (deduplicated after cross-validation):**

```
data/canonical/
  (same filenames as above, but with report_year removed — one row per data_year)
```

**Cross-validation report:**

```
data/cross_validation.json       # [{dataset, data_year, field, values_by_report_year, status: "consistent"|"discrepancy"}, ...]
```

Where `status: "discrepancy"` entries list which reports disagree and what the canonical resolution was (latest report wins, unless an earlier correction note is found).

Optional `?` fields are null/absent when not available for that year's format.

### 1.6 Implementation plan

1. Write a `extract.py` script with a class per parser.
2. Each parser takes a `(year: int, text: str)` tuple and returns a list of dicts.
3. A top-level loop iterates over all PDFs, calls `pdftotext -layout`, runs all parsers, and collects results.
4. **Extract all years from every report, not just the report's own year.** Most tables contain several years of historical data. We extract everything and tag each record with both `report_year` (which PDF it came from) and `data_year` (the year the data describes).
5. Write JSON output (one record per `(data_year, report_year, ...)` tuple).
6. **Cross-validation pass:** For each data point that appears in multiple reports (e.g. the 2017 class distribution appears in the 2017, 2018, 2019, ... reports), compare all instances. Flag discrepancies. This gives us:
   - **Parser correctness checks:** If the same number is consistently extracted from 5+ reports, we can be confident the parser is working. If one report disagrees, it's likely a parsing bug for that specific layout.
   - **Corrections in later reports:** Some reports were explicitly updated (e.g. "This report was updated on 13 February 2020 to correct statistics in Part A, 1-2 and 5"). Cross-validation will surface these corrections — the later report's value is authoritative.
   - **Final deduplication:** After cross-validation, produce a "canonical" dataset that takes the most recent (or most common) value for each data point, with a separate log of any discrepancies found.
7. Manual verification: spot-check a sample of extracted values against the PDFs, focusing especially on any cross-validation discrepancies.

### 1.7 Known complications

- **2012** explicitly dropped the route/combination table.
- **2017–2018** use numeric paper codes rather than names; need a code→name mapping from Section 4 of those reports.
- **2020** is the COVID year with anomalous 40% first rate. Data is valid but outcomes are unusual.
- **2023** is missing per-paper statistics entirely due to the Marking and Assessment Boycott.
- **Paper name normalisation:** The same paper may appear under slightly different names across years (e.g. "History of Philosophy" → "Early Modern Philosophy", "Philosophy of Logic" → "Philosophy of Logic and Language", "Plato" → "Plato: Republic (in translation)"). We'll need a normalisation/alias mapping.
- **HP candidates in Politics:** 2011 and earlier bundle HP (Human Sciences) candidates into Politics numbers with counts in parentheses. We want PPE-only numbers.
- **"(old regs)" papers:** Some years have both "Microeconomics" and "Microeconomics (old regs)". These are separate rows and should be kept separate.
- **2024–2025 assessment codes:** A single "paper" (like Theory of Politics) can have multiple assessment codes (A15005P1 and A12704P1) because of old/new regs. The per-paper stats table nests these under the paper name. We should aggregate to paper level (using the paper-name row) but also preserve the assessment-code detail.

---

## Phase 2: Analysis

### 2.1 Per-paper mark distributions

For each paper (2015+ where we have mean and SD, and for many papers also quartiles and band distributions):

- Fit parametric distributions (normal is the obvious first choice; compare with beta or skew-normal if the data suggests asymmetry).
- Where we have band counts (2017+), validate the parametric fit against the empirical distribution.
- Where we have only mean and SD (2015–2016), assume normality as a starting point.
- Characterise each paper: generous vs harsh marking, tight vs dispersed distribution.
- Examine trends over time: has mean/SD changed?

### 2.2 Subject-level patterns

- Compare Philosophy vs Politics vs Economics distributions.
- Economics is known to have wider SD (~7–10) vs Philosophy/Politics (~4–6). Quantify this.
- The economics papers with very high SD (Econometrics, Game Theory, Microeconomics, Quantitative Economics) are the "make or break" papers. Identify these.

### 2.3 Grade prior estimation

Given a student's 8 paper choices, estimate P(1st), P(2.1), P(2.2), P(other):

**Method 1 — Route-based empirical prior:**
- Determine the student's route (Phil/Pol, Pol/Econ, Phil/Econ, PPE) from their paper choices.
- Look up the historical classification distribution for that route.
- Simple and robust but coarse (doesn't account for specific paper choices within a route).

**Method 2 — Simulation from per-paper distributions:**
- For each of the 8 papers, sample a mark from the fitted distribution.
- Compute the overall average (or however the classification algorithm works — check if it's a simple average or if there's a more complex rule with dropped papers etc).
- Apply classification boundaries (typically: >=70 → 1st, 60–69 → 2.1, 50–59 → 2.2, 40–49 → 3rd, <40 → fail).
- Repeat N times (Monte Carlo simulation) to get P(each class).
- This accounts for paper-specific difficulty and variance.

**Method 3 — Analytical convolution (if assuming normality):**
- If each paper mark ~ N(μ_i, σ_i²) independently, the average of 8 papers ~ N(μ̄, σ̄²/8 + covariance terms).
- Without covariance data we'd assume independence, giving a tighter distribution than reality.
- Compute P(avg >= 70), P(60 <= avg < 70), etc.
- Fast but less accurate than simulation, and independence assumption is questionable (student ability is a latent variable).

**Recommendation:** Use Method 2 (simulation) as the primary approach. Validate against Method 1 (route-level empirical) as a sanity check. Method 3 is a nice analytical supplement.

**Important caveat about classification:** Oxford's actual classification algorithm is not a simple average threshold. Historically it involved various rules (e.g. a certain number of marks above a threshold, "benefit of the doubt" rules, etc.). The conventions may be described in Part B of the reports. We should extract and document whatever information is available about the classification algorithm, but the web tool should be transparent that it's an approximation.

### 2.4 Additional analyses

- Gender gap analysis: how does the gender gap in firsts rate vary by route and over time?
- Paper popularity trends: which papers are growing/shrinking?
- Correlation between paper difficulty (mean mark) and paper popularity (candidate count)?

---

## Phase 3: Web Tool

### 3.1 Architecture

Static site (HTML + CSS + JS). All data pre-computed and bundled as JSON. No backend needed.

### 3.2 Features

**Core: Grade prior calculator**
1. User selects their 8 papers from a dropdown/autocomplete list.
2. Tool determines their route (Phil/Pol, Pol/Econ, Phil/Econ, PPE).
3. Displays:
   - Estimated classification distribution (bar chart or pie chart) from simulation.
   - Historical route-level classification rates for comparison.
   - Per-paper difficulty indicators (mean, SD, where you'd need to score for each class).
4. Could allow user to input estimated marks for known papers and simulate the rest.

**Secondary: Explorer**
- Browse per-paper statistics over time.
- Compare papers head-to-head.
- View mark distributions (histograms where band data available, normal curves where only mean/SD available).
- Subject-level trends.
- Gender gap visualisations.

### 3.3 Tech stack

- Vanilla HTML/CSS/JS, or a lightweight framework if needed (could reassess after Phase 2).
- Charts: Chart.js or similar lightweight library.
- All data bundled as JSON files loaded at page init.

---

## Execution order

1. **Phase 1a:** Build the extraction pipeline — start with the simplest parsers (overall class distribution, subject aggregates) to establish the framework, then add parsers in order of complexity.
2. **Phase 1b:** Run extraction on all 15 reports. Manual verification pass.
3. **Phase 1c:** Paper name normalisation — build an alias mapping to link papers across years.
4. **Phase 2a:** Fit per-paper distributions. Compute route-level priors.
5. **Phase 2b:** Build simulation engine.
6. **Phase 3:** Build the web tool.

Steps 1a–1c are the bulk of the work. Phase 2 is analytical and relatively straightforward once the data is clean. Phase 3 is presentation.

---

## Phase 1 TODO

- [ ] 1. Scaffold: create `extract.py` framework with PDF text extraction, parser registry, JSON output
- [ ] 2. Parser: overall class distribution (all years)
- [ ] 3. Parser: class distribution by gender (all years)
- [ ] 4. Parser: overall gender statistics — total candidates, mean, SD by gender (all years)
- [ ] 5. Parser: subject-level aggregates from prose (2011–2014) and branch stats tables (2015+)
- [ ] 6. Parser: per-paper statistics (eras B–D: 2015–2022; era F: 2024–2025; skip 2023)
- [ ] 7. Parser: paper candidate numbers (all years)
- [ ] 8. Parser: class distribution by route/combination (2011, 2019–2025)
- [ ] 9. Parser: class distribution by ethnicity (2017–2025)
- [ ] 10. Cross-validation pass: compare overlapping data across reports, flag discrepancies
- [ ] 11. Produce canonical deduplicated dataset
- [ ] 12. Paper name normalisation/alias mapping
- [ ] 13. Manual verification spot-checks
