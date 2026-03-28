"""Tests for FaultSubsection, FaultSubsectionData, and FaultSubsectionRuptures."""

import numpy as np
import pyproj
import pytest
from shapely import LineString, MultiLineString

from parserf.models import FaultModel
from parserf.subsection import FaultSubsection, FaultSubsectionData


@pytest.fixture(scope="session")
def sub_0(dataset_31):
    return FaultSubsection(dataset_31, index=0)


class TestFaultSubsectionInit:
    def test_index_attribute(self, sub_0):
        assert sub_0.index == 0

    def test_invalid_index_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No subsection with index"):
            FaultSubsection(dataset_31, index=999999)

    def test_repr(self, sub_0):
        result = repr(sub_0)
        assert "index=0" in result
        assert "Airport Lake (0)" in result


class TestFaultSubsectionData:
    def test_basic_attributes(self, sub_0):
        assert sub_0.data.fault_model is FaultModel.UCERF3_31
        assert sub_0.data.index == 0
        assert sub_0.data.name == "Airport Lake (0)"

    def test_geojson_properties(self, sub_0):
        assert sub_0.data.parent_id == 1
        assert sub_0.data.upper_depth_km == 0.0
        assert sub_0.data.lower_depth_km == 13.0
        assert sub_0.data.dip == 50.0
        assert sub_0.data.aseismicity == 0.1

    def test_parent_name_lookup(self, sub_0):
        assert sub_0.data.parent_name == "Airport Lake"

    def test_geometry_is_linestring(self, sub_0):
        assert sub_0.data.geometry.geom_type == "LineString"

    def test_length_km_matches_pyproj(self, sub_0):
        """Verify length calculation against direct pyproj call."""
        geod = pyproj.Geod(ellps="WGS84")
        expected = geod.geometry_length(sub_0.data.geometry) / 1000.0
        assert sub_0.data.length_km == pytest.approx(expected)

    def test_width_km_formula(self, sub_0):
        """Verify width = (lower - upper) / sin(dip)."""
        expected = (sub_0.data.lower_depth_km - sub_0.data.upper_depth_km) / np.sin(
            np.radians(sub_0.data.dip)
        )
        assert sub_0.data.width_km == pytest.approx(expected)

    def test_area_km2(self, sub_0):
        assert sub_0.data.area_km2 == pytest.approx(sub_0.data.length_km * sub_0.data.width_km)


class TestParticipatingRuptures:
    def test_all_contain_subsection_index(self, sub_0):
        """Every participating rupture's parsed_indices should contain this index."""
        for indices in sub_0.ruptures.participating_ruptures["parsed_indices"]:
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
            "length_km",
            "area_km2",
            "parent_area_pcts",
            "geometry",
        }
        assert expected.issubset(set(sub_0.ruptures.participating_ruptures.columns))

    def test_geometries_are_lines(self, sub_0):
        """Each rupture geometry should be a LineString or MultiLineString."""
        for geom in sub_0.ruptures.participating_ruptures.geometry:
            assert isinstance(geom, (LineString, MultiLineString))

    def test_length_km_equals_subsection_sum(self, sub_0, dataset_31):
        """Verify rupture length equals sum of constituent subsection lengths."""
        row = sub_0.ruptures.participating_ruptures.iloc[0]
        expected = sum(FaultSubsectionData(dataset_31, i).length_km for i in row["parsed_indices"])
        assert row["length_km"] == pytest.approx(expected)

    def test_area_km2_equals_subsection_sum(self, sub_0, dataset_31):
        """Verify rupture area equals sum of constituent subsection areas."""
        row = sub_0.ruptures.participating_ruptures.iloc[0]
        expected = sum(FaultSubsectionData(dataset_31, i).area_km2 for i in row["parsed_indices"])
        assert row["area_km2"] == pytest.approx(expected)

    def test_parent_area_pcts_sum_to_100(self, sub_0):
        """Each rupture's parent area percentages should sum to 100."""
        for pcts in sub_0.ruptures.participating_ruptures["parent_area_pcts"]:
            assert pytest.approx(sum(pcts.values()), abs=0.01) == 100.0

    def test_parent_area_pcts_contains_parent(self, sub_0):
        """This subsection's parent name should appear in at least one rupture."""
        assert any(
            sub_0.data.parent_name in pcts
            for pcts in sub_0.ruptures.participating_ruptures["parent_area_pcts"]
        )

    def test_crs(self, sub_0):
        assert sub_0.ruptures.participating_ruptures.crs.to_epsg() == 4326


class TestCumulativeMFD:
    def test_has_expected_columns(self, sub_0):
        assert list(sub_0.ruptures.cumulative_mfd.columns) == ["magnitude", "cumulative_rate"]

    def test_magnitudes_sorted_ascending(self, sub_0):
        mags = sub_0.ruptures.cumulative_mfd["magnitude"].to_numpy()
        assert (np.diff(mags) >= 0).all()

    def test_cumulative_rates_non_increasing(self, sub_0):
        rates = sub_0.ruptures.cumulative_mfd["cumulative_rate"].to_numpy()
        assert (np.diff(rates) <= 0).all()

    def test_first_rate_equals_total(self, sub_0):
        """First cumulative rate should equal sum of all participating rupture rates."""
        mfd = sub_0.ruptures.cumulative_mfd
        total_rate = sub_0.ruptures.participating_ruptures["rate"].sum()
        assert mfd["cumulative_rate"].iloc[0] == pytest.approx(total_rate)

    def test_magnitudes_are_unique(self, sub_0):
        mfd = sub_0.ruptures.cumulative_mfd
        assert mfd["magnitude"].nunique() == len(mfd)

    def test_last_rate_equals_largest_mag_rate(self, sub_0):
        """Last cumulative rate should equal the sum of rates at the largest magnitude."""
        mfd = sub_0.ruptures.cumulative_mfd
        rups = sub_0.ruptures.participating_ruptures
        max_mag_rate = rups.loc[rups["m"] == rups["m"].max(), "rate"].sum()
        assert mfd["cumulative_rate"].iloc[-1] == pytest.approx(max_mag_rate)
