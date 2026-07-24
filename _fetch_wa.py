import urllib.request, json
url = "https://www.weatherapi.com/docs/weather_conditions.json"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    for item in data:
        print(f"{item.get('code', '?')}: {item.get('day', '?')}")
        if item.get('night'):
            print(f"  night: {item['night']}")
    print(f"\nTotal: {len(data)} conditions")
except Exception as e:
    print(f"Error: {e}")
