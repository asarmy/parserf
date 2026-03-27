"""Fault subsection view objects for earthquake rupture forecast datasets."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import numpy as np
import pandas as pd

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


def _subsection_lookup_maps(table):
    """Build fast index-keyed lookup dicts from a subsection table."""
    return {
        "geometry": table["geometry"].to_dict(),
        "length_km": table["length_km"].to_dict(),
        "area_km2": table["area_km2"].to_dict(),
        "parent_name": table["parent_name"].to_dict(),
    }


class FaultSubsectionData:
    """Dataset-backed view of a single subsection's local attributes.

    All values are read from the dataset's internal subsection cache; nothing is
    recomputed.

    Args:
        dataset: The fault model dataset backing this view.
        index: The subsection index within the fault model.

    Attributes:
        fault_model: The fault model enum value.
        index: Subsection index.
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
    """

    def __init__(self, dataset: FaultModelDataset, index: int) -> None:
        self._dataset = dataset
        self._index = index
        self._row = dataset._subsection_table.loc[index]

    @property
    def fault_model(self) -> FaultModel:
        """The fault model enum value."""
        return self._dataset.model

    @property
    def index(self) -> int:
        """Subsection index."""
        return self._index

    @property
    def name(self) -> str:
        """Subsection name (e.g., "Airport Lake (0)")."""
        return self._row["name"]  # type: ignore

    @property
    def parent_id(self) -> int:
        """Integer ID of the parent fault."""
        return self._row["parent-id"]  # type: ignore

    @property
    def parent_name(self) -> str:
        """Name of the parent fault."""
        return self._row["parent_name"]  # type: ignore

    @property
    def upper_depth(self) -> float:
        """Upper seismogenic depth in km."""
        return self._row["upper-depth"]  # type: ignore

    @property
    def lower_depth(self) -> float:
        """Lower seismogenic depth in km."""
        return self._row["lower-depth"]  # type: ignore

    @property
    def dip(self) -> float:
        """Fault dip angle in degrees."""
        return self._row["dip"]  # type: ignore

    @property
    def dip_direction(self) -> float:
        """Dip direction in degrees."""
        return self._row["dip-direction"]  # type: ignore

    @property
    def aseismicity(self) -> float:
        """Aseismicity factor (0 to 1)."""
        return self._row["aseismicity"]  # type: ignore

    @property
    def geometry(self):
        """Shapely LineString of the surface trace (EPSG:4326)."""
        return self._row["geometry"]

    @property
    def length_km(self) -> float:
        """Geodesic length of the surface trace in kilometers."""
        return self._row["length_km"]  # type: ignore

    @property
    def width_km(self) -> float:
        """Down-dip width in kilometers."""
        return self._row["width_km"]  # type: ignore

    @property
    def area_km2(self) -> float:
        """Area in square kilometers (length times width)."""
        return self._row["area_km2"]  # type: ignore


class FaultSubsectionRuptures:
    """Dataset-backed view of a single subsection's rupture participation.

    Args:
        dataset: The fault model dataset backing this view.
        index: The subsection index within the fault model.

    Attributes:
        participating_ruptures: GeoDataFrame of ruptures involving this subsection.
    """

    def __init__(self, dataset: FaultModelDataset, index: int) -> None:
        self._dataset = dataset
        self._index = index

    @cached_property
    def participating_ruptures(self) -> gpd.GeoDataFrame:
        """GeoDataFrame of ruptures involving this subsection.

        Columns include all fields from ruptures_parsed plus a merged surface-trace geometry
        (EPSG:4326), a length_km column giving the total geodesic length, an area_km2 column giving
        the total fault area, and a parent_area_pcts column with a dict mapping each parent fault
        name to its percentage of the rupture's total area.
        """
        all_rups = self._dataset.ruptures_parsed
        mask = all_rups["parsed_indices"].apply(lambda s: self._index in s)
        partic_rups = all_rups.loc[mask].reset_index(drop=True)

        table = self._dataset._subsection_table
        lookup = _subsection_lookup_maps(table)

        geometries = [
            merge_geometry(idx, lookup["geometry"]) for idx in partic_rups["parsed_indices"]
        ]

        partic_rups["length_km"] = partic_rups["parsed_indices"].apply(
            lambda s: sum(lookup["length_km"][i] for i in s if i in lookup["length_km"])
        )

        partic_rups["area_km2"] = partic_rups["parsed_indices"].apply(
            lambda s: sum(lookup["area_km2"][i] for i in s if i in lookup["area_km2"])
        )

        partic_rups["parent_area_pcts"] = partic_rups["parsed_indices"].apply(
            lambda s: _parent_area_pcts(s, lookup["area_km2"], lookup["parent_name"])  # type: ignore
        )

        return gpd.GeoDataFrame(partic_rups, geometry=geometries, crs="EPSG:4326")  # type: ignore

    @cached_property
    def cumulative_mfd(self) -> pd.DataFrame:
        """Cumulative magnitude frequency distribution for participating ruptures.

        Returns a DataFrame with columns ``magnitude`` (unique values, sorted ascending) and
        ``cumulative_rate`` (exceedance rate, i.e. sum of rates for all ruptures at or above each
        magnitude).
        """
        grouped = self.participating_ruptures.groupby("m")["rate"].sum()
        magnitude = grouped.index.to_numpy()
        cumulative_rate = np.cumsum(grouped.to_numpy()[::-1])[::-1]
        return pd.DataFrame({"magnitude": magnitude, "cumulative_rate": cumulative_rate})


class FaultSubsection:
    """Thin facade over a single fault subsection.

    Validates that the subsection index exists in the dataset, then exposes ``.data`` for
    subsection-local attributes and ``.ruptures`` for rupture-query logic.

    Args:
        dataset: The fault model dataset backing this view.
        index: The subsection index within the fault model.

    Raises:
        ValueError: If the subsection index is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.subsection import FaultSubsection
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> sub = FaultSubsection(ds, index=0)
        >>> sub.data.name
        'Airport Lake (0)'
        >>> sub.data.length_km  # geodesic length in km
        7.8...
    """

    def __init__(self, dataset: FaultModelDataset, *, index: int) -> None:
        if index not in dataset._subsection_table.index:
            raise ValueError(f"No subsection with index {index} in {dataset.model.name}")
        self._dataset = dataset
        self.index = index

    def __repr__(self) -> str:
        return (
            f"FaultSubsection(fault_model={self._dataset.model.name}, "
            f"index={self.index}, name='{self.data.name}')"
        )

    @cached_property
    def data(self) -> FaultSubsectionData:
        """Subsection-local attributes and geometry."""
        return FaultSubsectionData(self._dataset, self.index)

    @cached_property
    def ruptures(self) -> FaultSubsectionRuptures:
        """Rupture participation data."""
        return FaultSubsectionRuptures(self._dataset, self.index)
