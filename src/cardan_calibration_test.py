import time
from collections import deque
from config import PERIOD_WINDOW_SIZE, CARDAN_PULSES_PER_REV, COUNTER_STALL_WINDOW
from mv210 import MV210Client
from calculations import smooth_period_ms, calc_cardan_rpm_from_period_ms, calc_engine_rpm_from_period_ms, calc_pump_rpm_from_period_ms, calc_pump_flow_lps_from_period_ms, calc_pump_total_liters_from_counter

def counter_stalled(counter_samples) -> bool:
    if len(counter_samples) < COUNTER_STALL_WINDOW:
        return False
    first = counter_samples[0]
    return all(x == first for x in counter_samples)

def main():
    mv = MV210Client()
    mv.connect()
    print("Connected to MV210")
    print("Press Ctrl+C to stop\n")

    period_samples = deque(maxlen=PERIOD_WINDOW_SIZE)
    counter_samples = deque(maxlen=COUNTER_STALL_WINDOW)

    try:
        while True:
            counter = mv.read_di1_counter()
            raw_period_ms = mv.read_di3_period_ms()
            counter_samples.append(counter)

            if counter_stalled(counter_samples):
                effective_period_ms = 0.0
                period_samples.clear()
            else:
                if raw_period_ms > 0:
                    period_samples.append(raw_period_ms)
                effective_period_ms = smooth_period_ms(period_samples)

            cardan_rpm = calc_cardan_rpm_from_period_ms(effective_period_ms)
            engine_rpm = calc_engine_rpm_from_period_ms(effective_period_ms)
            pump_rpm = calc_pump_rpm_from_period_ms(effective_period_ms)
            pump_flow_lps = calc_pump_flow_lps_from_period_ms(effective_period_ms)
            pump_total_liters = calc_pump_total_liters_from_counter(counter, CARDAN_PULSES_PER_REV)

            print(f"counter={counter:10d} | raw_period_ms={raw_period_ms:8.2f} | period_ms={effective_period_ms:8.2f} | cardan_rpm={cardan_rpm:8.2f} | engine_rpm={engine_rpm:8.2f} | pump_rpm={pump_rpm:8.2f} | flow_lps={pump_flow_lps:8.3f} | total_l={pump_total_liters:12.2f}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        mv.disconnect()

if __name__ == "__main__":
    main()
