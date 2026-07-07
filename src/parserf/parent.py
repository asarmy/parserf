"""Parent fault view objects for earthquake rupture forecast datasets."""

from __future__ import annotations

from functools import cached_property

import geopandas as gpd
import pandas as pd

from parserf._utils import (
    _parent_geometry,
    _parent_geometry_3d,
    _RuptureSet,
)
from parserf.models import FaultModel, FaultModelDataset


class ParentFaultData:
    """Dataset-backed view of a parent fault's subsection attributes.

    Args:
        dataset: The fault model dataset backing this view.
        parent_id: The parent fault integer ID.

    Attributes:
        fault_model: The fault model enum value.
        name: Parent fault name.
        parent_id: Integer ID of the parent fault.
        subsections: DataFrame of all child subsection attributes.
        geometry: Merged, right-hand-rule oriented surface trace (Shapely LineString).
        geometry_3d: Merged dipping fault surface (Shapely PolygonZ).
    """

    def __init__(self, dataset: FaultModelDataset, *, parent_id: int) -> None:
        dataset._validate_parent_id(parent_id)
        self._dataset = dataset
        self._parent_id = parent_id
        table = dataset.subsections
        self._name = table.loc[table["parent_id"] == parent_id, "parent_name"].iloc[0]

    @property
    def fault_model(self) -> FaultModel:
        """The fault model enum value."""
        return self._dataset.model

    @property
    def name(self) -> str:
        """Parent fault name."""
        return self._name

    @property
    def parent_id(self) -> int:
        """Integer ID of the parent fault."""
        return self._parent_id

    @cached_property
    def subsections(self) -> pd.DataFrame:
        """DataFrame of all child subsection attributes.

        Columns include index, name, dip, dip_direction, upper_depth_km, lower_depth_km,
        aseismicity, length_km, width_km, area_km2, and geometry.
        """
        table = self._dataset.subsections
        df = table.loc[table["parent_id"] == self._parent_id].copy()
        columns = [
            "name",
            "dip",
            "dip_direction",
            "upper_depth_km",
            "lower_depth_km",
            "aseismicity",
            "length_km",
            "width_km",
            "area_km2",
            "geometry",
        ]
        return df[columns].rename_axis("index")

    @cached_property
    def geometry(self):
        """Oriented 2D surface trace of the parent fault as a Shapely LineString.

        Mirrors ``FaultSubsectionData.geometry``: the parent's coordinates as a single
        LineString. The child subsection traces are merged and oriented such that, when walking
        along the trace, the dip direction is to your right (right-hand rule). For vertical faults
        (dip ~ 90 degrees), the original order is preserved.

        Per-subsection scalars (dip, depths, areas, etc.) are not aggregated here; read them from
        ``subsections`` and aggregate as needed.

        Returns:
            LineString of the merged, oriented surface trace (EPSG:4326).
        """
        return _parent_geometry(self.subsections)

    @cached_property
    def geometry_3d(self):
        """Merged dipping fault surface of the parent as a single Shapely PolygonZ.

        The 3D counterpart to ``geometry``: the child subsection surfaces are stitched along the
        merged, right-hand-rule oriented trace into a single closed PolygonZ. Each vertex is hung
        down-dip from ``upper_depth_km`` to ``lower_depth_km`` using its own subsection's ``dip``
        and ``dip_direction``. Coordinates are ``(lon, lat, depth_km)`` with depth positive-down.

        Child subsections are contiguous, so this is always a single hole-free PolygonZ.
        The surface is generally non-planar, so Shapely's 2D ``.area`` and ``.length`` are not
        meaningful on it.

        Returns:
            Shapely PolygonZ of the merged dipping surface (EPSG:4326).
        """
        return _parent_geometry_3d(self.subsections)


class ParentFaultRuptures:
    """Dataset-backed view of rupture participation across a parent fault's subsections.

    Args:
        dataset: The fault model dataset backing this view.
        parent_id: The parent fault integer ID.
    """

    def __init__(self, dataset: FaultModelDataset, *, parent_id: int) -> None:
        dataset._validate_parent_id(parent_id)
        self._dataset = dataset
        table = dataset.subsections
        self._subsection_indices = frozenset(table.loc[table["parent_id"] == parent_id].index)
        self._rupture_set = _RuptureSet(dataset, self._subsection_indices)

    @cached_property
    def participating_ruptures(self) -> gpd.GeoDataFrame:
        """GeoDataFrame of ruptures involving any child subsection of this parent fault.

        Returns a GeoDataFrame (EPSG:4326) with one row per rupture, including a ``contributions``
        column: a list of ``(parent_id, area_pct)`` tuples for every parent the rupture touches
        (not just this one), summing to 100. ``rate`` is the full rupture rate, so a parent's
        attributed rate is ``rate * area_pct / 100``. Call ``rups.explode("contributions")`` for
        one row per (rupture, parent), then filter on ``parent_id`` to isolate this parent's rows.
        """
        return self._rupture_set.participating_ruptures

    @cached_property
    def cumulative_mfds(self) -> pd.DataFrame:
        """Cumulative magnitude frequency distributions for all child subsections.

        Returns a DataFrame with columns ``index`` (subsection index), ``magnitude``, and
        ``cumulative_rate``, ordered by ascending subsection index.
        """
        return self._rupture_set.per_subsection_mfds(self._subsection_indices)


class ParentFault:
    """Thin facade over a parent fault and its child subsections.

    Validates that the parent fault name exists in the dataset, then exposes ``.data`` for
    subsection attributes and ``.ruptures`` for rupture-query logic.

    Args:
        dataset: The fault model dataset backing this view.
        name: The parent fault name (e.g., "Airport Lake").

    Raises:
        ValueError: If the parent fault name is not found in the dataset.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> from parserf.parent import ParentFault
        >>> ds = FaultModelDataset(FaultModel.UCERF3_31)
        >>> flt = ParentFault(ds, name="Airport Lake")
        >>> flt.data.name
        'Airport Lake'
        >>> flt.data.subsections
        ...
    """

    def __init__(self, dataset: FaultModelDataset, *, name: str) -> None:
        self._dataset = dataset
        self._name = name
        self._parent_id = dataset.get_parent_fault_id(name=name)

    def __repr__(self) -> str:
        return (
            f"ParentFault(fault_model={self._dataset.model.name}, "
            f"name='{self._name}', parent_id={self._parent_id})"
        )

    @cached_property
    def data(self) -> ParentFaultData:
        """Parent fault attributes and child subsection data."""
        return ParentFaultData(self._dataset, parent_id=self._parent_id)

    @cached_property
    def ruptures(self) -> ParentFaultRuptures:
        """Rupture participation data across child subsections."""
        return ParentFaultRuptures(self._dataset, parent_id=self._parent_id)
