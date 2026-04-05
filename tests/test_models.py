"""Tests for FaultModelDataset."""

import pytest


@pytest.mark.slow
class TestFaultModelDataset:
    def test_get_parent_fault_id_known_result(self, dataset_31):
        assert dataset_31.get_parent_fault_id(name="Airport Lake") == 1

    def test_get_parent_fault_id_invalid_name_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No parent fault with name"):
            dataset_31.get_parent_fault_id(name="Nonexistent Fault")

    def test_grid_loads_for_all_models(self, dataset):
        grid = dataset.grid
        assert len(grid) > 0
        assert "lon" in grid.columns and "lat" in grid.columns
