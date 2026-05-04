# Ability model: additive vs proportional loading

## The problem

The original model uses an additive ability factor:

    mark_i = μ_i + θ + ε_i
    θ ~ N(0, σ²_a),  ε_i ~ N(0, σ²_paper_i - σ²_a)

σ_ability was calibrated at 2.74 to reproduce the population-level ~23% First
rate when θ is drawn randomly. This works at the population level but gives
implausible results when conditioning on ability:

- At the 95th percentile (θ fixed at +4.5 marks), a student taking
  Econometrics (σ=14) still has P(mark<50) ≈ 7%. That's because ability
  explains only 4% of Econometrics' variance — the model treats almost all
  spread as exam-day noise.

- For a gentler paper like Ethics (σ=5.7), ability explains 24% of variance.
  The model says ability matters 6× more for easy papers than hard ones.

- In reality, a strong student's advantage on a high-variance paper is
  *larger in marks*, not smaller. If anything, high-σ papers amplify ability
  differences (the variance comes partly from wider ability range among
  candidates, and partly from the paper being more discriminating).

## Why the additive model fails here

The additive model gives every paper the same absolute shift from ability:
+4.5 marks at the 95th percentile regardless of paper σ. This means:

| Paper        | σ_total | Shift at 95th | σ_eps  | P(<50) |
|-------------|---------|---------------|--------|--------|
| Ethics       | 5.7     | +4.5          | 5.0    | 0.0%   |
| Micro        | 8.9     | +4.5          | 8.5    | 0.8%   |
| QE           | 10.6    | +4.5          | 10.2   | 2.6%   |
| Econometrics | 14.0    | +4.5          | 13.7   | 7.3%   |

The residual σ_eps is nearly as large as the total σ — the model barely
distinguishes between students on high-variance papers. A 95th percentile
student on Econometrics has almost the same noise as a random student.

## The proportional alternative

Replace the fixed loading with a proportional one:

    mark_i = μ_i + λ_i × θ + ε_i
    θ ~ N(0, 1)  (standardised ability)
    λ_i = σ_i × √ρ  (loading proportional to paper spread)
    ε_i ~ N(0, σ²_i × (1 - ρ))

This gives a constant inter-paper correlation ρ. The ability shift on each
paper is proportional to that paper's total spread: high-σ papers get bigger
shifts, which matches the intuition that they're more discriminating.

### Calibration

ρ ≈ 0.20 reproduces the population First rate (~23%) for the popular 8-paper combo:

| ρ    | Population 1st | Population 2.1 |
|------|---------------|----------------|
| 0.10 | 19.5%         | 77.9%          |
| 0.15 | 21.5%         | 74.7%          |
| 0.20 | 23.3%         | 71.8%          |
| 0.25 | 24.7%         | 69.2%          |
| 0.30 | 25.9%         | 66.8%          |

### Conditioned results at ρ ≈ 0.196

**Popular 8 papers** (Ethics, Micro, Macro, IR, QE, Brit Pol, K&R, Theory of Pol):

| Percentile | P(1st) | P(2.1) |
|-----------|--------|--------|
| 25th       | 1.6%   | 95.5%  |
| 50th       | 10.9%  | 88.9%  |
| 75th       | 37.4%  | 62.6%  |
| 90th       | 69.1%  | 30.9%  |
| 95th       | 84.0%  | 16.0%  |

**Kingmaker combo** (Aristotle, GT, QE, Econometrics, Micro Analysis, Micro, Phil Logic, Ethics):

| Percentile | P(1st) | P(2.1) |
|-----------|--------|--------|
| 25th       | 3.3%   | 86.5%  |
| 50th       | 17.4%  | 81.2%  |
| 75th       | 47.7%  | 52.2%  |
| 90th       | 76.2%  | 23.7%  |
| 95th       | 87.6%  | 12.4%  |

At 95th percentile, the kingmaker combo (87.6% First) slightly outperforms
the safe combo (84.0%) — the higher variance helps when ability is high.
P(any<50) drops from ~15% (additive model) to ~2% (proportional).

### Per-paper P(<50) at 95th percentile

| Paper        | σ_total | Shift | σ_eps  | P(<50) |
|-------------|---------|-------|--------|--------|
| Ethics       | 5.7     | +4.2  | 5.1    | 0.0%   |
| Micro        | 8.9     | +6.5  | 8.0    | 0.1%   |
| QE           | 10.6    | +7.8  | 9.5    | 0.5%   |
| Game Theory  | 12.3    | +9.0  | 11.0   | 1.1%   |
| Econometrics | 14.0    | +10.3 | 12.5   | 2.0%   |

The shift on Econometrics is now +10.3 (vs +4.5 in the additive model),
and σ_eps drops from 13.7 to 12.5. Both effects reduce tail risk.

## What "50th percentile" means in this model

At the 50th percentile, θ = 0, so the student gets no ability bonus.
Marks for each paper are μ_i + ε_i — independent draws around the
population means with only the residual noise.

This gives a ~10% First rate rather than the population ~23%. That's because
the population rate includes students drawn from across the entire ability
distribution — including the upper tail who boost the average. The 50th
percentile (median ability) student is *not* expected to match the average
classification rate: the average is pulled up by the right tail.

Analogy: the median household doesn't earn the mean income.

However, note that the interpretation of "50th percentile" here is relative
to the PPE cohort, not the general population. A median PPE student is
already a strong student by national standards; the 10% First at median
reflects the within-cohort distribution.

In the tool, we should frame this clearly: "50th percentile among PPE
finalists" and note that the First rate for an average student is lower
than the cohort average because high-ability students disproportionately
contribute to the overall First rate.

## Limitations

- A single ρ is still a simplification. Same-subject papers probably
  correlate more than cross-subject pairs (shared study, shared examiners).
  A multi-factor model (one factor per subject + one global) would be
  better but requires data we don't have.

- The proportional loading assumes wider-spread papers are more
  discriminating. An alternative: wide spread could come from inconsistent
  marking rather than greater sensitivity to ability. Without individual-
  level data we can't distinguish these.

- ρ is calibrated to match aggregate classification rates. Individual-level
  mark correlations (which we don't have) could give a more direct estimate.

## Implementation

Engine uses proportional loading with ρ = 0.196 (calibrated via binary
search on 500k simulations to match 23.2% population First rate for the
8 most popular papers). The data bundle stores `rho` rather than
`sigma_ability`. The engine computes per-paper:

    λ_i = σ_i × √ρ
    σ_eps_i = σ_i × √(1 − ρ)
    shifted_μ_i = μ_i + λ_i × θ  where θ = Φ⁻¹(percentile)
