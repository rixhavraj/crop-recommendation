from __future__ import annotations

import pandas as pd


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily weather into monthly ML features."""
    group_prefix = [col for col in ["location_id", "location_name", "state", "lat", "lon"] if col in df.columns]
    group_cols = group_prefix + ["year", "month"]

    # Handle different column names between Live API and Normalized CSV
    rain_col = next((c for c in ["precipitation", "precipitation_sum", "total_rain"] if c in df.columns), "precipitation")
    wind_col = next((c for c in ["wind_speed_10m_max", "windspeed_10m_max"] if c in df.columns), "wind_speed_10m_max")
    et0_col = next((c for c in ["et0", "et0_fao_evapotranspiration"] if c in df.columns), None)
    rh_col = next((c for c in ["avg_humidity", "relative_humidity_2m_max"] if c in df.columns), None)

    # Aggregator map
    agg_map = {
        "total_rain": (rain_col, "sum"),
        "avg_temp_max": ("temperature_2m_max", "mean"),
        "avg_temp_min": ("temperature_2m_min", "mean"),
        "max_wind": (wind_col, "max"),
    }
    if rh_col: agg_map["avg_humidity"] = (rh_col, "mean")
    if et0_col: agg_map["total_et0"] = (et0_col, "sum")

    # Ensure group_cols is a unique list to avoid duplicate key errors during merge/concat
    group_cols = list(dict.fromkeys(group_cols))

    # Pre-emptively drop duplicates and ensure clean numeric indices
    df = df.drop_duplicates().reset_index(drop=True)

    # Simplified aggregation
    monthly = (
        df.groupby(group_cols)
        .agg(**agg_map)
        .reset_index()
    )

    # Vectorized heat stress calculation
    df["_is_heat"] = (df["temperature_2m_max"] > 35).astype(int)
    heat_group = df.groupby(group_cols)["_is_heat"].sum().reset_index(name="heat_stress_days")

    # Safe merge and duplicate avoidance
    monthly = monthly.merge(heat_group, on=group_cols, how="left")
    monthly = monthly.drop_duplicates(subset=group_cols).reset_index(drop=True)

    # Fill missing values for humidity and et0 early
    if "avg_humidity" not in monthly.columns: monthly["avg_humidity"] = 60.0
    if "total_et0" not in monthly.columns: monthly["total_et0"] = 0.0
    monthly["avg_humidity"] = monthly["avg_humidity"].fillna(60.0)
    monthly["total_et0"] = monthly["total_et0"].fillna(0.0)

    monthly["temp_range"] = monthly["avg_temp_max"] - monthly["avg_temp_min"]
    monthly["water_balance"] = monthly["total_rain"] - monthly["total_et0"]
    monthly["is_monsoon"] = monthly["month"].between(6, 9).astype(int)

    sort_cols = group_prefix + ["year", "month"]
    monthly = monthly.sort_values(sort_cols)

    if group_prefix:
        monthly["rain_3m_rolling"] = (
            monthly.groupby(group_prefix)["total_rain"]
            .transform(lambda series: series.rolling(3, min_periods=1).mean())
        )
    else:
        monthly["rain_3m_rolling"] = monthly["total_rain"].rolling(3, min_periods=1).mean()

    # Guarantee uniqueness for chart-friendly output
    monthly = monthly.drop_duplicates(subset=["year", "month"]).reset_index(drop=True)
    
    return monthly.reset_index(drop=True)


if __name__ == "__main__":
    raw = pd.read_csv("data/weather_raw.csv")
    features = engineer_features(raw)
    features.to_csv("data/features.csv", index=False)
    print(features.head())
