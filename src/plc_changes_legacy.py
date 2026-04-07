import time
from datetime import datetime
from pathlib import Path
from plc import PLCReader

DB_LIST = [1, 2, 3, 4, 5, 6, 8, 9, 10, 17, 32, 33, 34]
OFFSETS = list(range(0, 100, 4))
OUT_PATH = Path("/opt/pump_station/plc_changes.csv")
POLL_INTERVAL_SEC = 1.0

def main():
    plc = PLCReader()
    plc.connect()
    print("Connected to PLC")
    last_values = {}
    with OUT_PATH.open("a", encoding="utf-8") as f:
        try:
            while True:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for db in DB_LIST:
                    for offset in OFFSETS:
                        try:
                            value = plc.read_real(db, offset)
                            key = (db, offset)
                            if key not in last_values or last_values[key] != value:
                                line = f"{ts},REAL,{db},{offset},{value}\n"
                                f.write(line); f.flush(); print(line.strip())
                                last_values[key] = value
                        except Exception:
                            continue
                time.sleep(POLL_INTERVAL_SEC)
        except KeyboardInterrupt:
            print("\nStopped by user")
        finally:
            plc.disconnect()

if __name__ == "__main__":
    main()
