import os
import json
import hopsworks
import joblib
import pandas as pd
import numpy as np
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
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


def get_model_metadata(model, hw_model):
    """Extract metadata and hyperparameters from a sklearn model."""
    model_type = type(model).__name__
    params = {}

    if isinstance(model, RandomForestRegressor):
        params = {
            "n_estimators": model.n_estimators,
            "max_depth": str(model.max_depth) if model.max_depth else "None (unlimited)",
            "min_samples_split": model.min_samples_split,
            "min_samples_leaf": model.min_samples_leaf,
            "max_features": str(model.max_features),
            "random_state": model.random_state,
        }
    elif isinstance(model, Ridge):
        params = {
            "alpha": model.alpha,
            "solver": model.solver,
            "fit_intercept": model.fit_intercept,
            "max_iter": model.max_iter,
        }

    return {
        "model_type": model_type,
        "version": hw_model.version,
        "parameters": params,
    }


def compute_shap_values(model, X_scaled, feature_cols, X_background=None):
    """Compute SHAP values for a single prediction row."""
    try:
        if isinstance(model, RandomForestRegressor):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_scaled)
            base_value = float(explainer.expected_value)
        elif isinstance(model, Ridge):
            if X_background is not None:
                explainer = shap.LinearExplainer(model, X_background)
            else:
                explainer = shap.LinearExplainer(model, X_scaled)
            shap_values = explainer.shap_values(X_scaled)
            base_value = float(explainer.expected_value)
        else:
            # Fallback for unknown model types
            explainer = shap.KernelExplainer(model.predict, X_scaled[:1])
            shap_values = explainer.shap_values(X_scaled)
            base_value = float(explainer.expected_value)

        # Get SHAP values for the latest row (first/only row)
        if len(shap_values.shape) == 1:
            sv = shap_values
        else:
            sv = shap_values[0]

        # Build per-feature breakdown
        feature_shap = {}
        for i, col in enumerate(feature_cols):
            feature_shap[col] = round(float(sv[i]), 4)

        return {
            "base_value": round(base_value, 4),
            "feature_values": feature_shap,
        }
    except Exception as e:
        print(f"  WARNING: SHAP computation failed: {e}")
        return None


def compute_global_importance(model, X_scaled_full, feature_cols):
    """Compute global feature importance using mean |SHAP| on the full dataset."""
    try:
        if isinstance(model, RandomForestRegressor):
            explainer = shap.TreeExplainer(model)
        elif isinstance(model, Ridge):
            explainer = shap.LinearExplainer(model, X_scaled_full)
        else:
            return None

        shap_values = explainer.shap_values(X_scaled_full)
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        importance = {}
        for i, col in enumerate(feature_cols):
            importance[col] = round(float(mean_abs_shap[i]), 4)

        # Sort by importance descending
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return importance
    except Exception as e:
        print(f"  WARNING: Global importance computation failed: {e}")
        return None


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
    model_metadata = {}
    targets = {
        '1d': 'target_aqi_next_1d',
        '2d': 'target_aqi_next_2d',
        '3d': 'target_aqi_next_3d'
    }
    
    hw_model_objects = {}
    for key, target in targets.items():
        hw_model = get_latest_model(mr, f"aqi_model_{target}")
        print(f"Using model for {target} (version: {hw_model.version})")
        model_dir = hw_model.download()
        models[key] = joblib.load(os.path.join(model_dir, "best_model.pkl"))
        hw_model_objects[key] = hw_model
        model_metadata[key] = get_model_metadata(models[key], hw_model)
        
    # 3. Prepare features for prediction
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
    
    # 4. Prepare background data for SHAP (use full dataset)
    print("Preparing data for SHAP analysis...")
    df_clean = df.dropna(subset=['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d'])
    full_numeric = df_clean.select_dtypes(include=[np.number])
    for col in feature_cols:
        if col not in full_numeric.columns:
            full_numeric = full_numeric.copy()
            full_numeric[col] = 0
    X_full = full_numeric[feature_cols]
    X_full_scaled = scaler.transform(X_full)
    
    # Limit background data to avoid slow SHAP computation
    max_background = min(200, len(X_full_scaled))
    X_background = X_full_scaled[:max_background]
    
    # 5. Predict and compute SHAP
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
    
    # 6. Compute SHAP values for each model
    print("Computing SHAP values...")
    shap_data = {}
    for key in ['1d', '2d', '3d']:
        print(f"  Computing SHAP for {key} model...")
        shap_result = compute_shap_values(
            models[key], X_scaled, feature_cols, X_background=X_background
        )
        if shap_result:
            shap_data[key] = shap_result
    
    # 7. Compute global feature importance using the 1d model (primary)
    print("Computing global feature importance...")
    global_importance = compute_global_importance(
        models['1d'], X_background, feature_cols
    )
    
    # 8. Compute evaluation metrics on a test split
    print("Computing evaluation metrics...")
    eval_metrics = {}
    try:
        y_targets = {}
        for key, target in targets.items():
            if target in full_numeric.columns:
                y_targets[key] = full_numeric[target].values
        
        for key, target in targets.items():
            if key in y_targets:
                _, X_test, _, y_test = train_test_split(
                    X_full_scaled, y_targets[key], test_size=0.2, shuffle=False
                )
                preds = models[key].predict(X_test)
                eval_metrics[key] = {
                    "r2": round(float(r2_score(y_test, preds)), 4),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds))), 4),
                    "mae": round(float(mean_absolute_error(y_test, preds)), 4),
                    "test_samples": len(y_test),
                }
                print(f"  {key}: R²={eval_metrics[key]['r2']}, RMSE={eval_metrics[key]['rmse']}, MAE={eval_metrics[key]['mae']}")
    except Exception as e:
        print(f"  WARNING: Metric computation failed: {e}")
    
    # 9. Build output JSON
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
            },
            "feature_columns": feature_cols,
            "model_info": model_metadata,
            "evaluation_metrics": eval_metrics,
            "shap_values": shap_data,
            "global_feature_importance": global_importance,
        }
    }
    
    # 10. Save to JSON
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'predictions.json')
    
    with open(out_path, 'w') as f:
        json.dump(preds, f, indent=4, default=str)
        
    print(f"Successfully saved predictions to {out_path}")


if __name__ == "__main__":
    generate_predictions()
