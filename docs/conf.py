"""Sphinx configuration for the openNASR documentation."""

from importlib.metadata import version as distribution_version
import os


project = "openNASR"
author = "Adan E Vela"
release = distribution_version("openNASR")

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]

autoclass_content = "both"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "show-inheritance": True,
    "undoc-members": True,
}
autodoc_typehints = "description"

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
root_doc = "index"

html_theme = "furo"

intersphinx_mapping = (
    {}
    if os.environ.get("OPENNASR_DOCS_OFFLINE")
    else {
        "python": ("https://docs.python.org/3", None),
        "pandas": ("https://pandas.pydata.org/docs/", None),
    }
)
