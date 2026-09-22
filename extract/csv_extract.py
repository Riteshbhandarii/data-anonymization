from pathlib import Path
import pandas as pd

def inspect_csv(file_path):
    file_path = Path(file_path)

    print("=" * 60)
    print(f"FILE: {file_path.name}")
    print("=" * 60)

    try:
        df = pd.read_csv(file_path)
        print("\n[COLUMNS DETECTED]")
        for col in df.columns:
            print(f"- {col}")
            
        print(f"\nTotal Rows: {len(df)}")
        print("\n[DATA PREVIEW]")
        print(df.head(2))
    except Exception as e:
        print(f"Error reading CSV: {e}")

if __name__ == "__main__":
    file_path = input("Enter CSV file path: ").strip().strip('"')
    inspect_csv(file_path)