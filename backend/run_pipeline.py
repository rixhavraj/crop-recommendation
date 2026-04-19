"""
AgriSense ML Pipeline
1. Fetch or load cached weather data
2. Engineer monthly weather features
3. Train and benchmark multiple suitability models
4. Save the best model and training metadata
"""

import json

import joblib

from data.fetch_weather import get_weather_data
from ml.features import engineer_features
from ml.train import train


print("=" * 60)
print("STEP 1: Loading historical weather data")
print("=" * 60)

df, source_meta = get_weather_data(29.15, 75.73)
df.to_csv("data/weather_raw.csv", index=False)
date_min = df["date"].min()
date_max = df["date"].max()
years = (date_max - date_min).days / 365.25
print(f"  Source: {source_meta['source']}")
print(f"  Rows: {len(df)}")
print(f"  Date range: {date_min.strftime('%Y-%m-%d')} to {date_max.strftime('%Y-%m-%d')}")
print(f"  Span: {years:.1f} years")
print()

print("=" * 60)
print("STEP 2: Engineering monthly features")
print("=" * 60)

features = engineer_features(df)
features.to_csv("data/features.csv", index=False)
print(f"  Generated {len(features)} monthly rows")
print(f"  Feature columns: {list(features.columns)}")
print()

print("=" * 60)
print("STEP 3: Benchmarking and training models")
print("=" * 60)

report = train()
print(f"  Selected model: {report['metadata']['selected_model']}")
print(f"  Holdout accuracy: {report['holdout_metrics']['accuracy']:.2%}")
print(f"  Holdout F1: {report['holdout_metrics']['f1']:.4f}")
print()

print("=" * 60)
print("STEP 4: Verifying saved artifacts")
print("=" * 60)

model = joblib.load("models/crop_model.pkl")
encoders = joblib.load("models/encoders.pkl")
with open("models/model_metadata.json", encoding="utf-8") as f:
    metadata = json.load(f)

print(f"  Model type: {type(model).__name__}")
print(f"  Selected model name: {metadata['selected_model']}")
print(f"  Encoded crops: {list(encoders['crop'].classes_)}")
print(f"  Encoded soils: {list(encoders['soil_type'].classes_)}")
print(f"  Encoded irrigation levels: {list(encoders['irrigation_level'].classes_)}")
print()

print("=" * 60)
print("PIPELINE COMPLETE")
print("=" * 60)
