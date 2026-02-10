import pandas as pd
import sqlite3
from pathlib import Path

CSV_DIR      = Path(__file__).resolve().parent.parent / "data" / "historical"
SQLITE_PATH  = Path(__file__).resolve().parent.parent / "data" / "ancillary" / "FPA_FOD_20170508.sqlite"
SQLITE_TABLE = "Fires"


HIST_DATE_COL = "incident_start_date" 
ANC_DATE_COL  = "discovery_date"       

def load_csvs(csv_dir: Path) -> pd.DataFrame:
    df_list = []
    for csv_file in sorted(csv_dir.glob("*.csv")):
        df = pd.read_csv(csv_file, low_memory=False)
        df["source_file"] = csv_file.name
        df_list.append(df)
    combined = pd.concat(df_list, ignore_index=True)
    print(f"Loaded {len(df_list)} CSV files, total rows: {len(combined)}")
    return combined

def load_sqlite(sqlite_path: Path, table_name: str) -> pd.DataFrame:
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite file not found at {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    df = pd.read_sql(f"SELECT * FROM {table_name};", conn)
    conn.close()
    print(f"Loaded table `{table_name}` from SQLite, rows: {len(df)}")
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: c.strip().lower().replace(" ", "_"))

    for col in df.columns:
        if "date" in col or "time" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    before = len(df)
    df = df.drop_duplicates()
    print(f"Dropped {before - len(df)} duplicate rows")

    if {"latitude", "longitude"}.issubset(df.columns):
        before = len(df)
        df = df.dropna(subset=["latitude", "longitude"])
        print(f"Dropped {before - len(df)} rows with missing coordinates")

    if "brightness" in df.columns:
        before = len(df)
        df = df[(df["brightness"] >= 0) & (df["brightness"] <= 500)]
        print(f"Dropped {before - len(df)} rows with out-of-bounds brightness")

    return df

def main():
    #Load raw data
    df_hist_raw = load_csvs(CSV_DIR)
    df_anc_raw  = load_sqlite(SQLITE_PATH, SQLITE_TABLE)

    #Clean each
    df_hist = clean_dataframe(df_hist_raw)
    df_anc  = clean_dataframe(df_anc_raw)

    # Show available date columns
    print("\nDate-columns in CSVs:      ", [c for c in df_hist.columns if "date" in c])
    print("Date-columns in SQLite DB:", [c for c in df_anc.columns  if "date" in c])

    # Verify merge keys exist
    if HIST_DATE_COL not in df_hist.columns:
        raise KeyError(f"Expected '{HIST_DATE_COL}' in CSV data, but found: {df_hist.columns.tolist()}")
    if ANC_DATE_COL not in df_anc.columns:
        raise KeyError(f"Expected '{ANC_DATE_COL}' in SQLite data, but found: {df_anc.columns.tolist()}")

    # Merge on the matching date fields
    df_merged = pd.merge(
        df_hist,
        df_anc,
        how="left",
        left_on=HIST_DATE_COL,
        right_on=ANC_DATE_COL,
        suffixes=("_hist", "_fpa")
    )
    print(f"Merged datasets: resulting rows = {len(df_merged)}")

    # Save cleaned & merged output
    out_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "wildfires_cleaned.csv"
    df_merged.to_csv(out_file, index=False)
    print(f"\nCleaned & merged data saved to: {out_file}")

if __name__ == "__main__":
    main()
