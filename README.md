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

- `FaultModelDataset` is the package's data access layer: it encapsulates each fault model and provides cached access to raw and derived tables such as sections, parent IDs, and ruptures. It internally consolidates per-subsection data (geometry, computed dimensions, and parent fault names) as the single source of truth for the view objects below. It also provides identifier resolution methods: `nearest_index(lat, lon)` for subsection coordinates and `get_parent_id(name)` for parent fault names.

## Subsection Classes

- `FaultSubsection` is a thin facade that validates a subsection index exists in the dataset and exposes two view objects: `.data` and `.ruptures`. Use this when you need to access data and rupture information for a subsection in one instance.

- `FaultSubsectionData` is a dataset-backed view of a single subsection's basic attributes (name, dip, depth, geometry, length, width, area, etc.). Use this when you only need to access these attributes and do not need rupture information.

- `FaultSubsectionRuptures` is a dataset-backed view of a single subsection's rupture participation, providing the `participating_ruptures` GeoDataFrame with merged geometries, lengths, areas, and parent area percentages, and the `cumulative_mfd` DataFrame with magnitude exceedance rates. Use this when you only need to access rupture information and do not need basic attributes.

## Parent Fault Classes

- `ParentFault` is a thin facade that validates a parent fault name exists in the dataset and exposes two view objects: `.data` and `.ruptures`. Use this when you need to access data and rupture information for all subsections belonging to a parent fault. It accepts the parent fault name (e.g., `ParentFault(dataset, name="Airport Lake")`) and resolves it to an integer ID internally.

- `ParentFaultData` is a dataset-backed view of a parent fault's child subsection attributes (name, dip, depth, geometry, length, width, area, etc.) as a single DataFrame via the `subsections` property. It also provides faulting style information: `style` returns the dominant style (e.g., "normal", "strike-slip") and `style_counts` returns a DataFrame of style breakdowns by rupture count. Use this when you only need subsection attributes for a parent fault and do not need rupture information.

- `ParentFaultRuptures` is a dataset-backed view of rupture participation across a parent fault's subsections, providing `cumulative_mfds` — a DataFrame of cumulative magnitude frequency distributions for each child subsection with columns `index`, `magnitude`, and `cumulative_rate`. Use this when you only need rupture information for a parent fault.

# Credits

Portions of this code were generated or refined with the assistance of AI tools. The concept and code architecture/design are the original work of the author.
