#!/usr/bin/env python3
"""
Generate a multi-page PDF report of all analysis results.

Usage:
    python report.py                   # generates output/report.pdf
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.ticker as mticker
import numpy as np
from collections import defaultdict
from scipy import stats as sp_stats

ANALYSIS_DIR = Path("data/analysis")
CANONICAL_DIR = Path("data/canonical")
OUTPUT_DIR = Path("output")


def load(name, directory=ANALYSIS_DIR):
    return json.loads((directory / f"{name}.json").read_text())


def load_alias_map():
    p = Path("data/paper_aliases.json")
    if p.exists():
        return json.loads(p.read_text()).get("alias_map", {})
    return {}


def make_report():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "report.pdf"

    fits = load("paper_fits")
    profiles = load("paper_profiles")
    trends = load("temporal_trends")
    subject = load("subject_analysis")
    params = load("simulation_params")
    marginal = load("marginal_paper_value")
    boot_cis = load("bootstrap_cis")
    covid = load("covid_anomaly")
    popularity = load("popularity_time_series")
    market_share = load("subject_market_share")
    gender_class = load("gender_class", CANONICAL_DIR)
    paper_numbers = load("paper_numbers", CANONICAL_DIR)
    class_dist = load("class_distribution", CANONICAL_DIR)
    alias_map = load_alias_map()

    subject_colours = {"Philosophy": "#8b5cf6", "Politics": "#059669", "Economics": "#d97706"}

    with PdfPages(path) as pdf:

        # -------------------------------------------------------------------
        # Title page
        # -------------------------------------------------------------------
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.6, "Oxford PPE Finals", ha="center", fontsize=28, fontweight="bold")
        fig.text(0.5, 0.54, "Statistical Analysis of Examiners' Reports 2011–2025",
                 ha="center", fontsize=16, color="#555")
        n_reliable = sum(1 for f in fits.values() if f.get("reliable", True))
        fig.text(0.5, 0.42, f"{n_reliable} papers fitted ({len(fits)} total) · 100k Monte Carlo sims · 15 years of data",
                 ha="center", fontsize=11, color="#888")
        fig.text(0.5, 0.35, f"σ_ability = {params['sigma_ability']:.2f}  |  "
                 f"Calibration target: 23.4% first rate", ha="center", fontsize=10, color="#888")
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 1. Overall first-class rate over time
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 5))
        firsts = {r["data_year"]: r for r in class_dist if r.get("class") == "1st"}
        years = sorted(firsts.keys())
        rates = [firsts[y].get("pct", 0) for y in years]
        ax.bar(years, rates, color=["#ef4444" if y == 2020 else "#3b82f6" for y in years], alpha=0.8)
        ax.axhline(23.4, color="#888", linestyle="--", linewidth=0.8, label="Calibration target (23.4%)")
        ax.set_xlabel("Year")
        ax.set_ylabel("First-class rate (%)")
        ax.set_title("Overall First-Class Rate, PPE Finals (2005–2025)")
        ax.legend()
        ax.grid(True, alpha=0.2)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 2. Gender gap
        # -------------------------------------------------------------------
        first_rates = {}
        for r in gender_class:
            if r.get("class") != "1st" or r.get("value_type") != "pct":
                continue
            year = r.get("data_year")
            gender = r.get("gender")
            if year and gender:
                first_rates[(year, gender)] = r["value"]

        years_g = sorted(set(y for y, _ in first_rates))
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[2, 1],
                                         sharex=True, gridspec_kw={"hspace": 0.08})
        valid_m = [(y, first_rates.get((y, "M"))) for y in years_g if first_rates.get((y, "M")) is not None]
        valid_f = [(y, first_rates.get((y, "F"))) for y in years_g if first_rates.get((y, "F")) is not None]
        ax1.plot([y for y, _ in valid_m], [r for _, r in valid_m], "o-", color="#2563eb", label="Male", ms=5)
        ax1.plot([y for y, _ in valid_f], [r for _, r in valid_f], "o-", color="#dc2626", label="Female", ms=5)
        ax1.axvspan(2019.5, 2020.5, alpha=0.1, color="gray")
        ax1.set_ylabel("First-class rate (%)")
        ax1.legend(loc="upper left")
        ax1.set_title("Gender Gap in First-Class Rate")
        ax1.grid(True, alpha=0.3)

        gaps, gap_years = [], []
        for y in years_g:
            m, f = first_rates.get((y, "M")), first_rates.get((y, "F"))
            if m is not None and f is not None:
                gaps.append(m - f)
                gap_years.append(y)
        ax2.bar(gap_years, gaps, color=["#2563eb" if g > 0 else "#dc2626" for g in gaps], alpha=0.7)
        ax2.axhline(0, color="black", linewidth=0.5)
        ax2.set_ylabel("Gap (M − F, pp)")
        ax2.set_xlabel("Year")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 3. Subject summary
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.axis("off")
        ax.set_title("Subject-Level Summary", fontsize=14, fontweight="bold", pad=20)
        headers = ["Subject", "Mean", "SD", "Papers", "Total n", "First Rate",
                    "Within Var", "Between Var", "Ratio"]
        rows = []
        for subj in ["Philosophy", "Politics", "Economics"]:
            s = subject["subject_summary"].get(subj, {})
            v = subject["variance_decomposition"].get(subj, {})
            fr = subject["first_rate_by_subject"].get(subj, "")
            rows.append([subj, s.get("weighted_mean", ""), s.get("weighted_sd", ""),
                         s.get("n_papers", ""), s.get("n_total", ""), f"{fr}%",
                         v.get("within_paper_var", ""), v.get("between_paper_var", ""),
                         v.get("ratio_within_to_between", "")])
        table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#e2e8f0")
                cell.set_text_props(fontweight="bold")
            else:
                cell.set_facecolor("#f8fafc")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 4. Kingmaker papers (mu vs sigma)
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 7))
        for name, fit in fits.items():
            c = subject_colours.get(fit.get("subject"), "#6b7280")
            alpha = 0.7 if fit.get("reliable", True) else 0.25
            marker = "o" if fit.get("reliable", True) else "x"
            ax.scatter(fit["mu"], fit["sigma"], c=c, s=50, alpha=alpha,
                      marker=marker, edgecolors="white", linewidth=0.3)
        reliable_fits = {n: f for n, f in fits.items() if f.get("reliable", True)}
        top = sorted(reliable_fits.items(), key=lambda x: -x[1]["sigma"])[:10]
        for name, fit in top:
            ax.annotate(name, (fit["mu"], fit["sigma"]), fontsize=7, alpha=0.9,
                       xytext=(5, 3), textcoords="offset points")
        for subj, c in subject_colours.items():
            ax.scatter([], [], c=c, s=50, label=subj)
        ax.legend(loc="upper left")
        ax.set_xlabel("Mean mark (μ)")
        ax.set_ylabel("Standard deviation (σ)")
        ax.axhline(subject.get("kingmaker_threshold", 10.2), color="#ef4444", linestyle="--",
                   linewidth=0.8, alpha=0.5, label=f"Kingmaker threshold (2× median σ)")
        ax.set_title("Paper Risk/Reward: Mean vs Volatility")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 5. Paper difficulty rankings
        # -------------------------------------------------------------------
        for title, sorted_profiles, n_show in [
            ("Highest Mean (Easiest Papers)", profiles[:15], 15),
            ("Lowest Mean (Hardest Papers)", list(reversed(profiles[-15:])), 15),
            ("Highest Volatility (σ)", sorted(profiles, key=lambda p: -p["sigma"])[:15], 15),
        ]:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.axis("off")
            ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
            headers = ["#", "Paper", "Subject", "μ", "σ", "%1st", "%<50"]
            rows = []
            for i, p in enumerate(sorted_profiles[:n_show], 1):
                rows.append([str(i), p["paper"][:45], p["subject"] or "",
                           f"{p['mu']:.1f}", f"{p['sigma']:.1f}",
                           f"{p['pct_first']}", f"{p['pct_below_50']}"])
            table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center",
                           colWidths=[0.04, 0.4, 0.12, 0.06, 0.06, 0.06, 0.06])
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 1.4)
            for (row, col), cell in table.get_celld().items():
                if row == 0:
                    cell.set_facecolor("#e2e8f0")
                    cell.set_text_props(fontweight="bold")
                else:
                    cell.set_facecolor("#f8fafc" if row % 2 == 0 else "white")
            fig.tight_layout()
            pdf.savefig(fig)
            plt.close()

        # -------------------------------------------------------------------
        # 6. Popularity vs difficulty
        # -------------------------------------------------------------------
        yearly_n = defaultdict(lambda: defaultdict(int))
        for r in paper_numbers:
            name = alias_map.get(r.get("paper", ""), r.get("paper", ""))
            year = r.get("data_year")
            if year and name in fits:
                yearly_n[name][year] = max(yearly_n[name][year], r.get("n", 0))
        avg_n = {n: np.mean(list(c.values())) for n, c in yearly_n.items() if c}

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        for ax, attr, ylabel, title in [
            (axes[0], "mu", "Mean mark (μ)", "Mean vs Popularity"),
            (axes[1], "sigma", "Standard deviation (σ)", "Volatility vs Popularity"),
        ]:
            for name, fit in fits.items():
                n = avg_n.get(name, 0)
                if n < 1:
                    continue
                c = subject_colours.get(fit.get("subject"), "#6b7280")
                ax.scatter(n, fit[attr], c=c, s=40, alpha=0.7, edgecolors="white", linewidth=0.3)
            for subj, c in subject_colours.items():
                ax.scatter([], [], c=c, s=40, label=subj)
            ax.legend(fontsize=8)
            ax.set_xlabel("Avg candidates/year")
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, alpha=0.3)

        # Annotate high-sigma outliers on right panel
        for name, fit in fits.items():
            if fit["sigma"] > 9 and avg_n.get(name, 0) > 0:
                axes[1].annotate(name, (avg_n[name], fit["sigma"]),
                               fontsize=7, alpha=0.8, xytext=(5, 3), textcoords="offset points")

        # Correlation stats
        papers_with = [n for n in fits if n in avg_n and avg_n[n] > 0]
        ns = np.array([avg_n[n] for n in papers_with])
        mus = np.array([fits[n]["mu"] for n in papers_with])
        sigs = np.array([fits[n]["sigma"] for n in papers_with])
        r_mu, p_mu = sp_stats.pearsonr(ns, mus)
        r_sig, p_sig = sp_stats.pearsonr(ns, sigs)
        fig.suptitle(f"Popularity vs Difficulty/Volatility   "
                     f"(r_mean={r_mu:.2f}, p={p_mu:.3f}  |  r_sigma={r_sig:.2f}, p={p_sig:.3f})",
                     fontsize=11)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 7. Temporal trends
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.axis("off")
        ax.set_title("Temporal Trends in Paper Mean Marks (p < 0.10)", fontsize=14,
                     fontweight="bold", pad=20)
        headers = ["Paper", "Subject", "Slope", "95% CI", "p-value", "R²", "n"]
        rows = []
        for t in trends:
            if t["p_value"] >= 0.10:
                break
            rows.append([
                t["paper"][:40], t["subject"] or "",
                f"{t['slope']:+.3f}",
                f"[{t['slope_ci_lo']:+.3f}, {t['slope_ci_hi']:+.3f}]",
                f"{t['p_value']:.4f}",
                f"{t['r_squared']:.3f}",
                str(t["n_years"]),
            ])
        table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center",
                        colWidths=[0.35, 0.12, 0.08, 0.18, 0.08, 0.06, 0.04])
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#e2e8f0")
                cell.set_text_props(fontweight="bold")
            elif row <= 3:  # first 3 are significant
                cell.set_facecolor("#fef3c7")
            else:
                cell.set_facecolor("#f8fafc" if row % 2 == 0 else "white")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 8. Marginal paper value
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis("off")
        baseline_p = marginal["baseline_distribution"]["1st"]
        ax.set_title(f"Marginal Paper Value: Effect of 8th Paper on P(1st)\n"
                     f"Baseline = {baseline_p:.1%} with {marginal['median_8th_paper']}",
                     fontsize=13, fontweight="bold", pad=20)
        headers = ["Paper", "Subject", "μ", "σ", "P(1st)", "ΔP(1st)"]
        rows = []
        pp = marginal["per_paper"]
        show = pp[:10] + [None] + pp[-5:]
        for p in show:
            if p is None:
                rows.append(["···", "", "", "", "", ""])
                continue
            rows.append([
                p["paper"][:40], p["subject"] or "",
                f"{p['mu']:.1f}", f"{p['sigma']:.1f}",
                f"{p['p_first']:.1%}",
                f"{p['delta_first_vs_median']:+.1%}",
            ])
        table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center",
                        colWidths=[0.38, 0.14, 0.06, 0.06, 0.08, 0.10])
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.4)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#e2e8f0")
                cell.set_text_props(fontweight="bold")
            elif row <= 10:
                cell.set_facecolor("#dcfce7")
            elif row == 11:
                cell.set_facecolor("white")
            else:
                cell.set_facecolor("#fee2e2")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 9. COVID 2020 anomaly
        # -------------------------------------------------------------------
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        # Left: first rate bar chart highlighting 2020
        firsts_covid = {r["data_year"]: r for r in class_dist if r.get("class") == "1st"}
        cy = sorted(y for y in firsts_covid if 2015 <= y <= 2025)
        cr = [firsts_covid[y].get("pct", 0) for y in cy]
        colors = ["#ef4444" if y == 2020 else "#3b82f6" for y in cy]
        ax1.bar(cy, cr, color=colors, alpha=0.8)
        ax1.axhline(23.4, color="#888", linestyle="--", linewidth=0.8)
        ax1.set_title("First-Class Rate (2020 in red)")
        ax1.set_ylabel("First rate (%)")
        ax1.set_xlabel("Year")
        ax1.grid(True, alpha=0.2)

        # Right: band comparison
        bc = covid["band_comparison"]
        band_order = [">=70", "60-69", "50-59", "40-49", "30-39", "<30"]
        x = np.arange(len(band_order))
        w = 0.35
        pct_2020 = [bc[k]["pct_2020"] for k in band_order]
        pct_other = [bc[k]["pct_other"] for k in band_order]
        ax2.bar(x - w/2, pct_other, w, label="Other years", color="#3b82f6", alpha=0.7)
        ax2.bar(x + w/2, pct_2020, w, label="2020", color="#ef4444", alpha=0.7)
        ax2.set_xticks(x)
        ax2.set_xticklabels(band_order)
        ax2.set_title("Band Distribution: 2020 vs Other Years")
        ax2.set_ylabel("% of marks")
        ax2.legend()
        ax2.grid(True, alpha=0.2)

        fig.suptitle("COVID 2020: First Rate Doubled Despite Identical Paper-Level Marks",
                     fontsize=12, fontweight="bold")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 10. Subject market share over time
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 5))
        ms = market_share["time_series"]
        ms_years = [e["year"] for e in ms]
        subj_colors_ms = {"Economics": "#d97706", "Philosophy": "#8b5cf6", "Politics": "#059669"}
        for subj in market_share["subjects"]:
            pcts = [e[f"{subj}_pct"] for e in ms]
            ax.plot(ms_years, pcts, "o-", label=subj, color=subj_colors_ms.get(subj, "#6b7280"),
                    ms=4, linewidth=2)
        ax.set_xlabel("Year")
        ax.set_ylabel("Share of paper-sittings (%)")
        ax.set_title("Subject Market Share Over Time")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(20, 45)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 11. Popularity trends (top movers by total change, not just p-value)
        # -------------------------------------------------------------------
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

        # Filter to papers with significant trends AND >= 1pp total change
        sig_trends_pop = []
        for p in popularity["per_paper"]:
            if not p["trend"] or p["trend"]["p_value"] >= 0.05:
                continue
            if len(p["shares"]) < 2:
                continue
            total_change = p["shares"][-1] - p["shares"][0]
            if abs(total_change) >= 1.0:
                sig_trends_pop.append({**p, "total_change": total_change})

        growing_p = sorted([p for p in sig_trends_pop if p["total_change"] > 0],
                           key=lambda x: -x["total_change"])[:8]
        declining_p = sorted([p for p in sig_trends_pop if p["total_change"] < 0],
                             key=lambda x: x["total_change"])[:8]

        for p in growing_p:
            ax1.plot(p["years"], p["shares"], "o-", ms=3,
                     label=f"{p['paper'][:28]} ({p['total_change']:+.1f}pp)", alpha=0.8)
        ax1.set_title("Growing Papers (>1pp total change)")
        ax1.set_ylabel("Share of paper-sittings (%)")
        ax1.set_xlabel("Year")
        ax1.legend(fontsize=6, loc="upper left")
        ax1.grid(True, alpha=0.3)

        for p in declining_p:
            ax2.plot(p["years"], p["shares"], "o-", ms=3,
                     label=f"{p['paper'][:28]} ({p['total_change']:+.1f}pp)", alpha=0.8)
        ax2.set_title("Declining Papers (>1pp total change)")
        ax2.set_ylabel("Share of paper-sittings (%)")
        ax2.set_xlabel("Year")
        ax2.legend(fontsize=6, loc="upper right")
        ax2.grid(True, alpha=0.3)

        fig.suptitle("Paper Popularity Trends (share of all paper-sittings, significant trends with >1pp change)",
                     fontsize=11, fontweight="bold")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 12. Bootstrap CIs
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(8, 4))
        classes = ["1st", "2.1", "2.2", "3rd", "Pass", "Fail"]
        point_vals = [boot_cis["point_estimate"][c] for c in classes]
        ci_lo = [boot_cis["bootstrap_95_ci"][c]["ci_lo"] for c in classes]
        ci_hi = [boot_cis["bootstrap_95_ci"][c]["ci_hi"] for c in classes]
        x = np.arange(len(classes))
        bars = ax.bar(x, point_vals, color=["#22c55e", "#3b82f6", "#f59e0b", "#ef4444", "#6b7280", "#1f2937"],
                      alpha=0.8)
        err_lo = [p - l for p, l in zip(point_vals, ci_lo)]
        err_hi = [h - p for p, h in zip(point_vals, ci_hi)]
        ax.errorbar(x, point_vals, yerr=[err_lo, err_hi], fmt="none", ecolor="black",
                    capsize=4, linewidth=1.5)
        ax.set_xticks(x)
        ax.set_xticklabels(classes)
        ax.set_ylabel("Probability")
        paper_list = ", ".join(boot_cis["papers"][:3]) + f" + {len(boot_cis['papers'])-3} more"
        ax.set_title(f"Classification Probabilities for a Typical Student\n"
                     f"(8 most popular papers: {paper_list})\n"
                     f"Error bars = 95% bootstrap CI from resampling year-level data",
                     fontsize=10)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.grid(True, alpha=0.2, axis="y")
        for bar, val in zip(bars, point_vals):
            if val > 0.005:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                        f"{val:.1%}", ha="center", fontsize=9)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 13. Kingmaker table
        # -------------------------------------------------------------------
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.axis("off")
        km_threshold = subject.get("kingmaker_threshold", 10.2)
        med_sig = subject.get("median_sigma", 5.1)
        ax.set_title(f"Kingmaker Papers (σ ≥ 2× median σ = {km_threshold:.1f}; median σ = {med_sig:.1f})",
                     fontsize=13, fontweight="bold", pad=20)
        headers = ["#", "Paper", "Subject", "μ", "σ", "Total n"]
        rows = []
        for i, k in enumerate(subject["kingmaker_papers"], 1):
            rows.append([str(i), k["paper"][:45], k["subject"] or "",
                       f"{k['mu']:.1f}", f"{k['sigma']:.1f}", str(k["n_total"])])
        table = ax.table(cellText=rows, colLabels=headers, loc="center", cellLoc="center",
                        colWidths=[0.04, 0.45, 0.15, 0.06, 0.06, 0.08])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor("#e2e8f0")
                cell.set_text_props(fontweight="bold")
            else:
                cell.set_facecolor("#fff7ed" if row <= 3 else "#f8fafc")
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close()

        # -------------------------------------------------------------------
        # 9. Methodology notes
        # -------------------------------------------------------------------
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.08, 0.92, "Methodology Notes", fontsize=18, fontweight="bold")
        notes = [
            "Distribution fitting",
            "  Truncated normal (support [0,100]) fitted via MLE on pooled band counts.",
            "  6 bins: ≥70, 60–69, 50–59, 40–49, 30–39, <30.",
            "  81 papers fitted (65 band MLE, 16 moment estimates). 2020 excluded.",
            "  Goodness of fit: chi-squared test (bins merged where expected < 5).",
            "",
            "Classification rules",
            "  1st: avg ≥ 68.5, ≥ 2 marks of 70+, no mark < 50.",
            "  2.1: avg ≥ 59.0, ≥ 3 marks of 60+.",
            "  2.2: avg ≥ 49.0, ≥ 3 marks of 50+.",
            "  3rd: avg ≥ 40.0, ≥ 3 marks of 40+.",
            "",
            "Monte Carlo simulation",
            "  mark_i = μ_i + θ + ε_i,  θ ~ N(0, σ²_ability),  "
            "ε_i ~ N(0, σ²_paper − σ²_ability).",
            f"  σ_ability = {params['sigma_ability']:.2f}, calibrated to 23.4% first-class rate.",
            "  100,000 simulations per paper combination.",
            "",
            "Temporal trends",
            "  OLS regression of mean mark on year, excluding 2020.",
            "  95% CI: slope ± t_{n−2, 0.025} × stderr.",
            "",
            "Key limitations",
            "  • Truncated normal may poorly fit papers with ceiling effects or bimodality.",
            "  • Single-factor ability model; same-subject papers may be more correlated.",
            "  • Selection effects: observed distributions reflect who chose the paper.",
            "  • Temporal pooling: distributions are averages across years, not year-specific.",
        ]
        y = 0.87
        for line in notes:
            bold = not line.startswith(" ") and line.strip()
            fig.text(0.08, y, line, fontsize=9,
                    fontweight="bold" if bold else "normal", fontfamily="monospace")
            y -= 0.028
        pdf.savefig(fig)
        plt.close()

    print(f"Report saved to {path}")


if __name__ == "__main__":
    make_report()
