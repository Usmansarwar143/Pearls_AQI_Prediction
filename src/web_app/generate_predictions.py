import os
import json
import hopsworks
import joblib
import pandas as pd
import numpy as np
import shap
from datetime import datetime, timezone
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
            "criterion": model.criterion,
            "n_features_in": int(model.n_features_in_) if hasattr(model, 'n_features_in_') else None,
        }
    elif isinstance(model, Ridge):
        params = {
            "alpha": model.alpha,
            "solver": model.solver,
            "fit_intercept": model.fit_intercept,
            "max_iter": model.max_iter,
            "n_features_in": int(model.n_features_in_) if hasattr(model, 'n_features_in_') else None,
        }

    return {
        "model_type": model_type,
        "version": hw_model.version,
        "description": hw_model.description if hasattr(hw_model, 'description') else "",
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
            explainer = shap.KernelExplainer(model.predict, X_scaled[:1])
            shap_values = explainer.shap_values(X_scaled)
            base_value = float(explainer.expected_value)

        if len(shap_values.shape) == 1:
            sv = shap_values
        else:
            sv = shap_values[0]

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

        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return importance
    except Exception as e:
        print(f"  WARNING: Global importance computation failed: {e}")
        return None


def compute_dataset_statistics(df, feature_cols):
    """Compute comprehensive dataset statistics for dashboard display."""
    stats = {
        "total_rows": int(len(df)),
        "date_range": {
            "start": str(df['date'].min()),
            "end": str(df['date'].max()),
        },
        "aqi_statistics": {
            "mean": round(float(df['aqi'].mean()), 2),
            "median": round(float(df['aqi'].median()), 2),
            "std": round(float(df['aqi'].std()), 2),
            "min": round(float(df['aqi'].min()), 2),
            "max": round(float(df['aqi'].max()), 2),
            "q25": round(float(df['aqi'].quantile(0.25)), 2),
            "q75": round(float(df['aqi'].quantile(0.75)), 2),
        },
        "feature_statistics": {},
        "missing_values": {},
        "aqi_distribution": {},
    }

    # Feature-level statistics
    numeric_df = df.select_dtypes(include=[np.number])
    for col in feature_cols:
        if col in numeric_df.columns:
            stats["feature_statistics"][col] = {
                "mean": round(float(numeric_df[col].mean()), 4),
                "std": round(float(numeric_df[col].std()), 4),
                "min": round(float(numeric_df[col].min()), 4),
                "max": round(float(numeric_df[col].max()), 4),
            }

    # Missing value counts
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing > 0:
            stats["missing_values"][col] = missing

    # AQI category distribution
    aqi_cats = {
        "Good (0-50)": int(((df['aqi'] >= 0) & (df['aqi'] <= 50)).sum()),
        "Moderate (51-100)": int(((df['aqi'] > 50) & (df['aqi'] <= 100)).sum()),
        "Unhealthy for Sensitive (101-150)": int(((df['aqi'] > 100) & (df['aqi'] <= 150)).sum()),
        "Unhealthy (151-200)": int(((df['aqi'] > 150) & (df['aqi'] <= 200)).sum()),
        "Very Unhealthy (201-300)": int(((df['aqi'] > 200) & (df['aqi'] <= 300)).sum()),
        "Hazardous (301+)": int((df['aqi'] > 300).sum()),
    }
    stats["aqi_distribution"] = aqi_cats

    return stats


def compute_correlation_matrix(df, feature_cols):
    """Compute correlation of features with AQI target."""
    try:
        cols_to_use = [c for c in feature_cols if c in df.columns] + ['aqi']
        corr = df[cols_to_use].corr()['aqi'].drop('aqi').to_dict()
        return {k: round(float(v), 4) for k, v in sorted(corr.items(), key=lambda x: abs(x[1]), reverse=True)}
    except Exception:
        return None


def compute_residual_analysis(models, X_test_scaled, y_test_dict):
    """Compute residuals for error distribution analysis."""
    residuals = {}
    for key, model in models.items():
        if key in y_test_dict:
            preds = model.predict(X_test_scaled)
            res = y_test_dict[key] - preds
            residuals[key] = {
                "mean_residual": round(float(res.mean()), 4),
                "std_residual": round(float(res.std()), 4),
                "max_overpredict": round(float(res.min()), 4),
                "max_underpredict": round(float(res.max()), 4),
                "residual_histogram": {
                    "bins": list(np.round(np.linspace(float(res.min()), float(res.max()), 11), 2)),
                    "counts": [int(c) for c in np.histogram(res, bins=10)[0]],
                },
            }
    return residuals


def compute_prediction_intervals(models, X_scaled, feature_cols):
    """Compute prediction confidence using tree variance (RF only)."""
    intervals = {}
    for key, model in models.items():
        if isinstance(model, RandomForestRegressor):
            tree_preds = np.array([tree.predict(X_scaled) for tree in model.estimators_])
            mean_pred = float(tree_preds.mean())
            std_pred = float(tree_preds.std())
            intervals[key] = {
                "mean": round(mean_pred, 2),
                "std": round(std_pred, 2),
                "ci_lower": round(max(0, mean_pred - 1.96 * std_pred), 2),
                "ci_upper": round(min(500, mean_pred + 1.96 * std_pred), 2),
                "n_trees": model.n_estimators,
            }
    return intervals


def get_latest_feature_values(latest_row, feature_cols):
    """Extract the actual feature values for the latest row for display."""
    values = {}
    numeric = latest_row.select_dtypes(include=[np.number])
    for col in feature_cols:
        if col in numeric.columns:
            values[col] = round(float(numeric[col].values[0]), 4)
    return values


def generate_predictions():
    generation_start = datetime.now(timezone.utc)
    
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
    
    # Retry mechanism for fetching data from Hopsworks
    import time
    max_retries = 3
    df = None
    for attempt in range(max_retries):
        try:
            print(f"Fetching data (Attempt {attempt + 1}/{max_retries})...")
            df = query.read(read_options={"use_hive": True})
            break
        except Exception as e:
            print(f"Error fetching data on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Failed to fetch data after multiple attempts.")
                raise e
    
    df = df.sort_values(by="date", ascending=False)
    latest_row = df.iloc[0:1]
    
    # Extended history for trend analysis (30 data points)
    recent_history = df.head(30)[['date', 'aqi']].sort_values(by="date", ascending=True)
    recent_history['date'] = recent_history['date'].astype(str)
    history_data = recent_history.to_dict(orient="records")
    
    # Also keep short 7-day history
    short_history = df.head(7)[['date', 'aqi']].sort_values(by="date", ascending=True)
    short_history['date'] = short_history['date'].astype(str)
    short_history_data = short_history.to_dict(orient="records")
    
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
    
    for col in feature_cols:
        if col not in numeric_df.columns:
            print(f"  WARNING: Feature '{col}' expected by scaler but missing from data. Filling with 0.")
            numeric_df = numeric_df.copy()
            numeric_df[col] = 0
    
    X_latest = numeric_df[feature_cols]
    X_scaled = scaler.transform(X_latest)
    
    # 4. Prepare background data for SHAP
    print("Preparing data for SHAP analysis...")
    df_clean = df.dropna(subset=['target_aqi_next_1d', 'target_aqi_next_2d', 'target_aqi_next_3d'])
    full_numeric = df_clean.select_dtypes(include=[np.number])
    for col in feature_cols:
        if col not in full_numeric.columns:
            full_numeric = full_numeric.copy()
            full_numeric[col] = 0
    X_full = full_numeric[feature_cols]
    X_full_scaled = scaler.transform(X_full)
    
    max_background = min(200, len(X_full_scaled))
    X_background = X_full_scaled[:max_background]
    
    # 5. Predict
    raw_1d = float(models['1d'].predict(X_scaled)[0])
    raw_2d = float(models['2d'].predict(X_scaled)[0])
    raw_3d = float(models['3d'].predict(X_scaled)[0])
    
    print(f"Raw model predictions: 1d={raw_1d:.2f}, 2d={raw_2d:.2f}, 3d={raw_3d:.2f}")

    if any(p < 10 for p in [raw_1d, raw_2d, raw_3d]) and float(latest_row['aqi'].values[0]) > 20:
        print("WARNING: Model predictions are < 10 while current AQI is on US EPA scale.")
        print("Please trigger the 'retrain-pipeline' GitHub Action.")

    pred_1d = max(0, min(500, round(raw_1d)))
    pred_2d = max(0, min(500, round(raw_2d)))
    pred_3d = max(0, min(500, round(raw_3d)))
    
    # 6. SHAP values per model
    print("Computing SHAP values...")
    shap_data = {}
    for key in ['1d', '2d', '3d']:
        print(f"  Computing SHAP for {key} model...")
        shap_result = compute_shap_values(
            models[key], X_scaled, feature_cols, X_background=X_background
        )
        if shap_result:
            shap_data[key] = shap_result
    
    # 7. Global feature importance
    print("Computing global feature importance...")
    global_importance = compute_global_importance(
        models['1d'], X_background, feature_cols
    )
    
    # 8. Evaluation metrics
    print("Computing evaluation metrics...")
    eval_metrics = {}
    y_test_dict = {}
    X_test_scaled = None
    try:
        y_targets = {}
        for key, target in targets.items():
            if target in full_numeric.columns:
                y_targets[key] = full_numeric[target].values
        
        for key, target in targets.items():
            if key in y_targets:
                X_train, X_test, y_train, y_test = train_test_split(
                    X_full_scaled, y_targets[key], test_size=0.2, shuffle=False
                )
                X_test_scaled = X_test
                y_test_dict[key] = y_test
                preds_eval = models[key].predict(X_test)
                
                # Actual vs Predicted samples (last 20)
                actual_vs_pred = []
                sample_count = min(20, len(y_test))
                for i in range(sample_count):
                    actual_vs_pred.append({
                        "actual": round(float(y_test[-(sample_count - i)]), 2),
                        "predicted": round(float(preds_eval[-(sample_count - i)]), 2),
                    })
                
                eval_metrics[key] = {
                    "r2": round(float(r2_score(y_test, preds_eval)), 4),
                    "rmse": round(float(np.sqrt(mean_squared_error(y_test, preds_eval))), 4),
                    "mae": round(float(mean_absolute_error(y_test, preds_eval)), 4),
                    "test_samples": len(y_test),
                    "train_samples": len(y_train),
                    "actual_vs_predicted": actual_vs_pred,
                }
                print(f"  {key}: R²={eval_metrics[key]['r2']}, RMSE={eval_metrics[key]['rmse']}, MAE={eval_metrics[key]['mae']}")
    except Exception as e:
        print(f"  WARNING: Metric computation failed: {e}")
    
    # 9. Dataset statistics
    print("Computing dataset statistics...")
    dataset_stats = compute_dataset_statistics(df, feature_cols)
    
    # 10. Feature-AQI correlations
    print("Computing feature correlations...")
    correlations = compute_correlation_matrix(df_clean, feature_cols)
    
    # 11. Residual analysis
    print("Computing residual analysis...")
    residuals = {}
    if X_test_scaled is not None and y_test_dict:
        residuals = compute_residual_analysis(models, X_test_scaled, y_test_dict)
    
    # 12. Prediction confidence intervals (RF only)
    print("Computing prediction intervals...")
    prediction_intervals = compute_prediction_intervals(models, X_scaled, feature_cols)
    
    # 13. Latest feature values
    latest_feature_values = get_latest_feature_values(latest_row, feature_cols)
    
    # 14. Scaler parameters
    scaler_info = {
        "type": "StandardScaler",
        "version": hw_scaler.version,
        "n_features": len(feature_cols),
        "means": {col: round(float(scaler.mean_[i]), 4) for i, col in enumerate(feature_cols)} if hasattr(scaler, 'mean_') else {},
        "scales": {col: round(float(scaler.scale_[i]), 4) for i, col in enumerate(feature_cols)} if hasattr(scaler, 'scale_') else {},
    }
    
    generation_end = datetime.now(timezone.utc)
    
    # 15. Build comprehensive output JSON
    output = {
        "status": "success",
        "generated_at": generation_end.isoformat(),
        "generation_time_seconds": round((generation_end - generation_start).total_seconds(), 2),
        "data": {
            # Core predictions
            "current_aqi": float(latest_row['aqi'].values[0]),
            "current_date": str(latest_row['date'].values[0]),
            "history": short_history_data,
            "extended_history": history_data,
            "predictions": {
                "1_day": pred_1d,
                "2_days": pred_2d,
                "3_days": pred_3d,
                "raw_1_day": round(raw_1d, 4),
                "raw_2_days": round(raw_2d, 4),
                "raw_3_days": round(raw_3d, 4),
            },
            "prediction_intervals": prediction_intervals,
            
            # Feature info
            "feature_columns": feature_cols,
            "latest_feature_values": latest_feature_values,
            "feature_correlations": correlations,
            "scaler_info": scaler_info,
            
            # Model details
            "model_info": model_metadata,
            "evaluation_metrics": eval_metrics,
            "residual_analysis": residuals,
            
            # SHAP explainability
            "shap_values": shap_data,
            "global_feature_importance": global_importance,
            
            # Dataset overview
            "dataset_statistics": dataset_stats,
            
            # Pipeline info
            "pipeline_info": {
                "feature_group": "aqi_features",
                "feature_group_version": fg_version,
                "scaler_version": hw_scaler.version,
                "data_source": {
                    "pollution": "OpenWeather Air Pollution API",
                    "weather": "Open-Meteo Archive + Forecast API",
                },
                "target_city": "Sadiqabad, Punjab, Pakistan",
                "aqi_standard": "US EPA (0-500 scale)",
                "feature_engineering": [
                    "hour — Hour of day (0-23)",
                    "day_of_week — Day of week (0=Monday, 6=Sunday)",
                    "month — Month of year (1-12)",
                    "aqi_change_rate — Hourly AQI change (difference from previous reading)",
                    "aqi_rolling_24h — 24-hour rolling average AQI",
                ],
                "pollutants_tracked": [
                    "PM2.5 — Fine particulate matter",
                    "PM10 — Coarse particulate matter",
                    "O3 — Ozone",
                    "NO2 — Nitrogen Dioxide",
                    "SO2 — Sulfur Dioxide",
                    "CO — Carbon Monoxide",
                    "NO — Nitric Oxide",
                    "NH3 — Ammonia",
                ],
                "weather_features": [
                    "temperature_2m — Temperature at 2m height (°C)",
                    "relative_humidity_2m — Relative humidity (%)",
                    "wind_speed_10m — Wind speed at 10m height (km/h)",
                ],
            },
        }
    }
    
    # ---------------------------------------------------------
    # GENERATE LLM INSIGHTS VIA HUGGINGFACE
    # ---------------------------------------------------------
    import requests
    hf_api_key = os.getenv("HF_API_KEY")
    llm_insights = ""
    
    if hf_api_key:
        print("Calling HuggingFace LLM for AI Insights...")
        try:
            prompt = f"[INST] Act as an expert meteorologist analyzing air quality for Sadiqabad, Pakistan. The current AQI is {current_aqi:.1f}. The 1-day forecast is {preds['1_day']:.1f}, 2-day is {preds['2_days']:.1f}, 3-day is {preds['3_days']:.1f}. Provide a concise, 2-3 sentence plain-English health advisory and forecast summary. Do not use markdown or bullet points. [/INST]"
            headers = {"Authorization": f"Bearer {hf_api_key}", "Content-Type": "application/json"}
            payload = {
                "inputs": prompt,
                "parameters": {"max_new_tokens": 150, "temperature": 0.7, "return_full_text": False}
            }
            response = requests.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3", 
                headers=headers, 
                json=payload, 
                timeout=20
            )
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list) and len(res_json) > 0 and 'generated_text' in res_json[0]:
                    llm_insights = res_json[0]['generated_text'].strip()
                    print("LLM Insights generated successfully.")
                else:
                    print(f"Unexpected LLM response format: {res_json}")
            else:
                print(f"LLM API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Failed to generate LLM insights: {e}")
            
    output["data"]["llm_insights"] = llm_insights
    
    # Save to JSON
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, 'predictions.json')
    
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=4, default=str)
        
    print(f"Successfully saved predictions to {out_path}")


if __name__ == "__main__":
    generate_predictions()
