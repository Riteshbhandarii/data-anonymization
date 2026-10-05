from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
XLSX_DIR = BASE_DIR / "xlsx"
OUTPUT_DIR = BASE_DIR / "arx_data"

OUTPUT_DIR.mkdir(exist_ok=True)


def combine_xlsx(language):

    pattern = f"{language}_xlsx_*.xlsx"
    files = sorted(XLSX_DIR.glob(pattern))

    # Skip previously anonymized files
    files = [
        f for f in files
        if not f.name.lower().startswith("anonymized_")
    ]

    print(f"\n{language.upper()}: Found {len(files)} XLSX files")

    dataframes = []

    for file in files:

        print("Reading:", file.name)

        try:
            # Read the first/normal worksheet
            df = pd.read_excel(file)

            # Skip completely empty sheets/files
            if df.empty:
                print("  Empty - skipped")
                continue

            # Record source file
            df["source_file"] = file.name

            dataframes.append(df)

        except Exception as error:
            print("  ERROR:", error)

    if not dataframes:
        print("No usable XLSX data found.")
        return

    combined = pd.concat(
        dataframes,
        ignore_index=True
    )

    output_file = (
        OUTPUT_DIR /
        f"arx_{language}_xlsx_combined.csv"
    )

    combined.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCreated:")
    print(output_file)
    print("Total rows:", len(combined))
    print("Columns:", list(combined.columns))


combine_xlsx("en")
combine_xlsx("fi")

print("\nFinished.")