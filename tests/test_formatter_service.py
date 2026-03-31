"""Tests for transcript polishing and paragraph logic."""

import unittest

from app.services.formatter_service import TranscriptFormatter


class TestPolishPlaintext(unittest.TestCase):
    def test_gtgt_becomes_paragraph_break(self):
        raw = "hello >> world >> again"
        out = TranscriptFormatter._polish_plaintext(raw)
        self.assertEqual(out, "hello\n\nworld\n\nagain")

    def test_collapses_spaces_and_newlines(self):
        raw = "a  b\n\n\n\nc"
        out = TranscriptFormatter._polish_plaintext(raw)
        self.assertEqual(out, "a b\n\nc")


class TestReflowOrphans(unittest.TestCase):
    def test_merges_mid_clause_gtgt_split(self):
        raw = "He said how\n\nsocial media introduced me."
        out = TranscriptFormatter._reflow_orphan_paragraphs(raw)
        self.assertIn("how social", out)
        self.assertNotIn("how\n\nsocial", out)

    def test_merges_comma_then_lowercase(self):
        raw = "see the long form,\n\nright? But next."
        out = TranscriptFormatter._reflow_orphan_paragraphs(raw)
        self.assertIn("form, right?", out)

    def test_skips_single_char_block(self):
        raw = "Some sentence.\n\nM\n\nyou trade everything"
        out = TranscriptFormatter._reflow_orphan_paragraphs(raw)
        self.assertIn("\n\nM\n\n", out)

    def test_no_merge_after_full_stop_uppercase_next(self):
        raw = "First paragraph.\n\nSecond starts here."
        out = TranscriptFormatter._reflow_orphan_paragraphs(raw)
        self.assertIn("\n\n", out)
        self.assertIn("First paragraph.", out)


class TestFormatClean(unittest.TestCase):
    def test_youtube_style_segments(self):
        segs = [
            {"text": "Part one.", "start": 0.0, "duration": 1.0},
            {"text": ">> Part two.", "start": 1.0, "duration": 1.0},
        ]
        out = TranscriptFormatter.format_clean(segs)
        self.assertIn("\n\n", out)
        self.assertNotIn(">>", out)


class TestFormatParagraph(unittest.TestCase):
    def test_pause_splits_chunks(self):
        segs = [
            {"text": "A", "start": 0.0, "duration": 0.5},
            {"text": "B", "start": 5.0, "duration": 0.5},
        ]
        out = TranscriptFormatter.format_paragraph(segs, gap_seconds=1.0)
        self.assertIn("\n\n", out)


class TestFormatTimestamps(unittest.TestCase):
    def test_gtgt_collapsed_in_line(self):
        segs = [{"text": "foo >> bar", "start": 0.0, "duration": 1.0}]
        out = TranscriptFormatter.format_with_timestamps(segs)
        self.assertIn("[00:00]", out)
        self.assertNotIn(">>", out)
        self.assertIn("foo bar", out)


if __name__ == "__main__":
    unittest.main()
