"""Tests for parserf._utils module."""

import pandas as pd
import pytest

from parserf._utils import _cumulative_mfd, _parent_style, _parse_indices


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


class TestParseIndices:
    def test_basic_parsing(self):
        """Single values, multiple values, and ranges."""
        assert _parse_indices("42") == {42}
        assert _parse_indices("1-2-3") == {1, 2, 3}
        assert _parse_indices("0:3") == {0, 1, 2, 3}
        assert _parse_indices("3:0") == {0, 1, 2, 3}
        assert _parse_indices("5:5") == {5}

    def test_mixed_indices_and_ranges(self):
        assert _parse_indices("0:2-5-10:12") == {0, 1, 2, 5, 10, 11, 12}


class TestParentStyle:
    def test_returns_dominant_style(self):
        rakes = pd.DataFrame(
            {
                "parent_id": [1, 1, 1],
                "style": ["Reverse", "Strike-Slip", "Reverse"],
                "count": [50, 30, 20],
            }
        )
        assert _parent_style(rakes, 1) == "Reverse"
