"""Tests for FaultModel enum and FaultModelDataset."""

import pytest

from parserf.models import FaultModel


class TestFaultModel:
    def test_shorthand_values(self):
        assert FaultModel.NSHMP_2023 == 2023
        assert FaultModel.UCERF3_31 == 31
        assert FaultModel.UCERF3_32 == 32

    def test_construction_from_int(self):
        assert FaultModel(31) is FaultModel.UCERF3_31
        assert FaultModel(32) is FaultModel.UCERF3_32
        assert FaultModel(2023) is FaultModel.NSHMP_2023

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            FaultModel(999)


@pytest.mark.slow
class TestFaultModelDataset:
    def test_ruptures_parsed_has_parsed_indices(self, dataset):
        df = dataset.ruptures_parsed
        assert "parsed_indices" in df.columns
        assert isinstance(df["parsed_indices"].iloc[0], set)

    def test_nearest_index_returns_valid_index(self, dataset):
        """Returned index exists in the sections GeoDataFrame."""
        idx = dataset.nearest_index(lat=35.77, lon=-117.60)
        assert idx in dataset.sections["index"].values

    def test_nearest_index_known_result(self, dataset_31):
        """Coordinate near Ridgecrest should return Little Lake subsection."""
        idx = dataset_31.nearest_index(lat=35.77, lon=-117.60)
        name = dataset_31.sections.set_index("index").loc[idx, "name"]
        assert "Little Lake" in name

    def test_get_parent_id_known_result(self, dataset_31):
        assert dataset_31.get_parent_id(name="Airport Lake") == 1

    def test_get_parent_id_invalid_name_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No parent fault with name"):
            dataset_31.get_parent_id(name="Nonexistent Fault")
