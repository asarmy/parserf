"""Shared utility functions for parserf data processing scripts."""

import numpy as np
import pandas as pd


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
    from shapely import MultiLineString
    from shapely.ops import linemerge

    geoms = [index_to_geom[i] for i in sorted(parsed_indices) if i in index_to_geom]
    if len(geoms) == 0:
        return None
    if len(geoms) == 1:
        return geoms[0]
    return linemerge(MultiLineString(geoms))
