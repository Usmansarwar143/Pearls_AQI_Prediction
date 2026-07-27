import os
import json
import hopsworks
import joblib
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

def generate_predictions():
    print("Logging into Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    
    # 1. Fetch Latest Data
    print("Fetching latest AQI features...")
    fs = project.get_feature_store()
    feature_group = fs.get_feature_group(name="aqi_features", version=2)
    query = feature_group.select_all()
    df = query.read(read_options={"use_hive": True})
    
    df = df.sort_values(by="date", ascending=False)
    latest_row = df.iloc[0:1]
    
    recent_history = df.head(7)[['date', 'aqi']].sort_values(by="date", ascending=True)
    history_data = recent_history.to_dict(orient="records")
    
    # 2. Download Models
    print("Downloading models...")
    mr = project.get_model_registry()
    
    hw_scaler = mr.get_model("aqi_scaler", version=1)
    scaler_dir = hw_scaler.download()
    scaler = joblib.load(f"{scaler_dir}/scaler.pkl")
    
    models = {}
    targets = {
        '1d': 'target_aqi_next_1d',
        '2d': 'target_aqi_next_2d',
        '3d': 'target_aqi_next_3d'
    }
    
    for key, target in targets.items():
        hw_model = mr.get_model(f"aqi_model_{target}", version=1)
        model_dir = hw_model.download()
        models[key] = joblib.load(f"{model_dir}/best_model.pkl")
        
    # 3. Predict
    print("Generating predictions...")
    exclude_cols = ['date', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    numeric_df = latest_row.select_dtypes(include=[np.number])
    feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    
    X_latest = numeric_df[feature_cols]
    X_scaled = scaler.transform(X_latest)
    
    preds = {
        "status": "success",
        "data": {
            "current_aqi": float(latest_row['aqi'].values[0]),
            "current_date": str(latest_row['date'].values[0]),
            "history": history_data,
            "predictions": {
                "1_day": float(models['1d'].predict(X_scaled)[0]),
                "2_days": float(models['2d'].predict(X_scaled)[0]),
                "3_days": float(models['3d'].predict(X_scaled)[0])
            }
        }
    }
    
    # 4. Save to JSON
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'predictions.json')
    
    with open(out_path, 'w') as f:
        json.dump(preds, f, indent=4)
        
    print(f"Successfully saved predictions to {out_path}")

if __name__ == "__main__":
    generate_predictions()
