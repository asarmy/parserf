"""Tests for FaultModel enum and FaultModelDataset."""

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import pytest

from parserf.models import FaultModel


class TestFaultModel:
    def test_shorthand_values(self):
        assert FaultModel.NSHMP_2023 == 2023
        assert FaultModel.UCERF3_31 == 31
        assert FaultModel.UCERF3_32 == 32

    def test_construction_from_int(self):
        assert FaultModel(31) is FaultModel.UCERF3_31
        assert FaultModel(32) is FaultModel.UCERF3_32
        assert FaultModel(2023) is FaultModel.NSHMP_2023

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            FaultModel(999)


class TestFaultModelDataset:
    def test_sections_is_geodataframe(self, dataset):
        assert isinstance(dataset.sections, gpd.GeoDataFrame)

    def test_sections_has_expected_columns(self, dataset):
        expected = {
            "name",
            "state",
            "index",
            "parent-id",
            "upper-depth",
            "lower-depth",
            "dip",
            "dip-direction",
            "aseismicity",
            "geometry",
        }
        assert expected.issubset(set(dataset.sections.columns))

    def test_parent_ids_is_dataframe(self, dataset):
        assert isinstance(dataset.parent_ids, pd.DataFrame)

    def test_parent_ids_has_expected_columns(self, dataset):
        expected = {"name", "parent_id", "parent_name"}
        assert expected == set(dataset.parent_ids.columns)

    def test_ruptures_parsed_is_dataframe(self, dataset):
        assert isinstance(dataset.ruptures_parsed, pd.DataFrame)

    def test_ruptures_parsed_has_expected_columns(self, dataset):
        expected = {"m", "rate", "depth", "dip", "width", "rake", "indices", "parsed_indices"}
        assert expected.issubset(set(dataset.ruptures_parsed.columns))

    def test_ruptures_parsed_has_parsed_indices(self, dataset):
        df = dataset.ruptures_parsed
        assert "parsed_indices" in df.columns
        assert isinstance(df["parsed_indices"].iloc[0], set)

    def test_sections_not_empty(self, dataset):
        assert len(dataset.sections) > 0

    def test_caching(self, dataset):
        """Cached properties return the same object on repeated access."""
        assert dataset.sections is dataset.sections
        assert dataset.parent_ids is dataset.parent_ids

    def test_index_to_length_km_is_dict(self, dataset):
        assert isinstance(dataset.index_to_length_km, dict)

    def test_index_to_length_km_all_positive(self, dataset):
        assert all(v > 0 for v in dataset.index_to_length_km.values())

    def test_index_to_length_km_count_matches_sections(self, dataset):
        assert len(dataset.index_to_length_km) == len(dataset.sections)

    def test_index_to_length_km_spot_check(self, dataset):
        """Verify a value against a direct pyproj call."""
        geod = pyproj.Geod(ellps="WGS84")
        row = dataset.sections.iloc[0]
        expected = geod.geometry_length(row["geometry"]) / 1000.0
        assert dataset.index_to_length_km[row["index"]] == pytest.approx(expected)

    def test_index_to_area_km2_is_dict(self, dataset):
        assert isinstance(dataset.index_to_area_km2, dict)

    def test_index_to_area_km2_all_positive(self, dataset):
        assert all(v > 0 for v in dataset.index_to_area_km2.values())

    def test_index_to_area_km2_count_matches_sections(self, dataset):
        assert len(dataset.index_to_area_km2) == len(dataset.sections)

    def test_index_to_area_km2_spot_check(self, dataset):
        """Verify a value equals length_km * width_km for the same subsection."""
        row = dataset.sections.iloc[0]
        idx = row["index"]
        length_km = dataset.index_to_length_km[idx]
        width_km = (row["lower-depth"] - row["upper-depth"]) / np.sin(np.radians(row["dip"]))
        assert dataset.index_to_area_km2[idx] == pytest.approx(length_km * width_km)

    def test_index_to_parent_name_is_dict(self, dataset):
        assert isinstance(dataset.index_to_parent_name, dict)

    def test_index_to_parent_name_count_matches_sections(self, dataset):
        assert len(dataset.index_to_parent_name) == len(dataset.sections)

    def test_index_to_parent_name_all_strings(self, dataset):
        assert all(isinstance(v, str) for v in dataset.index_to_parent_name.values())
