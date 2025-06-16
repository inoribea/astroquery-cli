# astroquery_cli/__init__.py
import sys
import logging
from importlib import metadata

# Create a dummy astroquery.logger module to prevent the real one from being loaded
# and causing the AttributeError. This must happen BEFORE any astroquery module is imported.
class DummyLoggerModule:
    def _init_log(self, *args, **kwargs):
        # Return a dummy logger object that won't cause AttributeError
        class DummyLogger:
            def setLevel(self, level):
                pass
            def debug(self, msg, *args, **kwargs):
                pass
            def info(self, msg, *args, **kwargs):
                pass
            def warning(self, msg, *args, **kwargs):
                pass
            def error(self, msg, *args, **kwargs):
                pass
            def critical(self, msg, *args, **kwargs):
                pass
        return DummyLogger()

    # Also provide a dummy AstropyLogger if it's expected
    class AstropyLogger(logging.Logger):
        def _set_defaults(self):
            pass # No-op

# Place our dummy module in sys.modules before astroquery is imported
# This ensures that when astroquery tries to import astroquery.logger, it gets our dummy.
sys.modules['astroquery.logger'] = DummyLoggerModule()

# Optionally, suppress astroquery log messages globally if they still manage to get through
logging.getLogger('astroquery').setLevel(logging.CRITICAL)

try:
    __version__ = metadata.version("astroquery-cli")
except metadata.PackageNotFoundError:
    __version__ = "None"
