"""Private utility functions and internal classes for parserf data processing."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Geod
from shapely import LineString, MultiLineString
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
    return [(pid, area / total * 100.0) for pid, area in parent_areas.items()]


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
    """
    merged = linemerge(MultiLineString(geometries))
    return _orient_trace(merged, dip, dip_direction)


def _parent_style(rake_frequencies: pd.DataFrame, parent_id: int) -> str:
    """Return the dominant faulting style for a parent fault.

    Args:
        rake_frequencies: DataFrame with columns ``parent_id``, ``style``, ``count``.
        parent_id: The parent fault integer ID.

    Returns:
        The most common faulting style by rupture count.
    """
    parent_rakes = rake_frequencies.loc[rake_frequencies["parent_id"] == parent_id]
    counts = parent_rakes.groupby("style")["count"].sum()
    return counts.idxmax()


def _parent_style_counts(rake_frequencies: pd.DataFrame, parent_id: int) -> pd.DataFrame:
    """Return faulting style breakdown for a parent fault, sorted descending by count.

    Args:
        rake_frequencies: DataFrame with columns ``parent_id``, ``style``, ``count``.
        parent_id: The parent fault integer ID.

    Returns:
        DataFrame with columns ``style`` and ``count``, sorted by count descending.
    """
    parent_rakes = rake_frequencies.loc[rake_frequencies["parent_id"] == parent_id]
    counts = parent_rakes.groupby("style")["count"].sum().reset_index()
    return counts.sort_values("count", ascending=False).reset_index(drop=True)


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

        Returns a GeoDataFrame (EPSG:4326) in exploded form: one row per (rupture, parent) pair.
        The DataFrame index identifies the original rupture (duplicate index values indicate rows
        from the same rupture). Columns include ``m``, ``rate``, ``depth``, ``dip``, ``width``,
        ``rake``, ``geometry``, ``length_km``, ``area_km2``, ``parent_id``, and ``area_pct``.

        The ``rate`` column is the full rupture rate; multiply by ``area_pct / 100`` to get the
        parent-attributed rate.

        All parent contributions for each rupture are included, not just parents matching the
        target indices. This preserves interpretable ``area_pct`` values that sum to 100 per
        rupture. Filter on ``parent_id`` to isolate specific parents.
        """
        df = self._filtered.copy()
        if df.empty:
            return gpd.GeoDataFrame(
                columns=[
                    "m",
                    "rate",
                    "depth",
                    "dip",
                    "width",
                    "rake",
                    "geometry",
                    "length_km",
                    "area_km2",
                    "parent_id",
                    "area_pct",
                ],
                geometry="geometry",
                crs="EPSG:4326",
            )
        df["geometry"] = df["parsed_indices"].apply(self._geometry)
        df["length_km"] = df["parsed_indices"].apply(self._length_km)
        df["area_km2"] = df["parsed_indices"].apply(self._area_km2)
        df["_pcts"] = df["parsed_indices"].apply(self._parent_area_pcts)
        df = df.drop(columns=["parsed_indices", "indices"])
        df = df.explode("_pcts", ignore_index=False)
        df[["parent_id", "area_pct"]] = pd.DataFrame(
            df["_pcts"].tolist(),
            index=df.index,
        )
        df = df.drop(columns=["_pcts"])
        df["parent_id"] = df["parent_id"].astype(int)
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
            DataFrame with columns ``index``, ``magnitude``, and ``cumulative_rate``.
        """
        filtered = self._filtered
        if filtered.empty:
            return pd.DataFrame(columns=["index", "magnitude", "cumulative_rate"])
        frames = []
        for idx in subsection_indices:
            mask = filtered["parsed_indices"].apply(lambda s, i=idx: i in s)
            mfd = _cumulative_mfd(filtered.loc[mask])
            mfd.insert(0, "index", idx)
            frames.append(mfd)
        return pd.concat(frames, ignore_index=True)
