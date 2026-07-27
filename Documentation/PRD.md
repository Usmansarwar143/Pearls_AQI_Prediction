# Pearls AQI Predictor - Project Requirements Document (PRD)

## 1. Project Overview
**Pearls AQI Predictor** is a 100% serverless Air Quality Index (AQI) prediction service. Its primary goal is to predict the AQI for a specific city for the next 3 days based on raw weather and pollutant data. 

## 2. Targeted Users
- **General Public:** Individuals planning their outdoor activities based on air quality.
- **Health-Conscious Individuals:** People with respiratory issues needing advance warnings.
- **Environmentalists & Researchers:** Professionals tracking air quality trends and anomalies.
- **Local Governments:** City planners and authorities taking preemptive actions on hazardous days.

## 3. Core Features
- **Data Ingestion:** Fetch raw weather and pollutant data from external APIs (e.g., AQICN, OpenWeather).
- **Feature Engineering:** Compute features (time-based features like hour, day, month) and derived features (e.g., AQI change rate).
- **Historical Backfilling:** Ability to run feature scripts for a range of past dates to generate robust training data.
- **Machine Learning Pipeline:** Train and evaluate multiple ML models (Scikit-learn models like Random Forest, Ridge Regression, and advanced models using TensorFlow/PyTorch).
- **Explainable AI (XAI):** Integration of SHAP or LIME to provide feature importance explanations to users.
- **Automated CI/CD:** Scheduled pipelines (e.g., hourly feature generation, daily model training).
- **Interactive Dashboard:** A web application (HTML/JS frontend + FastAPI backend) to visualize real-time and forecasted AQI data, including alerts for hazardous AQI levels.

## 4. System Requirements
- The system must be 100% serverless (e.g., utilizing Hopsworks or Vertex AI for feature stores/model registries, and GitHub Actions for CI/CD).
- Model evaluation must use standard regression metrics: RMSE, MAE, and R².
- The final submission must include an end-to-end system, scalable pipelines, an interactive dashboard, and a detailed summary report.
