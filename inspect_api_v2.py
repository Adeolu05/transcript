from youtube_transcript_api import YouTubeTranscriptApi
import inspect

print(f"Type of YouTubeTranscriptApi: {type(YouTubeTranscriptApi)}")
print(f"Dir: {dir(YouTubeTranscriptApi)}")

if hasattr(YouTubeTranscriptApi, 'get_transcript'):
    print("get_transcript found on class.")
    method = getattr(YouTubeTranscriptApi, 'get_transcript')
    print(f"Type of get_transcript: {type(method)}")
    try:
        print("Inspect signature: " + str(inspect.signature(method)))
    except:
        print("Could not inspect signature")
else:
    print("get_transcript NOT found on class.")

print("-" * 20)

try:
    instance = YouTubeTranscriptApi()
    print("Instantiation successful.")
    print(f"Dir instance: {dir(instance)}")
    if hasattr(instance, 'get_transcript'):
        print("get_transcript found on instance.")
except Exception as e:
    print(f"Instantiation failed: {e}")
