import os
import requests
import json

payload = {
    "district": "Hisar",
    "lat": 29.15,
    "lon": 75.73,
    "month": 7,
    "year": 2023,
    "soil_type": "loam",
    "soil_ph": 7.0,
    "organic_matter_pct": 1.3,
    "irrigation_level": "medium"
}

try:
    api_base = os.getenv("API_BASE_URL", "http://localhost:8000/api")
    r = requests.post(f"{api_base}/recommend", json=payload)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
