#!/usr/bin/env python3
"""
LLM-based extraction of structured data from Oxford PPE FHS Examiners' Reports.

Uses Claude via Bedrock to extract data directly from PDFs, replacing
hand-crafted regex parsing for complex/varied table formats.

Usage:
    python llm_extract.py                          # extract all
    python llm_extract.py --year 2024              # single year
    python llm_extract.py --section gender_class    # single section type
    python llm_extract.py --dry-run                # print, don't write
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path

import anthropic
import json_repair

REPORTS_DIR = Path("reports")
RAW_DIR = Path("data/raw")
MODEL = "us.anthropic.claude-sonnet-4-6"


def get_client():
    return anthropic.AnthropicBedrock(aws_region="us-east-1")


def get_reports() -> list[tuple[int, Path]]:
    import re
    reports = []
    for f in sorted(REPORTS_DIR.iterdir()):
        if f.suffix.lower() == ".pdf":
            m = re.search(r"(20\d{2})", f.name)
            if m:
                reports.append((int(m.group(1)), f))
    return sorted(reports)


def load_pdf_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def call_llm(client, pdf_b64: str, prompt: str, max_tokens: int = 16000) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return resp.content[0].text


# ---------------------------------------------------------------------------
# Extraction prompts — each returns a JSON-producing prompt
# ---------------------------------------------------------------------------

GENDER_CLASS_PROMPT = """\
Extract the class distribution by gender table(s) from this PPE examiners' report.

This data shows the percentage (and sometimes count) of male and female candidates
achieving each degree classification (1st, 2.1, 2.2, 3rd, Pass, etc.) for each year shown.

Return a JSON array of objects. Each object represents ONE cell in the table:
{
  "report_year": <int, the year this report is for>,
  "data_year": <int, the year the data row is about>,
  "gender": "M" or "F",
  "class": <string, one of: "1st", "2.1", "2.2", "3rd", "Pass", "DDH", "Unclassified", "Fail", "Incomplete">,
  "value": <number>,
  "value_type": "pct" or "count"
}

Rules:
- Normalise class labels: I/First = "1st", II 1/II.1 = "2.1", II 2/II.2 = "2.2", III = "3rd", etc.
- Include ALL years shown in the table, not just the report's own year.
- If a cell is 0, include it. If a cell is missing/empty, omit it.
- If the table gives percentages, use value_type "pct". If it gives counts, use "count".
  If both are given for the same cell, emit two records (one pct, one count).
- For 2024-2025 reports, the format is a nested indented list by academic year.
  Convert academic years like "2023/24" to the calendar year of the exam (2024).

Return ONLY the JSON array, no other text."""

GENDER_STATS_PROMPT = """\
Extract the overall gender statistics from this PPE examiners' report.

Look for tables or text giving the total number of candidates, average mark,
and standard deviation BY GENDER (Male/Female) for each year shown.

This is typically in a section called "Total candidates, average mark and standard
deviation by gender" or similar. In early reports (2011-2014) it may be in prose.

Return a JSON array of objects:
{
  "report_year": <int>,
  "data_year": <int>,
  "gender": "M" or "F",
  "n": <int, number of candidates, or null if not given>,
  "mean": <float, average mark>,
  "sd": <float, standard deviation>
}

Rules:
- Include ALL years shown, not just the report's own year.
- If a value is not given, use null.
- For 2024-2025, academic years like "2023/24" → data_year 2024.

Return ONLY the JSON array, no other text."""

PER_PAPER_PROMPT = """\
Extract ALL per-paper statistics from this PPE examiners' report.

Look for sections with tables showing statistics for individual papers/assessments.
The format varies by year:
- 2015-2016: Paper name, Average, SD, Highest, Lowest (grouped by Philosophy/Politics/Economics)
- 2017-2018: Code, Candidates, >=70, >=60, >=50, >=40, >=30, <30, Q1, Median, Q3, Mean, St.Dev
- 2019-2022: Paper name, Cands, >=70, >=60, >=50, >=40, >=30, <30, Q1, Median, Q3, Mean, St.Dev, Max, Min
- 2023: No data (boycott year) — return empty array
- 2024-2025: Per-paper broken down by gender (Paper, Code, Gender, N, Mean, SD, Max, Min)
  PLUS a bands-of-marks table by gender (>=70, 60-69, 50-59, 40-49, 30-39, <30)

Return a JSON array of objects. Each object is one row:
{
  "report_year": <int>,
  "paper": <string, full paper name>,
  "subject": <string, "Philosophy", "Politics", "Economics", or "Joint" if identifiable, else null>,
  "gender": <string, "M", "F", or "All" if not broken down by gender>,
  "n": <int or null>,
  "mean": <float or null>,
  "sd": <float or null>,
  "max": <int or null>,
  "min": <int or null>,
  "q1": <float or null>,
  "median": <float or null>,
  "q3": <float or null>,
  "bands": {
    ">=70": <int or null>,
    "60-69": <int or null>,
    "50-59": <int or null>,
    "40-49": <int or null>,
    "30-39": <int or null>,
    "<30": <int or null>
  } or null if no band data
}

Rules:
- Include EVERY paper listed. Do not skip any.
- Where candidates <=5 and stats are suppressed, include the row with null values.
- If band data is given as percentages, still include them but note in the values.
  Actually, convert percentage bands to counts if total n is known; otherwise give the raw number.
- Papers with <=2 candidates may be entirely suppressed — that's fine, skip those.
- For 2024-2025: emit separate rows for gender="F", gender="M", and gender="All" (the paper total line).
- Preserve the exact paper name as given in the report.

Return ONLY the JSON array, no other text."""

ROUTE_CLASS_PROMPT = """\
Extract the class distribution by route/combination through PPE from this report.

This shows how many students in each route (Phil-Econ, Pol-Econ, Phil-Pol, PPE/Tripartite)
achieved each classification. In 2011 this is given as percentages. In 2019-2025 it's
given as counts and percentages.

If this data is not present in the report, return an empty array [].

Return a JSON array of objects:
{
  "report_year": <int>,
  "data_year": <int>,
  "route": <string, one of "Phil-Econ", "Pol-Econ", "Phil-Pol", "PPE">,
  "class": <string, "1st", "2.1", "2.2", "3rd", etc.>,
  "count": <int or null>,
  "pct": <float or null>
}

Rules:
- Include ALL years shown in the table.
- Normalise route names: "Phil/Pol" → "Phil-Pol", "Tripartite" or "PPE" → "PPE", etc.
- For 2024-2025, academic years like "2023/24" → data_year 2024.

Return ONLY the JSON array, no other text."""

ETHNICITY_CLASS_PROMPT = """\
Extract the class distribution by ethnicity from this PPE examiners' report.

This data appears from 2017 onwards and shows degree classifications broken down
by ethnicity categories (typically BME, White, Unknown/Not known/Prefer not to say).
Note: these use cohort entry years, not exam years.

If this data is not present in the report, return an empty array [].

Return a JSON array of objects:
{
  "report_year": <int>,
  "cohort_year": <string, the academic year label as given, e.g. "2015/16" or "2014/15">,
  "ethnicity": <string, e.g. "BME", "White", "Unknown">,
  "class": <string, "1st", "2.1", "2.2", "3rd", etc.>,
  "count": <int or null>,
  "pct": <float or null>
}

Rules:
- Include ALL cohort years shown.
- Normalise ethnicity: "Not known" / "Prefer not to say" → "Unknown".
- Normalise class labels as usual.
- Some cells may be suppressed for small n — omit those.

Return ONLY the JSON array, no other text."""

PAPER_NUMBERS_PROMPT = """\
Extract the "Numbers offering each paper/assessment" table from this report.

This table shows how many candidates took each paper in each year (typically
the last 5 years). It appears in all reports.

Return a JSON array of objects:
{
  "report_year": <int>,
  "data_year": <int>,
  "paper": <string, exact paper name as given>,
  "n": <int, number of candidates>
}

Rules:
- Include ALL years shown in the table columns.
- Include ALL papers listed.
- If a cell is empty, "-", or ".", omit that record.
- For 2024-2025, academic year "2023/24" → data_year 2024.
- Preserve exact paper names.

Return ONLY the JSON array, no other text."""


CLASS_DISTRIBUTION_PROMPT = """\
Extract the overall class distribution table from this PPE examiners' report.

This table shows the number and percentage of candidates achieving each degree
classification (1st, 2.1, 2.2, 3rd, Pass, Fail, etc.) for each year shown.
It typically appears in Part A and often includes several years of historical data.

Format varies:
- 2011–2018: Horizontal table with year columns and class rows
- 2019–2023: Vertical table with year headers and class sub-rows
- 2024–2025: Vertical list with academic year headers (e.g. "2023/24")

Return a JSON array of objects. Each object represents ONE cell:
{
  "report_year": <int, the year this report is for>,
  "data_year": <int, the year the data is about>,
  "class": <string, one of: "1st", "2.1", "2.2", "3rd", "Pass", "DDH", "Unclassified", "Fail", "Incomplete">,
  "count": <int>,
  "pct": <float, percentage>
}

Rules:
- Normalise class labels: I/First/First Class = "1st", II 1/II.1/Upper Second = "2.1",
  II 2/II.2/Lower Second = "2.2", III/Third = "3rd", Honours Pass = "Pass",
  Declared to have Deserved Honours = "DDH".
- Include ALL years shown in the table, not just the report's own year.
- For 2024–2025 reports, academic years like "2023/24" → data_year 2024.
- If count and percentage are both given, include both. If only one, include what's available (use null for the other).
- Do NOT include "Total" rows.

Return ONLY the JSON array, no other text."""


SECTIONS = {
    "class_distribution": ("Overall class distribution", CLASS_DISTRIBUTION_PROMPT),
    "gender_class": ("Class distribution by gender", GENDER_CLASS_PROMPT),
    "gender_stats": ("Gender statistics (n, mean, SD)", GENDER_STATS_PROMPT),
    "per_paper": ("Per-paper statistics", PER_PAPER_PROMPT),
    "route_class": ("Class distribution by route", ROUTE_CLASS_PROMPT),
    "ethnicity_class": ("Class distribution by ethnicity", ETHNICITY_CLASS_PROMPT),
    "paper_numbers": ("Paper candidate numbers", PAPER_NUMBERS_PROMPT),
}


def extract_section(client, report_year: int, pdf_b64: str, section_key: str) -> list[dict]:
    label, prompt = SECTIONS[section_key]
    raw = call_llm(client, pdf_b64, prompt)

    # Parse the JSON from the response (strip markdown fences if present)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json_repair.loads(text)

    if not isinstance(data, list):
        print(f"  WARNING: Expected list for {section_key} in {report_year}, got {type(data)}", file=sys.stderr)
        return []

    return data


def run_extraction(years=None, sections=None, dry_run=False):
    client = get_client()
    reports = get_reports()

    if years:
        reports = [(y, p) for y, p in reports if y in years]

    section_keys = sections or list(SECTIONS.keys())

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for report_year, pdf_path in reports:
        print(f"\n{'='*60}")
        print(f"Report: {report_year} ({pdf_path.name})")
        print(f"{'='*60}")

        pdf_b64 = load_pdf_b64(pdf_path)

        for section_key in section_keys:
            label = SECTIONS[section_key][0]
            print(f"  Extracting: {label}...", end=" ", flush=True)

            t0 = time.time()
            data = extract_section(client, report_year, pdf_b64, section_key)
            elapsed = time.time() - t0

            print(f"{len(data)} records ({elapsed:.1f}s)")

            if dry_run:
                if data:
                    print(json.dumps(data[:3], indent=2))
                    if len(data) > 3:
                        print(f"  ... and {len(data) - 3} more")
            else:
                out_path = RAW_DIR / f"{report_year}_{section_key}.json"
                with open(out_path, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"    → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="LLM-based data extraction from PPE reports")
    parser.add_argument("--year", type=int, nargs="+", help="Extract specific year(s)")
    parser.add_argument("--section", nargs="+", choices=list(SECTIONS.keys()),
                        help="Extract specific section(s)")
    parser.add_argument("--dry-run", action="store_true", help="Print results, don't write files")
    args = parser.parse_args()

    run_extraction(years=args.year, sections=args.section, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
