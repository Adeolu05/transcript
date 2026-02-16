import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.formatter_service import TranscriptFormatter
from app.services.file_service import FileGenerator

# Mock transcript data
mock_transcript = [
    {'text': "Hello world.", 'start': 0.0, 'duration': 1.0},
    {'text': "This is a test.", 'start': 2.0, 'duration': 1.5},
    {'text': "Transcript flow is working.", 'start': 5.0, 'duration': 2.0}
]

def test_formatter():
    print("Testing Formatter...")
    clean = TranscriptFormatter.format(mock_transcript, 'clean')
    print(f"Clean: {clean}")
    assert "Hello world. This is a test. Transcript flow is working." == clean
    
    timestamp = TranscriptFormatter.format(mock_transcript, 'timestamp')
    print(f"Timestamp:\n{timestamp}")
    assert "[00:00] Hello world." in timestamp

def test_file_generation():
    print("\nTesting File Generation...")
    # Test TXT
    txt_io = FileGenerator.generate_file("Hello world", 'txt')
    content = txt_io.getvalue().decode('utf-8')
    print(f"TXT Content: {content}")
    assert content == "Hello world"
    
    # Test DOCX (just check if it runs without error and returns bytes)
    docx_io = FileGenerator.generate_file("Hello world", 'docx')
    print(f"DOCX Size: {len(docx_io.getvalue())} bytes")
    
    # Test PDF
    pdf_io = FileGenerator.generate_file("Hello world", 'pdf')
    print(f"PDF Size: {len(pdf_io.getvalue())} bytes")

if __name__ == "__main__":
    try:
        test_formatter()
        test_file_generation()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
