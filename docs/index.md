# parserf

**parserf** parses Earthquake Rupture Forecast (ERF) datasets into clean, structured Python
objects — fault subsections, rupture scenarios, parent faults, and background seismicity. It loads
and caches the raw USGS GeoJSON/CSV source files once and exposes enriched, ready-to-use tables and
view objects, so downstream consumers (such as PSHA source-model builders) can pull exactly the
faults and rupture/MFD information they need without re-deriving geometry, dimensions, or rollups.

## Supported models

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

In a `uv` project, you can add the package with:

```bash
uv add parserf
```

## Quickstart

```python
from parserf import FaultModel, FaultModelDataset, FaultSubsection, get_nearest_subsection_index

ds = FaultModelDataset(FaultModel.NSHMP_2023)

idx = get_nearest_subsection_index(ds, lat=35.77, lon=-117.60)
sub = FaultSubsection(ds, index=idx)

sub.data.name                          # subsection name
sub.ruptures.participating_ruptures    # ruptures involving this subsection
sub.ruptures.cumulative_mfd            # magnitude, cumulative_rate
```

See the {doc}`api` reference for the full public surface, and the example notebooks below for
worked, end-to-end walkthroughs of each layer (models, subsections, parent faults, and spatial
queries).

```{toctree}
:maxdepth: 1
:caption: Examples
:hidden:

examples/1-models
examples/2-subsections
examples/3-parents
examples/4-queries
```

```{toctree}
:maxdepth: 2
:caption: Reference
:hidden:

api
```
