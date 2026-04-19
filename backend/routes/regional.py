from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
import pandas as pd

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# Load regional history and other data
with open(DATA_DIR / "regional_history.json", encoding="utf-8") as f:
    REGIONAL_HISTORY = json.load(f)

with open(DATA_DIR / "india_locations.json", encoding="utf-8") as f:
    LOCATIONS = json.load(f)["locations"]

class HistSuccess(BaseModel):
    crop: str
    avg_profit: int
    success_rate: str
    notable_year: str

class RegionalReport(BaseModel):
    region: str
    states: list[str]
    historical_success: list[HistSuccess]
    weather_summary: str
    top_recommended_crops: list[dict]

@router.get("/regional/{region_name}", response_model=RegionalReport)
async def get_regional_info(region_name: str, month: int = 7):
    if region_name not in REGIONAL_HISTORY:
        raise HTTPException(status_code=404, detail="Region not found")
    
    region_data = REGIONAL_HISTORY[region_name]
    
    # Try to get top recommendations for this region based on a representative city
    # We'll pick the first location that matches any state in the region
    rep_loc = None
    for loc in LOCATIONS:
        if loc["state"] in region_data["states"]:
            rep_loc = loc
            break
    
    if not rep_loc:
        rep_loc = LOCATIONS[0] # Fallback
        
    try:
        from data.fetch_weather import get_weather_data
        from ml.features import engineer_features
        from ml.predict import predict_crops
        
        # We'll look at July 2024 as a "recent history" context or use current average
        weather_df, _ = get_weather_data(rep_loc["lat"], rep_loc["lon"], location_name=rep_loc["name"])
        feature_df = engineer_features(weather_df)
        
        # Filter for the requested month across all years to see "typical" weather
        month_rows = feature_df[feature_df["month"] == month]
        if not month_rows.empty:
            avg_weather = month_rows.mean().fillna(0).to_dict()
            avg_weather["year"] = 2024 # Dummy for the predictor
            avg_weather["month"] = month
            
            recommendations = predict_crops(avg_weather, top_n=3)
            weather_summary = f"Historically, {month_rows['total_rain'].mean():.1f}mm rain and {month_rows['avg_temp_max'].mean():.1f}°C max temp."
        else:
            recommendations = []
            weather_summary = "Weather data unavailable for this season."
            
    except Exception as e:
        print(f"Error generating regional recommendations: {e}")
        recommendations = []
        weather_summary = "Historical weather insights currently unavailable."

    return {
        "region": region_name,
        "states": region_data["states"],
        "historical_success": region_data["historical_success"],
        "weather_summary": weather_summary,
        "top_recommended_crops": recommendations
    }

@router.get("/regions")
async def list_regions():
    return list(REGIONAL_HISTORY.keys())
