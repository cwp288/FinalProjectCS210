import os
import pandas as pd
import requests
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "config" / ".env")
MAP_KEY = os.getenv("FIRMS_MAP_KEY")
if not MAP_KEY:
    raise RuntimeError("Missing FIRMS_MAP_KEY in environment")

def fetch_firms_mapkey(sensor: str,
                      bbox: str,
                      days: int) -> pd.DataFrame:
    """
    Pulls the last N days of detections for a given sensor & bbox,
    authenticated via MAP_KEY in the URL.
    """
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{MAP_KEY}/{sensor}/{bbox}/{days}"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df

if __name__ == "__main__":
    df = fetch_firms_mapkey(
        sensor="VIIRS_SNPP_NRT",
        bbox="-124.5,32.5,-114.0,42.0",
        days=7
    )
    out_path = Path(__file__).parent.parent / "data" / "firms_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
