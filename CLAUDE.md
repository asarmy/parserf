CRITICAL: Never run `python` or `python3` directly. Always use `uv run python` or `uv run <script>`.

Common commands: `uv run pytest tests/ -q` (test), `uv run ruff check src/ tests/` (lint),
`uv build` (package), `uv run --group docs sphinx-build -b html docs docs/_build/html` (API docs,
Sphinx + Renku theme, published on Read the Docs via `.readthedocs.yaml`). Notebook tooling needs
the extra: `uv sync --extra examples`.

## Project Overview

Parserf is a Python library for parsing Earthquake Rupture Forecast (ERF) datasets. It provides structured access to fault model data (fault subsections, rupture scenarios) from seismic hazard models (USGS NSHM CONUS v6.0.0, UCERF3 v3.1/3.2).

## Architecture

**`models.py`** — Data layer. `FaultModel` enum identifies datasets. `FaultModelDataset` (frozen dataclass) loads and caches raw data (`_sections`, `_ruptures`) and exposes enriched public properties: `subsections` (DataFrame, single source of truth for subsection attributes), `ruptures` (DataFrame with parsed index sets; zero-rate ruptures are dropped, and the index preserves the ruptures.csv row number, which serves as the rupture id — so it has gaps), `parent_ids`, `grid` (background gridded seismicity rates with lon, lat, faulting style weights, and annual rates per magnitude bin). `get_parent_fault_id(name=...)` resolves parent fault names to integer IDs. `_validate_index()` and `_validate_parent_id()` centralize existence checks.

**`queries.py`** — Spatial and rupture query functions. All take a `FaultModelDataset` as first argument: `get_nearest_subsection_index()`, `get_subsections_list()`, `get_parents_list()`, `get_ruptures_near()`. Distances are true WGS84 geodesics to each subsection's map-view **footprint** (the dipping surface projected to the ground, via `dataset._subsection_footprints`/`_subsection_geometry_3d`) — not just the surface trace — so a site over the hanging wall of a dipping fault is in range even far from its trace; vertical faults are unaffected since their footprint collapses onto the trace. Nearest point on the footprint via `shapely.ops.nearest_points`, then `pyproj.Geod.inv` (do NOT reintroduce planar-degree shortcuts — degree distances are not monotonic with km). Keeps query behavior separate from data loading/caching (SRP).

**`selection.py`** — Batch selection classes. `ParentSelection(dataset, parent_ids)` (input IDs are de-duplicated preserving first-occurrence order) provides efficient batch access to subsection attributes, parent summaries (oriented surface trace), and enriched ruptures for all subsections of the selected parents using a single rupture table scan. Designed for downstream consumers that need to build per-parent source models (e.g., PSHA). Composable with `queries.py`: use `get_parents_list()` to find parent IDs near a coordinate, then pass them to `ParentSelection`. `GridSelection(dataset, *, lat, lon, dist_km)` filters background gridded seismicity to points within a geodesic distance of a site, returning a DataFrame sorted nearest-first with an added `dist_km` column. Uses a separate radius from `ParentSelection` since the relevant grid extent may differ from the fault search radius.

**`subsection.py`** — View layer for individual subsections. `FaultSubsection` is the facade, exposing:

- `.data` → `FaultSubsectionData`: subsection attributes (name, dip, depth, geometry, area, etc.) plus `geometry_3d` (dipping fault surface as a Shapely PolygonZ in lon/lat/depth_km)
- `.ruptures` → `FaultSubsectionRuptures`: rupture participation queries, merged geometries, cumulative MFD

`FaultSubsectionRuptures` delegates to `_RuptureSet` for filtering and enrichment.

**`parent.py`** — View layer for parent faults. `ParentFault(dataset, name=...)` is the facade, exposing:

- `.data` → `ParentFaultData`: child subsection attributes as a DataFrame, `geometry` (merged, oriented surface trace LineString — parallels `FaultSubsectionData.geometry`), and `geometry_3d` (merged dipping surface PolygonZ). Per-subsection scalars are not pre-aggregated at the parent level; consumers aggregate from `subsections`.
- `.ruptures` → `ParentFaultRuptures`: cumulative MFDs for all child subsections (ordered by ascending subsection index)

`ParentFault` resolves name → `parent_id` once via `get_parent_fault_id()` and passes the int to child views. `ParentFaultData` and `ParentFaultRuptures` take `parent_id` (keyword-only int).

**`_utils.py`** — Private helpers and shared domain logic. `_parse_indices()` converts rupture index strings to sets of ints. `_merge_geometry()` combines subsection LineStrings into single/multi-line geometries. `_cumulative_mfd()` computes cumulative magnitude frequency distributions from rupture data. `_orient_trace()` applies the right-hand rule to orient a fault trace by dip direction. `_parent_surface_trace()` merges and orients subsection geometries into a parent fault trace; raises `ValueError` if the subsections don't merge into a single contiguous LineString. `_parent_geometry()` builds a parent's oriented trace directly from its subsections DataFrame, computing an area-weighted dip/dip_direction internally just to drive orientation (not exposed as aggregates); used by `ParentFaultData.geometry` and `ParentSelection.parents`. 3D counterparts: `_surface_from_trace()` hangs a trace down-dip into a PolygonZ (lon, lat, depth_km); `_subsection_geometry_3d()` and `_parent_geometry_3d()` build the per-subsection and merged-parent dipping surfaces backing the `geometry_3d` properties. `_RuptureSet` is a private class that encapsulates rupture filtering by subsection index overlap, geometry/dimension enrichment, and aggregate MFD computation — used internally by `FaultSubsectionRuptures`, `ParentFaultRuptures`, and `ParentSelection`. `participating_ruptures` returns one row per rupture (indexed by rupture id) with a `contributions` column: a list of `(parent_id, area_pct)` tuples covering every parent the rupture touches (not just parents matching the target indices), summing to 100 per rupture; `rate` is the full rupture rate, so a parent's attributed rate is `rate * area_pct / 100`. Consumers explode to (rupture, parent) rows with `.explode("contributions")`. `per_subsection_mfds()` provides per-subsection cumulative MFDs (ascending subsection index) without exposing internal state.

**Data flow**: Raw GeoJSON/CSV → `FaultModelDataset` (load + cache) → view objects query `subsections` → on-demand geometry merging and computed properties returned to user.

**Key patterns**: `@cached_property` for lazy eval; frozen dataclass for immutability; facade pattern separating data vs. rupture views; set-based index lookup for O(1) membership checks.

**Key dependencies**: geopandas, pandas, shapely, pyproj, numpy.

**Data directories**: `RawData/` (original GeoJSON/CSV), `DerivedData/` (versioned derived outputs). Packaging is a whitelist: `MANIFEST.in` ships only the files `models.py` reads (per model: `parent_id.csv`, `sections.geojson`, `ruptures.csv`, and the grid CSV) — anything else under `data/` (e.g. `scripts/`, `rupture-set.json`) is excluded from wheels/sdists, so adding a new data dependency requires a matching `MANIFEST.in` line.

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

## Publishing to PyPI

Version is static in `pyproject.toml` (`[project] version`) — bump it manually before every
release. PyPI rejects re-uploading an existing version, so a stale version number will fail
the release. `1.0.0` is already published (first release, 2026-07-07).

Release procedure:

1. Bump `version` in `pyproject.toml`, commit, push to `main`.
2. Create a GitHub Release with tag `v<version>` (e.g. `v1.2.0`) and publish it.
3. `.github/workflows/release.yml` runs automatically: a `test` job (ruff + pytest) gates
   publishing — if tests fail, nothing is published. Then a guard step checks the release tag
   matches `uv version --short`, failing loudly if they diverge. Then `uv build` and
   `pypa/gh-action-pypi-publish` upload to PyPI via OIDC trusted publishing (no API
   token/secret; the PyPI trusted publisher is scoped to environment "Any", so the workflow
   declares no `environment:`).
4. The new tag also triggers Read the Docs via its GitHub webhook. An RTD Automation Rule
   (configured in the RTD dashboard, not in this repo) activates the new version and points
   `stable`/default at it — no GitHub Action involved.

`.github/workflows/CI.yml` runs ruff + pytest on every push to `main` and PR; it's what the
CI badge in `README.md` reflects.

Badges in `README.md` (PyPI version, downloads, CI, docs, coverage) only render once their
preconditions exist: first PyPI publish, first CI run, an RTD build, and — for the coverage
badge — the repo being public (private repos can't serve `raw.githubusercontent.com` images
through GitHub's image proxy, so `coverage.svg` embeds are broken while the repo is private).
