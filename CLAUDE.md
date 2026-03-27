CRITICAL: Never run `python` or `python3` directly. Always use `uv run python` or `uv run <script>`.

## Project Overview

Parserf is a Python library for parsing Earthquake Rupture Forecast (ERF) datasets. It provides
structured access to fault model data (fault subsections, rupture scenarios) from seismic hazard
models (USGS NSHM CONUS v6.0.0, UCERF3 v3.1/3.2).

## Architecture

**`models.py`** — Data layer. `FaultModel` enum identifies datasets. `FaultModelDataset` (frozen
dataclass) loads and caches sections (GeoDataFrame), parent_ids (DataFrame), and ruptures
(DataFrame) from GeoJSON/CSV files. `_subsection_table` is the single cached source of truth.

**`subsection.py`** — View layer. `FaultSubsection` is the main entry point, exposing:

- `.data` → `FaultSubsectionData`: subsection attributes (name, dip, depth, geometry, area, etc.)
- `.ruptures` → `FaultSubsectionRuptures`: rupture participation queries, merged geometries,
  parent contribution percentages

**`utils.py`** — `parse_indices()` converts rupture index strings ("2:0-1127:1126") to sets of
ints. `merge_geometry()` combines subsection LineStrings into single/multi-line geometries.

**Data flow**: Raw GeoJSON/CSV → `FaultModelDataset` (load + cache) → view objects query
`_subsection_table` → on-demand geometry merging and computed properties returned to user.

**Key patterns**: `@cached_property` for lazy eval; frozen dataclass for immutability; facade
pattern separating data vs. rupture views; set-based index lookup for O(1) membership checks.

**Key dependencies**: geopandas, pandas, shapely, pyproj, numpy/scipy.

**Data directoriess**: `RawData/` (original GeoJSON/CSV), `DerivedData/` (versioned derived
outputs).

Use Google style docstrings. Line length is 99.

For scripts, include module docstrings in this format (line length is 99):
"""
Create a database table, if it does not exist, and upsert CSV data into it.

This script performs the following steps:

1. Optionally backs up the current database before making changes.
2. Loads a SQLAlchemy ORM class by its table or class name.
3. Validates the existence and format of the provided CSV file.
4. Creates the corresponding database table if it doesn't exist.
5. Performs an "upsert" operation: inserts new rows or updates existing ones.

## Usage

Run this script from the project root directory:
uv run python dbtools/import_table.py <table_name> <csv_path> <description> [--backup]

## Example

    uv run python dbtools/import_table.py uscs data/uscs.csv "initial USCS data import"
    uv run python dbtools/import_table.py gradation_summary data/gradation.csv "Q4 lab results" --backup

"""
