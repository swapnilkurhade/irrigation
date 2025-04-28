import datetime
import math
from typing import Dict
from django.http import JsonResponse

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

def run_irrigation_system(request):
    response = {}
    sensor_data = read_sensor_data()
    response['sensor_data'] = sensor_data

    avg_soil_moisture = (sensor_data['SOIL_B_min'] + sensor_data['SOIL_C_min']) / 2
    response['avg_soil_moisture'] = round(avg_soil_moisture, 1)
    response['moisture_threshold'] = MOISTURE_THRESHOLD_MIN
    irrigation_needed = is_irrigation_required(sensor_data)
    response['irrigation_needed'] = irrigation_needed

    if not irrigation_needed:
        response['message'] = "Irrigation NOT required. Soil moisture is adequate."
        return JsonResponse(response)

    eto = calculate_eto_penman_monteith(sensor_data)
    response['eto'] = round(eto, 2)

    crop_week = get_crop_week()
    kc = KC_VALUES.get(crop_week, 1.0)
    response['crop_week'] = crop_week
    response['kc'] = kc

    etc = calculate_etc(eto, crop_week)
    response['etc'] = round(etc, 2)

    rainfall = sensor_data.get('PLV2_max', 0)
    response['rainfall'] = rainfall

    irrigation_req = calculate_irrigation_requirements(etc, rainfall)
    response['irrigation_requirement'] = round(irrigation_req, 2)

    water_volume = calculate_water_volume(irrigation_req)
    response['water_volume'] = round(water_volume, 2)

    pump_time = calculate_pump_time(water_volume)
    response['pump_time'] = round(pump_time, 2)

    response['message'] = f"Run irrigation pump for {round(pump_time)} minutes. This will provide {round(water_volume, 2)} liters of water."

    return JsonResponse(response)
