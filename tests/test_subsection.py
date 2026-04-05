"""Tests for FaultSubsection, FaultSubsectionData, and FaultSubsectionRuptures."""

import numpy as np
import pyproj
import pytest

from parserf.subsection import FaultSubsection


@pytest.fixture(scope="session")
def sub_0(dataset_31):
    return FaultSubsection(dataset_31, index=0)


class TestFaultSubsection:
    def test_invalid_index_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No subsection with index"):
            FaultSubsection(dataset_31, index=999999)

    def test_geojson_properties(self, sub_0):
        assert sub_0.data.parent_id == 1
        assert sub_0.data.upper_depth_km == 0.0
        assert sub_0.data.lower_depth_km == 13.0
        assert sub_0.data.dip == 50.0
        assert sub_0.data.aseismicity == 0.1

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


class TestCumulativeMFD:
    def test_first_rate_equals_total(self, sub_0):
        """First cumulative rate should equal sum of all participating rupture rates."""
        mfd = sub_0.ruptures.cumulative_mfd
        rups = sub_0.ruptures.participating_ruptures
        unique_rups = rups[~rups.index.duplicated()]
        total_rate = unique_rups["rate"].sum()
        assert mfd["cumulative_rate"].iloc[0] == pytest.approx(total_rate)

    def test_last_rate_equals_largest_mag_rate(self, sub_0):
        """Last cumulative rate should equal the sum of rates at the largest magnitude."""
        mfd = sub_0.ruptures.cumulative_mfd
        rups = sub_0.ruptures.participating_ruptures
        unique_rups = rups[~rups.index.duplicated()]
        max_mag_rate = unique_rups.loc[unique_rups["m"] == unique_rups["m"].max(), "rate"].sum()
        assert mfd["cumulative_rate"].iloc[-1] == pytest.approx(max_mag_rate)
