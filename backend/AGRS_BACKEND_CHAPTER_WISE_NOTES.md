# AgriSense Backend Chapter Wise Notes

Date: 2026-04-20  
Scope: `backend/` folder of the AgriSense project

This document is written for a computer science beginner who wants to understand:

- what this backend does
- how every major file works
- how the ML pipeline is built
- how requests move from the API to the model and back
- what each feature means
- how to explain this project in an interview

## Table of Contents

1. Project idea
2. Backend folder structure
3. Tech stack and core concepts
4. Application entrypoint: `main.py`
5. API routes
6. Data layer
7. ML feature engineering
8. ML training pipeline
9. ML prediction pipeline
10. Model artifacts
11. Support scripts
12. Request flow examples
13. Interview-ready explanation
14. Limitations and improvement ideas

---

## 1. Project Idea

AgriSense backend is an agriculture recommendation system.

Its main job is to help a user answer questions like:

- Which crop is suitable for my location?
- What crops fit the current weather and soil?
- What is the historical weather trend in my area?
- What should I know about irrigation, rainfall, and soil?

The backend uses:

- FastAPI for web APIs
- weather data from Open-Meteo
- soil data from SoilGrids
- a crop catalog stored in JSON
- an ML model trained on engineered weather and crop features

The system is not a generic chatbot only. It is a data-driven crop advisory backend.

---

## 2. Backend Folder Structure

The important backend files are:

- `main.py`
- `run_pipeline.py`
- `test_request.py`
- `requirements.txt`
- `data/fetch_weather.py`
- `data/fetch_soil.py`
- `data/features.csv`
- `data/weather_raw.csv`
- `data/crop_db.json`
- `data/regional_history.json`
- `data/india_locations.json`
- `ml/features.py`
- `ml/train.py`
- `ml/predict.py`
- `models/crop_model.pkl`
- `models/encoders.pkl`
- `models/model_metadata.json`
- `models/training_report.json`
- `routes/recommend.py`
- `routes/weather.py`
- `routes/regional.py`
- `routes/chat.py`

There are also cache folders:

- `data/weather_cache/`
- `data/soil_cache/`

These are used so the app can reuse previously fetched data when live API calls fail or are slow.

---

## 3. Tech Stack and Core Concepts

### 3.1 FastAPI

FastAPI is a Python web framework used to build APIs.

In this backend:

- `FastAPI()` creates the web app
- `APIRouter()` is used to split endpoints into separate files
- `@router.get(...)` and `@router.post(...)` define routes
- `pydantic.BaseModel` defines request and response schemas

### 3.2 Pandas

Pandas is used for table-like data.

It handles:

- CSV reading
- grouping data by month and year
- calculating averages and sums
- turning daily data into monthly features

### 3.3 Scikit-learn

Scikit-learn provides:

- `LabelEncoder`
- `train_test_split`
- `cross_validate`
- `StratifiedKFold`
- metrics like accuracy, precision, recall, F1, ROC AUC

### 3.4 XGBoost

XGBoost is a machine learning model that is good at tabular data.

In this project, it is used to predict whether a crop is suitable or not.

### 3.5 Joblib

Joblib saves and loads trained ML models from disk.

That is why `crop_model.pkl` and `encoders.pkl` can be reused without retraining.

### 3.6 External APIs

The project talks to two external services:

- Open-Meteo for weather
- SoilGrids for soil properties

If they fail, the backend tries local cache or fallback values.

---

## 4. Application Entrypoint: `main.py`

File: [`backend/main.py`](./main.py)

This is the file that starts the FastAPI application.

### What it imports

- `os` for environment variables
- `FastAPI` to create the app
- `CORSMiddleware` to allow frontend requests
- route modules: `chat`, `recommend`, `weather`, `regional`
- `load_dotenv()` to read variables from `.env`

### What the code does

#### `load_dotenv()`

This loads environment variables from `.env`.

That allows configuration like:

- allowed origins
- API base settings

#### `_parse_origins(raw_value)`

This helper function converts a comma-separated string into a Python list.

Example:

- input: `"http://localhost:5173,http://127.0.0.1:5173"`
- output: `["http://localhost:5173", "http://127.0.0.1:5173"]`

If no custom value is provided, it uses default local frontend origins.

#### `app = FastAPI(...)`

This creates the main backend app.

The app has:

- title: `AgriSense API`
- description: `India-wide AI crop recommendation and farmer assistant API`
- version: `1.0.0`

#### `app.add_middleware(CORSMiddleware, ...)`

CORS means Cross-Origin Resource Sharing.

It allows the frontend running on another port, such as `5173`, to call the backend safely.

#### `app.include_router(...)`

Each router is attached under `/api`.

So the actual routes become:

- `/api/recommend`
- `/api/weather`
- `/api/regional/{region_name}`
- `/api/regions`
- `/api/chat`

#### `@app.get("/")`

The root endpoint returns a small status message.

It is a quick check that the backend is alive.

#### `@app.get("/health")`

This is a health check endpoint.

It returns `{"status": "ok"}`.

### Interview explanation

You can say:

> `main.py` is the startup file. It creates the FastAPI app, adds CORS support, registers all route modules, and exposes basic health endpoints.

---

## 5. API Routes

The backend has four major route files.

1. `routes/recommend.py`
2. `routes/weather.py`
3. `routes/regional.py`
4. `routes/chat.py`

Each file has one responsibility.

---

## 5.1 Recommendation Route: `routes/recommend.py`

File: [`backend/routes/recommend.py`](./routes/recommend.py)

This is the main crop recommendation endpoint.

### Request model: `RecommendRequest`

This Pydantic model defines the input the API expects.

Fields:

- `district`: location name
- `lat`: latitude
- `lon`: longitude
- `month`: month number from 1 to 12
- `year`: calendar year
- `soil_type`: optional user-provided soil type
- `soil_ph`: optional pH value
- `organic_matter_pct`: optional organic matter percentage
- `irrigation_level`: optional irrigation preference

Important details:

- `month` is validated to stay between 1 and 12
- optional fields allow the user to override soil data if they know it

### Response model: `CropResult`

This defines the output structure for each recommended crop.

Fields:

- `crop`
- `confidence`
- `water_req`
- `avg_yield_qtl_acre`
- `price`
- `avg_cost_inr_acre`
- `expected_profit_inr_acre`
- `season`
- `reason`
- `emoji`
- `growth_instructions`
- `regional_success_rate`
- `regional_avg_profit`
- `ai_analysis`

### Main endpoint: `@router.post("/recommend")`

This endpoint generates crop recommendations.

#### Step 1: Import helpers

Inside the function, it imports:

- `get_soil_context`
- `get_weather_data`
- `engineer_features`
- `predict_crops`

They are imported inside the route so the app does not load them unnecessarily on startup.

#### Step 2: Fetch historical weather

`get_weather_data(req.lat, req.lon, location_name=req.district)` fetches daily weather history.

If no weather data is returned, the function raises `404`.

#### Step 3: Convert daily weather into monthly features

`engineer_features(weather_df)` groups daily weather into month-level rows.

This is needed because crop recommendation is done on monthly climate patterns, not raw daily rows.

#### Step 4: Find the requested month and year

The code first tries:

- exact `year` and `month`

If that is not found, it falls back to:

- matching only `month`

This makes the route more flexible when exact year data is missing.

#### Step 5: Get soil context

`get_soil_context(req.lat, req.lon)` returns soil properties for the location.

Then user-provided values can override the fetched soil values:

- `soil_type`
- `soil_ph`
- `organic_matter_pct`
- `irrigation_level`

#### Step 6: Predict crops

`predict_crops(weather_dict, soil_context=soil_context, state=state)` returns ranked crops.

The result is sorted by confidence.

#### Step 7: Return recommendations

If no recommendations are found, it raises `404`.

Otherwise it returns the list of `CropResult`.

### Error handling

The route catches:

- `HTTPException` and re-raises it
- all other exceptions as `500`

### Interview explanation

You can say:

> The recommendation route collects weather and soil inputs, converts weather into monthly features, then uses the ML prediction module to rank the most suitable crops for that month and location.

---

## 5.2 Weather Route: `routes/weather.py`

File: [`backend/routes/weather.py`](./routes/weather.py)

This route is used to inspect weather history, current weather, and soil for a location.

### Endpoint

`@router.get("/weather")`

### Query parameters

- `lat`
- `lon`
- `location_name`

### What it does

#### Step 1: Get ten years of history

The route calculates a start date about ten years ago.

This is used to load long-term weather history.

#### Step 2: Fetch data from three sources

It calls:

- `get_weather_data(...)` for historical weather
- `get_current_weather(...)` for live weather and forecast
- `get_soil_context(...)` for soil profile

#### Step 3: Handle missing history

If no historical data exists, it still returns:

- current weather
- forecast
- soil
- metadata about the source

This is a graceful fallback.

#### Step 4: Engineer monthly trends

If history exists, `engineer_features(history_df)` creates monthly rows.

Then the latest 120 months are used to create a chart-friendly list called `historical_trend`.

Each trend row includes:

- label like `Jul 24`
- rainfall
- temp_max
- temp_min
- water_balance
- humidity

### Why this route matters

It powers weather graphs and climate summaries in the frontend.

### Interview explanation

You can say:

> The weather route combines live weather, forecast, soil, and historical trend data so the user can understand the agricultural conditions of the selected location.

---

## 5.3 Regional Route: `routes/regional.py`

File: [`backend/routes/regional.py`](./routes/regional.py)

This route gives region-level agricultural information.

### Data loaded at module level

- `regional_history.json`
- `india_locations.json`

### Response model

#### `HistSuccess`

Represents historical crop success for one crop in a region.

Fields:

- `crop`
- `avg_profit`
- `success_rate`
- `notable_year`

#### `RegionalReport`

Represents the complete regional response.

Fields:

- `region`
- `states`
- `historical_success`
- `weather_summary`
- `top_recommended_crops`

### Endpoint: `@router.get("/regional/{region_name}")`

This route:

1. checks whether the region exists
2. finds a representative location in that region
3. fetches weather for that location
4. engineers features
5. filters rows for the requested month
6. computes average weather conditions
7. calls `predict_crops(...)`
8. returns region history plus crop suggestions

### Why a representative location is used

Some regions contain many states.

Instead of fetching all locations, the code picks one city or district as a sample weather anchor.

### Endpoint: `@router.get("/regions")`

Returns the list of available region names.

### Interview explanation

You can say:

> The regional route summarizes crop success by Indian region and combines that with weather-based recommendations for a representative location in that region.

---

## 5.4 Chat Route: `routes/chat.py`

File: [`backend/routes/chat.py`](./routes/chat.py)

This route acts like a rule-based agricultural assistant.

It is not a real large language model. It is a structured response generator.

### Request model: `ChatRequest`

Fields:

- `district`
- `lat`
- `lon`
- `question`
- `month`
- `year`

The `question` field must be at least 2 characters.

### Helper: `_is_hindi(text)`

Checks whether the input contains Hindi script characters.

This is done with a regex that matches Devanagari Unicode range.

### Helper: `_format_crop_list(recommendations)`

Turns the top crops into a readable string like:

- `Wheat (95.0%), Rice (90.0%), Mustard (88.5%)`

If no recommendations exist, it returns a fallback message.

### Helper: `_english_answer(...)`

This function looks at the question text and tries to classify intent.

It answers differently for:

- crop recommendation
- weather questions
- soil questions
- fertilizer questions
- water or irrigation questions
- generic questions

This is simple intent matching using keywords.

### Helper: `_hindi_answer(...)`

This does the same thing as `_english_answer`, but returns Hindi responses.

The Hindi answers appear partially encoded in the source file, but the intention is clear:

- answer in Hindi when the user writes in Hindi
- give crop, weather, soil, and irrigation help

### Main endpoint: `@router.post("/chat")`

This route:

1. fetches historical weather
2. fetches soil
3. fetches current weather
4. engineers monthly weather features
5. extracts a matching row for the requested month and year
6. generates crop recommendations
7. builds a weather context object
8. chooses English or Hindi response based on the input
9. returns:
   - `answer`
   - `soil`
   - `weather`
   - `recommendations`

### Important idea

This chat endpoint is rule-driven, not generative AI.

It simulates helpful answers using data and keyword detection.

### Interview explanation

You can say:

> The chat route is a lightweight agricultural assistant that answers in English or Hindi by combining weather, soil, and crop recommendation data with keyword-based intent handling.

---

## 6. Data Layer

The data layer handles weather, soil, and agricultural reference information.

---

## 6.1 Weather Fetching: `data/fetch_weather.py`

File: [`backend/data/fetch_weather.py`](./data/fetch_weather.py)

This is one of the most important backend files.

It is responsible for:

- fetching weather history
- fetching current weather
- caching responses
- loading cached weather if live data fails
- building a multi-location India weather dataset

### Important constants

- `DATA_DIR`: folder containing data files
- `WEATHER_CACHE_DIR`: folder for cached weather JSON
- `DEFAULT_END_DATE`: current date minus 5 days
- `DEFAULT_CACHE_LAT`, `DEFAULT_CACHE_LON`: default sample coordinates
- `DEFAULT_CURRENT_WEATHER`: empty fallback structure

### Helper: `_cache_path(lat, lon, suffix)`

Creates a deterministic cache file name for a location.

It uses an MD5 hash of:

- latitude
- longitude
- suffix

This avoids problems with long or invalid file names.

### Helper: `_normalize_weather_frame(...)`

This function standardizes weather data returned from different sources.

It:

- copies the dataframe
- ensures `date` exists
- drops duplicate `time`
- converts `date` to datetime
- creates `year` and `month`
- stores `lat` and `lon`
- stores `location_name`
- creates a unique `location_id`
- stores `state` if given
- renames columns to a consistent naming scheme
- removes duplicated columns

This is important because API data and CSV data can use different column names.

### Function: `load_cached_weather(...)`

This tries to read weather from local cache first.

If cache is missing, it falls back to `weather_raw.csv`.

If the CSV is used:

- it computes distance between requested coordinates and saved locations
- it picks the closest location if the distance is small enough

That means the project can still work even when the exact location has no cached data.

### Function: `fetch_weather(...)`

This calls the Open-Meteo archive API.

It requests:

- max temperature
- min temperature
- precipitation
- relative humidity
- wind speed
- evapotranspiration

After fetching:

- the response is turned into a dataframe
- normalized
- optionally saved to cache

### Function: `fetch_current_weather(...)`

This calls the Open-Meteo forecast API.

It gets:

- current temperature
- humidity
- apparent temperature
- precipitation
- weather code
- cloud cover
- wind speed
- wind direction

It also creates a short 3-day forecast list.

### Function: `load_cached_current_weather(...)`

Loads previously saved current weather from cache.

### Function: `get_weather_data(...)`

This is the safe public function used by routes and ML code.

Behavior:

1. try live fetch
2. if live fails, load cache
3. return data plus metadata telling where it came from

This is a good example of a live-data-with-fallback pattern.

### Function: `get_current_weather(...)`

Same pattern as above, but for current weather.

### Function: `load_india_locations()`

Loads all predefined Indian locations from `india_locations.json`.

### Function: `build_india_weather_dataset(...)`

Downloads or loads weather for every listed location and combines them into one dataframe.

This supports dataset generation and training.

### Interview explanation

You can say:

> The weather module standardizes weather data from Open-Meteo, caches it locally, and falls back to saved CSV data if live API access fails.

---

## 6.2 Soil Fetching: `data/fetch_soil.py`

File: [`backend/data/fetch_soil.py`](./data/fetch_soil.py)

This file fetches and normalizes soil information.

### Important constants

- `SOIL_CACHE_DIR`: local soil cache folder
- `SOIL_PROPERTIES`: soil properties to request
- `SOIL_DEPTHS`: depth layers
- `SOIL_VALUES`: metric type, here `mean`

### Helper: `_cache_path(lat, lon)`

Generates a cache file name for a coordinate pair.

### Helper: `_classify_soil(sand_pct, clay_pct, silt_pct)`

This turns percentage composition into a soil type label.

Rules:

- high clay -> `clay`
- high sand -> `sandy`
- high silt -> `silty`
- clay + low sand -> `black`
- moderate silt and clay -> `alluvial`
- otherwise -> `loam`

This is a heuristic classification, not a scientific lab classification.

### Helper: `_mean_depth_value(layer)`

Extracts the mean value across all depth samples in one soil layer.

It also applies the depth factor correction.

### Helper: `_normalise_soil_payload(payload)`

Converts the raw SoilGrids response into a compact dictionary:

- `soil_type`
- `soil_ph`
- `organic_matter_pct`
- `soil_soc_gkg`
- `soil_nitrogen_gkg`
- `soil_cec_cmolkg`
- `soil_sand_pct`
- `soil_silt_pct`
- `soil_clay_pct`
- `source`

It also converts soil organic carbon into estimated organic matter.

### Function: `fetch_soil(lat, lon)`

Calls the SoilGrids API.

Then:

- normalizes the payload
- saves raw and normalized data in cache
- returns the normalized soil context

### Function: `load_cached_soil(lat, lon)`

Loads soil context from cache.

### Function: `get_soil_context(lat, lon, prefer_live=True)`

This is the main public function.

Behavior:

1. try live SoilGrids request
2. if that fails, use cached soil
3. if cache also fails, return a hardcoded India-like fallback loam profile

The fallback is very important because it keeps the system usable even when third-party soil APIs fail.

### Interview explanation

You can say:

> The soil module queries SoilGrids, converts the raw response into useful agronomic fields, caches the result, and uses a realistic fallback profile if everything else fails.

---

## 6.3 Reference Crop Data: `data/crop_db.json`

File: [`backend/data/crop_db.json`](./data/crop_db.json)

This is the crop knowledge base used by the backend.

It contains:

- crop names
- valid months
- seasons
- rainfall minimums
- temperature ranges
- water requirement levels
- preferred soil types
- pH ranges
- organic matter thresholds
- expected yield
- price
- cost
- expected profit
- yield stability
- emoji

### Why this file is important

This file is the source of crop-specific business logic.

The model does not invent crop properties on its own.

Instead, the crop database gives it:

- agronomic constraints
- economic values
- seasonality

### Example interpretation

For a crop like Wheat:

- it is a rabi crop
- it likes cooler temperatures
- it prefers loam/alluvial/clay
- it has moderate water need

This makes the JSON file a compact agricultural reference table.

### Interview explanation

You can say:

> `crop_db.json` is the agricultural knowledge base. It stores the crop season, soil preference, climate needs, and economic estimates used by both training and prediction.

---

## 6.4 Regional Knowledge: `data/regional_history.json`

File: [`backend/data/regional_history.json`](./data/regional_history.json)

This file maps Indian regions to:

- states
- historical crop success

Each historical record contains:

- crop name
- average profit
- success rate
- notable year

This data helps the regional route and chat route answer region-specific questions.

### Interview explanation

You can say:

> The regional history file provides human-readable historical context so the backend can explain which crops have done well in each region.

---

## 6.5 India Locations: `data/india_locations.json`

This file lists sample Indian locations with coordinates and states.

It supports:

- weather fetching
- region matching
- training dataset generation

### Why it matters

The backend needs coordinates to query weather and soil APIs.

The locations file provides those coordinates in a structured form.

---

## 7. ML Feature Engineering

File: [`backend/ml/features.py`](./ml/features.py)

Feature engineering means converting raw data into useful ML inputs.

The model cannot learn directly from messy daily data.
It needs structured monthly features.

### Main function: `engineer_features(df)`

This function takes daily weather records and returns monthly aggregated rows.

### Step 1: Find grouping columns

The function groups by:

- location information, if present
- `year`
- `month`

This means each output row usually represents one location and one month.

### Step 2: Detect weather column names

Different inputs may use slightly different names.

The code handles aliases such as:

- `precipitation`
- `precipitation_sum`
- `total_rain`

Similarly for wind speed and humidity.

This makes the function resilient to different data sources.

### Step 3: Define aggregation map

It calculates:

- `total_rain` as sum
- `avg_temp_max` as mean
- `avg_temp_min` as mean
- `max_wind` as max
- `avg_humidity` as mean if available
- `total_et0` as sum if available

### Step 4: Clean the dataframe

The function:

- removes duplicates
- resets index

This avoids grouping errors.

### Step 5: Group by month

Daily records are grouped into monthly rows.

This is the main conversion from raw daily weather to monthly climate summary.

### Step 6: Count heat stress days

Heat stress is defined as:

- maximum temperature greater than 35 C

The function counts how many days in a month cross that threshold.

### Step 7: Compute derived features

The function adds:

- `temp_range` = max temp - min temp
- `water_balance` = rainfall - evapotranspiration
- `is_monsoon` = 1 if month is June to September

### Step 8: Compute rolling rainfall

It calculates `rain_3m_rolling`.

This is a 3-month rolling average, which smooths rainfall trends.

### Why these features matter

These features help the model understand:

- rainfall availability
- temperature stress
- water deficit or surplus
- seasonal patterns

### Interview explanation

You can say:

> The feature engineering module converts daily weather into monthly agronomic indicators like rainfall, heat stress, water balance, and monsoon season flag so the ML model can learn on clean tabular data.

---

## 8. ML Training Pipeline

File: [`backend/ml/train.py`](./ml/train.py)

This is the most important ML file in the project.

It builds training data, trains models, evaluates them, and saves the best one.

---

### 8.1 Imports

The file imports:

- standard library modules: `json`, `datetime`, `Path`, `sys`
- `joblib`
- `pandas`
- scikit-learn model and metric utilities
- `XGBClassifier`
- `get_soil_context`

### Why `sys.path` is modified

The script adds the backend directory to `sys.path`.

That allows direct execution of `train.py` from the command line without import path issues.

---

### 8.2 Feature Columns: `FEATURE_COLS`

This list defines the exact inputs the model expects.

It includes:

- climate features
- agronomic features
- soil features
- economic features
- `crop_encoded`

This is very important because training and prediction must use the same columns.

### Important beginner concept

An ML model cannot accept random columns.

It must receive exactly the features it was trained on, in the same structure.

---

### 8.3 Catalog Helpers

#### `_load_catalog()`

Loads crop definitions from `crop_db.json`.

#### `_soil_match_score(crop, soil_type)`

Returns:

- `1.0` if the soil is preferred
- `0.4` otherwise

This is a soft match score.

#### `_ph_match_score(crop, soil_ph)`

Checks whether soil pH falls within the crop’s preferred range.

If not, it decreases the score depending on how far the pH is from the acceptable range.

#### `_organic_match_score(crop, organic_matter_pct)`

Checks organic matter sufficiency in the same way.

#### `_climate_scores(crop, row)`

Computes:

- rain score
- temp score
- heat penalty
- water score

These scores measure how well a crop matches the climate row.

---

### 8.4 `build_training_data()`

This is where the training dataset is created.

#### Step 1: Load monthly features

It reads `features.csv`.

That file contains monthly climate data.

#### Step 2: Load crop catalog

It loads all crops from the crop database.

#### Step 3: Prepare soil cache

It keeps a local dictionary called `soil_cache` so repeated coordinates do not trigger repeated soil API calls.

#### Step 4: Define fallback soil scenarios

The code creates several soil scenarios:

- loam
- clay
- sandy
- black
- alluvial

These help the model see a variety of soil conditions.

This is a form of data augmentation.

#### Step 5: Iterate over weather rows

For each monthly weather row:

- extract latitude and longitude
- find or fetch real soil data
- fall back to generic soil if needed

#### Step 6: Combine weather and soil scenarios

For each weather row, the script loops through:

- real soil
- each synthetic soil scenario

Then it loops through every crop.

This creates many training examples.

#### Step 7: Skip crops not valid for the month

If the month is not in the crop’s allowed months, it is skipped.

This ensures seasonality matters.

#### Step 8: Compute revenue and profit features

The code calculates:

- `revenue`
- `profit_margin`

These are economics-related features.

#### Step 9: Compute match scores

It calculates:

- `soil_match`
- `ph_match`
- `organic_match`

These help the model understand soil compatibility.

#### Step 10: Build the composite suitability score

The code combines:

- rain
- temperature
- water balance
- heat stress
- soil match
- pH match
- organic matter match
- profit potential
- yield stability

This produces a number called `outcome_score`.

#### Step 11: Create the label

If `outcome_score >= 0.65`, the crop is labeled as suitable (`1`).

Otherwise it is labeled as unsuitable (`0`).

This means the labels are generated by rules, not by real farmer outcome data.

That is very important in interviews.

### Beginner interpretation

The project creates its own training labels because real agricultural outcome labels are not available.

So the model learns the same agronomic rules that were used to generate the labels.

---

### 8.5 `_build_estimators()`

This function defines two candidate models:

- `XGBClassifier`
- `RandomForestClassifier`

The XGBoost model uses:

- many trees
- depth control
- learning rate
- subsampling

The Random Forest uses:

- 300 trees
- max depth 16
- balanced class weights

### Why two models?

This allows comparison.

The project can choose the stronger performer.

---

### 8.6 `_evaluate_models(X, y)`

This runs cross-validation.

It uses:

- `StratifiedKFold`
- `cross_validate`
- metrics:
  - accuracy
  - precision
  - recall
  - F1
  - ROC AUC

### Why cross-validation matters

It tests the model on multiple splits, which gives a more stable estimate than one split alone.

---

### 8.7 `train()`

This is the main training function.

#### Step 1: Create model directory

`MODELS_DIR.mkdir(...)`

This ensures the folder exists before saving files.

#### Step 2: Build training data

`df = build_training_data()`

#### Step 3: Encode crop names

`LabelEncoder()` converts crop names into integers.

Example:

- Rice -> 0
- Wheat -> 1

The exact mapping depends on the dataset.

#### Step 4: Split features and label

- `X = df[FEATURE_COLS]`
- `y = df["suitable"]`

#### Step 5: Evaluate models

It computes CV metrics for XGBoost and Random Forest.

#### Step 6: Choose best model

The code currently chooses:

- `xgboost` if its F1 is greater than 0
- otherwise `random_forest`

This logic is simple and effectively always chooses XGBoost if it trained successfully.

#### Step 7: Train/test split

It creates:

- training set
- test set

#### Step 8: Fit the model

`model.fit(X_train, y_train)`

#### Step 9: Save artifacts

It saves:

- `crop_model.pkl`
- `encoders.pkl`

#### Step 10: Save training report

It writes `training_report.json` with metadata and metrics.

#### Step 11: Return report

The function returns the report dictionary.

### Important note

This training file is the source of the saved model, but there is a small mismatch between `run_pipeline.py` and the saved metadata formats.

That does not affect the notes, but it is useful to know when explaining the code.

### Interview explanation

You can say:

> The training pipeline generates crop suitability labels from agronomic rules, encodes crop names, compares XGBoost and Random Forest with cross-validation, then saves the best model and metadata to disk.

---

## 9. ML Prediction Pipeline

File: [`backend/ml/predict.py`](./ml/predict.py)

This file is used when the backend needs to recommend crops.

It loads the trained model, creates feature rows, predicts confidence, and explains the result.

---

### 9.1 Loading model artifacts

At module load time, it tries to read:

- `crop_model.pkl`
- `encoders.pkl`
- `model_metadata.json`

If loading fails, the code switches to rule-based scoring.

### Why this matters

The backend will still function even if the ML model is missing.

That is a good resilience pattern.

---

### 9.2 `REGIONAL_HISTORY`

The file loads `regional_history.json`.

This lets prediction include regional success context.

---

### 9.3 `_get_region_for_state(state)`

This maps a state to one of the known Indian regions.

If the state is found in a region’s state list, that region is returned.

If not, it returns `None`.

---

### 9.4 `_get_growth_instructions(crop_name)`

This returns human-readable farming advice for certain crops.

Examples:

- rice water management
- wheat irrigation stages
- cotton pest management
- maize drainage

If a crop is not in the hardcoded map, it returns generic advice.

### Why this is useful

It makes recommendations more actionable for the user.

---

### 9.5 `_build_feature_row(crop, weather, soil_context)`

This is a key function.

It constructs one complete feature dictionary for one crop at one location and time.

It combines:

- weather features
- crop economic fields
- soil features
- derived scores
- crop encoding

If the crop encoder exists:

- it tries to encode the crop name

If the crop name is unseen:

- it sets `crop_encoded = -1`

This prevents crashes for unknown crop labels.

---

### 9.6 `_rule_based_score(crop, weather, soil_context)`

If the ML model is unavailable, this function creates a fallback confidence score.

It evaluates:

- rainfall match
- temperature match
- water balance
- heat stress
- soil match
- pH match
- organic matter match
- profit potential

Then it returns a score between 5 and 98.

### Why fallback scoring exists

It keeps crop recommendation working even when the saved model cannot be loaded.

This is a major robustness feature.

---

### 9.7 `_generate_reason(crop_result, weather, soil_context)`

This creates a natural-language explanation for why a crop is recommended.

It may mention:

- rainfall match
- temperature match
- suitable soil
- profit potential

This is important for explainability.

### 9.8 `_generate_ai_analysis(...)`

This produces a longer “AI style” explanation.

It references:

- confidence
- historical regional success
- temperature
- rainfall
- soil profile

It is not true generative AI.

It is template-based reasoning language.

---

### 9.9 `predict_crops(weather_features, soil_context=None, top_n=5, state=None)`

This is the main public prediction function.

#### Step 1: Set defaults

If no soil context is provided, it uses an empty dictionary.

#### Step 2: Get month

The month is extracted from `weather_features`.

#### Step 3: Find regional context

If a state is provided, it maps the state to a region and retrieves historical success records.

#### Step 4: Loop through crops

For each crop:

- skip it if the month is not allowed
- build feature row
- if the ML model is available, predict probability
- otherwise use rule-based scoring

#### Step 5: Add crop details

The result includes:

- crop name
- confidence
- water requirement
- yield
- price
- cost
- profit
- season
- emoji
- growth instructions
- regional success rate
- regional average profit
- AI analysis

#### Step 6: Sort and return top results

The final list is sorted by confidence and trimmed to `top_n`.

Then each item gets a `reason`.

### Interview explanation

You can say:

> The prediction module scores every crop that is valid for the given month, uses the trained model if available, falls back to rule-based scoring otherwise, and then returns the top ranked crops with explanations.

---

## 10. Model Artifacts

The `models/` folder stores the trained outputs.

### `crop_model.pkl`

This is the trained classifier.

### `encoders.pkl`

This stores the label encoder used for crop names.

### `model_metadata.json`

This stores summary information like:

- trained timestamp
- selected model
- feature columns
- training rows
- class balance
- crop classes

### `training_report.json`

This stores more readable training metrics such as:

- accuracy
- precision
- recall
- F1
- ROC AUC

### Why artifacts matter

Without these files, the app would have to retrain every time.

Saving them makes prediction fast.

---

## 11. Support Scripts

### 11.1 `run_pipeline.py`

File: [`backend/run_pipeline.py`](./run_pipeline.py)

This script shows the full end-to-end workflow.

It does four things:

1. loads historical weather
2. engineers features
3. trains the model
4. verifies saved artifacts

It is useful as a project demo or reproducible pipeline.

### Note about script alignment

The script expects certain keys in the training report and metadata.

Some of those names are not perfectly aligned with the saved JSON files.

So this file is best treated as a high-level orchestration script rather than a guaranteed plug-and-play runner.

### 11.2 `test_request.py`

File: [`backend/test_request.py`](./test_request.py)

This is a simple manual API test script.

It sends a sample payload to the recommendation endpoint.

Useful fields:

- `district`
- `lat`
- `lon`
- `month`
- `year`
- `soil_type`
- `soil_ph`
- `organic_matter_pct`
- `irrigation_level`

It reads `API_BASE_URL` from environment variables if available.

If not, it uses `http://localhost:8000/api`.

### Why this file exists

It is a quick sanity-check tool for developers.

### 11.3 `requirements.txt`

This file lists Python dependencies:

- FastAPI
- Uvicorn
- python-dotenv
- requests
- pandas
- numpy
- scikit-learn
- xgboost
- joblib

These are the core packages needed by the backend.

---

## 12. Request Flow Examples

This chapter explains how one user request flows through the backend.

### 12.1 Crop recommendation flow

1. The frontend sends location, month, year, and optional soil details.
2. `/api/recommend` receives the request.
3. Weather history is fetched.
4. Weather rows are converted into monthly features.
5. Soil is fetched or loaded from cache.
6. The requested month is selected.
7. Each crop is scored.
8. The top crops are returned as JSON.

### 12.2 Weather dashboard flow

1. The frontend asks for weather at a location.
2. `/api/weather` loads history, current weather, and soil.
3. Monthly trends are computed.
4. A chart-friendly response is returned.

### 12.3 Chat flow

1. User asks a question like “Which crop is best?”
2. `/api/chat` fetches weather, soil, and recommendations.
3. The question is matched against keywords.
4. A structured response is returned in English or Hindi.

---

## 13. Interview-Ready Explanation

If someone asks you to explain this backend in simple terms, you can say:

> AgriSense backend is a FastAPI-based agriculture recommendation system. It fetches weather and soil data for a given location, converts daily weather into monthly features, uses crop knowledge from JSON files, and predicts suitable crops with a trained XGBoost model. If the model or live APIs fail, it has fallback logic so the system still provides useful answers.

If they ask about ML specifically:

> The ML model is trained on engineered climate, soil, and crop-economic features. The labels are created using agronomic rule logic, so the model learns to reproduce those suitability rules. The backend saves the trained model with Joblib and uses it later for fast predictions.

If they ask about explainability:

> Each recommendation includes a confidence score, reason, growth instructions, and regional context, so the system is easier to trust and explain.

---

## 14. Limitations and Improvement Ideas

This section is useful for interviews because it shows that you understand the project critically.

### 14.1 Current limitations

- The ML labels are rule-generated, not based on real field outcomes
- Weather requests still depend on an external API
- Soil type provided by the user is not deeply used in the model input path
- Crop coverage is limited by the crop catalog months
- The chat system is keyword-based, not a real generative AI model

### 14.2 Good improvement ideas

- use real historical yield data
- add stronger offline caching
- add more crops and more seasons
- use soil type as an explicit prediction feature
- add model comparison dashboards
- add probability calibration
- store training run history
- improve multilingual responses

---

## 15. File-by-File Quick Summary

- `main.py`: creates the FastAPI app and registers routes
- `routes/recommend.py`: generates crop recommendations
- `routes/weather.py`: returns current and historical weather context
- `routes/regional.py`: returns region-level crop insights
- `routes/chat.py`: answers agri questions in English or Hindi
- `data/fetch_weather.py`: fetches and caches weather data
- `data/fetch_soil.py`: fetches and caches soil data
- `data/crop_db.json`: crop knowledge base
- `data/regional_history.json`: historical regional crop data
- `data/india_locations.json`: supported locations
- `ml/features.py`: turns daily weather into monthly ML features
- `ml/train.py`: builds training data and trains the model
- `ml/predict.py`: scores crops and creates explanations
- `run_pipeline.py`: runs the full pipeline end to end
- `test_request.py`: manual request test script
- `requirements.txt`: Python dependencies

---

## 16. Final Takeaway

This backend is a strong educational project because it combines:

- API development
- data fetching
- caching
- feature engineering
- classification modeling
- rule-based fallback logic
- explainable outputs

It is especially good for interviews because it demonstrates:

- practical FastAPI work
- ML pipeline understanding
- data preprocessing knowledge
- system design thinking
- graceful fallback design

If you study this document and the code together, you should be able to answer beginner to medium interview questions about the project with confidence.
