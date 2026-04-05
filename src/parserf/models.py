"""Data access layer for earthquake rupture forecast fault model datasets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj

from parserf._utils import _parse_indices


class FaultModel(IntEnum):
    """Fault model identifiers with shorthand integer values.

    Attributes:
        NSHMP_2023: USGS NSHM CONUS v6.0.0.
        UCERF3_31: UCERF3 fault model 3.1 (USGS v5.3-maint).
        UCERF3_32: UCERF3 fault model 3.2 (USGS v5.3-maint).
    """

    NSHMP_2023 = 2023
    UCERF3_31 = 31
    UCERF3_32 = 32


_VERSION_MAP = {
    FaultModel.NSHMP_2023: "nshm-conus-v6.0.0",
    FaultModel.UCERF3_31: "fault-model-3.1",
    FaultModel.UCERF3_32: "fault-model-3.2",
}


@dataclass(frozen=True)
class FaultModelDataset:
    """Data access layer for earthquake rupture forecast fault model datasets.

    Provides cached access to earthquake rupture forecast data files for different fault models
    including NSHMP 2023, UCERF3 v3.1, and UCERF3 v3.2. Handles file loading and provides
    structured access to parent IDs, fault subsections, rupture scenarios, and faulting style
    data.

    Args:
        model: The fault model version.

    Attributes:
        parent_ids: DataFrame with columns ``parent_id`` (int) and ``parent_name`` (str).
        rake_frequencies: DataFrame of rake frequency counts per parent fault with columns
            ``parent_id``, ``style``, and ``count``.
        subsections: DataFrame of fault subsections indexed by ``index`` (int) with columns for
            geometry, dimensions, and parent fault info.
        ruptures: Rupture data with parsed subsection indices as sets of integers.

    Methods:
        get_parent_fault_id(name=...): Resolve a parent fault name to its integer ID.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> dataset = FaultModelDataset(FaultModel.UCERF3_31)
        >>> parent_ids = dataset.parent_ids
        >>> subsections = dataset.subsections
        >>> ruptures = dataset.ruptures
    """

    model: FaultModel

    @property
    def _package_root(self) -> Path:
        return Path(__file__).parent

    @cached_property
    def _raw_data_path(self) -> Path:
        return self._package_root / "data" / "RawData" / _VERSION_MAP[self.model]

    @cached_property
    def _derived_data_path(self) -> Path:
        return self._package_root / "data" / "DerivedData" / _VERSION_MAP[self.model]

    @cached_property
    def parent_ids(self) -> pd.DataFrame:
        """Load parent IDs for the selected fault model."""
        return pd.read_csv(self._derived_data_path / "parent_id.csv")

    @cached_property
    def rake_frequencies(self) -> pd.DataFrame:
        """Load rake frequency counts for each parent fault in the selected model."""
        return pd.read_csv(self._derived_data_path / "rake_frequencies.csv")

    @cached_property
    def _sections(self) -> gpd.GeoDataFrame:
        """Load fault subsections for the selected fault model."""
        return gpd.read_file(self._raw_data_path / "sections.geojson", use_arrow=True)

    @cached_property
    def _ruptures(self) -> pd.DataFrame:
        """Load scenario ruptures for the selected fault model."""
        return pd.read_csv(self._raw_data_path / "ruptures.csv")

    @cached_property
    def ruptures(self) -> pd.DataFrame:
        """Scenario ruptures with parsed subsection indices as integer sets."""
        df = self._ruptures.copy()
        df["parsed_indices"] = df["indices"].apply(_parse_indices)
        return df

    def _validate_index(self, index: int) -> None:
        """Raise ValueError if index is not a valid subsection index.

        Args:
            index: The subsection index to validate.

        Raises:
            ValueError: If the index is not found in the dataset.
        """
        if index not in self.subsections.index:
            raise ValueError(f"No subsection with index {index} in {self.model.name}")

    def _validate_parent_id(self, parent_id: int) -> None:
        """Raise ValueError if parent_id is not a valid parent fault ID.

        Args:
            parent_id: The parent fault ID to validate.

        Raises:
            ValueError: If the parent_id is not found in the dataset.
        """
        if parent_id not in self.parent_ids["parent_id"].values:
            raise ValueError(f"No parent fault with id {parent_id} in {self.model.name}")

    @cached_property
    def subsections(self) -> pd.DataFrame:
        """Fault subsections with computed dimensions and parent fault names.

        A DataFrame indexed by subsection ``index`` (int) containing all columns from the raw
        GeoJSON sections plus computed ``length_km``, ``width_km``, ``area_km2``, and looked-up
        ``parent_name``.  Built once per dataset and shared across view objects.
        """
        geod = pyproj.Geod(ellps="WGS84")
        df = self._sections.copy().set_index("index")
        df = df.rename(
            columns={
                "parent-id": "parent_id",
                "upper-depth": "upper_depth_km",
                "lower-depth": "lower_depth_km",
                "dip-direction": "dip_direction",
            }
        )
        df["length_km"] = df["geometry"].apply(lambda g: geod.geometry_length(g) / 1000.0)
        df["width_km"] = (df["lower_depth_km"] - df["upper_depth_km"]) / np.sin(
            np.radians(df["dip"])
        )
        df["area_km2"] = df["length_km"] * df["width_km"]
        pid_to_name = self.parent_ids.set_index("parent_id")["parent_name"].to_dict()
        df["parent_name"] = df["parent_id"].map(pid_to_name)
        return df

    def get_parent_fault_id(self, *, name: str) -> int:
        """Return the integer parent fault ID for a given parent fault name.

        Args:
            name: The parent fault name (e.g., "Airport Lake").

        Returns:
            The integer parent fault ID.

        Raises:
            ValueError: If the parent fault name is not found in the dataset.
        """
        match = self.parent_ids.loc[self.parent_ids["parent_name"] == name, "parent_id"]
        if match.empty:
            raise ValueError(f"No parent fault with name '{name}' in {self.model.name}")
        return int(match.iloc[0])
