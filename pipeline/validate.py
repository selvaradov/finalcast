#!/usr/bin/env python3
"""Quick validation of LLM-extracted data against regex-extracted and known values."""

import json
from pathlib import Path

RAW_DIR = Path("data/raw")

def check_gender_stats():
    """Cross-check gender stats across overlapping reports."""
    print("=== Gender Stats: Cross-report consistency ===")
    # Collect all observations for each (data_year, gender) tuple
    observations = {}
    for f in sorted(RAW_DIR.glob("*_gender_stats.json")):
        report_year = int(f.name[:4])
        data = json.loads(f.read_text())
        for r in data:
            key = (r["data_year"], r["gender"])
            observations.setdefault(key, []).append({
                "report_year": report_year,
                "mean": r.get("mean"),
                "sd": r.get("sd"),
                "n": r.get("n"),
            })

    discrepancies = 0
    for (dy, g), obs in sorted(observations.items()):
        if len(obs) < 2:
            continue
        means = [o["mean"] for o in obs if o["mean"] is not None]
        if means and (max(means) - min(means) > 0.05):
            discrepancies += 1
            print(f"  MISMATCH data_year={dy} gender={g}: means={means}")
            for o in obs:
                print(f"    report_year={o['report_year']}: mean={o['mean']}, sd={o['sd']}, n={o['n']}")

    if discrepancies == 0:
        print("  All overlapping observations consistent!")
    else:
        print(f"  {discrepancies} discrepancies found")
    print()


def check_route_class():
    """Check route class data coverage."""
    print("=== Route Class: Coverage ===")
    for f in sorted(RAW_DIR.glob("*_route_class.json")):
        report_year = int(f.name[:4])
        data = json.loads(f.read_text())
        if data:
            years = sorted(set(r["data_year"] for r in data))
            routes = sorted(set(r["route"] for r in data))
            print(f"  {report_year}: {len(data)} records, years={years}, routes={routes}")
        else:
            print(f"  {report_year}: empty")
    print()


def check_ethnicity():
    """Check ethnicity data coverage."""
    print("=== Ethnicity Class: Coverage ===")
    for f in sorted(RAW_DIR.glob("*_ethnicity_class.json")):
        report_year = int(f.name[:4])
        data = json.loads(f.read_text())
        if data:
            cohorts = sorted(set(r.get("cohort_year", "?") for r in data))
            ethnicities = sorted(set(r.get("ethnicity", "?") for r in data))
            print(f"  {report_year}: {len(data)} records, cohorts={cohorts}, ethnicities={ethnicities}")
        else:
            print(f"  {report_year}: empty")
    print()


def check_per_paper():
    """Check per-paper data coverage."""
    print("=== Per-Paper Stats: Coverage ===")
    for f in sorted(RAW_DIR.glob("*_per_paper.json")):
        report_year = int(f.name[:4])
        data = json.loads(f.read_text())
        if data:
            subjects = sorted(set(r.get("subject", "null") for r in data))
            genders = sorted(set(r.get("gender", "?") for r in data))
            has_bands = sum(1 for r in data if r.get("bands"))
            print(f"  {report_year}: {len(data)} records, subjects={subjects}, genders={genders}, with_bands={has_bands}")
        else:
            print(f"  {report_year}: empty (expected for 2011-2014, 2023)")
    print()


def check_gender_class_cross_validation():
    """Cross-validate gender class distributions across overlapping reports."""
    print("=== Gender Class: Cross-report consistency ===")
    observations = {}
    for f in sorted(RAW_DIR.glob("*_gender_class.json")):
        report_year = int(f.name[:4])
        data = json.loads(f.read_text())
        for r in data:
            key = (r["data_year"], r["gender"], r["class"], r["value_type"])
            observations.setdefault(key, []).append({
                "report_year": report_year,
                "value": r["value"],
            })

    discrepancies = 0
    for key, obs in sorted(observations.items()):
        if len(obs) < 2:
            continue
        vals = [o["value"] for o in obs if o["value"] is not None]
        if vals and (max(vals) - min(vals) > 0.2):
            discrepancies += 1
            if discrepancies <= 10:
                print(f"  MISMATCH {key}: values={[o['value'] for o in obs]} from reports={[o['report_year'] for o in obs]}")

    total_overlap = sum(1 for obs in observations.values() if len(obs) >= 2)
    print(f"  {total_overlap} overlapping observations, {discrepancies} discrepancies")
    print()


if __name__ == "__main__":
    check_gender_stats()
    check_route_class()
    check_ethnicity()
    check_per_paper()
    check_gender_class_cross_validation()
