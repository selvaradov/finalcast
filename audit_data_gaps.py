"""
Audit data completeness: compare paper_numbers (what papers exist each year)
against per_paper (what papers have extracted stats).

Run after any re-extraction to check progress:
    python audit_data_gaps.py

Also checks:
- Papers with only gendered stats (no All aggregate)
- Papers in per_paper but missing from paper_numbers (alias mismatches)
- Raw extraction coverage vs canonical
"""
import json
from collections import defaultdict, Counter
from pathlib import Path

CANONICAL_DIR = Path("data/canonical")
RAW_DIR = Path("data/raw")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def audit_coverage():
    """Compare paper_numbers vs per_paper for all years."""
    paper_numbers = load_json(CANONICAL_DIR / "paper_numbers.json")
    per_paper = load_json(CANONICAL_DIR / "per_paper.json")

    pn_by_year = defaultdict(dict)
    for r in paper_numbers:
        pn_by_year[r['data_year']][r['paper']] = r['n']

    pp_by_year = defaultdict(set)
    for r in per_paper:
        if r.get('mean') is not None:
            pp_by_year[r['report_year']].add(r['paper'])

    print("=" * 90)
    print("DATA COVERAGE AUDIT")
    print("=" * 90)
    print(f"\n{'Year':<6} {'In PN':<7} {'Has Stats':<10} {'Missing':<8} {'Miss%':<7} {'Large misses (n>=20)'}")
    print("-" * 90)

    for year in sorted(set(list(pp_by_year.keys()) + list(pn_by_year.keys()))):
        if year < 2015:
            continue
        pn_papers = pn_by_year.get(year, {})
        pp_papers = pp_by_year.get(year, set())
        missing = set(pn_papers.keys()) - pp_papers
        large_missing = [(pn_papers[p], p) for p in missing if pn_papers[p] >= 20]
        large_missing.sort(reverse=True)
        miss_rate = f"{len(missing)/len(pn_papers)*100:.0f}%" if pn_papers else "N/A"
        large_str = f"{len(large_missing)} papers" if large_missing else "none"
        print(f"{year:<6} {len(pn_papers):<7} {len(pp_papers):<10} {len(missing):<8} {miss_rate:<7} {large_str}")

    return pn_by_year, pp_by_year


def audit_detailed_gaps(pn_by_year, pp_by_year):
    """Show detailed gaps for years with >10 missing papers."""
    print("\n\n" + "=" * 90)
    print("DETAILED GAPS (years with >10 missing papers)")
    print("=" * 90)

    for year in sorted(pp_by_year.keys()):
        pn_papers = pn_by_year.get(year, {})
        pp_papers = pp_by_year.get(year, set())
        missing = set(pn_papers.keys()) - pp_papers

        if len(missing) <= 10:
            continue

        print(f"\n--- {year}: {len(missing)} papers missing stats ---")
        missing_sorted = sorted([(pn_papers[p], p) for p in missing], reverse=True)
        for n, p in missing_sorted:
            print(f"  n={n:>4}  {p}")


def audit_gendered_records():
    """Check papers with gendered stats but no All aggregate."""
    per_paper = load_json(CANONICAL_DIR / "per_paper.json")

    print("\n\n" + "=" * 90)
    print("GENDERED RECORDS WITHOUT 'ALL' AGGREGATE")
    print("=" * 90)

    for year in [2024, 2025]:
        gendered = defaultdict(list)
        all_papers = set()
        for r in per_paper:
            if r.get('report_year') != year or r.get('mean') is None:
                continue
            if r.get('gender') == 'All':
                all_papers.add(r['paper'])
            else:
                gendered[r['paper']].append(r)

        only_gendered = set(gendered.keys()) - all_papers
        print(f"\n  {year}: {len(only_gendered)} papers with ONLY gendered stats")
        for p in sorted(only_gendered):
            records = gendered[p]
            means = {r['gender']: r['mean'] for r in records}
            ns = {r['gender']: r.get('n') for r in records}
            print(f"    {p}: means={means}, ns={ns}")


def audit_alias_mismatches(pn_by_year, pp_by_year):
    """Papers in per_paper but NOT in paper_numbers (potential alias issues)."""
    print("\n\n" + "=" * 90)
    print("ALIAS MISMATCHES (in per_paper but not in paper_numbers)")
    print("=" * 90)

    for year in sorted(pp_by_year.keys()):
        pn_papers = set(pn_by_year.get(year, {}).keys())
        pp_papers = pp_by_year.get(year, set())
        extra = pp_papers - pn_papers
        if extra:
            print(f"\n  {year} ({len(extra)} extra):")
            for p in sorted(extra):
                print(f"    {p}")


def audit_raw_extraction():
    """Check raw extraction coverage for 2024/2025."""
    print("\n\n" + "=" * 90)
    print("RAW EXTRACTION ANALYSIS (2024/2025)")
    print("=" * 90)

    paper_numbers = load_json(CANONICAL_DIR / "paper_numbers.json")

    for year in [2024, 2025]:
        raw_path = RAW_DIR / f"{year}_per_paper.json"
        if not raw_path.exists():
            print(f"\n  {year}: no raw file")
            continue

        raw = load_json(raw_path)
        pn_papers = {r['paper']: r['n'] for r in paper_numbers if r.get('data_year') == year}

        # Group raw by paper
        raw_by_paper = defaultdict(list)
        for r in raw:
            raw_by_paper[r['paper']].append(r)

        raw_papers_with_mean = {p for p, rs in raw_by_paper.items()
                                if any(r.get('mean') is not None for r in rs)}

        captured = raw_papers_with_mean & set(pn_papers.keys())
        missed = set(pn_papers.keys()) - raw_papers_with_mean

        # Subject breakdown
        per_paper = load_json(CANONICAL_DIR / "per_paper.json")
        paper_subjects = {}
        for r in per_paper:
            if r.get('subject'):
                paper_subjects[r['paper']] = r['subject']

        captured_subj = Counter(paper_subjects.get(p, '?') for p in captured)
        missed_subj = Counter(paper_subjects.get(p, '?') for p in missed)

        print(f"\n  {year}: {len(raw)} raw records, {len(raw_by_paper)} unique papers")
        print(f"    Papers in paper_numbers: {len(pn_papers)}")
        print(f"    Papers with stats in raw: {len(raw_papers_with_mean)}")
        print(f"    Coverage: {len(captured)}/{len(pn_papers)} ({len(captured)/len(pn_papers)*100:.0f}%)")
        print(f"    Captured subjects: {dict(captured_subj)}")
        print(f"    Missed subjects:   {dict(missed_subj)}")
        print(f"    => LLM likely only extracted ONE section/table of per-paper stats")


def audit_web_bundle():
    """Compare web_bundle.json (from analysis.py) vs web/data.json."""
    print("\n\n" + "=" * 90)
    print("WEB DATA PIPELINE AUDIT")
    print("=" * 90)

    bundle_path = Path("data/analysis/web_bundle.json")
    data_path = Path("web/data.json")

    if not bundle_path.exists() or not data_path.exists():
        print("  Missing files, skipping")
        return

    bundle = load_json(bundle_path)
    data = load_json(data_path)

    extra_in_data = set(data.keys()) - set(bundle.keys())
    missing_from_data = set(bundle.keys()) - set(data.keys())

    print(f"\n  Keys in web_bundle.json (produced by analysis.py): {len(bundle)}")
    print(f"  Keys in web/data.json (used by the site): {len(data)}")
    print(f"\n  Keys manually added to data.json ({len(extra_in_data)}):")
    for k in sorted(extra_in_data):
        v = data[k]
        size = f"{len(v)} entries" if isinstance(v, (dict, list)) else repr(v)
        print(f"    {k}: {size}")
    if missing_from_data:
        print(f"\n  Keys in bundle but NOT in data.json ({len(missing_from_data)}):")
        for k in sorted(missing_from_data):
            print(f"    {k}")


if __name__ == "__main__":
    pn, pp = audit_coverage()
    audit_detailed_gaps(pn, pp)
    audit_gendered_records()
    audit_alias_mismatches(pn, pp)
    audit_raw_extraction()
    audit_web_bundle()
