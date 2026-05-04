#!/usr/bin/env python3
"""
Phase 2: Analysis engine for PPE Finals data.

Contains:
- Classification function (exact PPE rules)
- Distribution fitting (pooled per-paper)
- Monte Carlo simulation engine
"""

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats, optimize

CANONICAL_DIR = Path("data/canonical")
ANALYSIS_DIR = Path("data/analysis")


# ---------------------------------------------------------------------------
# C. Classification function (exact PPE rules)
# ---------------------------------------------------------------------------

def classify(marks: list[float]) -> str:
    """Classify 8 paper marks into a degree class using exact PPE rules.

    Rules:
      1st:  avg >= 68.5, at least 2 marks >= 70, no mark < 50
      2.1:  avg >= 59.0, at least 3 marks >= 60
      2.2:  avg >= 49.0, at least 3 marks >= 50
      3rd:  avg >= 40.0, at least 3 marks >= 40
      Pass: avg >= 30.0
      Fail: otherwise
    """
    assert len(marks) == 8
    avg = sum(marks) / 8
    n_70 = sum(1 for m in marks if m >= 70)
    n_60 = sum(1 for m in marks if m >= 60)
    n_50 = sum(1 for m in marks if m >= 50)
    n_40 = sum(1 for m in marks if m >= 40)
    any_below_50 = any(m < 50 for m in marks)

    if avg >= 68.5 and n_70 >= 2 and not any_below_50:
        return "1st"
    if avg >= 59.0 and n_60 >= 3:
        return "2.1"
    if avg >= 49.0 and n_50 >= 3:
        return "2.2"
    if avg >= 40.0 and n_40 >= 3:
        return "3rd"
    if avg >= 30.0:
        return "Pass"
    return "Fail"


# ---------------------------------------------------------------------------
# A. Distribution fitting
# ---------------------------------------------------------------------------

def fit_truncated_normal(band_counts: dict, n: int, lo=0, hi=100):
    """Fit a truncated normal to band count data via MLE on binned observations.

    band_counts: {">=70": k1, "60-69": k2, "50-59": k3, "40-49": k4, "30-39": k5, "<30": k6}
    n: total candidates

    Returns (mu, sigma, fit_quality) where fit_quality is chi-squared p-value.
    """
    boundaries = [30, 40, 50, 60, 70]
    observed = np.array([
        band_counts.get("<30", 0),
        band_counts.get("30-39", 0),
        band_counts.get("40-49", 0),
        band_counts.get("50-59", 0),
        band_counts.get("60-69", 0),
        band_counts.get(">=70", 0),
    ], dtype=float)

    total = observed.sum()
    if total == 0:
        return None

    def neg_log_likelihood(params):
        mu, sigma = params
        if sigma <= 0:
            return 1e10
        a, b = (lo - mu) / sigma, (hi - mu) / sigma
        Z = stats.norm.cdf(b) - stats.norm.cdf(a)
        if Z <= 0:
            return 1e10

        probs = []
        prev_cdf = stats.norm.cdf((lo - mu) / sigma)
        for bound in boundaries:
            cur_cdf = stats.norm.cdf((bound - mu) / sigma)
            probs.append((cur_cdf - prev_cdf) / Z)
            prev_cdf = cur_cdf
        cur_cdf = stats.norm.cdf((hi - mu) / sigma)
        probs.append((cur_cdf - prev_cdf) / Z)

        probs = np.array(probs)
        probs = np.clip(probs, 1e-10, None)
        return -np.sum(observed * np.log(probs))

    result = optimize.minimize(
        neg_log_likelihood,
        x0=[65.0, 6.0],
        method="Nelder-Mead",
        options={"xatol": 0.01, "fatol": 0.01},
    )
    mu, sigma = result.x
    sigma = abs(sigma)

    # Sanity bounds — if fit is degenerate, return None
    if mu < 20 or mu > 90 or sigma < 0.5 or sigma > 25:
        return None

    # Compute expected counts for chi-squared test
    a_norm, b_norm = (lo - mu) / sigma, (hi - mu) / sigma
    Z = stats.norm.cdf(b_norm) - stats.norm.cdf(a_norm)
    expected = []
    prev_cdf = stats.norm.cdf((lo - mu) / sigma)
    for bound in boundaries:
        cur_cdf = stats.norm.cdf((bound - mu) / sigma)
        expected.append(total * (cur_cdf - prev_cdf) / Z)
        prev_cdf = cur_cdf
    cur_cdf = stats.norm.cdf((hi - mu) / sigma)
    expected.append(total * (cur_cdf - prev_cdf) / Z)
    expected = np.array(expected)

    # Chi-squared goodness of fit (merge bins with expected < 5)
    obs_merged, exp_merged = [], []
    obs_acc, exp_acc = 0, 0
    for o, e in zip(observed, expected):
        obs_acc += o
        exp_acc += e
        if exp_acc >= 5:
            obs_merged.append(obs_acc)
            exp_merged.append(exp_acc)
            obs_acc, exp_acc = 0, 0
    if obs_acc > 0:
        if exp_merged:
            obs_merged[-1] += obs_acc
            exp_merged[-1] += exp_acc
        else:
            obs_merged.append(obs_acc)
            exp_merged.append(exp_acc)

    obs_merged = np.array(obs_merged)
    exp_merged = np.array(exp_merged)

    # df = n_bins - 1 - n_params
    df = len(obs_merged) - 1 - 2
    if df > 0:
        chi2 = np.sum((obs_merged - exp_merged) ** 2 / exp_merged)
        p_value = 1 - stats.chi2.cdf(chi2, df)
    else:
        chi2, p_value = 0.0, 1.0

    return mu, sigma, p_value


def pool_and_fit_papers():
    """Pool band data across years for each paper and fit distributions.

    Returns dict: {paper_name: {mu, sigma, p_value, n_total, years, subject}}
    """
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    # Group band data by canonical paper name, excluding 2020 (COVID)
    pooled = {}
    for r in per_paper:
        if r.get("gender") != "All":
            continue
        year = r.get("report_year")
        if year == 2020:
            continue
        bands = r.get("bands")
        if not bands:
            continue
        name = alias_map.get(r["paper"], r["paper"])
        n = r.get("n") or 0
        if name not in pooled:
            pooled[name] = {
                "bands": {k: 0 for k in [">=70", "60-69", "50-59", "40-49", "30-39", "<30"]},
                "n_total": 0,
                "years": [],
                "subject": r.get("subject"),
                "year_means": [],
                "year_sds": [],
            }
        for k in pooled[name]["bands"]:
            pooled[name]["bands"][k] += bands.get(k, 0) or 0
        pooled[name]["n_total"] += n
        pooled[name]["years"].append(year)
        if r.get("mean") is not None:
            pooled[name]["year_means"].append(r["mean"])
        if r.get("sd") is not None:
            pooled[name]["year_sds"].append(r["sd"])

    # Also add papers that only have mean+SD (no bands) — use moment estimates
    for r in per_paper:
        if r.get("gender") != "All":
            continue
        year = r.get("report_year")
        if year == 2020:
            continue
        bands = r.get("bands")
        name = alias_map.get(r["paper"], r["paper"])
        if name in pooled:
            continue  # already have band data
        if r.get("mean") is None or r.get("sd") is None:
            continue
        if name not in pooled:
            pooled[name] = {
                "bands": None,
                "n_total": r.get("n") or 0,
                "years": [],
                "subject": r.get("subject"),
                "year_means": [],
                "year_sds": [],
            }
        pooled[name]["years"].append(year)
        pooled[name]["year_means"].append(r["mean"])
        pooled[name]["year_sds"].append(r["sd"])
        pooled[name]["n_total"] += r.get("n") or 0

    # Fit distributions
    fits = {}
    for name, data in pooled.items():
        if data["bands"] and sum(data["bands"].values()) >= 10:
            result = fit_truncated_normal(data["bands"], data["n_total"])
            if result:
                mu, sigma, p_val = result
                fits[name] = {
                    "mu": round(mu, 2),
                    "sigma": round(sigma, 2),
                    "p_value": round(p_val, 4),
                    "n_total": data["n_total"],
                    "n_years": len(set(data["years"])),
                    "subject": data["subject"],
                    "method": "mle_bands",
                }
        elif data["year_means"]:
            mu = np.mean(data["year_means"])
            sigma = np.mean(data["year_sds"]) if data["year_sds"] else 6.0
            fits[name] = {
                "mu": round(float(mu), 2),
                "sigma": round(float(sigma), 2),
                "p_value": None,
                "n_total": data["n_total"],
                "n_years": len(set(data["years"])),
                "subject": data["subject"],
                "method": "moment_mean_sd",
            }

    return fits


# ---------------------------------------------------------------------------
# D. Monte Carlo simulation
# ---------------------------------------------------------------------------

def simulate_classification(
    paper_fits: dict[str, dict],
    papers: list[str],
    sigma_ability: float,
    n_sim: int = 100_000,
    rng: np.random.Generator | None = None,
) -> dict[str, float]:
    """Run Monte Carlo simulation for a given set of 8 papers.

    Model: mark_i = mu_i + theta + eps_i
           theta ~ N(0, sigma_ability^2)
           eps_i ~ N(0, sigma_paper_i^2 - sigma_ability^2)  (clamped to >0)

    Returns dict of {class: probability}.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    assert len(papers) == 8

    mus = []
    sigmas_paper = []
    for p in papers:
        fit = paper_fits.get(p)
        if fit is None:
            raise ValueError(f"No fit for paper: {p}")
        mus.append(fit["mu"])
        sigmas_paper.append(fit["sigma"])

    mus = np.array(mus)
    sigmas_paper = np.array(sigmas_paper)

    # Paper-specific noise (residual after removing ability)
    sigma_eps = np.sqrt(np.maximum(sigmas_paper**2 - sigma_ability**2, 0.1))

    # Sample
    theta = rng.normal(0, sigma_ability, size=n_sim)  # (n_sim,)
    eps = rng.normal(0, 1, size=(n_sim, 8)) * sigma_eps[None, :]  # (n_sim, 8)
    marks = mus[None, :] + theta[:, None] + eps  # (n_sim, 8)
    marks = np.clip(marks, 0, 100)

    # Classify each simulation
    counts = {"1st": 0, "2.1": 0, "2.2": 0, "3rd": 0, "Pass": 0, "Fail": 0}
    for i in range(n_sim):
        c = classify(marks[i].tolist())
        counts[c] += 1

    return {k: round(v / n_sim, 4) for k, v in counts.items()}


def calibrate_sigma_ability(paper_fits, target_first_rate=0.234, tol=0.005):
    """Calibrate sigma_ability to match the observed overall first-class rate.

    Uses a representative "average" set of papers (picks the 8 most popular).
    """
    # Pick 8 papers with the most data
    top_papers = sorted(paper_fits.keys(), key=lambda p: paper_fits[p]["n_total"], reverse=True)[:8]

    def objective(sigma_ab):
        result = simulate_classification(paper_fits, top_papers, sigma_ab, n_sim=50_000)
        return (result["1st"] - target_first_rate) ** 2

    best_sigma = 0.0
    best_err = float("inf")
    for s in np.arange(0.5, 8.0, 0.25):
        err = objective(s)
        if err < best_err:
            best_err = err
            best_sigma = s
        if err < tol**2:
            break

    # Refine
    result = optimize.minimize_scalar(
        objective,
        bounds=(max(0.1, best_sigma - 1), best_sigma + 1),
        method="bounded",
    )
    return result.x


# ---------------------------------------------------------------------------
# Paper difficulty profiles
# ---------------------------------------------------------------------------

def compute_paper_profiles(paper_fits):
    """Compute difficulty profile for each paper."""
    profiles = []
    for name, fit in paper_fits.items():
        mu, sigma = fit["mu"], fit["sigma"]
        # Use truncated normal CDF to compute band probabilities
        a, b = (0 - mu) / sigma, (100 - mu) / sigma
        Z = stats.norm.cdf(b) - stats.norm.cdf(a)

        def cdf(x):
            return (stats.norm.cdf((x - mu) / sigma) - stats.norm.cdf(a)) / Z

        pct_first = round(100 * (1 - cdf(70)), 1)
        pct_21 = round(100 * (cdf(70) - cdf(60)), 1)
        pct_below_50 = round(100 * cdf(50), 1)

        profiles.append({
            "paper": name,
            "subject": fit.get("subject"),
            "mu": mu,
            "sigma": sigma,
            "pct_first": pct_first,
            "pct_21": pct_21,
            "pct_below_50": pct_below_50,
            "n_total": fit["n_total"],
            "n_years": fit["n_years"],
            "method": fit["method"],
            "p_value": fit.get("p_value"),
        })

    return sorted(profiles, key=lambda p: -p["mu"])


# ---------------------------------------------------------------------------
# Temporal trend analysis
# ---------------------------------------------------------------------------

def compute_temporal_trends(min_years=4):
    """Compute temporal trends for all papers with sufficient data.

    For each paper with ≥min_years of mean data (excluding 2020),
    runs OLS regression of mean mark on year.

    Returns list of dicts with: paper, subject, slope, slope_ci_lo, slope_ci_hi,
    p_value, r_squared, n_years, years_range, mean_of_means.
    """
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    # Collect (year, mean) pairs per canonical paper
    series = {}
    for r in per_paper:
        if r.get("gender") != "All":
            continue
        year = r.get("report_year") or r.get("data_year")
        if year == 2020 or r.get("mean") is None:
            continue
        name = alias_map.get(r.get("paper", ""), r.get("paper", ""))
        if name not in series:
            series[name] = {"points": [], "subject": r.get("subject")}
        series[name]["points"].append((year, r["mean"]))

    trends = []
    for name, data in series.items():
        pts = sorted(set(data["points"]))
        if len(pts) < min_years:
            continue

        years = np.array([p[0] for p in pts], dtype=float)
        means = np.array([p[1] for p in pts], dtype=float)

        result = stats.linregress(years, means)
        slope, intercept, r_value, p_value, stderr = result

        # 95% CI for slope: slope ± t_{n-2, 0.025} * stderr
        t_crit = stats.t.ppf(0.975, df=len(years) - 2)
        ci_lo = slope - t_crit * stderr
        ci_hi = slope + t_crit * stderr

        trends.append({
            "paper": name,
            "subject": data["subject"],
            "slope": round(float(slope), 4),
            "slope_ci_lo": round(float(ci_lo), 4),
            "slope_ci_hi": round(float(ci_hi), 4),
            "p_value": round(float(p_value), 6),
            "r_squared": round(float(r_value ** 2), 4),
            "stderr": round(float(stderr), 4),
            "n_years": len(years),
            "years_range": [int(years.min()), int(years.max())],
            "mean_of_means": round(float(means.mean()), 2),
        })

    return sorted(trends, key=lambda t: t["p_value"])


# ---------------------------------------------------------------------------
# Subject-level analysis
# ---------------------------------------------------------------------------

def compute_subject_analysis(paper_fits):
    """Compute subject-level summary statistics and variance decomposition.

    Returns dict with subject_summary, variance_decomposition, kingmaker_papers,
    and first_rate_by_subject.
    """
    by_subject = {}
    for name, fit in paper_fits.items():
        subj = fit.get("subject")
        if not subj:
            continue
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append((name, fit))

    # Subject summary: weighted mean and SD
    subject_summary = {}
    for subj, papers in by_subject.items():
        mus = [f["mu"] for _, f in papers]
        sds = [f["sigma"] for _, f in papers]
        ns = [f["n_total"] for _, f in papers]
        total_n = sum(ns)
        if total_n > 0:
            w_mu = sum(m * n for m, n in zip(mus, ns)) / total_n
            w_sd = sum(s * n for s, n in zip(sds, ns)) / total_n
        else:
            w_mu = np.mean(mus)
            w_sd = np.mean(sds)
        subject_summary[subj] = {
            "weighted_mean": round(float(w_mu), 2),
            "weighted_sd": round(float(w_sd), 2),
            "unweighted_mean": round(float(np.mean(mus)), 2),
            "unweighted_sd": round(float(np.mean(sds)), 2),
            "n_papers": len(papers),
            "n_total": total_n,
        }

    # Variance decomposition: within-paper vs between-paper
    variance_decomp = {}
    for subj, papers in by_subject.items():
        mus = np.array([f["mu"] for _, f in papers])
        sds = np.array([f["sigma"] for _, f in papers])
        ns = np.array([f["n_total"] for _, f in papers])
        total_n = ns.sum()
        if total_n == 0 or len(papers) < 2:
            continue
        grand_mean = np.average(mus, weights=ns)
        between_var = float(np.average((mus - grand_mean) ** 2, weights=ns))
        within_var = float(np.average(sds ** 2, weights=ns))
        variance_decomp[subj] = {
            "between_paper_var": round(between_var, 2),
            "within_paper_var": round(within_var, 2),
            "ratio_within_to_between": round(within_var / between_var, 1) if between_var > 0 else None,
            "grand_mean": round(float(grand_mean), 2),
        }

    # Kingmaker papers (top 10 by sigma)
    all_papers = [(name, fit) for name, fit in paper_fits.items()]
    all_papers.sort(key=lambda x: -x[1]["sigma"])
    kingmakers = [{
        "paper": name,
        "subject": fit.get("subject"),
        "mu": fit["mu"],
        "sigma": fit["sigma"],
        "n_total": fit["n_total"],
    } for name, fit in all_papers[:10]]

    # First rate by subject (using fitted truncated normals)
    first_rate = {}
    for subj, papers in by_subject.items():
        total_n = 0
        weighted_pct = 0.0
        for name, fit in papers:
            mu, sigma = fit["mu"], fit["sigma"]
            a, b = (0 - mu) / sigma, (100 - mu) / sigma
            Z = stats.norm.cdf(b) - stats.norm.cdf(a)
            pct_70 = 1 - (stats.norm.cdf((70 - mu) / sigma) - stats.norm.cdf(a)) / Z
            weighted_pct += pct_70 * fit["n_total"]
            total_n += fit["n_total"]
        if total_n > 0:
            first_rate[subj] = round(100 * weighted_pct / total_n, 1)

    return {
        "subject_summary": subject_summary,
        "variance_decomposition": variance_decomp,
        "kingmaker_papers": kingmakers,
        "first_rate_by_subject": first_rate,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all():
    """Run all analyses and save to data/analysis/."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    print("Fitting paper distributions...")
    paper_fits = pool_and_fit_papers()
    _save("paper_fits", paper_fits)
    print(f"  {len(paper_fits)} papers fitted")

    print("Computing paper profiles...")
    profiles = compute_paper_profiles(paper_fits)
    _save("paper_profiles", profiles)

    print("Computing temporal trends...")
    trends = compute_temporal_trends()
    _save("temporal_trends", trends)
    sig = [t for t in trends if t["p_value"] < 0.05]
    print(f"  {len(trends)} papers analysed, {len(sig)} with significant trend (p<0.05)")

    print("Computing subject analysis...")
    subject = compute_subject_analysis(paper_fits)
    _save("subject_analysis", subject)

    print("Calibrating sigma_ability...")
    sigma_ab = calibrate_sigma_ability(paper_fits)
    params = {"sigma_ability": round(float(sigma_ab), 4)}
    _save("simulation_params", params)
    print(f"  sigma_ability = {params['sigma_ability']}")

    print("\nDone! All outputs in", ANALYSIS_DIR)


def _save(name, data):
    path = ANALYSIS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  → {path}")


if __name__ == "__main__":
    run_all()
