"""Private utility functions and internal classes for parserf data processing."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from shapely import LineString, MultiLineString, Polygon
from shapely.ops import linemerge

_GEOD = Geod(ellps="WGS84")


def _parse_indices(indices_str: str) -> set[int]:
    """Parse earthquake rupture forecast scenario rupture index strings.

    Converts strings like "2:0-1127:1126" into sets of integers like "{0, 1, 2, 1126, 1127}".

    Args:
        indices_str: String representation of one or multiple ranges.

    Returns:
        Set of all indices implied by indices_str.
    """
    chunks = indices_str.split("-")
    indices = set()
    for chunk in chunks:
        chunk = chunk.strip()
        if ":" in chunk:
            start_str, end_str = chunk.split(":")
            start, end = int(start_str), int(end_str)
            xmin, xmax = min(start, end), max(start, end)
            indices.update(range(xmin, xmax + 1))
        else:
            indices.add(int(chunk))
    return indices


def _merge_geometry(parsed_indices, index_to_geom):
    """Merge fault subsection geometries into a single line geometry.

    Args:
        parsed_indices: Set of subsection indices for a rupture.
        index_to_geom: Dict mapping subsection index to its LineString geometry.

    Returns:
        A LineString (if sections connect) or MultiLineString (if they don't), or None if no
        geometries found.
    """
    geoms = [index_to_geom[i] for i in sorted(parsed_indices) if i in index_to_geom]
    if len(geoms) == 0:
        return None
    if len(geoms) == 1:
        return geoms[0]
    return linemerge(MultiLineString(geoms))


def _surface_from_trace(
    coords, upper_depths, lower_depths, dips, dip_directions
) -> Polygon | None:
    """Build a dipping fault surface as a PolygonZ from a surface trace.

    Each trace vertex is placed at its upper seismogenic depth to form the top edge, then offset
    down-dip (geodesically, along the dip-direction azimuth) and dropped to the lower depth to form
    the bottom edge. The top edge and reversed bottom edge are stitched into a single closed ring.

    The down-dip horizontal offset is ``H = (lower - upper) / tan(dip)``; vertical faults
    (dip within 1 degree of 90) use ``H = 0``. The surface is generally non-planar.

    Args:
        coords: Sequence of (lon, lat) surface-trace vertices.
        upper_depths: Per-vertex upper seismogenic depth in km.
        lower_depths: Per-vertex lower seismogenic depth in km.
        dips: Per-vertex dip angle in degrees.
        dip_directions: Per-vertex dip direction in degrees from north.

    Returns:
        A Shapely PolygonZ with (lon, lat, depth_km) coordinates (depth positive-down), or None if
        fewer than two vertices are supplied.
    """
    coords = list(coords)
    if len(coords) < 2:
        return None
    top = []
    bottom = []
    for (lon, lat), upper, lower, dip, dip_direction in zip(
        coords, upper_depths, lower_depths, dips, dip_directions
    ):
        if np.isclose(dip, 90.0, atol=1.0):
            offset_m = 0.0
        else:
            offset_m = (lower - upper) / np.tan(np.radians(dip)) * 1000.0
        lon_b, lat_b, _ = _GEOD.fwd(lon, lat, dip_direction, offset_m)
        top.append((lon, lat, upper))
        bottom.append((lon_b, lat_b, lower))
    return Polygon(top + bottom[::-1])


def _subsection_geometry_3d(row) -> Polygon | None:
    """Build a single subsection's dipping surface PolygonZ.

    Args:
        row: A subsection row with ``geometry`` (LineString), ``upper_depth_km``,
            ``lower_depth_km``, ``dip``, and ``dip_direction``.

    Returns:
        A Shapely PolygonZ in (lon, lat, depth_km), or None for a degenerate trace.
    """
    coords = [(x, y) for x, y, *_ in row["geometry"].coords]
    n = len(coords)
    return _surface_from_trace(
        coords,
        [row["upper_depth_km"]] * n,
        [row["lower_depth_km"]] * n,
        [row["dip"]] * n,
        [row["dip_direction"]] * n,
    )


def _cumulative_mfd(ruptures: pd.DataFrame) -> pd.DataFrame:
    """Compute cumulative magnitude frequency distribution from rupture data.

    Args:
        ruptures: DataFrame with at least columns ``m`` (magnitude) and ``rate``
            (annual rate of occurrence).

    Returns:
        DataFrame with columns ``magnitude`` (unique values, sorted ascending) and
        ``cumulative_rate`` (exceedance rate, i.e. sum of rates for all ruptures at or above
        each magnitude).
    """
    grouped = ruptures.groupby("m")["rate"].sum()
    magnitude = grouped.index.to_numpy()
    cumulative_rate = np.cumsum(grouped.to_numpy()[::-1])[::-1]
    return pd.DataFrame({"magnitude": magnitude, "cumulative_rate": cumulative_rate})


def _parent_area_pcts(
    parsed_indices: set[int],
    index_to_area: dict[int, float],
    index_to_parent_id: dict[int, int],
) -> list[tuple[int, float]]:
    """Compute area percentage contribution by parent fault ID for a rupture.

    Args:
        parsed_indices: Set of subsection indices participating in the rupture.
        index_to_area: Dict mapping subsection index to area in km².
        index_to_parent_id: Dict mapping subsection index to parent fault ID.

    Returns:
        List of (parent_id, area_pct) tuples, one per contributing parent fault.
    """
    parent_areas: dict[int, float] = {}
    for i in parsed_indices:
        if i in index_to_area and i in index_to_parent_id:
            pid = index_to_parent_id[i]
            parent_areas[pid] = parent_areas.get(pid, 0.0) + index_to_area[i]
    total = sum(parent_areas.values())
    if total == 0:
        return []
    return [(int(pid), area / total * 100.0) for pid, area in parent_areas.items()]


def _orient_trace(line: LineString, dip: float, dip_direction: float) -> LineString:
    """Orient a fault trace so that dip direction is to the right (right-hand rule).

    For vertical faults (dip within 1 degree of 90), the original order is preserved.

    Args:
        line: LineString of the merged surface trace.
        dip: Fault dip angle in degrees.
        dip_direction: Dip direction in degrees from north.

    Returns:
        LineString in right-hand-rule order (possibly reversed).
    """
    if np.isclose(dip, 90.0, atol=1.0):
        return line

    coords = line.coords
    lon1, lat1 = coords[0][0], coords[0][1]
    lon2, lat2 = coords[-1][0], coords[-1][1]
    az_trace, _, _ = _GEOD.inv(lon1, lat1, lon2, lat2)

    az_expected = (dip_direction - 90) % 360
    diff = ((az_trace - az_expected + 180) % 360) - 180
    if abs(diff) > 90:
        return line.reverse()
    return line


def _parent_surface_trace(
    geometries: list[LineString],
    dip: float,
    dip_direction: float,
) -> LineString:
    """Merge subsection geometries into an oriented parent fault surface trace.

    Args:
        geometries: List of subsection LineString geometries.
        dip: Representative dip angle in degrees.
        dip_direction: Representative dip direction in degrees from north.

    Returns:
        LineString of the merged, oriented surface trace (right-hand rule).

    Raises:
        ValueError: If the subsections do not merge into a single contiguous trace.
    """
    merged = linemerge(MultiLineString(geometries))
    if not isinstance(merged, LineString):
        raise ValueError("Parent subsections do not merge into a single contiguous trace.")
    return _orient_trace(merged, dip, dip_direction)


def _parent_geometry(subsections: pd.DataFrame) -> LineString:
    """Build a parent fault's merged, oriented surface trace from its subsections.

    The merged trace is oriented by the right-hand rule (dip direction to the right). An
    area-weighted dip and dip direction are computed internally solely to drive that
    orientation; they are an implementation detail and are not exposed as parent-level
    aggregates.

    Args:
        subsections: DataFrame of child subsections with ``geometry``, ``dip``,
            ``dip_direction``, and ``area_km2`` columns.

    Returns:
        LineString of the merged, oriented surface trace (right-hand rule).
    """
    weights = subsections["area_km2"]
    dip = (subsections["dip"] * weights).sum() / weights.sum()
    dip_direction = (subsections["dip_direction"] * weights).sum() / weights.sum()
    return _parent_surface_trace(subsections["geometry"].tolist(), dip, dip_direction)


def _parent_geometry_3d(subsections: pd.DataFrame) -> Polygon:
    """Build a parent fault's dipping surface as a single PolygonZ.

    Reuses the merged, right-hand-rule oriented surface trace from :func:`_parent_geometry` to get
    the globally ordered top-edge vertices, then offsets each vertex down-dip using that vertex's
    own subsection ``dip``, ``dip_direction``, and depths (looked up by coordinate). Child
    subsections of a parent are contiguous, so the result is a single hole-free PolygonZ.

    Args:
        subsections: DataFrame of child subsections with ``geometry``, ``dip``, ``dip_direction``,
            ``upper_depth_km``, ``lower_depth_km``, and ``area_km2`` columns.

    Returns:
        A Shapely PolygonZ in (lon, lat, depth_km).

    Raises:
        ValueError: If the subsections do not merge into a single contiguous trace.
    """
    trace = _parent_geometry(subsections)
    lookup: dict[tuple[float, float], tuple[float, float, float, float]] = {}
    for _, sub in subsections.iterrows():
        params = (
            sub["upper_depth_km"],
            sub["lower_depth_km"],
            sub["dip"],
            sub["dip_direction"],
        )
        for x, y, *_ in sub["geometry"].coords:
            lookup[(round(x, 6), round(y, 6))] = params

    coords = [(x, y) for x, y, *_ in trace.coords]
    params_per_vertex = [lookup[(round(lon, 6), round(lat, 6))] for lon, lat in coords]
    uppers, lowers, dips, dip_directions = zip(*params_per_vertex)
    return _surface_from_trace(coords, uppers, lowers, dips, dip_directions)


class _RuptureSet:
    """Internal rupture subset with shared selection and enrichment behavior.

    Encapsulates the common pattern of filtering ruptures by subsection index overlap, then
    enriches with merged geometries, dimensions, and parent area breakdowns.

    Args:
        dataset: The fault model dataset backing this query.
        indices: Target subsection indices to filter by.
    """

    def __init__(self, dataset, indices: frozenset[int]) -> None:
        self._dataset = dataset
        self._indices = indices

    @cached_property
    def _filtered(self) -> pd.DataFrame:
        """Ruptures involving any of the target subsection indices."""
        all_rups = self._dataset.ruptures
        mask = all_rups["parsed_indices"].apply(lambda s: not s.isdisjoint(self._indices))
        return all_rups.loc[mask]

    @cached_property
    def _geometry_map(self) -> dict[int, object]:
        return self._dataset.subsections["geometry"].to_dict()

    @cached_property
    def _length_map(self) -> dict[int, float]:
        return self._dataset.subsections["length_km"].to_dict()

    @cached_property
    def _area_map(self) -> dict[int, float]:
        return self._dataset.subsections["area_km2"].to_dict()

    @cached_property
    def _parent_id_map(self) -> dict[int, int]:
        return self._dataset.subsections["parent_id"].to_dict()

    def _geometry(self, parsed_indices: set[int]):
        return _merge_geometry(parsed_indices, self._geometry_map)

    def _length_km(self, parsed_indices: set[int]) -> float:
        return sum(self._length_map[i] for i in parsed_indices if i in self._length_map)

    def _area_km2(self, parsed_indices: set[int]) -> float:
        return sum(self._area_map[i] for i in parsed_indices if i in self._area_map)

    def _parent_area_pcts(self, parsed_indices: set[int]) -> list[tuple[int, float]]:
        return _parent_area_pcts(parsed_indices, self._area_map, self._parent_id_map)

    @cached_property
    def participating_ruptures(self) -> gpd.GeoDataFrame:
        """Filtered ruptures enriched with geometry and derived attributes.

        Returns a GeoDataFrame (EPSG:4326) with one row per rupture, indexed by the rupture id.
        Columns: ``m``, ``rate``, ``depth``, ``dip``, ``width``, ``rake``, ``geometry``,
        ``length_km``, ``area_km2``, and ``contributions``.

        ``contributions`` is the per-parent area breakdown: a list of ``(parent_id, area_pct)``
        tuples covering every parent fault the rupture touches (not just parents matching the
        target indices), so the percentages sum to 100 per rupture. ``rate`` is the full rupture
        rate; a parent's attributed rate is ``rate * area_pct / 100``.

        To get one row per (rupture, parent) — e.g. to attribute rates to individual faults —
        explode the column::

            e = rups.explode("contributions")
            e[["parent_id", "area_pct"]] = pd.DataFrame(
                e["contributions"].tolist(), index=e.index
            )
        """
        df = self._filtered.copy()
        if df.empty:
            columns = [
                column
                for column in self._dataset.ruptures.columns
                if column not in {"indices", "parsed_indices"}
            ]
            columns.extend(["geometry", "length_km", "area_km2", "contributions"])
            return gpd.GeoDataFrame(
                columns=columns,
                geometry="geometry",
                crs="EPSG:4326",
            )
        df["geometry"] = df["parsed_indices"].apply(self._geometry)
        df["length_km"] = df["parsed_indices"].apply(self._length_km)
        df["area_km2"] = df["parsed_indices"].apply(self._area_km2)
        df["contributions"] = df["parsed_indices"].apply(self._parent_area_pcts)
        df = df.drop(columns=["parsed_indices", "indices"])
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

    @cached_property
    def cumulative_mfd(self) -> pd.DataFrame:
        """Aggregate cumulative MFD for all ruptures in this set."""
        if self._filtered.empty:
            return pd.DataFrame(columns=["magnitude", "cumulative_rate"])
        return _cumulative_mfd(self._filtered)

    def per_subsection_mfds(self, subsection_indices: frozenset[int]) -> pd.DataFrame:
        """Cumulative MFDs per subsection for the given indices.

        Args:
            subsection_indices: Subsection indices to compute MFDs for.

        Returns:
            DataFrame with columns ``index``, ``magnitude``, and ``cumulative_rate``, ordered by
            ascending subsection index.
        """
        filtered = self._filtered
        if filtered.empty:
            return pd.DataFrame(columns=["index", "magnitude", "cumulative_rate"])
        frames = []
        for idx in sorted(subsection_indices):
            mask = filtered["parsed_indices"].apply(lambda s, i=idx: i in s)
            mfd = _cumulative_mfd(filtered.loc[mask])
            mfd.insert(0, "index", idx)
            frames.append(mfd)
        return pd.concat(frames, ignore_index=True)
