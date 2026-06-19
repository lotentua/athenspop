"""Sphinx configuration for the athenspop documentation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "athenspop"
author = "Dimitris Mantas"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "design/**",
    "plans/**",
    "../examples/athens/output/**",
]

html_theme = "pydata_sphinx_theme"
html_title = "athenspop"
html_static_path: list[str] = []
html_theme_options = {
    "show_toc_level": 2,
    "navigation_with_keys": False,
}

autodoc_typehints = "description"
autodoc_member_order = "bysource"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
