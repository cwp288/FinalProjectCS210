

import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text 


CSV_PATH   = Path(__file__).resolve().parent.parent / "data" / "processed" / "wildfires_cleaned.csv"
DB_PATH    = Path(__file__).resolve().parent.parent / "data" / "ancillary" / "wildfires_processed.db"
TABLE_NAME = "wildfires_cleaned"

def main():
    print(f"Loading CSV from {CSV_PATH}…")
    df = pd.read_csv(CSV_PATH, parse_dates=True, low_memory=False)
    print(f"Read {len(df)} rows and {len(df.columns)} columns.")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    print(f"Writing to SQLite database at {DB_PATH} (table: {TABLE_NAME})…")

    df.to_sql(TABLE_NAME, engine, if_exists="replace", index=False)
    print("Write complete!")

    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))  # wrap in text()
        count = result.scalar()  # fetch the single value
    print(f"Database table `{TABLE_NAME}` now has {count} rows.")

if __name__ == "__main__":
    main()
