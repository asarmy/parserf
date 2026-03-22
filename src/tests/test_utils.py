"""Tests for parserf.utils module."""

from parserf.utils import parse_indices


class TestParseIndices:
    """Tests for the parse_indices function."""

    def test_single_index(self):
        """Test parsing a single index."""
        assert parse_indices("42") == {42}

    def test_multiple_individual_indices(self):
        """Test parsing multiple individual indices separated by hyphens."""
        assert parse_indices("1-2-3") == {1, 2, 3}

    def test_range_ascending(self):
        """Test parsing a range in ascending order."""
        assert parse_indices("0:3") == {0, 1, 2, 3}

    def test_range_descending(self):
        """Test parsing a range in descending order (start > end)."""
        assert parse_indices("3:0") == {0, 1, 2, 3}

    def test_single_element_range(self):
        """Test parsing a range with the same start and end."""
        assert parse_indices("5:5") == {5}

    def test_mixed_indices_and_ranges(self):
        """Test parsing both individual indices and ranges."""
        result = parse_indices("0:2-5-10:12")
        assert result == {0, 1, 2, 5, 10, 11, 12}

    def test_complex_example(self):
        """Test the example from the docstring."""
        result = parse_indices("2:0-1127:1126")
        assert result == set(range(0, 3)) | set(range(1126, 1128))

    def test_with_whitespace(self):
        """Test that whitespace in chunks is handled correctly."""
        result = parse_indices("0:2 - 5 - 10:12")
        assert result == {0, 1, 2, 5, 10, 11, 12}

    def test_zero_index(self):
        """Test parsing indices starting from zero."""
        assert parse_indices("0:2") == {0, 1, 2}

    def test_large_indices(self):
        """Test parsing large index numbers."""
        assert parse_indices("1000:1002") == {1000, 1001, 1002}

    def test_empty_result_not_possible(self):
        """Verify that parse_indices always returns a non-empty set."""
        result = parse_indices("0")
        assert len(result) > 0
