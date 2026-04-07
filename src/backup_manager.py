import sqlite3
import time
from pathlib import Path
from config import DB_PATH, BACKUP_A_PATH, BACKUP_B_PATH

def backup_database_rotating(db):
    db.commit()
    last_slot = db.get_meta_text("last_backup_slot", "b")
    next_slot = "a" if last_slot == "b" else "b"
    target = BACKUP_A_PATH if next_slot == "a" else BACKUP_B_PATH
    tmp_target = Path(str(target) + ".tmp")

    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(tmp_target)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()

    tmp_target.replace(target)
    db.set_meta_text("last_backup_slot", next_slot)
    db.set_meta_int("last_backup_utc", int(time.time()))
