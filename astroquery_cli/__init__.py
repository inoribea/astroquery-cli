# astroquery_cli/__init__.py
import logging

# Monkey patch AstropyLogger: add _set_defaults to avoid AttributeError
# This must be done before astroquery imports astropy.logger
try:
    # Attempt to import AstropyLogger directly.
    # If astropy is not yet fully loaded, this might fail,
    # but it's the earliest point we can try to patch.
    from astropy.logger import AstropyLogger
    if not hasattr(AstropyLogger, '_set_defaults'):
        def _dummy_set_defaults(self):
            pass
        AstropyLogger._set_defaults = _dummy_set_defaults
except Exception:
    # If AstropyLogger cannot be imported or patched at this stage,
    # it means astroquery might have already initialized its logger.
    pass

logging.getLogger('astroquery').setLevel(logging.CRITICAL)

from importlib import metadata

try:
    __version__ = metadata.version("astroquery-cli")
except metadata.PackageNotFoundError:
    __version__ = "None"
