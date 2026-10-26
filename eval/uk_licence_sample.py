"""Recreate the 30-record UK licence sample used in the RQ2 evaluation.

Source: Leicester City Council licensed premises register.
Place the downloaded XLSX at outputs/uk-licence/licensed-premises-register.xlsx.
"""

from pathlib import Path

import pandas as pd

SOURCE = Path("outputs/uk-licence/licensed-premises-register.xlsx")
OUTPUT = Path("outputs/uk-licence/uk_licence_test_30.csv")
SEED = 42
SAMPLE_SIZE = 30


def main():
    if not SOURCE.exists():
        raise FileNotFoundError(f"Download the source spreadsheet to {SOURCE}")

    df = pd.read_excel(SOURCE, dtype=str).fillna("")
    df = df[df["Licence Number"].str.strip() != ""].copy()
    df["Prefix"] = df["Licence Number"].str.extract(r"^([A-Za-z]+)")[0]

    samples = []
    for _, group in df.groupby("Prefix"):
        n = max(1, round(SAMPLE_SIZE * len(group) / len(df)))
        samples.append(group.sample(n=min(n, len(group)), random_state=SEED))

    test = pd.concat(samples).drop_duplicates(subset=["Licence Number"])

    if len(test) > SAMPLE_SIZE:
        test = test.sample(SAMPLE_SIZE, random_state=SEED)
    elif len(test) < SAMPLE_SIZE:
        remaining = df[~df["Licence Number"].isin(test["Licence Number"])]
        extra = remaining.sample(SAMPLE_SIZE - len(test), random_state=SEED)
        test = pd.concat([test, extra])

    test = test.sort_values("Licence Number").reset_index(drop=True)

    test["Test Text"] = test.apply(
        lambda r: (
            f"Licence number: {r['Licence Number']}. "
            f"Operating name: {r['Operating Name']}. "
            f"Licence holder: {r['Licence Holder']}. "
            f"Premises address: {r['Premise Address 1']}, "
            f"{r['Premises Address Town']}."
        ),
        axis=1,
    )

    test["Ground Truth"] = test["Licence Number"]
    test["Label"] = "IDENTIFIER_CODE"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        raise FileExistsError(f"{OUTPUT} already exists; will not overwrite it")

    test.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Created {OUTPUT} with {len(test)} records")


if __name__ == "__main__":
    main()
