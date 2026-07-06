import os
import sqlite3
from datetime import datetime, timezone, timedelta

def get_ist_now() -> datetime:
    """Returns a naive datetime object representing the current Indian Standard Time (IST)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(tzinfo=None)


def get_db_connection(db_path: str = "data/attendance.db") -> sqlite3.Connection:
    """Connects to the SQLite database, creating parent folders if necessary."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = "data/attendance.db") -> None:
    """Initializes the database schema."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create attendance table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            liveness_method TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(name: str, db_path: str = "data/attendance.db") -> int:
    """Registers a new user in the database. Returns the new user's ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        created_at = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO users (name, created_at) VALUES (?, ?)", (name.strip(), created_at))
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError(f"User '{name}' is already registered.")
    finally:
        conn.close()

def get_user_by_name(name: str, db_path: str = "data/attendance.db") -> dict | None:
    """Retrieves a user by their name."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM users WHERE name = ?", (name.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def log_attendance(user_id: int, liveness_method: str, db_path: str = "data/attendance.db") -> int:
    """Logs a successful attendance entry for a user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    timestamp = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO attendance (user_id, liveness_method, timestamp) VALUES (?, ?, ?)",
        (user_id, liveness_method, timestamp)
    )
    conn.commit()
    log_id = cursor.lastrowid
    conn.close()
    return log_id

def get_attendance_today(db_path: str = "data/attendance.db") -> list:
    """Retrieves all attendance logs recorded today."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    # Get today's date in IST from Python
    ist_today = get_ist_now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT a.id, u.name, a.timestamp, a.liveness_method
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE date(a.timestamp) = ?
        ORDER BY a.timestamp DESC
    """, (ist_today,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_users(db_path: str = "data/attendance.db") -> list:
    """Retrieves all registered users."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM users ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_user(user_id: int, db_path: str = "data/attendance.db") -> None:
    """Deletes a user and their cascading attendance logs."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
