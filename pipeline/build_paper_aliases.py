#!/usr/bin/env python3
"""
Build paper name normalisation map using LLM to cluster variants.

Outputs data/paper_aliases.json: {canonical_name: [variant1, variant2, ...]}
"""

import json
from pathlib import Path

import anthropic
import json_repair

RAW_DIR = Path("data/raw")


def get_all_paper_names():
    names = set()
    for f in RAW_DIR.glob("*_per_paper.json"):
        for r in json.loads(f.read_text()):
            if r.get("paper"):
                names.add(r["paper"])
    for f in RAW_DIR.glob("*_paper_numbers.json"):
        for r in json.loads(f.read_text()):
            if r.get("paper"):
                names.add(r["paper"])
    return sorted(names)


def cluster_names(names):
    client = anthropic.AnthropicBedrock(aws_region="us-east-1")

    prompt = f"""\
Below is a list of {len(names)} paper/assessment names from Oxford PPE exam reports spanning 2011-2025.
Many refer to the same paper but with different formatting:
- Abbreviated vs full names ("Gov. and Pol. of the US" vs "Government and Politics of the United States")
- With or without numeric codes ("101. Early Modern Philosophy" vs "Early Modern Philosophy")
- With or without degree suffixes ("(PPE)", "(HP)")
- With or without syllabus notes ("(old regs)", "(old syllabus)", "(take-home paper)")
- Minor punctuation/spelling differences

Group these into clusters where each cluster represents ONE distinct paper/assessment.
For each cluster, choose the clearest full name as the canonical name.

IMPORTANT rules:
- Papers with genuinely different content are DIFFERENT even if names are similar
  (e.g. "Microeconomics" and "Microeconomic Analysis" might be different papers if they coexist)
- "Thesis in Philosophy" / "Thesis in Politics" / "Thesis in Economics" are different
- Special subjects with different topics are different papers
- "(old regs)" / "(old syllabus)" variants ARE the same paper (just different exam regulations)
- "(PPE)" / "(HP)" suffixes indicate which degree but same paper content — group together
- "(take-home paper)" is the same paper in a different exam format — group together

Return a JSON object where each key is the canonical name and the value is an array of ALL
variant strings that map to it (including the canonical name itself).

Here are the names:

{json.dumps(names, indent=2)}

Return ONLY the JSON object."""

    resp = client.messages.create(
        model="us.anthropic.claude-sonnet-4-6",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = json_repair.loads(text)

    return data


def main():
    names = get_all_paper_names()
    print(f"Found {len(names)} unique paper names")

    print("Clustering via LLM...")
    clusters = cluster_names(names)

    # Verify all names are covered
    all_variants = set()
    for variants in clusters.values():
        all_variants.update(variants)

    missing = set(names) - all_variants
    if missing:
        print(f"WARNING: {len(missing)} names not in any cluster:")
        for n in sorted(missing):
            print(f"  {n}")

    extra = all_variants - set(names)
    if extra:
        print(f"NOTE: {len(extra)} names in clusters but not in input (LLM invented)")

    # Build reverse map: variant -> canonical
    alias_map = {}
    for canonical, variants in clusters.items():
        for v in variants:
            alias_map[v] = canonical

    out_path = Path("data/paper_aliases.json")
    with open(out_path, "w") as f:
        json.dump({"clusters": clusters, "alias_map": alias_map}, f, indent=2)

    print(f"\n{len(clusters)} canonical papers")
    print(f"{len(alias_map)} total aliases")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
