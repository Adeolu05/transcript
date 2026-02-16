from youtube_transcript_api import YouTubeTranscriptApi

with open("debug_results.txt", "w") as f:
    try:
        f.write("Fetching transcript...\n")
        api = YouTubeTranscriptApi()
        transcript = api.fetch('jNQXAC9IVRw') 
        
        f.write(f"Type of transcript: {type(transcript)}\n")
        f.write(f"Length: {len(transcript)}\n\n")
        
        if len(transcript) > 0:
            first_item = transcript[0]
            f.write(f"Type of first item: {type(first_item)}\n")
            f.write(f"First item repr: {repr(first_item)}\n\n")
            
            # Check for attributes
            for attr in ['text', 'start', 'duration']:
                if hasattr(first_item, attr):
                    f.write(f"Has .{attr} attribute: {getattr(first_item, attr)}\n")
                    
    except Exception as e:
        f.write(f"Error: {e}\n")
        import traceback
        f.write(traceback.format_exc())
