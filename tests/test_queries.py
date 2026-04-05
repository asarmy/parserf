"""Tests for spatial and rupture query functions."""

import pytest

from parserf.queries import (
    get_nearest_subsection_index,
    get_parents_list,
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
