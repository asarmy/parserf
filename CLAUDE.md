CRITICAL: Never use system Python. Always use the project's uv-managed .venv (use `uv run` instead of calling `python` directly).

Use Google style docstrings. Line length is 99.

For scripts, include module docstrings in this format (line length is 99):
"""
Short description (e.g., Delete specific records from a table by primary key.)

Usage
-----
Run this script from the project root directory:
    uv run python dbtools/delete_records.py <table_name> <primary_keys...> -d <description> [--backup]

Examples
--------
    uv run python dbtools/delete_records.py unit_weight_moisture_content 88 89 90 -d "Remove bad data"
    uv run python dbtools/delete_records.py geology $(seq 1 200) -d "Flush geology records to start over"
"""
