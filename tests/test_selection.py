"""Tests for ParentSelection."""

import pytest

from parserf.selection import ParentSelection


@pytest.fixture(scope="session")
def selection(dataset_31):
    """ParentSelection for two known parent faults."""
    return ParentSelection(dataset_31, [1, 2])


@pytest.mark.slow
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
        # Find a rupture group that includes a non-selected parent
        grouped = rups.groupby(rups.index)
        found = False
        for rup_id, group in grouped:
            parent_ids = set(group["parent_id"])
            if not parent_ids.issubset(selected):
                found = True
                assert pytest.approx(group["area_pct"].sum(), abs=0.01) == 100.0
                break
        assert found, "Expected at least one rupture with a non-selected parent"
