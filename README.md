# parserf

Library for parsing earthquake rupture forecast (ERF) datasets.

# Data Development

## Original Data Sources

- [UCERF3](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/5.3-maint/active-crust/fault/CA/ucerf3)

- [nshm-conus-v6.0.0](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/6.0.0/active-crust/fault/wus-system/branch-avg)

## Derived Data

- Parent fault information (`parent_id` and `parent_name`) is extracted from `sections.geojson` files.
- Rake frequency counts are based on `ruptures.csv` files for each parent fault and are converted to styles using the following convention:
  - `strike-slip`: from -20° to 20°, from 160° to 180°, and from -180° to -160°
  - `reverse oblique`: from 20° to 70° and from 110° to 160°
  - `reverse`: from 70° to 110°
  - `normal oblique`: from -160° to -110° and from -70° to -20°
  - `normal`: from -110° to -70°

# Code Architecture

## Data Layer

- `FaultModelDataset` (`models.py`) is the data access layer: it encapsulates each fault model and provides cached access to raw and derived tables (`subsections`, `ruptures`, `parent_ids`, `rake_frequencies`). It internally consolidates per-subsection data (geometry, computed dimensions, and parent fault names) as the single source of truth for the view and query layers below. It also provides `get_parent_fault_id(name=...)` for resolving parent fault names to integer IDs.

## Queries

- `queries.py` contains spatial query functions that all take a `FaultModelDataset` as their first argument: `get_nearest_subsection_index()`, `get_subsections_list()`, `get_parents_list()`, and `get_ruptures_near()`.

## Single-Entity Views

- `FaultSubsection` (`subsection.py`) is a thin facade that validates a subsection index exists in the dataset and exposes two view objects: `.data` and `.ruptures`. Use this when you need to access data and rupture information for a subsection in one instance.

- `FaultSubsectionData` is a dataset-backed view of a single subsection's basic attributes (name, dip, depth, geometry, length, width, area, etc.). Use this when you only need to access these attributes and do not need rupture information.

- `FaultSubsectionRuptures` is a dataset-backed view of the ruptures that a single subsection participates in, including a breakdown of the contribution of each parent fault (by area, in percent) to the rupture scenario. The view is provided with the `participating_ruptures` GeoDataFrame in exploded form (one row per rupture-parent pair with `parent_id` and `area_pct` columns), and a `cumulative_mfd` DataFrame with magnitude exceedance rates for the subsection. Use this when you only need to access rupture information and do not need basic attributes.

- `ParentFault` (`parent.py`) is a thin facade that validates a parent fault name exists in the dataset and exposes two view objects: `.data` and `.ruptures`. Use this when you need to access data and rupture information for all subsections belonging to a parent fault. It accepts the parent fault name (e.g., `ParentFault(dataset, name="Airport Lake")`) and resolves it to an integer ID internally.

- `ParentFaultData` is a dataset-backed view of a parent fault's child subsection attributes (name, dip, depth, geometry, length, width, area, etc.) as a single DataFrame via the `subsections` property. It also provides faulting style information: `style` returns the dominant style (e.g., "normal", "strike-slip") and `style_counts` returns a DataFrame of style breakdowns by rupture count. It also provides a merged, oriented `surface_trace` LineString, oriented such that dip direction is on the right when you progress along the coordinates. Use this when you only need subsection attributes for a parent fault and do not need rupture information.

- `ParentFaultRuptures` is a dataset-backed view of the ruptures that any subsection of the parent fault participates in, including a breakdown of the contribution of each parent fault (by area, in percent) to the rupture scenario. The view is provided with `participating_ruptures` in exploded form and `cumulative_mfds` provides a DataFrame of cumulative magnitude frequency distributions for each child subsection with columns `index`, `magnitude`, and `cumulative_rate`. Use this when you only need rupture information for a parent fault.

## Batch Parent Fault Selection

- `ParentSelection` (`selection.py`) provides efficient batch access to parent fault data and ruptures. It takes a dataset and a list of parent fault IDs (e.g., from `get_parents_list()`), and exposes:
  - `.subsections` — all subsections for the selected parents (full extent)
  - `.parents` — per-parent summary GeoDataFrame with `style` and `geometry` (oriented surface trace)
  - `.ruptures` — enriched GeoDataFrame in exploded form: one row per (rupture, parent) pair with `parent_id` and `area_pct` columns. The `rate` column is the full rupture rate; multiply by `area_pct / 100` for the parent-attributed rate. All parent contributions for each rupture are included (not just selected parents), so `area_pct` values sum to 100 per rupture.

# Credits

Portions of this code were generated or refined with the assistance of AI tools. The concept and code architecture/design are the original work of the author.
