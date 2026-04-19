import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class ChatRequest(BaseModel):
    district: str
    lat: float
    lon: float
    question: str = Field(..., min_length=2)
    month: int = Field(1, ge=1, le=12)
    year: int = 2026


def _is_hindi(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


def _format_crop_list(recommendations: list[dict]) -> str:
    if not recommendations:
        return "recommended crops are not available right now"
    return ", ".join(
        f"{item['crop']} ({item['confidence']:.1f}%)" for item in recommendations[:3]
    )


def _english_answer(question: str, soil: dict, weather: dict, recommendations: list[dict]) -> str:
    question_lc = question.lower()
    current = weather["current"]
    historical = weather["historical_summary"]

    if not recommendations:
        return (
            "I could not generate crop recommendations for this location right now, "
            "but the weather and soil data were loaded successfully. Try another district or month."
        )

    if any(token in question_lc for token in ["best crop", "which crop", "what crop", "recommend"]):
        top = recommendations[0]
        return (
            f"The best crop right now is {top['crop']} with confidence {top['confidence']:.1f}%. "
            f"Top options are {_format_crop_list(recommendations)}. {top['reason']}"
        )

    if any(token in question_lc for token in ["weather", "rain", "temperature", "humidity", "wind"]):
        return (
            f"Current weather is {current.get('temperature_2m', 'NA')} C with humidity "
            f"{current.get('relative_humidity_2m', 'NA')}%, wind {current.get('wind_speed_10m', 'NA')} km/h, "
            f"and precipitation {current.get('precipitation', 'NA')} mm. "
            f"The latest historical monthly summary shows {historical['total_rain']} mm rain and "
            f"{historical['avg_temp_max']} C average max temperature."
        )

    if any(token in question_lc for token in ["soil", "ph", "clay", "sand", "silt", "fertility"]):
        return (
            f"Soil at your location looks like {soil['soil_type']} soil with pH {soil['soil_ph']:.1f}, "
            f"organic matter {soil['organic_matter_pct']:.2f}%, sand {soil['soil_sand_pct']:.1f}%, "
            f"silt {soil['soil_silt_pct']:.1f}%, and clay {soil['soil_clay_pct']:.1f}%. "
            f"This profile supports crops like {_format_crop_list(recommendations)}."
        )

    if any(token in question_lc for token in ["fertilizer", "nitrogen", "nutrient"]):
        nitrogen = soil["soil_nitrogen_gkg"]
        nitrogen_hint = "low" if nitrogen < 0.5 else "moderate" if nitrogen < 1.0 else "good"
        return (
            f"Soil nitrogen is about {nitrogen:.2f} g/kg, which looks {nitrogen_hint}. "
            f"Focus on a soil-test-based fertilizer plan, split nitrogen applications, and organic matter improvement. "
            f"For this location, {_format_crop_list(recommendations)} are currently the strongest crop options."
        )

    if any(token in question_lc for token in ["water", "irrigation"]):
        return (
            f"The latest water balance is {historical['water_balance']} mm. "
            f"Choose irrigation carefully for high-water crops and prefer {_format_crop_list(recommendations)} "
            f"if you want lower risk under the current weather-soil pattern."
        )

    top = recommendations[0]
    return (
        f"Based on your weather and soil, the strongest crops are {_format_crop_list(recommendations)}. "
        f"Current temperature is {current.get('temperature_2m', 'NA')} C and your soil is {soil['soil_type']} "
        f"with pH {soil['soil_ph']:.1f}. If you want, ask about crop choice, weather, soil, fertilizer, or irrigation."
    )


def _hindi_answer(question: str, soil: dict, weather: dict, recommendations: list[dict]) -> str:
    question_lc = question.lower()
    current = weather["current"]
    historical = weather["historical_summary"]

    if not recommendations:
        return (
            "Is location ke liye abhi crop recommendations generate nahi ho pa rahi hain. "
            "Aap kisi aur district ya month try kar sakte hain."
        )

    if any(token in question_lc for token in ["crop", "recommend", "which", "best"]) or "फसल" in question:
        top = recommendations[0]
        return (
            f"इस समय सबसे अच्छी फसल {top['crop']} है और इसका confidence {top['confidence']:.1f}% है। "
            f"ऊपर के विकल्प हैं: {_format_crop_list(recommendations)}। {top['reason']}"
        )

    if any(token in question_lc for token in ["weather", "rain", "temperature"]) or "मौसम" in question:
        return (
            f"अभी तापमान {current.get('temperature_2m', 'NA')} C है, humidity "
            f"{current.get('relative_humidity_2m', 'NA')}% है, हवा {current.get('wind_speed_10m', 'NA')} km/h है, "
            f"और बारिश {current.get('precipitation', 'NA')} mm है। "
            f"पिछले मासिक सार में {historical['total_rain']} mm बारिश और "
            f"{historical['avg_temp_max']} C औसत अधिकतम तापमान था।"
        )

    if any(token in question_lc for token in ["soil", "ph", "fertility"]) or "मिट्टी" in question:
        return (
            f"आपकी मिट्टी {soil['soil_type']} प्रकार की दिख रही है, pH {soil['soil_ph']:.1f} है, "
            f"organic matter {soil['organic_matter_pct']:.2f}% है। "
            f"इस मिट्टी और मौसम में {_format_crop_list(recommendations)} अच्छे विकल्प हैं।"
        )

    return (
        f"आपके स्थान के मौसम और मिट्टी के हिसाब से {_format_crop_list(recommendations)} सबसे अच्छे विकल्प हैं। "
        f"अगर चाहें तो फसल, मौसम, खाद, सिंचाई या मिट्टी के बारे में अलग से पूछ सकते हैं।"
    )


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        from data.fetch_soil import get_soil_context
        from data.fetch_weather import get_current_weather, get_weather_data
        from ml.features import engineer_features
        from ml.predict import predict_crops

        history_df, _ = get_weather_data(req.lat, req.lon, location_name=req.district)
        soil_context, _ = get_soil_context(req.lat, req.lon)
        current_weather, _ = get_current_weather(req.lat, req.lon)
        features = engineer_features(history_df) if not history_df.empty else history_df

        weather_features = {}
        if not features.empty:
            row = features[(features["year"] == req.year) & (features["month"] == req.month)]
            if row.empty:
                row = features[features["month"] == req.month]
            if not row.empty:
                weather_features = row.iloc[-1].to_dict()

        recommendations = predict_crops(weather_features, soil_context=soil_context) if weather_features else []

        weather_context = {
            "current": current_weather.get("current", {}),
            "historical_summary": {
                "year": int(weather_features.get("year", req.year)),
                "month": int(weather_features.get("month", req.month)),
                "total_rain": round(float(weather_features.get("total_rain", 0.0)), 1),
                "avg_temp_max": round(float(weather_features.get("avg_temp_max", 0.0)), 1),
                "avg_temp_min": round(float(weather_features.get("avg_temp_min", 0.0)), 1),
                "avg_humidity": round(float(weather_features.get("avg_humidity", 0.0)), 1),
                "water_balance": round(float(weather_features.get("water_balance", 0.0)), 1),
            },
        }

        answer = (
            _hindi_answer(req.question, soil_context, weather_context, recommendations)
            if _is_hindi(req.question)
            else _english_answer(req.question, soil_context, weather_context, recommendations)
        )

        return {
            "answer": answer,
            "soil": soil_context,
            "weather": weather_context,
            "recommendations": recommendations[:3],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Unable to answer the query right now")
