import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests


DATA_DIR = Path(__file__).resolve().parent
WEATHER_CACHE_DIR = DATA_DIR / "weather_cache"
WEATHER_CACHE_DIR.mkdir(exist_ok=True)

# Archives are usually delayed by 2-5 days
DEFAULT_END_DATE = (date.today() - timedelta(days=5)).isoformat()
DEFAULT_CACHE_LAT = 29.15
DEFAULT_CACHE_LON = 75.73
DEFAULT_CURRENT_WEATHER = {"current": {}, "forecast": []}


def _cache_path(lat: float, lon: float, suffix: str = "history") -> Path:
    key = hashlib.md5(f"{lat:.4f}:{lon:.4f}:{suffix}".encode("ascii")).hexdigest()[:12]
    return WEATHER_CACHE_DIR / f"weather_{suffix}_{key}.json"


def _normalize_weather_frame(
    df: pd.DataFrame,
    lat: float,
    lon: float,
    location_name: str | None = None,
    state: str | None = None,
) -> pd.DataFrame:
    frame = df.copy()

    # Synchronize 'time' and 'date' columns to prevent duplicates
    if "time" in frame.columns:
        if "date" not in frame.columns:
            frame["date"] = frame["time"]
        frame = frame.drop(columns=["time"])

    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["lat"] = lat
    frame["lon"] = lon

    if location_name:
        fname = str(location_name)
        frame["location_name"] = fname
        frame["location_id"] = f"{fname.lower().replace(' ', '_')}_{lat:.2f}_{lon:.2f}"
    else:
        frame["location_name"] = "Selected Location"
        frame["location_id"] = f"loc_{lat:.2f}_{lon:.2f}"

    if state:
        frame["state"] = state

    # Ensure other consistent naming
    rename_map = {
        "windspeed_10m_max": "wind_speed_10m_max",
        "precipitation_sum": "precipitation",
        "et0_fao_evapotranspiration": "et0"
    }
    frame = frame.rename(columns=rename_map)

    # Final sweep: Ensure absolute uniqueness of column names
    frame = frame.loc[:, ~frame.columns.duplicated()].copy()

    return frame


def load_cached_weather(
    lat: float,
    lon: float,
    start: str = "2016-01-01",
    end: str | None = None,
) -> pd.DataFrame:
    path = _cache_path(lat, lon, "history")
    
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(payload["daily"])
        frame = _normalize_weather_frame(
            frame,
            lat=lat,
            lon=lon,
            location_name=payload.get("location_name"),
            state=payload.get("state"),
        )
    else:
        # Fallback to the main weather_raw.csv if it exists
        csv_path = DATA_DIR / "weather_raw.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"No cached data found (checked JSON and {csv_path.name})")
        
        all_data = pd.read_csv(csv_path)
        
        # Calculate distance to all points to find the closest match
        # Using a simple Euclidean square for speed (fine for local lookups)
        all_data["_dist"] = (all_data["lat"] - lat)**2 + (all_data["lon"] - lon)**2
        closest_dist = all_data["_dist"].min()
        
        # Threshold: Allow fallback for any location in India if no exact match
        # Using a much larger threshold (25.0 sq deg is ~500km) to ensure data is always available
        if closest_dist < 25.0:
            match_row = all_data.loc[all_data["_dist"] == closest_dist].iloc[0]
            target_id = match_row["location_id"]
            frame = all_data[all_data["location_id"] == target_id].copy()
            print(f"Using fuzzy fallback: {match_row['location_name']} (dist^2: {closest_dist:.2f}) for requested {lat}, {lon}")
        else:
            frame = pd.DataFrame()

        if frame.empty:
            available_locs = all_data["location_name"].unique()
            raise FileNotFoundError(
                f"No close weather data found in CSV for {lat}, {lon}. Available regions: {', '.join(available_locs[:5])}..."
            )

    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.drop_duplicates(subset=["date", "location_id"]).copy()
    
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end or str(date.today()))
    frame = frame[(frame["date"] >= start_ts) & (frame["date"] <= end_ts)].copy()

    if frame.empty:
        # If specific range missing, just return what we have for that location
        return frame.reset_index(drop=True)

    return frame.reset_index(drop=True)


def fetch_weather(
    lat: float,
    lon: float,
    start: str = "2016-01-01",
    end: str | None = None,
    timeout: int = 30,
    location_name: str | None = None,
    state: str | None = None,
    persist_cache: bool = True,
) -> pd.DataFrame:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end or DEFAULT_END_DATE,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "relative_humidity_2m_max",
            "windspeed_10m_max",
            "et0_fao_evapotranspiration",
        ],
        "timezone": "Asia/Kolkata",
    }

    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    frame = pd.DataFrame(payload["daily"])
    frame = _normalize_weather_frame(frame, lat=lat, lon=lon, location_name=location_name, state=state)

    if persist_cache:
        cache_payload = {
            "lat": lat,
            "lon": lon,
            "location_name": location_name,
            "state": state,
            "daily": payload["daily"],
        }
        _cache_path(lat, lon, "history").write_text(json.dumps(cache_payload), encoding="utf-8")

    return frame


def fetch_current_weather(lat: float, lon: float, timeout: int = 30) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "Asia/Kolkata",
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
        ],
        "forecast_days": 3,
    }

    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    current = payload.get("current", {})
    daily = payload.get("daily", {})
    forecast = []
    for idx, day in enumerate(daily.get("time", [])):
        forecast.append(
            {
                "date": day,
                "temp_max": daily.get("temperature_2m_max", [None])[idx],
                "temp_min": daily.get("temperature_2m_min", [None])[idx],
                "rainfall": daily.get("precipitation_sum", [None])[idx],
                "wind_speed_max": daily.get("wind_speed_10m_max", [None])[idx],
            }
        )

    normalized = {"current": current, "forecast": forecast}
    _cache_path(lat, lon, "current").write_text(json.dumps(normalized), encoding="utf-8")
    return normalized


def load_cached_current_weather(lat: float, lon: float) -> dict:
    path = _cache_path(lat, lon, "current")
    if not path.exists():
        return DEFAULT_CURRENT_WEATHER.copy()
    return json.loads(path.read_text(encoding="utf-8"))


def get_weather_data(
    lat: float,
    lon: float,
    start: str = "2016-01-01",
    end: str | None = None,
    prefer_live: bool = True,
    location_name: str | None = None,
    state: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    if prefer_live:
        try:
            frame = fetch_weather(
                lat=lat,
                lon=lon,
                start=start,
                end=end,
                location_name=location_name,
                state=state,
            )
            return frame, {"source": "open-meteo", "used_cache": False}
        except Exception as exc:
            cached = load_cached_weather(lat=lat, lon=lon, start=start, end=end)
            return cached, {
                "source": "local-cache",
                "used_cache": True,
                "warning": f"Live weather fetch failed: {exc}",
            }

    cached = load_cached_weather(lat=lat, lon=lon, start=start, end=end)
    return cached, {"source": "local-cache", "used_cache": True}


def get_current_weather(lat: float, lon: float, prefer_live: bool = True) -> tuple[dict, dict]:
    if prefer_live:
        try:
            current = fetch_current_weather(lat=lat, lon=lon)
            return current, {"source": "open-meteo", "used_cache": False}
        except Exception as exc:
            cached = load_cached_current_weather(lat=lat, lon=lon)
            return cached, {
                "source": "local-cache",
                "used_cache": True,
                "warning": f"Live current weather fetch failed: {exc}",
            }

    cached = load_cached_current_weather(lat=lat, lon=lon)
    return cached, {"source": "local-cache", "used_cache": True}


def load_india_locations() -> list[dict]:
    with open(DATA_DIR / "india_locations.json", encoding="utf-8") as f:
        return json.load(f)["locations"]


def build_india_weather_dataset(start: str = "2016-01-01") -> pd.DataFrame:
    frames = []
    for location in load_india_locations():
        frame, _ = get_weather_data(
            lat=location["lat"],
            lon=location["lon"],
            start=start,
            location_name=location["name"],
            state=location["state"],
        )
        frame["location_id"] = location["id"]
        frame["location_name"] = location["name"]
        frame["state"] = location["state"]
        frames.append(frame)

    return pd.concat(frames, ignore_index=True)


if __name__ == "__main__":
    df, meta = get_weather_data(DEFAULT_CACHE_LAT, DEFAULT_CACHE_LON)
    print(f"Loaded {len(df)} weather rows from {meta['source']}")
