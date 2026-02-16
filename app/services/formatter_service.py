from typing import List, Dict

class TranscriptFormatter:
    @staticmethod
    def format_clean(transcript: List[Dict]) -> str:
        """Joins all text parts with spaces."""
        return " ".join([entry['text'] for entry in transcript])

    @staticmethod
    def format_paragraph(transcript: List[Dict]) -> str:
        """Joins text but tries to create paragraphs (naive approach)."""
        # A simple approach: join with spaces, but maybe every X seconds or lines add a newline?
        # For now, let's just do simple joining, maybe double newline every 5 lines?
        lines = [entry['text'] for entry in transcript]
        text = ""
        for i, line in enumerate(lines):
            text += line + " "
            if (i + 1) % 5 == 0:
                text += "\n\n"
        return text.strip()

    @staticmethod
    def format_with_timestamps(transcript: List[Dict]) -> str:
        """Formats with [MM:SS] Text."""
        formatted_text = ""
        for entry in transcript:
            start = int(entry['start'])
            minutes = start // 60
            seconds = start % 60
            timestamp = f"[{minutes:02}:{seconds:02}]"
            formatted_text += f"{timestamp} {entry['text']}\n"
        return formatted_text

    @staticmethod
    def format(transcript: List[Dict], format_type: str = 'clean') -> str:
        if format_type == 'timestamp':
            return TranscriptFormatter.format_with_timestamps(transcript)
        elif format_type == 'paragraph':
            return TranscriptFormatter.format_paragraph(transcript)
        else:
            return TranscriptFormatter.format_clean(transcript)
