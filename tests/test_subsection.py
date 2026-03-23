"""Tests for FaultSubsection."""

import geopandas as gpd
import numpy as np
import pyproj
import pytest
from shapely import LineString, MultiLineString

from parserf.models import FaultModel
from parserf.subsection import FaultSubsection


@pytest.fixture(scope="session")
def sub_0(dataset_31):
    return FaultSubsection(dataset_31, index=0)


class TestFaultSubsectionInit:
    def test_basic_attributes(self, sub_0):
        assert sub_0.fault_model is FaultModel.UCERF3_31
        assert sub_0.index == 0
        assert sub_0.name == "Airport Lake (0)"

    def test_geojson_properties(self, sub_0):
        assert sub_0.parent_id == 1
        assert sub_0.upper_depth == 0.0
        assert sub_0.lower_depth == 13.0
        assert sub_0.dip == 50.0
        assert sub_0.aseismicity == 0.1

    def test_parent_name_lookup(self, sub_0):
        assert sub_0.parent_name == "Airport Lake"

    def test_geometry_is_linestring(self, sub_0):
        assert sub_0.geometry.geom_type == "LineString"

    def test_invalid_index_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No subsection with index"):
            FaultSubsection(dataset_31, index=999999)

    def test_repr(self, sub_0):
        result = repr(sub_0)
        assert "index=0" in result
        assert "Airport Lake (0)" in result


class TestFaultSubsectionComputed:
    def test_length_km_positive(self, sub_0):
        assert sub_0.length_km > 0

    def test_length_km_reasonable(self, sub_0):
        """Subsection trace lengths are typically 1-20 km."""
        assert 0.1 < sub_0.length_km < 50.0

    def test_length_km_matches_pyproj(self, sub_0):
        """Verify length calculation against direct pyproj call."""
        geod = pyproj.Geod(ellps="WGS84")
        expected = geod.geometry_length(sub_0.geometry) / 1000.0
        assert sub_0.length_km == pytest.approx(expected)

    def test_width_km_positive(self, sub_0):
        assert sub_0.width_km > 0

    def test_width_km_formula(self, sub_0):
        """Verify width = (lower - upper) / sin(dip)."""
        expected = (sub_0.lower_depth - sub_0.upper_depth) / np.sin(np.radians(sub_0.dip))
        assert sub_0.width_km == pytest.approx(expected)

    def test_area_km2(self, sub_0):
        assert sub_0.area_km2 == pytest.approx(sub_0.length_km * sub_0.width_km)

    def test_area_km2_positive(self, sub_0):
        assert sub_0.area_km2 > 0


class TestParticipatingRuptures:
    def test_is_geodataframe(self, sub_0):
        assert isinstance(sub_0.participating_ruptures, gpd.GeoDataFrame)

    def test_not_empty(self, sub_0):
        assert len(sub_0.participating_ruptures) > 0

    def test_all_contain_subsection_index(self, sub_0):
        """Every participating rupture's parsed_indices should contain this index."""
        for indices in sub_0.participating_ruptures["parsed_indices"]:
            assert sub_0.index in indices

    def test_has_expected_columns(self, sub_0):
        expected = {
            "m",
            "rate",
            "depth",
            "dip",
            "width",
            "rake",
            "indices",
            "parsed_indices",
            "geometry",
        }
        assert expected.issubset(set(sub_0.participating_ruptures.columns))

    def test_geometries_are_lines(self, sub_0):
        """Each rupture geometry should be a LineString or MultiLineString."""
        for geom in sub_0.participating_ruptures.geometry:
            assert isinstance(geom, (LineString, MultiLineString))

    def test_crs(self, sub_0):
        assert sub_0.participating_ruptures.crs.to_epsg() == 4326


class TestFaultSubsectionMultipleModels:
    def test_first_subsection_loads(self, dataset):
        sub = FaultSubsection(dataset, index=0)
        assert sub.index == 0
        assert sub.length_km > 0
