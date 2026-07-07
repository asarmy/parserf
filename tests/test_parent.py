"""Tests for ParentFault, ParentFaultData, and ParentFaultRuptures."""

import pandas as pd
import pytest
from pyproj import Geod

from parserf.parent import ParentFault
from parserf.subsection import FaultSubsection


@pytest.fixture(scope="session")
def parent_fault(dataset_31):
    return ParentFault(dataset_31, name="Compton")


class TestParentFaultData:
    """Specific tests for Compton fault in UCERF3.1."""

    def test_geometry_right_hand_rule(self, parent_fault):
        """Forward azimuth of trace should be within 90 degrees of (dip_direction - 90)."""
        coords = parent_fault.data.geometry.coords
        subs = parent_fault.data.subsections
        weights = subs["area_km2"]
        dip_direction = (subs["dip_direction"] * weights).sum() / weights.sum()
        geod = Geod(ellps="WGS84")
        az_trace, _, _ = geod.inv(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])
        az_expected = (dip_direction - 90) % 360
        diff = ((az_trace - az_expected + 180) % 360) - 180
        assert abs(diff) <= 90


class TestParentFaultRuptures:
    def test_participating_ruptures_area_pcts_sum_to_100(self, parent_fault):
        """Each rupture's per-parent contributions cover 100% of its area."""
        rups = parent_fault.ruptures.participating_ruptures
        for contributions in rups["contributions"]:
            total = sum(area_pct for _, area_pct in contributions)
            assert pytest.approx(total, abs=0.01) == 100.0

    def test_explode_contributions_recipe(self, parent_fault):
        """The documented explode recipe yields one row per (rupture, parent), pcts sum to 100."""
        rups = parent_fault.ruptures.participating_ruptures
        exploded = rups.explode("contributions")
        exploded[["parent_id", "area_pct"]] = pd.DataFrame(
            exploded["contributions"].tolist(), index=exploded.index
        )
        # One exploded row per (rupture, parent) contribution.
        assert len(exploded) == sum(len(c) for c in rups["contributions"])
        # area_pct still sums to 100 per rupture once flattened.
        per_rupture = exploded.groupby(exploded.index)["area_pct"].sum()
        assert (per_rupture - 100.0).abs().max() < 0.01

    def test_mfd_consistent_with_subsection_api(self, parent_fault, dataset_31):
        """Per-subsection MFD from ParentFault should match FaultSubsection API."""
        mfds = parent_fault.ruptures.cumulative_mfds
        parent_mfd = mfds[mfds["index"] == 341].reset_index(drop=True)
        sub_mfd = FaultSubsection(dataset_31, index=341).ruptures.cumulative_mfd
        assert list(parent_mfd["magnitude"]) == list(sub_mfd["magnitude"])
        assert list(parent_mfd["cumulative_rate"]) == pytest.approx(
            list(sub_mfd["cumulative_rate"])
        )


class TestParentGeometry3d:
    def test_single_polygon_z_no_holes(self, parent_fault):
        poly = parent_fault.data.geometry_3d
        assert poly.geom_type == "Polygon"
        assert poly.has_z
        assert len(list(poly.interiors)) == 0

    def test_depth_range_spans_subsections(self, parent_fault):
        """PolygonZ depths span the child subsections' upper..lower depth range."""
        subs = parent_fault.data.subsections
        zs = [z for *_, z in parent_fault.data.geometry_3d.exterior.coords]
        assert min(zs) == pytest.approx(subs["upper_depth_km"].min())
        assert max(zs) == pytest.approx(subs["lower_depth_km"].max())

    def test_top_edge_matches_2d_trace(self, parent_fault):
        """The top half of the ring reproduces the oriented 2D surface trace vertices."""
        trace_coords = [(x, y) for x, y, *_ in parent_fault.data.geometry.coords]
        ring = list(parent_fault.data.geometry_3d.exterior.coords)
        top = [(x, y) for x, y, _ in ring[: len(trace_coords)]]
        assert top == pytest.approx(trace_coords)
