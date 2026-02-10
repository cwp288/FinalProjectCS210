import os
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from meteostat import Point, Daily, Stations

PG_URI            = os.getenv(
    "PG_URI",
    "postgresql://postgres:soccer00@localhost:5432/wildfire_db"
)
ENGINE            = create_engine(PG_URI)

GRID_SQL = """
SELECT DISTINCT g.cell_id,
       ST_Y(ST_Centroid(g.geometry)) AS lat,
       ST_X(ST_Centroid(g.geometry)) AS lon
FROM grid_cells AS g
JOIN fire_hotspots_assigned AS h
  ON g.cell_id = h.cell_id;
"""

OUT_TABLE_WEATHER = "env_observations"

START_DATE = datetime(2015, 1, 1)
END_DATE   = datetime(2015, 12, 31)


def fetch_grid(engine):
    """Load active grid cells from PostGIS."""
    df = pd.read_sql(GRID_SQL, engine)
    logging.info(f"Loaded {len(df)} grid cells for ingestion.")
    return df


def ingest_weather(engine, grid, start, end):
    """Fetch daily weather via Meteostat and load into PostGIS with station fallback."""
    logging.info("Fetching daily weather with Meteostat…")
    table_created = False
    total_rows = 0

    for idx, row in grid.iterrows():
        cid, lat, lon = int(row.cell_id), float(row.lat), float(row.lon)
        logging.info(f"[{idx+1}/{len(grid)}] Processing cell {cid} at ({lat}, {lon})…")
        try:
            stations_df = Stations().nearby(lat, lon).fetch(5)
            logging.info(f"  Found {len(stations_df)} nearby stations for cell {cid}.")
        except Exception as e:
            logging.error(f"  Failed to fetch stations for cell {cid}: {e}")
            continue
        if stations_df.empty:
            logging.warning(f"  No Meteostat stations near cell {cid}.")
            continue

        data = None
        for station_idx, station_id in enumerate(stations_df.index):
            try:
                logging.info(f"Trying station {station_id} ({station_idx+1}/{len(stations_df)}) for cell {cid}…")
                data = Daily(station_id, start, end).fetch()
                if not data.empty:
                    logging.info(f"Success: Using station {station_id} for cell {cid}.")
                    break
                else:
                    logging.info(f"No data for station {station_id} (cell {cid}).")
            except Exception as e:
                logging.warning(f"Fetch failed for station {station_id} (cell {cid}) → {e}")

        if data is None or data.empty:
            logging.warning(f"  No weather data for cell {cid} from any nearby stations.")
            continue

        df = data.reset_index()
        df['cell_id'] = cid
        df = df.rename(columns={
            'time': 'date',
            'tmax': 'T2M_MAX',
            'tmin': 'T2M_MIN',
            'prcp': 'PRECTOT'
        })

        with engine.begin() as conn:
            if not table_created:
                conn.execute(text(f"DROP TABLE IF EXISTS {OUT_TABLE_WEATHER};"))
                df[['cell_id', 'date', 'T2M_MAX', 'T2M_MIN', 'PRECTOT']].to_sql(OUT_TABLE_WEATHER, conn, if_exists='replace', index=False)
                table_created = True
                logging.info(f"  Created table and wrote {len(df)} rows for cell {cid}.")
            else:
                df[['cell_id', 'date', 'T2M_MAX', 'T2M_MIN', 'PRECTOT']].to_sql(OUT_TABLE_WEATHER, conn, if_exists='append', index=False)
                logging.info(f"  Appended {len(df)} rows for cell {cid}.")
        total_rows += len(df)
        logging.info(f"  Finished cell {cid}, total weather rows written so far: {total_rows}.")

    if not table_created:
        logging.error("No weather data fetched; table was not created.")
        return

    logging.info(f"Loaded {total_rows} weather rows into `{OUT_TABLE_WEATHER}` (batch write mode).")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    logging.info("Starting environmental weather ingestion (Meteostat)…")

    grid = fetch_grid(ENGINE)
    if grid.empty:
        logging.error("Grid is empty; check your grid_cells and fire_hotspots_assigned tables.")
        return

    ingest_weather(ENGINE, grid, START_DATE, END_DATE)
    logging.info("Weather ETL complete.")

if __name__ == '__main__':
    main()