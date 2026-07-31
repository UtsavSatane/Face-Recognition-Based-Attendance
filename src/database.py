import os
import sqlite3
import hashlib
from datetime import datetime, timezone, timedelta

def get_ist_now() -> datetime:
    """Returns a naive datetime object representing the current Indian Standard Time (IST)."""
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(tzinfo=None)

def hash_password(password: str) -> str:
    """Computes the SHA-256 hash of a password."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db_connection(db_path: str = "data/attendance.db") -> sqlite3.Connection:
    """Connects to the SQLite database, creating parent folders if necessary."""
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = "data/attendance.db") -> None:
    """Initializes the database schema with support for logins, credentials, and settings."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Check if users table exists and if it has the new column 'login_id'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    users_exists = cursor.fetchone() is not None
    
    needs_migration = False
    migrated_users = []
    
    if users_exists:
        cursor.execute("PRAGMA table_info(users)")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'login_id' not in columns:
            needs_migration = True
            # Read old users
            cursor.execute("SELECT id, name, created_at FROM users")
            migrated_users = [dict(row) for row in cursor.fetchall()]
            
            # Drop old tables to handle foreign keys cleanly
            cursor.execute("DROP TABLE IF EXISTS attendance")
            cursor.execute("DROP TABLE IF EXISTS users")
            conn.commit()
            
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            login_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            department TEXT,
            section TEXT,
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
    
    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Create password_resets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            otp TEXT,
            created_at TIMESTAMP,
            approved_at TIMESTAMP,
            admin_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    # Ensure department and section columns exist in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    if 'department' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT")
    if 'section' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN section TEXT")
        
    conn.commit()
    
    # If migration is needed, insert migrated users
    if needs_migration:
        for u in migrated_users:
            login_id = "".join(c for c in u['name'].lower() if c.isalnum()).strip()
            if not login_id:
                login_id = f"student_{u['id']}"
            hashed_pwd = hash_password("student123")
            cursor.execute(
                "INSERT INTO users (id, name, login_id, password, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (u['id'], u['name'], login_id, hashed_pwd, 'student', u['created_at'])
            )
        conn.commit()
        
    # Seed default admin if not exists
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if not cursor.fetchone():
        admin_login = "admin"
        admin_hash = hash_password("admin123")
        created_at = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (name, login_id, password, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ("Administrator", admin_login, admin_hash, "admin", created_at)
        )
        conn.commit()
        
    # Seed default settings if not exists
    cursor.execute("SELECT value FROM settings WHERE key = 'similarity_threshold'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('similarity_threshold', '0.5')")
    cursor.execute("SELECT value FROM settings WHERE key = 'liveness_mode'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('liveness_mode', 'Blink & Head Turn')")
        
    conn.commit()
    conn.close()

def add_user(name: str, login_id: str, password: str, role: str = 'student', db_path: str = "data/attendance.db", department: str = None, section: str = None) -> int:
    """Registers a new user (student/admin) in the database. Returns the new user's ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        created_at = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
        hashed_password = hash_password(password)
        cursor.execute(
            "INSERT INTO users (name, login_id, password, role, department, section, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name.strip(), login_id.strip().lower(), hashed_password, role,
             department.strip() if department else None,
             section.strip() if section else None, created_at)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except sqlite3.IntegrityError:
        raise ValueError(f"Login ID '{login_id}' is already registered.")
    finally:
        conn.close()

def authenticate_user(login_id: str, password: str, db_path: str = "data/attendance.db") -> dict | None:
    """Authenticates a user and returns their user profile dictionary if successful."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    hashed_pwd = hash_password(password)
    cursor.execute(
        "SELECT id, name, login_id, role, department, section, created_at FROM users WHERE login_id = ? AND password = ?",
        (login_id.strip().lower(), hashed_pwd)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_name(name: str, db_path: str = "data/attendance.db") -> dict | None:
    """Retrieves a user by their name."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, login_id, role, department, section, created_at FROM users WHERE name = ?", (name.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_login_id(login_id: str, db_path: str = "data/attendance.db") -> dict | None:
    """Retrieves a user by their login ID."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, login_id, role, department, section, created_at FROM users WHERE login_id = ?", (login_id.strip().lower(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def log_attendance(user_id: int, liveness_method: str, db_path: str = "data/attendance.db") -> int:
    """Logs a successful attendance entry for a user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    timestamp_dt = get_ist_now()
    timestamp = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO attendance (user_id, liveness_method, timestamp) VALUES (?, ?, ?)",
        (user_id, liveness_method, timestamp)
    )
    conn.commit()
    log_id = cursor.lastrowid
    
    # Get user details for classroom folder logging
    cursor.execute("SELECT name, login_id, role, department, section FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        user = dict(user_row)
        # Check if the user is a student and has department & section set
        if user['role'] == 'student' and user.get('department') and user.get('section'):
            import csv
            # Sanitize names for folder paths
            dept_sanitized = "".join(c for c in user['department'] if c.isalnum() or c in (' ', '_', '-')).strip()
            sec_sanitized = "".join(c for c in user['section'] if c.isalnum() or c in (' ', '_', '-')).strip()
            if dept_sanitized and sec_sanitized:
                # Use a different folder for tests to keep test output isolated
                if "test_" in os.path.basename(db_path):
                    classrooms_base = "data/test_classrooms"
                else:
                    classrooms_base = "classrooms"
                classroom_folder = os.path.join(classrooms_base, f"{dept_sanitized}_{sec_sanitized}")
                os.makedirs(classroom_folder, exist_ok=True)
                
                # Append to cumulative attendance file
                cumulative_csv = os.path.join(classroom_folder, "attendance.csv")
                file_exists = os.path.exists(cumulative_csv)
                try:
                    with open(cumulative_csv, mode="a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        if not file_exists:
                            writer.writerow(["Timestamp", "Student ID", "Name", "Department", "Section", "Liveness Method"])
                        writer.writerow([timestamp, user['login_id'], user['name'], user['department'], user['section'], liveness_method])
                except Exception as e:
                    print(f"Error logging classroom cumulative attendance: {e}")
                
                # Append to daily attendance file
                date_str = timestamp_dt.strftime("%Y-%m-%d")
                daily_csv = os.path.join(classroom_folder, f"attendance_{date_str}.csv")
                daily_exists = os.path.exists(daily_csv)
                try:
                    with open(daily_csv, mode="a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        if not daily_exists:
                            writer.writerow(["Timestamp", "Student ID", "Name", "Department", "Section", "Liveness Method"])
                        writer.writerow([timestamp, user['login_id'], user['name'], user['department'], user['section'], liveness_method])
                except Exception as e:
                    print(f"Error logging classroom daily attendance: {e}")
                    
    return log_id

def get_last_attendance(user_id: int, db_path: str = "data/attendance.db") -> datetime | None:
    """Retrieves the timestamp of the last logged attendance for the user."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp FROM attendance WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
    return None

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
    """Retrieves all registered users (usually filters to role='student' or sorted name)."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, login_id, role, department, section, created_at FROM users WHERE role = 'student' ORDER BY name ASC")
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

def get_setting(key: str, default_value: str, db_path: str = "data/attendance.db") -> str:
    """Gets the value of a setting from the database."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row['value']
    return default_value

def update_setting(key: str, value: str, db_path: str = "data/attendance.db") -> None:
    """Updates or sets the value of a setting."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, str(value))
    )
    conn.commit()
    conn.close()

def get_student_attendance_history(user_id: int, db_path: str = "data/attendance.db") -> list:
    """Retrieves all attendance records for a specific student, sorted by latest first."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, liveness_method
        FROM attendance
        WHERE user_id = ?
        ORDER BY timestamp DESC, id DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_reset_request(login_id: str, db_path: str = "data/attendance.db") -> int:
    """Creates a pending password reset request for the student. Enforces rate-limiting."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        # Find user
        cursor.execute("SELECT id FROM users WHERE login_id = ? AND role = 'student'", (login_id.strip().lower(),))
        user_row = cursor.fetchone()
        if not user_row:
            raise ValueError(f"Student ID '{login_id}' is not registered.")
            
        user_id = user_row['id']
        now_str = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check last reset request for rate limiting (15 minutes cooldown)
        cursor.execute(
            "SELECT created_at FROM password_resets WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        last_req = cursor.fetchone()
        if last_req:
            last_time = datetime.strptime(last_req['created_at'], "%Y-%m-%d %H:%M:%S")
            if get_ist_now() - last_time < timedelta(minutes=15):
                # Calculate remaining cooldown time
                remaining_sec = 15 * 60 - int((get_ist_now() - last_time).total_seconds())
                remaining_min = int(remaining_sec / 60) + (1 if remaining_sec % 60 > 0 else 0)
                raise ValueError(f"You can only request a password reset once every 15 minutes. Please try again in {remaining_min} minute(s).")
                
        # Insert request
        cursor.execute(
            "INSERT INTO password_resets (user_id, status, created_at) VALUES (?, 'PENDING', ?)",
            (user_id, now_str)
        )
        conn.commit()
        req_id = cursor.lastrowid
        return req_id
    finally:
        conn.close()

def get_reset_requests(db_path: str = "data/attendance.db") -> list:
    """Retrieves all reset requests with student and auditing admin details."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.id, pr.status, pr.otp, pr.created_at, pr.approved_at,
               u.name AS student_name, u.login_id AS student_login_id,
               adm.name AS admin_name, adm.login_id AS admin_login_id
        FROM password_resets pr
        JOIN users u ON pr.user_id = u.id
        LEFT JOIN users adm ON pr.admin_id = adm.id
        ORDER BY pr.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_reset_request_status(request_id: int, status: str, admin_id: int, otp: str = None, db_path: str = "data/attendance.db") -> None:
    """Updates the status and logs the auditing admin for a password reset request."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        now_str = get_ist_now().strftime("%Y-%m-%d %H:%M:%S") if status == 'APPROVED' else None
        cursor.execute("""
            UPDATE password_resets
            SET status = ?, admin_id = ?, otp = ?, approved_at = ?
            WHERE id = ?
        """, (status, admin_id, otp, now_str, request_id))
        conn.commit()
    finally:
        conn.close()

def verify_and_reset_password(login_id: str, otp: str, new_password: str, db_path: str = "data/attendance.db") -> tuple[bool, str]:
    """Verifies the reset OTP and resets the student's password. Enforces expiration and single-use."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        # Find approved request with matching OTP for this student
        cursor.execute("""
            SELECT pr.id, pr.approved_at, pr.user_id
            FROM password_resets pr
            JOIN users u ON pr.user_id = u.id
            WHERE u.login_id = ? AND pr.status = 'APPROVED' AND pr.otp = ?
            ORDER BY pr.created_at DESC LIMIT 1
        """, (login_id.strip().lower(), otp.strip()))
        row = cursor.fetchone()
        
        if not row:
            return False, "Invalid OTP or Student ID, or request is not approved yet."
            
        req_id = row['id']
        user_id = row['user_id']
        approved_time = datetime.strptime(row['approved_at'], "%Y-%m-%d %H:%M:%S")
        
        # Check for 15-minute token expiration
        if get_ist_now() - approved_time > timedelta(minutes=15):
            # Invalidate request as expired
            cursor.execute("UPDATE password_resets SET status = 'EXPIRED', otp = NULL WHERE id = ?", (req_id,))
            conn.commit()
            return False, "The OTP has expired (15-minute validity). Please request a new password reset."
            
        # Valid request! Execute reset and set status to COMPLETED (clearing OTP to prevent reuse)
        hashed_password = hash_password(new_password)
        cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
        cursor.execute("UPDATE password_resets SET status = 'COMPLETED', otp = NULL WHERE id = ?", (req_id,))
        conn.commit()
        return True, "Password successfully reset! You can now log in."
    finally:
        conn.close()


