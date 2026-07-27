# Pearls AQI Predictor - Architecture & Technical Stack

## 1. Project Flow
The system is divided into three distinct operational pipelines that act upon a central Feature Store and Model Registry:

1. **Feature Pipeline (Data Ingestion & Engineering):**
   - Fetches external data (AQICN, OpenWeather).
   - Generates and structures features.
   - Saves features to the Feature Store.
2. **Training Pipeline (Model Development):**
   - Retrieves historical data (features & targets) from the Feature Store.
   - Trains and evaluates models.
   - Saves the best-performing model to the Model Registry.
3. **Inference / Web App Pipeline:**
   - Loads the latest features from the Feature Store and the best model from the Model Registry.
   - Computes predictions and renders them on an interactive dashboard.

## 2. Technology Stack
- **Language:** Python 3.10+
- **Machine Learning:** Scikit-Learn (Random Forest, Ridge Regression), TensorFlow, PyTorch.
- **MLOps (Feature Store & Model Registry):** Hopsworks or Vertex AI (Free Tiers).
- **Automation / CI-CD:** GitHub Actions or Apache Airflow.
- **Backend API:** FastAPI or Flask.
- **Frontend App:** Streamlit or Gradio.
- **Explainable AI:** SHAP or LIME.
- **Data Handling:** Pandas, NumPy.

## 3. Folder & File Structure (Proposed)
```text
Pearls_AQI_Prediction/
├── .github/workflows/          # CI/CD automation scripts
├── data/                       # Local cached data (if any)
├── notebooks/                  # EDA and experimentation notebooks
├── src/                        # Main source code
│   ├── feature_pipeline/       # Scripts to fetch data and push to feature store
│   │   ├── fetch_api.py
│   │   ├── compute_features.py
│   │   └── backfill.py
│   ├── training_pipeline/      # Scripts to pull data, train, and register model
│   │   ├── train.py
│   │   └── evaluate.py
│   └── web_app/                # Dashboard and API code
│       ├── backend_api.py      # FastAPI/Flask server
│       └── frontend_app.py     # Streamlit/Gradio dashboard
├── Documentation/              # Project Documentation (PRD, Architecture, etc.)
├── requirements.txt            # Python dependencies
└── .env.example                # Example environment variables (API keys)
```
