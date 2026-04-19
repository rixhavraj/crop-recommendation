from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

import sys
from pathlib import Path

# Add backend to sys.path for direct script execution
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from data.fetch_soil import get_soil_context


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

FEATURE_COLS = [
    "total_rain",
    "avg_temp_max",
    "avg_temp_min",
    "avg_humidity",
    "heat_stress_days",
    "water_balance",
    "rain_3m_rolling",
    "is_monsoon",
    "avg_yield_qtl_acre",
    "avg_price_inr_qtl",
    "avg_cost_inr_acre",
    "expected_profit_inr_acre",
    "yield_stability_score",
    "irrigation_need_score",
    "soil_ph",
    "organic_matter_pct",
    "soil_soc_gkg",
    "soil_nitrogen_gkg",
    "soil_cec_cmolkg",
    "soil_sand_pct",
    "soil_silt_pct",
    "soil_clay_pct",
    "soil_match_score",
    "ph_match_score",
    "organic_matter_match",
    "profit_margin",
    "revenue_per_acre",
    "crop_encoded",
]


def _load_catalog() -> dict:
    with open(DATA_DIR / "crop_db.json", encoding="utf-8") as f:
        return json.load(f)


def _soil_match_score(crop: dict, soil_type: str) -> float:
    return 1.0 if soil_type in crop["preferred_soils"] else 0.4


def _ph_match_score(crop: dict, soil_ph: float) -> float:
    if crop["soil_ph_min"] <= soil_ph <= crop["soil_ph_max"]:
        return 1.0

    gap = min(abs(soil_ph - crop["soil_ph_min"]), abs(soil_ph - crop["soil_ph_max"]))
    return max(0.0, 1.0 - (gap / 2.5))


def _organic_match_score(crop: dict, organic_matter_pct: float) -> float:
    if organic_matter_pct >= crop["soil_organic_matter_min"]:
        return 1.0

    deficit = crop["soil_organic_matter_min"] - organic_matter_pct
    return max(0.0, 1.0 - (deficit / 1.5))


def _climate_scores(crop: dict, row: pd.Series) -> tuple[float, float, float, float]:
    monthly_rain_req = crop["rainfall_min_mm"] / max(len(crop["months"]), 1)
    rain_ratio = row["total_rain"] / max(monthly_rain_req, 1)
    rain_score = min(rain_ratio, 1.0)

    if crop["temp_min"] <= row["avg_temp_max"] <= crop["temp_max"]:
        temp_score = 1.0
    else:
        span = max(crop["temp_max"] - crop["temp_min"], 1)
        if row["avg_temp_max"] < crop["temp_min"]:
            diff = crop["temp_min"] - row["avg_temp_max"]
        else:
            diff = row["avg_temp_max"] - crop["temp_max"]
        temp_score = max(0.0, 1.0 - (diff / span))

    heat_penalty = max(0.0, 1.0 - (row["heat_stress_days"] / 31.0))
    water_score = 1.0 if row["water_balance"] >= 0 else max(0.0, 1.0 + (row["water_balance"] / 250.0))

    return rain_score, temp_score, heat_penalty, water_score


def build_training_data() -> pd.DataFrame:
    features = pd.read_csv(DATA_DIR / "features.csv")
    catalog = _load_catalog()
    crops = catalog["crops"]

    soil_cache: dict[tuple[float, float], dict] = {}
    rows: list[dict] = []

    # SOIL AUGMENTATION: Help the model understand soil performance across ALL zones
    soil_scenarios = [
        {"soil_type": "loam", "soil_ph": 7.0, "organic_matter_pct": 1.2, "soil_soc_gkg": 7.0, "soil_nitrogen_gkg": 0.7, "soil_cec_cmolkg": 12.0, "soil_sand_pct": 42.0, "soil_silt_pct": 33.0, "soil_clay_pct": 25.0},
        {"soil_type": "clay", "soil_ph": 6.5, "organic_matter_pct": 1.5, "soil_soc_gkg": 8.5, "soil_nitrogen_gkg": 0.9, "soil_cec_cmolkg": 18.0, "soil_sand_pct": 20.0, "soil_silt_pct": 30.0, "soil_clay_pct": 50.0},
        {"soil_type": "sandy", "soil_ph": 7.2, "organic_matter_pct": 0.6, "soil_soc_gkg": 3.5, "soil_nitrogen_gkg": 0.3, "soil_cec_cmolkg": 5.0, "soil_sand_pct": 80.0, "soil_silt_pct": 10.0, "soil_clay_pct": 10.0},
        {"soil_type": "black", "soil_ph": 8.0, "organic_matter_pct": 1.3, "soil_soc_gkg": 7.5, "soil_nitrogen_gkg": 0.8, "soil_cec_cmolkg": 22.0, "soil_sand_pct": 30.0, "soil_silt_pct": 25.0, "soil_clay_pct": 45.0},
        {"soil_type": "alluvial", "soil_ph": 6.8, "organic_matter_pct": 1.4, "soil_soc_gkg": 8.1, "soil_nitrogen_gkg": 1.0, "soil_cec_cmolkg": 14.0, "soil_sand_pct": 40.0, "soil_silt_pct": 40.0, "soil_clay_pct": 20.0},
    ]

    for _, feature_row in features.iterrows():
        lat = float(feature_row.get("lat", 29.15))
        lon = float(feature_row.get("lon", 75.73))
        cache_key = (round(lat, 4), round(lon, 4))
        
        # Real soil sample lookup
        if cache_key not in soil_cache:
            try:
                soil_sample, _ = get_soil_context(lat=lat, lon=lon)
                soil_cache[cache_key] = soil_sample
            except:
                soil_cache[cache_key] = soil_scenarios[0]
        
        real_soil = soil_cache[cache_key]
        
        # Build dataset for every soil possibility in this climate zone
        for scenario in [real_soil] + soil_scenarios:
            for crop in crops:
                if int(feature_row["month"]) not in crop["months"]:
                    continue

                rain_score, temp_score, heat_score, water_score = _climate_scores(crop, feature_row)
                revenue = crop["avg_yield_qtl_acre"] * crop["avg_price_inr_qtl"]
                profit_margin = crop["expected_profit_inr_acre"] / max(crop["avg_cost_inr_acre"], 1)

                soil_match = _soil_match_score(crop, scenario["soil_type"])
                ph_match = _ph_match_score(crop, scenario["soil_ph"])
                organic_match = _organic_match_score(crop, scenario["organic_matter_pct"])

                # Aggressive Suitability Scoring
                outcome_score = (
                    0.20 * rain_score
                    + 0.15 * temp_score
                    + 0.10 * water_score
                    + 0.05 * heat_score
                    + 0.20 * soil_match     # Soil type is key
                    + 0.12 * ph_match       # pH is key
                    + 0.08 * organic_match  # Organic matter is key
                    + 0.06 * min(max(crop["expected_profit_inr_acre"] / 80000.0, 0.0), 1.0)
                    + 0.04 * crop["yield_stability_score"]
                )

                label = int(outcome_score >= 0.65)

                rows.append(
                    {
                        **feature_row.to_dict(),
                        "crop": crop["name"],
                        "season": crop["season"],
                        "soil_type": scenario["soil_type"],
                        "soil_ph": scenario["soil_ph"],
                        "organic_matter_pct": scenario["organic_matter_pct"],
                        "soil_soc_gkg": scenario["soil_soc_gkg"],
                        "soil_nitrogen_gkg": scenario["soil_nitrogen_gkg"],
                        "soil_cec_cmolkg": scenario["soil_cec_cmolkg"],
                        "soil_sand_pct": scenario["soil_sand_pct"],
                        "soil_silt_pct": scenario["soil_silt_pct"],
                        "soil_clay_pct": scenario["soil_clay_pct"],
                        "avg_yield_qtl_acre": crop["avg_yield_qtl_acre"],
                        "avg_price_inr_qtl": crop["avg_price_inr_qtl"],
                        "avg_cost_inr_acre": crop["avg_cost_inr_acre"],
                        "expected_profit_inr_acre": crop["expected_profit_inr_acre"],
                        "yield_stability_score": crop["yield_stability_score"],
                        "irrigation_need_score": crop["irrigation_need_score"],
                        "soil_match_score": soil_match,
                        "ph_match_score": ph_match,
                        "organic_matter_match": organic_match,
                        "profit_margin": profit_margin,
                        "revenue_per_acre": revenue,
                        "suitable": label,
                        "composite_outcome_score": round(outcome_score, 4),
                    }
                )

    return pd.DataFrame(rows)


def _build_estimators() -> dict:
    return {
        "xgboost": XGBClassifier(
            n_estimators=400,
            max_depth=7,
            learning_rate=0.06,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            eval_metric="logloss",
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=16,
            random_state=42,
            class_weight="balanced",
        ),
    }


def _evaluate_models(X: pd.DataFrame, y: pd.Series) -> dict:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    summaries = {}
    for name, estimator in _build_estimators().items():
        scores = cross_validate(estimator, X, y, cv=cv, scoring=scoring)
        summaries[name] = {m: round(float(scores[f"test_{m}"].mean()), 4) for m in scoring}
    return summaries


def train() -> dict:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = build_training_data()

    crop_encoder = LabelEncoder()
    df["crop_encoded"] = crop_encoder.fit_transform(df["crop"])

    X = df[FEATURE_COLS]
    y = df["suitable"]

    cv_summary = _evaluate_models(X, y)
    best_name = "xgboost" if cv_summary["xgboost"]["f1"] > 0 else "random_forest"
    model = _build_estimators()[best_name]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, stratify=y, random_state=42)
    model.fit(X_train, y_train)

    # Save artifacts
    joblib.dump(model, MODELS_DIR / "crop_model.pkl")
    joblib.dump({"crop": crop_encoder}, MODELS_DIR / "encoders.pkl")
    
    report = {
        "metadata": {
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "all_india_samples": len(df),
            "model_type": best_name
        },
        "metrics": cv_summary
    }
    with open(MODELS_DIR / "training_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Deep Intelligence Training Complete. Samples: {len(df)}")
    return report


if __name__ == "__main__":
    train()
