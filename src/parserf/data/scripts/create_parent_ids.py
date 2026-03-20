"""Extract parent fault IDs from sections.geojson files.

For each sections.geojson in RawData subdirectories, extract the name and parent-id columns, derive
a parent_name by stripping trailing bracket indices, and save as a CSV in the corresponding
DerivedData subdirectory.

Usage
-----
Can be run from any directory:
    uv run python src/parserf/data/scripts/create_parent_ids.py

Examples
--------
From the project root:
    uv run python src/parserf/data/scripts/create_parent_ids.py

From the data directory:
    cd src/parserf/data && uv run python scripts/create_parent_ids.py

From the scripts directory:
    cd src/parserf/data/scripts && uv run python create_parent_ids.py
"""

from pathlib import Path

import geopandas as gpd

data_dir = Path(__file__).resolve().parent.parent
raw_dir = data_dir / "RawData"
derived_dir = data_dir / "DerivedData"

for folder in sorted(raw_dir.iterdir()):
    if not folder.is_dir() or folder.name.startswith("."):
        continue

    geojson_path = folder / "sections.geojson"
    if not geojson_path.exists():
        print(f"Warning: {geojson_path} not found")
        continue

    print(f"Processing {geojson_path}")

    gdf = gpd.read_file(geojson_path)

    parent_ids_df = gdf[["name", "parent-id"]].copy()
    parent_ids_df = parent_ids_df.rename(columns={"parent-id": "parent_id"})

    # Strip section index suffix like (0), (1), etc.
    parent_ids_df["name"] = (
        parent_ids_df["name"].str.replace(r"\s*\(\d+\)\s*$", "", regex=True).str.strip()
    )

    parent_ids_df = parent_ids_df.drop_duplicates()

    # Derive parent_name by stripping trailing bracket index like [1], [0]
    parent_ids_df["parent_name"] = (
        parent_ids_df["name"].str.replace(r"\s*\[\d+\]\s*$", "", regex=True).str.strip()
    )

    out_dir = derived_dir / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "parent_id.csv"
    parent_ids_df.to_csv(csv_path, index=False)

    print(f"✅ Saved {len(parent_ids_df)} records to {csv_path}")
