#!/usr/bin/env python3
"""
Build canonical deduplicated dataset from LLM-extracted raw data.

Loads per-year JSON files from data/raw/, deduplicates overlapping
observations (preferring the latest report's value), normalises paper
names, and writes to data/canonical/.

Usage:
    python build_canonical.py
"""

import json
import re
from pathlib import Path

RAW_DIR = Path("data/raw")
CANONICAL_DIR = Path("data/canonical")
ALIASES_PATH = Path("data/paper_aliases.json")

LLM_SECTIONS = [
    "class_distribution", "subject_aggregates",
    "gender_class", "gender_stats", "per_paper",
    "route_class", "ethnicity_class", "paper_numbers",
]


def load_alias_map():
    if ALIASES_PATH.exists():
        data = json.loads(ALIASES_PATH.read_text())
        return data.get("alias_map", {})
    return {}


def normalise_paper(name, alias_map):
    return alias_map.get(name, name)


COMPONENT_PATTERN = re.compile(
    r"\((Essay|Exam|Coursework|Combined|old regs|old syllabus)\)",
    re.IGNORECASE,
)
ASSESSMENT_CODE_PATTERN = re.compile(r"\(A\d+[A-Z]*\d*\)")


def is_component_record(raw_name):
    """True if this is a component/sub-assessment rather than the aggregate."""
    if COMPONENT_PATTERN.search(raw_name):
        return "Combined" not in raw_name
    if ASSESSMENT_CODE_PATTERN.search(raw_name):
        return True
    return False


def is_old_regs(raw_name):
    return bool(re.search(r"\bold (regs|syllabus)\b", raw_name, re.IGNORECASE))


def deduplicate_per_paper(records):
    """Deduplicate per_paper records using priority rules.

    For each (report_year, paper, gender) group:
    1. Discard component records (Essay/Exam/Coursework/assessment codes)
       unless the only records are components (keep Combined if present)
    2. Discard old regs/syllabus records
    3. Among remaining: prefer records with bands data, then highest n
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for r in records:
        key = (r.get("report_year"), r.get("paper"), r.get("gender", "All"))
        groups[key].append(r)

    result = []
    for key, recs in groups.items():
        if len(recs) == 1:
            r = recs[0]
            r.pop("_raw_name", None)
            result.append(r)
            continue

        # Separate components from aggregates
        aggregates = []
        combined = []
        for r in recs:
            raw = r.get("_raw_name", "")
            if "Combined" in raw:
                combined.append(r)
            elif not is_component_record(raw):
                aggregates.append(r)

        # Prefer aggregates; if none, use Combined; if none, keep all
        candidates = aggregates or combined or recs

        # Remove old regs
        non_old = [r for r in candidates if not is_old_regs(r.get("_raw_name", ""))]
        if non_old:
            candidates = non_old

        # Among remaining: prefer records with bands, then highest n
        def score(r):
            has_bands = 1 if r.get("bands") and any(v for v in r["bands"].values() if v) else 0
            return (has_bands, r.get("n") or 0)

        candidates.sort(key=score, reverse=True)
        winner = candidates[0]
        winner.pop("_raw_name", None)
        result.append(winner)

    return result


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

    print("Loading LLM-extracted data...")
    llm_data = load_llm_data()

    print("Loading paper aliases...")
    alias_map = load_alias_map()

    # Normalise paper names (preserve raw name for per_paper dedup)
    for r in llm_data["per_paper"]:
        if "paper" in r:
            r["_raw_name"] = r["paper"]
            r["paper"] = normalise_paper(r["paper"], alias_map)
    for r in llm_data["paper_numbers"]:
        if "paper" in r:
            r["paper"] = normalise_paper(r["paper"], alias_map)

    # 1. Class distribution — dedup by (data_year, class)
    canon = deduplicate(
        llm_data["class_distribution"],
        lambda r: (r["data_year"], r["class"]),
    )
    for r in canon:
        r.pop("report_year", None)
    save("class_distribution", canon)

    # 2. Subject aggregates — dedup by (data_year, subject)
    canon = deduplicate(
        llm_data["subject_aggregates"],
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

    # 5. Per-paper stats — dedup components, old regs, route splits
    canon = deduplicate_per_paper(llm_data["per_paper"])
    save("per_paper", canon)

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
