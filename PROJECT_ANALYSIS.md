# AgriSense Project Analysis

Date checked: 2026-04-18
Workspace: `c:\Users\rixha\WorkSpace\FullStack\agrs`

## 1. Overall status

The project is partially working.

- The backend application starts successfully.
- The frontend builds successfully for production.
- The saved ML model loads successfully.
- The live recommendation and weather endpoints do not work in the current checked environment because they try to fetch weather from Open-Meteo every time a request is made.

So the project is not fully working end to end right now. It works structurally, but the live API flow depends on external weather access.

## 2. Backend check

Backend entrypoint: `backend/main.py`

What works:

- The FastAPI app loads successfully.
- The root endpoint `/` responds with HTTP 200.
- The backend includes two main API routes:
  - `/api/recommend`
  - `/api/weather`

Observed result:

- Root endpoint response: `{"status": "AgriSense API is running 🌾"}`

What fails:

- `/api/weather` returns HTTP 500 when the app cannot reach Open-Meteo.
- `/api/recommend` also returns HTTP 500 for the same reason.

Why it fails:

- `backend/routes/weather.py` calls `fetch_weather(lat, lon)` on every request.
- `backend/routes/recommend.py` also calls `fetch_weather(req.lat, req.lon)` on every request.
- `backend/data/fetch_weather.py` always requests data from `https://archive-api.open-meteo.com/v1/archive`.

That means the backend has no offline fallback for request-time weather retrieval.

## 3. Frontend check

Frontend entrypoint: `frontend/src/App.jsx`

What works:

- The React/Vite project builds successfully with `npm run build`.
- The UI is wired to:
  - show API status
  - search a location using Open-Meteo geocoding
  - submit a recommendation request
  - fetch chart data for weather history

Observed build result:

- Build succeeded
- Output bundle was generated in `frontend/dist`

Warnings found during build:

- CSS warning: `@import` appears after Tailwind directives in `src/index.css`
- Large JS chunk warning: the built JS bundle is about `589.19 kB`

Important runtime dependency:

- The frontend depends on the backend at `http://localhost:8000`
- It also depends on Open-Meteo geocoding for search suggestions

What this means:

- The frontend itself is valid and buildable.
- But user-facing features are only fully usable when the backend can access live weather data.

## 4. ML pipeline explanation

Main ML flow file: `backend/run_pipeline.py`

The pipeline has four stages:

1. Fetch daily weather data
2. Convert daily weather into monthly ML features
3. Train an XGBoost suitability model
4. Save the trained model for production use

### Stage 1: Weather ingestion

File: `backend/data/fetch_weather.py`

The project fetches:

- daily maximum temperature
- daily minimum temperature
- daily precipitation
- daily maximum relative humidity
- daily maximum wind speed
- daily FAO evapotranspiration (`et0_fao_evapotranspiration`)

Configured range:

- Start date: `2015-01-01`
- End date: current date at runtime

Data found in the current saved dataset:

- `weather_raw.csv` rows: `4126`
- Date range: `2015-01-01` to `2026-04-18`

That means the system currently has about 11.3 years of daily weather data saved locally.

## 5. Feature engineering

File: `backend/ml/features.py`

Daily weather is grouped by `year` and `month` and converted into monthly features.

Monthly features created:

- `total_rain`
- `avg_temp_max`
- `avg_temp_min`
- `avg_humidity`
- `max_wind`
- `total_et0`
- `temp_range`
- `heat_stress_days`
- `water_balance`
- `rain_3m_rolling`
- `is_monsoon`

Meaning of important engineered fields:

- `heat_stress_days`: number of days in the month where max temperature is greater than 35 C
- `water_balance`: rainfall minus evapotranspiration
- `rain_3m_rolling`: rolling average rainfall across 3 months
- `is_monsoon`: 1 for June to September, otherwise 0

Saved feature dataset:

- `features.csv` rows: `136`

This is correct for monthly aggregation over the saved 2015-01 to 2026-04 range.

## 6. Training data creation

File: `backend/ml/train.py`

This project does not train on real historical farmer outcome labels.

Instead, it creates synthetic labels using rule logic from `backend/data/crop_db.json`.

How it builds labels:

- For each monthly weather row
- For each crop in the crop database
- It keeps only crops whose planting season includes that month
- It marks a crop as `suitable = 1` only if:
  - monthly rainfall passes the crop threshold
  - monthly max temperature falls inside the crop temperature range
- Otherwise it labels the example as `suitable = 0`

Training dataset size:

- Total rows: `363`
- Crop classes represented: `10`
- Label distribution:
  - unsuitable (`0`): `275`
  - suitable (`1`): `88`

Important interpretation:

- The model is learning to imitate hand-coded agronomic rules.
- It is not learning from observed yields, farmer profits, or field trial outcomes.
- So the model accuracy mainly measures how well XGBoost reproduces the generated rules.

## 7. Model details

File: `backend/ml/train.py`

Model type:

- `XGBClassifier`

Hyperparameters found:

- `n_estimators = 200`
- `max_depth = 6`
- `learning_rate = 0.1`
- `eval_metric = logloss`

Encoded crop classes:

- Cluster Bean (Guar)
- Cotton
- Groundnut
- Maize
- Moong Bean
- Pearl Millet (Bajra)
- Rice (Paddy)
- Sesame (Til)
- Sorghum (Jowar)
- Sugarcane

## 8. How much did the model train?

From the code and saved model:

- The model was trained on `363` generated crop-month examples.
- It used a train/test split of 80/20.
- That means approximately:
  - training rows: about `290`
  - test rows: about `73`

The saved training code does not store:

- number of boosting rounds actually used by early stopping
- validation history
- training loss curve
- timestamped experiment metrics

But the configured estimator count is `200`, so the model was trained with 200 trees.

## 9. Model quality

Recomputed test accuracy from the saved model:

- Accuracy: `97.26%`

Confusion matrix:

- true negatives: `56`
- false positives: `0`
- false negatives: `2`
- true positives: `15`

Classification report summary:

- Class `0` precision: `0.9655`
- Class `0` recall: `1.0000`
- Class `1` precision: `1.0000`
- Class `1` recall: `0.8824`
- Weighted F1: `0.9720`

Important warning about this result:

- This is not proof that the model gives the best real-world results.
- The labels came from the same rule system the model is trying to learn.
- Because of that, the score mostly shows the model is very good at reproducing those generated labels.

In other words:

- the model is internally consistent
- the model is not externally validated on real agricultural outcomes

## 10. Is the project getting data?

Yes, there is evidence that it has already received and saved data locally.

Current saved data:

- Raw daily weather rows: `4126`
- Monthly feature rows: `136`
- Training rows after crop expansion: `363`

But for live API usage:

- the project must fetch fresh weather data again at request time
- if that external request fails, the recommendation endpoints fail

So the correct answer is:

- Yes, the project has data locally.
- Yes, it processes that saved data.
- No, live requests are not robust because they still depend on external weather access.

## 11. Is it processing the data?

Yes.

The processing path is:

1. download daily weather
2. aggregate daily weather into monthly weather summaries
3. derive stress and water features
4. expand monthly rows across crop definitions
5. generate suitability labels
6. train the classifier
7. save the model
8. score crops for a chosen month and location

This is a complete processing pipeline.

## 12. Is it giving the best dataset and best results?

Not in a strong scientific sense.

What it does well:

- uses a sensible weather history range
- creates useful agronomic features
- gives interpretable crop recommendations
- produces high agreement with its own synthetic labels

What prevents calling it the "best" dataset or "best" results:

- the training labels are generated from hand-written crop rules
- there is no real ground-truth yield dataset
- there is no profit optimization
- there is no soil-feature usage in the model even though `soil_type` exists in the API schema
- there is no cross-validation
- there is no comparison with baseline models
- there is no external validation against known recommended crops for a district and season

So the more accurate statement is:

- it gives rule-consistent recommendations
- it does not prove best real-world agricultural recommendations

## 13. Recommendation output example

Using the saved monthly features for `July 2024`, the model produces top recommendations such as:

1. Cluster Bean (Guar) - `99.5`
2. Pearl Millet (Bajra) - `99.4`
3. Moong Bean - `99.4`
4. Cotton - `98.8`
5. Maize - `97.8`

Weather used for that month:

- rainfall: `206.1 mm`
- avg max temp: `35.99 C`
- avg min temp: `27.45 C`
- avg humidity: `88.97`
- heat stress days: `23`
- water balance: `53.56 mm`
- rolling 3 month rain: `82.4 mm`
- monsoon flag: `1`

Interpretation:

- the model strongly favors kharif-season crops in July
- it especially favors crops with lower water demand and suitable temperature tolerance

## 14. Important project limitations

### 14.1 Live API dependency

Files:

- `backend/routes/recommend.py`
- `backend/routes/weather.py`
- `backend/data/fetch_weather.py`

Problem:

- both API endpoints fail when Open-Meteo is unreachable

Effect:

- the app may look healthy at `/`
- but the main features can still fail for end users

### 14.2 The model is trained on generated labels

File:

- `backend/ml/train.py`

Problem:

- labels come from rule checks in code, not real crop success records

Effect:

- high model accuracy does not equal high field accuracy

### 14.3 `soil_type` is accepted but unused

File:

- `backend/routes/recommend.py`

Problem:

- the request schema includes `soil_type`
- but it is not used in feature creation or prediction

Effect:

- recommendations do not actually change based on soil type

### 14.4 Seasonal coverage is narrow

File:

- `backend/data/crop_db.json`

Problem:

- crop definitions only cover kharif-style months, mainly June to September

Effect:

- for months like April, `predict_crops` can return an empty list
- the app is not a year-round crop planner right now

### 14.5 Encoding issues in console output

Files:

- `backend/ml/predict.py`
- several frontend strings

Problem:

- emoji and some special characters can display incorrectly on Windows `cp1252`

Effect:

- console output can break or look garbled in some environments

## 15. How the project works end to end

### Backend flow

1. Frontend sends location, month, and year to `/api/recommend`
2. Backend downloads historical daily weather for the selected coordinates
3. Backend converts that daily weather into monthly feature rows
4. Backend selects the requested month and year
5. Backend scores all crops that match the chosen month
6. Backend returns the top crop recommendations with confidence, yield, price, and explanation

### Weather chart flow

1. Frontend sends coordinates to `/api/weather`
2. Backend downloads weather history again
3. Backend converts it into monthly features
4. Backend returns recent monthly summaries for charts

### Frontend flow

1. User searches a district or uses geolocation
2. Frontend keeps selected coordinates in state
3. User chooses month and year
4. Frontend requests recommendations from the backend
5. Frontend renders crop cards and weather charts

## 16. Final assessment

The project is a good prototype, but not yet a fully reliable production system.

Best summary:

- Backend core app: working
- Frontend build: working
- Saved ML model: working
- Offline saved data analysis: working
- Live weather fetch: not reliable in the checked environment
- Live recommendation endpoint: not fully working because of weather fetch dependency
- Model performance against generated labels: strong
- Real-world proof of best crop recommendation: not established

## 17. Suggested next improvements

If this project should become truly reliable, the best next steps are:

1. Add cached/offline weather fallback so APIs still work when Open-Meteo is unavailable.
2. Use `soil_type` as a real model feature or remove it from the API.
3. Add real outcome data such as yield, profitability, irrigation availability, and soil measurements.
4. Add cross-validation and model comparison instead of only one train/test split.
5. Expand crop coverage beyond June to September.
6. Store model metrics and training metadata after every training run.

