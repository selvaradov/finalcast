# Methodology

This page describes the statistical model behind the grade prior calculator. The approach uses a latent ability factor model fitted to 15 years of Oxford PPE examiners' report data, with Monte Carlo simulation to estimate classification probabilities.

## 1. The model

Each paper's mark is modelled as a draw from:

$$\text{mark}_i = \mu_i + \lambda_i \cdot \theta + \varepsilon_i$$

The key idea is a **variance decomposition**: the total spread in marks on any paper ($\sigma_i^2$) is split into two components:

- **Ability component** ($\lambda_i^2 = \sigma_i^2 \rho$): the part of variance explained by how good you are overall. Papers with higher total spread are assumed to be more discriminating.
- **Noise component** ($\sigma_i^2(1-\rho)$): residual randomness — exam-day luck, marker variation, topic lottery.

The parameters:

- $\mu_i$ — paper-specific mean mark.
- $\sigma_i$ — paper-specific standard deviation (total spread). Both $\mu_i$ and $\sigma_i$ are fitted jointly by MLE.
- $\theta$ — standardised latent ability. The ability slider sets $\theta = \Phi^{-1}(\text{percentile})$, where $\Phi^{-1}$ is the standard normal quantile function. So the 75th percentile → $\theta \approx 0.67$.
- $\lambda_i = \sigma_i \sqrt{\rho}$ — ability loading, proportional to paper spread.
- $\varepsilon_i \sim \mathcal{N}(0,\; \sigma_i^2(1-\rho))$ — residual exam-day noise, independent across papers.

### Why truncated normal?

Marks are bounded in $[0, 100]$ and typically clustered in the 55–75 range. An ordinary normal would place implausible probability mass below 0 or above 100. The truncated normal respects these bounds and better fits the observed compression of marks near class boundaries.

### Fitting $\mu_i$ and $\sigma_i$

The examiners' reports give *band counts*: for each paper, the number of candidates scoring 70+, 60–69, 50–59, 40–49, 30–39, and <30. We fit a truncated normal $\mathcal{N}(\mu_i, \sigma_i^2)$ truncated to $[0, 100]$ by maximising the multinomial log-likelihood of these bin counts. Data is pooled across all available years (2017–2022, 2024–2025) excluding 2020.

### Calibration of $\rho$

The inter-paper correlation $\rho \approx 0.196$ is calibrated so that the model reproduces the observed ~23% first-class rate *when averaged across the full ability distribution* (integrating over $\theta \sim \mathcal{N}(0,1)$). This was done via binary search on 500k simulations with the 8 most popular papers.

Note that at $\theta = 0$ specifically (the median student), the First rate is only ~11%. The population average is pulled up by the right tail — analogous to how mean income exceeds median income.

## 2. Classification rules

PPE uses *conjunctive* classification — candidates need both an average threshold and a minimum count of papers at the relevant mark level:

| Class | Average ≥ | Additional requirement |
|-------|-----------|----------------------|
| 1st   | 68.5      | ≥ 2 marks of 70+, no mark below 50 |
| 2.1   | 59.0      | ≥ 3 marks of 60+ |
| 2.2   | 49.0      | ≥ 3 marks of 50+ |
| 3rd   | 40.0      | ≥ 3 marks of 40+ |
| Pass  | 30.0      | — |

These conjunctive rules create non-linear interactions with paper variance — for instance, a single mark below 50 vetoes a First regardless of average, making high-$\sigma$ papers risky even when their mean is above 70.

## 3. Simulation

For a given set of 8 papers and ability percentile, the tool draws $N = 50{,}000$ independent exam sittings. Each draw:

1. Computes the shifted mean for each paper: $\tilde{\mu}_i = \mu_i + \sigma_i \sqrt{\rho} \cdot \theta$
2. Draws $\varepsilon_i \sim \mathcal{N}(0, \sigma_i^2(1-\rho))$ independently for each paper
3. Clips $\text{mark}_i = \max(0, \min(100, \tilde{\mu}_i + \varepsilon_i))$
4. Classifies the 8 marks using the conjunctive rules above

The reported probability for each class is the empirical frequency across all $N$ draws. Uncertainty from finite simulation is negligible ($\lt 0.1\text{pp}$ at $N = 50{,}000$); the reported $\pm 3\text{pp}$ uncertainty reflects model limitations rather than Monte Carlo error.

## 4. Data

Source data is extracted from Oxford PPE Final Honour School internal examiners' reports, 2011–2025. Mark distributions come from band data: the percentage of candidates achieving each class-level mark on each paper. 81 papers are fitted in total — 65 via MLE on band data, 16 via method-of-moments from reported mean and standard deviation.

Two years receive special treatment:

- **2020 (COVID):** excluded from all fitting. The first-class rate doubled (~40%) despite paper-level marks barely shifting (+0.3 on average). The anomaly was caused by modified classification conventions: the lowest two passing results were dropped as a safety net, while the marking scale was unchanged.
- **2023 (marking boycott):** no per-paper data available; excluded by data absence.

## 5. Limitations

- Uses aggregate band data, not individual marks — the true joint distribution across papers for any one candidate is unobservable.
- Assumes a single latent ability factor with constant $\rho$ across all paper pairs. In reality, within-subject correlations are likely higher than cross-subject correlations.
- No conditioning on prior performance — the ability slider is a self-assessment, not a calibrated prediction from collections data.
- Temporal trends exist for some papers (e.g. Microeconomic Analysis: +1.65 marks/year) but are ignored in simulation, which uses pooled estimates.
- Estimates are priors — they describe what has happened historically for similar paper combinations, not what will happen to any individual candidate.
