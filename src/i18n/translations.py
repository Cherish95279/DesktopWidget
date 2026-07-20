# -*- coding: utf-8 -*-
"""
Translation infrastructure for DesktopWidget.

Manages application translations via a Python-based dictionary system.
Also supports Qt .qm/.ts files when lrelease is available.
"""

import os
import sys
from typing import Optional, Dict, Tuple

from PyQt6.QtCore import QLocale, QSettings, QTranslator, QLibraryInfo
from PyQt6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = ["zh_CN", "zh_TW", "en", "es", "ja", "de", "fr", "ko"]

LANGUAGE_LABELS = {
    "zh_CN": "\u4e2d\u6587\u7b80\u4f53",
    "zh_TW": "\u4e2d\u6587\u7e41\u9ad4",
    "en": "English",
    "es": "Espa\u00f1ol",
    "ja": "\u65e5\u672c\u8a9e",
    "de": "Deutsch",
    "fr": "Fran\u00e7ais",
    "ko": "한국어",
}


# ---------------------------------------------------------------------------
# Built-in translation dictionaries
# ---------------------------------------------------------------------------

_builtin_translations: Dict[str, Dict[str, Dict[str, str]]] = {}
_default_lang: str = "zh_CN"


def _load_builtin_translations():
    """Load translation strings from .ts files into memory."""
    global _builtin_translations, _default_lang

    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        return

    base = os.path.dirname(os.path.abspath(__file__))
    # /src/i18n/ -> /src/ -> project root
    project_root = os.path.normpath(os.path.join(base, "..", ".."))
    search_dirs = [
        os.path.normpath(os.path.join(base, "..", "translations")),       # src/translations/
        os.path.normpath(os.path.join(base, "translations")),              # src/i18n/translations/
        os.path.join(project_root, "translations"),                        # <project>/translations/
    ]

    lang_codes = ["zh_CN", "zh_TW", "en", "es", "ja", "de", "fr", "ko"]

    for lang_code in lang_codes:
        _builtin_translations[lang_code] = {}
        ts_file = None
        for search_dir in search_dirs:
            candidate = os.path.join(search_dir, "translations_" + lang_code + ".ts")
            if os.path.isfile(candidate):
                ts_file = candidate
                break

        if not ts_file:
            continue

        try:
            tree = ET.parse(ts_file)
            root = tree.getroot()
            entry_count = 0

            for context_elem in root.findall("context"):
                ctx_name_elem = context_elem.find("name")
                if ctx_name_elem is None:
                    continue
                ctx_name = ctx_name_elem.text
                if ctx_name not in _builtin_translations[lang_code]:
                    _builtin_translations[lang_code][ctx_name] = {}

                for msg_elem in context_elem.findall("message"):
                    source_elem = msg_elem.find("source")
                    trans_elem = msg_elem.find("translation")
                    if source_elem is None:
                        continue
                    source = source_elem.text
                    if source is None:
                        continue

                    if trans_elem is not None and trans_elem.text and trans_elem.text.strip():
                        translation = trans_elem.text
                    else:
                        translation = source

                    _builtin_translations[lang_code][ctx_name][source] = translation
                    entry_count += 1

        except Exception as e:
            print(f" [i18n] Failed to load {lang_code}: {e}")

    if "zh_CN" in _builtin_translations:
        _default_lang = "zh_CN"


_load_builtin_translations()


def _detect_system_language() -> str:
    """Detect the user's preferred language code."""
    try:
        locale = QLocale.system()
        name = locale.name()
        if name in SUPPORTED_LANGUAGES:
            return name
        lang = name.split('_')[0]
        if lang == "zh":
            return "zh_CN"
        for supported in SUPPORTED_LANGUAGES:
            if supported.startswith(lang):
                return supported
    except Exception:
        pass
    return "zh_CN"


class DictTranslator(QTranslator):
    """QTranslator subclass that uses _builtin_translations dict."""

    def __init__(self, lang_code: str, parent=None):
        super().__init__(parent)
        self._lang_code = lang_code

    def translate(self, context: str, source_text: str,
                  disambiguation: str = None, n: int = -1) -> str:
        lang = self._lang_code
        if lang in _builtin_translations:
            ctx_dict = _builtin_translations[lang].get(context, {})
            if source_text in ctx_dict:
                result = ctx_dict[source_text]
                if result:
                    return result
        if lang != _default_lang and _default_lang in _builtin_translations:
            ctx_dict = _builtin_translations[_default_lang].get(context, {})
            if source_text in ctx_dict:
                result = ctx_dict[source_text]
                if result:
                    return result
        # Return empty so Qt falls back to source text as default
        # No translation found; Qt will try next translator or use source text


class TranslatorManager:
    """Singleton that manages application translations.

    Uses a built-in Python dictionary for translations (loaded from .ts file).
    Also integrates with Qt's QTranslator for .qm/.ts files when available.
    """


    _instance: Optional["TranslatorManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._qt_translator: Optional[object] = None
        self._qt_base_translator: Optional[QTranslator] = None
        self._current_lang: str = "zh_CN"
        self._app: Optional[QApplication] = None
        self._loading: bool = False
        self._dict_translator = None

    def init_translator(self, app: QApplication) -> None:
        """Call once at application startup."""
        self._app = app

        settings = QSettings("MyDesktopApp", "WeatherSettings")
        stored_lang = settings.value("language", "")
        if stored_lang and stored_lang in SUPPORTED_LANGUAGES:
            lang_code = stored_lang
        else:
            lang_code = _detect_system_language()

        if lang_code not in SUPPORTED_LANGUAGES:
            lang_code = "zh_CN"


        # 加载语言，但不发射信号（界面还未完全创建�?
        self._load_language(lang_code, emit_signal=False)

        lang_keys = list(_builtin_translations.keys())
        tw_count = sum(len(ctx) for ctx in _builtin_translations.get("zh_TW", {}).values())
        en_count = sum(len(ctx) for ctx in _builtin_translations.get("en", {}).values())

    def switch_language(self, lang_code: str) -> None:
        """Switch the application language (not currently used)."""
        if lang_code not in SUPPORTED_LANGUAGES:
            return
        # 切换时发射信号（但当前版本未使用此方法）
        self._load_language(lang_code, emit_signal=True)

    def current_language(self) -> str:
        return self._current_lang

    def language_label(self, lang_code: str) -> str:
        return LANGUAGE_LABELS.get(lang_code, lang_code)

    def translate(self, context: str, source_text: str, disambiguation: str = None, n: int = -1) -> str:
        """Translate a string, falling back to source text if no translation found."""
        if self._qt_translator is not None and self._app is not None:
            try:
                result = self._qt_translator.translate(context, source_text, disambiguation, n)
                if result:
                    return result
            except Exception:
                pass

        lang = self._current_lang
        if lang in _builtin_translations and context in _builtin_translations[lang]:
            if source_text in _builtin_translations[lang][context]:
                return _builtin_translations[lang][context][source_text]

        if lang != _default_lang and _default_lang in _builtin_translations:
            if context in _builtin_translations[_default_lang]:
                if source_text in _builtin_translations[_default_lang][context]:
                    return _builtin_translations[_default_lang][context][source_text]

        return source_text

    def _load_language(self, lang_code: str, emit_signal: bool = False) -> None:
        """Load a language, optionally emit signal."""
        if self._loading:
            return
        self._loading = True
        try:
            if lang_code not in SUPPORTED_LANGUAGES:
                lang_code = "zh_CN"

            # Remove old Qt base translator (QColorDialog etc.)
            if self._qt_base_translator is not None and self._app is not None:
                self._app.removeTranslator(self._qt_base_translator)
                self._qt_base_translator = None
            # Remove old app translators
            if self._qt_translator is not None and self._app is not None:
                self._app.removeTranslator(self._qt_translator)
                self._qt_translator = None
            if self._dict_translator is not None and self._app is not None:
                self._app.removeTranslator(self._dict_translator)
                self._dict_translator = None

            qm_dir = _find_translation_dir()
            qm_file = os.path.join(qm_dir, "translations_" + lang_code + ".qm")
            ts_file = os.path.join(qm_dir, "translations_" + lang_code + ".ts")

            loaded_via_qt = False

            if os.path.isfile(ts_file) and self._app is not None:
                try:
                    self._qt_translator = QTranslator(self._app)
                    if self._qt_translator.load(ts_file):
                        self._app.installTranslator(self._qt_translator)
                        loaded_via_qt = True
                except Exception:
                    pass

            if not loaded_via_qt and os.path.isfile(qm_file) and self._app is not None:
                try:
                    self._qt_translator = QTranslator(self._app)
                    if self._qt_translator.load(qm_file):
                        self._app.installTranslator(self._qt_translator)
                        loaded_via_qt = True
                except Exception:
                    pass

            # Install DictTranslator for builtin dictionary-based translations
            if self._app is not None:
                try:
                    self._dict_translator = DictTranslator(lang_code, self._app)
                    self._app.installTranslator(self._dict_translator)
                except Exception:
                    pass

            # Load Qt base translation for standard dialogs (QColorDialog etc.)
            # English (en) has 0-byte qtbase_en.qm, skip it
            if self._app is not None and lang_code != "en":
                try:
                    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
                    self._qt_base_translator = QTranslator(self._app)
                    if self._qt_base_translator.load("qtbase_" + lang_code, qt_path):
                        self._app.installTranslator(self._qt_base_translator)
                    else:
                        self._qt_base_translator = None
                except Exception:
                    self._qt_base_translator = None

            self._current_lang = lang_code

            # 仅在明确要求时发射信号（当前版本中此方法仅被 init_translator 调用，emit_signal=False�?
            if emit_signal:
                pass  # language_changed signal removed (QObject inheritance was causing stack overflow)

            settings = QSettings("MyDesktopApp", "WeatherSettings")
            settings.setValue("language", lang_code)
            settings.sync()
        finally:
            self._loading = False

    @classmethod
    def get_instance(cls) -> "TranslatorManager":
        return cls()


def _find_translation_dir() -> str:
    """Find the directory containing .ts/.qm translation files."""
    # PyInstaller 打包后的路径
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    # 优先查找打包后的路径
    candidate = os.path.normpath(os.path.join(base, "translations"))
    if os.path.isdir(candidate):
        return candidate

    # 开发环境：从 src/i18n/ 向上找到 src/translations/
    dev_base = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.normpath(os.path.join(dev_base, "..", "translations"))
    if os.path.isdir(fallback):
        return fallback

    # 最后备选
    return os.path.join(base, "translations")


# Global instance
_translator_manager: Optional[TranslatorManager] = None


def get_translator_manager() -> TranslatorManager:
    global _translator_manager
    if _translator_manager is None:
        _translator_manager = TranslatorManager()
    return _translator_manager