from datetime import datetime, timedelta, timezone
import subprocess
from mv210 import MV210Client

OWEN_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)

def read_owen_utc_datetime() -> datetime:
    mv = MV210Client()
    mv.connect()
    try:
        raw_seconds = mv.read_u32(61568)
        return OWEN_EPOCH + timedelta(seconds=raw_seconds)
    finally:
        mv.disconnect()

def sync_time_from_owen():
    dt_utc = read_owen_utc_datetime()
    dt_str = dt_utc.strftime("%Y-%m-%d %H:%M:%S")
    subprocess.run(["timedatectl", "set-ntp", "false"], check=False)
    subprocess.run(["date", "-u", "-s", dt_str], check=True)
