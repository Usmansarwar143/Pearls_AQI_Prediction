# Pearls AQI Predictor - Implementation Phases

## Phase 1: Planning & Setup
- Understand project requirements and finalize documentation (PRD, Architecture, Rules, etc.).
- Initialize GitHub repository and define folder structures.
- Setup external accounts (AQICN/OpenWeather API keys, Hopsworks/Vertex AI accounts).
- Setup Python virtual environment and `.env` files.

## Phase 2: Data Engineering & EDA
- Perform Exploratory Data Analysis (EDA) on historical weather and AQI data in Jupyter Notebooks to identify trends.
- Write the Python feature script to fetch raw data.
- Compute time-based features (hour, day, month) and derived features (AQI change rate).
- Integrate with the Feature Store and verify data ingestion.
- Execute the backfill script for a range of past dates to populate historical data.

## Phase 3: Model Development
- Fetch historical features and targets from the Feature Store.
- Experiment with multiple models: Scikit-learn (Random Forest, Ridge Regression) and Deep Learning (TensorFlow/PyTorch).
- Evaluate models using RMSE, MAE, and R².
- Implement SHAP/LIME for feature importance extraction.
- Register the best performing model in the Model Registry.

## Phase 4: Automation (CI/CD)
- Set up CI/CD pipelines (GitHub Actions or Apache Airflow).
- Create a workflow/DAG to run the **Feature Script every hour**.
- Create a workflow/DAG to run the **Training Script every day**.
- Ensure logs and errors are properly tracked.

## Phase 5: Web Application
- Build a backend API using **FastAPI** to serve models and features.
- Develop the frontend dashboard using **raw HTML, CSS (Vanilla), and JavaScript**.
- Connect the frontend to the FastAPI backend via AJAX/Fetch API to retrieve the latest features and predictions.
- Design simple, descriptive widgets to show predictions and hazardous AQI alerts.

## Phase 6: Final Review & Delivery
- Perform end-to-end testing of the fully automated pipeline.
- Ensure the UI adheres to the design specifications.
- Compile the final detailed report documenting the achievements, challenges, and architecture.
