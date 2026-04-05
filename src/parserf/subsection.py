"""Fault subsection view objects for earthquake rupture forecast datasets."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import pandas as pd

from parserf._utils import _RuptureSet
from parserf.models import FaultModel, FaultModelDataset


class FaultSubsectionData:
    """Dataset-backed view of a single subsection's local attributes.

    All values are read from the dataset's internal subsection cache; nothing is recomputed.

    Args:
        dataset: The fault model dataset backing this view.
        index: The subsection index within the fault model.

    Attributes:
        fault_model: The fault model enum value.
        index: Subsection index.
        name: Subsection name (e.g., "Airport Lake (0)").
        parent_id: Integer ID of the parent fault.
        parent_name: Name of the parent fault.
        upper_depth_km: Upper seismogenic depth in km.
        lower_depth_km: Lower seismogenic depth in km.
        dip: Fault dip angle in degrees.
        dip_direction: Dip direction in degrees.
        aseismicity: Aseismicity factor (0 to 1).
        geometry: Shapely LineString of the surface trace (EPSG:4326).
        length_km: Geodesic length of the surface trace in km.
        width_km: Down-dip width in km.
        area_km2: Fault area in km².
    """

    def __init__(self, dataset: FaultModelDataset, *, index: int) -> None:
        dataset._validate_index(index)
        self._dataset = dataset
        self._index = index
        self._row = dataset.subsections.loc[index]

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
        return self._row["parent_id"]  # type: ignore

    @property
    def parent_name(self) -> str:
        """Name of the parent fault."""
        return self._row["parent_name"]  # type: ignore

    @property
    def upper_depth_km(self) -> float:
        """Upper seismogenic depth in km."""
        return self._row["upper_depth_km"]  # type: ignore

    @property
    def lower_depth_km(self) -> float:
        """Lower seismogenic depth in km."""
        return self._row["lower_depth_km"]  # type: ignore

    @property
    def dip(self) -> float:
        """Fault dip angle in degrees."""
        return self._row["dip"]  # type: ignore

    @property
    def dip_direction(self) -> float:
        """Dip direction in degrees."""
        return self._row["dip_direction"]  # type: ignore

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

    def __init__(self, dataset: FaultModelDataset, *, index: int) -> None:
        dataset._validate_index(index)
        self._rupture_set = _RuptureSet(dataset, frozenset({index}))

    @cached_property
    def cumulative_mfd(self) -> pd.DataFrame:
        """Cumulative magnitude frequency distribution for participating ruptures.

        Returns a DataFrame with columns ``magnitude`` (sorted ascending) and ``cumulative_rate``
        (exceedance rate, i.e. sum of rates for all ruptures at or above each magnitude).
        """
        return self._rupture_set.cumulative_mfd

    @cached_property
    def participating_ruptures(self) -> gpd.GeoDataFrame:
        """GeoDataFrame of ruptures involving this subsection.

        Returns a GeoDataFrame (EPSG:4326) in exploded form: one row per (rupture, parent) pair
        with ``parent_id`` and ``area_pct`` columns, plus merged geometry, ``length_km``, and
        ``area_km2``. The ``rate`` column is the full rupture rate; multiply by ``area_pct / 100``
        for the parent-attributed rate.

        All parent contributions for each rupture are included, not just the queried subsection's
        parent. This preserves interpretable ``area_pct`` values that sum to 100 per rupture.
        """
        return self._rupture_set.participating_ruptures


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
        dataset._validate_index(index)
        self._dataset = dataset
        self.index = index
        self._name = dataset.subsections.loc[index, "name"]

    def __repr__(self) -> str:
        return (
            f"FaultSubsection(fault_model={self._dataset.model.name}, "
            f"index={self.index}, name='{self._name}')"
        )

    @cached_property
    def data(self) -> FaultSubsectionData:
        """Subsection-local attributes and geometry."""
        return FaultSubsectionData(self._dataset, index=self.index)

    @cached_property
    def ruptures(self) -> FaultSubsectionRuptures:
        """Rupture participation data."""
        return FaultSubsectionRuptures(self._dataset, index=self.index)
