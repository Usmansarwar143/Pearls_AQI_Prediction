import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import hopsworks
from dotenv import load_dotenv

load_dotenv()

def evaluate_models():
    print("Connecting to Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    fs = project.get_feature_store()
    mr = project.get_model_registry()
    
    print("Fetching Feature Group 'aqi_features'...")
    try:
        fg = fs.get_feature_group(name="aqi_features", version=1)
        df = fg.read()
    except Exception as e:
        print("Error fetching data from Hopsworks:", e)
        return

    df = df.dropna(subset=['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d'])
    
    exclude_cols = ['date', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    numeric_df = df.select_dtypes(include=[np.number])
    feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    X = numeric_df[feature_cols]
    
    print("Downloading scaler from Model Registry...")
    try:
        hw_scaler = mr.get_model("aqi_scaler", version=1)
        scaler_dir = hw_scaler.download()
        scaler = joblib.load(scaler_dir + '/scaler.pkl')
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
            hw_model = mr.get_model(f"aqi_model_{target}", version=1)
            model_dir = hw_model.download()
            model = joblib.load(model_dir + '/best_model.pkl')
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
