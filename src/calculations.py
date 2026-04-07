from statistics import median
from config import GEAR_RATIO, PUMP_LITERS_PER_REV, ENGINE_RPM_FROM_CARDAN_COEFF

def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))

def scale_4_20ma(raw_ma: float, eng_min: float, eng_max: float) -> float:
    ma = clamp(raw_ma, 4.0, 20.0)
    return eng_min + ((ma - 4.0) / 16.0) * (eng_max - eng_min)

def calc_manifold_pressure_mpa_from_current(raw_ma: float) -> float:
    value = scale_4_20ma(raw_ma, 0.0, 103.4) - 0.4
    return max(0.0, value)

def calc_mech_oil_pressure_kpa_from_current(raw_ma: float) -> float:
    return scale_4_20ma(raw_ma, 0.0, 2500.0)

def calc_mech_oil_temp_c_from_current(raw_ma: float) -> float:
    return scale_4_20ma(raw_ma, -50.0, 150.0)

def calc_hydraulic_oil_temp_c_from_current(raw_ma: float) -> float:
    return scale_4_20ma(raw_ma, -50.0, 150.0)

def calc_transmission_oil_temp_c_from_current(raw_ma: float) -> float:
    return scale_4_20ma(raw_ma, -50.0, 150.0)

def calc_transmission_oil_pressure_kpa_from_current(raw_ma: float) -> float:
    return scale_4_20ma(raw_ma, 0.0, 2500.0)

def smooth_period_ms(period_values):
    vals = [float(v) for v in period_values if v is not None and v > 0]
    if not vals:
        return 0.0
    return float(median(vals))

def calc_cardan_rpm_from_period_ms(period_ms: float) -> float:
    if period_ms <= 0:
        return 0.0
    return 60000.0 / period_ms

def calc_engine_rpm_from_period_ms(period_ms: float) -> float:
    return calc_cardan_rpm_from_period_ms(period_ms) * ENGINE_RPM_FROM_CARDAN_COEFF

def calc_pump_rpm_from_period_ms(period_ms: float) -> float:
    return calc_cardan_rpm_from_period_ms(period_ms) / GEAR_RATIO

def calc_pump_flow_lps_from_period_ms(period_ms: float) -> float:
    pump_rpm = calc_pump_rpm_from_period_ms(period_ms)
    pump_flow_lpm = pump_rpm * PUMP_LITERS_PER_REV
    return pump_flow_lpm / 60.0

def calc_pump_total_liters_from_counter(counter: int, pulses_per_rev: float) -> float:
    if pulses_per_rev <= 0:
        return 0.0
    cardan_revs = counter / pulses_per_rev
    pump_revs = cardan_revs / GEAR_RATIO
    return pump_revs * PUMP_LITERS_PER_REV

def bucket_pressure_mpa(value: float) -> str | None:
    if value < 0:
        return None
    if value < 10:
        return "pressure_mpa_0_10"
    if value < 25:
        return "pressure_mpa_10_25"
    if value < 50:
        return "pressure_mpa_25_50"
    if value < 75:
        return "pressure_mpa_50_75"
    if value <= 105:
        return "pressure_mpa_75_105"
    return None

def bucket_pump_rpm(value: float) -> str | None:
    if value < 0:
        return None
    if value < 30:
        return "pump_rpm_0_30"
    if value < 60:
        return "pump_rpm_30_60"
    if value < 90:
        return "pump_rpm_60_90"
    if value < 120:
        return "pump_rpm_90_120"
    if value < 160:
        return "pump_rpm_120_160"
    if value < 200:
        return "pump_rpm_160_200"
    if value < 250:
        return "pump_rpm_200_250"
    if value <= 300:
        return "pump_rpm_250_300"
    return None

def bucket_mech_oil_temp_c(value: float) -> str | None:
    if value < 5:
        return "mech_oil_temp_lt_5"
    if value < 15:
        return "mech_oil_temp_5_15"
    if value < 40:
        return "mech_oil_temp_15_40"
    if value < 60:
        return "mech_oil_temp_40_60"
    if value < 80:
        return "mech_oil_temp_60_80"
    return "mech_oil_temp_gt_80"

def bucket_mech_oil_pressure_kpa(value: float) -> str | None:
    if value < 400:
        return "mech_oil_pressure_lt_400"
    if value < 600:
        return "mech_oil_pressure_400_600"
    if value < 1000:
        return "mech_oil_pressure_600_1000"
    return "mech_oil_pressure_gt_1000"
