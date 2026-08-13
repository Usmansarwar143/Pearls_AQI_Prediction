import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
from epa_aqi import calculate_epa_aqi

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
        components = item['components']
        
        # Calculate US EPA AQI (0-500 scale) from pollutant concentrations
        # instead of using OpenWeather's 1-5 European scale
        epa_aqi = calculate_epa_aqi(
            pm2_5=components.get('pm2_5'),
            pm10=components.get('pm10'),
            o3=components.get('o3'),
            no2=components.get('no2'),
            so2=components.get('so2'),
            co=components.get('co'),
        )
        
        records.append({
            'timestamp': item['dt'],
            'aqi': epa_aqi,
            'co': components['co'],
            'no': components['no'],
            'no2': components['no2'],
            'o3': components['o3'],
            'so2': components['so2'],
            'pm2_5': components['pm2_5'],
            'pm10': components['pm10'],
            'nh3': components['nh3'],
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

def fetch_recent_weather(lat, lon, past_days=7):
    """Fetch recent weather using Open-Meteo Forecast API.
    
    The Archive API has a ~5-7 day lag, so recent days are missing.
    The Forecast API covers the last few days + future forecast with no lag.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&past_days={past_days}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
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
    
    print("Fetching historical weather data (Archive API)...")
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    weather_df = fetch_historical_weather(lat, lon, start_date_str, end_date_str)
    
    # Supplement with recent weather from the Forecast API to cover
    # the ~5-7 day lag in the Archive API
    print("Fetching recent weather data (Forecast API)...")
    recent_weather_df = fetch_recent_weather(lat, lon, past_days=min(days_back, 7))
    
    if not recent_weather_df.empty:
        weather_df = pd.concat([weather_df, recent_weather_df], ignore_index=True)
        weather_df = weather_df.drop_duplicates(subset=['date'], keep='last')
        weather_df = weather_df.sort_values('date').reset_index(drop=True)
        print(f"Combined weather data range: {weather_df['date'].min()} to {weather_df['date'].max()}")
    
    return pollution_df, weather_df

if __name__ == "__main__":
    p_df, w_df = get_data(days_back=7)
    print("Pollution data shape:", p_df.shape)
    print("Weather data shape:", w_df.shape)
