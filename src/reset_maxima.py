from db import Database

MAXIMA_DEFAULTS = {
    "max_manifold_pressure_mpa": 0.0,
    "max_mech_oil_pressure_kpa": 0.0,
    "max_mech_oil_temp_c": -999999.0,
    "max_hydraulic_oil_temp_c": -999999.0,
    "max_transmission_oil_temp_c": -999999.0,
    "max_transmission_oil_pressure_kpa": 0.0,
}

def main():
    db = Database()
    try:
        db.conn.execute("PRAGMA busy_timeout = 5000;")
        for key, value in MAXIMA_DEFAULTS.items():
            db.set_meta_real(key, value)
        db.insert_system_log("INFO", "MAXIMA_RESET", "Maxima reset")
        db.commit()
        print("Maxima reset completed.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
