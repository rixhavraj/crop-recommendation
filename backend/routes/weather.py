from fastapi import APIRouter, HTTPException, Query
import datetime

router = APIRouter()


@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    location_name: str = Query("Selected Location", description="Location label"),
):
    try:
        from data.fetch_soil import get_soil_context
        from data.fetch_weather import get_current_weather, get_weather_data
        from ml.features import engineer_features

        ten_years_ago = (datetime.date.today() - datetime.timedelta(days=365*10)).strftime("%Y-01-01")
        
        history_df, history_meta = get_weather_data(lat, lon, start=ten_years_ago, location_name=location_name)
        current_weather, current_meta = get_current_weather(lat, lon)
        soil_context, soil_meta = get_soil_context(lat, lon)

        if history_df.empty:
            return {
                "location": {"name": location_name, "lat": lat, "lon": lon},
                "weather_source": history_meta["source"],
                "current_source": current_meta["source"],
                "soil_source": soil_meta["source"],
                "current": current_weather.get("current", {}),
                "forecast": current_weather.get("forecast", []),
                "historical_trend": [],
                "soil": soil_context,
                "error": "No historical weather data available for this region",
            }
        
        features = engineer_features(history_df)
        if features.empty:
            return {
                "location": {"name": location_name, "lat": lat, "lon": lon},
                "weather_source": history_meta["source"],
                "current": {},
                "historical_trend": [],
                "error": "No historical weather data available for this region"
            }
        
        latest = features.sort_values(["year", "month"]).iloc[-1]
        
        # Generate trend for the chart
        # We'll take the last 10 years (120 months) and ensure no NaN values for JSON
        trend_df = features.sort_values(["year", "month"]).tail(120).fillna(0)
        historical_trend = []
        
        # Month labels for the chart
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        for _, r in trend_df.iterrows():
            m_idx = int(r["month"]) - 1
            historical_trend.append({
                "label": f"{month_names[m_idx]} {str(int(r['year']))[2:]}",
                "rainfall": round(float(r["total_rain"]), 1),
                "temp_max": round(float(r["avg_temp_max"]), 1),
                "temp_min": round(float(r["avg_temp_min"]), 1),
                "water_balance": round(float(r["water_balance"]), 1),
                "humidity": round(float(r["avg_humidity"]), 1),
            })

        return {
            "location": {
                "name": location_name,
                "lat": lat,
                "lon": lon,
            },
            "weather_source": history_meta["source"],
            "current_source": current_meta["source"],
            "soil_source": soil_meta["source"],
            "current": current_weather.get("current", {}),
            "forecast": current_weather.get("forecast", []),
            "historical_trend": historical_trend,
            "soil": soil_context,
        }
    except Exception as exc:
        print(f"WEATHER_ROUTE_ERROR: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to load weather data")
