import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import hopsworks
from dotenv import load_dotenv

load_dotenv()

def get_latest_model(mr, name):
    """Retrieve the latest version of a model from Hopsworks Model Registry."""
    try:
        models = mr.get_models(name)
        if models:
            return max(models, key=lambda m: m.version)
        return mr.get_model(name)
    except Exception:
        return mr.get_model(name)


def evaluate_models():
    print("Connecting to Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    fs = project.get_feature_store()
    mr = project.get_model_registry()
    
    fg_version = int(os.getenv("HOPSWORKS_FEATURE_GROUP_VERSION", 3))
    print(f"Fetching Feature Group 'aqi_features' version {fg_version}...")
    try:
        fg = fs.get_feature_group(name="aqi_features", version=fg_version)
        query = fg.select_all()
        df = query.read(read_options={"use_hive": True})
    except Exception as e:
        print("Error fetching data from Hopsworks:", e)
        return

    df = df.dropna(subset=['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d'])
    
    exclude_cols = ['date', 'timestamp', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    numeric_df = df.select_dtypes(include=[np.number])
    feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    X = numeric_df[feature_cols]
    
    print("Downloading latest scaler from Model Registry...")
    try:
        hw_scaler = get_latest_model(mr, "aqi_scaler")
        print(f"Loaded scaler version: {hw_scaler.version}")
        scaler_dir = hw_scaler.download()
        scaler = joblib.load(os.path.join(scaler_dir, 'scaler.pkl'))
    except Exception as e:
        print("Error downloading scaler:", e)
        return
        
    X_scaled = scaler.transform(X)

    targets = ['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    
    print("\n--- Model Evaluation (Hopsworks) ---")
    for target in targets:
        y = numeric_df[target]
        _, X_test, _, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)
        
        try:
            hw_model = get_latest_model(mr, f"aqi_model_{target}")
            print(f"Evaluating {target} using model version: {hw_model.version}")
            model_dir = hw_model.download()
            model = joblib.load(os.path.join(model_dir, 'best_model.pkl'))
        except Exception as e:
            print(f"Error downloading model for {target}:", e)
            continue
            
        preds = model.predict(X_test)
        
        r2 = r2_score(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        mae = mean_absolute_error(y_test, preds)
        
        print(f"Target: {target}")
        print(f"  R2 Score: {r2:.4f}")
        print(f"  RMSE:     {rmse:.4f}")
        print(f"  MAE:      {mae:.4f}")
        print("-" * 25)

if __name__ == "__main__":
    evaluate_models()
