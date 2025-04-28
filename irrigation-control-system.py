"""
Automated Irrigation Control System

This program:
1. Reads sensor data (soil moisture, temperature, humidity, etc.)
2. Determines if irrigation is required based on soil moisture thresholds
3. If needed, calculates evapotranspiration (ET) using Penman-Monteith method
4. Determines water volume requirements based on crop type and growth stage
5. Calculates pump operation time


"""

import pandas as pd
import numpy as np
import math
import datetime
import requests
from typing import Dict, Tuple, Optional, List

# Constants
FIELD_AREA = 1000  # m²
MOTOR_FLOW_RATE = 1000  # L/min
IRRIGATION_EFFICIENCY = 0.85  # 85% efficiency

# Soil moisture thresholds (example values, should be adjusted based on soil type and crop)
MOISTURE_THRESHOLD_MIN = 40  # %
MOISTURE_THRESHOLD_MAX = 60  # %

# Weekly Kc values (crop coefficient) for a sample crop (e.g., sugarcane)
# In a real application, this would be loaded from a CSV or API
KC_VALUES = {
    1: 0.3,  # Week 1 after planting
    2: 0.4,  # Week 2
    3: 0.5,  # Week 3
    4: 0.7,  # Week 4
    5: 0.8,  # Week 5
    6: 0.9,  # Week 6
    7: 1.0,  # Week 7
    8: 1.1,  # Week 8
    9: 1.1,  # Week 9
    10: 1.0,  # Week 10
    11: 0.9,  # Week 11
    12: 0.8,  # Week 12
}

def read_sensor_data() -> Dict:
    """
    Read sensor data from the system.
    In a real application, this would connect to actual sensors or an API.
    
    Returns:
        Dictionary containing sensor readings
    """
    # For demonstration, we're using sample data
    # In a real application, this would connect to the actual sensors
    return {
        'TC_min': 18.5,       # Min temperature (°C)
        'HUM_min': 40,        # Min humidity (%)
        'SOILTC_min': 16.2,   # Min soil temperature (°C)
        'SOIL_B_min': 35,     # Min soil moisture sensor B (%)
        'SOIL_C_min': 33,     # Min soil moisture sensor C (%)
        'PRES_min': 1009.2,   # Min atmospheric pressure (hPa)
        
        'TC_max': 28.3,       # Max temperature (°C)
        'HUM_max': 65,        # Max humidity (%)
        'SOILTC_max': 22.1,   # Max soil temperature (°C)
        'ANE_max': 12.5,      # Max wind speed (km/h)
        'PLV2_max': 0,        # Max rainfall (mm)
        'SOIL_B_max': 42,     # Max soil moisture sensor B (%)
        'SOIL_C_max': 40,     # Max soil moisture sensor C (%)
        'LDR_max': 975,       # Max light sensor reading
        'LW_max': 875,        # Max light intensity
        'LUX_max': 65000,     # Max illuminance (lux)
        'PRES_max': 1014.6,   # Max atmospheric pressure (hPa)
    }

def get_crop_week() -> int:
    """
    Determine the current week of crop growth.
    In a real application, this would be based on planting date.
    
    Returns:
        Current week number
    """
    # For demonstration, assume we are in week 6 of growth
    # In a real application, this would calculate based on planting date
    planting_date = datetime.datetime(2025, 3, 15)  # Example planting date
    current_date = datetime.datetime.now()
    days_difference = (current_date - planting_date).days
    current_week = (days_difference // 7) + 1
    
    # Limit to the weeks we have data for
    return min(current_week, max(KC_VALUES.keys()))

def is_irrigation_required(sensor_data: Dict) -> bool:
    """
    Determine if irrigation is required based on soil moisture sensors.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        Boolean indicating if irrigation is required
    """
    # Use the average of both soil moisture sensors (B and C)
    avg_soil_moisture_min = (sensor_data['SOIL_B_min'] + sensor_data['SOIL_C_min']) / 2
    
    print(f"Average minimum soil moisture: {avg_soil_moisture_min:.1f}%")
    print(f"Moisture threshold: {MOISTURE_THRESHOLD_MIN}%")
    
    # If average soil moisture is below threshold, irrigation is required
    if avg_soil_moisture_min < MOISTURE_THRESHOLD_MIN:
        return True
    else:
        return False

def calculate_eto_penman_monteith(sensor_data: Dict) -> float:
    """
    Calculate reference evapotranspiration (ETo) using the Penman-Monteith method.
    
    Args:
        sensor_data: Dictionary containing sensor readings
        
    Returns:
        Reference evapotranspiration (mm/day)
    """
    # Extract relevant sensor data
    temp_avg = (sensor_data['TC_min'] + sensor_data['TC_max']) / 2  # Average temperature (°C)
    temp_min = sensor_data['TC_min']  # Minimum temperature (°C)
    temp_max = sensor_data['TC_max']  # Maximum temperature (°C)
    hum_avg = (sensor_data['HUM_min'] + sensor_data['HUM_max']) / 2  # Average humidity (%)
    wind_speed = sensor_data['ANE_max'] * 1000 / 3600  # Convert km/h to m/s
    solar_radiation = sensor_data['LUX_max'] * 0.0079  # Approximate conversion from lux to MJ/m²/day
    
    # Constants
    altitude = 100  # meters above sea level (example value)
    latitude = 40  # degrees North (example value)
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    
    # Calculate atmospheric pressure from altitude
    atm_pressure = 101.3 * ((293 - 0.0065 * altitude) / 293) ** 5.26
    
    # Calculate psychrometric constant (γ)
    psychrometric_constant = 0.000665 * atm_pressure
    
    # Calculate saturation vapor pressure
    sat_vp_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
    sat_vp_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
    sat_vp = (sat_vp_tmin + sat_vp_tmax) / 2
    
    # Calculate actual vapor pressure
    actual_vp = (sat_vp * hum_avg) / 100
    
    # Calculate vapor pressure deficit
    vpd = sat_vp - actual_vp
    
    # Calculate slope of saturation vapor pressure curve
    delta = (4098 * (0.6108 * math.exp((17.27 * temp_avg) / (temp_avg + 237.3)))) / ((temp_avg + 237.3) ** 2)
    
    # Calculate extraterrestrial radiation (Ra)
    solar_declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset_hour_angle = math.acos(-math.tan(latitude * math.pi / 180) * math.tan(solar_declination))
    
    inv_dist_earth_sun = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    ra = 24 * 60 / math.pi * 0.082 * inv_dist_earth_sun * (
        sunset_hour_angle * math.sin(latitude * math.pi / 180) * math.sin(solar_declination) +
        math.cos(latitude * math.pi / 180) * math.cos(solar_declination) * math.sin(sunset_hour_angle)
    )
    
    # Calculate clear sky solar radiation (Rso)
    rso = (0.75 + 2e-5 * altitude) * ra
    
    # Use measured solar radiation if available, otherwise estimate
    rs = solar_radiation
    
    # Calculate net solar radiation (Rns)
    rns = (1 - 0.23) * rs
    
    # Calculate net longwave radiation (Rnl)
    stefan_boltzmann = 4.903e-9  # MJ K⁻⁴ m⁻² day⁻¹
    tmin_k = temp_min + 273.16
    tmax_k = temp_max + 273.16
    rnl = stefan_boltzmann * ((tmin_k**4 + tmax_k**4) / 2) * (0.34 - 0.14 * math.sqrt(actual_vp)) * (1.35 * rs / rso - 0.35)
    
    # Calculate net radiation (Rn)
    rn = rns - rnl
    
    # Calculate soil heat flux (G)
    # For daily calculations, G is often assumed to be 0
    g = 0
    
    # Calculate reference evapotranspiration (ETo)
    numerator = 0.408 * delta * (rn - g) + psychrometric_constant * (900 / (temp_avg + 273)) * wind_speed * vpd
    denominator = delta + psychrometric_constant * (1 + 0.34 * wind_speed)
    eto = numerator / denominator
    
    return max(0, eto)  # Ensure ETo is not negative

def calculate_etc(eto: float, crop_week: int) -> float:
    """
    Calculate crop evapotranspiration (ETc) using the crop coefficient (Kc).
    
    Args:
        eto: Reference evapotranspiration (mm/day)
        crop_week: Current week of crop growth
        
    Returns:
        Crop evapotranspiration (mm/day)
    """
    # Get the crop coefficient for the current week
    kc = KC_VALUES.get(crop_week, 1.0)  # Default to 1.0 if week not found
    
    # Calculate crop evapotranspiration
    etc = eto * kc
    
    return etc

def calculate_irrigation_requirements(etc: float, rainfall: float) -> float:
    """
    Calculate irrigation water requirements.
    
    Args:
        etc: Crop evapotranspiration (mm/day)
        rainfall: Effective rainfall (mm/day)
        
    Returns:
        Irrigation water requirement (mm/day)
    """
    # Effective rainfall is the portion of rainfall that is actually useful for plants
    # For simplicity, we'll use 80% of actual rainfall as effective
    effective_rainfall = rainfall * 0.8
    
    # Calculate irrigation requirement (accounting for irrigation efficiency)
    irrigation_req = max(0, (etc - effective_rainfall) / IRRIGATION_EFFICIENCY)
    
    return irrigation_req

def calculate_water_volume(irrigation_req: float) -> float:
    """
    Calculate required water volume based on irrigation requirement and field area.
    
    Args:
        irrigation_req: Irrigation water requirement (mm/day)
        
    Returns:
        Water volume (L)
    """
    # Convert mm/day to L for the whole field
    # 1 mm over 1 m² equals 1 L of water
    water_volume = irrigation_req * FIELD_AREA
    
    return water_volume

def calculate_pump_time(water_volume: float) -> float:
    """
    Calculate required pump operation time based on water volume and flow rate.
    
    Args:
        water_volume: Required water volume (L)
        
    Returns:
        Pump operation time (minutes)
    """
    # Calculate time required to pump the required volume
    pump_time = water_volume / MOTOR_FLOW_RATE
    
    return pump_time

def main():
    """
    Main function to run the irrigation control system.
    """
    print("==== Irrigation Control System ====")
    
    # 1. Read sensor data
    print("\nStep 1: Reading sensor data...")
    sensor_data = read_sensor_data()
    print("Sensor data retrieved successfully.")
    
    # 2. Check if irrigation is required
    print("\nStep 2: Determining if irrigation is required...")
    irrigation_needed = is_irrigation_required(sensor_data)
    
    if not irrigation_needed:
        print("Irrigation is NOT required. Soil moisture is adequate.")
        return
    
    print("Irrigation IS required. Soil moisture is below threshold.")
    
    # 3. Calculate reference evapotranspiration (ETo)
    print("\nStep 3: Calculating reference evapotranspiration (ETo)...")
    eto = calculate_eto_penman_monteith(sensor_data)
    print(f"Reference evapotranspiration (ETo): {eto:.2f} mm/day")
    
    # 4. Get crop week and Kc value
    print("\nStep 4: Determining crop growth stage...")
    crop_week = get_crop_week()
    kc = KC_VALUES.get(crop_week, 1.0)
    print(f"Current crop week: {crop_week}")
    print(f"Crop coefficient (Kc): {kc:.2f}")
    
    # 5. Calculate crop evapotranspiration (ETc)
    print("\nStep 5: Calculating crop evapotranspiration (ETc)...")
    etc = calculate_etc(eto, crop_week)
    print(f"Crop evapotranspiration (ETc): {etc:.2f} mm/day")
    
    # 6. Account for rainfall
    rainfall = sensor_data.get('PLV2_max', 0)  # mm/day
    print(f"Rainfall: {rainfall:.2f} mm/day")
    
    # 7. Calculate irrigation requirements
    print("\nStep 6: Calculating irrigation requirements...")
    irrigation_req = calculate_irrigation_requirements(etc, rainfall)
    print(f"Irrigation requirement: {irrigation_req:.2f} mm/day")
    
    # 8. Calculate water volume
    print("\nStep 7: Calculating required water volume...")
    water_volume = calculate_water_volume(irrigation_req)
    print(f"Required water volume: {water_volume:.2f} L")
    
    # 9. Calculate pump operation time
    print("\nStep 8: Calculating pump operation time...")
    pump_time = calculate_pump_time(water_volume)
    print(f"Required pump operation time: {pump_time:.2f} minutes")
    
    # 10. Final recommendation
    print("\n==== Irrigation Recommendation ====")
    print(f"Run irrigation pump for {round(pump_time)} minutes.")
    print(f"This will provide {water_volume:.2f} liters of water.")

if __name__ == "__main__":
    main()
