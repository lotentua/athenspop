# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Configure the public Sphinx documentation for athenspop."""

import pathlib
import sys

#: Repository source directory used by autodoc.
SOURCE_DIRECTORY = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

#: Public project name displayed by Sphinx.
project = "athenspop"
#: Copyright attribution displayed on generated pages.
copyright = "2022 Theodore Chatziioannou; 2026 National Technical University of Athens"
#: Public project authors displayed by Sphinx.
author = "Theodore Chatziioannou and National Technical University of Athens"

#: Sphinx extensions for the Markdown manuals and API reference.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

#: Official object inventories used to link external types in API signatures.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

#: NumPy scalar types that are absent from its published object inventory.
nitpick_ignore = [
    ("py:class", "numpy.float64"),
    ("py:class", "numpy.int64"),
]

#: File extensions treated as documentation sources.
source_suffix = {".md": "markdown"}
#: Root documentation page.
root_doc = "index"
#: Paths omitted from the documentation source tree.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

#: HTML theme used by the public documentation.
html_theme = "pydata_sphinx_theme"
#: Browser title for generated HTML pages.
html_title = "athenspop"
#: Static assets copied into generated documentation.
html_static_path = ["_static"]
#: HTML-theme navigation settings.
html_theme_options = {
    "show_toc_level": 2,
    "navigation_with_keys": False,
}

#: Render type annotations in API descriptions instead of signatures.
autodoc_typehints = "description"
#: Preserve source order in generated API member lists.
autodoc_member_order = "bysource"
#: Interpret public docstrings using Google style.
napoleon_google_docstring = True
#: Disable NumPy-style docstring parsing.
napoleon_numpy_docstring = False

#: MyST features used by the manuals.
myst_enable_extensions = ["colon_fence", "deflist", "dollarmath"]
#: Heading depth exposed for stable fragment links.
myst_heading_anchors = 3
