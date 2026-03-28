CRITICAL: Never run `python` or `python3` directly. Always use `uv run python` or `uv run <script>`.

## Project Overview

Parserf is a Python library for parsing Earthquake Rupture Forecast (ERF) datasets. It provides
structured access to fault model data (fault subsections, rupture scenarios) from seismic hazard
models (USGS NSHM CONUS v6.0.0, UCERF3 v3.1/3.2).

## Architecture

**`models.py`** — Data layer. `FaultModel` enum identifies datasets. `FaultModelDataset` (frozen
dataclass) loads and caches sections (GeoDataFrame), parent_ids (DataFrame), and ruptures
(DataFrame) from GeoJSON/CSV files. `_subsection_table` is the single cached source of truth.
`get_parent_id(name=...)` resolves parent fault names to integer IDs.
`nearest_index(lat=..., lon=...)` resolves coordinates to subsection indices.

**`subsection.py`** — View layer for individual subsections. `FaultSubsection` is the facade,
exposing:

- `.data` → `FaultSubsectionData`: subsection attributes (name, dip, depth, geometry, area, etc.)
- `.ruptures` → `FaultSubsectionRuptures`: rupture participation queries, merged geometries,
  parent contribution percentages, cumulative MFD

`FaultSubsectionRuptures` uses layered cached properties: `_participating_ruptures` (cheap filter)
is the shared foundation; `cumulative_mfd` reads it without triggering geometry merging;
`participating_ruptures` copies and enriches it with geometries/dimensions on demand.

**`parent.py`** — View layer for parent faults. `ParentFault(dataset, name=...)` is the facade,
exposing:

- `.data` → `ParentFaultData`: child subsection attributes as a DataFrame, faulting style
- `.ruptures` → `ParentFaultRuptures`: cumulative MFDs for all child subsections

`ParentFault` resolves name → `parent_id` once via `get_parent_id()` and passes the int to child
views. `ParentFaultData` and `ParentFaultRuptures` take `parent_id` (keyword-only int).

**`utils.py`** — Private helpers: `_parse_indices()` converts rupture index strings to sets of
ints. `_merge_geometry()` combines subsection LineStrings into single/multi-line geometries.
`_cumulative_mfd()` computes cumulative magnitude frequency distributions from rupture data.

**Data flow**: Raw GeoJSON/CSV → `FaultModelDataset` (load + cache) → view objects query
`_subsection_table` → on-demand geometry merging and computed properties returned to user.

**Key patterns**: `@cached_property` for lazy eval; frozen dataclass for immutability; facade
pattern separating data vs. rupture views; set-based index lookup for O(1) membership checks.

**Key dependencies**: geopandas, pandas, shapely, pyproj, numpy/scipy.

**Data directoriess**: `RawData/` (original GeoJSON/CSV), `DerivedData/` (versioned derived
outputs).

## Documentation requirements

Use Google style docstrings.

For scripts, include module docstrings in this format (line length is 99):
"""
Create a database table, if it does not exist, and upsert CSV data into it.

This script performs the following steps:

1. Optionally backs up the current database before making changes.
2. Loads a SQLAlchemy ORM class by its table or class name.
3. Validates the existence and format of the provided CSV file.
4. Creates the corresponding database table if it doesn't exist.
5. Performs an "upsert" operation: inserts new rows or updates existing ones.

Usage:

Run this script from the project root directory:
uv run python dbtools/import_table.py <table_name> <csv_path> <description> [--backup]

Example:

    uv run python dbtools/import_table.py uscs data/uscs.csv "initial USCS data import"
    uv run python dbtools/import_table.py gradation_summary data/gradation.csv "Q4 lab results" --backup

"""

## Tests

Add tests only when they are materially useful: they should specify intended behavior, catch plausible regressions, or document important edge cases. Skip low-value assertions written just to appear thorough.
