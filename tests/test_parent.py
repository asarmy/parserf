"""Tests for ParentFault, ParentFaultData, and ParentFaultRuptures."""

import numpy as np
import pytest

from parserf.parent import ParentFault


@pytest.fixture(scope="session")
def parent_fault(dataset_31):
    return ParentFault(dataset_31, name="Airport Lake")


class TestParentFault:
    def test_repr(self, parent_fault):
        result = repr(parent_fault)
        assert "Airport Lake" in result
        assert "UCERF3_31" in result

    def test_invalid_name_raises(self, dataset_31):
        with pytest.raises(ValueError, match="No parent fault with name"):
            ParentFault(dataset_31, name="Nonexistent Fault")


class TestParentFaultData:
    def test_fault_model(self, parent_fault):
        from parserf.models import FaultModel

        assert parent_fault.data.fault_model is FaultModel.UCERF3_31

    def test_name(self, parent_fault):
        assert parent_fault.data.name == "Airport Lake"

    def test_subsections_has_expected_columns(self, parent_fault):
        expected = {
            "name",
            "dip",
            "dip_direction",
            "upper_depth_km",
            "lower_depth_km",
            "aseismicity",
            "length_km",
            "width_km",
            "area_km2",
            "geometry",
        }
        assert expected == set(parent_fault.data.subsections.columns)

    def test_subsections_index_name(self, parent_fault):
        assert parent_fault.data.subsections.index.name == "index"

    def test_all_subsections_belong_to_parent(self, parent_fault, dataset_31):
        """Every subsection in the table should have this parent's ID."""
        table = dataset_31._subsection_table
        for idx in parent_fault.data.subsections.index:
            assert table.loc[idx, "parent-id"] == parent_fault.data.parent_id

    def test_style_known_result(self, parent_fault):
        assert parent_fault.data.style == "normal"

    def test_style_counts_has_expected_columns(self, parent_fault):
        assert list(parent_fault.data.style_counts.columns) == ["style", "count"]

    def test_style_counts_sorted_descending(self, parent_fault):
        counts = parent_fault.data.style_counts["count"].to_numpy()
        assert (np.diff(counts) <= 0).all()

    def test_style_matches_top_count(self, parent_fault):
        assert parent_fault.data.style == parent_fault.data.style_counts["style"].iloc[0]


class TestParentFaultRuptures:
    def test_cumulative_mfds_has_expected_columns(self, parent_fault):
        expected = ["index", "magnitude", "cumulative_rate"]
        assert list(parent_fault.ruptures.cumulative_mfds.columns) == expected

    def test_cumulative_mfds_indices_match_subsections(self, parent_fault):
        """MFD indices should match the parent fault's subsection indices."""
        mfd_indices = set(parent_fault.ruptures.cumulative_mfds["index"].unique())
        sub_indices = set(parent_fault.data.subsections.index)
        assert mfd_indices == sub_indices

    def test_magnitudes_sorted_per_index(self, parent_fault):
        """Magnitudes should be sorted ascending within each subsection."""
        for _, group in parent_fault.ruptures.cumulative_mfds.groupby("index"):
            mags = group["magnitude"].to_numpy()
            assert (np.diff(mags) >= 0).all()

    def test_cumulative_rates_non_increasing_per_index(self, parent_fault):
        """Cumulative rates should be non-increasing within each subsection."""
        for _, group in parent_fault.ruptures.cumulative_mfds.groupby("index"):
            rates = group["cumulative_rate"].to_numpy()
            assert (np.diff(rates) <= 0).all()
