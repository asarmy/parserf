"""Create a rake frequency table for each parent fault.

For each fault model data directory:
- Load ruptures.csv and sections.geojson, and parse rupture indices
- Explode to get one row per subsection involved in each rupture
- Map subsections to parent_id via sections.geojson parent-id field
- Classify each rake angle into a style of faulting
- Map parent_id to parent_name via parent_id.csv (from DerivedData)
- Aggregate by (parent_id, parent_name, rake, style) with occurrence counts
- Save as rake_frequencies.csv in the corresponding DerivedData subdirectory

Usage
-----
Can be run from any directory:
    uv run python src/parserf/data/scripts/create_rakes.py

Examples
--------
From the project root:
    uv run python src/parserf/data/scripts/create_rakes.py

From the data directory:
    cd src/parserf/data && uv run python scripts/create_rakes.py

From the scripts directory:
    cd src/parserf/data/scripts && uv run python create_rakes.py
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from parserf.utils import parse_indices

data_dir = Path(__file__).resolve().parent.parent
raw_dir = data_dir / "RawData"
derived_dir = data_dir / "DerivedData"


def classify_rake(rake: float) -> str:
    """Classify style of faulting based on rake angle.

    Args:
        rake: Rake angle in degrees.

    Returns:
        Style of faulting classification.
    """
    # Normalize rake into [-180, 180)
    rake = ((rake + 180) % 360) - 180

    ranges = [
        ((-20, 20), "Strike-slip"),
        ((20, 70), "Reverse oblique"),
        ((70, 110), "Reverse"),
        ((110, 160), "Reverse oblique"),
        ((160, 180), "Strike-slip"),
        ((-180, -160), "Strike-slip"),
        ((-160, -110), "Normal oblique"),
        ((-110, -70), "Normal"),
        ((-70, -20), "Normal oblique"),
    ]

    for (low, high), label in ranges:
        if low <= rake < high:
            return label.lower()

    return "unknown"


for folder in sorted(raw_dir.iterdir()):
    if not folder.is_dir() or folder.name.startswith("."):
        continue

    ruptures_path = folder / "ruptures.csv"
    sections_path = folder / "sections.geojson"
    parent_ids_path = derived_dir / folder.name / "parent_id.csv"

    if not ruptures_path.exists():
        print(f"Warning: {ruptures_path} not found, skipping {folder.name}")
        continue
    if not sections_path.exists():
        print(f"Warning: {sections_path} not found, skipping {folder.name}")
        continue
    if not parent_ids_path.exists():
        print(f"Warning: {parent_ids_path} not found, skipping {folder.name}")
        continue

    print(f"Processing {folder.name}...")

    # Load data files
    ruptures = pd.read_csv(ruptures_path)
    sections = gpd.read_file(sections_path)
    parent_ids = pd.read_csv(parent_ids_path)

    # Parse indices and explode to one row per subsection per rupture
    ruptures["parsed_indices"] = ruptures["indices"].apply(parse_indices)
    exploded = ruptures.explode("parsed_indices", ignore_index=True)

    # Map subsection index to parent_id via sections.geojson
    subsection_to_parent = sections.set_index("index")["parent-id"].to_dict()
    exploded["parent_id"] = exploded["parsed_indices"].map(subsection_to_parent)

    # Round rakes to nearest integer and classify style of faulting
    exploded["rake"] = exploded["rake"].round(0).astype(int)
    exploded["style"] = exploded["rake"].apply(classify_rake)

    # Map parent_id to parent_name
    parent_id_to_name = parent_ids.set_index("parent_id")["parent_name"].to_dict()
    exploded["parent_name"] = exploded["parent_id"].map(parent_id_to_name)

    # Aggregate to frequency table
    result = (
        exploded.groupby(["parent_id", "parent_name", "rake", "style"])
        .size()
        .reset_index(name="count")
    )

    # Save
    out_dir = derived_dir / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "rake_frequencies.csv"
    result.to_csv(output_path, index=False)

    print(f"Saved {len(result)} records to {output_path}")
