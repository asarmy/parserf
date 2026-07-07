"""Tests for FaultModelDataset."""

import pytest


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


def test_packaged_data_contract_all_models(dataset):
    subsection_columns = {
        "parent_id",
        "parent_name",
        "dip",
        "dip_direction",
        "upper_depth_km",
        "lower_depth_km",
        "length_km",
        "width_km",
        "area_km2",
        "geometry",
    }
    rupture_columns = {"m", "rate", "parsed_indices"}

    assert not dataset.subsections.empty
    assert subsection_columns <= set(dataset.subsections.columns)
    assert not dataset.ruptures.empty
    assert rupture_columns <= set(dataset.ruptures.columns)


def test_ruptures_drop_zero_rates_and_preserve_raw_index(dataset_31):
    assert (dataset_31.ruptures["rate"] != 0).all()
    expected_index = dataset_31._ruptures.index[dataset_31._ruptures["rate"] != 0]
    assert dataset_31.ruptures.index.equals(expected_index)
