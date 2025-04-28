"""""
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
from typing import Dict

# Constants
FIELD_AREA = 1000  # m²
MOTOR_FLOW_RATE = 1000  # L/min
IRRIGATION_EFFICIENCY = 0.85

MOISTURE_THRESHOLD_MIN = 40
MOISTURE_THRESHOLD_MAX = 60

KC_VALUES = {
    1: 0.3, 2: 0.4, 3: 0.5, 4: 0.7,
    5: 0.8, 6: 0.9, 7: 1.0, 8: 1.1,
    9: 1.1, 10: 1.0, 11: 0.9, 12: 0.8
}

def read_sensor_data() -> Dict:
    return {
        'TC_min': 18.5, 'HUM_min': 40, 'SOILTC_min': 16.2,
        'SOIL_B_min': 35, 'SOIL_C_min': 33, 'PRES_min': 1009.2,
        'TC_max': 28.3, 'HUM_max': 65, 'SOILTC_max': 22.1,
        'ANE_max': 12.5, 'PLV2_max': 0, 'SOIL_B_max': 42,
        'SOIL_C_max': 40, 'LDR_max': 975, 'LW_max': 875,
        'LUX_max': 65000, 'PRES_max': 1014.6,
    }

def get_crop_week() -> int:
    planting_date = datetime.datetime(2025, 3, 15)
    current_date = datetime.datetime.now()
    days_difference = (current_date - planting_date).days
    return min((days_difference // 7) + 1, max(KC_VALUES.keys()))

def is_irrigation_required(sensor_data: Dict) -> bool:
    avg_soil_moisture_min = (sensor_data['SOIL_B_min'] + sensor_data['SOIL_C_min']) / 2
    print(f"Average minimum soil moisture: {avg_soil_moisture_min:.1f}%")
    print(f"Moisture threshold: {MOISTURE_THRESHOLD_MIN}%")
    return avg_soil_moisture_min < MOISTURE_THRESHOLD_MIN

def calculate_eto_penman_monteith(sensor_data: Dict) -> float:
    temp_avg = (sensor_data['TC_min'] + sensor_data['TC_max']) / 2
    temp_min = sensor_data['TC_min']
    temp_max = sensor_data['TC_max']
    hum_avg = (sensor_data['HUM_min'] + sensor_data['HUM_max']) / 2
    wind_speed = sensor_data['ANE_max'] * 1000 / 3600
    solar_radiation = sensor_data['LUX_max'] * 0.0079
    altitude = 100
    latitude = 40
    day_of_year = datetime.datetime.now().timetuple().tm_yday
    atm_pressure = 101.3 * ((293 - 0.0065 * altitude) / 293) ** 5.26
    gamma = 0.000665 * atm_pressure
    sat_vp_tmin = 0.6108 * math.exp((17.27 * temp_min) / (temp_min + 237.3))
    sat_vp_tmax = 0.6108 * math.exp((17.27 * temp_max) / (temp_max + 237.3))
    sat_vp = (sat_vp_tmin + sat_vp_tmax) / 2
    actual_vp = (sat_vp * hum_avg) / 100
    vpd = sat_vp - actual_vp
    delta = (4098 * (0.6108 * math.exp((17.27 * temp_avg) / (temp_avg + 237.3)))) / ((temp_avg + 237.3) ** 2)
    solar_declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset_hour_angle = math.acos(-math.tan(latitude * math.pi / 180) * math.tan(solar_declination))
    inv_dist = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    ra = 24 * 60 / math.pi * 0.082 * inv_dist * (
        sunset_hour_angle * math.sin(latitude * math.pi / 180) * math.sin(solar_declination) +
        math.cos(latitude * math.pi / 180) * math.cos(solar_declination) * math.sin(sunset_hour_angle))
    rso = (0.75 + 2e-5 * altitude) * ra
    rs = solar_radiation
    rns = (1 - 0.23) * rs
    tmin_k = temp_min + 273.16
    tmax_k = temp_max + 273.16
    rnl = 4.903e-9 * ((tmin_k**4 + tmax_k**4) / 2) * (0.34 - 0.14 * math.sqrt(actual_vp)) * (1.35 * rs / rso - 0.35)
    rn = rns - rnl
    g = 0
    numerator = 0.408 * delta * (rn - g) + gamma * (900 / (temp_avg + 273)) * wind_speed * vpd
    denominator = delta + gamma * (1 + 0.34 * wind_speed)
    eto = numerator / denominator
    return max(0, eto)

def calculate_etc(eto: float, crop_week: int) -> float:
    kc = KC_VALUES.get(crop_week, 1.0)
    return eto * kc

def calculate_irrigation_requirements(etc: float, rainfall: float) -> float:
    effective_rainfall = rainfall * 0.8
    return max(0, (etc - effective_rainfall) / IRRIGATION_EFFICIENCY)

def calculate_water_volume(irrigation_req: float) -> float:
    return irrigation_req * FIELD_AREA

def calculate_pump_time(water_volume: float) -> float:
    return water_volume / MOTOR_FLOW_RATE

def main():
    print("==== Irrigation Control System ====")
    print("\nStep 1: Reading sensor data...")
    sensor_data = read_sensor_data()
    print("Sensor data retrieved successfully:")
    for key, val in sensor_data.items():
        print(f"{key}: {val}")

    print("\nStep 2: Determining if irrigation is required...")
    irrigation_needed = is_irrigation_required(sensor_data)

    if not irrigation_needed:
        print("Irrigation is NOT required. Soil moisture is adequate.")
        return

    print("Irrigation IS required. Soil moisture is below threshold.")
    print("\nStep 3: Calculating reference evapotranspiration (ETo)...")
    eto = calculate_eto_penman_monteith(sensor_data)
    print(f"Reference evapotranspiration (ETo): {eto:.2f} mm/day")

    print("\nStep 4: Determining crop growth stage...")
    crop_week = get_crop_week()
    kc = KC_VALUES.get(crop_week, 1.0)
    print(f"Current crop week: {crop_week}")
    print(f"Crop coefficient (Kc): {kc:.2f}")

    print("\nStep 5: Calculating crop evapotranspiration (ETc)...")
    etc = calculate_etc(eto, crop_week)
    print(f"Crop evapotranspiration (ETc): {etc:.2f} mm/day")

    rainfall = sensor_data.get('PLV2_max', 0)
    print(f"Rainfall: {rainfall:.2f} mm/day")

    print("\nStep 6: Calculating irrigation requirements...")
    irrigation_req = calculate_irrigation_requirements(etc, rainfall)
    print(f"Irrigation requirement: {irrigation_req:.2f} mm/day")

    print("\nStep 7: Calculating required water volume...")
    water_volume = calculate_water_volume(irrigation_req)
    print(f"Required water volume: {water_volume:.2f} L")

    print("\nStep 8: Calculating pump operation time...")
    pump_time = calculate_pump_time(water_volume)
    print(f"Required pump operation time: {pump_time:.2f} minutes")

    print("\n==== Irrigation Recommendation ====")
    print(f"Run irrigation pump for {round(pump_time)} minutes.")
    print(f"This will provide {water_volume:.2f} liters of water.")

if __name__ == "__main__":
    main()
