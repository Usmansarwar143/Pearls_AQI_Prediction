# Pearls AQI Predictor - Rules & Guidelines

## 1. Core Principles
- **100% Serverless:** Everything from data storage, model registry, CI/CD, to web hosting should utilize serverless, managed services (e.g., GitHub Actions, Hopsworks Serverless, Streamlit Cloud, Vercel).
- **Modularity:** Keep feature extraction, model training, and inference separated into independent scripts/services.

## 2. What to Use
- **Python:** Strict adherence to Python for data science and backend operations.
- **Environment Variables:** All secrets, API keys (AQICN, OpenWeather, Hopsworks), and configuration strings MUST be stored in `.env` files or CI/CD Secret Managers.
- **Logging:** Implement standard Python `logging` for all pipelines to monitor daily and hourly runs in CI/CD.

## 3. What to Avoid
- **Avoid Stateful Servers:** Do not rely on local databases or continuously running EC2 instances. 
- **Avoid Hardcoding Secrets:** Never commit API keys or sensitive data to version control.
- **Avoid Monoliths:** Do not bundle the model training logic inside the web application codebase.

## 4. Error Handling
- **API Resilience:** Implement retries and fallback logic using `try-except` blocks when fetching external API data.
- **Graceful Degradation:** If the Feature Store or Model Registry is temporarily unreachable, the web app should display a cached prediction or a user-friendly error message rather than crashing.
- **Data Validation:** Validate incoming API data (check for NaNs, missing dates) before pushing to the Feature Store.

## 5. Boundaries of AI
- **Explainability:** Predictions must not be a "black box". Use SHAP or LIME to show users exactly *why* the AQI is predicted to be at a certain level.
- **Forecast Limits:** Limit predictions strictly to a 3-day window as requested; accuracy heavily diminishes beyond this point.
- **Disclaimer:** The web app must clearly state that these are AI-generated estimations and should not supersede official government health warnings in extreme scenarios.
