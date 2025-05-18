import gettext
import os
import sys

TEXT_DOMAIN = "messages"
LOCALE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'locales'))

_ = lambda s: s
current_lang_code = "en"

def init_translation(lang_code: str = "en"):
    global _, current_lang_code
    current_lang_code = lang_code
    if not lang_code:
        current_lang_code = "en"

    try:
        translation_instance = gettext.translation(
            TEXT_DOMAIN,
            localedir=LOCALE_DIR,
            languages=[current_lang_code],
            fallback=True
        )
        translation_instance.install()
        _ = translation_instance.gettext
    except FileNotFoundError:
        null_trans = gettext.NullTranslations()
        null_trans.install()
        _ = null_trans.gettext
    except Exception:
        null_trans = gettext.NullTranslations()
        null_trans.install()
        _ = null_trans.gettext

def get_translator():
    return _

def get_current_language():
    return current_lang_code

def _parse_lang_from_argv():
    lang = os.getenv("AQ_LANG", "en")
    try:
        args_to_check = ["-l", "--lang", "--language"]
        for i, arg in enumerate(sys.argv[:-1]):
            if arg in args_to_check:
                potential_lang = sys.argv[i + 1]
                if not potential_lang.startswith("-"):
                    lang = potential_lang
                    break
    except Exception:
        pass
    return lang

INITIAL_LANG = _parse_lang_from_argv()
init_translation(INITIAL_LANG)
