PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta_state (
    key TEXT PRIMARY KEY,
    value_text TEXT,
    value_real REAL,
    value_int INTEGER,
    updated_utc INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS board_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc INTEGER NOT NULL,
    manifold_pressure_mpa REAL,
    mech_oil_pressure_kpa REAL,
    mech_oil_temp_c REAL,
    hydraulic_oil_temp_c REAL,
    transmission_oil_temp_c REAL,
    transmission_oil_pressure_kpa REAL,
    engine_hours_total REAL,
    transmission_hours_total REAL,
    reserve_1 REAL,
    reserve_2 REAL,
    reserve_3 REAL
);

CREATE TABLE IF NOT EXISTS work_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc INTEGER NOT NULL,
    manifold_pressure_mpa REAL,
    pump_rpm REAL,
    pump_flow_lps REAL,
    pump_total_liters REAL,
    reserve_1 REAL
);

CREATE TABLE IF NOT EXISTS system_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc INTEGER NOT NULL,
    level TEXT NOT NULL,
    event_code TEXT NOT NULL,
    message TEXT,
    details_json TEXT
);

CREATE TABLE IF NOT EXISTS usb_export_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc INTEGER NOT NULL,
    usb_label TEXT,
    usb_mount_path TEXT,
    export_type TEXT NOT NULL,
    range_start_utc INTEGER NOT NULL,
    range_end_utc INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT
);

CREATE TABLE IF NOT EXISTS smart_counters (
    counter_key TEXT PRIMARY KEY,
    minutes REAL NOT NULL DEFAULT 0,
    updated_utc INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_board_log_time ON board_log(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_work_log_time ON work_log(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_system_log_time ON system_log(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_system_log_code ON system_log(event_code);
CREATE INDEX IF NOT EXISTS idx_usb_export_time ON usb_export_log(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_usb_export_range ON usb_export_log(export_type, range_start_utc, range_end_utc);
