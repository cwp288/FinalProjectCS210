# Spatiotemporal Wildfire Risk Warning System

**Tech:** Python, PostgreSQL/PostGIS, Pandas, (XGBoost, LSTM)  
**Project:** CS210 Final Project — July 2025

## Overview
This project implements a **spatiotemporal wildfire ignition risk warning system** that forecasts **new ignition risk 24–72 hours ahead per 1 km² grid cell** to support:
- proactive crew positioning
- targeted risk warnings
- fast spatial/temporal querying for operational analysis

The system is built as a **modular Python ETL + PostGIS feature store + modeling pipeline**:
1) ingest/clean wildfire ignition events and align them to a uniform grid,
2) ingest real-time / historical weather and environmental covariates per grid cell,
3) build a supervised learning dataset using rolling-window features,
4) train/validate predictive models and evaluate out-of-region generalization.

> **Data note:** Large datasets, databases, and generated artifacts are intentionally excluded from this repo (`data/`, `.env`, model outputs).

---

## Key Features
- **Spatial forecasting at 1 km² resolution:** grid-based features per cell, enabling risk prediction and mapping.
- **Modular ETL design:** separate scripts for ingestion, preprocessing, PostGIS loading, feature engineering, and training.
- **Scalable PostGIS feature store:** designed to support fast queries via spatial + temporal indexing (GiST for geometry, B-Tree for time/IDs).
- **Forecast horizon support:** pipeline is designed for 24–72 hour prediction windows using rolling features and lagged covariates.
- **Modeling:** experiments include gradient boosted trees (XGBoost) and an LSTM sequence model with sliding-window validation.

---

## Repo Status (what’s included here)
This repository contains:
- PostGIS setup + grid assignment
- weather ingestion (current implementation uses **Meteostat**)
- modeling dataset construction with rolling window features
- a baseline model training script (RandomForest)

---

## Pipeline: What Each Script Does

### 1) Historical wildfire ingest + preprocessing
- `clean_preprocess.py`  
  Cleans and merges historical wildfire sources (CSV files + the FPA FOD SQLite fire database) and writes:
  - `data/processed/wildfires_cleaned.csv`

- `load_historical.py`  
  Quick schema/preview utility for CSVs in `data/historical/`.

- `load_to_db.py`  
  Loads `wildfires_cleaned.csv` into a local SQLite database (helpful for debugging / inspection).

### 2) PostGIS feature store + spatial grid assignment
- `setup_postgis.py`  
  Loads cleaned wildfire points into PostGIS, constructs a grid, and spatially assigns ignitions to grid cells:
  - `fire_hotspots`
  - `grid_cells`
  - `fire_hotspots_assigned`

### 3) Weather ingestion (real-time / historical covariates)
- `ingest_env_weather_meteostat.py`  
  Pulls daily weather per grid cell (using centroid-to-station fallback logic) and loads to PostGIS:
  - `env_observations`

### 4) Feature engineering + labeled dataset creation
- `prepare_model_dataset.py`  
  Creates a labeled dataset for ignition prediction by combining:
  - `env_observations` (covariates)
  - `fire_hotspots_assigned` (ignition dates / locations)

  Adds rolling-window features (e.g., 7-day rolling averages and precipitation sums) and outputs:
  - `model_dataset.csv` (ignored in git)

### 5) Modeling
- `train_baseline.py`  
  Baseline classification model using a RandomForest and evaluation metrics (ROC-AUC, classification report).

### Optional: Terrain / land cover enrichment
- `compute_landcover.py`  
  Optional raster enrichment that computes land cover majority class + mean slope per grid cell and stores:
  - `land_cover_summary`

### Optional: FIRMS hotspot fetch (API)
- `fetch_firms.py`  
  Fetches recent hotspots via the NASA FIRMS API (requires API key).

---

## Setup

### 1) Clone
```bash
git clone https://github.com/cwp288/FinalProjectCS210.git
cd FinalProjectCS210
