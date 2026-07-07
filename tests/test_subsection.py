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


class TestGeometry3d:
    def test_is_polygon_z(self, sub_0):
        poly = sub_0.data.geometry_3d
        assert poly.geom_type == "Polygon"
        assert poly.has_z
        assert len(list(poly.interiors)) == 0

    def test_edge_depths(self, sub_0):
        """Top edge sits at upper depth, bottom edge at lower depth."""
        coords = list(sub_0.data.geometry_3d.exterior.coords)
        n = len(sub_0.data.geometry.coords)
        top = coords[:n]
        bottom = coords[n:-1]  # drop the closing vertex
        assert all(z == pytest.approx(sub_0.data.upper_depth_km) for *_, z in top)
        assert all(z == pytest.approx(sub_0.data.lower_depth_km) for *_, z in bottom)

    def test_downdip_offset_matches_width(self, sub_0):
        """Slant distance between a top vertex and its bottom vertex equals width_km."""
        coords = list(sub_0.data.geometry_3d.exterior.coords)
        n = len(sub_0.data.geometry.coords)
        lon_t, lat_t, _ = coords[0]
        lon_b, lat_b, _ = coords[2 * n - 1]  # bottom vertex paired with first top vertex
        geod = pyproj.Geod(ellps="WGS84")
        _, _, horiz_m = geod.inv(lon_t, lat_t, lon_b, lat_b)
        dz_m = (sub_0.data.lower_depth_km - sub_0.data.upper_depth_km) * 1000.0
        slant_km = np.hypot(horiz_m, dz_m) / 1000.0
        assert slant_km == pytest.approx(sub_0.data.width_km, rel=1e-3)

    def test_vertical_fault_has_no_horizontal_offset(self, dataset_31):
        """For a near-vertical subsection, the bottom edge sits under the top edge."""
        subs = dataset_31.subsections
        idx = (subs["dip"] - 90.0).abs().idxmin()
        assert abs(subs.loc[idx, "dip"] - 90.0) <= 1.0
        sub = FaultSubsection(dataset_31, index=int(idx))
        coords = list(sub.data.geometry_3d.exterior.coords)
        n = len(sub.data.geometry.coords)
        lon_t, lat_t, _ = coords[0]
        lon_b, lat_b, _ = coords[2 * n - 1]
        assert lon_b == pytest.approx(lon_t)
        assert lat_b == pytest.approx(lat_t)


class TestCumulativeMFD:
    def test_first_rate_equals_total(self, sub_0):
        """First cumulative rate should equal sum of all participating rupture rates."""
        mfd = sub_0.ruptures.cumulative_mfd
        rups = sub_0.ruptures.participating_ruptures
        total_rate = rups["rate"].sum()
        assert mfd["cumulative_rate"].iloc[0] == pytest.approx(total_rate)
