import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import app.services.transcript_service
print(f"Transcript Service File: {app.services.transcript_service.__file__}")
print(f"Dir: {dir(app.services.transcript_service)}")
from app.services.transcript_service import get_transcript

def test_extraction():
    video_id = "jNQXAC9IVRw" # Me at the zoo (very short)
    print(f"Testing extraction for video ID: {video_id}")
    try:
        transcript = get_transcript(video_id)
        print("Transcript extracted successfully.")
        print(f"First line: {transcript[0]['text']}")
        assert len(transcript) > 0
    except Exception as e:
        print(f"Extraction failed: {e}")
        # It's possible tests fail due to network or IP blocks on YouTube side
        # In that case, we might need to handle it gracefully or warn the user.
        raise e

if __name__ == "__main__":
    test_extraction()
