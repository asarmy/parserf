"""Tests for spatial and rupture query functions."""

import pytest

from parserf.queries import (
    get_nearest_subsection_index,
    get_parents_list,
    get_ruptures_near,
    get_subsections_list,
)


@pytest.mark.slow
class TestSpatialQueries:
    def test_get_nearest_subsection_index_known_result(self, dataset_31):
        """Coordinate near Ridgecrest should return Little Lake subsection."""
        idx = get_nearest_subsection_index(dataset_31, lat=35.77, lon=-117.60)
        name = dataset_31.subsections.loc[idx, "name"]
        assert "Little Lake" in name

    def test_get_subsections_list_contains_nearest(self, dataset_31):
        """The nearest subsection should appear in a sufficiently large radius."""
        nearest = get_nearest_subsection_index(dataset_31, lat=35.77, lon=-117.60)
        result = get_subsections_list(dataset_31, lat=35.77, lon=-117.60, dist_km=50.0)
        assert nearest == result[0]

    def test_get_parents_list_contains_nearest_parent(self, dataset_31):
        """The nearest subsection's parent should be first."""
        nearest = get_nearest_subsection_index(dataset_31, lat=35.77, lon=-117.60)
        parent_id = int(dataset_31.subsections.loc[nearest, "parent_id"])
        result = get_parents_list(dataset_31, lat=35.77, lon=-117.60, dist_km=50.0)
        assert result[0] == parent_id

    def test_get_parents_list_unique_ids(self, dataset_31):
        """Returned parent IDs should have no duplicates."""
        result = get_parents_list(dataset_31, lat=35.77, lon=-117.60, dist_km=50.0)
        assert len(result) == len(set(result))


class TestEmptyResults:
    """Query functions should return well-formed empty results for remote coordinates."""

    def test_get_subsections_list_empty(self, dataset_31):
        assert get_subsections_list(dataset_31, lat=0.0, lon=0.0, dist_km=1.0) == []

    def test_get_parents_list_empty(self, dataset_31):
        assert get_parents_list(dataset_31, lat=0.0, lon=0.0, dist_km=1.0) == []

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
            "parent_id",
            "area_pct",
        }
        assert set(result.columns) == expected_cols
        assert str(result.crs) == "EPSG:4326"
