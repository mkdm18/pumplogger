import csv, json, sqlite3, subprocess, time, os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from config import DB_PATH, USB_MOUNT_POINT, TIMEZONE_OFFSET_MINUTES

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)
def find_usb_partition():
    """
    Ищем реальную флешку:
    - removable device RM=1
    - поддерживаем флешки с разделом: /dev/sdb1
    - поддерживаем флешки без раздела: /dev/sdb
    - исключаем системные разделы
    """
    cmd = ["lsblk", "-J", "-o", "NAME,PATH,RM,MOUNTPOINT,FSTYPE,TYPE"]
    res = run_cmd(cmd)
    if res.returncode != 0:
        return None

    data = json.loads(res.stdout)

    for dev in data.get("blockdevices", []):
        if dev.get("rm") != True:
            continue

        dev_path = dev.get("path")
        dev_mountpoint = dev.get("mountpoint")
        dev_fstype = dev.get("fstype")

        # 1. Сначала ищем разделы типа /dev/sdb1
        for part in dev.get("children", []) or []:
            path = part.get("path")
            mountpoint = part.get("mountpoint")
            fstype = part.get("fstype")

            if not path or not fstype:
                continue

            if mountpoint in ("/", "/boot", "/boot/firmware"):
                continue

            return path

        # 2. Если разделов нет, но сама флешка имеет файловую систему
        # например /dev/sdb с exfat/vfat прямо на диске
        if dev_path and dev_fstype:
            if dev_mountpoint not in ("/", "/boot", "/boot/firmware"):
                return dev_path

    return None

def ensure_mount_point():
    Path(USB_MOUNT_POINT).mkdir(parents=True, exist_ok=True)

def is_mounted(mount_point: str) -> bool:
    with open("/proc/mounts", "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == mount_point:
                return True
    return False

def mount_usb_partition(dev_path: str, mount_point: str) -> bool:
    ensure_mount_point()

    if is_mounted(mount_point):
        return True

    # uid/gid пользователя omega, чтобы сервис мог писать на vfat/exfat/ntfs
    uid = os.getuid()
    gid = os.getgid()

    mount_options = f"uid={uid},gid={gid},umask=002"

    res = run_cmd(["mount", "-o", mount_options, dev_path, mount_point])

    if res.returncode == 0:
        return True

    # fallback для ext4 или других ФС, где uid/gid mount options не поддерживаются
    res = run_cmd(["mount", dev_path, mount_point])
    return res.returncode == 0

def unmount_usb(mount_point: str) -> bool:
    if not is_mounted(mount_point):
        return True
    return run_cmd(["umount", mount_point]).returncode == 0

def is_writable_dir(path: str) -> bool:
    try:
        test_file = Path(path) / ".write_test"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False

def read_export_days(mount_point: str, default_days: int = 2) -> int:
    cfg = Path(mount_point) / "export.txt"
    if not cfg.exists():
        return default_days
    try:
        text = cfg.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("days="):
                return max(1, int(line.split("=", 1)[1].strip()))
    except Exception:
        pass
    return default_days

def utc_to_local_str(ts_utc: int) -> str:
    dt_utc = datetime.fromtimestamp(ts_utc, tz=timezone.utc)
    return (dt_utc + timedelta(minutes=TIMEZONE_OFFSET_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")

def ensure_export_dirs(mount_point: str):
    board_dir = Path(mount_point) / "EXPORT" / "BOARD"
    work_dir = Path(mount_point) / "EXPORT" / "WORK"
    board_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    return board_dir, work_dir

def export_board_logs(conn, board_dir: Path, start_utc: int, end_utc: int):
    rows = conn.execute("SELECT * FROM board_log WHERE timestamp_utc >= ? AND timestamp_utc < ? ORDER BY timestamp_utc", (start_utc, end_utc)).fetchall()
    grouped = {}
    for row in rows:
        local_date = utc_to_local_str(row["timestamp_utc"]).split(" ")[0]
        grouped.setdefault(local_date, []).append(row)
    for day, items in grouped.items():
        out_file = board_dir / f"{day}.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["timestamp_utc","timestamp_local","manifold_pressure_mpa","mech_oil_pressure_kpa","mech_oil_temp_c","hydraulic_oil_temp_c","transmission_oil_temp_c","transmission_oil_pressure_kpa","engine_hours_total","transmission_hours_total"])
            for r in items:
                wr.writerow([r["timestamp_utc"], utc_to_local_str(r["timestamp_utc"]), r["manifold_pressure_mpa"], r["mech_oil_pressure_kpa"], r["mech_oil_temp_c"], r["hydraulic_oil_temp_c"], r["transmission_oil_temp_c"], r["transmission_oil_pressure_kpa"], r["engine_hours_total"], r["transmission_hours_total"]])

def export_work_logs(conn, work_dir: Path, start_utc: int, end_utc: int):
    rows = conn.execute("SELECT * FROM work_log WHERE timestamp_utc >= ? AND timestamp_utc < ? ORDER BY timestamp_utc", (start_utc, end_utc)).fetchall()
    grouped = {}
    for row in rows:
        dt_local = utc_to_local_str(row["timestamp_utc"])
        day, hhmmss = dt_local.split(" ")
        slot = "00-12" if int(hhmmss[:2]) < 12 else "12-24"
        grouped.setdefault((day, slot), []).append(row)
    for (day, slot), items in grouped.items():
        out_file = work_dir / f"{day}_{slot}.csv"
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["timestamp_utc","timestamp_local","manifold_pressure_mpa","pump_rpm","pump_flow_lps","pump_total_liters"])
            for r in items:
                wr.writerow([r["timestamp_utc"], utc_to_local_str(r["timestamp_utc"]), r["manifold_pressure_mpa"], r["pump_rpm"], r["pump_flow_lps"], r["pump_total_liters"]])

def perform_usb_export(days: int):
    now_utc = int(time.time())
    start_utc = now_utc - days * 86400
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        board_dir, work_dir = ensure_export_dirs(USB_MOUNT_POINT)
        export_board_logs(conn, board_dir, start_utc, now_utc)
        export_work_logs(conn, work_dir, start_utc, now_utc)
    finally:
        conn.close()
