"""Data access layer for earthquake rupture forecast fault model datasets."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
from shapely.geometry import Point

from parserf.utils import parse_indices


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
    structured access to parent IDs, fault sections, and rupture scenarios with parsed subsection
    indices.

    Args:
        model: The fault model version.

    Attributes:
        parent_ids: DataFrame with columns ``parent_id`` (int) and ``parent_name`` (str).
        sections: GeoDataFrame of fault subsections with geometry and metadata.
        ruptures_parsed: Rupture data with parsed subsection indices as sets of integers.

    Examples:
        >>> from parserf.models import FaultModel, FaultModelDataset
        >>> dataset = FaultModelDataset(FaultModel.UCERF3_31)
        >>> parent_ids = dataset.parent_ids
        >>> sections = dataset.sections
        >>> ruptures = dataset.ruptures_parsed
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
    def sections(self) -> gpd.GeoDataFrame:
        """Load fault subsections for the selected fault model."""
        return gpd.read_file(self._raw_data_path / "sections.geojson", use_arrow=True)

    @cached_property
    def _ruptures(self) -> pd.DataFrame:
        """Load scenario ruptures for the selected fault model."""
        return pd.read_csv(self._raw_data_path / "ruptures.csv")

    @cached_property
    def ruptures_parsed(self) -> pd.DataFrame:
        """Scenario ruptures with parsed subsection indices as integer sets."""
        df = self._ruptures.copy()
        df["parsed_indices"] = df["indices"].apply(parse_indices)
        return df

    @cached_property
    def _subsection_table(self) -> pd.DataFrame:
        """Indexed table of per-subsection data: the single source of truth.

        A DataFrame indexed by subsection ``index`` (int) containing all columns from
        ``sections`` plus computed ``length_km``, ``width_km``, ``area_km2``, and looked-up
        ``parent_name``.  Built once per dataset and shared across view objects.
        """
        geod = pyproj.Geod(ellps="WGS84")
        df = self.sections.copy().set_index("index")
        df["length_km"] = df["geometry"].apply(lambda g: geod.geometry_length(g) / 1000.0)
        df["width_km"] = (df["lower-depth"] - df["upper-depth"]) / np.sin(np.radians(df["dip"]))
        df["area_km2"] = df["length_km"] * df["width_km"]
        pid_to_name = self.parent_ids.set_index("parent_id")["parent_name"].to_dict()
        df["parent_name"] = df["parent-id"].map(pid_to_name)
        return df

    def nearest_index(self, *, lat: float, lon: float) -> int:
        """Return the subsection index closest to a geographic coordinate.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.

        Returns:
            The integer index of the nearest fault subsection.
        """
        point = Point(lon, lat)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")
            distances = self.sections.set_index("index").distance(point)
        return int(distances.idxmin())
