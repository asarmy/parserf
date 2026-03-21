"""Compute fault dimension statistics by parent fault for each fault model.

For each fault model data directory:
- Load sections.geojson from RawData and parent_id.csv from DerivedData
- Convert geometry to EPSG:5070 for length calculations in meters
- Aggregate dimensions (length sum, dip/depth min/max/mean) by parent_id
- Merge with parent_name from parent_id.csv
- Save as dimensions.csv in the corresponding DerivedData subdirectory

Usage
-----
Can be run from any directory:
    uv run python src/parserf/data/scripts/create_dimensions.py

Examples
--------
From the project root:
    uv run python src/parserf/data/scripts/create_dimensions.py

From the data directory:
    cd src/parserf/data && uv run python scripts/create_dimensions.py

From the scripts directory:
    cd src/parserf/data/scripts && uv run python create_dimensions.py
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

data_dir = Path(__file__).resolve().parent.parent
raw_dir = data_dir / "RawData"
derived_dir = data_dir / "DerivedData"

for folder in sorted(raw_dir.iterdir()):
    if not folder.is_dir() or folder.name.startswith("."):
        continue

    sections_path = folder / "sections.geojson"
    parent_ids_path = derived_dir / folder.name / "parent_id.csv"

    if not sections_path.exists():
        print(f"Warning: {sections_path} not found, skipping {folder.name}")
        continue
    if not parent_ids_path.exists():
        print(f"Warning: {parent_ids_path} not found, skipping {folder.name}")
        continue

    print(f"Processing {folder.name}...")

    # Load data files
    sections = gpd.read_file(sections_path)
    parent_ids = pd.read_csv(parent_ids_path)

    # Convert to EPSG:5070 for length calculations (meters)
    sections_5070 = sections.to_crs("EPSG:5070")
    sections["length_meters"] = sections_5070.geometry.length

    # Aggregate by parent_id
    agg_funcs = {
        "length_meters": "sum",
        "dip": ["min", "max", "mean"],
        "upper-depth": ["min", "max", "mean"],
        "lower-depth": ["min", "max", "mean"],
    }
    stats = sections.groupby("parent-id").agg(agg_funcs)

    # Flatten column names
    stats.columns = [
        "length_meters",
        "dip_degrees_min",
        "dip_degrees_max",
        "dip_degrees_mean",
        "upper_depth_km_min",
        "upper_depth_km_max",
        "upper_depth_km_mean",
        "lower_depth_km_min",
        "lower_depth_km_max",
        "lower_depth_km_mean",
    ]
    stats = stats.reset_index()
    stats = stats.rename(columns={"parent-id": "parent_id"})

    # Round to 3 decimals
    for col in stats.columns:
        if col != "parent_id":
            stats[col] = stats[col].round(3)

    # Merge with parent_ids to get fault names
    stats = stats.merge(parent_ids[["parent_id", "parent_name"]], on="parent_id", how="left")

    # Reorder columns: parent_id, parent_name, then stats
    cols = ["parent_id", "parent_name"] + [
        c for c in stats.columns if c not in ["parent_id", "parent_name"]
    ]
    stats = stats[cols]

    # Save
    out_dir = derived_dir / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "dimensions.csv"
    stats.to_csv(output_path, index=False)

    print(f"Saved {len(stats)} records to {output_path}")
