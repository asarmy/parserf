"""Tests for parserf.utils module."""

import numpy as np
import pandas as pd
import pytest

from parserf.utils import _cumulative_mfd, _parse_indices


class TestCumulativeMfd:
    def test_cumulative_rates(self):
        df = pd.DataFrame({"m": [6.0, 6.5, 7.0], "rate": [0.01, 0.005, 0.001]})
        result = _cumulative_mfd(df)
        assert result["cumulative_rate"].iloc[0] == pytest.approx(0.016)
        assert result["cumulative_rate"].iloc[1] == pytest.approx(0.006)
        assert result["cumulative_rate"].iloc[2] == pytest.approx(0.001)

    def test_groups_duplicate_magnitudes(self):
        df = pd.DataFrame({"m": [6.0, 6.0, 7.0], "rate": [0.01, 0.02, 0.005]})
        result = _cumulative_mfd(df)
        assert len(result) == 2
        assert result["cumulative_rate"].iloc[0] == pytest.approx(0.035)

    def test_magnitudes_sorted_ascending(self):
        df = pd.DataFrame({"m": [7.0, 6.0, 6.5], "rate": [0.001, 0.01, 0.005]})
        result = _cumulative_mfd(df)
        mags = result["magnitude"].to_numpy()
        assert (np.diff(mags) >= 0).all()

    def test_rates_non_increasing(self):
        df = pd.DataFrame({"m": [6.0, 6.5, 7.0], "rate": [0.01, 0.005, 0.001]})
        result = _cumulative_mfd(df)
        rates = result["cumulative_rate"].to_numpy()
        assert (np.diff(rates) <= 0).all()


class TestParseIndices:
    """Tests for the _parse_indices function."""

    def test_basic_parsing(self):
        """Single values, multiple values, and ranges."""
        assert _parse_indices("42") == {42}
        assert _parse_indices("1-2-3") == {1, 2, 3}
        assert _parse_indices("0:3") == {0, 1, 2, 3}
        assert _parse_indices("3:0") == {0, 1, 2, 3}
        assert _parse_indices("5:5") == {5}

    def test_mixed_indices_and_ranges(self):
        assert _parse_indices("0:2-5-10:12") == {0, 1, 2, 5, 10, 11, 12}

    def test_docstring_example(self):
        result = _parse_indices("2:0-1127:1126")
        assert result == set(range(0, 3)) | set(range(1126, 1128))

    def test_whitespace_handling(self):
        assert _parse_indices("0:2 - 5 - 10:12") == {0, 1, 2, 5, 10, 11, 12}
