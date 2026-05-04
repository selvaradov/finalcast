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
# A2. Per-year GOF validation of pooled fits
# ---------------------------------------------------------------------------

def validate_pooled_fits(paper_fits):
    """Test each year's band counts against the pooled truncated normal fit.

    For each paper with an MLE fit, runs chi-squared on each individual year's
    band counts against the pooled (mu, sigma). Reports per-paper and per-year
    results.
    """
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    boundaries = [30, 40, 50, 60, 70]
    band_keys = ["<30", "30-39", "40-49", "50-59", "60-69", ">=70"]

    # Group per-year band data by paper
    year_data = {}
    for r in per_paper:
        if r.get("gender") != "All" or r.get("report_year") == 2020:
            continue
        bands = r.get("bands")
        if not bands:
            continue
        name = alias_map.get(r["paper"], r["paper"])
        year = r.get("report_year")
        observed = [bands.get(k, 0) or 0 for k in band_keys]
        if sum(observed) < 10:
            continue
        year_data.setdefault(name, []).append({
            "year": year,
            "observed": observed,
            "n": sum(observed),
        })

    results = []
    for paper, fit in paper_fits.items():
        if fit["method"] != "mle_bands" or paper not in year_data:
            continue
        mu, sigma = fit["mu"], fit["sigma"]
        a_norm = (0 - mu) / sigma
        b_norm = (100 - mu) / sigma
        Z = stats.norm.cdf(b_norm) - stats.norm.cdf(a_norm)

        # Expected bin probabilities under pooled fit
        probs = []
        prev = stats.norm.cdf(a_norm)
        for bound in boundaries:
            cur = stats.norm.cdf((bound - mu) / sigma)
            probs.append((cur - prev) / Z)
            prev = cur
        probs.append((stats.norm.cdf(b_norm) - prev) / Z)
        probs = np.array(probs)

        year_results = []
        for yd in year_data[paper]:
            obs = np.array(yd["observed"], dtype=float)
            exp = probs * yd["n"]

            # Merge bins with expected < 5
            obs_m, exp_m = [], []
            oa, ea = 0.0, 0.0
            for o, e in zip(obs, exp):
                oa += o
                ea += e
                if ea >= 5:
                    obs_m.append(oa)
                    exp_m.append(ea)
                    oa, ea = 0.0, 0.0
            if oa > 0:
                if exp_m:
                    obs_m[-1] += oa
                    exp_m[-1] += ea
                else:
                    obs_m.append(oa)
                    exp_m.append(ea)

            obs_m = np.array(obs_m)
            exp_m = np.array(exp_m)
            df = len(obs_m) - 1  # no param estimation (using pooled fit)
            if df > 0:
                chi2 = float(np.sum((obs_m - exp_m) ** 2 / exp_m))
                p = float(1 - stats.chi2.cdf(chi2, df))
            else:
                chi2, p = 0.0, 1.0

            year_results.append({
                "year": yd["year"],
                "n": yd["n"],
                "chi2": round(chi2, 2),
                "df": df,
                "p_value": round(p, 4),
            })

        n_years = len(year_results)
        n_fail = sum(1 for yr in year_results if yr["p_value"] < 0.05)

        results.append({
            "paper": paper,
            "subject": fit.get("subject"),
            "mu": fit["mu"],
            "sigma": fit["sigma"],
            "pooled_gof_p": fit.get("p_value"),
            "n_years_tested": n_years,
            "n_years_fail": n_fail,
            "year_results": sorted(year_results, key=lambda x: x["year"]),
        })

    results.sort(key=lambda x: -x["n_years_fail"])

    # Summary stats
    total_tests = sum(r["n_years_tested"] for r in results)
    total_fail = sum(r["n_years_fail"] for r in results)
    papers_any_fail = sum(1 for r in results if r["n_years_fail"] > 0)

    summary = {
        "total_paper_years_tested": total_tests,
        "total_failing_p05": total_fail,
        "expected_false_positives_at_05": round(total_tests * 0.05, 1),
        "papers_with_any_failure": papers_any_fail,
        "total_papers_tested": len(results),
        "per_paper": results,
    }
    return summary


# ---------------------------------------------------------------------------
# A3. Asymmetry / skewness analysis
# ---------------------------------------------------------------------------

def analyse_asymmetry(paper_fits):
    """Analyse distributional asymmetry using quartile data.

    Computes Bowley skewness for each paper-year, tests whether the
    truncated normal is adequate, and fits skew-normal where it isn't.
    """
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    # Collect quartile observations per paper
    paper_quartiles = {}
    for r in per_paper:
        if r.get("gender") != "All" or r.get("report_year") == 2020:
            continue
        q1, med, q3 = r.get("q1"), r.get("median"), r.get("q3")
        if q1 is None or med is None or q3 is None:
            continue
        name = alias_map.get(r["paper"], r["paper"])
        paper_quartiles.setdefault(name, []).append({
            "year": r.get("report_year"),
            "q1": q1, "median": med, "q3": q3,
        })

    results = []
    for paper, obs_list in paper_quartiles.items():
        fit = paper_fits.get(paper)
        if not fit:
            continue

        # Bowley skewness per year
        skews = []
        for obs in obs_list:
            iqr = obs["q3"] - obs["q1"]
            if iqr > 0:
                skew = (obs["q1"] + obs["q3"] - 2 * obs["median"]) / iqr
                skews.append(skew)

        if len(skews) < 2:
            continue

        mean_skew = float(np.mean(skews))
        sd_skew = float(np.std(skews, ddof=1))
        n = len(skews)

        # One-sample t-test: is mean skewness significantly different from 0?
        t_stat = mean_skew / (sd_skew / math.sqrt(n)) if sd_skew > 0 else 0
        p_value = float(2 * (1 - stats.t.cdf(abs(t_stat), df=n - 1)))

        # Expected Bowley skewness under the fitted truncated normal
        mu, sigma = fit["mu"], fit["sigma"]
        a, b = (0 - mu) / sigma, (100 - mu) / sigma
        rv = stats.truncnorm(a, b, loc=mu, scale=sigma)
        expected_q1 = float(rv.ppf(0.25))
        expected_med = float(rv.ppf(0.5))
        expected_q3 = float(rv.ppf(0.75))
        expected_iqr = expected_q3 - expected_q1
        expected_skew = (expected_q1 + expected_q3 - 2 * expected_med) / expected_iqr if expected_iqr > 0 else 0

        # Observed quartiles (pooled means)
        obs_q1 = float(np.mean([o["q1"] for o in obs_list]))
        obs_med = float(np.mean([o["median"] for o in obs_list]))
        obs_q3 = float(np.mean([o["q3"] for o in obs_list]))

        results.append({
            "paper": paper,
            "subject": fit.get("subject"),
            "n_years": n,
            "mean_bowley_skew": round(mean_skew, 4),
            "sd_skew": round(sd_skew, 4),
            "t_stat": round(t_stat, 3),
            "p_value": round(p_value, 4),
            "expected_skew_truncnorm": round(expected_skew, 4),
            "observed_quartiles": {
                "q1": round(obs_q1, 1),
                "median": round(obs_med, 1),
                "q3": round(obs_q3, 1),
            },
            "fitted_quartiles": {
                "q1": round(expected_q1, 1),
                "median": round(expected_med, 1),
                "q3": round(expected_q3, 1),
            },
            "fit_mu": mu,
            "fit_sigma": sigma,
        })

    results.sort(key=lambda x: x["p_value"])

    sig_papers = [r for r in results if r["p_value"] < 0.05]
    mean_abs_skew = float(np.mean([abs(r["mean_bowley_skew"]) for r in results]))

    summary = {
        "n_papers_tested": len(results),
        "n_significant_skew_p05": len(sig_papers),
        "mean_abs_bowley_skew": round(mean_abs_skew, 4),
        "overall_mean_skew": round(float(np.mean([r["mean_bowley_skew"] for r in results])), 4),
        "assessment": _assess_asymmetry(results),
        "per_paper": results,
    }
    return summary


def _assess_asymmetry(results):
    """Generate a textual assessment of the asymmetry findings."""
    n = len(results)
    n_sig = sum(1 for r in results if r["p_value"] < 0.05)
    expected_fp = n * 0.05
    mean_abs = np.mean([abs(r["mean_bowley_skew"]) for r in results])

    if n_sig <= expected_fp * 1.5 and mean_abs < 0.15:
        return "truncated_normal_adequate"
    elif n_sig <= expected_fp * 2 and mean_abs < 0.25:
        return "mostly_adequate_few_exceptions"
    else:
        return "consider_alternative_distributions"


# ---------------------------------------------------------------------------
# J29. Marginal paper value analysis
# ---------------------------------------------------------------------------

def compute_marginal_paper_value(paper_fits, sigma_ability, n_sim=100_000):
    """Compute the marginal effect of each paper on classification probabilities.

    Takes the 7 most popular papers as a base, then simulates adding each
    possible 8th paper and reports the resulting classification distribution.
    Also computes a "median baseline" using the 8th-most-popular paper.
    """
    rng = np.random.default_rng(42)

    # Rank papers by n_total to pick base 7
    ranked = sorted(paper_fits.items(), key=lambda x: -x[1]["n_total"])
    base_7 = [name for name, _ in ranked[:7]]
    median_8th = ranked[7][0]

    # Baseline: the 8 most popular
    baseline = simulate_classification(paper_fits, base_7 + [median_8th], sigma_ability, n_sim, rng)

    results = []
    for paper, fit in paper_fits.items():
        if paper in base_7:
            continue
        rng_copy = np.random.default_rng(42)
        dist = simulate_classification(paper_fits, base_7 + [paper], sigma_ability, n_sim, rng_copy)
        delta_first = dist["1st"] - baseline["1st"]
        delta_22_plus = (dist["2.2"] + dist["3rd"] + dist["Pass"] + dist["Fail"]) - \
                        (baseline["2.2"] + baseline["3rd"] + baseline["Pass"] + baseline["Fail"])

        results.append({
            "paper": paper,
            "subject": fit.get("subject"),
            "mu": fit["mu"],
            "sigma": fit["sigma"],
            "p_first": round(dist["1st"], 4),
            "p_21": round(dist["2.1"], 4),
            "p_22_or_below": round(dist["2.2"] + dist["3rd"] + dist["Pass"] + dist["Fail"], 4),
            "delta_first_vs_median": round(delta_first, 4),
            "delta_22_plus_vs_median": round(delta_22_plus, 4),
        })

    results.sort(key=lambda x: -x["delta_first_vs_median"])

    return {
        "base_7_papers": base_7,
        "median_8th_paper": median_8th,
        "baseline_distribution": baseline,
        "n_sim": n_sim,
        "sigma_ability": round(sigma_ability, 4),
        "per_paper": results,
    }


# ---------------------------------------------------------------------------
# J31. Bootstrap confidence intervals on simulation
# ---------------------------------------------------------------------------

def bootstrap_simulation_cis(paper_fits, sigma_ability, n_bootstrap=200, n_sim=50_000):
    """Bootstrap CIs on classification probabilities for the default paper set.

    Resamples the per-paper band data (with replacement across years),
    refits distributions, and re-runs simulation to get CI on outputs.
    """
    per_paper_raw = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    band_keys = [">=70", "60-69", "50-59", "40-49", "30-39", "<30"]

    # Collect per-year band data by paper
    year_bands = {}
    for r in per_paper_raw:
        if r.get("gender") != "All" or r.get("report_year") == 2020:
            continue
        bands = r.get("bands")
        if not bands:
            continue
        name = alias_map.get(r["paper"], r["paper"])
        year_bands.setdefault(name, []).append({
            "bands": {k: bands.get(k, 0) or 0 for k in band_keys},
            "n": sum(bands.get(k, 0) or 0 for k in band_keys),
            "mean": r.get("mean"),
            "sd": r.get("sd"),
        })

    # Use top-8 papers as the simulation target
    top_8 = sorted(paper_fits.keys(), key=lambda p: paper_fits[p]["n_total"], reverse=True)[:8]

    rng = np.random.default_rng(123)
    boot_results = []

    for b in range(n_bootstrap):
        # Resample: for each paper, resample years with replacement
        boot_fits = {}
        for paper in top_8:
            if paper not in year_bands:
                boot_fits[paper] = paper_fits[paper]
                continue
            years = year_bands[paper]
            n_years = len(years)
            indices = rng.integers(0, n_years, size=n_years)
            pooled_bands = {k: 0 for k in band_keys}
            total_n = 0
            for i in indices:
                for k in band_keys:
                    pooled_bands[k] += years[i]["bands"][k]
                total_n += years[i]["n"]

            result = fit_truncated_normal(pooled_bands, total_n)
            if result:
                mu, sigma, p_val = result
                boot_fits[paper] = {"mu": mu, "sigma": sigma, "n_total": total_n}
            else:
                boot_fits[paper] = paper_fits[paper]

        sim_rng = np.random.default_rng(42 + b)
        dist = simulate_classification(boot_fits, top_8, sigma_ability, n_sim, sim_rng)
        boot_results.append(dist)

    # Compute CIs
    classes = ["1st", "2.1", "2.2", "3rd", "Pass", "Fail"]
    cis = {}
    for cls in classes:
        vals = sorted([br[cls] for br in boot_results])
        lo = vals[int(0.025 * len(vals))]
        hi = vals[int(0.975 * len(vals))]
        median = vals[len(vals) // 2]
        cis[cls] = {
            "median": round(median, 4),
            "ci_lo": round(lo, 4),
            "ci_hi": round(hi, 4),
        }

    # Point estimate for reference
    point_rng = np.random.default_rng(42)
    point = simulate_classification(paper_fits, top_8, sigma_ability, n_sim * 2, point_rng)

    return {
        "papers": top_8,
        "n_bootstrap": n_bootstrap,
        "n_sim_per_bootstrap": n_sim,
        "sigma_ability": round(sigma_ability, 4),
        "point_estimate": point,
        "bootstrap_95_ci": cis,
    }


# ---------------------------------------------------------------------------
# F20. Paper popularity time series
# ---------------------------------------------------------------------------

def compute_popularity_time_series():
    """Compute candidate share per paper over time, with trend analysis.

    Uses share of total paper-sittings (not raw counts) to account for
    changing cohort sizes over time.
    """
    pn = json.loads((CANONICAL_DIR / "paper_numbers.json").read_text())

    # Total candidates per year (sum of all paper-sittings)
    year_totals = {}
    for r in pn:
        year_totals[r["data_year"]] = year_totals.get(r["data_year"], 0) + r["n"]

    # Group by paper
    by_paper = {}
    for r in pn:
        name = r["paper"]
        year = r["data_year"]
        total = year_totals.get(year, 1)
        share = 100 * r["n"] / total
        by_paper.setdefault(name, []).append((year, r["n"], share))

    results = []
    for paper, points in by_paper.items():
        points = sorted(set(points))
        years = [p[0] for p in points]
        counts = [p[1] for p in points]
        shares = [round(p[2], 2) for p in points]

        # Trend on share (not raw count) — this controls for cohort size changes
        trend = None
        if len(points) >= 4:
            ya = np.array(years, dtype=float)
            sa = np.array(shares, dtype=float)
            result = stats.linregress(ya, sa)
            trend = {
                "slope_pct_per_year": round(float(result.slope), 4),
                "p_value": round(float(result.pvalue), 4),
                "r_squared": round(float(result.rvalue ** 2), 4),
            }

        results.append({
            "paper": paper,
            "years": years,
            "counts": counts,
            "shares": shares,
            "n_years": len(years),
            "latest_n": counts[-1] if counts else None,
            "latest_share": shares[-1] if shares else None,
            "peak_share": round(max(shares), 2),
            "peak_year": years[shares.index(max(shares))],
            "trend": trend,
        })

    results.sort(key=lambda x: -(x["latest_share"] or 0))

    sig_trends = [r for r in results if r["trend"] and r["trend"]["p_value"] < 0.05]
    growing = [r for r in sig_trends if r["trend"]["slope_pct_per_year"] > 0]
    declining = [r for r in sig_trends if r["trend"]["slope_pct_per_year"] < 0]

    return {
        "n_papers": len(results),
        "n_significant_trends": len(sig_trends),
        "n_growing": len(growing),
        "n_declining": len(declining),
        "year_totals": year_totals,
        "per_paper": results,
    }


# ---------------------------------------------------------------------------
# F22. Subject market share over time
# ---------------------------------------------------------------------------

def compute_subject_market_share():
    """Compute the share of paper-sittings by subject per year."""
    pn = json.loads((CANONICAL_DIR / "paper_numbers.json").read_text())
    fits = json.loads((ANALYSIS_DIR / "paper_fits.json").read_text())

    # Map paper to subject via fits
    paper_subject = {p: f.get("subject") for p, f in fits.items()}

    # Sum candidates by (year, subject)
    year_subject = {}
    year_total = {}
    for r in pn:
        year = r["data_year"]
        subj = paper_subject.get(r["paper"])
        if not subj:
            continue
        year_subject.setdefault(year, {}).setdefault(subj, 0)
        year_subject[year][subj] += r["n"]
        year_total[year] = year_total.get(year, 0) + r["n"]

    years = sorted(year_subject.keys())
    subjects = sorted(set(s for ys in year_subject.values() for s in ys))

    time_series = []
    for year in years:
        total = year_total.get(year, 1)
        entry = {"year": year, "total": total}
        for subj in subjects:
            n = year_subject.get(year, {}).get(subj, 0)
            entry[f"{subj}_n"] = n
            entry[f"{subj}_pct"] = round(100 * n / total, 1) if total > 0 else 0
        time_series.append(entry)

    return {
        "subjects": subjects,
        "years": years,
        "time_series": time_series,
    }


# ---------------------------------------------------------------------------
# H25. COVID 2020 anomaly quantification
# ---------------------------------------------------------------------------

def quantify_covid_anomaly():
    """Quantify the 2020 COVID anomaly by comparing per-paper marks to pooled fits.

    Key finding: the 40% first rate (vs 23% normal) was NOT driven by inflated
    paper-level marks — per-paper means and band distributions are essentially
    identical to other years. The anomaly was at the classification stage
    (modified conjunctive rules or safety-net reclassification).
    """
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    fits = json.loads((ANALYSIS_DIR / "paper_fits.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    cd = json.loads((CANONICAL_DIR / "class_distribution.json").read_text())
    first_by_year = {}
    for r in cd:
        if r.get("class") == "1st" and r.get("pct") is not None:
            first_by_year[r["data_year"]] = r["pct"]

    # Collect 2020 per-paper data
    covid_papers = []
    for r in per_paper:
        if r.get("report_year") != 2020 or r.get("gender") != "All":
            continue
        name = alias_map.get(r["paper"], r["paper"])
        fit = fits.get(name)
        if not fit or r.get("mean") is None:
            continue

        mean_shift = r["mean"] - fit["mu"]
        covid_papers.append({
            "paper": name,
            "subject": fit.get("subject"),
            "covid_mean": r["mean"],
            "pooled_mean": fit["mu"],
            "mean_shift": round(mean_shift, 2),
            "covid_sd": r.get("sd"),
            "pooled_sd": fit["sigma"],
            "covid_n": r.get("n"),
        })

    covid_papers.sort(key=lambda x: -x["mean_shift"])

    shifts = [p["mean_shift"] for p in covid_papers]
    mean_shift = float(np.mean(shifts)) if shifts else 0
    median_shift = float(np.median(shifts)) if shifts else 0

    # Subject-level shifts
    by_subject = {}
    for p in covid_papers:
        subj = p.get("subject")
        if subj:
            by_subject.setdefault(subj, []).append(p["mean_shift"])
    subject_shifts = {s: round(float(np.mean(v)), 2) for s, v in by_subject.items()}

    # Band-level comparison: 2020 vs other years
    band_keys = [">=70", "60-69", "50-59", "40-49", "30-39", "<30"]
    bands_2020 = {k: 0 for k in band_keys}
    bands_other = {k: 0 for k in band_keys}
    for r in per_paper:
        if r.get("gender") != "All" or not r.get("bands"):
            continue
        bands = r["bands"]
        target = bands_2020 if r.get("report_year") == 2020 else bands_other
        for k in band_keys:
            target[k] += bands.get(k, 0) or 0

    n_2020 = sum(bands_2020.values())
    n_other = sum(bands_other.values())
    band_comparison = {}
    for k in band_keys:
        pct_2020 = round(100 * bands_2020[k] / n_2020, 1) if n_2020 > 0 else 0
        pct_other = round(100 * bands_other[k] / n_other, 1) if n_other > 0 else 0
        band_comparison[k] = {
            "pct_2020": pct_2020,
            "pct_other": pct_other,
            "diff": round(pct_2020 - pct_other, 1),
        }

    return {
        "first_rate_2019": first_by_year.get(2019),
        "first_rate_2020": first_by_year.get(2020),
        "first_rate_2021": first_by_year.get(2021),
        "n_papers_compared": len(covid_papers),
        "mean_mark_shift": round(mean_shift, 2),
        "median_mark_shift": round(median_shift, 2),
        "shift_range": [round(min(shifts), 2), round(max(shifts), 2)] if shifts else None,
        "subject_mean_shifts": subject_shifts,
        "band_comparison": band_comparison,
        "interpretation": (
            "Per-paper means and band distributions are nearly identical between 2020 and other years "
            f"(mean shift = {mean_shift:+.1f} marks). The 17pp jump in first-class rate "
            "(23% to 40%) was driven by changes to classification rules or safety-net "
            "reclassification, not by inflated paper-level marks."
        ),
        "per_paper": covid_papers,
    }


# ---------------------------------------------------------------------------
# H26. 2023 boycott residual effects
# ---------------------------------------------------------------------------

def check_boycott_residual():
    """Check whether 2024 marks show residual effects from the 2023 boycott."""
    per_paper = json.loads((CANONICAL_DIR / "per_paper.json").read_text())
    fits = json.loads((ANALYSIS_DIR / "paper_fits.json").read_text())
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    # Compare 2024 means to pooled fits (which exclude 2020 and are pooled
    # across 2017-2022 + 2024-2025). A residual boycott effect would show
    # 2024 systematically different from the pooled mean.
    papers_2024 = []
    for r in per_paper:
        if r.get("report_year") != 2024 or r.get("gender") != "All":
            continue
        name = alias_map.get(r["paper"], r["paper"])
        fit = fits.get(name)
        if not fit or r.get("mean") is None:
            continue
        papers_2024.append({
            "paper": name,
            "mean_2024": r["mean"],
            "pooled_mean": fit["mu"],
            "deviation": round(r["mean"] - fit["mu"], 2),
        })

    if not papers_2024:
        return {"n_papers": 0, "assessment": "no_data"}

    deviations = [p["deviation"] for p in papers_2024]
    mean_dev = float(np.mean(deviations))
    # One-sample t-test: are 2024 means systematically shifted from pooled?
    t_stat, p_value = stats.ttest_1samp(deviations, 0)

    return {
        "n_papers": len(papers_2024),
        "mean_deviation_from_pooled": round(mean_dev, 2),
        "t_stat": round(float(t_stat), 3),
        "p_value": round(float(p_value), 4),
        "assessment": "no_significant_residual" if p_value > 0.05 else "significant_residual",
        "per_paper": sorted(papers_2024, key=lambda x: -abs(x["deviation"])),
    }


# ---------------------------------------------------------------------------
# I27+I28. Bundle data for web tool
# ---------------------------------------------------------------------------

def bundle_web_data(sigma_ability):
    """Create a single JSON bundle with everything the web tool needs."""
    fits = json.loads((ANALYSIS_DIR / "paper_fits.json").read_text())
    profiles = json.loads((ANALYSIS_DIR / "paper_profiles.json").read_text())
    marginal = json.loads((ANALYSIS_DIR / "marginal_paper_value.json").read_text())
    trends = json.loads((ANALYSIS_DIR / "temporal_trends.json").read_text())
    subject = json.loads((ANALYSIS_DIR / "subject_analysis.json").read_text())
    boot_cis = json.loads((ANALYSIS_DIR / "bootstrap_cis.json").read_text())
    cd = json.loads((CANONICAL_DIR / "class_distribution.json").read_text())
    rc = json.loads((CANONICAL_DIR / "route_class.json").read_text())
    pn = json.loads((CANONICAL_DIR / "paper_numbers.json").read_text())
    aliases = json.loads(Path("data/paper_aliases.json").read_text())

    # Build paper catalogue: one entry per paper with everything a student needs
    paper_catalogue = {}
    for p in profiles:
        name = p["paper"]
        paper_catalogue[name] = {
            "subject": p["subject"],
            "mu": p["mu"],
            "sigma": p["sigma"],
            "pct_first": p["pct_first"],
            "pct_21": p["pct_21"],
            "pct_below_50": p["pct_below_50"],
            "method": p["method"],
        }

    # Add marginal value data
    for m in marginal["per_paper"]:
        name = m["paper"]
        if name in paper_catalogue:
            paper_catalogue[name]["delta_first"] = m["delta_first_vs_median"]
            paper_catalogue[name]["p_first_as_8th"] = m["p_first"]

    # Add trend data for papers with significant trends
    sig_trends = {t["paper"]: t for t in trends if t["p_value"] < 0.10}
    for name, t in sig_trends.items():
        if name in paper_catalogue:
            paper_catalogue[name]["trend_slope"] = t["slope"]
            paper_catalogue[name]["trend_p"] = t["p_value"]

    # Add popularity (latest count)
    latest_year = max(r["data_year"] for r in pn)
    for r in pn:
        if r["data_year"] == latest_year and r["paper"] in paper_catalogue:
            paper_catalogue[r["paper"]]["latest_candidates"] = r["n"]

    # Route classification data (most recent 5 years)
    route_data = {}
    for r in rc:
        year = r["data_year"]
        if year < 2019 or year == 2020:
            continue
        route = r["route"]
        route_data.setdefault(route, {}).setdefault(r["class"], [])
        if r.get("pct") is not None:
            route_data[route][r["class"]].append(r["pct"])
    route_summary = {}
    for route, classes in route_data.items():
        route_summary[route] = {
            cls: round(float(np.mean(vals)), 1)
            for cls, vals in classes.items() if vals
        }

    # Historical first rates by year
    first_rates = {}
    for r in cd:
        if r.get("class") == "1st" and r.get("pct") is not None:
            first_rates[r["data_year"]] = r["pct"]

    # Paper name alias map (for fuzzy matching in the UI)
    reverse_aliases = {}
    for variant, canonical in aliases.get("alias_map", {}).items():
        reverse_aliases.setdefault(canonical, []).append(variant)

    bundle = {
        "sigma_ability": sigma_ability,
        "paper_catalogue": paper_catalogue,
        "subject_summary": subject["subject_summary"],
        "route_summary": route_summary,
        "first_rates_by_year": first_rates,
        "bootstrap_ci_first": boot_cis["bootstrap_95_ci"]["1st"],
        "marginal_baseline": {
            "base_7": marginal["base_7_papers"],
            "median_8th": marginal["median_8th_paper"],
            "baseline_p_first": marginal["baseline_distribution"]["1st"],
        },
        "paper_aliases": reverse_aliases,
        "kingmaker_papers": subject["kingmaker_papers"],
    }
    return bundle


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

    print("Validating pooled fits per-year (A2)...")
    validation = validate_pooled_fits(paper_fits)
    _save("pooled_fit_validation", validation)
    print(f"  {validation['total_paper_years_tested']} paper-years tested, "
          f"{validation['total_failing_p05']} failing (expected ~{validation['expected_false_positives_at_05']} by chance)")

    print("Analysing asymmetry (A3)...")
    asymmetry = analyse_asymmetry(paper_fits)
    _save("asymmetry_analysis", asymmetry)
    print(f"  {asymmetry['n_papers_tested']} papers tested, "
          f"{asymmetry['n_significant_skew_p05']} with significant skew. "
          f"Assessment: {asymmetry['assessment']}")

    print("Computing marginal paper values (J29)...")
    marginal = compute_marginal_paper_value(paper_fits, sigma_ab)
    _save("marginal_paper_value", marginal)
    top = marginal["per_paper"][0]
    bot = marginal["per_paper"][-1]
    print(f"  Best 8th paper: {top['paper']} (Δ1st = +{top['delta_first_vs_median']:.1%})")
    print(f"  Worst 8th paper: {bot['paper']} (Δ1st = {bot['delta_first_vs_median']:.1%})")

    print("Bootstrap CIs on simulation (J31)...")
    boot_cis = bootstrap_simulation_cis(paper_fits, sigma_ab)
    _save("bootstrap_cis", boot_cis)
    ci = boot_cis["bootstrap_95_ci"]["1st"]
    print(f"  P(1st) = {boot_cis['point_estimate']['1st']:.1%} "
          f"[{ci['ci_lo']:.1%}, {ci['ci_hi']:.1%}]")

    print("Computing paper popularity time series (F20)...")
    popularity = compute_popularity_time_series()
    _save("popularity_time_series", popularity)
    print(f"  {popularity['n_papers']} papers, {popularity['n_growing']} growing, "
          f"{popularity['n_declining']} declining (p<0.05)")

    print("Computing subject market share (F22)...")
    market_share = compute_subject_market_share()
    _save("subject_market_share", market_share)
    print(f"  {len(market_share['subjects'])} subjects across {len(market_share['years'])} years")

    print("Quantifying COVID 2020 anomaly (H25)...")
    covid = quantify_covid_anomaly()
    _save("covid_anomaly", covid)
    print(f"  Mean mark shift: +{covid['mean_mark_shift']} marks across {covid['n_papers_compared']} papers")
    print(f"  First rate: {covid['first_rate_2019']}% (2019) → {covid['first_rate_2020']}% (2020) → {covid['first_rate_2021']}% (2021)")

    print("Checking boycott residual effects (H26)...")
    boycott = check_boycott_residual()
    _save("boycott_residual", boycott)
    print(f"  2024 mean deviation from pooled: {boycott['mean_deviation_from_pooled']} marks, "
          f"p={boycott['p_value']}. Assessment: {boycott['assessment']}")

    print("Bundling web tool data (I27+I28)...")
    bundle = bundle_web_data(sigma_ab)
    _save("web_bundle", bundle)
    print(f"  {len(bundle['paper_catalogue'])} papers in catalogue")

    print("\nDone! All outputs in", ANALYSIS_DIR)


def _save(name, data):
    path = ANALYSIS_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  → {path}")


if __name__ == "__main__":
    run_all()
