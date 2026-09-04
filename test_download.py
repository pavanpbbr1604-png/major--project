import urllib.request

urls = [
    "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/right01.jpg",
    "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/data/basketball2.png"
]

for url in urls:
    try:
        print(f"Testing {url}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            print(f"  SUCCESS! Code: {response.status}")
    except Exception as e:
        print(f"  FAILED: {e}")
