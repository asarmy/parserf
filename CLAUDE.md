CRITICAL: Never use system Python. Always use the project's uv-managed .venv (use `uv run` instead of calling `python` directly).

Use Google style docstrings. Line length is 99.

For scripts, include module docstrings in this format (line length is 99):
"""
Create a database table, if it does not exist, and upsert CSV data into it.

This script performs the following steps:
1. Optionally backs up the current database before making changes.
2. Loads a SQLAlchemy ORM class by its table or class name.
3. Validates the existence and format of the provided CSV file.
4. Creates the corresponding database table if it doesn't exist.
5. Performs an "upsert" operation: inserts new rows or updates existing ones.

Usage
-----
Run this script from the project root directory:
    uv run python dbtools/import_table.py <table_name> <csv_path> <description> [--backup]

Example
-------
    uv run python dbtools/import_table.py uscs data/uscs.csv "initial USCS data import"
    uv run python dbtools/import_table.py gradation_summary data/gradation.csv "Q4 lab results" --backup
"""
