"""
Transcript output languages offered in the web picker and Telegram /language.

YouTube auto-translates captions into any of these when the video lacks a
native track; Vimeo can only pick among the tracks the uploader provided.
Codes follow YouTube's caption codes (note zh-Hans / zh-Hant).
"""

from __future__ import annotations

from typing import Dict, List

DEFAULT_LANGUAGE = "en"

# (code, native name, English name). Order is the order shown to users.
SUPPORTED_LANGUAGES: List[tuple[str, str, str]] = [
    ("en", "English", "English"),
    ("es", "Español", "Spanish"),
    ("fr", "Français", "French"),
    ("de", "Deutsch", "German"),
    ("pt", "Português", "Portuguese"),
    ("it", "Italiano", "Italian"),
    ("nl", "Nederlands", "Dutch"),
    ("pl", "Polski", "Polish"),
    ("tr", "Türkçe", "Turkish"),
    ("ro", "Română", "Romanian"),
    ("sv", "Svenska", "Swedish"),
    ("cs", "Čeština", "Czech"),
    ("id", "Bahasa Indonesia", "Indonesian"),
    ("vi", "Tiếng Việt", "Vietnamese"),
    ("ru", "Русский", "Russian"),
    ("uk", "Українська", "Ukrainian"),
    ("el", "Ελληνικά", "Greek"),
    ("ja", "日本語", "Japanese"),
    ("ko", "한국어", "Korean"),
    ("zh-Hans", "简体中文", "Chinese (Simplified)"),
    ("zh-Hant", "繁體中文", "Chinese (Traditional)"),
    ("hi", "हिन्दी", "Hindi"),
    ("ar", "العربية", "Arabic"),
]

LANGUAGE_CODES = frozenset(code for code, _, _ in SUPPORTED_LANGUAGES)
_NATIVE_NAMES: Dict[str, str] = {code: native for code, native, _ in SUPPORTED_LANGUAGES}


_ZH_TRADITIONAL = frozenset({"zh-hant", "zh-tw", "zh-hk", "zh-mo"})


def lang_base(code: str) -> str:
    return (code or "").strip().split("-")[0].lower()


def is_traditional_chinese(code: str) -> bool:
    return (code or "").strip().lower() in _ZH_TRADITIONAL


def languages_match(code: str, target: str) -> bool:
    """
    Same language for our purposes: regional variants are interchangeable
    (en-GB ~ en), but Chinese scripts are not (zh-Hans != zh-Hant).
    """
    c, t = (code or "").strip().lower(), (target or "").strip().lower()
    if not c or not t:
        return False
    if c == t:
        return True
    if lang_base(t) == "zh":
        return lang_base(c) == "zh" and is_traditional_chinese(c) == is_traditional_chinese(t)
    return lang_base(c) == lang_base(t)


def language_name(code: str) -> str:
    """Native name for *code*, matching regional variants (en-GB -> English)."""
    if code in _NATIVE_NAMES:
        return _NATIVE_NAMES[code]
    match = next((c for c, _, _ in SUPPORTED_LANGUAGES if languages_match(code, c)), None)
    return _NATIVE_NAMES[match] if match else code


def public_language_list() -> List[Dict[str, str]]:
    return [
        {"code": code, "name": native, "english_name": english}
        for code, native, english in SUPPORTED_LANGUAGES
    ]
