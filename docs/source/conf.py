#!/usr/bin/env python3
#
# django-ca documentation build configuration file, created by
# sphinx-quickstart on Mon Jan  4 18:57:14 2016.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import os
import re
import sys

import sphinx_rtd_theme
from docutils.nodes import Text as DocutilsText
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx

try:
    from sphinxcontrib import spelling
except ImportError:
    spelling = None


sys.path.insert(0, os.path.dirname(__file__))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
# sys.path.insert(0, os.path.abspath('.'))

_BASE_DIR = os.path.dirname(os.path.abspath(__name__))
_ROOT_DIR = os.path.dirname(os.path.dirname(_BASE_DIR))
_SRC_DIR = os.path.join(_ROOT_DIR, "ca")
_FIXTURES = os.path.join(_SRC_DIR, "django_ca", "tests", "fixtures")
sys.path.insert(0, _SRC_DIR)
sys.path.insert(0, os.path.join(_ROOT_DIR, "devscripts"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ca.settings")

import django  # NOQA: E402
from django.conf import settings  # NOQA: E402

from dev.config import CONFIG  # NOQA: E402

settings.configure(
    SECRET_KEY="dummy",
    BASE_DIR=_SRC_DIR,
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django_ca",
    ],
    FIXTURES_DIR=_FIXTURES,
)
django.setup()


# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    # Enable Celery task docs: https://docs.celeryproject.org/en/latest/userguide/sphinx.html
    "celery.contrib.sphinx",
    "numpydoc",
    "sphinx_jinja",
    "django_ca_sphinx",
]

autodoc_typehints = "none"

if spelling is not None:
    from django_ca_sphinx.spelling import URIFilter, MagicWordsFilter, TypeHintsFilter  # isort:skip

    extensions.append("sphinxcontrib.spelling")
    spelling_exclude_patterns = ["**/generated/*.rst"]
    spelling_filters = [URIFilter, MagicWordsFilter, TypeHintsFilter]
    # spelling_show_suggestions = True

numpydoc_show_class_members = False
autodoc_inherit_docstrings = False
manpages_url = "https://manpages.debian.org/{page}.{section}"


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "django-ca"
copyright = "2016 - 2020, Mathias Ertl"
author = "Mathias Ertl"

import django_ca  # NOQA: E402

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
release = version = django_ca.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "alabaster"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
# html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
# html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
# html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
# html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'h', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'r', 'sv', 'tr'
# html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# Now only 'ja' uses this config value
# html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
# html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = "django-cadoc"

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
    # Latex figure (float) alignment
    #'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "django-ca.tex", "django-ca Documentation", "Mathias Ertl", "manual"),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
# latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "django-ca", "django-ca Documentation", [author], 1)]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "django-ca",
        "django-ca Documentation",
        author,
        "django-ca",
        "One line description of project.",
        "Miscellaneous",
    ),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
# texinfo_no_detailmenu = False

autodoc_mock_imports = [
    "OpenSSL",
    "acme",
    "freezegun",
    "josepy",
    "pyvirtualdisplay",
    "selenium",
]

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "cg": ("https://cryptography.io/en/%s/" % CONFIG["cryptography"][-1], None),
    "django": (
        "https://docs.djangoproject.com/en/%s/" % CONFIG["django-major"][-1],
        "https://docs.djangoproject.com/en/%s/_objects/" % CONFIG["django-major"][-1],
    ),
    "acme": ("https://acme-python.readthedocs.io/en/stable/", None),
}

rst_epilog = f"""
.. |minimum-python| replace:: {CONFIG['python-major'][0]}
"""

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Jinja template contexts
jinja_contexts = {
    "full-requirements-from-source": {
        "base": "Python",
        "how:": "installed via APT",
    },
    "full-requirements-in-docker": {
        "base": "Docker",
        "how:": "each in a separate Docker container",
    },
    "manage-as-py": {"manage": "python manage.py"},
    "manage-in-docker-compose": {
        "manage": "docker-compose exec backend manage",
        "shared": True,
    },
    "manage-from-source": {"manage": "django-ca"},
    "requirements-as-py": {},
    "requirements-in-docker": {},
    "requirements-in-docker-compose": {},
    "requirements-from-source": {},
    "guide-source-where-to-go": {
        "shared": False,
        "guide": "from-source",
        "manage": "django-ca",
        "user": "root",
    },
    "quickstart-with-docker": {
        "backend_host": "backend",
        "ca_default_hostname": "ca.example.com",
        "frontend_host": "frontend",
        "network": "django-ca",
        "nginx_host": "nginx",
        "postgres_host": "postgres",
        "postgres_password": "password",
        "redis_host": "redis",
    },
    "quickstart-with-docker-compose": {},
    "guide-as-app-where-to-go": {"shared": False, "guide": "as-app", "manage": "manage.py"},
    "guide-docker-compose-where-to-go": {
        "shared": True,
        "guide": "with-docker-compose",
        "manage": "docker-compose exec backend manage",
        "path": "~/ca/",
    },
}
jinja_globals = {"version": version, "last_version": str(CONFIG["LAST_RELEASE"])}

# Make typehints to third-party libraries work in Shpinx:
#   https://github.com/agronholm/sphinx-autodoc-typehints/issues/38#issuecomment-448517805
#   See also: https://github.com/sphinx-doc/sphinx/issues/4826
qualname_overrides = {
    "ExtensionTypeTypeVar": "cg:cryptography.x509.ExtensionType",
    "IterableItem": ":py:data:`django_ca.typehints.IterableItem`",
    "ParsableItem": ":py:data:`django_ca.typehints.ParsableItem`",
    "ParsableValue": ":py:data:`django_ca.typehints.ParsableValue`",
    "SerializedItem": ":py:data:`django_ca.typehints.SerializedItem`",
    "SerializedValue": ":py:data:`django_ca.typehints.SerializedValue`",
    "BasicConstraintsBase": ":py:data:`django_ca.typehints.BasicConstraintsBase`",
    "Union": "python:typing.Union",
    "Optional": "python:typing.Optional",
    "cryptography.hazmat._oid.ObjectIdentifier": "cg:cryptography.x509.ObjectIdentifier",
    "cryptography.hazmat._oid.ExtendedKeyUsageOID": "cg:cryptography.x509.oid.ExtendedKeyUsageOID",
    "cryptography.hazmat.primitives.serialization.base.Encoding": "cg:cryptography.hazmat.primitives.serialization.Encoding",  # NOQA: E501 # black does not allow a newline here
    "cryptography.hazmat.primitives._serialization.Encoding": "cg:cryptography.hazmat.primitives.serialization.Encoding",  # NOQA: E501 # black does not allow a newline here
    "cryptography.x509.base.Certificate": "cg:cryptography.x509.Certificate",
    "cryptography.x509.base.CertificateBuilder": "cg:cryptography.x509.CertificateBuilder",
    "cryptography.x509.base.CertificateRevocationList": "cg:cryptography.x509.CertificateRevocationList",
    "cryptography.x509.base.CertificateSigningRequest": "cg:cryptography.x509.CertificateSigningRequest",
    "cryptography.x509.base.RevokedCertificate": "cg:cryptography.x509.RevokedCertificate",
    "cryptography.x509.extensions.AuthorityInformationAccess": "cg:cryptography.x509.AuthorityInformationAccess",  # NOQA: E501 # black does not allow a newline here
    "cryptography.x509.extensions.AuthorityKeyIdentifier": "cg:cryptography.x509.AuthorityKeyIdentifier",
    "cryptography.x509.extensions.BasicConstraints": "cg:cryptography.x509.BasicConstraints",
    "cryptography.x509.extensions.CRLDistributionPoints": "cg:cryptography.x509.CRLDistributionPoints",
    "cryptography.x509.extensions.CertificatePolicies": "cg:cryptography.x509.CertificatePolicies",
    "cryptography.x509.extensions.DistributionPoint": "cg:cryptography.x509.DistributionPoint",
    "cryptography.x509.extensions.ExtendedKeyUsage": "cg:cryptography.x509.ExtendedKeyUsage",
    "cryptography.x509.extensions.Extension": "cg:cryptography.x509.Extension",
    "cryptography.x509.extensions.ExtensionType": "cg:cryptography.x509.ExtensionType",
    "cryptography.x509.extensions.FreshestCRL": "cg:cryptography.x509.FreshestCRL",
    "cryptography.x509.extensions.InhibitAnyPolicy": "cg:cryptography.x509.InhibitAnyPolicy",
    "cryptography.x509.extensions.IssuerAlternativeName": "cg:cryptography.x509.IssuerAlternativeName",
    "cryptography.x509.extensions.KeyUsage": "cg:cryptography.x509.KeyUsage",
    "cryptography.x509.extensions.NameConstraints": "cg:cryptography.x509.NameConstraints",
    "cryptography.x509.extensions.OCSPNoCheck": "cg:cryptography.x509.OCSPNoCheck",
    "cryptography.x509.extensions.PolicyConstraints": "cg:cryptography.x509.PolicyConstraints",
    "cryptography.x509.extensions.PolicyInformation": "cg:cryptography.x509.PolicyInformation",
    "cryptography.x509.extensions.PrecertPoison": "cg:cryptography.x509.PrecertPoison",
    "cryptography.x509.extensions.PrecertificateSignedCertificateTimestamps": "cg:cryptography.x509.PrecertificateSignedCertificateTimestamps",  # NOQA: E501 # black does not allow a newline here
    "cryptography.x509.extensions.ReasonFlags": "cg:cryptography.x509.ReasonFlags",
    "cryptography.x509.extensions.SubjectAlternativeName": "cg:cryptography.x509.SubjectAlternativeName",
    "cryptography.x509.extensions.SubjectKeyIdentifier": "cg:cryptography.x509.SubjectKeyIdentifier",
    "cryptography.x509.extensions.TLSFeature": "cg:cryptography.x509.TLSFeature",
    "cryptography.x509.extensions.TLSFeatureType": "cg:cryptography.x509.TLSFeatureType",
    "cryptography.x509.extensions.UserNotice": "cg:cryptography.x509.UserNotice",
    "cryptography.x509.extensions.NoticeReference": "cg:cryptography.x509.NoticeReference",
    "cryptography.x509.general_name.GeneralName": "cg:cryptography.x509.GeneralName",
    "cryptography.x509.name.Name": "cg:cryptography.x509.Name",
    "cryptography.x509.name.RelativeDistinguishedName": "cg:cryptography.x509.RelativeDistinguishedName",
    "django_ca.extensions.extensions.AuthorityKeyIdentifier": "django_ca.extensions.AuthorityKeyIdentifier",
    "django_ca.extensions.extensions.SubjectKeyIdentifier": "django_ca.extensions.SubjectKeyIdentifier",
    "django_ca.extensions.extensions.IssuerAlternativeName": "django_ca.extensions.IssuerAlternativeName",
    "django_ca.extensions.extensions.NameConstraints": "django_ca.extensions.NameConstraints",
    "ExtensionTypeVar": "cg:cryptography.x509.ExtensionType",
    "Union": "python:typing.Union",
    "typing.S": "django_ca.extensions.base.S",
    "django.http.request.HttpRequest": "django:django.http.HttpRequest",
    "Optional[typing_extensions.Literal['ca', 'user', 'attribute']]": "str",
    "typing.ExtensionTypeTypeVar": "cg:cryptography.x509.ExtensionType",
    "typing.ParsableValue": ":py:data:`django_ca.typehints.ParsableValue`",
    "typing.SerializedValue": ":py:data:`django_ca.typehints.SerializedValue`",
    "typing_extensions.Literal": "str",
    "NoneType": "None",
}

text_overrides = {
    "ExtensionTypeTypeVar": "ExtensionType",
    "cryptography.x509.extensions.Extension": "cryptography.x509.Extension",
    "cryptography.x509.extensions.UserNotice": "cryptography.x509.UserNotice",
    "cryptography.hazmat._oid.ObjectIdentifier": "cryptography.x509.ObjectIdentifier",
}


nitpick_ignore = [
    ("py:class", "python:typing.Optional"),
]


def resolve_internal_aliases(app, doctree):
    """
    .. seealso::

        * https://www.sphinx-doc.org/en/master/extdev/appapi.html#events
        * https://stackoverflow.com/a/62301461

    """
    pending_xrefs = doctree.traverse(condition=pending_xref)
    for node in pending_xrefs:
        alias = node.get("reftarget", None)

        if alias is not None and alias in qualname_overrides:
            reftype_match = re.match(r":py:([^:]*):`(.*)`", qualname_overrides[alias])
            if reftype_match is not None:
                reftype, target = reftype_match.groups()
                node["reftype"] = reftype
                node["reftarget"] = target
            else:
                node["reftarget"] = qualname_overrides[alias]

            # In TypeVar cases, this is plain text and not a type, so we wrap it ina literal for common look
            # if not isinstance(node.children[0], literal):
            #    node.children = [literal('', '', *node.children, classes=['xref', 'py', 'py-class'])]

        if alias is not None and alias in text_overrides:
            # this will rewrite the rendered text:
            # find the text node child
            text_node = next(iter(node.traverse(lambda n: n.tagname == "#text")))
            text_node.parent.replace(text_node, DocutilsText(text_overrides[alias], ""))


def setup(app: Sphinx) -> None:
    app.connect("doctree-read", resolve_internal_aliases)
