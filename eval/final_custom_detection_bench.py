#!/usr/bin/env python3

"""
Run the final detection benchmark with the project's custom recognizers.

Custom recognizers:
- INVOICE
- PERSONAL_ID
- PLATE

The baseline benchmark implementation remains unchanged so that
baseline and improved results can be compared directly.
"""

import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------
# Make repository modules importable
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))


# ---------------------------------------------------------
# Import baseline benchmark and project recognizers
# ---------------------------------------------------------

import final_detection_bench as bench

from detect.pattern_recognizers import register_project_recognizers


# ---------------------------------------------------------
# Add project-specific entity mappings
# ---------------------------------------------------------

bench.TYPE_MAP.update({
    "PLATE": "PLATE",
    "INVOICE": "INVOICE",
    "PERSONAL_ID": "PERSONAL_ID",
})


# ---------------------------------------------------------
# Extend the baseline analyzer
# ---------------------------------------------------------

baseline_build_analyzer = bench.build_analyzer


def build_custom_analyzer():
    """
    Build the same Presidio analyzer as the baseline,
    then register the project-specific recognizers.
    """

    analyzer = baseline_build_analyzer()

    register_project_recognizers(analyzer)

    return analyzer


bench.build_analyzer = build_custom_analyzer


# ---------------------------------------------------------
# Run benchmark without destroying baseline result files
# ---------------------------------------------------------

def main(root):

    results_dir = ROOT / "eval" / "results"

    results_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    baseline_result = (
        results_dir
        / "final-presidio.json"
    )

    baseline_misses = (
        results_dir
        / "final-misses.json"
    )

    backup_result = (
        results_dir
        / "_baseline-presidio-backup.json"
    )

    backup_misses = (
        results_dir
        / "_baseline-misses-backup.json"
    )

    custom_result = (
        results_dir
        / "final-custom-presidio.json"
    )

    custom_misses = (
        results_dir
        / "final-custom-misses.json"
    )

    # Preserve the existing baseline output.
    if baseline_result.exists():

        shutil.copy2(
            baseline_result,
            backup_result,
        )

    if baseline_misses.exists():

        shutil.copy2(
            baseline_misses,
            backup_misses,
        )

    print()
    print("=" * 86)
    print(
        "final detection benchmark "
        "+ CUSTOM RECOGNIZERS"
    )
    print("=" * 86)

    try:

        # This writes the normal baseline output filenames.
        bench.main(root)

        # Rename the newly generated files as custom results.
        if baseline_result.exists():

            if custom_result.exists():
                custom_result.unlink()

            baseline_result.replace(
                custom_result
            )

        if baseline_misses.exists():

            if custom_misses.exists():
                custom_misses.unlink()

            baseline_misses.replace(
                custom_misses
            )

    finally:

        # Restore original baseline result files.
        if backup_result.exists():

            backup_result.replace(
                baseline_result
            )

        if backup_misses.exists():

            backup_misses.replace(
                baseline_misses
            )

    print()
    print("=" * 86)
    print("CUSTOM RESULT FILES")
    print("=" * 86)

    print(custom_result)
    print(custom_misses)


if __name__ == "__main__":

    root = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "bench_final_detection"
    )

    main(root)


