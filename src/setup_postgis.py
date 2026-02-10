
import os
from pathlib import Path

import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import box
from sqlalchemy import create_engine, text


PG_URI = os.getenv(
    "PG_URI",
    "postgresql://postgres:soccer00@localhost:5432/wildfire_db"
)

CSV_PATH       = Path(__file__).resolve().parent.parent / "data" / "processed" / "wildfires_cleaned.csv"
HOTSPOTS_TABLE = "fire_hotspots"
GRID_TABLE     = "grid_cells"
ASSIGNED_TABLE = "fire_hotspots_assigned"


CELL_SIZE_DEG = 0.01


def main():
    engine = create_engine(PG_URI)

    print(f"Reading cleaned CSV from {CSV_PATH}…")
    df = pd.read_csv(CSV_PATH, parse_dates=True, low_memory=False)
    print(f" → {len(df)} rows, {len(df.columns)} columns")

    if "longitude_hist" in df.columns and "latitude_hist" in df.columns:
        lon_col, lat_col = "longitude_hist", "latitude_hist"
    elif "longitude" in df.columns and "latitude" in df.columns:
        lon_col, lat_col = "longitude", "latitude"
    elif "longitude_fpa" in df.columns and "latitude_fpa" in df.columns:
        lon_col, lat_col = "longitude_fpa", "latitude_fpa"
    else:
        raise KeyError(
            "No suitable longitude/latitude columns found. "
            f"Available columns: {df.columns.tolist()}"
        )

    print(f"Using '{lon_col}' and '{lat_col}' for point geometry")

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326"
    ).dropna(subset=["geometry"])

    if gdf.empty:
        raise ValueError(
            "GeoDataFrame is empty after dropping null geometries. "
            "Please verify your lon/lat columns and data."
        )

    print(f"Writing {HOTSPOTS_TABLE} to PostGIS…")
    gdf.to_postgis(HOTSPOTS_TABLE, engine, if_exists="replace", index=False)

    print("Generating grid…")
    minx, miny, maxx, maxy = gdf.total_bounds
    nx = int(np.ceil((maxx - minx) / CELL_SIZE_DEG))
    ny = int(np.ceil((maxy - miny) / CELL_SIZE_DEG))

    cells, ids = [], []
    idx = 0
    for i in range(nx):
        for j in range(ny):
            cells.append(box(
                minx + i * CELL_SIZE_DEG,
                miny + j * CELL_SIZE_DEG,
                minx + (i + 1) * CELL_SIZE_DEG,
                miny + (j + 1) * CELL_SIZE_DEG
            ))
            ids.append(idx)
            idx += 1

    grid_gdf = gpd.GeoDataFrame(
        {"cell_id": ids},
        geometry=cells,
        crs="EPSG:4326"
    )
    print(f" → {len(grid_gdf)} cells")
    print(f"Writing {GRID_TABLE} to PostGIS…")
    grid_gdf.to_postgis(GRID_TABLE, engine, if_exists="replace", index=False)
    print("Joining hotspots → grid cells…")
    join_sql = f"""
    DROP TABLE IF EXISTS {ASSIGNED_TABLE};
    CREATE TABLE {ASSIGNED_TABLE} AS
    SELECT
      h.*,
      g.cell_id
    FROM
      {HOTSPOTS_TABLE} AS h
    JOIN
      {GRID_TABLE}     AS g
    ON
      ST_Contains(g.geometry, h.geometry);
    """
    with engine.begin() as conn:
        conn.execute(text(join_sql))

    print(f"Done! Table `{ASSIGNED_TABLE}` now has points with their `cell_id`.")


if __name__ == "__main__":
    main()
