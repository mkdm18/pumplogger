from pathlib import Path
from config import DB_PATH, DATA_DIR, BASE_DIR
from db import Database

def initialize_database():
    Path(BASE_DIR).mkdir(parents=True, exist_ok=True)
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).parent / "schema.sql"
    db = Database(DB_PATH)
    try:
        db.execute_script(schema_path.read_text(encoding="utf-8"))
        db.ensure_default_meta()
    finally:
        db.close()
