"""
Export participating ruptures of a parent fault to a space-delimited text file.

For each rupture that involves the named parent fault, writes a header line
``magnitude rate area_pct rake width npts`` followed by ``npts`` lines of ``lon lat`` pairs.
``rate`` is formatted in scientific notation with 5 decimals; magnitude, area_pct, rake, width, and
coordinates are fixed-decimal floats; npts is an integer.

Usage:

Run from any directory; output is written to ``<name>.txt`` in the cwd.

    uv run python export_parent_ruptures.py --model NSHMP_2023 --name "Compton"

"""

import argparse
import difflib
import sys
from pathlib import Path

from shapely import LineString, MultiLineString

from parserf import FaultModel, FaultModelDataset, ParentFault


def _coords(geom):
    """Yield (lon, lat) pairs from a LineString or MultiLineString."""
    if isinstance(geom, LineString):
        yield from geom.coords
    elif isinstance(geom, MultiLineString):
        for part in geom.geoms:
            yield from part.coords
    else:
        raise TypeError(f"unexpected geometry type: {type(geom).__name__}")


def _suggest(ds: FaultModelDataset, query: str) -> list[str]:
    """Suggest candidate parent fault names for a failed exact match."""
    names = ds.parent_ids["parent_name"]
    subs = names[names.str.contains(query, case=False, regex=False, na=False)]
    if not subs.empty:
        return sorted(subs.tolist())
    return difflib.get_close_matches(query, names.tolist(), n=5, cutoff=0.6)


def _export(ds: FaultModelDataset, name: str, *, tolerance: float) -> None:
    flt = ParentFault(ds, name=name)
    rups = flt.ruptures.participating_ruptures
    parent_only = rups[rups["parent_id"] == flt.data.parent_id]

    if tolerance > 0:
        parent_only = parent_only.assign(
            geometry=parent_only.geometry.simplify(tolerance, preserve_topology=False)
        )

    out_path = Path.cwd() / f"{name}.txt"
    with out_path.open("w") as f:
        for _, row in parent_only.iterrows():
            points = [(lon, lat) for lon, lat in _coords(row["geometry"])]
            npts = len(points)
            f.write(
                f"{row['m']:.4f} {row['rate']:.5e} "
                f"{row['area_pct'] / 100:.4f} {row['rake']:.0f} "
                f"{row['width']:.1f} {npts}\n"
            )
            for lon, lat in points:
                f.write(f"{lon:.6f} {lat:.6f}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export participating ruptures of a parent fault to a text file."
    )
    parser.add_argument("--model", required=True, choices=[m.name for m in FaultModel])
    parser.add_argument("--name", required=True)
    parser.add_argument(
        "--simplify",
        type=float,
        default=0.0001,
        help=(
            "Douglas-Peucker tolerance in degrees (~111 km/deg). 0 disables. "
            "Default 0.0001 (~10 m) removes near-collinear vertices."
        ),
    )
    args = parser.parse_args()

    ds = FaultModelDataset(FaultModel[args.model])

    try:
        _export(ds, args.name, tolerance=args.simplify)
    except ValueError:
        print(f"No parent fault named '{args.name}' in {args.model}.", file=sys.stderr)
        suggestions = _suggest(ds, args.name)
        if suggestions:
            print("Did you mean:", file=sys.stderr)
            for s in suggestions:
                print(f"  {s}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
