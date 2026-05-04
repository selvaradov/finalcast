#!/usr/bin/env python3
"""
Build canonical deduplicated dataset from raw extracted data.

Merges regex-extracted (class_distribution, subject_aggregates) and
LLM-extracted data. Where overlapping reports disagree, prefers the
latest report's value (most likely to be corrected).

Usage:
    python build_canonical.py
"""

import json
from pathlib import Path

from extract import ClassDistributionParser, SubjectAggregatesParser, get_reports, extract_text

RAW_DIR = Path("data/raw")
CANONICAL_DIR = Path("data/canonical")
ALIASES_PATH = Path("data/paper_aliases.json")


def load_alias_map():
    if ALIASES_PATH.exists():
        data = json.loads(ALIASES_PATH.read_text())
        return data.get("alias_map", {})
    return {}


def normalise_paper(name, alias_map):
    return alias_map.get(name, name)

LLM_SECTIONS = [
    "gender_class", "gender_stats", "per_paper",
    "route_class", "ethnicity_class", "paper_numbers",
]


def build_regex_data():
    """Run the regex parsers and return their results keyed by section."""
    results = {"class_distribution": [], "subject_aggregates": []}
    parsers = [
        ("class_distribution", ClassDistributionParser()),
        ("subject_aggregates", SubjectAggregatesParser()),
    ]
    for report_year, pdf_path in get_reports():
        text = extract_text(pdf_path)
        for section_key, parser in parsers:
            records = parser.extract(report_year, text)
            results[section_key].extend(records)
    return results


def load_llm_data():
    """Load all LLM-extracted raw JSON files."""
    results = {s: [] for s in LLM_SECTIONS}
    for section in LLM_SECTIONS:
        for f in sorted(RAW_DIR.glob(f"*_{section}.json")):
            data = json.loads(f.read_text())
            results[section].extend(data)
    return results


def deduplicate(records, key_fn):
    """Deduplicate records, preferring the highest report_year."""
    by_key = {}
    for r in records:
        k = key_fn(r)
        existing = by_key.get(k)
        if existing is None or r.get("report_year", 0) > existing.get("report_year", 0):
            by_key[k] = r
    return list(by_key.values())


def build():
    CANONICAL_DIR.mkdir(parents=True, exist_ok=True)

    print("Running regex parsers...")
    regex_data = build_regex_data()

    print("Loading LLM-extracted data...")
    llm_data = load_llm_data()

    print("Loading paper aliases...")
    alias_map = load_alias_map()

    # Normalise paper names in LLM data
    for section in ["per_paper", "paper_numbers"]:
        for r in llm_data[section]:
            if "paper" in r:
                r["paper"] = normalise_paper(r["paper"], alias_map)

    # 1. Class distribution (regex) — dedup by (data_year, class)
    canon = deduplicate(
        regex_data["class_distribution"],
        lambda r: (r["data_year"], r["class"]),
    )
    # Drop report_year from canonical records
    for r in canon:
        r.pop("report_year", None)
    save("class_distribution", canon)

    # 2. Subject aggregates (regex) — dedup by (data_year, subject)
    canon = deduplicate(
        regex_data["subject_aggregates"],
        lambda r: (r["data_year"], r["subject"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("subject_aggregates", canon)

    # 3. Gender class distribution — dedup by (data_year, gender, class, value_type)
    canon = deduplicate(
        llm_data["gender_class"],
        lambda r: (r["data_year"], r["gender"], r["class"], r["value_type"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("gender_class", canon)

    # 4. Gender stats — dedup by (data_year, gender)
    canon = deduplicate(
        llm_data["gender_stats"],
        lambda r: (r["data_year"], r["gender"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("gender_stats", canon)

    # 5. Per-paper stats — no dedup needed (single report per year)
    save("per_paper", llm_data["per_paper"])

    # 6. Route class distribution — dedup by (data_year, route, class)
    canon = deduplicate(
        llm_data["route_class"],
        lambda r: (r["data_year"], r["route"], r["class"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("route_class", canon)

    # 7. Ethnicity class distribution — dedup by (cohort_year, ethnicity, class)
    canon = deduplicate(
        llm_data["ethnicity_class"],
        lambda r: (r.get("cohort_year"), r.get("ethnicity"), r.get("class")),
    )
    for r in canon:
        r.pop("report_year", None)
    save("ethnicity_class", canon)

    # 8. Paper numbers — dedup by (data_year, paper), filter malformed
    valid_pn = [r for r in llm_data["paper_numbers"]
                if "paper" in r and "data_year" in r and "n" in r]
    canon = deduplicate(
        valid_pn,
        lambda r: (r["data_year"], r["paper"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("paper_numbers", canon)

    print("\nDone! Canonical data in", CANONICAL_DIR)


def save(name, data):
    path = CANONICAL_DIR / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  {name}: {len(data)} records → {path}")


if __name__ == "__main__":
    build()
