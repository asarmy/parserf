CRITICAL: Never run `python` or `python3` directly. Always use `uv run python` or `uv run <script>`.

## Project Overview

Parserf is a Python library for parsing Earthquake Rupture Forecast (ERF) datasets. It provides structured access to fault model data (fault subsections, rupture scenarios) from seismic hazard models (USGS NSHM CONUS v6.0.0, UCERF3 v3.1/3.2).

## Architecture

**`models.py`** — Data layer. `FaultModel` enum identifies datasets. `FaultModelDataset` (frozen dataclass) loads and caches raw data (`_sections`, `_ruptures`) and exposes enriched public properties: `subsections` (DataFrame, single source of truth for subsection attributes), `ruptures` (DataFrame with parsed index sets), `parent_ids`, `rake_frequencies`, `grid` (background gridded seismicity rates with lon, lat, faulting style weights, and annual rates per magnitude bin). `get_parent_fault_id(name=...)` resolves parent fault names to integer IDs. `_validate_index()` and `_validate_parent_id()` centralize existence checks.

**`queries.py`** — Spatial and rupture query functions. All take a `FaultModelDataset` as first argument: `get_nearest_subsection_index()`, `get_subsections_list()`, `get_parents_list()`, `get_ruptures_near()`. Keeps query behavior separate from data loading/caching (SRP).

**`selection.py`** — Batch selection classes. `ParentSelection(dataset, parent_ids)` provides efficient batch access to subsection attributes, parent summaries (style, oriented surface trace), and enriched ruptures for all subsections of the selected parents using a single rupture table scan. Designed for downstream consumers that need to build per-parent source models (e.g., PSHA). Composable with `queries.py`: use `get_parents_list()` to find parent IDs near a coordinate, then pass them to `ParentSelection`. `GridSelection(dataset, *, lat, lon, dist_km)` filters background gridded seismicity to points within a geodesic distance of a site, returning a DataFrame sorted nearest-first with an added `dist_km` column. Uses a separate radius from `ParentSelection` since the relevant grid extent may differ from the fault search radius.

**`subsection.py`** — View layer for individual subsections. `FaultSubsection` is the facade, exposing:

- `.data` → `FaultSubsectionData`: subsection attributes (name, dip, depth, geometry, area, etc.)
- `.ruptures` → `FaultSubsectionRuptures`: rupture participation queries, merged geometries, cumulative MFD

`FaultSubsectionRuptures` delegates to `_RuptureSet` for filtering and enrichment.

**`parent.py`** — View layer for parent faults. `ParentFault(dataset, name=...)` is the facade, exposing:

- `.data` → `ParentFaultData`: child subsection attributes as a DataFrame, faulting style
- `.ruptures` → `ParentFaultRuptures`: cumulative MFDs for all child subsections

`ParentFault` resolves name → `parent_id` once via `get_parent_fault_id()` and passes the int to child views. `ParentFaultData` and `ParentFaultRuptures` take `parent_id` (keyword-only int).

**`_utils.py`** — Private helpers and shared domain logic. `_parse_indices()` converts rupture index strings to sets of ints. `_merge_geometry()` combines subsection LineStrings into single/multi-line geometries. `_cumulative_mfd()` computes cumulative magnitude frequency distributions from rupture data. `_orient_trace()` applies the right-hand rule to orient a fault trace by dip direction. `_parent_surface_trace()` merges and orients subsection geometries into a parent fault trace. `_parent_style()` / `_parent_style_counts()` compute dominant faulting style from rake frequencies. `_RuptureSet` is a private class that encapsulates rupture filtering by subsection index overlap, geometry/dimension enrichment, and aggregate MFD computation — used internally by `FaultSubsectionRuptures`, `ParentFaultRuptures`, and `ParentSelection`. Produces an exploded rupture format: one row per (rupture, parent) pair with `parent_id` and `area_pct` columns. All parent contributions for each rupture are included (not just parents matching the target indices), so `area_pct` values sum to 100 per rupture — filter on `parent_id` to isolate specific parents. `per_subsection_mfds()` provides per-subsection cumulative MFDs without exposing internal state.

**Data flow**: Raw GeoJSON/CSV → `FaultModelDataset` (load + cache) → view objects query `subsections` → on-demand geometry merging and computed properties returned to user.

**Key patterns**: `@cached_property` for lazy eval; frozen dataclass for immutability; facade pattern separating data vs. rupture views; set-based index lookup for O(1) membership checks.

**Key dependencies**: geopandas, pandas, shapely, pyproj, numpy.

**Data directories**: `RawData/` (original GeoJSON/CSV), `DerivedData/` (versioned derived outputs).

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
