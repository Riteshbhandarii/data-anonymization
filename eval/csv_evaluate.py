import pandas as pd
from pathlib import Path

def evaluate_csv_leakage(original_path, anonymized_path):
    orig_df = pd.read_csv(original_path)
    anon_df = pd.read_csv(anonymized_path)

    # 1. Collect original sensitive values
    sensitive_fields = {"name", "email", "phone", "company", "iban", "date", "personal_id", "plate", "address"}
    original_sensitive = set()
    
    for col in orig_df.columns:
        if col.lower() in sensitive_fields:
            # Extract unique string values, dropping NaNs
            original_sensitive.update(orig_df[col].dropna().astype(str).unique())

    # 2. Collect all output values
    anonymized_values = set()
    for col in anon_df.columns:
        anonymized_values.update(anon_df[col].dropna().astype(str).unique())

    # 3. Check for leaks
    leaks = []
    for sensitive_value in original_sensitive:
        for output_value in anonymized_values:
            # Check if the original sensitive string appears in the output
            if sensitive_value.lower() in output_value.lower():
                leaks.append(sensitive_value)
                break

    leaks = sorted(set(leaks))
    
    print("=" * 70)
    print("CSV LEAKAGE EVALUATION")
    print("=" * 70)
    print(f"\nOriginal sensitive values: {len(original_sensitive)}")
    print(f"Sensitive values found in output: {len(leaks)}")
    
    if leaks:
        print("\n[LEAKS FOUND]")
        for leak in leaks:
            print(f"- {leak}")
    else:
        print("\nNo original sensitive values found.")

    # 4. Calculate Score
    if len(leaks) == 0:
        score = 4
    elif len(leaks) == 1:
        score = 3
    elif len(leaks) <= 3:
        score = 2
    elif len(leaks) <= 5:
        score = 1
    else:
        score = 0

    print("\n[RESULT]")
    print(f"Data Leakage Score: {score}/4")
    if score >= 3:
        print("Technical leakage test: PASS")
    else:
        print("Technical leakage test: FAIL")

if __name__ == "__main__":
    original_path = input("Enter ORIGINAL CSV file path: ").strip().strip('"')
    anonymized_path = input("Enter ANONYMIZED CSV file path: ").strip().strip('"')
    
    evaluate_csv_leakage(original_path, anonymized_path)
