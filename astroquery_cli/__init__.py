# astroquery_cli/__init__.py
import logging
from importlib import metadata

logging.getLogger('astroquery').setLevel(logging.CRITICAL)

try:
    __version__ = metadata.version("astroquery-cli")
except metadata.PackageNotFoundError:
    __version__ = "None"
