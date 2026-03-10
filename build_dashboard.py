#!/usr/bin/env python3
"""
Build Dashboard: Reads step3 and step4 CSVs and injects fresh data into dashboard.html
Run this after step3 and/or step4 to update the dashboard without manual editing.
"""

import csv
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STEP3_CSV = os.path.join(BASE_DIR, "step3", "keyword_analysis.csv")
STEP4_CSV = os.path.join(BASE_DIR, "step4", "keyword_rankings.csv")
DASHBOARD = os.path.join(BASE_DIR, "dashboard.html")


def read_csv(path):
    """Read a CSV file and return list of dicts."""
    if not os.path.exists(path):
        print(f"WARNING: {path} not found, skipping.")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    print("=" * 60)
    print("Build Dashboard")
    print("=" * 60)

    if not os.path.exists(DASHBOARD):
        print(f"ERROR: {DASHBOARD} not found.")
        sys.exit(1)

    with open(DASHBOARD, 'r', encoding='utf-8') as f:
        html = f.read()

    updated = []

    # Inject step3 data
    rows3 = read_csv(STEP3_CSV)
    if rows3 is not None:
        old3 = re.search(r'const DATA3\s*=\s*\[.*?\];', html, re.DOTALL)
        if old3:
            html = html[:old3.start()] + f'const DATA3 = {json.dumps(rows3)};' + html[old3.end():]
            updated.append(f"DATA3: {len(rows3)} rows from step3")
        else:
            print("WARNING: Could not find DATA3 in dashboard.html")

    # Inject step4 data
    rows4 = read_csv(STEP4_CSV)
    if rows4 is not None:
        old4 = re.search(r'const DATA4\s*=\s*\[.*?\];', html, re.DOTALL)
        if old4:
            html = html[:old4.start()] + f'const DATA4 = {json.dumps(rows4)};' + html[old4.end():]
            updated.append(f"DATA4: {len(rows4)} rows from step4")
        else:
            print("WARNING: Could not find DATA4 in dashboard.html")

    with open(DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nUpdated: {', '.join(updated)}")
    print(f"Output: {DASHBOARD}")
    print("=" * 60)


if __name__ == "__main__":
    main()
