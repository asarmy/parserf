"""Spatial and rupture query functions for earthquake rupture forecast datasets."""

from __future__ import annotations

import warnings

import geopandas as gpd
import pandas as pd
import pyproj
from shapely.geometry import Point

from parserf._utils import _RuptureSet
from parserf.models import FaultModelDataset


def _distances_km(dataset: FaultModelDataset, *, lat: float, lon: float) -> pd.Series:
    """Compute geodesic distance in km from a point to each subsection's nearest point.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        Series indexed by subsection index with distances in km.
    """
    point = Point(lon, lat)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")
        degrees = dataset.subsections.distance(point)
    geod = pyproj.Geod(ellps="WGS84")
    km = degrees.apply(lambda d: geod.line_length([lon, lon + d], [lat, lat]) / 1000.0)
    return km


def get_nearest_subsection_index(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
) -> int:
    """Return the subsection index closest to a geographic coordinate.

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        The integer index of the nearest fault subsection.
    """
    point = Point(lon, lat)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")
        distances = dataset.subsections.distance(point)
    return int(distances.idxmin())


def get_subsections_list(
    dataset: FaultModelDataset,
    *,
    lat: float,
    lon: float,
    dist_km: float,
) -> list[int]:
    """Return subsection indices within a distance of a geographic coordinate.

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

    Args:
        dataset: The fault model dataset to query.
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        dist_km: Search radius in kilometers.

    Returns:
        GeoDataFrame (EPSG:4326) in exploded form: one row per (rupture, parent) pair with
        ``parent_id`` and ``area_pct`` columns, plus merged geometry, ``length_km``, and
        ``area_km2``.
    """
    indices = get_subsections_list(dataset, lat=lat, lon=lon, dist_km=dist_km)
    rs = _RuptureSet(dataset, frozenset(indices))
    return rs.participating_ruptures
