import os
import hopsworks
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Pearls AQI Predictor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store loaded models and data
models = {}
scaler = None
feature_group = None
fs = None

def get_latest_data_and_predict():
    global feature_group, fs
    if feature_group is None:
        project = hopsworks.login(
            project=os.getenv("HOPSWORKS_PROJECT_NAME"),
            api_key_value=os.getenv("HOPSWORKS_API_KEY")
        )
        fs = project.get_feature_store()
        feature_group = fs.get_feature_group(name="aqi_features", version=2)

    # Fetch the latest data
    query = feature_group.select_all()
    df = query.read(read_options={"use_hive": True})
    
    # Sort by date descending and get the most recent row
    df = df.sort_values(by="date", ascending=False)
    latest_row = df.iloc[0:1]
    
    # Also return the last 7 days of historical AQI for the chart
    recent_history = df.head(7)[['date', 'aqi']].sort_values(by="date", ascending=True)
    history_data = recent_history.to_dict(orient="records")
    
    # Prepare features for prediction
    exclude_cols = ['date', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    numeric_df = latest_row.select_dtypes(include=[np.number])
    feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    
    X_latest = numeric_df[feature_cols]
    
    # Scale features
    X_scaled = scaler.transform(X_latest)
    
    # Predict
    preds = {
        "current_aqi": float(latest_row['aqi'].values[0]),
        "current_date": str(latest_row['date'].values[0]),
        "history": history_data,
        "predictions": {
            "1_day": float(models['1d'].predict(X_scaled)[0]),
            "2_days": float(models['2d'].predict(X_scaled)[0]),
            "3_days": float(models['3d'].predict(X_scaled)[0])
        }
    }
    
    return preds

@app.on_event("startup")
def load_models():
    global models, scaler
    print("Logging into Hopsworks to download models...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    mr = project.get_model_registry()
    
    print("Downloading scaler...")
    hw_scaler = mr.get_model("aqi_scaler", version=1)
    scaler_dir = hw_scaler.download()
    scaler = joblib.load(f"{scaler_dir}/scaler.pkl")
    
    targets = {
        '1d': 'target_aqi_next_1d',
        '2d': 'target_aqi_next_2d',
        '3d': 'target_aqi_next_3d'
    }
    
    for key, target in targets.items():
        print(f"Downloading model for {target}...")
        hw_model = mr.get_model(f"aqi_model_{target}", version=1)
        model_dir = hw_model.download()
        models[key] = joblib.load(f"{model_dir}/best_model.pkl")
        
    print("All models loaded successfully!")

@app.get("/api/predict")
def predict():
    try:
        result = get_latest_data_and_predict()
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Serve static files for the frontend
app.mount("/", StaticFiles(directory="src/web_app/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.web_app.api:app", host="0.0.0.0", port=8000, reload=True)
