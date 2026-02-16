from youtube_transcript_api import YouTubeTranscriptApi

try:
    print("Fetching transcript...")
    api = YouTubeTranscriptApi()
    # Use a known video ID with captions
    transcript = api.fetch('jNQXAC9IVRw') 
    
    print(f"Type of transcript: {type(transcript)}")
    if len(transcript) > 0:
        first_item = transcript[0]
        print(f"Type of first item: {type(first_item)}")
        print(f"Dir of first item: {dir(first_item)}")
        print(f"First item repr: {first_item}")
        
        try:
            print(f"Try subscripting: {first_item['text']}")
        except Exception as e:
            print(f"Subscripting failed: {e}")
            
except Exception as e:
    print(f"Error: {e}")
