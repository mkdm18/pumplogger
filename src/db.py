import sqlite3
import time
from pathlib import Path
from config import DB_PATH

DEFAULT_META = {
    "boot_count": ("int", 0),
    "db_recovery_count": ("int", 0),
    "total_uptime_seconds": ("int", 0),
    "engine_hours_total": ("real", 0.0),
    "transmission_hours_total": ("real", 0.0),
    "pump_total_liters": ("real", 0.0),
    "backup_success_count": ("int", 0),
    "backup_error_count": ("int", 0),
    "last_backup_slot": ("text", "b"),
    "timezone_offset_minutes": ("int", 300),
    "last_mode": ("text", "INIT"),
    "max_manifold_pressure_mpa": ("real", 0.0),
    "max_mech_oil_pressure_kpa": ("real", 0.0),
    "max_mech_oil_temp_c": ("real", -999999.0),
    "max_hydraulic_oil_temp_c": ("real", -999999.0),
    "max_transmission_oil_temp_c": ("real", -999999.0),
    "max_transmission_oil_pressure_kpa": ("real", 0.0),
    "manifold_start_threshold": ("real", 1.0),
    "manifold_stop_threshold": ("real", 1.0),
    "cardan_activity_threshold": ("int", 1),
    "transmission_oil_pressure_run_threshold": ("real", 300.0),
}

SMART_COUNTER_KEYS = [
    "pressure_mpa_0_10", "pressure_mpa_10_25", "pressure_mpa_25_50", "pressure_mpa_50_75", "pressure_mpa_75_105",
    "pump_rpm_0_30", "pump_rpm_30_60", "pump_rpm_60_90", "pump_rpm_90_120",
    "pump_rpm_120_160", "pump_rpm_160_200", "pump_rpm_200_250", "pump_rpm_250_300",
    "mech_oil_temp_lt_5", "mech_oil_temp_5_15", "mech_oil_temp_15_40", "mech_oil_temp_40_60", "mech_oil_temp_60_80", "mech_oil_temp_gt_80",
    "mech_oil_pressure_lt_400", "mech_oil_pressure_400_600", "mech_oil_pressure_600_1000", "mech_oil_pressure_gt_1000",
]

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path, timeout=10)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        self.conn.close()

    def execute_script(self, script_text: str):
        self.conn.executescript(script_text)
        self.conn.commit()

    def commit(self):
        self.conn.commit()

    def integrity_ok(self) -> bool:
        cur = self.conn.execute("PRAGMA integrity_check;")
        row = cur.fetchone()
        return bool(row and row[0] == "ok")

    def ensure_default_meta(self):
        now_utc = int(time.time())
        for key, (kind, value) in DEFAULT_META.items():
            cur = self.conn.execute("SELECT key FROM meta_state WHERE key = ?", (key,))
            if cur.fetchone():
                continue
            if kind == "int":
                self.conn.execute("INSERT INTO meta_state (key, value_int, updated_utc) VALUES (?, ?, ?)", (key, int(value), now_utc))
            elif kind == "real":
                self.conn.execute("INSERT INTO meta_state (key, value_real, updated_utc) VALUES (?, ?, ?)", (key, float(value), now_utc))
            elif kind == "text":
                self.conn.execute("INSERT INTO meta_state (key, value_text, updated_utc) VALUES (?, ?, ?)", (key, str(value), now_utc))
        for key in SMART_COUNTER_KEYS:
            cur = self.conn.execute("SELECT counter_key FROM smart_counters WHERE counter_key = ?", (key,))
            if cur.fetchone():
                continue
            self.conn.execute("INSERT INTO smart_counters (counter_key, minutes, updated_utc) VALUES (?, ?, ?)", (key, 0.0, now_utc))
        self.conn.commit()

    def get_meta_int(self, key: str, default: int = 0) -> int:
        row = self.conn.execute("SELECT value_int FROM meta_state WHERE key = ?", (key,)).fetchone()
        return default if row is None or row["value_int"] is None else int(row["value_int"])

    def get_meta_real(self, key: str, default: float = 0.0) -> float:
        row = self.conn.execute("SELECT value_real FROM meta_state WHERE key = ?", (key,)).fetchone()
        return default if row is None or row["value_real"] is None else float(row["value_real"])

    def get_meta_text(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value_text FROM meta_state WHERE key = ?", (key,)).fetchone()
        return default if row is None or row["value_text"] is None else str(row["value_text"])

    def set_meta_int(self, key: str, value: int):
        self.conn.execute(
            "INSERT INTO meta_state (key, value_int, updated_utc) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value_int=excluded.value_int, updated_utc=excluded.updated_utc",
            (key, int(value), int(time.time())),
        )

    def set_meta_real(self, key: str, value: float):
        self.conn.execute(
            "INSERT INTO meta_state (key, value_real, updated_utc) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value_real=excluded.value_real, updated_utc=excluded.updated_utc",
            (key, float(value), int(time.time())),
        )

    def set_meta_text(self, key: str, value: str):
        self.conn.execute(
            "INSERT INTO meta_state (key, value_text, updated_utc) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value_text=excluded.value_text, updated_utc=excluded.updated_utc",
            (key, str(value), int(time.time())),
        )

    def increment_meta_int(self, key: str, delta: int = 1):
        self.set_meta_int(key, self.get_meta_int(key, 0) + delta)

    def insert_board_log(self, **kwargs):
        self.conn.execute(
            "INSERT INTO board_log (timestamp_utc, manifold_pressure_mpa, mech_oil_pressure_kpa, mech_oil_temp_c, hydraulic_oil_temp_c, transmission_oil_temp_c, transmission_oil_pressure_kpa, engine_hours_total, transmission_hours_total, reserve_1, reserve_2, reserve_3) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                kwargs["timestamp_utc"], kwargs["manifold_pressure_mpa"], kwargs["mech_oil_pressure_kpa"],
                kwargs["mech_oil_temp_c"], kwargs["hydraulic_oil_temp_c"], kwargs["transmission_oil_temp_c"],
                kwargs["transmission_oil_pressure_kpa"], kwargs["engine_hours_total"], kwargs["transmission_hours_total"],
                kwargs.get("reserve_1"), kwargs.get("reserve_2"), kwargs.get("reserve_3")
            ),
        )

    def insert_work_log(self, **kwargs):
        self.conn.execute(
            "INSERT INTO work_log (timestamp_utc, manifold_pressure_mpa, pump_rpm, pump_flow_lps, pump_total_liters, reserve_1) VALUES (?, ?, ?, ?, ?, ?)",
            (kwargs["timestamp_utc"], kwargs["manifold_pressure_mpa"], kwargs["pump_rpm"], kwargs["pump_flow_lps"], kwargs["pump_total_liters"], kwargs.get("reserve_1")),
        )

    def insert_system_log(self, level: str, event_code: str, message: str = "", details_json: str = None):
        self.conn.execute(
            "INSERT INTO system_log (timestamp_utc, level, event_code, message, details_json) VALUES (?, ?, ?, ?, ?)",
            (int(time.time()), level, event_code, message, details_json),
        )

    def increment_smart_counter_minutes(self, counter_key: str, delta_minutes: float):
        self.conn.execute(
            "INSERT INTO smart_counters (counter_key, minutes, updated_utc) VALUES (?, ?, ?) "
            "ON CONFLICT(counter_key) DO UPDATE SET minutes = smart_counters.minutes + excluded.minutes, updated_utc = excluded.updated_utc",
            (counter_key, float(delta_minutes), int(time.time())),
        )

    def update_maxima(self, manifold_pressure_mpa, mech_oil_pressure_kpa, mech_oil_temp_c, hydraulic_oil_temp_c, transmission_oil_temp_c, transmission_oil_pressure_kpa):
        if manifold_pressure_mpa > self.get_meta_real("max_manifold_pressure_mpa", 0.0):
            self.set_meta_real("max_manifold_pressure_mpa", manifold_pressure_mpa)
        if mech_oil_pressure_kpa > self.get_meta_real("max_mech_oil_pressure_kpa", 0.0):
            self.set_meta_real("max_mech_oil_pressure_kpa", mech_oil_pressure_kpa)
        if mech_oil_temp_c > self.get_meta_real("max_mech_oil_temp_c", -999999.0):
            self.set_meta_real("max_mech_oil_temp_c", mech_oil_temp_c)
        if hydraulic_oil_temp_c > self.get_meta_real("max_hydraulic_oil_temp_c", -999999.0):
            self.set_meta_real("max_hydraulic_oil_temp_c", hydraulic_oil_temp_c)
        if transmission_oil_temp_c > self.get_meta_real("max_transmission_oil_temp_c", -999999.0):
            self.set_meta_real("max_transmission_oil_temp_c", transmission_oil_temp_c)
        if transmission_oil_pressure_kpa > self.get_meta_real("max_transmission_oil_pressure_kpa", 0.0):
            self.set_meta_real("max_transmission_oil_pressure_kpa", transmission_oil_pressure_kpa)
