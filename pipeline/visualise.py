#!/usr/bin/env python3
"""
Generate charts and summary tables from analysis outputs.

Usage:
    python visualise.py              # generate all charts + tables
    python visualise.py --charts     # charts only
    python visualise.py --tables     # tables only
"""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

ANALYSIS_DIR = Path("data/analysis")
CANONICAL_DIR = Path("data/canonical")
OUTPUT_DIR = Path("output/charts")
TABLE_DIR = Path("output/tables")


def load(name, directory=ANALYSIS_DIR):
    return json.loads((directory / f"{name}.json").read_text())


# ---------------------------------------------------------------------------
# Gender gap time series (E16, K32)
# ---------------------------------------------------------------------------

def chart_gender_gap():
    """Plot 1st-class rate by gender over time."""
    gender_class = load("gender_class", CANONICAL_DIR)

    # Build {(year, gender): pct_first}
    first_rates = {}
    for r in gender_class:
        if r.get("class") != "1st" or r.get("value_type") != "pct":
            continue
        year = r.get("data_year")
        gender = r.get("gender")
        if year and gender:
            first_rates[(year, gender)] = r["value"]

    years = sorted(set(y for y, _ in first_rates))
    m_rates = [first_rates.get((y, "M")) for y in years]
    f_rates = [first_rates.get((y, "F")) for y in years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), height_ratios=[2, 1],
                                     sharex=True, gridspec_kw={"hspace": 0.08})

    # Top panel: rates
    valid_m = [(y, r) for y, r in zip(years, m_rates) if r is not None]
    valid_f = [(y, r) for y, r in zip(years, f_rates) if r is not None]
    ax1.plot([y for y, _ in valid_m], [r for _, r in valid_m], "o-", color="#2563eb", label="Male", markersize=5)
    ax1.plot([y for y, _ in valid_f], [r for _, r in valid_f], "o-", color="#dc2626", label="Female", markersize=5)

    # Highlight COVID year
    if (2020, "M") in first_rates:
        ax1.axvspan(2019.5, 2020.5, alpha=0.1, color="gray")
        ax1.text(2020, ax1.get_ylim()[1] * 0.95, "COVID", ha="center", fontsize=8, color="gray")

    ax1.set_ylabel("First-class rate (%)")
    ax1.legend(loc="upper left")
    ax1.set_title("Gender Gap in First-Class Rate, PPE Finals (2006–2025)")
    ax1.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax1.grid(True, alpha=0.3)

    # Bottom panel: gap
    gaps = []
    gap_years = []
    for y in years:
        m = first_rates.get((y, "M"))
        f = first_rates.get((y, "F"))
        if m is not None and f is not None:
            gaps.append(m - f)
            gap_years.append(y)

    colours = ["#2563eb" if g > 0 else "#dc2626" for g in gaps]
    ax2.bar(gap_years, gaps, color=colours, alpha=0.7)
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.set_ylabel("Gap (M − F, pp)")
    ax2.set_xlabel("Year")
    ax2.grid(True, alpha=0.3)

    plt.savefig(OUTPUT_DIR / "gender_gap_time_series.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  gender_gap_time_series.png")


# ---------------------------------------------------------------------------
# Paper popularity vs difficulty (F21, K33)
# ---------------------------------------------------------------------------

def chart_popularity_vs_difficulty():
    """Scatter: mean mark vs avg candidates, coloured by subject. Size by sigma."""
    fits = load("paper_fits")
    paper_numbers = load("paper_numbers", CANONICAL_DIR)

    # Compute average annual candidates per canonical paper
    from collections import defaultdict
    yearly_n = defaultdict(lambda: defaultdict(int))
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    for r in paper_numbers:
        name = alias_map.get(r.get("paper", ""), r.get("paper", ""))
        year = r.get("data_year")
        if year and name in fits:
            yearly_n[name][year] = max(yearly_n[name][year], r.get("n", 0))

    avg_n = {name: np.mean(list(counts.values())) for name, counts in yearly_n.items() if counts}

    subject_colours = {"Philosophy": "#8b5cf6", "Politics": "#059669", "Economics": "#d97706"}

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # Left: mean vs popularity
    ax = axes[0]
    for name, fit in fits.items():
        n = avg_n.get(name, 0)
        if n < 1:
            continue
        c = subject_colours.get(fit.get("subject"), "#6b7280")
        ax.scatter(n, fit["mu"], c=c, s=40, alpha=0.7, edgecolors="white", linewidth=0.3)

    for subj, c in subject_colours.items():
        ax.scatter([], [], c=c, s=40, label=subj)
    ax.legend()
    ax.set_xlabel("Average candidates per year")
    ax.set_ylabel("Mean mark (μ)")
    ax.set_title("Paper Mean vs Popularity")
    ax.grid(True, alpha=0.3)

    # Right: sigma vs popularity
    ax = axes[1]
    for name, fit in fits.items():
        n = avg_n.get(name, 0)
        if n < 1:
            continue
        c = subject_colours.get(fit.get("subject"), "#6b7280")
        ax.scatter(n, fit["sigma"], c=c, s=40, alpha=0.7, edgecolors="white", linewidth=0.3)

    for subj, c in subject_colours.items():
        ax.scatter([], [], c=c, s=40, label=subj)
    ax.legend()
    ax.set_xlabel("Average candidates per year")
    ax.set_ylabel("Standard deviation (σ)")
    ax.set_title("Paper Spread vs Popularity")
    ax.grid(True, alpha=0.3)

    # Annotate outliers (high sigma)
    for name, fit in fits.items():
        if fit["sigma"] > 9:
            n = avg_n.get(name, 0)
            if n > 0:
                ax.annotate(name, (n, fit["sigma"]), fontsize=7, alpha=0.8,
                          xytext=(5, 3), textcoords="offset points")

    plt.suptitle("Paper Difficulty/Spread vs Popularity", fontsize=14, y=1.01)
    plt.savefig(OUTPUT_DIR / "popularity_vs_difficulty.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  popularity_vs_difficulty.png")


# ---------------------------------------------------------------------------
# Kingmaker chart (K37)
# ---------------------------------------------------------------------------

def chart_kingmakers():
    """Sigma vs mu for all papers, highlighting kingmakers."""
    fits = load("paper_fits")
    subject_colours = {"Philosophy": "#8b5cf6", "Politics": "#059669", "Economics": "#d97706"}

    fig, ax = plt.subplots(figsize=(12, 7))
    for name, fit in fits.items():
        c = subject_colours.get(fit.get("subject"), "#6b7280")
        ax.scatter(fit["mu"], fit["sigma"], c=c, s=50, alpha=0.7, edgecolors="white", linewidth=0.3)

    # Label top-sigma papers
    top = sorted(fits.items(), key=lambda x: -x[1]["sigma"])[:10]
    for name, fit in top:
        ax.annotate(name, (fit["mu"], fit["sigma"]), fontsize=7, alpha=0.9,
                   xytext=(5, 3), textcoords="offset points")

    for subj, c in subject_colours.items():
        ax.scatter([], [], c=c, s=50, label=subj)
    ax.legend(loc="upper left")
    ax.set_xlabel("Mean mark (μ)")
    ax.set_ylabel("Standard deviation (σ)")
    ax.set_title("Paper Risk/Reward: Mean vs Spread")
    ax.grid(True, alpha=0.3)

    plt.savefig(OUTPUT_DIR / "kingmaker_papers.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("  kingmaker_papers.png")


# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

def table_subject_summary():
    """Subject-level summary table."""
    subject = load("subject_analysis")

    lines = ["# Subject-Level Summary", ""]
    lines.append("| Subject | Weighted Mean | Weighted SD | Papers | Total n | First Rate | Within Var | Between Var | Ratio |")
    lines.append("|---------|-------------|------------|--------|---------|-----------|-----------|------------|-------|")

    for subj in ["Philosophy", "Politics", "Economics"]:
        s = subject["subject_summary"].get(subj, {})
        v = subject["variance_decomposition"].get(subj, {})
        fr = subject["first_rate_by_subject"].get(subj, "—")
        lines.append(
            f"| {subj} | {s.get('weighted_mean','—')} | {s.get('weighted_sd','—')} "
            f"| {s.get('n_papers','—')} | {s.get('n_total','—')} | {fr}% "
            f"| {v.get('within_paper_var','—')} | {v.get('between_paper_var','—')} "
            f"| {v.get('ratio_within_to_between','—')} |"
        )

    lines.extend(["", "## Kingmaker Papers (Top 10 by σ)", ""])
    lines.append("| Paper | Subject | μ | σ | Total n |")
    lines.append("|-------|---------|---|---|---------|")
    for k in subject["kingmaker_papers"]:
        lines.append(f"| {k['paper']} | {k['subject']} | {k['mu']} | {k['sigma']} | {k['n_total']} |")

    text = "\n".join(lines) + "\n"
    (TABLE_DIR / "subject_summary.md").write_text(text)
    print("  subject_summary.md")


def table_paper_rankings():
    """Paper difficulty ranking tables."""
    profiles = load("paper_profiles")

    lines = ["# Paper Difficulty Rankings", ""]

    # Top 15 by mean (easiest)
    lines.extend(["## Highest Mean (Easiest)", ""])
    lines.append("| # | Paper | Subject | μ | σ | %1st | %<50 | n |")
    lines.append("|---|-------|---------|---|---|------|------|---|")
    for i, p in enumerate(profiles[:15], 1):
        lines.append(
            f"| {i} | {p['paper']} | {p['subject']} | {p['mu']} | {p['sigma']} "
            f"| {p['pct_first']} | {p['pct_below_50']} | {p['n_total']} |"
        )

    # Bottom 15 by mean (hardest)
    lines.extend(["", "## Lowest Mean (Hardest)", ""])
    lines.append("| # | Paper | Subject | μ | σ | %1st | %<50 | n |")
    lines.append("|---|-------|---------|---|---|------|------|---|")
    for i, p in enumerate(reversed(profiles[-15:]), 1):
        lines.append(
            f"| {i} | {p['paper']} | {p['subject']} | {p['mu']} | {p['sigma']} "
            f"| {p['pct_first']} | {p['pct_below_50']} | {p['n_total']} |"
        )

    # Top 15 by sigma (highest spread)
    by_sigma = sorted(profiles, key=lambda p: -p["sigma"])
    lines.extend(["", "## Highest Spread (σ)", ""])
    lines.append("| # | Paper | Subject | σ | μ | %1st | %<50 | n |")
    lines.append("|---|-------|---------|---|---|------|------|---|")
    for i, p in enumerate(by_sigma[:15], 1):
        lines.append(
            f"| {i} | {p['paper']} | {p['subject']} | {p['sigma']} | {p['mu']} "
            f"| {p['pct_first']} | {p['pct_below_50']} | {p['n_total']} |"
        )

    text = "\n".join(lines) + "\n"
    (TABLE_DIR / "paper_rankings.md").write_text(text)
    print("  paper_rankings.md")


def table_temporal_trends():
    """Temporal trends summary table."""
    trends = load("temporal_trends")

    lines = ["# Temporal Trends in Paper Mean Marks", "",
             "OLS regression of mean mark on year (excluding 2020). Sorted by p-value.", ""]
    lines.append("| Paper | Subject | Slope | 95% CI | p-value | R² | n years | Range |")
    lines.append("|-------|---------|-------|--------|---------|-----|---------|-------|")

    # Show all with p < 0.10
    for t in trends:
        if t["p_value"] >= 0.10:
            break
        sig = "**" if t["p_value"] < 0.05 else ""
        lines.append(
            f"| {sig}{t['paper']}{sig} | {t['subject']} "
            f"| {t['slope']:+.3f} | [{t['slope_ci_lo']:+.3f}, {t['slope_ci_hi']:+.3f}] "
            f"| {t['p_value']:.4f} | {t['r_squared']:.3f} "
            f"| {t['n_years']} | {t['years_range'][0]}–{t['years_range'][1]} |"
        )

    n_total = len(trends)
    n_sig = sum(1 for t in trends if t["p_value"] < 0.05)
    n_near = sum(1 for t in trends if 0.05 <= t["p_value"] < 0.10)
    lines.extend(["",
        f"**{n_total}** papers analysed. **{n_sig}** significant at p<0.05, "
        f"**{n_near}** near-significant (0.05 <= p < 0.10). "
        f"Bold = significant at p<0.05."])

    text = "\n".join(lines) + "\n"
    (TABLE_DIR / "temporal_trends.md").write_text(text)
    print("  temporal_trends.md")


def table_popularity_difficulty_correlation():
    """Compute and report correlation between popularity and difficulty/variance."""
    fits = load("paper_fits")
    paper_numbers = load("paper_numbers", CANONICAL_DIR)
    aliases_path = Path("data/paper_aliases.json")
    alias_map = {}
    if aliases_path.exists():
        alias_map = json.loads(aliases_path.read_text()).get("alias_map", {})

    from collections import defaultdict
    yearly_n = defaultdict(lambda: defaultdict(int))
    for r in paper_numbers:
        name = alias_map.get(r.get("paper", ""), r.get("paper", ""))
        year = r.get("data_year")
        if year and name in fits:
            yearly_n[name][year] = max(yearly_n[name][year], r.get("n", 0))

    avg_n = {name: np.mean(list(counts.values())) for name, counts in yearly_n.items() if counts}

    # Compute correlations
    from scipy import stats as sp_stats
    papers_with_data = [name for name in fits if name in avg_n and avg_n[name] > 0]
    ns = np.array([avg_n[name] for name in papers_with_data])
    mus = np.array([fits[name]["mu"] for name in papers_with_data])
    sigmas = np.array([fits[name]["sigma"] for name in papers_with_data])

    r_mu, p_mu = sp_stats.pearsonr(ns, mus)
    r_sig, p_sig = sp_stats.pearsonr(ns, sigmas)
    r_spearman_mu, p_spearman_mu = sp_stats.spearmanr(ns, mus)
    r_spearman_sig, p_spearman_sig = sp_stats.spearmanr(ns, sigmas)

    lines = ["# Popularity vs Difficulty/Spread", "",
             f"n = {len(papers_with_data)} papers with both fitted distributions and candidate count data.", ""]
    lines.append("| Relationship | Pearson r | p-value | Spearman ρ | p-value |")
    lines.append("|-------------|-----------|---------|-----------|---------|")
    lines.append(f"| Popularity vs Mean (μ) | {r_mu:.3f} | {p_mu:.4f} | {r_spearman_mu:.3f} | {p_spearman_mu:.4f} |")
    lines.append(f"| Popularity vs Spread (σ) | {r_sig:.3f} | {p_sig:.4f} | {r_spearman_sig:.3f} | {p_spearman_sig:.4f} |")

    lines.extend(["", "## Interpretation", ""])
    if p_mu < 0.05:
        direction = "easier" if r_mu > 0 else "harder"
        lines.append(f"- More popular papers tend to be **{direction}** (r={r_mu:.3f}, p={p_mu:.4f}).")
    else:
        lines.append(f"- No significant relationship between popularity and mean difficulty (r={r_mu:.3f}, p={p_mu:.4f}).")

    if p_sig < 0.05:
        direction = "higher spread" if r_sig > 0 else "lower spread"
        lines.append(f"- More popular papers tend to have **{direction}** (r={r_sig:.3f}, p={p_sig:.4f}).")
    else:
        lines.append(f"- No significant relationship between popularity and spread (r={r_sig:.3f}, p={p_sig:.4f}).")

    text = "\n".join(lines) + "\n"
    (TABLE_DIR / "popularity_difficulty.md").write_text(text)
    print("  popularity_difficulty.md")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_charts():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating charts...")
    chart_gender_gap()
    chart_popularity_vs_difficulty()
    chart_kingmakers()

def run_tables():
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating tables...")
    table_subject_summary()
    table_paper_rankings()
    table_temporal_trends()
    table_popularity_difficulty_correlation()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--charts", action="store_true")
    parser.add_argument("--tables", action="store_true")
    args = parser.parse_args()

    if not args.charts and not args.tables:
        args.charts = args.tables = True

    if args.charts:
        run_charts()
    if args.tables:
        run_tables()

    print("\nDone!")
