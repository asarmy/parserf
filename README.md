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

- `FaultModelDataset` is the package's data access layer: it encapsulates each fault model and provides cached access to raw and derived tables such as sections, parent IDs, and ruptures. It internally consolidates per-subsection data (geometry, computed dimensions, and parent fault names) as the single source of truth for the view objects below.

- `FaultSubsection` is a thin facade that validates a subsection index exists in the dataset and exposes two view objects: `.data` and `.ruptures`.

- `FaultSubsectionData` is a dataset-backed view of a single subsection's local attributes (name, dip, depth, geometry, length, width, area, etc.), reading all values from the dataset's internal subsection cache.

- `FaultSubsectionRuptures` is a dataset-backed view of a single subsection's rupture participation, providing the `participating_ruptures` GeoDataFrame with merged geometries, lengths, areas, and parent area percentages.

# Credits

Portions of this code were generated or refined with the assistance of AI tools. The concept and code architecture/design are the original work of the author.
