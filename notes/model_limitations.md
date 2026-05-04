# Model Limitations: Quantitative Assessment

Companion to `ability_model.md` and `selection_and_ability.md`. This note
puts numbers on the two main modelling limitations: the truncated normal
assumption and the single-factor correlation structure.

---

## 1. Truncated normal skewness

### The concern

UK exam marks are asymmetric: compressed into 58–68 with a hard ceiling
around 75–80 and a longer left tail. The truncated normal (support [0, 100])
doesn't capture this — it allows symmetric spread above and below the mean,
overstating the upper tail.

### Band-level calibration is fine

The MLE fits directly on 6 band counts, so band-level probabilities are
well-calibrated. Fitted vs observed P(>=70) for kingmaker papers:

| Paper | Observed P(>=70) | Fitted P(>=70) | Difference |
|-------|-----------------|---------------|------------|
| Econometrics | 34.9% (51/146) | 37.0% | +2.1pp |
| Game Theory | 35.7% (51/143) | 38.4% | +2.7pp |
| QE | 31.3% (153/489) | 32.7% | +1.4pp |
| Micro Analysis | 36.2% (21/58) | 37.4% | +1.2pp |

### The problem is within the 70+ band

The fitted distribution spreads mass across 70–100. In reality, marks
cluster at 70–74. The model overstates Q3 by 2–4 marks:

| Paper | σ | Q3 observed | Q3 fitted | Error |
|-------|---|------------|-----------|-------|
| Econometrics | 14.0 | 70.5 | 74.7 | +4.2 |
| Game Theory | 12.3 | 71.2 | 74.6 | +3.4 |
| Micro Analysis | 8.2 | 70.5 | 72.9 | +2.4 |
| QE | 10.6 | 70.4 | 72.4 | +2.0 |

This inflates E[mark | mark >= 70]. Under the fitted model, the conditional
expectation for a 70+ mark on Econometrics is 79.2 — reality is closer to
72–73. The model thinks a First-class mark on a kingmaker paper means a
strong 75–80, when it usually means a bare 70–72.

### Impact on First rates

Simulating with a hard ceiling at 82 (a rough proxy for compressed right
tails):

| Combo | Pct | Baseline P(1st) | Capped P(1st) | Difference |
|-------|-----|----------------|--------------|------------|
| Popular 8 | 75th | 37.3% | 36.4% | -0.9pp |
| Popular 8 | 95th | 84.0% | 83.4% | -0.6pp |
| Kingmaker | 75th | 47.5% | 45.0% | -2.5pp |
| Kingmaker | 95th | 87.7% | 86.3% | -1.4pp |

The kingmaker combo sees a larger reduction (~2pp) because more papers have
wide distributions with inflated right tails. But overall the effect is
modest: classification depends mainly on whether marks cross 70 (which the
band calibration gets right), not on how far above 70 they are.

### Verdict

The truncated normal overstates Q3 noticeably but inflates First rates by
only ~1–2pp. Not worth implementing skew-normal — the 6 bins available for
fitting probably can't reliably identify a skewness parameter. Quartile data
exists for some years but coverage is patchy. The Bowley skewness test finds
only 3/60 papers significantly skewed (QE, Sociology of Post-Industrial
Societies, IR in the Era of Two World Wars).

---

## 2. Multi-factor ability model

### The concern

The single-factor model (ρ = 0.196 for all paper pairs) assumes that
same-subject pairs have the same correlation as cross-subject pairs. In
reality, your three Philosophy marks probably correlate more strongly with
each other than with your Economics marks.

### Pair structure

In an 8-paper combo, 28 total pairs break down as:

| Combo | Same-subject pairs | Cross-subject pairs |
|-------|-------------------|-------------------|
| Popular 8 (3P, 3E, 2Pol) | 7/28 (25%) | 21/28 (75%) |
| Kingmaker (3Phil, 5Econ) | 13/28 (46%) | 15/28 (54%) |

Subject-concentrated combos are more affected because a larger share of
their pairs would have higher-than-modelled correlation.

### Two-factor model

Decompose ability into global + subject-specific factors:

    mark_i = μ_i + σ_i·√ρ_global·θ_global + σ_i·√ρ_subject·θ_subject + σ_i·√ρ_eps·ε_i

    ρ_within  = ρ_global + ρ_subject    (same-subject correlation)
    ρ_between = ρ_global                (cross-subject correlation)

### Simulation results

Conditioned P(First) under different correlation structures:

**Popular 8 (Ethics, Micro, Macro, IR, QE, Brit Pol, K&R, Theory of Pol):**

| Scenario | 50th | 75th | 90th | 95th |
|----------|------|------|------|------|
| Single ρ=0.196 | 10.8% | 37.5% | 69.3% | 84.0% |
| ρ_w=0.30, ρ_b=0.10 | 15.9% | 31.9% | 50.2% | 61.3% |
| ρ_w=0.40, ρ_b=0.08 | 18.0% | 31.4% | 46.3% | 55.4% |
| ρ_w=0.50, ρ_b=0.05 | 20.0% | 29.9% | 40.3% | 46.9% |

**Kingmaker combo (Aristotle, GT, QE, Econometrics, Micro Analysis, Micro, Phil Logic, Ethics):**

| Scenario | 50th | 75th | 90th | 95th |
|----------|------|------|------|------|
| Single ρ=0.196 | 17.3% | 47.7% | 76.4% | 87.7% |
| ρ_w=0.30, ρ_b=0.10 | 25.1% | 41.4% | 57.3% | 66.4% |
| ρ_w=0.40, ρ_b=0.08 | 27.4% | 40.7% | 53.6% | 61.3% |
| ρ_w=0.50, ρ_b=0.05 | 29.7% | 39.1% | 48.1% | 53.7% |

### Population-level calibration check

All scenarios give ~22–23% First at the population level (matching the
observed rate):

| Scenario | Population 1st rate |
|----------|-------------------|
| Single ρ=0.196 | 23.1% |
| ρ_w=0.30, ρ_b=0.10 | 21.7% |
| ρ_w=0.40, ρ_b=0.08 | 22.0% |
| ρ_w=0.50, ρ_b=0.05 | 22.2% |

### Interpretation

The multi-factor model redistributes probability across ability levels.
Higher within-subject correlation means:

- **Median students get more Firsts** (more subject-level luck: you can get
  lucky in one subject's factor and ride that across several papers)
- **Top students get fewer Firsts** (less protection from global ability:
  being 95th percentile overall doesn't pin down your performance in each
  subject as tightly)

At the 95th percentile, the difference is large: 84% → 61% for Popular 8
under the mild scenario (ρ_w=0.30). The single-factor model substantially
overstates how much being "globally good" protects you.

### Why we can't fit it

We have one calibration target (23% population First rate) but two free
parameters (ρ_within, ρ_between). Without individual-level mark data, the
model is under-identified. The psychometrics literature suggests
ρ_within ≈ 0.3–0.5 for same-discipline academic modules, but this is
indirect evidence from different contexts.

### Recommendation

Keep the single-factor model as the default — it's the only one we can
calibrate from our data. But note in the web tool that the model assumes
uniform inter-paper correlation, which understates risk for students who
are strong in one subject but weaker in another. The ±3pp confidence
interval partially covers this, but the structural bias at extreme
percentiles (95th) is larger than 3pp.

A possible enhancement: an advanced "subject specialisation" toggle that
lets users express how correlated they think their same-subject papers are.
Presets like "balanced" (ρ_w=0.25) vs "specialist" (ρ_w=0.45) would be
more transparent than pretending the single-factor model is definitive.
