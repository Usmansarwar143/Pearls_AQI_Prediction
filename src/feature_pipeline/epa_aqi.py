"""
US EPA Air Quality Index (AQI) Calculator

Converts raw pollutant concentrations (µg/m³) from the OpenWeather API
into the standard US EPA 0–500 AQI scale using official breakpoint tables.

Reference: https://www.airnow.gov/sites/default/files/2020-05/aqi-technical-assistance-document-sept2018.pdf
"""


def _aqi_from_breakpoints(concentration, breakpoints):
    """
    Calculate sub-AQI for a single pollutant using EPA linear interpolation.
    
    Formula: AQI = ((AQI_hi - AQI_lo) / (BP_hi - BP_lo)) * (C - BP_lo) + AQI_lo
    
    Args:
        concentration: Truncated pollutant concentration
        breakpoints: List of (BP_lo, BP_hi, AQI_lo, AQI_hi) tuples
    
    Returns:
        Calculated AQI value, or None if concentration is out of range
    """
    for bp_lo, bp_hi, aqi_lo, aqi_hi in breakpoints:
        if bp_lo <= concentration <= bp_hi:
            aqi = ((aqi_hi - aqi_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + aqi_lo
            return round(aqi)
    return None


# --- EPA Breakpoint Tables ---
# Each entry: (BP_lo, BP_hi, AQI_lo, AQI_hi)

# PM2.5 (µg/m³, 24-hour average — used as instantaneous approximation)
PM25_BREAKPOINTS = [
    (0.0,   12.0,   0,   50),
    (12.1,  35.4,   51,  100),
    (35.5,  55.4,   101, 150),
    (55.5,  150.4,  151, 200),
    (150.5, 250.4,  201, 300),
    (250.5, 350.4,  301, 400),
    (350.5, 500.4,  401, 500),
]

# PM10 (µg/m³, 24-hour average)
PM10_BREAKPOINTS = [
    (0,   54,   0,   50),
    (55,  154,  51,  100),
    (155, 254,  101, 150),
    (255, 354,  151, 200),
    (355, 424,  201, 300),
    (425, 504,  301, 400),
    (505, 604,  401, 500),
]

# O3 — Ozone (µg/m³). EPA uses ppm, so we convert:
# 1 ppm O3 = 1960 µg/m³ at STP. Breakpoints below are in µg/m³.
# Based on 8-hour average thresholds converted from ppm.
O3_BREAKPOINTS = [
    (0,     107,   0,   50),    # 0–0.054 ppm
    (108,   139,   51,  100),   # 0.055–0.070 ppm
    (140,   167,   101, 150),   # 0.071–0.085 ppm
    (168,   207,   151, 200),   # 0.086–0.105 ppm
    (208,   393,   201, 300),   # 0.106–0.200 ppm
    # Above 0.2 ppm O3, EPA uses 1-hour values only
]

# NO2 (µg/m³, 1-hour average)
# EPA uses ppb; 1 ppb NO2 = 1.88 µg/m³
NO2_BREAKPOINTS = [
    (0,     100,   0,   50),    # 0–53 ppb
    (101,   188,   51,  100),   # 54–100 ppb
    (189,   677,   101, 150),   # 101–360 ppb
    (678,   1221,  151, 200),   # 361–649 ppb
    (1222,  2349,  201, 300),   # 650–1249 ppb
    (2350,  3102,  301, 400),   # 1250–1649 ppb
    (3103,  3852,  401, 500),   # 1650–2049 ppb
]

# SO2 (µg/m³, 1-hour average)
# EPA uses ppb; 1 ppb SO2 = 2.62 µg/m³
SO2_BREAKPOINTS = [
    (0,     92,    0,   50),    # 0–35 ppb
    (93,    197,   51,  100),   # 36–75 ppb
    (198,   487,   101, 150),   # 76–185 ppb
    (488,   798,   151, 200),   # 186–304 ppb
    (799,   1583,  201, 300),   # 305–604 ppb
    (1584,  2107,  301, 400),   # 605–804 ppb
    (2108,  2630,  401, 500),   # 805–1004 ppb
]

# CO — Carbon Monoxide (µg/m³, 8-hour average)
# EPA uses ppm; 1 ppm CO = 1145 µg/m³
CO_BREAKPOINTS = [
    (0,      5145,   0,   50),   # 0–4.4 ppm
    (5146,   10345,  51,  100),  # 4.5–9.4 ppm
    (10346,  13945,  101, 150),  # 9.5–12.4 ppm
    (13946,  17545,  151, 200),  # 12.5–15.4 ppm
    (17546,  34645,  201, 300),  # 15.5–30.4 ppm
    (34646,  46345,  301, 400),  # 30.5–40.4 ppm
    (46346,  57645,  401, 500),  # 40.5–50.4 ppm
]


def calculate_epa_aqi(pm2_5=None, pm10=None, o3=None, no2=None, so2=None, co=None):
    """
    Calculate the overall US EPA AQI from pollutant concentrations.
    
    The overall AQI is the MAXIMUM of all individual pollutant sub-AQIs.
    All concentrations should be in µg/m³ (as returned by OpenWeather API).
    
    Args:
        pm2_5: PM2.5 concentration (µg/m³)
        pm10:  PM10 concentration (µg/m³)
        o3:    Ozone concentration (µg/m³)
        no2:   Nitrogen Dioxide concentration (µg/m³)
        so2:   Sulfur Dioxide concentration (µg/m³)
        co:    Carbon Monoxide concentration (µg/m³)
    
    Returns:
        int: The overall EPA AQI value (0–500 scale)
    """
    sub_aqis = []
    
    pollutant_map = [
        (pm2_5, PM25_BREAKPOINTS),
        (pm10,  PM10_BREAKPOINTS),
        (o3,    O3_BREAKPOINTS),
        (no2,   NO2_BREAKPOINTS),
        (so2,   SO2_BREAKPOINTS),
        (co,    CO_BREAKPOINTS),
    ]
    
    for concentration, breakpoints in pollutant_map:
        if concentration is not None and concentration >= 0:
            aqi = _aqi_from_breakpoints(concentration, breakpoints)
            if aqi is not None:
                sub_aqis.append(aqi)
    
    if not sub_aqis:
        return 0
    
    return max(sub_aqis)
