import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import hopsworks
from dotenv import load_dotenv

load_dotenv()

def train_and_evaluate():
    print("Connecting to Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    fs = project.get_feature_store()
    
    print("Fetching Feature Group 'aqi_features'...")
    try:
        fg = fs.get_feature_group(name="aqi_features", version=2)
        query = fg.select_all()
        df = query.read(read_options={"use_hive": True})
    except Exception as e:
        print("Error fetching data from Hopsworks:", e)
        return

    print(f"Data loaded from Hopsworks. Shape: {df.shape}")

    # Drop NaNs for targets
    df = df.dropna(subset=['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d'])
    
    # Features (X)
    exclude_cols = ['date', 'timestamp', 'target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    numeric_df = df.select_dtypes(include=[np.number])
    feature_cols = [c for c in numeric_df.columns if c not in exclude_cols]
    X = numeric_df[feature_cols]
    
    print(f"Features used ({len(feature_cols)}): {feature_cols}")

    targets = ['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d']
    
    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Save the scaler and feature column list locally first
    os.makedirs('data/models/scaler', exist_ok=True)
    joblib.dump(scaler, 'data/models/scaler/scaler.pkl')
    with open('data/models/scaler/feature_cols.json', 'w') as f:
        json.dump(feature_cols, f, indent=2)
    print("Scaler and feature column metadata saved locally.")

    mr = project.get_model_registry()

    # Save scaler to Model Registry
    print("Uploading scaler to Hopsworks Model Registry...")
    hw_scaler = mr.python.create_model(
        name="aqi_scaler", 
        description="StandardScaler for AQI features (EPA scale, timestamp excluded)"
    )
    hw_scaler.save('data/models/scaler')

    for target in targets:
        print(f"\nTraining models for {target}...")
        y = numeric_df[target]
        
        # Split data temporally
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, shuffle=False)
        
        # Random Forest
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        rf_preds = rf.predict(X_test)
        
        # Ridge
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train, y_train)
        ridge_preds = ridge.predict(X_test)
        
        rf_r2 = r2_score(y_test, rf_preds)
        ridge_r2 = r2_score(y_test, ridge_preds)
        
        print(f"  Random Forest R2: {rf_r2:.4f}")
        print(f"  Ridge Regression R2: {ridge_r2:.4f}")
        
        best_model = rf if rf_r2 > ridge_r2 else ridge
        best_name = "RandomForest" if rf_r2 > ridge_r2 else "Ridge"
        print(f"  Best model for {target}: {best_name}")
        
        # Save model locally first
        model_dir = f'data/models/{target}'
        os.makedirs(model_dir, exist_ok=True)
        model_path = f'{model_dir}/best_model.pkl'
        joblib.dump(best_model, model_path)
        
        # Save to Model Registry
        print(f"  Uploading {best_name} to Hopsworks Model Registry for {target}...")
        hw_model = mr.python.create_model(
            name=f"aqi_model_{target}", 
            metrics={"r2": rf_r2 if rf_r2 > ridge_r2 else ridge_r2},
            description=f"Best model for {target} using {best_name} (US EPA scale 0-500)"
        )
        hw_model.save(model_dir)
        print(f"  Saved {target} model to Hopsworks.")

    print("\nTraining complete and all assets uploaded to Hopsworks!")

if __name__ == "__main__":
    train_and_evaluate()
