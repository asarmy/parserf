"""Parent fault selection for batch earthquake rupture forecast queries."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj

from parserf._utils import _parent_geometry, _RuptureSet
from parserf.models import FaultModelDataset


class ParentSelection:
    """Scoped view of a dataset for a set of parent faults.

    Provides efficient batch access to subsection attributes, parent summaries, and enriched
    rupture data for all subsections belonging to the selected parents.

    Args:
        dataset: The fault model dataset backing this view.
        parent_ids: Ordered list of parent fault IDs to include. Duplicates are de-duplicated,
            preserving first-occurrence order.

    Raises:
        ValueError: If any parent fault ID is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.queries import get_parents_list
        >>> from parserf.selection import ParentSelection
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> pids = get_parents_list(ds, lat=35.77, lon=-117.60, dist_km=150)
        >>> sel = ParentSelection(ds, pids)
        >>> sel.parents
        ...
        >>> sel.ruptures
        ...
    """

    def __init__(self, dataset: FaultModelDataset, parent_ids: list[int]) -> None:
        if not parent_ids:
            raise ValueError("parent_ids must not be empty")
        parent_ids = list(dict.fromkeys(parent_ids))
        for pid in parent_ids:
            dataset._validate_parent_id(pid)
        self._dataset = dataset
        self._parent_ids = list(parent_ids)

    @property
    def parent_ids(self) -> list[int]:
        """Input parent fault IDs in their original order."""
        return self._parent_ids

    @cached_property
    def subsections(self) -> pd.DataFrame:
        """All subsections for the selected parents (full extent).

        Returns the subset of ``dataset.subsections`` whose ``parent_id`` is in the selection,
        preserving the original index and columns.
        """
        subs = self._dataset.subsections
        return subs.loc[subs["parent_id"].isin(self._parent_ids)]

    @cached_property
    def parents(self) -> gpd.GeoDataFrame:
        """Per-parent summary with oriented surface trace.

        Returns a GeoDataFrame indexed by ``parent_id`` (in input order) with columns
        ``parent_name`` and ``geometry`` (oriented surface trace as LineString, EPSG:4326).
        """
        subs = self.subsections

        records = []
        for pid, group in subs.groupby("parent_id"):
            trace = _parent_geometry(group)
            records.append(
                {
                    "parent_id": pid,
                    "parent_name": group["parent_name"].iloc[0],
                    "geometry": trace,
                }
            )

        gdf = gpd.GeoDataFrame(records, geometry="geometry", crs="EPSG:4326")
        return gdf.set_index("parent_id").loc[self._parent_ids]

    @cached_property
    def _rupture_set(self) -> _RuptureSet:
        """Single rupture set for all subsections of selected parents."""
        return _RuptureSet(self._dataset, frozenset(self.subsections.index))

    @cached_property
    def ruptures(self) -> gpd.GeoDataFrame:
        """Enriched ruptures for all subsections of the selected parents.

        Returns a GeoDataFrame (EPSG:4326) with one row per rupture, indexed by rupture id.
        Columns: ``m``, ``rate``, ``geometry``, ``length_km``, ``area_km2``, and ``contributions``
        — a list of ``(parent_id, area_pct)`` tuples for every parent the rupture touches (not just
        parents in the selection), summing to 100. ``rate`` is the full rupture rate, so a parent's
        attributed rate is ``rate * area_pct / 100``.

        Call ``rups.explode("contributions")`` for one row per (rupture, parent), then filter on
        ``parent_id`` to isolate specific parents.
        """
        return self._rupture_set.participating_ruptures


class GridSelection:
    """Scoped view of background gridded seismicity within a radius of a site.

    Filters ``dataset.grid`` to grid points within a geodesic distance of the given coordinate.

    Args:
        dataset: The fault model dataset backing this view.
        lat: Site latitude in decimal degrees.
        lon: Site longitude in decimal degrees.
        dist_km: Search radius in kilometers.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.selection import GridSelection
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> gs = GridSelection(ds, lat=34.05, lon=-118.25, dist_km=50)
        >>> gs.grid
        ...
    """

    def __init__(
        self, dataset: FaultModelDataset, *, lat: float, lon: float, dist_km: float
    ) -> None:
        self._dataset = dataset
        self._lat = lat
        self._lon = lon
        self._dist_km = dist_km

    @cached_property
    def grid(self) -> pd.DataFrame:
        """Grid points within the search radius, sorted by distance (nearest first).

        Returns the subset of ``dataset.grid`` with an additional ``dist_km`` column indicating
        geodesic distance from the site to each grid point.
        """
        df = self._dataset.grid
        geod = pyproj.Geod(ellps="WGS84")
        _, _, dist_m = geod.inv(
            np.full(len(df), self._lon),
            np.full(len(df), self._lat),
            df["lon"].values,
            df["lat"].values,
        )
        dist_km = dist_m / 1000.0
        mask = dist_km <= self._dist_km
        result = df.loc[mask].copy()
        result["dist_km"] = dist_km[mask]
        return result.sort_values("dist_km").reset_index(drop=True)
