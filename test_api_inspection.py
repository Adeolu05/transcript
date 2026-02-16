from youtube_transcript_api import YouTubeTranscriptApi
import sys

def test_list_transcripts():
    video_id = "jNQXAC9IVRw"
    try:
        print("Attempting list_transcripts...")
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            print("list_transcripts successful.")
            
            # iterating?
            for transcript in transcript_list:
                print(f"Transcript: {transcript.language} ({transcript.language_code})")
                
            # try fetching english
            en_transcript = transcript_list.find_transcript(['en'])
            print("Found English transcript.")
            data = en_transcript.fetch()
            print(f"Fetched {len(data)} lines.")
            print(f"First line: {data[0]['text']}")
        else:
            print("list_transcripts NOT found.")
            
            # Check for get_transcript
            if hasattr(YouTubeTranscriptApi, 'get_transcript'):
                print("get_transcript found.")
                data = YouTubeTranscriptApi.get_transcript(video_id)
                print(f"Fetched {len(data)} lines.")
            else:
                print("get_transcript NOT found either.")
                print(f"Dir: {dir(YouTubeTranscriptApi)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_list_transcripts()
