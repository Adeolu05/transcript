import requests
import re
import json

# Test with a known Vimeo video
video_id = "76979871"  # Example video ID
url = f"https://vimeo.com/{video_id}"

print(f"Fetching: {url}")
response = requests.get(url, timeout=10)
html = response.text

# Try different patterns
patterns = [
    r'var\s+config\s*=\s*(\{.*?\});',
    r'window\.vimeoPlayerConfig\s*=\s*(\{.*?\});',
    r'"config":\s*(\{.*?\})',
    r'data-config=\'(\{.*?\})\'',
    r'data-config="(\{.*?\})"',
]

print("\nTrying different config patterns...")
for i, pattern in enumerate(patterns, 1):
    print(f"\nPattern {i}: {pattern[:50]}...")
    match = re.search(pattern, html, re.DOTALL)
    if match:
        print(f"  ✅ MATCH FOUND!")
        try:
            config_str = match.group(1)
            print(f"  Config snippet: {config_str[:200]}...")
            config = json.loads(config_str)
            print(f"  Successfully parsed JSON")
            print(f"  Keys: {list(config.keys())[:10]}")
        except Exception as e:
            print(f"  ❌ Error parsing: {e}")
    else:
        print(f"  ❌ No match")

# Also save a snippet of the HTML for inspection
print("\n" + "="*50)
print("Saving HTML snippet...")
with open("vimeo_debug.html", "w", encoding="utf-8") as f:
    f.write(html[:5000])
print("First 5000 chars saved to vimeo_debug.html")
