# Roadmap

Future work and ideas that haven't been implemented.

## Analysis extensions

### Gender & demographics
- **Gender gap by route** — do Phil-Pol/Pol-Econ routes show different gender gaps?
- **Per-paper gender analysis** — 2024–2025 reports have gender-disaggregated per-paper stats for the first time
- **Gender-disaggregated simulation** — allow the model to condition on gender (separate ability distributions)
- **Ethnicity attainment gap** — track over time (data available 2017–2025). Comparing to university-wide gaps needs external data and is probably infeasible.

### Model improvements
- **Correlation structure validation** — infeasible without individual-level data; see `notes/selection_and_ability.md`
- **Re-fit merged Feminist Theory** — combined cross-route data (n=31 in 2022) should give a more reliable sigma than either route alone
- **Document small-n fitting limitations** in methodology page

## Web tool features

### Calculator
- **Ability shift comparison** — "If you were one tier higher, your P(1st) would go from X% to Y%"
- **Risk profile** — P(dropping below 2.1) as a downside-risk framing

### Explorer
- **Head-to-head paper comparison** — select two papers and see stats side-by-side

## Data quality

- Manual verification spot-checks against source PDFs (low priority — population-weighted coverage is 99.3%)

## Data format reference

Useful context if re-extraction is ever needed.

### Per-paper statistics format eras

| Era | Years | Format |
|-----|-------|--------|
| A | 2011–2014 | No per-paper stats table. Subject-level averages only. |
| B | 2015–2016 | Simple table: paper name, mean, SD, min, max. |
| C | 2017–2018 | Rich table with numeric codes. Bands as percentages, quartiles. |
| D | 2019–2022 | Named papers, bands as counts (2020+) or percentages (2019). |
| E | 2023 | Empty (marking boycott). |
| F | 2024–2025 | Gender-disaggregated. Separate stats and bands tables. |

### Known complications

- 2017–2018 use numeric paper codes (need code→name mapping from paper_numbers)
- 2023 missing per-paper statistics (boycott)
- Paper name normalisation: ~400 variants mapped to 94 canonical names via `data/paper_aliases.json`
- 2024–2025: multiple assessment codes per paper (old/new regs, component splits)
- 2020 excluded from all fitting (COVID classification rule change doubled First rate despite stable marking)
