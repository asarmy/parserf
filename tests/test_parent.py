"""Tests for ParentFault, ParentFaultData, and ParentFaultRuptures."""

import pytest
from pyproj import Geod

from parserf.parent import ParentFault


@pytest.fixture(scope="session")
def parent_fault(dataset_31):
    return ParentFault(dataset_31, name="Airport Lake")


class TestParentFault:
    def test_invalid_name_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No parent fault with name"):
            ParentFault(dataset_31, name="Nonexistent Fault")


class TestParentFaultData:
    def test_all_subsections_belong_to_parent(self, parent_fault, dataset_31):
        """Every subsection in the table should have this parent's ID."""
        table = dataset_31.subsections
        for idx in parent_fault.data.subsections.index:
            assert table.loc[idx, "parent_id"] == parent_fault.data.parent_id

    def test_style_known_result(self, parent_fault):
        assert parent_fault.data.style == "normal"

    def test_dip(self, parent_fault):
        expected = int(round(parent_fault.data.subsections["dip"].mean()))
        assert parent_fault.data.dip == expected
        assert isinstance(parent_fault.data.dip, int)

    def test_surface_trace_right_hand_rule(self, parent_fault):
        """Forward azimuth of trace should be within 90 degrees of (dip_direction - 90)."""
        trace = parent_fault.data.surface_trace
        coords = trace.coords
        geod = Geod(ellps="WGS84")
        az_trace, _, _ = geod.inv(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])
        az_expected = (parent_fault.data.dip_direction - 90) % 360
        diff = ((az_trace - az_expected + 180) % 360) - 180
        assert abs(diff) <= 90


class TestParentFaultRuptures:
    def test_participating_ruptures_area_pcts_sum_to_100(self, parent_fault):
        rups = parent_fault.ruptures.participating_ruptures
        per_rupture = rups.groupby(rups.index)["area_pct"].sum()
        for total in per_rupture:
            assert pytest.approx(total, abs=0.01) == 100.0

    def test_cumulative_mfds_indices_match_subsections(self, parent_fault):
        """MFD indices should match the parent fault's subsection indices."""
        mfd_indices = set(parent_fault.ruptures.cumulative_mfds["index"].unique())
        sub_indices = set(parent_fault.data.subsections.index)
        assert mfd_indices == sub_indices
