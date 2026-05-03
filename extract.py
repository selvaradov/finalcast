#!/usr/bin/env python3
"""
Extract structured data from Oxford PPE FHS Examiners' Reports (2011-2025).

Usage:
    python extract.py                  # extract all, write to data/
    python extract.py --year 2025      # extract single year
    python extract.py --dry-run        # print extracted data, don't write files
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPORTS_DIR = Path("reports")
RAW_DIR = Path("data/raw")
CANONICAL_DIR = Path("data/canonical")

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_text(pdf_path: Path) -> str:
    """Run pdftotext -layout and return the full text."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed on {pdf_path}: {result.stderr}")
    return result.stdout


def detect_year(filename: str) -> int:
    """Extract the report year from the filename."""
    m = re.search(r"(20\d{2})", filename)
    if not m:
        raise ValueError(f"Cannot detect year from filename: {filename}")
    return int(m.group(1))


def get_reports() -> list[tuple[int, Path]]:
    """Return sorted list of (year, path) for all report PDFs."""
    reports = []
    for f in sorted(REPORTS_DIR.iterdir()):
        if f.suffix.lower() == ".pdf":
            year = detect_year(f.name)
            reports.append((year, f))
    return sorted(reports)

# ---------------------------------------------------------------------------
# Parser base
# ---------------------------------------------------------------------------

class Parser:
    """Base class for parsers. Subclasses implement extract()."""
    name: str = "base"

    def extract(self, report_year: int, text: str) -> list[dict]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Parser 1: Overall class distribution
# ---------------------------------------------------------------------------

CLASS_LABELS = {
    "i": "1st",
    "1st": "1st",
    "first": "1st",
    "first class": "1st",
    "ii 1": "2.1",
    "ii.1": "2.1",
    "ii1": "2.1",
    "2.1": "2.1",
    "2:1": "2.1",
    "second class, division one": "2.1",
    "ii 2": "2.1",  # will be overridden below
    "ii.2": "2.2",
    "ii2": "2.2",
    "2.2": "2.2",
    "2:2": "2.2",
    "second class, division two": "2.2",
    "iii": "3rd",
    "3rd": "3rd",
    "third": "3rd",
    "third class": "3rd",
    "honours pass": "Pass",
    "pass": "Pass",
    "ddh": "DDH",
    "declared to have deserved honours": "DDH",
    "unclassified": "Unclassified",
    "fail": "Fail",
    "incomplete": "Incomplete",
    "incom.": "Incomplete",
}
# Fix the ii 2 entry
CLASS_LABELS["ii 2"] = "2.2"


def _norm_class(raw: str) -> str | None:
    """Normalise a class label string, return None if not recognised."""
    s = raw.strip().lower().rstrip(".")
    # Try exact match first
    if s in CLASS_LABELS:
        return CLASS_LABELS[s]
    # Try prefix matches for the longer labels
    for key, val in sorted(CLASS_LABELS.items(), key=lambda x: -len(x[0])):
        if s.startswith(key):
            return val
    return None


class ClassDistributionParser(Parser):
    name = "class_distribution"

    def extract(self, report_year: int, text: str) -> list[dict]:
        if report_year >= 2024:
            return self._parse_vertical_2024(report_year, text)
        else:
            return self._parse_horizontal(report_year, text)

    def _parse_vertical_2024(self, report_year: int, text: str) -> list[dict]:
        """2024-2025 format: vertical list with 'Year and Classification', 'Number of students', 'As a Percentage'."""
        results = []
        lines = text.split("\n")

        # Find the class distribution section — skip the table of contents
        # by requiring the line to be a standalone section header (not part of a TOC)
        start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if re.match(r"1\.\s+[Cc]lass distribution\s*$", stripped):
                start = i
                break
        if start is None:
            return results

        current_year = None
        for line in lines[start:start+120]:
            # Year line: "2023/24   250" or "2023/24   250   20.9%"
            m = re.match(r"\s*(20\d{2})/(\d{2})\s+(\d+)", line)
            if m:
                # This is a year header like "2024/25    233   19.5%"
                # The year is the exam year (second part): 2024/25 means exams in 2025
                current_year = 2000 + int(m.group(2))
                total_count = int(m.group(3))
                continue

            if current_year is None:
                continue

            # Check for "Grand Total" to stop
            if "grand total" in line.lower():
                break

            # A line with just "-" and a count (uncategorised/incomplete)
            # Must check before the general class regex since "-" also matches \D+
            m_dash = re.match(r"\s+-\s+(\d+)\s+([\d.]+%?)", line)
            if m_dash:
                results.append({
                    "report_year": report_year,
                    "data_year": current_year,
                    "class": "Other/Uncategorised",
                    "count": int(m_dash.group(1)),
                    "pct": float(m_dash.group(2).rstrip("%")),
                })
                continue

            # Class line: indented, with class name, count, percentage
            m = re.match(r"\s{2,}(\D+?)\s{2,}(\d+)\s+([\d.]+%)", line)
            if m:
                raw_class = m.group(1).strip()
                count = int(m.group(2))
                pct = float(m.group(3).rstrip("%"))
                norm = _norm_class(raw_class)
                if norm and norm not in ("Unclassified",):
                    results.append({
                        "report_year": report_year,
                        "data_year": current_year,
                        "class": norm,
                        "count": count,
                        "pct": pct,
                    })
                continue

        return results

    def _parse_horizontal(self, report_year: int, text: str) -> list[dict]:
        """2011-2018 format: horizontal table with year columns.

        Layout: class label at left, counts aligned under year columns, percentages on
        the next line (sometimes in parentheses). In 2011, pdftotext splits some rows
        so the counts and the label end up on separate lines — we handle this by merging
        consecutive lines before parsing.
        """
        results = []
        lines = text.split("\n")

        # Find the class distribution table
        start = None
        for i, line in enumerate(lines):
            if re.search(r"class distribution of FHS candidates", line, re.IGNORECASE):
                start = i
                break
            if re.search(r"1\.\s+class distribution", line, re.IGNORECASE):
                start = i
                break
        if start is None:
            return results

        # Find the header row with years
        year_positions = []  # (col_center, year)
        header_idx = None
        for i in range(start, min(start + 10, len(lines))):
            years_found = list(re.finditer(r"\b(20\d{2})\b", lines[i]))
            if len(years_found) >= 3:
                header_idx = i
                for m in years_found:
                    year_positions.append((m.start() + 2, int(m.group(1))))
                break

        if not year_positions:
            return results

        # Helper: extract integers at column positions from a line
        def extract_counts(line: str) -> dict[int, int]:
            vals = {}
            for col_center, yr in year_positions:
                ws = max(0, col_center - 8)
                we = min(len(line), col_center + 8)
                window = line[ws:we]
                if "%" in window:
                    continue
                # Match integer, possibly followed by space and "(pct)" — take just the int
                m = re.search(r"\b(\d{1,3})\b", window)
                if m:
                    vals[yr] = int(m.group(1))
            return vals

        # Helper: find class label in the leftmost part of a line
        def find_label(line: str) -> str | None:
            if not year_positions:
                return None
            label_end = year_positions[0][0] - 6
            if label_end < 2:
                label_end = 18
            region = line[:label_end].strip()
            # Remove parenthesised percentages or stray numbers
            region = re.sub(r"\([\d.%]+\)", "", region).strip()
            region = re.sub(r"[\d.]+%", "", region).strip()
            if not region:
                return None
            return _norm_class(region)

        # Collect raw lines from header+1 to Total
        raw_lines = []
        for line in lines[header_idx + 1 : header_idx + 40]:
            stripped = line.strip()
            if re.match(r"Total\b", stripped, re.IGNORECASE):
                break
            if re.match(r"\d+\.\s", stripped) and "class" not in stripped.lower():
                break
            raw_lines.append(line)

        # Merge consecutive non-percentage lines that together form one row.
        # A "data line" has integers at column positions; a "pct line" has % signs.
        # If line N has counts but no label, and line N+1 has a label (but maybe
        # fewer counts because they're in the rightmost columns), merge them.
        merged = []
        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            stripped = line.strip()

            # Skip empty and percentage-only lines
            if not stripped or ("%" in stripped and not find_label(line)):
                i += 1
                continue

            label = find_label(line)
            counts = extract_counts(line)

            if counts and not label and i + 1 < len(raw_lines):
                # Counts without label — peek at next line for the label
                next_line = raw_lines[i + 1]
                next_label = find_label(next_line)
                next_counts = extract_counts(next_line)
                if next_label:
                    # Merge: take label from next, counts from both
                    all_counts = {**counts, **next_counts}
                    merged.append((next_label, all_counts))
                    i += 2
                    continue
            elif label and counts:
                merged.append((label, counts))
                i += 1
                continue
            elif label and not counts:
                # Label with no counts on this line — check next line for counts
                if i + 1 < len(raw_lines):
                    next_line = raw_lines[i + 1]
                    next_counts = extract_counts(next_line)
                    if next_counts and not find_label(next_line):
                        merged.append((label, next_counts))
                        i += 2
                        continue
                # No counts found — record with zero for all years
                merged.append((label, {}))

            i += 1

        # Build results
        for norm_class, counts in merged:
            for yr, count in counts.items():
                results.append({
                    "report_year": report_year,
                    "data_year": yr,
                    "class": norm_class,
                    "count": count,
                    "pct": None,
                })

        # Compute percentages from counts
        by_year: dict[int, list[dict]] = {}
        for r in results:
            by_year.setdefault(r["data_year"], []).append(r)
        for dy, rows in by_year.items():
            total = sum(r["count"] for r in rows)
            if total > 0:
                for r in rows:
                    r["pct"] = round(100.0 * r["count"] / total, 1)

        return results


# ---------------------------------------------------------------------------
# Parser 2: Subject-level aggregates from prose
# ---------------------------------------------------------------------------

class SubjectAggregatesParser(Parser):
    name = "subject_aggregates"

    def extract(self, report_year: int, text: str) -> list[dict]:
        results = []

        # Join the text into a single string for multi-line matching
        flat = " ".join(text.split())

        # Detect the previous-year reference
        prev_year = None
        m = re.search(r"\((\d{4}) figures? in brackets?\)", flat, re.IGNORECASE)
        if m:
            prev_year = int(m.group(1))

        # --- Extract means ---
        # Pattern A (2011): "Philosophy, 65.6 (65.3); Politics, 65.2 (64.8); Economics, 64.7 (64.9)"
        # Pattern B (2012+): "for all scripts, 65.4 (64.7); for Philosophy, 65.5 (64.6); ..."
        # Both follow "average marks..." and have "Subject, VALUE (PREV_VALUE);" structure
        subjects = ["all scripts", "philosophy", "politics", "economics"]
        for subj in subjects:
            # Match "Subject, VALUE" or "for Subject, VALUE" with optional (PREV)
            pattern = re.compile(
                r"(?:for\s+)?" + re.escape(subj) + r"[,:]?\s*([\d.]+)\s*(?:\(([\d.]+)\))?",
                re.IGNORECASE,
            )
            for sm in pattern.finditer(flat):
                # Only match if it's near an "average mark" context
                context_start = max(0, sm.start() - 200)
                context = flat[context_start:sm.start()]
                if "average mark" not in context.lower():
                    continue

                subject = subj.title()
                if subject == "All Scripts":
                    subject = "All"
                val = float(sm.group(1))
                results.append({
                    "report_year": report_year,
                    "data_year": report_year,
                    "subject": subject,
                    "mean": val,
                    "sd": None,
                })
                if sm.group(2) and prev_year:
                    results.append({
                        "report_year": report_year,
                        "data_year": prev_year,
                        "subject": subject,
                        "mean": float(sm.group(2)),
                        "sd": None,
                    })

        # --- Extract SDs ---
        # Pattern A (2011): "standard deviation of marks ... was 5.5 (4.8) in Philosophy, 4.9 (4.9) in Politics and 7.4 (6.7) in Economics"
        # Pattern B (2012+): "standard deviations were ... for Philosophy 5.0 (6.1); for Politics 4.8 (4.9); for Economics 8.9 (7.4)"
        # Pattern C: "for all scripts, 6.06 (N/A for 2013), for Philosophy, 5.14 (5.0); ..."

        # Find the SD sentence region
        sd_match = re.search(r"standard deviations? (?:of marks )?(?:in the three subjects )?(?:were|was)\b(.*?)(?:\.\s+(?:[A-Z]|\d+\.))", flat, re.IGNORECASE)
        if sd_match:
            sd_body = sd_match.group(1)

            for subj in subjects:
                # "for Subject VALUE (PREV)" or "VALUE (PREV) in Subject"
                p1 = re.search(
                    r"(?:for\s+)?" + re.escape(subj) + r"[,:]?\s*([\d.]+)\s*(?:\(([\d.]+)\))?",
                    sd_body, re.IGNORECASE,
                )
                p2 = re.search(
                    r"([\d.]+)\s*\(([\d.]+)\)\s+in\s+" + re.escape(subj),
                    sd_body, re.IGNORECASE,
                )
                sm = p2 or p1
                if sm:
                    subject = subj.title()
                    if subject == "All Scripts":
                        subject = "All"
                    sd_val = float(sm.group(1))
                    # Update matching mean entry
                    for r in results:
                        if r["data_year"] == report_year and r["subject"] == subject and r["sd"] is None:
                            r["sd"] = sd_val
                            break
                    # Previous year
                    if sm.group(2) and prev_year:
                        try:
                            prev_sd = float(sm.group(2))
                            for r in results:
                                if r["data_year"] == prev_year and r["subject"] == subject and r["sd"] is None:
                                    r["sd"] = prev_sd
                                    break
                        except ValueError:
                            pass

        # --- Also extract from branch stats tables (2016+) ---
        self._extract_from_branch_table(report_year, text, results)

        # Deduplicate
        seen = set()
        deduped = []
        for r in results:
            key = (r["report_year"], r["data_year"], r["subject"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    def _extract_from_branch_table(self, report_year: int, text: str, results: list[dict]):
        """Extract from branch statistics tables (2016+). Three formats:
        A (2016-2018): labeled rows like "Philosophy (Avg) 65.1 65.8"
        B (2019-2023): compact "Phil Pol Econ All" columns with Avg./St. D. rows
        C (2024-2025): hierarchical indented "2023/24 MT" -> "Phil" -> "F"/"M"
        """
        lines = text.split("\n")

        # Find the branch stats table header (skip TOC entries by requiring line > 50)
        start = None
        patterns = [
            r"(?:average mark|standard deviation).*(?:each branch|in each branch)",
            r"average mark.*standard deviation.*(?:total|subject)",
        ]
        for pat in patterns:
            for i, line in enumerate(lines):
                if i > 50 and re.search(pat, line, re.IGNORECASE):
                    start = i
                    break
            if start is not None:
                break
        if start is None:
            return

        # Detect format by scanning lines after header
        for i in range(start + 1, min(start + 15, len(lines))):
            line = lines[i]
            if re.search(r"\(Avg\)", line):
                self._parse_branch_labeled(report_year, lines, start, results)
                return
            if re.search(r"Phil\s+Pol\s+Econ\s+All", line):
                self._parse_branch_compact(report_year, lines, start, results)
                return
            if re.match(r"Avg|Average", line.strip(), re.IGNORECASE):
                self._parse_branch_compact(report_year, lines, start, results)
                return
            if re.search(r"\d{4}/\d{2}\s+MT", line):
                self._parse_branch_hierarchical(report_year, lines, start, results)
                return

    def _parse_branch_labeled(self, report_year: int, lines: list[str], start: int, results: list[dict]):
        """Format A (2016-2018): 'Subject (Avg) val1 val2 val3' rows."""
        years = []
        for i in range(start, min(start + 10, len(lines))):
            year_matches = list(re.finditer(r"\b(20\d{2})\b", lines[i]))
            if len(year_matches) >= 2:
                years = [int(m.group(1)) for m in year_matches]
                break
        if not years:
            return

        subject_map = {"all scripts": "All", "all subjects": "All", "philosophy": "Philosophy", "politics": "Politics", "economics": "Economics"}
        for line in lines[start:start + 40]:
            for key, subj in subject_map.items():
                if key in line.lower().replace("*", ""):
                    nums = re.findall(r"\d+\.\d+", line)
                    if "(avg)" in line.lower():
                        for yi, yr in enumerate(years):
                            if yi < len(nums):
                                results.append({
                                    "report_year": report_year, "data_year": yr,
                                    "subject": subj, "mean": float(nums[yi]), "sd": None,
                                })
                    elif "(st dev)" in line.lower():
                        for yi, yr in enumerate(years):
                            if yi < len(nums):
                                for r in results:
                                    if r["report_year"] == report_year and r["data_year"] == yr and r["subject"] == subj and r["sd"] is None:
                                        r["sd"] = float(nums[yi])
                                        break
                    break

    def _parse_branch_compact(self, report_year: int, lines: list[str], start: int, results: list[dict]):
        """Format B (2019-2023): compact table with 'Phil Pol Econ All' column groups."""
        years = []
        for i in range(start, min(start + 10, len(lines))):
            year_matches = list(re.finditer(r"\b(20\d{2})\b", lines[i]))
            if len(year_matches) >= 2:
                years = [int(m.group(1)) for m in year_matches]
                break
        if not years:
            return

        for line in lines[start:start + 15]:
            stripped = line.strip()
            if re.match(r"Avg|Average", stripped, re.IGNORECASE):
                nums = re.findall(r"\d+\.\d+", stripped)
                if len(nums) >= 4:
                    per_year = len(nums) // len(years)
                    for yi, yr in enumerate(years):
                        offset = yi * per_year
                        for si, subj in enumerate(["Philosophy", "Politics", "Economics", "All"]):
                            if offset + si < len(nums):
                                results.append({
                                    "report_year": report_year, "data_year": yr,
                                    "subject": subj, "mean": float(nums[offset + si]), "sd": None,
                                })
            elif re.match(r"St", stripped, re.IGNORECASE):
                nums = re.findall(r"\d+\.\d+", stripped)
                if len(nums) >= 4:
                    per_year = len(nums) // len(years)
                    for yi, yr in enumerate(years):
                        offset = yi * per_year
                        for si, subj in enumerate(["Philosophy", "Politics", "Economics", "All"]):
                            if offset + si < len(nums):
                                for r in results:
                                    if r["report_year"] == report_year and r["data_year"] == yr and r["subject"] == subj and r["sd"] is None:
                                        r["sd"] = float(nums[offset + si])
                                        break

    def _parse_branch_hierarchical(self, report_year: int, lines: list[str], start: int, results: list[dict]):
        """Format C (2024-2025): hierarchical indented year/branch/gender rows."""
        branch_map = {"phil": "Philosophy", "pol": "Politics", "econ": "Economics"}
        current_year = None

        for line in lines[start:start + 100]:
            # Year header: "2023/24 MT"
            ym = re.match(r"\s*(20\d{2})/(\d{2})\s+MT", line)
            if ym:
                current_year = int(ym.group(1)) + 1  # "2023/24" -> data_year 2024
                nums = re.findall(r"\d+\.\d+", line)
                if len(nums) >= 2:
                    results.append({
                        "report_year": report_year, "data_year": current_year,
                        "subject": "All", "mean": float(nums[0]), "sd": float(nums[1]),
                    })
                continue
            if current_year is None:
                continue
            # Branch line (1 level indent): "  Phil   542   65.2   5.0"
            bm = re.match(r"\s{2,4}(Phil|Pol|Econ)\b", line)
            if bm and not re.match(r"\s{4,}", line):
                branch = branch_map.get(bm.group(1).lower())
                if branch:
                    nums = re.findall(r"\d+\.\d+", line)
                    if len(nums) >= 2:
                        results.append({
                            "report_year": report_year, "data_year": current_year,
                            "subject": branch, "mean": float(nums[0]), "sd": float(nums[1]),
                        })
                continue
            # Skip gender lines (deeper indent) and Total lines
            if re.match(r"\s{4,}[FM]", line) or re.match(r"\s+Total", line, re.IGNORECASE):
                continue
            # Stop if we hit the next section
            if re.match(r"\s*c\.\s", line) or re.match(r"\s*Page\s+\d+", line, re.IGNORECASE):
                if current_year:
                    break


# ---------------------------------------------------------------------------
# Parser 3: Gender statistics (total candidates, mean, SD by gender)
# ---------------------------------------------------------------------------

class GenderStatsParser(Parser):
    name = "gender_stats"

    def extract(self, report_year: int, text: str) -> list[dict]:
        results = []

        # Try tabular format first (2015+)
        results.extend(self._parse_table(report_year, text))

        # Try prose format (2011-2014)
        results.extend(self._parse_prose(report_year, text))

        # Deduplicate
        seen = set()
        deduped = []
        for r in results:
            key = (r["report_year"], r["data_year"], r["gender"])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return deduped

    def _parse_table(self, report_year: int, text: str) -> list[dict]:
        """Parse the tabular gender stats (2015-2023)."""
        results = []
        lines = text.split("\n")

        # Look for "Overall Statistics by Sex/Gender" or "Average mark and standard deviation by gender"
        start = None
        for i, line in enumerate(lines):
            if re.search(r"overall statistics by (sex|gender)", line, re.IGNORECASE):
                start = i
                break
            if re.search(r"average mark and standard deviation by gender", line, re.IGNORECASE):
                start = i
                break
        if start is None:
            return results

        # Check if it says "See Section 3" (2024-2025 redirect)
        for line in lines[start:start+5]:
            if "see section" in line.lower():
                return results

        # Find year header row with F/M columns
        year_gender_cols = []  # [(col_start, year, gender)]
        for line in lines[start:start+15]:
            years = list(re.finditer(r"\b(20\d{2})\b", line))
            if len(years) >= 2:
                # Next line should have F/M
                idx = lines.index(line, start)
                fm_line = lines[idx + 1] if idx + 1 < len(lines) else ""
                fm_matches = list(re.finditer(r"\b([FM])\b", fm_line))
                if len(fm_matches) >= 2:
                    # Match F/M positions to years
                    for fm_m in fm_matches:
                        gender = fm_m.group(1)
                        col = fm_m.start()
                        # Find closest year
                        best_year = None
                        best_dist = 999
                        for ym in years:
                            dist = abs(col - ym.start())
                            if dist < best_dist:
                                best_dist = dist
                                best_year = int(ym.group(1))
                        if best_year:
                            year_gender_cols.append((col, best_year, gender))
                    break

        if not year_gender_cols:
            return results

        # Parse rows: Total Candidates, Average Mark, Standard Deviation
        data = {}  # (year, gender) -> {total, mean, sd}
        for col, yr, g in year_gender_cols:
            data[(yr, g)] = {"total": None, "mean": None, "sd": None}

        for line in lines[start+3:start+20]:
            stripped = line.strip().lower()
            field = None
            if "total" in stripped and "cand" in stripped:
                field = "total"
            elif "average" in stripped or "avg" in stripped:
                field = "mean"
            elif "st" in stripped and "dev" in stripped:
                field = "sd"

            if field is None:
                continue

            # Extract values at each column position
            for col, yr, g in year_gender_cols:
                window_start = max(0, col - 3)
                window_end = min(len(line), col + 15)
                window = line[window_start:window_end]
                num_match = re.search(r"([\d.]+)", window)
                if num_match:
                    val = num_match.group(1)
                    if field == "total":
                        # Could have percentage after count
                        if "%" not in window:
                            data[(yr, g)][field] = int(float(val))
                        else:
                            # Try to find the count before the %
                            count_match = re.search(r"(\d+)\s", window)
                            if count_match:
                                data[(yr, g)][field] = int(count_match.group(1))
                    else:
                        data[(yr, g)][field] = float(val)

        for (yr, g), vals in data.items():
            if vals["mean"] is not None:
                results.append({
                    "report_year": report_year,
                    "data_year": yr,
                    "gender": g,
                    "total": vals["total"],
                    "mean": vals["mean"],
                    "sd": vals["sd"],
                })

        return results

    def _parse_prose(self, report_year: int, text: str) -> list[dict]:
        """Parse gender stats from prose (2011-2014)."""
        results = []

        # Pattern: "X (Y%) of the Z candidates were female"
        m = re.search(
            r"(\d+)\s*\(([\d.]+)%\)\s*(?:of the\s+)?(\d+)\s+candidates were female",
            text, re.IGNORECASE,
        )
        if m:
            n_female = int(m.group(1))
            n_total = int(m.group(3))
            n_male = n_total - n_female

        # Pattern: "average mark for female candidates was X.X"
        fm = re.search(
            r"average mark for female candidates was ([\d.]+).*?"
            r"standard deviation (?:was|for female candidates (?:in \d+ )?was) ([\d.]+)",
            text, re.IGNORECASE | re.DOTALL,
        )
        mm = re.search(
            r"average mark for male candidates was ([\d.]+).*?"
            r"standard deviation (?:was|for male candidates (?:was )?)?([\d.]+)",
            text, re.IGNORECASE | re.DOTALL,
        )

        if fm:
            results.append({
                "report_year": report_year,
                "data_year": report_year,
                "gender": "F",
                "total": n_female if m else None,
                "mean": float(fm.group(1)),
                "sd": float(fm.group(2)),
            })
        if mm:
            results.append({
                "report_year": report_year,
                "data_year": report_year,
                "gender": "M",
                "total": n_male if m else None,
                "mean": float(mm.group(1)),
                "sd": float(mm.group(2)),
            })

        return results


# ---------------------------------------------------------------------------
# Registry and main
# ---------------------------------------------------------------------------

ALL_PARSERS = [
    ClassDistributionParser(),
    SubjectAggregatesParser(),
    GenderStatsParser(),
]


def run_extraction(
    years: list[int] | None = None,
    dry_run: bool = False,
) -> dict[str, list[dict]]:
    """Run all parsers on all (or selected) reports. Return {parser_name: [records]}."""
    reports = get_reports()
    if years:
        reports = [(y, p) for y, p in reports if y in years]

    all_results: dict[str, list[dict]] = {p.name: [] for p in ALL_PARSERS}

    for report_year, pdf_path in reports:
        print(f"Processing {pdf_path.name} ({report_year})...")
        text = extract_text(pdf_path)

        for parser in ALL_PARSERS:
            try:
                records = parser.extract(report_year, text)
                all_results[parser.name].extend(records)
                if records:
                    print(f"  {parser.name}: {len(records)} records")
                else:
                    print(f"  {parser.name}: no records found")
            except Exception as e:
                print(f"  {parser.name}: ERROR - {e}")

    if not dry_run:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        for name, records in all_results.items():
            if records:
                out_path = RAW_DIR / f"{name}.json"
                with open(out_path, "w") as f:
                    json.dump(records, f, indent=2)
                print(f"Wrote {out_path} ({len(records)} records)")

    return all_results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, nargs="*", help="Process only these years")
    ap.add_argument("--dry-run", action="store_true", help="Don't write files")
    args = ap.parse_args()
    results = run_extraction(years=args.year, dry_run=args.dry_run)

    if args.dry_run:
        for name, records in results.items():
            print(f"\n=== {name} ({len(records)} records) ===")
            for r in records[:10]:
                print(f"  {r}")
            if len(records) > 10:
                print(f"  ... and {len(records) - 10} more")
