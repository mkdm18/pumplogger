import time
from pathlib import Path
from collections import deque

from config import (
    BASE_DIR,
    DATA_DIR,
    LOG_DIR,
    EXPORT_DIR,
    DB_COMMIT_INTERVAL_SECONDS,
    WAIT_POLL_SECONDS,
    BOARD_LOG_INTERVAL_WAIT,
    BOARD_LOG_INTERVAL_REC,
    WORK_LOG_INTERVAL_REC,
    TIME_SYNC_INTERVAL_SECONDS,
    BACKUP_INTERVAL_REC_SECONDS,
    CARDAN_PULSES_PER_REV,
    RETURN_TO_WAIT_DELAY_SECONDS,
    MANIFOLD_START_THRESHOLD_MPA,
    MANIFOLD_STOP_THRESHOLD_MPA,
    CARDAN_ACTIVITY_THRESHOLD,
    PERIOD_WINDOW_SIZE,
    COUNTER_STALL_WINDOW,
    GEAR_RATIO,
    USB_EXPORT_CHECK_INTERVAL_SECONDS,
    USB_MOUNT_POINT,
    USB_AUTO_UNMOUNT_AFTER_EXPORT,
)
from db import Database
from plc import PLCReader
from mv210 import MV210Client
from calculations import (
    calc_manifold_pressure_mpa_from_current,
    calc_mech_oil_pressure_kpa_from_current,
    calc_mech_oil_temp_c_from_current,
    calc_hydraulic_oil_temp_c_from_current,
    calc_transmission_oil_temp_c_from_current,
    calc_transmission_oil_pressure_kpa_from_current,
    smooth_period_ms,
    calc_pump_rpm_from_period_ms,
    calc_pump_flow_lps_from_period_ms,
)
from backup_manager import backup_database_rotating
from time_sync import sync_time_from_owen
from storage import initialize_database
from usb_export import (
    find_usb_partition,
    mount_usb_partition,
    is_writable_dir,
    read_export_days,
    perform_usb_export,
    unmount_usb,
)


def ensure_dirs():
    for p in [BASE_DIR, DATA_DIR, LOG_DIR, EXPORT_DIR]:
        Path(p).mkdir(parents=True, exist_ok=True)


def read_board_values(plc: PLCReader) -> dict:
    currents = plc.read_raw_currents()

    return {
        "manifold_pressure_mpa": calc_manifold_pressure_mpa_from_current(currents["db1_current_ma"]),
        "mech_oil_pressure_kpa": calc_mech_oil_pressure_kpa_from_current(currents["db3_current_ma"]),
        "mech_oil_temp_c": calc_mech_oil_temp_c_from_current(currents["db2_current_ma"]),
        "hydraulic_oil_temp_c": calc_hydraulic_oil_temp_c_from_current(currents["db6_current_ma"]),
        "transmission_oil_temp_c": calc_transmission_oil_temp_c_from_current(currents["db9_current_ma"]),
        "transmission_oil_pressure_kpa": calc_transmission_oil_pressure_kpa_from_current(currents["db8_current_ma"]),
    }


def counter_stalled(counter_samples) -> bool:
    if len(counter_samples) < COUNTER_STALL_WINDOW:
        return False
    first = counter_samples[0]
    return all(x == first for x in counter_samples)


def main():
    ensure_dirs()
    initialize_database()

    db = Database()
    db.ensure_default_meta()
    db.increment_meta_int("boot_count", 1)
    db.insert_system_log("INFO", "BOOT", "System boot")

    plc = PLCReader()
    mv = MV210Client()

    last_commit_ts = 0.0
    last_time_sync_ts = 0.0
    last_board_log_ts = 0.0
    last_work_log_ts = 0.0
    last_backup_ts = 0.0
    last_usb_check_ts = 0.0

    mode = "WAIT"
    db.set_meta_text("last_mode", mode)
    db.insert_system_log("INFO", "MODE_WAIT", "Enter WAIT mode")

    period_samples = deque(maxlen=PERIOD_WINDOW_SIZE)
    counter_samples = deque(maxlen=COUNTER_STALL_WINDOW)

    last_counter = None
    rec_inactive_since = None

    # Источник истины для общего литража — БД
    pump_total_liters = db.get_meta_real("pump_total_liters", 0.0)

    # Накопитель импульсов кардана между записями бортового журнала
    board_interval_cardan_pulses = 0

    while True:
        now = time.time()
        now_int = int(now)

        # Подключения к устройствам
        try:
            if not plc.is_connected():
                plc.connect()
            if not mv.is_connected():
                mv.connect()
        except Exception as e:
            db.insert_system_log("WARN", "DEVICE_WAIT", f"Waiting devices: {e}")
            db.commit()
            time.sleep(WAIT_POLL_SECONDS)
            continue

        # Синхронизация времени
        if now - last_time_sync_ts >= TIME_SYNC_INTERVAL_SECONDS:
            try:
                sync_time_from_owen()
                db.insert_system_log("INFO", "TIME_SYNC_OK", "Synced time from MV210")
            except Exception as e:
                db.insert_system_log("ERROR", "TIME_SYNC_ERROR", str(e))
            last_time_sync_ts = now

        # Чтение МВ210
        try:
            counter = mv.read_di1_counter()
            raw_period_ms = mv.read_di3_period_ms()
        except Exception as e:
            db.insert_system_log("ERROR", "MV210_READ_ERROR", str(e))
            db.commit()
            time.sleep(WAIT_POLL_SECONDS)
            continue

        # Активность по DI1
        cardan_delta = 0
        if last_counter is not None:
            cardan_delta = counter - last_counter
            if cardan_delta < 0:
                cardan_delta = 0

        last_counter = counter
        board_interval_cardan_pulses += cardan_delta

        # Детектор остановки по счетчику
        counter_samples.append(counter)

        if counter_stalled(counter_samples):
            effective_period_ms = 0.0
            period_samples.clear()
        else:
            if raw_period_ms > 0:
                period_samples.append(raw_period_ms)
            effective_period_ms = smooth_period_ms(period_samples)

        # Мгновенные обороты / расход по эффективному периоду
        pump_rpm = calc_pump_rpm_from_period_ms(effective_period_ms)
        pump_flow_lps = calc_pump_flow_lps_from_period_ms(effective_period_ms)

        # Чтение PLC
        try:
            board = read_board_values(plc)
        except Exception as e:
            db.insert_system_log("ERROR", "PLC_READ_ERROR", str(e))
            db.commit()
            time.sleep(WAIT_POLL_SECONDS)
            continue

        manifold_pressure_mpa = board["manifold_pressure_mpa"]
        cardan_active = cardan_delta >= CARDAN_ACTIVITY_THRESHOLD

        # Переходы между режимами
        if mode == "WAIT":
            if cardan_active or manifold_pressure_mpa > MANIFOLD_START_THRESHOLD_MPA:
                mode = "REC"
                db.set_meta_text("last_mode", mode)
                db.insert_system_log("INFO", "MODE_REC", "Enter REC mode")
                db.commit()
                rec_inactive_since = None

        elif mode == "REC":
            if manifold_pressure_mpa < MANIFOLD_STOP_THRESHOLD_MPA and not cardan_active:
                if rec_inactive_since is None:
                    rec_inactive_since = now
                elif now - rec_inactive_since >= RETURN_TO_WAIT_DELAY_SECONDS:
                    mode = "WAIT"
                    db.set_meta_text("last_mode", mode)
                    db.insert_system_log("INFO", "MODE_WAIT", "Return to WAIT mode")
                    db.commit()

                    try:
                        backup_database_rotating(db)
                        db.increment_meta_int("backup_success_count", 1)
                        db.insert_system_log("INFO", "BACKUP_OK", "Backup completed on return to WAIT")
                    except Exception as e:
                        db.increment_meta_int("backup_error_count", 1)
                        db.insert_system_log("ERROR", "BACKUP_FAIL", str(e))

                    db.commit()
                    rec_inactive_since = None
            else:
                rec_inactive_since = None

        # Бортовой журнал
        board_interval = BOARD_LOG_INTERVAL_WAIT if mode == "WAIT" else BOARD_LOG_INTERVAL_REC
        if now - last_board_log_ts >= board_interval:
            transmission_hours_total = db.get_meta_real("transmission_hours_total", 0.0)
            transmission_threshold = db.get_meta_real("transmission_oil_pressure_run_threshold", 300.0)

            if board["transmission_oil_pressure_kpa"] > transmission_threshold:
                transmission_hours_total += board_interval / 3600.0
                db.set_meta_real("transmission_hours_total", transmission_hours_total)

            # Число оборотов насоса за интервал бортового журнала
            cardan_revs_interval = board_interval_cardan_pulses / CARDAN_PULSES_PER_REV
            pump_revs_interval = cardan_revs_interval / GEAR_RATIO

            db.insert_board_log(
                timestamp_utc=now_int,
                manifold_pressure_mpa=board["manifold_pressure_mpa"],
                mech_oil_pressure_kpa=board["mech_oil_pressure_kpa"],
                mech_oil_temp_c=board["mech_oil_temp_c"],
                hydraulic_oil_temp_c=board["hydraulic_oil_temp_c"],
                transmission_oil_temp_c=board["transmission_oil_temp_c"],
                transmission_oil_pressure_kpa=board["transmission_oil_pressure_kpa"],
                engine_hours_total=pump_revs_interval,
                transmission_hours_total=transmission_hours_total,
                reserve_1=None,
                reserve_2=None,
                reserve_3=None,
            )

            db.update_maxima(
                manifold_pressure_mpa=board["manifold_pressure_mpa"],
                mech_oil_pressure_kpa=board["mech_oil_pressure_kpa"],
                mech_oil_temp_c=board["mech_oil_temp_c"],
                hydraulic_oil_temp_c=board["hydraulic_oil_temp_c"],
                transmission_oil_temp_c=board["transmission_oil_temp_c"],
                transmission_oil_pressure_kpa=board["transmission_oil_pressure_kpa"],
            )

            board_interval_cardan_pulses = 0
            last_board_log_ts = now

        # Рабочий журнал
        if mode == "REC" and now - last_work_log_ts >= WORK_LOG_INTERVAL_REC:
            # Общий литраж считаем накопительно в БД
            pump_total_liters += pump_flow_lps * WORK_LOG_INTERVAL_REC
            db.set_meta_real("pump_total_liters", pump_total_liters)

            db.insert_work_log(
                timestamp_utc=now_int,
                manifold_pressure_mpa=board["manifold_pressure_mpa"],
                pump_rpm=pump_rpm,
                pump_flow_lps=pump_flow_lps,
                pump_total_liters=pump_total_liters,
                reserve_1=None,
            )
            last_work_log_ts = now

        # Проверка флешки и экспорт только в WAIT
        if mode == "WAIT" and now - last_usb_check_ts >= USB_EXPORT_CHECK_INTERVAL_SECONDS:
            try:
                dev_path = find_usb_partition()
                if dev_path:
                    mounted = mount_usb_partition(dev_path, USB_MOUNT_POINT)
                    if mounted and is_writable_dir(USB_MOUNT_POINT):
                        days = read_export_days(USB_MOUNT_POINT, default_days=2)
                        perform_usb_export(days)
                        db.insert_system_log("INFO", "USB_EXPORT_OK", f"USB export completed, days={days}")
                        db.commit()

                        if USB_AUTO_UNMOUNT_AFTER_EXPORT:
                            unmount_usb(USB_MOUNT_POINT)
            except Exception as e:
                db.insert_system_log("ERROR", "USB_EXPORT_FAIL", str(e))
                db.commit()

            last_usb_check_ts = now

        # Общий commit
        if now - last_commit_ts >= DB_COMMIT_INTERVAL_SECONDS:
            db.increment_meta_int("total_uptime_seconds", DB_COMMIT_INTERVAL_SECONDS)
            db.commit()
            last_commit_ts = now

        # Периодический backup в режиме REC
        if mode == "REC" and now - last_backup_ts >= BACKUP_INTERVAL_REC_SECONDS:
            try:
                backup_database_rotating(db)
                db.increment_meta_int("backup_success_count", 1)
                db.insert_system_log("INFO", "BACKUP_OK", "Periodic REC backup completed")
            except Exception as e:
                db.increment_meta_int("backup_error_count", 1)
                db.insert_system_log("ERROR", "BACKUP_FAIL", str(e))

            db.commit()
            last_backup_ts = now

        time.sleep(WAIT_POLL_SECONDS if mode == "WAIT" else 1)


if __name__ == "__main__":
    main()