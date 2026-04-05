"""Tests for ParentFault, ParentFaultData, and ParentFaultRuptures."""

import pytest
from pyproj import Geod

from parserf.parent import ParentFault
from parserf.subsection import FaultSubsection


@pytest.fixture(scope="session")
def parent_fault(dataset_31):
    return ParentFault(dataset_31, name="Compton")


class TestParentFaultData:
    """Specific tests for Compton fault in UCERF3.1."""

    def test_parent_id(self, parent_fault):
        assert parent_fault.data.parent_id == 43

    def test_style_known_result(self, parent_fault):
        assert parent_fault.data.style == "reverse"

    def test_dip(self, parent_fault):
        assert parent_fault.data.dip == 20
        assert isinstance(parent_fault.data.dip, int)

    def test_subsection_indices(self, parent_fault):
        assert set(parent_fault.data.subsections.index) == {341, 342, 343, 344, 345}

    def test_surface_trace_orientation(self, parent_fault):
        """Dip is to the right, so trace should run south-to-north (first lat < last lat)."""
        trace = parent_fault.data.surface_trace
        coords = trace.coords
        assert coords[0][1] < coords[-1][1]

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

    def test_mfd_consistent_with_subsection_api(self, parent_fault, dataset_31):
        """Per-subsection MFD from ParentFault should match FaultSubsection API."""
        mfds = parent_fault.ruptures.cumulative_mfds
        parent_mfd = mfds[mfds["index"] == 341].reset_index(drop=True)
        sub_mfd = FaultSubsection(dataset_31, index=341).ruptures.cumulative_mfd
        assert list(parent_mfd["magnitude"]) == list(sub_mfd["magnitude"])
        assert list(parent_mfd["cumulative_rate"]) == pytest.approx(
            list(sub_mfd["cumulative_rate"])
        )
