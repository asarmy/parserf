"""Tests for spatial and rupture query functions."""

from types import SimpleNamespace

import geopandas as gpd
import pandas as pd
import pyproj
import pytest
from shapely.geometry import LineString

from parserf._utils import _subsection_geometry_3d
from parserf.queries import (
    get_nearest_subsection_index,
    get_parents_list,
    get_ruptures_near,
    get_subsections_list,
)


@pytest.mark.slow
class TestSpatialQueries:
    def test_get_nearest_subsection_index_known_result(self, dataset_31):
        """A coordinate on a subsection's own trace should resolve to that subsection.

        Distance is now measured to each subsection's map-view footprint (see
        ``_distances_km``), so an off-trace coordinate can resolve to a dipping neighbor whose
        down-dip footprint reaches it (e.g. -117.60, 35.77 now resolves to Airport Lake, not
        Little Lake, because Airport Lake's dip extends its footprint toward that point). Pin
        this test to a point directly on the Little Lake trace, which stays unambiguous.
        """
        idx = get_nearest_subsection_index(dataset_31, lat=35.74744, lon=-117.75892)
        name = dataset_31.subsections.loc[idx, "name"]
        assert "Little Lake" in name

    def test_get_parents_list_contains_nearest_parent(self, dataset_31):
        """The nearest subsection's parent should be first."""
        nearest = get_nearest_subsection_index(dataset_31, lat=35.77, lon=-117.60)
        parent_id = int(dataset_31.subsections.loc[nearest, "parent_id"])
        result = get_parents_list(dataset_31, lat=35.77, lon=-117.60, dist_km=50.0)
        assert result[0] == parent_id

    def test_geodesic_distance_controls_nearest_and_radius_membership(self):
        """Geodesic distances should not be approximated by east-west degree lengths."""
        lat = 36.0
        lon = -120.0
        subsections = gpd.GeoDataFrame(
            {
                "parent_id": [1, 2],
                "geometry": [
                    LineString([(lon + 1.0, lat), (lon + 1.0, lat + 0.01)]),
                    LineString([(lon, lat + 0.95), (lon + 0.01, lat + 0.95)]),
                ],
            },
            index=[10, 20],
            crs="EPSG:4326",
        )
        # These subsections are vertical (no dip/depth columns), so their footprint is just the
        # trace itself; _distances_km reads dataset._subsection_footprints.
        dataset = SimpleNamespace(
            subsections=subsections, _subsection_footprints=subsections["geometry"]
        )

        geod = pyproj.Geod(ellps="WGS84")
        _, _, east_dist_m = geod.inv(lon, lat, lon + 1.0, lat)
        _, _, north_dist_m = geod.inv(lon, lat, lon, lat + 0.95)
        assert east_dist_m / 1000.0 < 100.0
        assert north_dist_m / 1000.0 > 100.0

        assert get_nearest_subsection_index(dataset, lat=lat, lon=lon) == 10
        assert get_subsections_list(dataset, lat=lat, lon=lon, dist_km=100.0) == [10]

    def test_get_subsections_list_matches_footprint_beyond_trace(self):
        """A site over the down-dip footprint should match even far from the trace itself."""
        lat, lon = 36.0, -120.0
        trace = LineString([(lon, lat), (lon + 0.1, lat)])
        row = pd.Series(
            {
                "geometry": trace,
                "upper_depth_km": 0.0,
                "lower_depth_km": 15.0,
                "dip": 20.0,
                "dip_direction": 0.0,  # dips due north
            }
        )
        footprint = _subsection_geometry_3d(row)  # extends ~41 km north of the trace

        subsections = gpd.GeoDataFrame(
            {"parent_id": [1], "geometry": [trace]}, index=[10], crs="EPSG:4326"
        )
        footprints = gpd.GeoSeries([footprint], index=[10], crs="EPSG:4326")
        dataset = SimpleNamespace(subsections=subsections, _subsection_footprints=footprints)

        # Site 30 km due north of the trace: over the footprint, but far from the trace itself.
        geod = pyproj.Geod(ellps="WGS84")
        site_lon, site_lat, _ = geod.fwd(lon, lat, 0.0, 30_000.0)

        assert get_subsections_list(dataset, lat=site_lat, lon=site_lon, dist_km=5.0) == [10]


class TestEmptyResults:
    """Query functions should return well-formed empty results for remote coordinates."""

    def test_get_ruptures_near_empty(self, dataset_31):
        result = get_ruptures_near(dataset_31, lat=0.0, lon=0.0, dist_km=1.0)
        assert result.empty
        expected_cols = {
            "m",
            "rate",
            "depth",
            "dip",
            "width",
            "rake",
            "geometry",
            "length_km",
            "area_km2",
            "contributions",
        }
        assert set(result.columns) == expected_cols
        assert str(result.crs) == "EPSG:4326"
