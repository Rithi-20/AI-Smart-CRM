import os
import sqlite3
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.exists("/data") and os.access("/data", os.W_OK):
    DB_PATH = "/data/crm.db"
else:
    DB_PATH = os.path.join(BASE_DIR, "crm.db")

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def execute_write(query: str, params: tuple = ()):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def generate_next_id(table_name: str, prefix: str) -> str:
    rows = execute_query(f"SELECT id FROM {table_name}")
    existing_nums = []
    for r in rows:
        val = str(r["id"])
        if val.startswith(prefix):
            try:
                num = int(val.replace(prefix, ""))
                existing_nums.append(num)
            except ValueError:
                pass
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    return f"{prefix}{next_num:03d}"

def log_action(action_type: str, target_table: str, target_id: Any, after_value: Optional[str] = None, performed_by: str = "ai_agent") -> str:
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).isoformat()
    log_id = generate_next_id("action_log", "LOG")
    query = """
    INSERT INTO action_log (id, action_type, target_table, target_id, after_value, performed_by, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(query, (log_id, action_type, target_table, str(target_id), after_value, performed_by, timestamp))
    return log_id
