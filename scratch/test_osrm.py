
import urllib.request
import json

def test_osrm():
    url = "https://router.project-osrm.org/route/v1/driving/3.05,36.75;3.06,36.76?overview=full&geometries=geojson"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print("OSRM Success")
            print(f"Distance: {data['routes'][0]['distance']}")
            print(f"Points: {len(data['routes'][0]['geometry']['coordinates'])}")
    except Exception as e:
        print(f"OSRM Failed: {e}")

if __name__ == "__main__":
    test_osrm()
