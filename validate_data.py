#!/usr/bin/env python3
"""
Data validation suite for canonical and analysis outputs.

Checks run after build_canonical.py and analysis.py to verify data integrity:
  1. Alias completeness — all raw names resolve via alias_map
  2. Coverage — paper-count and population-weighted per_paper coverage
  3. Dedup integrity — no remaining duplicate (year, paper, gender) groups
  4. Fit reliability — flag papers with n_total < 30 or sigma < 2.0
  5. Consistency — per_paper means within plausible range, no NaN/null anomalies

Usage:
    python validate_data.py          # run all checks
    python validate_data.py --quick  # just coverage + dedup (fast)
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path("data/raw")
CANONICAL_DIR = Path("data/canonical")
ANALYSIS_DIR = Path("data/analysis")
ALIASES_PATH = Path("data/paper_aliases.json")


def load(path):
    return json.loads(path.read_text())


def check_alias_completeness():
    """Verify all raw paper names in 2024/2025 per_paper are in alias_map."""
    print("=" * 70)
    print("1. ALIAS COMPLETENESS")
    print("=" * 70)

    if not ALIASES_PATH.exists():
        print("  SKIP: paper_aliases.json not found")
        return True

    aliases = load(ALIASES_PATH)
    alias_map = aliases.get("alias_map", {})

    unaliased = []
    for f in sorted(RAW_DIR.glob("*_per_paper.json")):
        year = int(f.name[:4])
        data = load(f)
        for r in data:
            name = r.get("paper", "")
            if name and name not in alias_map:
                unaliased.append((year, name))

    if unaliased:
        print(f"  FAIL: {len(unaliased)} raw names not in alias_map:")
        for year, name in sorted(set(unaliased)):
            print(f"    {year}: '{name}'")
        return False
    else:
        total_variants = len(alias_map)
        canonical = len(set(alias_map.values()))
        print(f"  PASS: all raw names aliased ({total_variants} variants → {canonical} canonical)")
        return True


def check_coverage():
    """Compute paper-count and population-weighted coverage."""
    print("\n" + "=" * 70)
    print("2. PER_PAPER COVERAGE (population-weighted)")
    print("=" * 70)

    paper_numbers = load(CANONICAL_DIR / "paper_numbers.json")
    per_paper = load(CANONICAL_DIR / "per_paper.json")

    years_with_pp = sorted(set(
        r.get("report_year") for r in per_paper if r.get("mean") is not None
    ))

    print(f"\n  {'Year':<6} {'Papers':>7} {'Covered':>8} {'Paper%':>7} "
          f"{'Pop(PN)':>8} {'Pop(Cov)':>9} {'Pop%':>6}")
    print("  " + "-" * 60)

    total_pn_pop = 0
    total_covered_pop = 0
    total_pn_papers = 0
    total_covered_papers = 0
    ok = True

    for year in years_with_pp:
        pn_papers = {r['paper']: r['n']
                     for r in paper_numbers if r.get('data_year') == year}
        pp_papers = set(r['paper'] for r in per_paper
                        if r.get('report_year') == year and r.get('mean') is not None)
        covered = pp_papers & set(pn_papers.keys())

        pn_total_pop = sum(pn_papers.values())
        covered_pop = sum(pn_papers.get(p, 0) for p in covered)

        paper_pct = len(covered) / len(pn_papers) * 100 if pn_papers else 0
        pop_pct = covered_pop / pn_total_pop * 100 if pn_total_pop else 0

        total_pn_pop += pn_total_pop
        total_covered_pop += covered_pop
        total_pn_papers += len(pn_papers)
        total_covered_papers += len(covered)

        flag = " !" if pop_pct < 95 else ""
        print(f"  {year:<6} {len(pn_papers):>7} {len(covered):>8} {paper_pct:>6.1f}% "
              f"{pn_total_pop:>8} {covered_pop:>9} {pop_pct:>5.1f}%{flag}")

        if pop_pct < 90:
            ok = False

    print("  " + "-" * 60)
    overall_paper_pct = total_covered_papers / total_pn_papers * 100
    overall_pop_pct = total_covered_pop / total_pn_pop * 100
    print(f"  {'ALL':<6} {total_pn_papers:>7} {total_covered_papers:>8} "
          f"{overall_paper_pct:>6.1f}% {total_pn_pop:>8} {total_covered_pop:>9} "
          f"{overall_pop_pct:>5.1f}%")

    status = "PASS" if overall_pop_pct >= 99 else "WARN" if overall_pop_pct >= 95 else "FAIL"
    print(f"\n  {status}: population-weighted coverage = {overall_pop_pct:.1f}%")
    return ok


def check_dedup_integrity():
    """Confirm no duplicate (year, paper, gender) groups in canonical per_paper."""
    print("\n" + "=" * 70)
    print("3. DEDUP INTEGRITY")
    print("=" * 70)

    per_paper = load(CANONICAL_DIR / "per_paper.json")

    groups = defaultdict(list)
    for r in per_paper:
        key = (r.get("report_year"), r.get("paper"), r.get("gender", "All"))
        groups[key].append(r)

    dupes = {k: v for k, v in groups.items() if len(v) > 1}
    if dupes:
        print(f"  FAIL: {len(dupes)} duplicate groups remain!")
        for k, recs in sorted(dupes.items())[:5]:
            print(f"    {k}: {len(recs)} records (n={[r.get('n') for r in recs]})")
        return False
    else:
        print(f"  PASS: {len(groups)} unique (year, paper, gender) groups, zero duplicates")
        return True


def check_fit_reliability():
    """Flag papers with unreliable MLE fits."""
    print("\n" + "=" * 70)
    print("4. FIT RELIABILITY")
    print("=" * 70)

    fits_path = ANALYSIS_DIR / "paper_fits.json"
    if not fits_path.exists():
        print("  SKIP: paper_fits.json not found (run analysis.py first)")
        return True

    fits = load(fits_path)
    reliable = [n for n, f in fits.items() if f.get("reliable")]
    unreliable = [(n, f) for n, f in fits.items() if not f.get("reliable")]

    print(f"  {len(reliable)} reliable / {len(fits)} total papers")

    if unreliable:
        small_n = [(n, f) for n, f in unreliable if f["n_total"] < 30]
        low_sigma = [(n, f) for n, f in unreliable
                     if f["sigma"] < 2.0 and f["n_total"] >= 30]
        both = [(n, f) for n, f in unreliable
                if f["n_total"] < 30 and f["sigma"] < 2.0]

        print(f"  Unreliable: {len(small_n)} small-n (<30), "
              f"{len(low_sigma)} low-σ (<2.0 with adequate n), "
              f"{len(both)} both")

        if low_sigma:
            print("\n  Low-σ papers (possible degenerate MLE — review manually):")
            for name, f in sorted(low_sigma, key=lambda x: x[1]["sigma"]):
                print(f"    σ={f['sigma']:<5.2f}  n={f['n_total']:>3}  {name}")

    print("\n  PASS" if not unreliable else f"\n  INFO: {len(unreliable)} flagged")
    return True


def check_data_sanity():
    """Basic sanity checks on canonical data."""
    print("\n" + "=" * 70)
    print("5. DATA SANITY")
    print("=" * 70)

    per_paper = load(CANONICAL_DIR / "per_paper.json")
    issues = []

    for r in per_paper:
        mean = r.get("mean")
        if mean is not None:
            if mean < 30 or mean > 90:
                issues.append(f"Implausible mean={mean} for {r.get('paper')} "
                              f"({r.get('report_year')})")
        sd = r.get("sd")
        if sd is not None and sd > 25:
            issues.append(f"Very high SD={sd} for {r.get('paper')} "
                          f"({r.get('report_year')})")
        n = r.get("n")
        if n is not None and n > 300:
            issues.append(f"Implausibly large n={n} for {r.get('paper')} "
                          f"({r.get('report_year')})")

    if issues:
        print(f"  WARN: {len(issues)} potential issues:")
        for issue in issues[:10]:
            print(f"    {issue}")
        if len(issues) > 10:
            print(f"    ... and {len(issues) - 10} more")
        return False
    else:
        print(f"  PASS: {len(per_paper)} records, all within plausible ranges")
        return True


def main():
    quick = "--quick" in sys.argv

    results = []
    results.append(("Alias completeness", check_alias_completeness()))
    results.append(("Coverage", check_coverage()))
    results.append(("Dedup integrity", check_dedup_integrity()))
    if not quick:
        results.append(("Fit reliability", check_fit_reliability()))
        results.append(("Data sanity", check_data_sanity()))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_ok = True
    for name, ok in results:
        status = "✓" if ok else "✗"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print("\n  All checks passed.")
    else:
        print("\n  Some checks failed — review output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
