"""Tests for ParentSelection and GridSelection."""

import pytest

from parserf.selection import GridSelection, ParentSelection


@pytest.fixture(scope="session")
def selection(dataset_31):
    """ParentSelection for two known parent faults."""
    return ParentSelection(dataset_31, [1, 2])


class TestParentSelection:
    def test_invalid_parent_id_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No parent fault with id"):
            ParentSelection(dataset_31, [999999])

    def test_empty_parent_ids_raises(self, dataset_31):
        with pytest.raises(ValueError, match="must not be empty"):
            ParentSelection(dataset_31, [])

    def test_preserves_input_order(self, selection):
        assert list(selection.parents.index) == [1, 2]

    def test_ruptures_include_non_selected_parents(self, selection):
        """Ruptures should include all parent contributions, not just selected parents."""
        rups = selection.ruptures
        selected = {1, 2}
        # Find a rupture whose contributions include a non-selected parent
        found = False
        for contributions in rups["contributions"]:
            parent_ids = {pid for pid, _ in contributions}
            if not parent_ids.issubset(selected):
                found = True
                total = sum(area_pct for _, area_pct in contributions)
                assert pytest.approx(total, abs=0.01) == 100.0
                break
        assert found, "Expected at least one rupture with a non-selected parent"


class TestGridSelection:
    def test_all_points_within_radius(self, dataset_31):
        dist_km = 50
        gs = GridSelection(dataset_31, lat=34.05, lon=-118.25, dist_km=dist_km)
        grid = gs.grid
        assert len(grid) > 0
        assert (grid["dist_km"] <= dist_km).all()
        assert grid["dist_km"].is_monotonic_increasing
