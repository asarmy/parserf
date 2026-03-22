"""Shared utility functions for parserf data processing scripts."""


def parse_indices(indices_str: str) -> set[int]:
    """Parse earthquake rupture forecast scenario rupture index strings.

    Converts strings like "2:0-1127:1126" into sets of integers like "{0, 1, 2, 1126, 1127}".

    Args:
        indices_str: String representation of one or multiple ranges.

    Returns:
        Set of all indices implied by indices_str.
    """
    chunks = indices_str.split("-")
    indices = set()
    for chunk in chunks:
        chunk = chunk.strip()
        if ":" in chunk:
            start_str, end_str = chunk.split(":")
            start, end = int(start_str), int(end_str)
            xmin, xmax = min(start, end), max(start, end)
            indices.update(range(xmin, xmax + 1))
        else:
            indices.add(int(chunk))
    return indices
