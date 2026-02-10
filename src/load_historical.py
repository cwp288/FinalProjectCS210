

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'historical'

def preview_csv(file_path: Path, nrows: int = 5):
    print(f"\n=== Preview of {file_path.name} ===")
    try:

        df_sample = pd.read_csv(file_path, nrows=nrows)
        print("First rows:")
        print(df_sample)


        print("\nColumns:")
        print(df_sample.columns.tolist())


        df_full = pd.read_csv(file_path)
        print("\nInfo:")
        df_full.info()
        print("\nDescriptive statistics:")
        print(df_full.describe(include='all').T)

    except Exception as e:
        print(f"Error previewing {file_path.name}: {e}")

def main():
    if not DATA_DIR.exists():
        print(f"Directory {DATA_DIR} does not exist.")
        return

    csv_files = sorted(DATA_DIR.glob('*.csv'))
    if not csv_files:
        print(f"No CSV files found in {DATA_DIR}")
        return

    for csv_file in csv_files:
        preview_csv(csv_file)

if __name__ == '__main__':
    main()
