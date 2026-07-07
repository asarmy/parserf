"""Spatial and rupture query functions for earthquake rupture forecast datasets."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
from shapely.geometry import Point
from shapely.ops import nearest_points

from parserf._utils import _RuptureSet
from parserf.models import FaultModelDataset


def _distances_km(dataset: FaultModelDataset, *, lat: float, lon: float) -> pd.Series:
    """Compute geodesic distance in km from a point to each subsection's footprint.

    Distance is measured to the subsection's map-view footprint (the dipping surface projected to
    the ground, via ``dataset._subsection_footprints``) rather than just its surface trace. For a
    dipping fault the footprint extends down-dip from the trace, so a site over the hanging wall —
    even far from the trace — is at distance 0. Vertical faults are unaffected: their footprint
    collapses onto the trace.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Series indexed by subsection index with distances in km.
    """
    point = Point(lon, lat)
    footprints = dataset._subsection_footprints
    nearest = footprints.apply(lambda geom: nearest_points(point, geom)[1])
    geod = pyproj.Geod(ellps="WGS84")
    _, _, dist_m = geod.inv(
        np.full(len(nearest), lon),
        np.full(len(nearest), lat),
        nearest.x.values,
        nearest.y.values,
    )
    return pd.Series(dist_m / 1000.0, index=footprints.index)


def get_nearest_subsection_index(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
) -> int:
    """Return the subsection index closest to a geographic coordinate.

    Distance is measured to each subsection's map-view footprint (the dipping surface projected to
    the ground), not just its surface trace — see :func:`_distances_km`. A coordinate over the
    hanging wall of a dipping fault can therefore resolve to that fault even far from its trace.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        The integer index of the nearest fault subsection.
    """
    return int(_distances_km(dataset, lat=lat, lon=lon).idxmin())


def get_subsections_list(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
    dist_km: float,
) -> list[int]:
    """Return subsection indices within a distance of a geographic coordinate.

    Distance is measured to each subsection's map-view footprint (the dipping surface projected to
    the ground), not just its surface trace — see :func:`_distances_km`. A coordinate over the
    hanging wall of a dipping fault is within range even far from its trace.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        dist_km: Search radius in kilometers.

    Returns:
        List of subsection indices within dist_km, sorted by distance (nearest first).
    """
    km = _distances_km(dataset, lat=lat, lon=lon)
    within = km[km <= dist_km].sort_values()
    return list(within.index)


def get_parents_list(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
    dist_km: float,
) -> list[int]:
    """Return parent fault IDs within a distance of a geographic coordinate.

    Distance is measured to each child subsection's map-view footprint (the dipping surface
    projected to the ground), not just its surface trace — see :func:`_distances_km`.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        dist_km: Search radius in kilometers.

    Returns:
        List of unique parent fault IDs whose nearest child subsection is within dist_km, sorted by
        the distance of their closest child (nearest first).
    """
    indices = get_subsections_list(dataset, lat=lat, lon=lon, dist_km=dist_km)
    parent_col = dataset.subsections["parent_id"]
    seen: set[int] = set()
    result: list[int] = []
    for idx in indices:
        pid = int(parent_col.loc[idx])
        if pid not in seen:
            seen.add(pid)
            result.append(pid)
    return result


def get_ruptures_near(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
    dist_km: float,
) -> gpd.GeoDataFrame:
    """Return enriched ruptures involving any subsection within a distance of a coordinate.

    Distance is measured to each subsection's map-view footprint (the dipping surface projected to
    the ground), not just its surface trace — see :func:`_distances_km`.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        dist_km: Search radius in kilometers.

    Returns:
        GeoDataFrame (EPSG:4326) with one row per rupture: merged ``geometry``, ``length_km``,
        ``area_km2``, and a ``contributions`` column (a list of ``(parent_id, area_pct)`` tuples,
        summing to 100, for every parent the rupture touches). Call
        ``rups.explode("contributions")`` for one row per (rupture, parent).
    """
    indices = get_subsections_list(dataset, lat=lat, lon=lon, dist_km=dist_km)
    rs = _RuptureSet(dataset, frozenset(indices))
    return rs.participating_ruptures
