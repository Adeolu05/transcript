import requests
import re
import json

# Test with headers
video_id = "76979871"
player_url = f"https://player.vimeo.com/video/{video_id}"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': f'https://vimeo.com/{video_id}',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

print(f"Testing: {player_url}")
response = requests.get(player_url, headers=headers, timeout=10)
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    config_pattern = r'"text_tracks"\s*:\s*(\[.*?\])'
    match = re.search(config_pattern, response.text, re.DOTALL)
    if match:
        text_tracks = json.loads(match.group(1))
        print(f"✅ Found {len(text_tracks)} text tracks")
        for track in text_tracks:
            print(f"  - {track.get('lang')}: {track.get('label')}")
    else:
        print("❌ No text tracks found")
else:
    print(f"❌ Failed: {response.status_code}")
