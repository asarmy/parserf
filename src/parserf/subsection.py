"""Fault subsection model for earthquake rupture forecast datasets."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import numpy as np
import pyproj
from shapely import LineString

from parserf.models import FaultModel, FaultModelDataset
from parserf.utils import merge_geometry


def _parent_area_pcts(
    parsed_indices: set[int],
    index_to_area: dict[int, float],
    index_to_parent: dict[int, str],
) -> dict[str, float]:
    """Compute area percentage contribution by parent fault name for a rupture."""
    parent_areas: dict[str, float] = {}
    for i in parsed_indices:
        if i in index_to_area and i in index_to_parent:
            name = index_to_parent[i]
            parent_areas[name] = parent_areas.get(name, 0.0) + index_to_area[i]
    total = sum(parent_areas.values())
    if total == 0:
        return {}
    return {k: v / total * 100.0 for k, v in parent_areas.items()}


class FaultSubsection:
    """A dataset-backed view of a single fault subsection.

    Provides convenient, subsection-centered access to the underlying ``FaultModelDataset``: core
    section attributes, computed geometric properties, and derived participating-rupture data.

    Args:
        dataset: The fault model dataset backing this view.
        index: The subsection index within the fault model.

    Attributes:
        index: Subsection index.
        fault_model: The fault model enum value.
        name: Subsection name (e.g., "Airport Lake (0)").
        parent_id: Integer ID of the parent fault.
        parent_name: Name of the parent fault.
        upper_depth: Upper seismogenic depth in km.
        lower_depth: Lower seismogenic depth in km.
        dip: Fault dip angle in degrees.
        dip_direction: Dip direction in degrees.
        aseismicity: Aseismicity factor (0 to 1).
        geometry: Shapely LineString of the surface trace (EPSG:4326).
        length_km: Geodesic length of the surface trace in km.
        width_km: Down-dip width in km.
        area_km2: Fault area in km².
        participating_ruptures: GeoDataFrame of ruptures where this subsection participates, with
            merged section geometries (EPSG:4326), length_km, area_km2, and parent_area_pcts
            columns.

    Raises:
        ValueError: If the subsection index is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.subsection import FaultSubsection
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> sub = FaultSubsection(ds, index=0)
        >>> sub.name
        'Airport Lake (0)'
        >>> sub.length_km  # geodesic length in km
        7.8...
    """

    def __init__(self, dataset: FaultModelDataset, *, index: int) -> None:
        sections = dataset.sections
        matches = sections.loc[sections["index"] == index]
        if matches.empty:
            raise ValueError(f"No subsection with index {index} in {dataset.model.name}")
        self._dataset = dataset
        self._row = matches.iloc[0]
        self.index = index

    def __repr__(self) -> str:
        return (
            f"FaultSubsection(fault_model={self.fault_model.name}, "
            f"index={self.index}, name='{self.name}')"
        )

    # --- Section attributes (delegated to dataset row) ---

    @property
    def fault_model(self) -> FaultModel:
        """The fault model enum value."""
        return self._dataset.model

    @property
    def name(self) -> str:
        """Subsection name (e.g., "Airport Lake (0)")."""
        return self._row["name"]

    @property
    def parent_id(self) -> int:
        """Integer ID of the parent fault."""
        return self._row["parent-id"]

    @cached_property
    def parent_name(self) -> str | None:
        """Name of the parent fault, or None if not found."""
        parent_match = self._dataset.parent_ids.loc[
            self._dataset.parent_ids["parent_id"] == self.parent_id
        ]
        if parent_match.empty:
            return None
        return parent_match.iloc[0]["parent_name"]

    @property
    def upper_depth(self) -> float:
        """Upper seismogenic depth in km."""
        return self._row["upper-depth"]

    @property
    def lower_depth(self) -> float:
        """Lower seismogenic depth in km."""
        return self._row["lower-depth"]

    @property
    def dip(self) -> float:
        """Fault dip angle in degrees."""
        return self._row["dip"]

    @property
    def dip_direction(self) -> float:
        """Dip direction in degrees."""
        return self._row["dip-direction"]

    @property
    def aseismicity(self) -> float:
        """Aseismicity factor (0 to 1)."""
        return self._row["aseismicity"]

    @property
    def geometry(self) -> LineString:
        """Shapely LineString of the surface trace (EPSG:4326)."""
        return self._row["geometry"]

    # --- Computed geometric properties ---

    @property
    def length_km(self) -> float:
        """Geodesic length of the surface trace in kilometers."""
        geod = pyproj.Geod(ellps="WGS84")
        return geod.geometry_length(self.geometry) / 1000.0

    @property
    def width_km(self) -> float:
        """Down-dip width in kilometers."""
        dip_rad = np.radians(self.dip)
        return (self.lower_depth - self.upper_depth) / np.sin(dip_rad)

    @property
    def area_km2(self) -> float:
        """Area in square kilometers (length times width)."""
        return self.length_km * self.width_km

    # --- Derived data ---

    @cached_property
    def participating_ruptures(self) -> gpd.GeoDataFrame:
        """GeoDataFrame of ruptures involving this subsection.

        Columns include all fields from ruptures_parsed plus a merged surface-trace geometry
        (EPSG:4326), a length_km column giving the total geodesic length, an area_km2
        column giving the total fault area, and a parent_area_pcts column with a dict mapping
        each parent fault name to its percentage of the rupture's total area.
        """
        rp = self._dataset.ruptures_parsed
        mask = rp["parsed_indices"].apply(lambda s: self.index in s)
        pr_df = rp.loc[mask].reset_index(drop=True)

        index_to_geom = self._dataset.index_to_geometry
        geometries = [merge_geometry(idx, index_to_geom) for idx in pr_df["parsed_indices"]]

        index_to_len = self._dataset.index_to_length_km
        pr_df["length_km"] = pr_df["parsed_indices"].apply(
            lambda s: sum(index_to_len[i] for i in s if i in index_to_len)
        )

        index_to_area = self._dataset.index_to_area_km2
        pr_df["area_km2"] = pr_df["parsed_indices"].apply(
            lambda s: sum(index_to_area[i] for i in s if i in index_to_area)
        )

        index_to_parent = self._dataset.index_to_parent_name
        pr_df["parent_area_pcts"] = pr_df["parsed_indices"].apply(
            lambda s: _parent_area_pcts(s, index_to_area, index_to_parent)
        )

        return gpd.GeoDataFrame(pr_df, geometry=geometries, crs="EPSG:4326")
