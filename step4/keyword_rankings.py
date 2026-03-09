#!/usr/bin/env python3
"""
Step 4: Keyword Ranking Checker
Searches Google Play Store for each keyword Blockchain.com uses,
records the ranking position of Blockchain.com and top 5 competitors.
Reads keyword_analysis.csv from ../step3/, outputs keyword_rankings.csv

Note: Google Play Store search returns max ~30 results per query.
If Blockchain.com is not in the top 30, it shows as 'Not in top 30'.
"""

import csv
import os
import sys
import time
import random

from google_play_scraper import search as gplay_search

# ── Paths ──────────────────────────────────────────────────────────────────
STEP3_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "step3")
STEP3_CSV = os.path.join(STEP3_DIR, "keyword_analysis.csv")
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "keyword_rankings.csv")

BLOCKCHAIN_PKG = "piuk.blockchain.android"
BC_APP_NAME = "Blockchain Wallet: Buy BTC"
MAX_RESULTS = 30  # Google Play caps search at ~30


def load_bc_keywords():
    """Load unique keywords that Blockchain.com uses from the main step3 CSV."""
    if not os.path.exists(STEP3_CSV):
        print(f"ERROR: {STEP3_CSV} not found. Run step3 first.")
        sys.exit(1)

    keywords = {}
    with open(STEP3_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('app_name', '') == BC_APP_NAME:
                kw = row['keyword']
                if kw not in keywords:
                    keywords[kw] = {
                        'type': row['type'],
                        'theme': row['theme'],
                        'reach': row['reach'],
                        'table_stakes': row['table_stakes'],
                    }
    return keywords


def search_keyword(keyword):
    """Search Google Play for a keyword and return ranked list of apps."""
    try:
        results = gplay_search(keyword, n_hits=MAX_RESULTS, lang='en', country='us')
        ranked = []
        for i, r in enumerate(results):
            ranked.append({
                'rank': i + 1,
                'package_id': r['appId'],
                'title': r.get('title', ''),
            })
        return ranked
    except Exception as e:
        print(f"  ERROR searching '{keyword}': {e}")
        return []


def main():
    print("=" * 60)
    print("Step 4: Keyword Ranking Checker")
    print("=" * 60)

    # Load BC keywords from step3 main CSV
    bc_keywords = load_bc_keywords()
    if not bc_keywords:
        print(f"\nERROR: No Blockchain.com keywords found in {STEP3_CSV}")
        sys.exit(1)

    # Sort by reach (highest first)
    sorted_keywords = sorted(
        bc_keywords.items(),
        key=lambda x: int(x[1].get('reach', 0)),
        reverse=True
    )

    total = len(sorted_keywords)
    print(f"\nKeywords to search: {total}")
    print(f"Target app: {BLOCKCHAIN_PKG}")
    print(f"Max results per search: {MAX_RESULTS} (Google Play limit)")

    rows = []
    found_count = 0
    not_found_count = 0

    for i, (keyword, meta) in enumerate(sorted_keywords, 1):
        print(f"\n[{i}/{total}] Searching: '{keyword}' (reach: {meta['reach']})")

        results = search_keyword(keyword)

        # Find Blockchain.com's position
        bc_rank = None
        total_results = len(results)

        for r in results:
            if r['package_id'] == BLOCKCHAIN_PKG:
                bc_rank = r['rank']
                break

        if bc_rank:
            found_count += 1
            print(f"  ✓ Blockchain.com ranked #{bc_rank} out of {total_results}")
        else:
            not_found_count += 1
            print(f"  ✗ Blockchain.com not in top {total_results}")

        # Get top 5 competitors (excluding Blockchain.com)
        top5 = []
        for r in results:
            if r['package_id'] != BLOCKCHAIN_PKG:
                top5.append(r)
            if len(top5) == 5:
                break

        row = {
            'keyword': keyword,
            'type': meta['type'],
            'theme': meta['theme'],
            'reach': meta['reach'],
            'table_stakes': meta['table_stakes'],
            'bc_rank': bc_rank if bc_rank else 'Not in top 30',
            'total_results': total_results,
        }

        for n in range(1, 6):
            if n <= len(top5):
                row[f'top_{n}'] = top5[n - 1]['title']
                row[f'top_{n}_pkg'] = top5[n - 1]['package_id']
            else:
                row[f'top_{n}'] = ''
                row[f'top_{n}_pkg'] = ''

        rows.append(row)

        # Small delay to avoid rate limiting
        time.sleep(random.uniform(0.5, 1.5))

    # Sort output by reach desc, then bc_rank
    rows.sort(key=lambda r: (
        -int(r['reach']),
        0 if r['bc_rank'] == 'Not in top 30' else -1,
        int(r['bc_rank']) if r['bc_rank'] != 'Not in top 30' else 999,
    ))

    # Write CSV
    fieldnames = [
        'keyword', 'type', 'theme', 'reach', 'table_stakes',
        'bc_rank', 'total_results',
        'top_1', 'top_1_pkg',
        'top_2', 'top_2_pkg',
        'top_3', 'top_3_pkg',
        'top_4', 'top_4_pkg',
        'top_5', 'top_5_pkg',
    ]

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Keywords searched: {total}")
    print(f"BC ranked (in top 30): {found_count}")
    print(f"BC not in top 30:      {not_found_count}")

    ranked_rows = [r for r in rows if r['bc_rank'] != 'Not in top 30']
    if ranked_rows:
        ranked_rows.sort(key=lambda r: int(r['bc_rank']))
        print(f"\nTop 10 best rankings:")
        for r in ranked_rows[:10]:
            print(f"  #{r['bc_rank']:>3} — '{r['keyword']}' (reach: {r['reach']})")

        print(f"\nBottom 10 worst rankings:")
        for r in ranked_rows[-10:]:
            print(f"  #{r['bc_rank']:>3} — '{r['keyword']}' (reach: {r['reach']})")

    print(f"\nOutput: {OUTPUT_CSV}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
