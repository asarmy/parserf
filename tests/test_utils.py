"""Tests for parserf._utils module."""

import pandas as pd
import pytest
from shapely.geometry import LineString

from parserf._utils import _cumulative_mfd, _parent_geometry, _parse_indices


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


class TestParentGeometry:
    def test_disjoint_subsections_raise_clear_value_error(self):
        subsections = pd.DataFrame(
            {
                "geometry": [
                    LineString([(0.0, 0.0), (1.0, 0.0)]),
                    LineString([(2.0, 0.0), (3.0, 0.0)]),
                ],
                "dip": [60.0, 60.0],
                "dip_direction": [90.0, 90.0],
                "area_km2": [1.0, 1.0],
            }
        )

        with pytest.raises(
            ValueError,
            match="subsections do not merge into a single contiguous trace",
        ):
            _parent_geometry(subsections)
