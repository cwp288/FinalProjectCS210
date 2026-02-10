import logging
import pandas as pd
from sqlalchemy import create_engine, inspect

PG_URI = "postgresql://postgres:soccer00@localhost:5432/wildfire_db"
ENGINE = create_engine(PG_URI)

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger()

    logger.info("Inspecting fire_hotspots_assigned schema…")
    insp = inspect(ENGINE)
    for col in insp.get_columns("fire_hotspots_assigned"):
        logger.info(f" • {col['name']}: {col['type']}")

    logger.info("Loading weather observations…")
    env = pd.read_sql(
        "SELECT * FROM env_observations;",
        ENGINE,
        parse_dates=["date"],
    ).assign(cell_id=lambda df: df.cell_id.astype(int))
    logger.info(f"Loaded {len(env)} rows; columns: {env.columns.tolist()}")

    logger.info("Loading raw fire dates…")
    hot_raw = pd.read_sql(
        "SELECT cell_id, date FROM fire_hotspots_assigned;",
        ENGINE,
    )
    hot_raw["date_int"] = pd.to_numeric(hot_raw["date"], errors="coerce")
    hot_raw = hot_raw.dropna(subset=["date_int"])
    hot_raw["date_int"] = hot_raw["date_int"].astype(int)
    hot_raw["burn_date"] = pd.to_datetime(hot_raw["date_int"], format="%Y%m%d", errors="coerce")
    hot = (
        hot_raw
        .dropna(subset=["burn_date"])    
        .loc[:, ["cell_id", "burn_date"]]  
        .assign(cell_id=lambda df: df.cell_id.astype(int))
    )
    logger.info(f"Prepared {len(hot)} burn events; columns: {hot.columns.tolist()}")

    logger.info("Merging to label burned vs. non-burned…")
    df = (
        env
        .merge(
            hot.assign(burned=1),
            left_on=["cell_id", "date"],
            right_on=["cell_id", "burn_date"],
            how="left"
        )
        .drop(columns=["burn_date"])
        .fillna({"burned": 0})
    )
    df["burned"] = df["burned"].astype(int)

    logger.info(f"After merge, columns: {df.columns.tolist()}")
    if "date" not in df.columns:
        raise KeyError("`date` column missing after merge; found: " + repr(df.columns.tolist()))
    logger.info("Sorting and computing 7-day rolling mean of T2M_MAX…")
    df = df.sort_values(["cell_id", "date"])
    df["t2m_max_7d"] = (
        df.groupby("cell_id")["T2M_MAX"]
          .transform(lambda s: s.rolling(7, min_periods=1).mean())
    )
    logger.info("Computing additional rolling features…")
    df["t2m_min_7d"]    = df.groupby("cell_id")["T2M_MIN"]   .transform(lambda s: s.rolling(7, min_periods=1).mean())
    df["precip_7d"]     = df.groupby("cell_id")["PRECTOT"]   .transform(lambda s: s.rolling(7, min_periods=1).sum())

    if "RH2M" in df.columns:
        df["rh2m_7d_mean"] = df.groupby("cell_id")["RH2M"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    else:
        print("Warning: RH2M column not found, skipping rh2m_7d_mean feature.")
        logger.warning("RH2M column not found, skipping rh2m_7d_mean feature.")

    if "WS2M" in df.columns:
        df["ws2m_7d_max"] = df.groupby("cell_id")["WS2M"].transform(lambda s: s.rolling(7, min_periods=1).max())
    else:
        print("Warning: WS2M column not found, skipping ws2m_7d_max feature.")
        logger.warning("WS2M column not found, skipping ws2m_7d_max feature.")

    logger.info("Preview of final DataFrame:")
    print(df.head())
    df.to_csv("model_dataset.csv", index=False)
    logger.info(
        "Wrote model_dataset.csv: %d rows, dates %s→%s, burned sum %d",
        len(df), df.date.min().date(), df.date.max().date(), df.burned.sum()
    )

if __name__ == "__main__":
    main()
