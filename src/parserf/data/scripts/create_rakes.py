"""Compute rake statistics by parent fault for each fault model.

For each fault model data directory:
- Load ruptures.csv and sections.geojson, and parse rupture indices
- Explode to get one row per subsection involved in each rupture
- Map subsections to parent_id via parent_id.csv (from DerivedData)
- Aggregate rake values (min, max) and preferred style of faulting by parent_id
- Save as rakes.csv in the corresponding DerivedData subdirectory

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
import numpy as np
import pandas as pd

data_dir = Path(__file__).resolve().parent.parent
raw_dir = data_dir / "RawData"
derived_dir = data_dir / "DerivedData"

# Hard-coded preferred style overrides
PREF_STYLE_OVERRIDES = {
    "nshm-conus-v6.0.0": {
        155: "strike-slip",  # Maacama
    },
    "fault-model-3.1": {
        23: "strike-slip",  # Burnt Mountain
        101: "reverse oblique",  # Great Valley 5 (Pittsburg - Kirby Hills)
        155: "strike-slip",  # Maacama
    },
    "fault-model-3.2": {
        23: "strike-slip",  # Burnt Mountain
        155: "strike-slip",  # Maacama
    },
}

style_priority = {
    "strike-slip": 0,
    "reverse": 1,
    "normal": 2,
    "reverse oblique": 3,
    "normal oblique": 4,
    "unknown": 5,
}


def parse_indices(indices_str: str) -> list[int]:
    """Parse earthquake rupture forecast scenario rupture index strings.

    Converts strings like "2:0-1127:1126" into lists of integers.

    Args:
        indices_str: String representation of one or multiple ranges.

    Returns:
        Expansion of all indices implied by indices_str.
    """
    chunks = indices_str.split("-")
    indices_list = []
    for chunk in chunks:
        chunk = chunk.strip()
        if ":" in chunk:
            start_str, end_str = chunk.split(":")
            start, end = int(start_str), int(end_str)
            xmin, xmax = min(start, end), max(start, end)
            indices_list.extend(np.arange(xmin, xmax + 1).tolist())
        else:
            indices_list.append(int(chunk))
    return indices_list


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
        print(f"❌ Warning: {ruptures_path} not found, skipping {folder.name}")
        continue
    if not sections_path.exists():
        print(f"❌ Warning: {sections_path} not found, skipping {folder.name}")
        continue
    if not parent_ids_path.exists():
        print(f"❌ Warning: {parent_ids_path} not found, skipping {folder.name}")
        continue

    print(f"Processing {folder.name}...")

    # Load data files
    ruptures = pd.read_csv(ruptures_path)
    sections = gpd.read_file(sections_path)
    parent_ids = pd.read_csv(parent_ids_path)

    # Parse indices
    ruptures["parsed_indices"] = ruptures["indices"].apply(parse_indices)

    # Explode ruptures by subsections
    r = ruptures.copy()
    r["subsection_idx"] = r["parsed_indices"]
    e = r.explode("subsection_idx", ignore_index=True)

    # Map to parent_id
    subsection_to_parent = sections.set_index("index")["parent-id"].to_dict()
    e["parent_id"] = e["subsection_idx"].map(subsection_to_parent)

    # Classify style for each rupture scenario
    e["style"] = e["rake"].apply(classify_rake)

    # Aggregate by parent_id
    rake_stats = e.groupby("parent_id")["rake"].agg(["min", "max"])
    rake_stats.columns = ["min_rake", "max_rake"]
    rake_stats = rake_stats.reset_index()

    # Round to int
    rake_stats["min_rake"] = rake_stats["min_rake"].round(0).astype(int)
    rake_stats["max_rake"] = rake_stats["max_rake"].round(0).astype(int)

    # Classify style of faulting based on min and max rake
    rake_stats["min_rake_style"] = rake_stats["min_rake"].apply(classify_rake)
    rake_stats["max_rake_style"] = rake_stats["max_rake"].apply(classify_rake)

    # Calculate average dip per parent_id
    avg_dip = sections.groupby("parent-id")["dip"].mean().to_dict()

    def get_pref_style(group, parent_id, folder_name):
        """Get most common style with tie-breaking by priority.

        If average dip <= 70 degrees, ignore strike-slip to capture obliquity.
        """
        # Hard override for a couple of cases that produce errors otherwise
        folder_overrides = PREF_STYLE_OVERRIDES.get(folder_name, {})
        if parent_id in folder_overrides:
            return folder_overrides[parent_id]

        counts = group.value_counts()

        # If dip <= 70, filter out strike-slip
        if avg_dip.get(parent_id, 90) <= 70:
            counts = counts.drop("strike-slip", errors="ignore")

        if counts.empty:
            return ""

        max_count = counts.max()
        tied_styles = counts[counts == max_count].index.tolist()
        # Sort by priority and return first
        tied_styles.sort(key=lambda s: style_priority.get(s, 99))
        return tied_styles[0]

    pref_styles = (
        e.groupby("parent_id")["style"]
        .apply(lambda g: get_pref_style(g, g.name, folder.name))
        .reset_index()
    )
    pref_styles.columns = ["parent_id", "pref_style"]

    # Merge pref_style into rake_stats
    rake_stats = rake_stats.merge(pref_styles, on="parent_id", how="left")

    # Merge with parent_ids to get fault names
    rake_stats = rake_stats.merge(
        parent_ids[["parent_id", "parent_name"]], on="parent_id", how="left"
    )

    # Reorder columns: parent_id, parent_name, stats, styles
    rake_stats = rake_stats[
        [
            "parent_id",
            "parent_name",
            "min_rake",
            "max_rake",
            "min_rake_style",
            "max_rake_style",
            "pref_style",
        ]
    ]

    # Save
    out_dir = derived_dir / folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / "rakes.csv"
    rake_stats.to_csv(output_path, index=False)

    print(f"✅ Saved {len(rake_stats)} records to {output_path}")
