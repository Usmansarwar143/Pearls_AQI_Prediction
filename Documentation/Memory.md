# Pearls AQI Predictor - Project Memory

## 📝 Status
- **Current Phase:** Phase 6 (Final Review & Delivery)
- **Active State:** Phase 5 complete. Web application backend and frontend connected. Ready for final testing and review.

## ✅ Completed Tasks
- [x] Read and analyze project requirements from `AQI_predict-1.pdf`.
- [x] Created `Documentation/PRD.md` (Project Requirements Document).
- [x] Created `Documentation/Architecture.md` (System Flow & Tech Stack).
- [x] Created `Documentation/Rules.md` (Development Guidelines & Boundaries).
- [x] Created `Documentation/Phases.md` (Project Implementation Steps).
- [x] Created `Documentation/Design.md` (UI/UX Aesthetics).
- [x] Phase 1: Initialize Git repo, setup Python environment (`venv`), `.env`, and requirements.txt.
- [x] Phase 2: Perform EDA, write feature pipelines (`fetch_api.py`, `compute_features.py`), and backfill data.
- [x] Phase 3: Train Scikit-Learn/Deep Learning models and evaluate.
- [x] Phase 4: Setup GitHub Actions / Airflow for CI/CD automation.

### 1. Phase Status
- **Phase 1 (Data Engineering & EDA):** Completed. `fetch_api.py` and `compute_features.py` fetch and process data correctly.
- **Phase 2 (Hopsworks Setup):** Completed. Migrated to Hopsworks Feature Store.
- **Phase 3 (Training & Evaluation):** Completed. Migrated models to Hopsworks Model Registry.
- **Phase 4 (Automation):** Completed. Set up GitHub Actions CI/CD workflows for automated hourly feature updates (`hourly_feature_pipeline.yml`) and daily model training (`daily_training_pipeline.yml`).
- **Phase 5 (Web Application):** Completed. FastAPI backend implemented and connected to the HTML/CSS/JS frontend dashboard.
- **Bug Resolution (Forecast Discrepancy Fix):** Resolved forecast jump issue (154, 158, 136 vs current 76). Excluded `timestamp` from training features, removed artificial `owm_to_epa_aqi()` converter, configured dynamic model loading from Hopsworks Model Registry, and set `wait_for_job=True` for backfill synchronization.

### 2. Next Steps
- Transition to **Phase 6 (Final Review & Delivery)**.
- Trigger `retrain-pipeline` GitHub Action to backfill EPA feature data and train new models on EPA AQI scale.
- Perform end-to-end testing of the pipeline and UI.
- Finalize documentation.

## ⏳ Remaining Tasks
- [x] Phase 4: Setup GitHub Actions / Airflow for CI/CD automation.
- [x] Phase 5: Develop the FastAPI backend and HTML/CSS/JS frontend.
- [x] Fix EPA forecast scale mismatch and dynamic model version loading.
- [ ] Phase 6: Final testing, UI polishing, and reporting.

## 📁 Active Files
- `Documentation/Memory.md`
- `src/web_app/generate_predictions.py`
- `src/training_pipeline/train.py`
- `src/training_pipeline/evaluate.py`
- `src/feature_pipeline/backfill.py`

---
*Note: This file should be updated continuously as the project progresses to ensure all context and current state are tracked.*
