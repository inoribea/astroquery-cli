# astroquery_cli/__init__.py
from importlib import metadata
import logging
import sys

# Suppress astroquery log messages globally
logging.getLogger('astroquery').setLevel(logging.CRITICAL)

# Monkey patch logging.Logger._set_defaults to prevent AttributeError from astroquery
# This needs to happen before astroquery is imported.
# We replace _set_defaults with a no-op if it exists.
if hasattr(logging.Logger, '_set_defaults'):
    original_set_defaults = logging.Logger._set_defaults
    def no_op_set_defaults(self):
        pass
    logging.Logger._set_defaults = no_op_set_defaults

try:
    __version__ = metadata.version("astroquery-cli")
except metadata.PackageNotFoundError:
    __version__ = "None"
