import requests
import re

video_id = "76979871"
# Try the player URL instead
player_url = f"https://player.vimeo.com/video/{video_id}"

print(f"Fetching player: {player_url}")
response = requests.get(player_url, timeout=10)
html = response.text

print(f"HTML length: {len(html)}")

# Look for common script patterns
if "text_tracks" in html:
    print("✅ Found 'text_tracks' in HTML!")
    
# Save snippet
with open("vimeo_player_debug.html", "w", encoding="utf-8") as f:
    # Find the part with text_tracks
    idx = html.find("text_tracks")
    if idx > 0:
        start = max(0, idx - 500)
        end = min(len(html), idx + 1000)
        f.write(html[start:end])
        print(f"Saved snippet around 'text_tracks' to vimeo_player_debug.html")
    else:
        f.write(html[:5000])
        print("Saved first 5000 chars to vimeo_player_debug.html")
