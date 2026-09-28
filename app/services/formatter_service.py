import re
from typing import List, Dict, Tuple

# Timed formats built from caption segments rather than the formatted prose.
SUBTITLE_FORMATS = ("srt", "vtt")
# Floor for zero/negative-length cues so every subtitle is visible.
_MIN_CUE_SECONDS = 0.5

# YouTube auto-captions and many ASR tracks use >> as a hard turn / beat marker.
_ARTIFACT_GTGT = re.compile(r"\s*>>\s*")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r" {2,}")
# Sentence/clause end — allows … and optional closing quote.
_ENDS_SENTENCE_LIKE = re.compile(r'[.!?…]["\']?\s*$')


class TranscriptFormatter:
    """Format caption segments into readable plain text, PDF, and DOCX."""

    # Roughly 45–55 lines of prose; keeps paragraphs skimmable without tiny fragments.
    _MAX_PARAGRAPH_CHARS = 2600

    @staticmethod
    def _polish_plaintext(text: str) -> str:
        """
        Turn >> markers into paragraph breaks and normalize whitespace.
        Research-backed pattern: >> in YouTube transcripts correlates with speaker
        or editorial cuts; breaking here matches how humans read interviews.
        """
        t = _ARTIFACT_GTGT.sub("\n\n", text)
        t = _MULTI_NEWLINE.sub("\n\n", t)
        blocks = []
        for block in t.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            block = _MULTI_SPACE.sub(" ", block)
            blocks.append(block)
        return "\n\n".join(blocks)

    @staticmethod
    def _ends_sentence_like(block: str) -> bool:
        """True if the block ends with clear sentence-ending punctuation."""
        return bool(_ENDS_SENTENCE_LIKE.search(block.rstrip()))

    @staticmethod
    def _starts_lowercase_clause(block: str) -> bool:
        s = block.lstrip()
        return bool(s) and s[0].isalpha() and s[0].islower()

    @staticmethod
    def _reflow_orphan_paragraphs(text: str) -> str:
        """
        After >> becomes paragraph breaks, merge false splits: previous block
        does not finish a sentence but the next clearly continues (starts with
        lowercase). Fixes 'He said how' + 'social media...' and '2014' + 'where...'.
        Skips single-character blocks (e.g. 'M' listener cues) to avoid 'M you...'.
        """
        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        i = 0
        while i < len(blocks) - 1:
            a, b = blocks[i], blocks[i + 1]
            if len(a.strip()) == 1:
                i += 1
                continue
            if (not TranscriptFormatter._ends_sentence_like(a)
                    and TranscriptFormatter._starts_lowercase_clause(b)):
                blocks[i] = f"{a} {b}"
                del blocks[i + 1]
                continue
            i += 1
        return "\n\n".join(blocks)

    @staticmethod
    def _finalize_body(polished: str) -> str:
        """Reflow orphans, then split only very long paragraphs."""
        reflowed = TranscriptFormatter._reflow_orphan_paragraphs(polished)
        return TranscriptFormatter._break_long_blocks(reflowed)

    @staticmethod
    def _break_long_blocks(text: str, max_chars: int | None = None) -> str:
        """Split only very long paragraphs at sentence boundaries."""
        limit = max_chars or TranscriptFormatter._MAX_PARAGRAPH_CHARS
        out: List[str] = []
        for para in text.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            if len(para) <= limit:
                out.append(para)
                continue
            sentences = re.split(r"(?<=[.!?])\s+", para)
            buf: List[str] = []
            buf_len = 0
            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                add_len = len(s) if not buf else len(s) + 1
                if buf and buf_len + add_len > limit:
                    out.append(" ".join(buf))
                    buf = [s]
                    buf_len = len(s)
                else:
                    buf.append(s)
                    buf_len += add_len
            if buf:
                out.append(" ".join(buf))
        return "\n\n".join(out)

    @staticmethod
    def format_clean(transcript: List[Dict]) -> str:
        """Join segments, remove >> artifacts into paragraphs, split long runs."""
        parts = [entry["text"].strip() for entry in transcript if entry.get("text", "").strip()]
        joined = " ".join(parts)
        polished = TranscriptFormatter._polish_plaintext(joined)
        return TranscriptFormatter._finalize_body(polished)

    @staticmethod
    def format_paragraph(transcript: List[Dict], gap_seconds: float = 1.25) -> str:
        """
        Paragraphs on caption timing gaps (natural pause) plus >> polish.
        ~1–1.5s gap is a common threshold in subtitle tooling for clause boundaries.
        """
        if not transcript:
            return ""
        chunks: List[str] = []
        current: List[str] = [transcript[0]["text"].strip()]
        for i in range(1, len(transcript)):
            prev, cur = transcript[i - 1], transcript[i]
            prev_end = float(prev["start"]) + float(prev.get("duration") or 0)
            gap = float(cur["start"]) - prev_end
            if gap > gap_seconds:
                chunks.append(" ".join(current))
                current = [cur["text"].strip()]
            else:
                current.append(cur["text"].strip())
        chunks.append(" ".join(current))
        joined = "\n\n".join(chunks)
        polished = TranscriptFormatter._polish_plaintext(joined)
        return TranscriptFormatter._finalize_body(polished)

    @staticmethod
    def format_with_timestamps(transcript: List[Dict]) -> str:
        """One line per cue; >> collapsed to a single space so lines stay readable."""
        formatted_text = ""
        for entry in transcript:
            start = int(entry["start"])
            minutes = start // 60
            seconds = start % 60
            timestamp = f"[{minutes:02}:{seconds:02}]"
            line = _ARTIFACT_GTGT.sub(" ", entry.get("text", ""))
            line = _MULTI_SPACE.sub(" ", line).strip()
            formatted_text += f"{timestamp} {line}\n"
        return formatted_text

    @staticmethod
    def _subtitle_cues(transcript: List[Dict]) -> List[Tuple[float, float, str]]:
        """
        (start, end, text) per non-empty cue. Auto-captions overlap heavily, so each
        cue ends no later than the next one starts — otherwise players stack lines.
        """
        entries = []
        for entry in transcript:
            text = _ARTIFACT_GTGT.sub(" ", entry.get("text") or "")
            # A blank line inside a cue would end it early in SRT/VTT
            text = "\n".join(
                _MULTI_SPACE.sub(" ", line).strip() for line in text.splitlines() if line.strip()
            )
            if text:
                start = max(0.0, float(entry.get("start") or 0))
                entries.append((start, start + float(entry.get("duration") or 0), text))

        cues = []
        for i, (start, end, text) in enumerate(entries):
            if i + 1 < len(entries) and entries[i + 1][0] > start:
                end = min(end, entries[i + 1][0])
            if end <= start:
                end = start + _MIN_CUE_SECONDS
            cues.append((start, end, text))
        return cues

    @staticmethod
    def _subtitle_timestamp(seconds: float, ms_sep: str) -> str:
        total_ms = int(round(seconds * 1000))
        h, rem = divmod(total_ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, ms = divmod(rem, 1000)
        return f"{h:02}:{m:02}:{s:02}{ms_sep}{ms:03}"

    @staticmethod
    def format_srt(transcript: List[Dict]) -> str:
        ts = TranscriptFormatter._subtitle_timestamp
        blocks = [
            f"{i}\n{ts(start, ',')} --> {ts(end, ',')}\n{text}\n"
            for i, (start, end, text) in enumerate(
                TranscriptFormatter._subtitle_cues(transcript), start=1
            )
        ]
        return "\n".join(blocks)

    @staticmethod
    def format_vtt(transcript: List[Dict]) -> str:
        ts = TranscriptFormatter._subtitle_timestamp
        blocks = [
            f"{ts(start, '.')} --> {ts(end, '.')}\n{text}\n"
            for start, end, text in TranscriptFormatter._subtitle_cues(transcript)
        ]
        return "WEBVTT\n\n" + "\n".join(blocks)

    @staticmethod
    def format_subtitles(transcript: List[Dict], file_format: str) -> str:
        if file_format == "srt":
            return TranscriptFormatter.format_srt(transcript)
        if file_format == "vtt":
            return TranscriptFormatter.format_vtt(transcript)
        raise ValueError(f"Not a subtitle format: {file_format}")

    @staticmethod
    def format(transcript: List[Dict], format_type: str = "clean") -> str:
        if format_type == "timestamp":
            return TranscriptFormatter.format_with_timestamps(transcript)
        if format_type == "paragraph":
            return TranscriptFormatter.format_paragraph(transcript)
        return TranscriptFormatter.format_clean(transcript)
