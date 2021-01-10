# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../../dlpt'))
#sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..', '..')))
#sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
#sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', '..', '..', 'dlpt')))

import sphinx_rtd_theme

# -- Project information -----------------------------------------------------

project = 'dlpt'
copyright = '2021, Domen Jurkovic @ Damogran Labs'
author = 'Domen Jurkovic @ Damogran Labs'

# The full version, including alpha/beta/rc tags
release = '1.0.1'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx_rtd_theme',
    'sphinx.ext.napoleon'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

autodoc_mock_imports = ['psutil', 'jsonpickle']

master_doc = 'index'


def run_apidoc(_):
    """
    Run apidoc plug-in manually, as readthedocs doesn't support it
    https://github.com/rtfd/readthedocs.org/issues/1139
    """
    here = os.path.abspath(os.path.dirname(__file__))
    out = here
    src = os.path.join(here, "..", "..", project)

    ignore_paths = []

    argv = [
        "-f",
        "-T",
        "-e",
        "-M",
        "-o", out,
        src
    ] + ignore_paths

    # Sphinx 1.7+
    from sphinx.ext import apidoc
    apidoc.main(argv)


def skip(app, what, name, obj, would_skip, options):
    """
    Show classes __init__() docstring.
    https://stackoverflow.com/a/5599712/9200430
    """
    if name == "__init__":
        return False
    return would_skip


def setup(app):
    app.connect('builder-inited', run_apidoc)
    app.connect("autodoc-skip-member", skip)
