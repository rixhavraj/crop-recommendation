# AgriSense ML Performance Report

Date: 2026-04-20
Project: AgriSense backend

## Training Summary

The model was retrained successfully using the backend ML pipeline.

- Training sample count: `21,390`
- Selected model: `XGBoost`
- Training completed with cached soil fallback because live SoilGrids access was blocked in this environment

## Cross-Validation Metrics

From `models/training_report.json`:

### XGBoost

- Accuracy: `0.9940`
- Precision: `0.9955`
- Recall: `0.9967`
- F1 score: `0.9961`
- ROC AUC: `0.9998`

### Random Forest

- Accuracy: `0.9907`
- Precision: `0.9938`
- Recall: `0.9942`
- F1 score: `0.9940`
- ROC AUC: `0.9996`

## Holdout Test Metrics

I also evaluated the saved model on a separate 15% stratified holdout split:

- Accuracy: `0.9947`
- Precision: `0.9964`
- Recall: `0.9968`
- F1 score: `0.9966`
- ROC AUC: `0.9998`

### Classification Report

- Class `0`
  - Precision: `0.9892`
  - Recall: `0.9879`
  - F1: `0.9885`
  - Support: `742`
- Class `1`
  - Precision: `0.9964`
  - Recall: `0.9968`
  - F1: `0.9966`
  - Support: `2467`

## Sample Prediction Test

Test input:

- Month: `July`
- Weather: hot monsoon-like conditions
- Soil: loam
- State: Haryana

Top predicted crops:

1. Rice (Paddy) - `100.0%`
2. Pearl Millet (Bajra) - `100.0%`
3. Cotton - `100.0%`
4. Maize - `100.0%`
5. Sorghum (Jowar) - `100.0%`

## Notes

- The backend server and frontend dev server were launched successfully in the host environment.
- Backend startup log showed Uvicorn running on `http://127.0.0.1:8000`.
- Frontend startup log showed Vite running on `http://127.0.0.1:5173`.
- Local HTTP requests from the sandboxed shell could not reliably connect to those listeners, so the validation was done through process logs and offline ML evaluation.

## Interpretation

The model is performing very strongly on the project's generated suitability labels.

Important caveat:

- The labels are rule-generated from agronomic logic, not from real field outcome data.
- So these scores show the model is good at reproducing the project's own suitability rules.
- They do not prove real-world agricultural superiority.
