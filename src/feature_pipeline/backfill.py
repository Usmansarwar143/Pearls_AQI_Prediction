import os
import pandas as pd
import hopsworks
from fetch_api import get_data
from compute_features import engineer_features
from dotenv import load_dotenv

load_dotenv()

def backfill_historical_data(days_back=365):
    print(f"Starting backfill process for the last {days_back} days...")
    
    # 1. Fetch Data
    p_df, w_df = get_data(days_back=days_back)
    
    # 2. Engineer Features
    print("Engineering features...")
    features_df = engineer_features(p_df, w_df)
    
    print(f"Feature engineering complete. Shape: {features_df.shape}")
    
    # 3. Save to Hopsworks Feature Store
    print("Connecting to Hopsworks...")
    project = hopsworks.login(
        project=os.getenv("HOPSWORKS_PROJECT_NAME"),
        api_key_value=os.getenv("HOPSWORKS_API_KEY")
    )
    fs = project.get_feature_store()
    
    fg_version = int(os.getenv("HOPSWORKS_FEATURE_GROUP_VERSION", 3))
    # Create Feature Group
    print(f"Creating/Getting Feature Group 'aqi_features' version {fg_version}...")
    aqi_fg = fs.get_or_create_feature_group(
        name="aqi_features",
        version=fg_version,
        primary_key=["date"],
        description="Hourly Air Quality Index dataset with weather features",
        online_enabled=False,
        time_travel_format="HUDI"
    )
    
    # Insert data (wait_for_job=True ensures backfill completes before training begins)
    print("Inserting data into Hopsworks Feature Group...")
    try:
        aqi_fg.insert(features_df, write_options={"wait_for_job": True})
        print("Backfill process successfully completed and pushed to Hopsworks!")
    except Exception as e:
        print("\n" + "="*80)
        print(f"HOPSWORKS MATERIALIZATION JOB FAILED for Feature Group version {fg_version}!")
        print("Attempting to retrieve Spark execution logs from Hopsworks...")
        print("="*80)
        try:
            jobs_api = project.get_jobs_api()
            job_name = f"aqi_features_{fg_version}_offline_fg_materialization"
            job = jobs_api.get_job(job_name)
            executions = job.get_executions()
            if executions:
                out_path, err_path = executions[0].download_logs()
                print(f"\n--- [HOPSWORKS STDERR: {job_name}] ---")
                with open(err_path, "r", errors="ignore") as f_err:
                    err_lines = f_err.read()
                    print(err_lines[-3000:] if len(err_lines) > 3000 else err_lines)
                print(f"\n--- [HOPSWORKS STDOUT: {job_name}] ---")
                with open(out_path, "r", errors="ignore") as f_out:
                    out_lines = f_out.read()
                    print(out_lines[-3000:] if len(out_lines) > 3000 else out_lines)
        except Exception as log_err:
            print(f"Could not download job logs: {log_err}")
        print("="*80 + "\n")
        raise e

if __name__ == "__main__":
    backfill_historical_data(days_back=365)
