"""Sphinx configuration for the parserf documentation site."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version

# -- Project information -----------------------------------------------------

project = "parserf"
author = "Alex Sarmiento"
copyright = f"2026, {author}"
release = _pkg_version("parserf")
version = release

# -- General configuration ----------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_nb",  # supersedes myst_parser (which it depends on): adds .ipynb rendering
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- MyST-NB (notebook rendering) ----------------------------------------------

# The example notebooks are committed with their outputs already populated (plots, tables) —
# render those stored outputs as-is rather than re-executing on every docs build. Re-executing
# would require the full example-notebook dependency stack (matplotlib, ipykernel) plus loading
# real fault model datasets during the Read the Docs build.
nb_execution_mode = "off"

# -- Autodoc / Napoleon --------------------------------------------------------

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
add_module_names = False

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
# Render class-level "Attributes:" sections as a field list (:ivar:) rather than as
# `.. attribute::` directives — the latter register objects that collide with the real
# @property / @cached_property members autodoc already documents via `:members:`.
napoleon_use_ivar = True

# -- Intersphinx ----------------------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable/", None),
}

# -- HTML output ----------------------------------------------------------------

html_theme = "renku"
html_theme_options = {
    "logo_only": False,
    "collapse_navigation": True,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
}
html_context = {
    "display_github": True,
    "github_user": "asarmy",
    "github_repo": "parserf",
    "github_version": "main",
    "conf_py_path": "/docs/",
}
html_static_path = ["_static"]
html_css_files = ["notebook-output.css"]
