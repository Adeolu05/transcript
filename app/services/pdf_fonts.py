"""
Pick a PDF font that can actually draw the transcript's characters.

Decided from the text itself, not the requested language: YouTube/Vimeo may
fall back to the original captions, so a "Spanish" request can return Russian.

- Western European text -> Helvetica (built in, not embedded; unchanged output)
- Chinese / Japanese -> ReportLab's built-in CID fonts (no files needed)
- Korean -> an embedded Korean TTF (Nanum Gothic in Docker); the built-in Korean
  CID fonts render blank in PDFium (Chrome's viewer)
- Other alphabetic scripts (Polish, Vietnamese, Cyrillic, Greek...) -> an embedded
  Unicode TTF (DejaVu Sans in Docker), verified glyph by glyph
- Scripts that need shaping or right-to-left layout (Arabic, Hebrew, Indic, Thai...)
  -> UnsupportedPdfScript: ReportLab would draw them as disconnected or reversed glyphs
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

from app.core.config import settings
from app.core.languages import is_traditional_chinese

UNSUPPORTED_PDF_MESSAGE = (
    "PDF isn't available for this language yet. Download DOCX or TXT instead."
)

_COMPLEX_SCRIPTS: Tuple[Tuple[int, int], ...] = (
    (0x0590, 0x08FF),  # Hebrew, Arabic, Syriac, Thaana, NKo, Samaritan...
    (0x0900, 0x0DFF),  # Devanagari through Sinhala (Indic)
    (0x0E00, 0x0FFF),  # Thai, Lao, Tibetan
    (0x1000, 0x109F),  # Myanmar
    (0x1780, 0x17FF),  # Khmer
    (0xFB1D, 0xFDFF),  # Hebrew / Arabic presentation forms
    (0xFE70, 0xFEFF),  # Arabic presentation forms B
)
_HANGUL = ((0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7AF))
_KANA = ((0x3040, 0x30FF), (0x31F0, 0x31FF))
_HAN = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF))

_TTF_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Debian/Ubuntu (Docker image)
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",  # Fedora/Alpine
    "/Library/Fonts/Arial Unicode.ttf",  # macOS dev machines
    "C:/Windows/Fonts/arial.ttf",  # Windows dev machines
)
_KOREAN_TTF_CANDIDATES = (
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Debian fonts-nanum (Docker image)
    "C:/Windows/Fonts/malgun.ttf",  # Windows dev machines
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # macOS dev machines
)
_UNICODE_FONT_NAME = "TranscriptUnicode"
_KOREAN_FONT_NAME = "TranscriptKorean"


class UnsupportedPdfScript(Exception):
    """Text uses a script this PDF pipeline cannot typeset correctly."""

    def __init__(self) -> None:
        super().__init__(UNSUPPORTED_PDF_MESSAGE)


@dataclass(frozen=True)
class PdfFont:
    name: str
    # CJK text has no spaces between words, so lines must break per character
    cjk_wrap: bool = False
    # Non-letter symbols the font can't draw (e.g. emoji, "♪"); removed rather than
    # letting one caption symbol block the whole PDF
    drop: frozenset = frozenset()


def _in_ranges(cp: int, ranges: Iterable[Tuple[int, int]]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def _has(chars: Set[str], ranges: Iterable[Tuple[int, int]]) -> bool:
    ranges = tuple(ranges)
    return any(_in_ranges(ord(ch), ranges) for ch in chars)


def _is_western(ch: str) -> bool:
    try:
        ch.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


_register_lock = threading.Lock()
_registered: Set[str] = set()
# font name -> code points it can draw (None = no font file found)
_ttf_glyphs: Dict[str, Optional[Set[int]]] = {}


def _register_cid(name: str) -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    with _register_lock:
        if name not in _registered:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
            _registered.add(name)
    return name


def _register_ttf(name: str, candidates: Iterable[str]) -> Optional[Set[int]]:
    """Register the first existing TTF under *name* once; returns its code points."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    with _register_lock:
        if name not in _ttf_glyphs:
            path = next((Path(c) for c in candidates if c and Path(c).is_file()), None)
            glyphs = None
            if path is not None:
                font = TTFont(name, str(path))
                pdfmetrics.registerFont(font)
                glyphs = set(font.face.charToGlyph)
            _ttf_glyphs[name] = glyphs
        return _ttf_glyphs[name]


def _embedded_font(name: str, candidates: Iterable[str], chars: Set[str], **kw) -> PdfFont:
    """Embedded TTF if it covers every letter; symbols it lacks are dropped."""
    glyphs = _register_ttf(name, candidates)
    if glyphs is None or not all(ord(ch) in glyphs for ch in chars if ch.isalpha()):
        raise UnsupportedPdfScript()
    return PdfFont(name, drop=frozenset(ch for ch in chars if ord(ch) not in glyphs), **kw)


def pdf_font_for(text: str, language: str = "") -> PdfFont:
    """Font able to render *text*; raises UnsupportedPdfScript otherwise."""
    chars = {ch for ch in set(text) if not ch.isspace()}

    if _has(chars, _COMPLEX_SCRIPTS):
        raise UnsupportedPdfScript()
    if _has(chars, _HANGUL):
        return _embedded_font(_KOREAN_FONT_NAME, _KOREAN_TTF_CANDIDATES, chars, cjk_wrap=True)
    if _has(chars, _KANA):
        return PdfFont(_register_cid("HeiseiKakuGo-W5"), cjk_wrap=True)
    if _has(chars, _HAN):
        name = "MSung-Light" if is_traditional_chinese(language) else "STSong-Light"
        return PdfFont(_register_cid(name), cjk_wrap=True)

    beyond_western = {ch for ch in chars if not _is_western(ch)}
    if not beyond_western:
        return PdfFont("Helvetica")

    # Only letters decide; symbols the chosen font lacks are dropped
    try:
        return _embedded_font(
            _UNICODE_FONT_NAME, (settings.pdf_font_path, *_TTF_CANDIDATES), chars
        )
    except UnsupportedPdfScript:
        if any(ch.isalpha() for ch in beyond_western):
            raise
        return PdfFont("Helvetica", drop=frozenset(beyond_western))


def pdf_supported(text: str) -> bool:
    try:
        pdf_font_for(text)
        return True
    except UnsupportedPdfScript:
        return False
