"""Data access layer for earthquake rupture forecast fault model datasets."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from functools import cached_property
from pathlib import Path

import geopandas as gpd
import pandas as pd

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

    Provides cached access to earthquake rupture forecast data files for different fault
    models including NSHMP 2023, UCERF3 v3.1, and UCERF3 v3.2. Handles file loading and
    provides structured access to parent IDs, fault sections, and rupture scenarios with
    parsed subsection indices.

    Args:
        model: The fault model version.

    Attributes:
        parent_ids: DataFrame containing fault names and their parent IDs.
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
    def index_to_geometry(self) -> dict:
        """Subsection index to LineString geometry lookup.

        Builds a dict mapping subsection index -> geometry for fast repeated lookup. Built once per
        dataset so that multiple FaultSubsection instances can share it when constructing rupture
        geometries.
        """
        return self.sections.set_index("index")["geometry"].to_dict()
