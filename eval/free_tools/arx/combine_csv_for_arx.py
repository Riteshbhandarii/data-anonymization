from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_DIR = BASE_DIR / "csv"
OUTPUT_DIR = BASE_DIR / "arx_data"

OUTPUT_DIR.mkdir(exist_ok=True)


def combine_files(language):

    pattern = f"{language}_csv_*.csv"
    files = sorted(CSV_DIR.glob(pattern))

    files = [
        f for f in files
        if not f.name.lower().startswith("anonymized_")
    ]

    print(f"\n{language.upper()}: Found {len(files)} files")

    dataframes = []

    for file in files:
        print("Adding:", file.name)

        df = pd.read_csv(file)

        df["source_file"] = file.name

        dataframes.append(df)

    if not dataframes:
        print("No files found!")
        return

    combined = pd.concat(
        dataframes,
        ignore_index=True
    )

    output_file = OUTPUT_DIR / f"arx_{language}_combined.csv"

    combined.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCreated:")
    print(output_file)

    print("Total rows:", len(combined))
    print("Columns:", list(combined.columns))


combine_files("en")
combine_files("fi")

print("\nFinished.")