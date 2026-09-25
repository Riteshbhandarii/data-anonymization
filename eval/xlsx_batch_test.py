from pathlib import Path
import subprocess
import sys
import csv

from xlsx_evaluate import evaluate_leakage
from xlsx_consistency import evaluate_consistency
from xlsx_context import evaluate_context


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

MAX_FILES = 10

METHODS = {
    "redaction": "redact/xlsx_redaction.py",
    "tokenization": "redact/xlsx_tokenization.py",
    "surrogate": "redact/xlsx_surrogate.py",
    "masking": "redact/xlsx_masking.py",
    "generalization": "redact/xlsx_generalization.py",
    "date_shifting": "redact/xlsx_date_shifting.py",
}


def run_anonymizer(script_path, input_file, output_file):
    """
    Run one anonymization script and automatically answer
    its two input prompts.
    """

    user_input = (
        f"{input_file}\n"
        f"{output_file}\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            script_path,
        ],
        input=user_input,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print("\nERROR")
        print(result.stderr)

        return False

    return True


def main():

    dataset_folder = input(
        "Enter XLSX dataset folder: "
    ).strip().strip('"')

    dataset_folder = Path(dataset_folder)

    if not dataset_folder.exists():
        print("Dataset folder does not exist.")
        return

    files = sorted(
        dataset_folder.glob("*.xlsx")
    )

    if not files:
        print("No XLSX files found.")
        return

    # Test only first N files
    files = files[:MAX_FILES]

    print(
        f"\nFound {len(files)} XLSX files "
        f"for batch testing."
    )

    project_root = Path(__file__).resolve().parent.parent

    results_folder = (
        project_root
        / "results"
        / "xlsx_batch"
    )

    results_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_path = (
        results_folder
        / "xlsx_batch_results.csv"
    )

    rows = []

    # -------------------------------------------------
    # FILE LOOP
    # -------------------------------------------------

    for file_index, original_file in enumerate(
        files,
        start=1
    ):

        print("\n" + "=" * 80)

        print(
            f"FILE {file_index}/{len(files)}: "
            f"{original_file.name}"
        )

        print("=" * 80)

        # ---------------------------------------------
        # METHOD LOOP
        # ---------------------------------------------

        for method_name, script_relative in METHODS.items():

            print(
                f"\nTesting method: "
                f"{method_name}"
            )

            script_path = (
                project_root
                / script_relative
            )

            output_file = (
                results_folder
                / (
                    f"{original_file.stem}"
                    f"_{method_name}.xlsx"
                )
            )

            success = run_anonymizer(
                script_path,
                original_file,
                output_file,
            )

            if not success:

                rows.append(
                    {
                        "file": original_file.name,
                        "method": method_name,
                        "data_leakage": "ERROR",
                        "full_leaks": "",
                        "partial_leaks": "",
                        "consistency": "",
                        "context": "",
                    }
                )

                continue

            # -----------------------------------------
            # DATA LEAKAGE
            # -----------------------------------------

            leakage_result = evaluate_leakage(
                str(original_file),
                str(output_file),
            )

            leakage_score = leakage_result[0]
            full_leaks = len(leakage_result[1])
            partial_leaks = len(leakage_result[2])

            # -----------------------------------------
            # CONSISTENCY
            # -----------------------------------------

            consistency_score = evaluate_consistency(
                str(original_file),
                str(output_file),
            )

            # -----------------------------------------
            # CONTEXT
            # -----------------------------------------

            context_result = evaluate_context(
                str(original_file),
                str(output_file),
            )

            context_score = context_result[0]

            # -----------------------------------------
            # SAVE RESULT
            # -----------------------------------------

            rows.append(
                {
                    "file": original_file.name,
                    "method": method_name,
                    "data_leakage": leakage_score,
                    "full_leaks": full_leaks,
                    "partial_leaks": partial_leaks,
                    "consistency": consistency_score,
                    "context": context_score,
                }
            )

    # -------------------------------------------------
    # CSV
    # -------------------------------------------------

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "file",
                "method",
                "data_leakage",
                "full_leaks",
                "partial_leaks",
                "consistency",
                "context",
            ],
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 80)
    print("BATCH TEST COMPLETE")
    print("=" * 80)

    print(
        f"\nFiles tested: {len(files)}"
    )

    print(
        f"Methods per file: {len(METHODS)}"
    )

    print(
        f"Total method tests: {len(rows)}"
    )

    print(
        "\nResults saved to:"
    )

    print(csv_path)


if __name__ == "__main__":
    main()