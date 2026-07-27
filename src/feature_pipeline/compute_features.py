import pandas as pd

def engineer_features(pollution_df, weather_df):
    """
    Merges pollution and weather dataframes and computes time-based and derived features.
    """
    if pollution_df.empty or weather_df.empty:
        raise ValueError("Dataframes cannot be empty")
        
    # Ensure date columns are datetime
    pollution_df['date'] = pd.to_datetime(pollution_df['date'])
    weather_df['date'] = pd.to_datetime(weather_df['date'])
    
    # Round pollution date to nearest hour to match weather data
    pollution_df['date'] = pollution_df['date'].dt.floor('h')
    weather_df['date'] = weather_df['date'].dt.floor('h')
    
    # Merge on date, drop duplicates in case of API overlaps
    pollution_df = pollution_df.drop_duplicates(subset=['date'])
    weather_df = weather_df.drop_duplicates(subset=['date'])
    
    df = pd.merge(pollution_df, weather_df, on='date', how='inner')
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # Time-based features
    df['hour'] = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    
    # Derived features
    # AQI change rate (difference from previous hour)
    df['aqi_change_rate'] = df['aqi'].diff().fillna(0)
    
    # Rolling mean of AQI (24 hours)
    df['aqi_rolling_24h'] = df['aqi'].rolling(window=24, min_periods=1).mean()
    
    # Targets: Predict AQI 24h, 48h, 72h into the future
    # 24 rows = 1 day since data is hourly
    df['target_aqi_next_1d'] = df['aqi'].shift(-24)
    df['target_aqi_next_2d'] = df['aqi'].shift(-48)
    df['target_aqi_next_3d'] = df['aqi'].shift(-72)
    
    # Note: Shifting will introduce NaNs at the tail of the dataframe. 
    # We don't drop them here because we need the latest features for inference (web app).
    # The training pipeline will drop NaNs before fitting the model.
    
    return df
