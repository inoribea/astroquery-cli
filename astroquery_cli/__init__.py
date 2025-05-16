# astroquery_cli/__init__.py
from importlib import metadata
try:
    __version__ = metadata.version("astroquery-cli")
except metadata.PackageNotFoundError:
    __version__ = "None" 