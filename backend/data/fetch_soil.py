from __future__ import annotations

import hashlib
import json
from pathlib import Path

import requests


DATA_DIR = Path(__file__).resolve().parent
SOIL_CACHE_DIR = DATA_DIR / "soil_cache"
SOIL_CACHE_DIR.mkdir(exist_ok=True)

SOIL_PROPERTIES = ["phh2o", "soc", "clay", "sand", "silt", "nitrogen", "cec"]
SOIL_DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]
SOIL_VALUES = ["mean"]


def _cache_path(lat: float, lon: float) -> Path:
    key = hashlib.md5(f"{lat:.4f}:{lon:.4f}".encode("ascii")).hexdigest()[:12]
    return SOIL_CACHE_DIR / f"soil_{key}.json"


def _classify_soil(sand_pct: float, clay_pct: float, silt_pct: float) -> str:
    if clay_pct >= 40:
        return "clay"
    if sand_pct >= 70:
        return "sandy"
    if silt_pct >= 50:
        return "silty"
    if clay_pct >= 28 and sand_pct <= 45:
        return "black"
    if silt_pct >= 35 and clay_pct <= 27:
        return "alluvial"
    return "loam"


def _mean_depth_value(layer: dict) -> float | None:
    values = []
    factor = float(layer.get("unit_measure", {}).get("d_factor", 1) or 1)

    for depth in layer.get("depths", []):
        raw = depth.get("values", {}).get("mean")
        if raw is None:
            continue
        values.append(float(raw) / factor)

    if not values:
        return None

    return round(sum(values) / len(values), 3)


def _normalise_soil_payload(payload: dict) -> dict:
    layers = payload.get("properties", {}).get("layers", [])
    layer_map = {layer["name"]: _mean_depth_value(layer) for layer in layers}

    ph = layer_map.get("phh2o")
    soc_gkg = layer_map.get("soc")
    organic_matter_pct = round((soc_gkg or 0.0) * 0.1724, 3) if soc_gkg is not None else None
    sand_pct = layer_map.get("sand")
    clay_pct = layer_map.get("clay")
    silt_pct = layer_map.get("silt")

    soil_type = _classify_soil(
        sand_pct=sand_pct or 40.0,
        clay_pct=clay_pct or 20.0,
        silt_pct=silt_pct or 40.0,
    )

    return {
        "soil_type": soil_type,
        "soil_ph": ph if ph is not None else 7.0,
        "organic_matter_pct": organic_matter_pct if organic_matter_pct is not None else 1.2,
        "soil_soc_gkg": soc_gkg if soc_gkg is not None else 7.0,
        "soil_nitrogen_gkg": layer_map.get("nitrogen") if layer_map.get("nitrogen") is not None else 0.7,
        "soil_cec_cmolkg": layer_map.get("cec") if layer_map.get("cec") is not None else 12.0,
        "soil_sand_pct": sand_pct if sand_pct is not None else 42.0,
        "soil_silt_pct": silt_pct if silt_pct is not None else 33.0,
        "soil_clay_pct": clay_pct if clay_pct is not None else 25.0,
        "source": "soilgrids",
    }


def fetch_soil(lat: float, lon: float, timeout: int = 30) -> dict:
    url = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    params = {
        "lon": lon,
        "lat": lat,
    }
    for prop in SOIL_PROPERTIES:
        params.setdefault("property", [])
        params["property"].append(prop)
    for depth in SOIL_DEPTHS:
        params.setdefault("depth", [])
        params["depth"].append(depth)
    for value in SOIL_VALUES:
        params.setdefault("value", [])
        params["value"].append(value)

    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    context = _normalise_soil_payload(payload)

    cache_payload = {
        "lat": lat,
        "lon": lon,
        "raw": payload,
        "context": context,
    }
    _cache_path(lat, lon).write_text(json.dumps(cache_payload, indent=2), encoding="utf-8")
    return context


def load_cached_soil(lat: float, lon: float) -> dict:
    path = _cache_path(lat, lon)
    if not path.exists():
        raise FileNotFoundError(f"No cached soil profile for {lat}, {lon}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["context"]


def get_soil_context(lat: float, lon: float, prefer_live: bool = True) -> tuple[dict, dict]:
    try:
        if prefer_live:
            try:
                context = fetch_soil(lat=lat, lon=lon)
                return context, {"source": "soilgrids", "used_cache": False}
            except Exception as exc:
                print(f"Live soil lookup failed: {exc}, checking cache...")
                cached = load_cached_soil(lat=lat, lon=lon)
                return cached, {"source": "soil-cache", "used_cache": True}

        cached = load_cached_soil(lat=lat, lon=lon)
        return cached, {"source": "soil-cache", "used_cache": True}
    except Exception:
        # ABSOLUTE FALLBACK: Realistic India Loam profile
        # This keeps the app working for new regions even if 3rd party APIs are down
        print(f"No soil data for {lat}, {lon}, using India-Regional fallback")
        return {
            "soil_type": "loam",
            "soil_ph": 7.0,
            "organic_matter_pct": 1.2,
            "soil_soc_gkg": 7.0,
            "soil_nitrogen_gkg": 0.7,
            "soil_cec_cmolkg": 12.0,
            "soil_sand_pct": 42.0,
            "soil_silt_pct": 33.0,
            "soil_clay_pct": 25.0,
            "source": "india-regional-fallback",
        }, {"source": "fallback", "used_cache": False}
