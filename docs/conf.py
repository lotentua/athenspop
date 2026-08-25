# Copyright (c) 2022 Theodore Chatziioannou
# Copyright (c) 2026 National Technical University of Athens
# Licensed under the MIT License.

"""Configure the public Sphinx documentation for athenspop."""

import pathlib
import sys

#: This path identifies the repository source directory used by autodoc.
SOURCE_DIRECTORY = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

#: Sphinx displays this public project name.
project = "athenspop"
#: Generated pages display this copyright attribution.
copyright = "2022 Theodore Chatziioannou; 2026 National Technical University of Athens"
#: Sphinx displays these public project authors.
author = "Theodore Chatziioannou and National Technical University of Athens"

#: These Sphinx extensions support the Markdown manuals and API reference.
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

#: Sphinx treats these file extensions as documentation sources.
source_suffix = {".md": "markdown"}
#: This value identifies the root documentation page.
root_doc = "index"
#: Sphinx omits these paths from the documentation source tree.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

#: The public documentation uses this HTML theme.
html_theme = "pydata_sphinx_theme"
#: Generated HTML pages use this browser title.
html_title = "athenspop"
#: Sphinx copies these static assets into the generated documentation.
html_static_path = ["_static"]
#: These values configure navigation in the HTML theme.
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

#: The manuals use these MyST features.
myst_enable_extensions = ["colon_fence", "deflist", "dollarmath"]
#: This value controls the heading depth exposed for stable fragment links.
myst_heading_anchors = 3
