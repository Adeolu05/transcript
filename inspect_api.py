from youtube_transcript_api import YouTubeTranscriptApi

print("Attributes of YouTubeTranscriptApi:")
print(dir(YouTubeTranscriptApi))

try:
    print("\nAttempting to call static get_transcript:")
    YouTubeTranscriptApi.get_transcript("123")
except AttributeError as e:
    print(f"\nCaught expected error: {e}")
except Exception as e:
    print(f"\nCaught other error: {e}")
