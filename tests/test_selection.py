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
