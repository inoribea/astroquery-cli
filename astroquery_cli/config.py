import os
from pathlib import Path
import configparser

# Global config object and path
_config = None
CONFIG_FILE_PATH = None

def load_config():
    global _config, CONFIG_FILE_PATH
    _config = configparser.ConfigParser()
    aqc_dir = Path.home() / ".aqc"
    CONFIG_FILE_PATH = aqc_dir / "config.ini"

    if not aqc_dir.exists():
        aqc_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {aqc_dir}")

    is_debug = os.environ.get("AQC_DEBUG", "false").lower() == "true"
    is_verbose = os.environ.get("AQC_VERBOSE", "false").lower() == "true"

    if CONFIG_FILE_PATH.exists():
        _config.read(CONFIG_FILE_PATH)
        if is_debug or is_verbose:
            print(f"Loaded config from: {CONFIG_FILE_PATH}")
    else:
        if is_debug or is_verbose:
            print(f"Config file not found: {CONFIG_FILE_PATH}. Using default settings.")
        # Create a default config file for the user
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write("[Environment]\n")
            f.write("ADS_DEV_KEY = \n") # Add this line
            f.write("# AQC_DEBUG = true\n")
            f.write("# AQC_VERBOSE = true\n")
            f.write("# AQC_LANG = en\n")
        if is_debug or is_verbose:
            print(f"Created default config file: {CONFIG_FILE_PATH}. Please edit it to set your environment variables.")

    # Set environment variables from config
    if 'Environment' in _config:
        for key, value in _config['Environment'].items():
            os.environ[key.upper()] = value

    # Handle specific environment variables that might be set directly
    # For ADS_DEV_KEY, if it's not in config.ini but is in os.environ, keep it.
    # Otherwise, if it's in config.ini, it will override os.environ.
    # If neither, it remains unset.
    if "ADS_DEV_KEY" not in os.environ and 'Environment' in _config and 'ads_dev_key' in _config['Environment']:
        os.environ["ADS_DEV_KEY"] = _config['Environment']['ads_dev_key']

    if "AQC_DEBUG" not in os.environ and 'Environment' in _config and 'aqc_debug' in _config['Environment']:
        os.environ["AQC_DEBUG"] = _config['Environment']['aqc_debug']

    if "AQC_VERBOSE" not in os.environ and 'Environment' in _config and 'aqc_verbose' in _config['Environment']:
        os.environ["AQC_VERBOSE"] = _config['Environment']['aqc_verbose']

    if "AQC_LANG" not in os.environ and 'Environment' in _config and 'aqc_lang' in _config['Environment']:
        os.environ["AQC_LANG"] = _config['Environment']['aqc_lang']

def set_language(lang: str):
    global _config, CONFIG_FILE_PATH
    if _config is None:
        load_config() # Ensure config is loaded

    if 'Environment' not in _config:
        _config['Environment'] = {}
    _config['Environment']['aqc_lang'] = lang
    with open(CONFIG_FILE_PATH, 'w') as f:
        _config.write(f)
    os.environ["AQC_LANG"] = lang # Also update the environment variable immediately

def get_language():
    global _config
    if _config is None:
        load_config() # Ensure config is loaded
    return _config.get('Environment', 'aqc_lang', fallback=None)
