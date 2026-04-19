# AgriSense Upgrade Report

Date: 2026-04-18

## What was improved

### 1. `soil_type` is now a real model feature

- The backend API now accepts and uses:
  - `soil_type`
  - `soil_ph`
  - `organic_matter_pct`
  - `irrigation_level`
- These values are used in both:
  - training data generation
  - production-time recommendation scoring

Files:

- `backend/routes/recommend.py`
- `backend/ml/train.py`
- `backend/ml/predict.py`

### 2. Richer agronomic and economic crop data

The crop catalog was expanded with:

- preferred soil types
- soil pH ranges
- organic matter thresholds
- irrigation need score
- average yield
- price
- average cost per acre
- expected profit per acre
- yield stability score
- season labels

Files:

- `backend/data/crop_db.json`

### 3. Expanded crop coverage beyond June to September

The system now includes crops from multiple seasons:

- kharif
- rabi
- zaid
- annual
- multi-season

Added coverage includes crops such as:

- Wheat
- Mustard
- Chickpea
- Barley
- Potato
- Onion
- Tomato

This means the recommender now returns results across much more of the year instead of mostly monsoon months only.

### 4. Cross-validation and model comparison

The training pipeline now compares multiple models:

- Logistic Regression
- Random Forest
- XGBoost

The project now:

- runs 5-fold stratified cross-validation
- measures accuracy, precision, recall, F1, and ROC-AUC
- selects the best model automatically
- stores the evaluation report to disk

Files:

- `backend/ml/train.py`
- `backend/models/training_report.json`

### 5. Training metadata is saved after every run

Saved artifacts now include:

- best model pickle
- encoder bundle
- model metadata JSON
- training report JSON

Files:

- `backend/models/crop_model.pkl`
- `backend/models/encoders.pkl`
- `backend/models/model_metadata.json`
- `backend/models/training_report.json`

### 6. Live API fallback now works when Open-Meteo fails

The project no longer hard-fails when live weather fetch is unavailable.

New behavior:

- try live Open-Meteo first
- if that fails, use local cached `weather_raw.csv`

This fixes the previous end-to-end runtime failure for:

- `/api/weather`
- `/api/recommend`

Files:

- `backend/data/fetch_weather.py`
- `backend/routes/weather.py`
- `backend/routes/recommend.py`

### 7. Frontend now exposes the new agronomic inputs

The UI now lets a user pick:

- month across the full year
- soil type
- irrigation level
- soil pH
- organic matter percentage

Files:

- `frontend/src/App.jsx`

### 8. All-India Regional Intelligence (Directions)

The system now supports full geographical analysis across all major Indian zones:
- North, South, East, West, Central, and North-East.
- Added historical success data for each region, including:
  - Notable profitable crops per region.
  - Success rates and historical profit benchmarks (INR/acre).
  - Representative climate summaries (rainfall/temperature history).
- The ML model is now integrated with regional analysis to provide real-time top recommendations for any selected zone.

Files:
- `backend/routes/regional.py`
- `backend/data/regional_history.json`
- `frontend/src/components/RegionalDashboard.jsx`
- `frontend/src/App.jsx`

### 9. Enhanced Visual Aesthetics and UX

The user interface was upgraded to provide a more "premium" feel:
- Glassmorphism design system throughout.
- Fluid navigation between Local Analysis and Regional Dashboard.
- Richer visualizations for confidence percentages and profit benchmarks.
- Interactive regional selector for intuitive directional analysis.

Files:
- `frontend/src/index.css`
- `frontend/src/App.jsx`
- `frontend/src/components/RegionalDashboard.jsx`

## Verification results

### Backend and API

Verified successfully:

- `/api/weather` returns HTTP 200
- `/api/recommend` returns HTTP 200
- when live weather is unavailable, cached weather is used

Observed weather response:

- source: `local-cache`
- used_cache: `true`

### Frontend

Verified successfully:

- `npm run build` completed successfully

Build warnings still present:

- CSS import ordering warning in `src/index.css`
- large bundle size warning from Vite

These are not blocking runtime.

### Model training

Latest saved metrics:

- selected model: `xgboost`
- training rows: `14454`
- test rows: `2891`
- holdout accuracy: `0.9914`
- holdout F1: `0.9944`
- holdout ROC-AUC: `0.9997`

Cross-validation summary:

- logistic regression F1: `0.9580`
- random forest F1: `0.9890`
- xgboost F1: `0.9951`

## Proof boundary: what can and cannot be proven

The project is substantially stronger now, but it still cannot honestly prove that it gives the best real-world agricultural recommendations.

Why that cannot be proven yet:

- the training labels are still generated from agronomic rules and crop profile logic inside the project
- there is still no external ground-truth dataset of real farm outcomes by district, soil, irrigation, and season
- there is no benchmark against published extension-service recommendations or farm trial results
- there is no out-of-sample validation on independently collected farmer data

So the correct claim is:

- the upgraded system gives better structured and more realistic agronomic recommendations than before
- the model is well-evaluated against the project’s richer internal labels
- the project is not yet scientifically proven to be the best real-world recommender

## What would be needed to prove real-world quality

To move from "strong prototype" to "provably strong real-world recommender", the project would need:

1. A real historical farm dataset with observed crop outcome labels.
2. Yield and profit records by location, month, irrigation, and soil condition.
3. Independent validation data not created from the same project rules.
4. Benchmark comparison against agricultural extension recommendations or regional agronomy datasets.
5. Field or retrospective validation showing better outcomes than a baseline recommendation method.

## Practical outcome

The project is now much more usable:

- it no longer breaks when live weather fetch fails
- it uses soil and irrigation context for predictions
- it supports more seasons and crops
- it stores full model evaluation artifacts
- it exposes the richer controls in the frontend

That is a meaningful upgrade in both engineering quality and recommendation realism.
