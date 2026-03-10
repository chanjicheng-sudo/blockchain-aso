#!/usr/bin/env python3
"""
Run All: Execute the full ASO pipeline end-to-end.
  Step 1: Scrape competitors from Google Play Store
  Step 2: Fetch metadata (title, summary, description, developer, tags)
  Step 3: Keyword analysis with thematic classification
  Step 4: Google Play keyword ranking check
  Build:  Inject fresh data into dashboard.html

Usage:
  python run_all.py          # Run everything (steps 1-4 + dashboard)
  python run_all.py 3 4      # Run only steps 3, 4 + dashboard
  python run_all.py dashboard # Only rebuild the dashboard
"""

import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STEPS = {
    '1': ('step1/scrape_competitors.py', 'Step 1: Scrape Competitors'),
    '2': ('step2/fetch_metadata.py', 'Step 2: Fetch Metadata'),
    '3': ('step3/keyword_analysis.py', 'Step 3: Keyword Analysis'),
    '4': ('step4/keyword_rankings.py', 'Step 4: Keyword Rankings'),
}


def run_step(script, label):
    """Run a Python script and return success/failure."""
    path = os.path.join(BASE_DIR, script)
    if not os.path.exists(path):
        print(f"  ERROR: {path} not found, skipping.")
        return False

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}\n")

    start = time.time()
    result = subprocess.run(
        [sys.executable, path],
        cwd=os.path.dirname(path),
    )
    elapsed = time.time() - start

    if result.returncode == 0:
        print(f"\n  ✓ {label} completed in {elapsed:.1f}s")
        return True
    else:
        print(f"\n  ✗ {label} failed (exit code {result.returncode})")
        return False


def build_dashboard():
    """Rebuild the dashboard with fresh CSV data."""
    path = os.path.join(BASE_DIR, "build_dashboard.py")
    if not os.path.exists(path):
        print("  ERROR: build_dashboard.py not found.")
        return False

    print(f"\n{'='*60}")
    print(f"  Building Dashboard")
    print(f"{'='*60}\n")

    result = subprocess.run([sys.executable, path], cwd=BASE_DIR)
    return result.returncode == 0


def main():
    args = sys.argv[1:]

    # Determine which steps to run
    if not args:
        steps_to_run = ['1', '2', '3', '4']
    elif args == ['dashboard']:
        steps_to_run = []
    else:
        steps_to_run = [a for a in args if a in STEPS]

    print("\n" + "=" * 60)
    print("  ASO Pipeline Runner")
    print("=" * 60)

    if steps_to_run:
        print(f"  Steps to run: {', '.join(steps_to_run)}")
    else:
        print("  Dashboard rebuild only")

    results = {}
    for step_num in steps_to_run:
        script, label = STEPS[step_num]
        results[step_num] = run_step(script, label)

    # Always rebuild dashboard at the end
    build_dashboard()

    # Summary
    print(f"\n{'='*60}")
    print("  PIPELINE SUMMARY")
    print(f"{'='*60}")
    for step_num, success in results.items():
        _, label = STEPS[step_num]
        status = "✓" if success else "✗"
        print(f"  {status} {label}")
    print(f"  ✓ Dashboard rebuilt")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
