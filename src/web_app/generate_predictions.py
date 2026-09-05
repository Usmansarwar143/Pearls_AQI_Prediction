import os
import json
import hopsworks
import joblib
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()


def get_latest_model(mr, name):
    """Retrieve the highest version model object from Hopsworks Model Registry."""
    try:
        models = mr.get_models(name)
        if models:
            return max(models, key=lambda m: m.version)
        return mr.get_model(name)
    except Exception:
        return mr.get_model(name)


def generate_predictions():
    print("Logging into Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    
    fg_version = int(os.getenv("HOPSWORKS_FEATURE_GROUP_VERSION", 3))
    print(f"Fetching latest AQI features from Feature Group 'aqi_features' version {fg_version}...")
    fs = project.get_feature_store()
    feature_group = fs.get_feature_group(name="aqi_features", version=fg_version)
    query = feature_group.select_all()
    df = query.read(read_options={"use_hive": True})
    
    df = df.sort_values(by="date", ascending=False)
    latest_row = df.iloc[0:1]
    
    recent_history = df.head(7)[['date', 'aqi']].sort_values(by="date", ascending=True)
    recent_history['date'] = recent_history['date'].astype(str)
    history_data = recent_history.to_dict(orient="records")
    
    # 2. Download Latest Scaler & Models
    print("Downloading latest models from Model Registry...")
    mr = project.get_model_registry()
    
    hw_scaler = get_latest_model(mr, "aqi_scaler")
    print(f"Using scaler version: {hw_scaler.version}")
    scaler_dir = hw_scaler.download()
    scaler = joblib.load(os.path.join(scaler_dir, "scaler.pkl"))
    
    # Load feature column metadata if saved with the scaler
    feature_cols_path = os.path.join(scaler_dir, "feature_cols.json")
    if os.path.exists(feature_cols_path):
        with open(feature_cols_path, "r") as f:
            feature_cols = json.load(f)
        print(f"Loaded feature columns from scaler metadata ({len(feature_cols)} features).")
    elif hasattr(scaler, 'feature_names_in_'):
        # Use the scaler's own record of expected features (most reliable fallback)
        feature_cols = list(scaler.feature_names_in_)
        print(f"Using feature columns from scaler.feature_names_in_ ({len(feature_cols)} features).")
    else:
        exclude_cols = ['date', 'timestamp', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
        numeric_df = latest_row.select_dtypes(include=[np.number])
        feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    
    models = {}
    targets = {
        '1d': 'target_aqi_next_1d',
        '2d': 'target_aqi_next_2d',
        '3d': 'target_aqi_next_3d'
    }
    
    for key, target in targets.items():
        hw_model = get_latest_model(mr, f"aqi_model_{target}")
        print(f"Using model for {target} (version: {hw_model.version})")
        model_dir = hw_model.download()
        models[key] = joblib.load(os.path.join(model_dir, "best_model.pkl"))
        
    # 3. Predict Direct US EPA AQI
    print("Generating predictions...")
    numeric_df = latest_row.select_dtypes(include=[np.number])
    
    # Ensure all features expected by the scaler are present, fill missing ones with 0
    for col in feature_cols:
        if col not in numeric_df.columns:
            print(f"  WARNING: Feature '{col}' expected by scaler but missing from data. Filling with 0.")
            numeric_df = numeric_df.copy()
            numeric_df[col] = 0
    
    X_latest = numeric_df[feature_cols]
    X_scaled = scaler.transform(X_latest)
    
    raw_1d = float(models['1d'].predict(X_scaled)[0])
    raw_2d = float(models['2d'].predict(X_scaled)[0])
    raw_3d = float(models['3d'].predict(X_scaled)[0])
    
    print(f"Raw model predictions: 1d={raw_1d:.2f}, 2d={raw_2d:.2f}, 3d={raw_3d:.2f}")

    # Detect legacy 1-5 scale models and warn if needed
    if any(p < 10 for p in [raw_1d, raw_2d, raw_3d]) and float(latest_row['aqi'].values[0]) > 20:
        print("WARNING: Model predictions are < 10 while current AQI is on US EPA scale.")
        print("This indicates an older model version trained on the 1-5 OWM scale was loaded.")
        print("Please trigger the 'retrain-pipeline' GitHub Action to train and register EPA-scale models.")

    # Clamp predictions to valid EPA AQI range [0, 500]
    pred_1d = max(0, min(500, round(raw_1d)))
    pred_2d = max(0, min(500, round(raw_2d)))
    pred_3d = max(0, min(500, round(raw_3d)))
    
    preds = {
        "status": "success",
        "data": {
            "current_aqi": float(latest_row['aqi'].values[0]),
            "current_date": str(latest_row['date'].values[0]),
            "history": history_data,
            "predictions": {
                "1_day": pred_1d,
                "2_days": pred_2d,
                "3_days": pred_3d
            }
        }
    }
    
    # 4. Save to JSON
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'predictions.json')
    
    with open(out_path, 'w') as f:
        json.dump(preds, f, indent=4, default=str)
        
    print(f"Successfully saved predictions to {out_path}")


if __name__ == "__main__":
    generate_predictions()
