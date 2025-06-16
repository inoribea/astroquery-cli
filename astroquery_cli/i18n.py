import gettext
import os
import sys
import builtins

TEXT_DOMAIN = "messages"
LOCALE_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'locales'))

class Translator:
    def __init__(self):
        self._translator = gettext.NullTranslations()
        self.current_lang_code = "en"

    def load_translation_file(self, lang_code: str):
        mo_file_path = os.path.join(LOCALE_BASE_DIR, lang_code, "LC_MESSAGES", f"{TEXT_DOMAIN}.mo")
        
        # Fallback to default if language-specific MO file not found
        if not os.path.exists(mo_file_path):
            mo_file_path = os.path.join(LOCALE_BASE_DIR, f"{TEXT_DOMAIN}.mo") # Default MO file path

        try:
            with open(mo_file_path, 'rb') as mo_file:
                translation = gettext.GNUTranslations(mo_file)
            return translation
        except FileNotFoundError:
            return gettext.NullTranslations()
        except Exception:
            return gettext.NullTranslations()

    def init_translation(self, lang_code: str = "en"):
        """Initialize the translator for the given language code."""
        self._translator = self.load_translation_file(lang_code)
        self.current_lang_code = lang_code

    def gettext(self, message):
        """Translate a message using the current translator."""
        return self._translator.gettext(message)

    def get_current_language(self):
        return self.current_lang_code

translator_instance = Translator()

_ = translator_instance.gettext
builtins._ = _

def init_translation(lang_code: str = "en"):
    translator_instance.init_translation(lang_code)
    global _
    _ = translator_instance.gettext
    builtins._ = _

def get_translator(lang: str = "en"):
    """Return a gettext function for the specified language (one-off use)."""
    temp_translator = translator_instance.load_translation_file(lang)
    return temp_translator.gettext

def _parse_lang_from_argv():
    lang = os.environ.get("AQC_LANG", None)
    
    # Check for --default option
    default_args_to_check = ["-d", "--default"]
    for i, arg in enumerate(sys.argv[:-1]):
        if arg in default_args_to_check:
            potential_lang = sys.argv[i + 1]
            if not potential_lang.startswith("-"):
                lang = potential_lang
                break

    # Check for --lang or --language option
    if not lang: # Only check if not already found by --default
        args_to_check = ["-l", "--lang", "--language"]
        for i, arg in enumerate(sys.argv[:-1]):
            if arg in args_to_check:
                potential_lang = sys.argv[i + 1]
                if not potential_lang.startswith("-"):
                    lang = potential_lang
                    break
    
    if lang is None:
        lang = os.environ.get("AQC_LANG", "en") # Fallback to environment variable or default 'en'
    
    return lang

INITIAL_LANG = _parse_lang_from_argv()
init_translation(INITIAL_LANG)
