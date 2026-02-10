import os
from pathlib import Path
import geopandas as gpd
from sqlalchemy import create_engine, text
from rasterstats import zonal_stats
import rasterio
import pandas as pd

PG_URI        = os.getenv("PG_URI", "")
ENGINE        = create_engine(PG_URI)
GRID_SQL      = "SELECT cell_id, geom FROM grid_cells;"
LC_RASTER     = Path("data/ancillary/nlcd_2016_landcover.tif")
SLOPE_RASTER  = Path("data/ancillary/slope_30m.tif")
OUT_TABLE     = "land_cover_summary"

def main():
    grid = gpd.read_postgis(GRID_SQL, ENGINE, geom_col="geom")

    stats_lc = zonal_stats(
        grid.geometry, str(LC_RASTER),
        stats=["majority"], categorical=False, geojson_out=False
    )
    df_lc = pd.DataFrame(stats_lc)
    df_lc["cell_id"] = grid["cell_id"]

    stats_slope = zonal_stats(
        grid.geometry, str(SLOPE_RASTER),
        stats=["mean"], geojson_out=False
    )
    df_slope = pd.DataFrame(stats_slope).rename(columns={"mean":"slope_mean"})
    df_slope["cell_id"] = grid["cell_id"]

    df = df_lc.merge(df_slope, on="cell_id")
    with ENGINE.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {OUT_TABLE};"))
        df.to_sql(OUT_TABLE, conn, if_exists="replace", index=False)
    print(f"Wrote land‐cover summary ({len(df)} cells) to `{OUT_TABLE}`")

if __name__ == "__main__":
    main()
