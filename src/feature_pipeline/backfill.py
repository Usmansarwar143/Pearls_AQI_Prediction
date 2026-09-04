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
    
    # Create Feature Group
    print("Creating/Getting Feature Group 'aqi_features'...")
    aqi_fg = fs.get_or_create_feature_group(
        name="aqi_features",
        version=2,
        primary_key=["date"],
        description="Hourly Air Quality Index dataset with weather features",
        online_enabled=False,
        time_travel_format="HUDI"
    )
    
    # Insert data (wait_for_job=True ensures backfill completes before training begins)
    print("Inserting data into Hopsworks Feature Group...")
    aqi_fg.insert(features_df, write_options={"wait_for_job": True})
    
    print("Backfill process successfully completed and pushed to Hopsworks!")

if __name__ == "__main__":
    backfill_historical_data(days_back=365)
