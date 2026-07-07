# parserf

**parserf** parses Earthquake Rupture Forecast (ERF) datasets into clean, structured Python
objects — fault subsections, rupture scenarios, parent faults, and background seismicity. It loads
and caches the raw USGS GeoJSON/CSV source files once and exposes enriched, ready-to-use tables and
view objects, so downstream consumers (such as PSHA source-model builders) can pull exactly the
faults and rupture/MFD information they need without re-deriving geometry, dimensions, or rollups.

## Supported Models

| `FaultModel` value      | Model                  |
| ----------------------- | ---------------------- |
| `FaultModel.NSHMP_2023` | USGS NSHM CONUS v6.0.0 |
| `FaultModel.UCERF3_31`  | UCERF3 fault model 3.1 |
| `FaultModel.UCERF3_32`  | UCERF3 fault model 3.2 |

## Installation

`parserf` requires Python `>=3.12`.

```bash
pip install parserf
```

For example notebooks, install the optional `examples` extra. It adds `ipykernel`,
`jupyterlab`, and `matplotlib`.

```bash
pip install "parserf[examples]"
```

In a `uv` project, you can add the package with:

```bash
uv add parserf
```

## User Guide

Consider the package architecture:

```
            FaultModelDataset            <- data layer: load + cache raw/derived tables
          (subsections, ruptures,           (the single source of truth)
           parent_ids, grid)
                       |
       +---------------+-----------------------------+
       |               |                             |
   queries.py      single-entity views        batch selection
  (get data by     FaultSubsection            ParentSelection  (many parents at once)
   lat/lon)        ParentFault                GridSelection    (background grid near site)
                       |
                each facade exposes:
                .data      -> attributes (no rupture info)
                .ruptures  -> participating ruptures + MFDs
```

Two recurring ideas:

- **Facade + view split.** `FaultSubsection` / `ParentFault` are thin facades that validate the
  index/name, then hand you `.data` (plain attributes) and `.ruptures` (rupture participation +
  MFDs). Use whichever half you need.
- **Queries are separate from data.** Spatial lookups live in `queries.py` and all take the dataset
  as their first argument — they don't live on the dataset object itself.

### 1. Load a dataset

```python
from parserf import FaultModel, FaultModelDataset

ds = FaultModelDataset(FaultModel.NSHMP_2023)

# Cached tables (each is a (Geo)DataFrame, lazily built and memoized):
ds.subsections       # every subsection: geometry, dip, depths, length/width/area, parent info
ds.ruptures          # rupture scenarios; subsection indices parsed into sets[int]
ds.parent_ids        # parent_name <-> parent_id map
ds.grid              # background gridded seismicity (lon, lat, style wts, rate per mag bin)
```

### 2. Typical queries

All query functions take `ds` first.

```python
from parserf import (
    get_nearest_subsection_index,
    get_subsections_list,
    get_parents_list,
    get_ruptures_near,
)

# Given a fault name, what is the parent fault id?
pid = ds.get_parent_fault_id(name="Little Lake")

# Given a location, what is the closest subsection id?
idx = get_nearest_subsection_index(ds, lat=35.77, lon=-117.60)

# Can I get a list of all the subsection or parent fault indices within a site radius?
nearby_subs = get_subsections_list(ds, lat=35.77, lon=-117.60, dist_km=50.0)
parent_ids  = get_parents_list(ds, lat=35.77, lon=-117.60, dist_km=50.0)

# What are all the rupture scenarios that the closest subsection participates in?
rups_near = get_ruptures_near(ds, lat=35.77, lon=-117.60, dist_km=50.0)
```

### 3. Look at one subsection

```python
from parserf import FaultSubsection

sub = FaultSubsection(ds, index=idx)

# .data — plain attributes
sub.data.name, sub.data.parent_name
sub.data.dip, sub.data.upper_depth_km, sub.data.lower_depth_km
sub.data.length_km, sub.data.width_km, sub.data.area_km2
sub.data.geometry          # shapely LineString of the surface trace
sub.data.geometry_3d       # shapely PolygonZ of the dipping surface (lon, lat, depth_km)

# .ruptures — participation + MFD
rups = sub.ruptures.participating_ruptures   # one row per rupture; .contributions = per-parent breakdown
mfd  = sub.ruptures.cumulative_mfd           # columns: magnitude, cumulative_rate
```

### 4. Look at one parent fault

`ParentFault` takes the **name** and resolves it internally.

```python
from parserf import ParentFault

flt = ParentFault(ds, name="Compton")

# .data
flt.data.subsections     # DataFrame of all child subsections
flt.data.geometry        # merged + oriented LineString (dips to the right as you walk along it)
flt.data.geometry_3d     # shapely PolygonZ of the dipping surface (lon, lat, depth_km)

# .ruptures
flt.ruptures.participating_ruptures   # one row per rupture; .contributions = per-parent breakdown
flt.ruptures.cumulative_mfds          # per child subsection: index, magnitude, cumulative_rate
```

Per-subsection scalars (dip, depths, areas) are intentionally **not** pre-aggregated at the parent
level — read them from `flt.data.subsections` and aggregate as you see fit (e.g., area-weighted).

### 5. Batch selection (the downstream-model path)

Find parents near a site, then pull all of them in **one** rupture-table scan.

```python
import pandas as pd

from parserf import ParentSelection, GridSelection

parent_ids = get_parents_list(ds, lat=35.77, lon=-117.60, dist_km=50.0)
sel = ParentSelection(ds, parent_ids)

sel.parents       # per-parent GeoDataFrame (indexed by parent_id): parent_name, geometry
sel.subsections   # all subsections for those parents (FULL extent — not radius-clipped)
sel.ruptures      # one row per rupture: m, rate, depth, dip, width, rake, geometry,
                  # length_km, area_km2, contributions

# Each rupture's `contributions` lists (parent_id, area_pct) for every parent it touches.
# To attribute rates to individual faults, explode that column into one row per (rupture, parent):
rups = sel.ruptures.explode("contributions")
rups[["parent_id", "area_pct"]] = pd.DataFrame(rups["contributions"].tolist(), index=rups.index)
rups["attributed_rate"] = rups["rate"] * rups["area_pct"] / 100.0   # full rate × that parent's area share

# Background seismicity near the same site (its own radius; grid extent may differ from faults)
gs = GridSelection(ds, lat=35.77, lon=-117.60, dist_km=100)
gs.grid           # grid points within 100 km, sorted nearest-first, with a dist_km column
```

## FAQ

**Why does `contributions` hold a list of tuples instead of one row per parent?**

Rupture tables are one row per rupture, and `rate` is the full rupture rate. `contributions` keeps
the per-parent area breakdown as `(parent_id, area_pct)` tuples. To get `(rupture, parent)` rows,
use `.explode("contributions")`, then attribute rates with `rate * area_pct / 100`.

**Why are some ruptures missing?**

`FaultModelDataset.ruptures` drops zero-rate ruptures when it builds the parsed rupture table.

## Data Development

### Original Data Sources

#### Faults

- [UCERF3](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/5.3-maint/active-crust/fault/CA/ucerf3)

- [nshm-conus-v6.0.0](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/6.0.0/active-crust/fault/wus-system/branch-avg)

#### Background grids

- [UCERF3](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/5.3-maint/active-crust/grid/grid-data?ref_type=heads)

- [nshm-conus-v6.0.0](https://code.usgs.gov/ghsc/nshmp/nshms/nshm-conus/-/tree/6.0.0/active-crust/grid/grid-data?ref_type=tags)

### Derived Data

- Parent fault information (`parent_id` and `parent_name`) is extracted from `sections.geojson` files.

## Documentation

Full API docs are built with Sphinx (Renku theme) and published on Read the Docs. To build them
locally, install the `docs` dependency group and run:

```bash
uv run --group docs sphinx-build -b html docs docs/_build/html
```

Then open `docs/_build/html/index.html`.

## Credits

Portions of this code were generated or refined with the assistance of AI tools. The concept and code architecture/design are the original work of the author.
