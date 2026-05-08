# Methodology

This page describes the statistical model behind the grade prior calculator. The approach uses a latent ability factor model fitted to 15 years of Oxford PPE examiners' reports (2011–2025, covering candidates going back to 2005), with Monte Carlo simulation to estimate classification probabilities.

## 1. The model

### Intuition

Your mark on any particular paper can be modelled as a function of:
- how well people on average do in that paper,
- your ability, and
- random external factors

In expectation, a more academically-capable student will score higher across all their papers, but there's still randomness (e.g., from question selection, marker idiosyncrasies, and luck on the day).

Our model treats ability as a single shared parameter $\theta$, and then adds on independent random noise for each paper. In reality, there's more than one latent variable which affects marks (e.g., plausibly there are distinct features like "philosophy ability", "politics ability", and "economics ability"), but we don't have sufficiently granular data to reliably estimate these.

Since marks are bounded between 0 and 100 (and in practice cluster in the 55–75 range), we use a _truncated_ normal distribution when fitting paper parameters. This prevents the model from placing probability mass on impossible marks like −5 or 110, and better fits the compression of marks near the boundaries of the scale.

### The mark equation

Each paper's mark is modelled as:

$$\text{mark}_i = \mu_i + \sigma_i \sqrt{\rho} \cdot \theta + \varepsilon_i$$

where:

- $\mu_i$ — the average mean on paper $i$ (fitted from data).
- $\sigma_i$ — the spread of marks on paper $i$ (fitted from data).
- $\theta$ — your overall ability, on a standard normal scale.
  - The ability slider sets $\theta = \Phi^{-1}(\text{percentile})$, where $\Phi^{-1}$ is the standard normal quantile function.
  - So the 50th percentile → $\theta = 0$; the 95th percentile → $\theta \approx 1.64$.
- $\rho$ — the fraction of each paper's variance explained by ability. This is assumed constant across all papers (about 0.2, i.e. ~20%), calibrated to match the observed population-wide first-class rate.
- $\varepsilon_i \sim \mathcal{N}(0,\\; \sigma_i^2(1-\rho))$ — residual noise (making up 80% of variance), independent across papers.

The $\sigma_i \sqrt{\rho}$ term means that ability matters more on high-spread papers -- i.e., they're more discriminating.

### Variance decomposition

The total variance in marks on paper $i$ is $\sigma_i^2$. The model splits this into:

- **Ability-driven variance** ($\sigma_i^2 \rho \approx 20\%$): the part that correlates across papers, since it comes from the shared factor $\theta$.
- **Noise variance** ($\sigma_i^2 (1-\rho) \approx 80\%$): the part that's independent across papers.

So, doing well on one paper is (weak) Bayesian evidence that your $\theta$ is high, which in turn predicts slightly higher marks on your other papers.

### Fitting $\mu_i$ and $\sigma_i$

The examiners' reports give *band counts*: for each paper, the number of candidates scoring 70+, 60–69, 50–59, 40–49, 30–39, and <30. We fit a truncated normal $\mathcal{N}(\mu_i, \sigma_i^2)$ truncated to $[0, 100]$ by maximising the multinomial log-likelihood of these bin counts. Band data is available from 2017 onwards, and is pooled across all years where it's available (2017–2022, 2024–2025), excluding 2020.

For earlier years (2011–2016), examiners' reports provide only the mean and standard deviation for each paper rather than full band counts. For these we use **method-of-moments** — i.e., simply setting $\mu_i$ and $\sigma_i$ equal to the observed sample mean and standard deviation.

In total, 63 papers are fitted by MLE on band data and 16 by method-of-moments from reported summary statistics.

### Calibration of $\rho$

The inter-paper correlation $\rho \approx 0.196$ is calibrated so that the model reproduces the observed ~23% first-class rate *when averaged across the full ability distribution* (integrating over $\theta \sim \mathcal{N}(0,1)$). This was done via binary search on 500k simulations with the 8 most popular papers.

Note that at $\theta = 0$ (the median student), the First rate is only ~11%. The population average is pulled up by the right tail — analogous to how mean income exceeds median income.

## 2. Classification rules

For reference, the classification rules given in the examination conventions are reproduced below:

<table class="methodology-rules-table">
<thead><tr><th>Class</th><th>Average ≥</th><th>Additional requirement</th></tr></thead>
<tbody>
<tr><td class="class-first">1st</td><td>68.5</td><td>≥ 2 marks of 70+, no mark below 50</td></tr>
<tr><td class="class-21">2.1</td><td>59.0</td><td>≥ 3 marks of 60+</td></tr>
<tr><td class="class-22">2.2</td><td>49.0</td><td>≥ 3 marks of 50+</td></tr>
<tr><td class="class-low">3rd</td><td>40.0</td><td>≥ 3 marks of 40+</td></tr>
<tr><td class="class-low">Pass</td><td>30.0</td><td>—</td></tr>
</tbody>
</table>

Because the rules are conjunctive, volatile papers introduce additional risk. For instance, a single mark below 50 blocks a First regardless of average, making high-$\sigma$ papers risky even when their mean is above 70.

## 3. Simulation

For a given set of 8 papers and ability percentile, the tool draws $N = 50{,}000$ independent exam sittings. Each draw:

1. Computes the shifted mean for each paper: $\tilde{\mu}_i = \mu_i + \sigma_i \sqrt{\rho} \cdot \theta$
2. Draws $\varepsilon_i \sim \mathcal{N}(0, \sigma_i^2(1-\rho))$ independently for each paper
3. Clips $\text{mark}_i = \max(0, \min(100, \tilde{\mu}_i + \varepsilon_i))$
4. Classifies the 8 marks using the conjunctive rules above

The reported probability for each class is the empirical frequency across all $N$ draws. Uncertainty from finite simulation is negligible ($\lt 0.1\text{pp}$ at $N = 50{,}000$); the reported $\pm 3\text{pp}$ uncertainty reflects model limitations rather than Monte Carlo error.

## 4. Data

Source data is extracted from Oxford PPE Final Honour School internal examiners' reports, 2011–2025. Mark distributions come from band data (2017+) or reported summary statistics (2011–2016). 79 papers are fitted in total.

Two years are worth special mention:

- **2020 (COVID):** excluded from all fitting. Note that even though the first-class rate doubled (~40%), paper-level marks stayed roughly the same (+0.3 on average). This was because the examination conventions were changed to exclude the lowest two passing results from classification.
- **2023 (marking boycott):** no per-paper data available.

## 5. Limitations

- Uses aggregate band data, not individual marks — the true joint distribution across papers for any one candidate is unobservable.
- Assumes a single latent ability factor with constant $\rho$ across all paper pairs. In reality, within-subject correlations are likely higher than cross-subject correlations.
- Temporal trends exist for some papers (e.g. Microeconomic Analysis: +1.65 marks/year) but are ignored in simulation, which uses pooled estimates.
- Estimates are priors — they describe what has happened historically for similar paper combinations, not what will happen to any individual candidate. In particular, we don't account for selection bias or other potential sources of endogeneity, so these shouldn't be taken as causal effects. (Sorry, James Duffy!)