# Selection Effects and Latent Ability: How Much Should We Trust the Simulation?

## The core concern

Our Monte Carlo simulator answers: "given paper choices X, what's the probability distribution over degree classifications?" But the answer assumes a **random student** — someone drawn from the same population as the historical exam-takers. Real students self-select into papers, and differ from each other in ability. Both effects could distort our estimates.

This note examines three questions:
1. How large are selection effects, and which direction do they push?
2. How good is our single-factor latent ability model?
3. What could we do to validate or improve?

---

## 1. Selection effects

### The problem

When we observe that Game Theory has mean 66.4 and σ = 12.3, those statistics describe **the students who chose Game Theory**, not a random student who might take it. If stronger students preferentially select harder papers, the observed distribution conflates paper difficulty with student ability.

### Direction of bias

The sign of the bias depends on who selects into which papers. There are two plausible mechanisms, and they work in opposite directions on our simulation outputs:

**Positive selection into hard papers (upward bias on hard-paper means).** Students who choose quantitative options like Econometrics or Game Theory may be more mathematically able. The observed mean of 65.5 for Econometrics may overstate what a randomly-assigned student would score, because the actual takers are better-than-average at quantitative work. If the true difficulty gap between papers is larger than what we observe (because positive selection inflates hard-paper means), then easy papers are **even more advantageous** than our simulation suggests, and hard papers are even riskier.

**Positive selection into easy papers (downward bias on easy-paper means).** Alternatively, students may strategically pick papers perceived as "easy" precisely because they need the grade boost. If weaker students disproportionately take the papers with high means, the observed means understate what an average student would score. This would narrow the true difficulty gap, making paper choice matter **less** than our simulation suggests.

### What we can and cannot infer from our data

We found a negative correlation between popularity and mean mark (r = −0.28, p = 0.013): popular papers are slightly harder. However, this is essentially uninformative about self-selection for two reasons:

1. **Compulsory papers confound the correlation.** Microeconomics and Macroeconomics are among the most popular papers and have middling means. Their popularity reflects course requirements, not student preference — by definition, there is zero selection bias in a compulsory paper because the population taking it is identical to the overall student population. Including them in the correlation artificially drives the result.

2. **Popularity is not the same as selectivity.** The correlation between how many students take a paper and its mean mark tells us about the landscape of paper difficulty, not about who is choosing what. A paper could be unpopular because it's obscure, not because strong students avoid it.

Without individual-level data (where we could compare a student's marks on chosen vs. unchosen papers, or use an instrument for paper choice), we cannot identify the magnitude or direction of selection effects from aggregate data alone.

### Impact on simulation outputs

We can, however, bound the plausible impact. The marginal paper value analysis (J29) shows P(1st) ranges from roughly 20% to 29% across paper choices. If selection effects shift paper means by ±2–3 marks (a plausible range from the education literature — see Section 3), re-running the simulation with adjusted means changes P(1st) by roughly ±2–3pp. Critically, the **ranking** of which papers help or hurt is likely robust: a paper with observed mean 71 is almost certainly easier than one with mean 63, even allowing for selection. But the **magnitude** of the marginal paper value is uncertain.

**Bottom line:** Selection effects are a real and unresolvable limitation of aggregate data. They could plausibly shift paper difficulty estimates by 1–3 marks in either direction, which translates to roughly ±2–3pp on classification probabilities. We cannot determine the sign without individual-level data.

---

## 2. How good is the single-factor ability model?

### What the model does

Our generative model uses proportional ability loading (see `notes/ability_model.md`):

```
mark_i = μ_i + λ_i × θ + ε_i

θ     = Φ⁻¹(percentile)        standardised latent ability (fixed, not random)
λ_i   = σ_i × √ρ              ability loading proportional to paper spread
ε_i   ~ N(0, σ²_i × (1 − ρ))  residual exam-day noise
```

This gives all paper pairs a constant inter-paper correlation ρ ≈ 0.196, calibrated to match the observed ~23% first-class rate. The proportional loading means high-variance papers get larger ability shifts, matching the intuition that they are more discriminating.

### Is ρ = 0.196 plausible?

ρ = 0.196 means the shared ability factor accounts for ~20% of variance in each paper's marks. This implies:

- **Implied correlation between any two papers**: ρ ≈ 0.20. This is a weak positive correlation, which seems reasonable for papers across different subjects (a student's mark on Ethics doesn't strongly predict their Macroeconomics mark).

- **Implied correlation between same-subject papers**: The model says this is the same 0.20 as for cross-subject pairs. This is almost certainly wrong — we'd expect Philosophy papers to correlate more with each other than with Economics papers.

The 20% shared variance is at the low end of what the psychometrics literature suggests for academic assessments across diverse subjects (typically 20–40%), but within the plausible range given that PPE papers span three fairly distinct disciplines. See `notes/model_limitations.md` for a quantitative analysis of the multi-factor alternative.

### The single-factor limitation

The real correlation structure is probably something like:
- Within-subject pairs: ρ ≈ 0.3–0.5
- Cross-subject pairs: ρ ≈ 0.1–0.2

Our model uses ρ ≈ 0.20 for all pairs, which is:
- **Too low** for same-subject pairs → underestimates the chance that a student scores consistently high (or low) across their Philosophy papers
- **Roughly correct** for cross-subject pairs

Quantitative analysis in `notes/model_limitations.md` shows this matters substantially: under a two-factor model with ρ_within=0.30 and ρ_between=0.10, P(First) at the 95th percentile drops from 84% to 61% for the popular 8 combo.

### Impact on classification probabilities

For a **First**: the conjunctive requirement is avg ≥ 68.5, ≥ 2 marks of 70+, no mark below 50. Higher within-subject correlation makes it easier to get multiple 70+ marks in your strong subject, but also makes a sub-50 mark more likely in your weak subject. These effects partially cancel for the average-threshold requirement but compound for the conjunctive conditions.

For the **overall P(1st)**: the model was calibrated to match the observed 23.4% rate, so the aggregate is correct by construction. The bias shows up in **differential predictions**: the model may understate how much paper composition matters, because it doesn't capture that choosing 3 Philosophy papers means those 3 marks are more correlated than our model assumes.

A student heavy in one subject faces higher variance than our model predicts (good if they're strong in that subject, bad if they're weak). A well-diversified student faces lower variance. We'd expect our model to slightly understate the advantage of subject concentration for strong students and slightly overstate it for average students.

### Why the bootstrap CIs don't help here

The bootstrap CIs on P(1st) are ±2.4pp (parameter uncertainty). One might hope this covers the model-structure error, but it doesn't: bootstrap CIs measure **precision** (the spread of estimates due to sampling and parameter uncertainty), not **accuracy** (how close the model is to reality). If the single-factor assumption introduces a structural bias — say, systematically depressing P(1st) by 3pp for subject-concentrated paper sets — the bootstrap interval is centred on the wrong value. It gives a precise estimate of the wrong number.

---

## 3. Validation possibilities

### From our dataset

**Test 1: Route-level first rates.** Different routes imply different subject weightings. If our model's route predictions match observed route-level first rates (which they do to within ~1–3pp — see D14), the single-factor model is adequate at the route level, even if the internal correlation structure is wrong. This is a useful but weak test: routes are broad groupings, and a model can get route averages right while being wrong about individual paper combinations. ✅ Already done.

**Test 2: Compare observed and fitted quartiles.** If the truncated normal misses the tails, quartiles will diverge. Our A3 analysis shows 3/60 papers have significantly skewed quartiles. The kingmaker papers (Econometrics, Game Theory, Quantitative Economics) show observed Q3 ≈ 70–71 vs fitted Q3 ≈ 72–75 — the fit overstates the upper tail. This means we may **overestimate** P(70+) for these papers by 2–5pp, making the kingmaker effect slightly smaller than modelled.

**Test 3: Year-to-year mark stability.** If ability differences between cohorts are large, we'd see more year-to-year variation than our model (which treats each year as i.i.d.) predicts. The temporal trends analysis (A5) found only 3/65 papers with significant drift, and the per-year GOF validation (A2) found 15/222 paper-years failing — only slightly above the 11 expected by chance. The pooled model is adequate for temporal stability.

**Test 4: Sensitivity analysis on correlation structure.** We can run the simulation under alternative correlation structures — single-factor (current), two-factor (ability + subject), and independence — and report how much the classification probabilities change. This doesn't tell us which structure is correct, but it quantifies how much the model choice matters. If results are similar across structures, the choice is unimportant. This is feasible with our current code.

### From the literature

Several bodies of work could help calibrate our assumptions:

1. **Oxford assessment studies.** The Oxford Centre for Educational Assessment publishes on mark distributions and classification outcomes. The Norrington Table (college-level results) is public and could provide an external check on aggregate classification rates by year.

2. **Inter-subject correlation in joint honours.** The closest methodological precedent is work on modular degree classification in UK universities (e.g., Mayya & Roff 2004 on internal consistency of module marks, or the QAA reports on degree classification). These typically find within-programme correlations of 0.3–0.6 between modules, with within-discipline correlations higher than cross-discipline. These numbers could directly calibrate a multi-factor model even without individual-level PPE data.

3. **Selection effects in university course choice.** The economics-of-education literature has studied strategic course selection (e.g., Butcher, McEwan & Weerapana 2014 on grade inflation and course selection at Wellesley; Ost 2010 on peer effects in course selection). The consistent finding is that selection effects exist and are moderate — on the order of 0.1–0.3 SD of the mark distribution, which for PPE papers (SD ~6–8) would mean ~1–2 marks. However, these estimates come from US college contexts with very different institutional features, so they provide order-of-magnitude guidance rather than direct calibration.

4. **Factor models of academic performance.** The psychometrics literature on g-factor models is relevant to our single-factor assumption. For academic (rather than cognitive) assessments, a single factor typically explains 20–40% of variance across diverse subjects (similar to our ~18% estimate), with residual correlations within subject clusters. A hierarchical model (general ability + subject-specific factors) is the standard in this literature.

### Concrete suggestions for improvement

1. **(Feasible now)** Sensitivity analysis: run the simulation under alternative correlation structures (single-factor, two-factor, independence) to quantify how much model choice matters.

2. **(Feasible now)** For the web tool, present results as ranges rather than point estimates: "P(1st) is approximately 20–25%" rather than "P(1st) = 23.2%". Frame the output as a rough prior, not a precise prediction.

3. **(Feasible now)** Use the literature on inter-module correlations (typically ρ within-subject ≈ 0.3–0.5) to calibrate a two-factor model, even without individual-level PPE data. Compare results to the single-factor model.

4. **(Would need external data)** If individual-level mark data were ever available (e.g., from an exam board access request), we could directly estimate the inter-paper correlation matrix and calibrate a multi-factor model. This would also let us quantify selection effects by comparing a student's marks on chosen vs. unchosen papers within the same subject.

---

## Summary

| Concern | Magnitude | Can we resolve it? | Impact on P(1st) |
|---------|-----------|---------------------|-------------------|
| Selection effects on paper means | ±1–3 marks | No, without individual data | ±2–3pp |
| Single-factor vs multi-factor correlation | ρ off by ~0.1–0.3 for same-subject pairs | No, under-identified without individual data | Large at extreme percentiles (up to ~23pp at 95th) |
| Truncated normal for kingmakers | Q3 overstated by 2–4 marks | Not worth it (6 bins can't identify skewness) | ~1–2pp |
| Temporal pooling | Adequate (A2 confirms) | Resolved | <1pp |

**Overall assessment:** The simulation is fit for purpose as a rough guide ("your paper choices put you in the 20–25% range for a First, not the 15–20% range"). It should not be read as precise to the percentage point. The main unresolvable limitation is selection effects; the main improvable limitation is the correlation structure. For the web tool, framing outputs as approximate ranges (±3pp) and being transparent about the assumptions is the honest approach.
