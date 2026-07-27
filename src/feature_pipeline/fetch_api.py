import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = "SadiqAbad"
COUNTRY = "PK"

def get_coordinates(city=CITY, country=COUNTRY):
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},{country}&limit=1&appid={OPENWEATHER_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"Could not find coordinates for {city}, {country}")
    return data[0]['lat'], data[0]['lon']

def fetch_historical_pollution(lat, lon, start_ts, end_ts):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={start_ts}&end={end_ts}&appid={OPENWEATHER_API_KEY}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    records = []
    for item in data.get('list', []):
        records.append({
            'timestamp': item['dt'],
            'aqi': item['main']['aqi'],
            'co': item['components']['co'],
            'no': item['components']['no'],
            'no2': item['components']['no2'],
            'o3': item['components']['o3'],
            'so2': item['components']['so2'],
            'pm2_5': item['components']['pm2_5'],
            'pm10': item['components']['pm10'],
            'nh3': item['components']['nh3'],
        })
        
    df = pd.DataFrame(records)
    if not df.empty:
        df['date'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

def fetch_historical_weather(lat, lon, start_date_str, end_date_str):
    # Open-Meteo provides a free historical weather API without a key
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date_str}&end_date={end_date_str}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    if 'hourly' in data:
        df = pd.DataFrame({
            'date': pd.to_datetime(data['hourly']['time']),
            'temperature_2m': data['hourly']['temperature_2m'],
            'relative_humidity_2m': data['hourly']['relative_humidity_2m'],
            'wind_speed_10m': data['hourly']['wind_speed_10m']
        })
        return df
    return pd.DataFrame()

def get_data(days_back=730):
    lat, lon = get_coordinates()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    
    print("Fetching historical pollution data...")
    pollution_df = fetch_historical_pollution(lat, lon, start_ts, end_ts)
    
    print("Fetching historical weather data...")
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    weather_df = fetch_historical_weather(lat, lon, start_date_str, end_date_str)
    
    return pollution_df, weather_df

if __name__ == "__main__":
    p_df, w_df = get_data(days_back=7)
    print("Pollution data shape:", p_df.shape)
    print("Weather data shape:", w_df.shape)
