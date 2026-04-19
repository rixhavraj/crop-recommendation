from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class RecommendRequest(BaseModel):
    district: str
    lat: float
    lon: float
    month: int = Field(..., ge=1, le=12)
    year: int
    soil_type: str | None = None
    soil_ph: float | None = None
    organic_matter_pct: float | None = None
    irrigation_level: str | None = None


class CropResult(BaseModel):
    crop: str
    confidence: float
    water_req: str
    avg_yield_qtl_acre: float
    price: int
    avg_cost_inr_acre: int
    expected_profit_inr_acre: int
    season: str
    reason: str
    emoji: str = ""
    growth_instructions: list[str] = []
    regional_success_rate: str | None = None
    regional_avg_profit: int | None = None
    ai_analysis: str = ""


@router.post("/recommend", response_model=list[CropResult])
async def recommend(req: RecommendRequest):
    try:
        from data.fetch_soil import get_soil_context
        from data.fetch_weather import get_weather_data
        from ml.features import engineer_features
        from ml.predict import predict_crops

        weather_df, _ = get_weather_data(req.lat, req.lon, location_name=req.district)
        if weather_df.empty:
            raise HTTPException(status_code=404, detail="No weather data available for this location")

        feature_df = engineer_features(weather_df)
        if feature_df.empty:
            raise HTTPException(status_code=404, detail="No historical weather features available for this location")

        row = feature_df[(feature_df["year"] == req.year) & (feature_df["month"] == req.month)]
        if row.empty:
            row = feature_df[feature_df["month"] == req.month]
            if row.empty:
                raise HTTPException(status_code=404, detail="No weather data for that period")

        soil_context, _ = get_soil_context(req.lat, req.lon)
        
        # Override with user inputs if provided
        if req.soil_type: soil_context["soil_type"] = req.soil_type
        if req.soil_ph is not None: soil_context["soil_ph"] = req.soil_ph
        if req.organic_matter_pct is not None: soil_context["organic_matter_pct"] = req.organic_matter_pct
        if req.irrigation_level: soil_context["irrigation_level"] = req.irrigation_level

        weather_dict = row.iloc[-1].to_dict()
        state = row.iloc[-1].get("state")
        recommendations = predict_crops(weather_dict, soil_context=soil_context, state=state)
        if not recommendations:
            raise HTTPException(status_code=404, detail="No crop recommendations available for the selected month")
        return recommendations

    except HTTPException:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Unable to generate crop recommendations")
