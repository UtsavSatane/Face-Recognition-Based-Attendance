import os
import pytest
import sqlite3
from datetime import datetime
from src.database import (
    init_db, add_user, get_user_by_name, log_attendance,
    get_attendance_today, get_all_users, delete_user,
    authenticate_user, get_user_by_login_id, get_last_attendance,
    get_setting, update_setting, get_student_attendance_history,
    create_reset_request, get_reset_requests, update_reset_request_status,
    verify_and_reset_password
)

TEST_DB_PATH = "data/test_attendance.db"

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Sets up a clean test database before each test and tears it down afterwards."""
    import shutil
    # Ensure any previous test database is removed
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    # Ensure previous test classrooms are removed
    if os.path.exists("data/test_classrooms"):
        try:
            shutil.rmtree("data/test_classrooms")
        except Exception:
            pass
        
    # Initialize the test schema
    init_db(TEST_DB_PATH)
    
    yield
    
    # Clean up test database
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass # Handle Windows file locking during teardown if necessary
            
    # Clean up test classrooms
    if os.path.exists("data/test_classrooms"):
        try:
            shutil.rmtree("data/test_classrooms")
        except Exception:
            pass

def test_database_initialization():
    """Verifies that the database files and tables are initialized correctly."""
    assert os.path.exists(TEST_DB_PATH)
    
    # Connect and check tables
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
    assert cursor.fetchone() is not None
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
    assert cursor.fetchone() is not None
    
    conn.close()

def test_add_and_get_user():
    """Tests registering new users and retrieving their records."""
    # Register user
    user_id = add_user("Alice Smith", "alicesmith", "password123", "student", TEST_DB_PATH)
    assert user_id > 0
    
    # Retrieve user by name
    user = get_user_by_name("Alice Smith", TEST_DB_PATH)
    assert user is not None
    assert user["name"] == "Alice Smith"
    assert user["login_id"] == "alicesmith"
    assert user["id"] == user_id

    # Retrieve user by login_id
    user2 = get_user_by_login_id("alicesmith", TEST_DB_PATH)
    assert user2 is not None
    assert user2["id"] == user_id

    # Test duplicate login ID restriction
    with pytest.raises(ValueError, match="already registered"):
        add_user("Alice Double", "alicesmith", "anotherpwd", "student", TEST_DB_PATH)

def test_authenticate_user():
    """Tests authenticating a user with correct and incorrect credentials."""
    add_user("Bob Jones", "bobjones", "mysecret123", "student", TEST_DB_PATH)
    
    # Successful authentication
    user = authenticate_user("bobjones", "mysecret123", TEST_DB_PATH)
    assert user is not None
    assert user["name"] == "Bob Jones"
    assert user["role"] == "student"

    # Unsuccessful authentication (wrong password)
    assert authenticate_user("bobjones", "wrongpwd", TEST_DB_PATH) is None
    
    # Unsuccessful authentication (wrong login id)
    assert authenticate_user("nonexistent", "mysecret123", TEST_DB_PATH) is None

def test_get_nonexistent_user():
    """Tests retrieval of an unregistered user returns None."""
    user = get_user_by_name("Bob Jones", TEST_DB_PATH)
    assert user is None

def test_log_and_fetch_attendance():
    """Tests logging attendance entries and querying them."""
    user_id = add_user("Charlie Brown", "charlie", "pwd1", "student", TEST_DB_PATH)
    
    # Log attendance
    log_id = log_attendance(user_id, "Blink Only", TEST_DB_PATH)
    assert log_id > 0
    
    # Fetch today's logs
    logs = get_attendance_today(TEST_DB_PATH)
    assert len(logs) == 1
    assert logs[0]["name"] == "Charlie Brown"
    assert logs[0]["liveness_method"] == "Blink Only"

    # Get last attendance timestamp
    last_time = get_last_attendance(user_id, TEST_DB_PATH)
    assert last_time is not None

def test_get_all_users():
    """Tests retrieving a list of all enrolled users in alphabetical order."""
    add_user("Zack", "zack", "pwd", "student", TEST_DB_PATH)
    add_user("Aaron", "aaron", "pwd", "student", TEST_DB_PATH)
    
    users = get_all_users(TEST_DB_PATH)
    assert len(users) == 2
    assert users[0]["name"] == "Aaron"
    assert users[1]["name"] == "Zack"

def test_delete_user():
    """Tests deleting users and cascading delete verification."""
    user_id = add_user("David Miller", "david", "pwd", "student", TEST_DB_PATH)
    log_attendance(user_id, "None", TEST_DB_PATH)
    
    # Verify user exists
    assert get_user_by_name("David Miller", TEST_DB_PATH) is not None
    assert len(get_attendance_today(TEST_DB_PATH)) == 1
    
    # Delete user
    delete_user(user_id, TEST_DB_PATH)
    
    # Verify user and cascade logs are removed
    assert get_user_by_name("David Miller", TEST_DB_PATH) is None
    assert len(get_attendance_today(TEST_DB_PATH)) == 0

def test_settings_persistence():
    """Tests setting and getting custom configuration key-value pairs."""
    # Test getting seeded setting
    val = get_setting("similarity_threshold", "0.6", TEST_DB_PATH)
    assert val == "0.5" # Seeded in init_db

    # Update setting
    update_setting("similarity_threshold", "0.7", TEST_DB_PATH)
    val = get_setting("similarity_threshold", "0.6", TEST_DB_PATH)
    assert val == "0.7"

    # Nonexistent setting returns default
    assert get_setting("nonexistent_key", "default_val", TEST_DB_PATH) == "default_val"

def test_get_student_attendance_history():
    """Tests retrieving attendance history for a specific student."""
    user_id = add_user("Ethan Hunt", "ethan", "imf123", "student", TEST_DB_PATH)
    
    # Initially history is empty
    history = get_student_attendance_history(user_id, TEST_DB_PATH)
    assert len(history) == 0
    
    # Log two entries
    log_attendance(user_id, "Blink Only", TEST_DB_PATH)
    log_attendance(user_id, "Blink & Head Turn", TEST_DB_PATH)
    
    # Fetch history and verify entries
    history = get_student_attendance_history(user_id, TEST_DB_PATH)
    assert len(history) == 2
    assert history[0]["liveness_method"] == "Blink & Head Turn" # Latest first
    assert history[1]["liveness_method"] == "Blink Only"

def test_classroom_attendance_logging():
    """Tests that logging attendance for a student with department and section correctly creates classroom folders and CSV files."""
    import shutil
    import csv
    
    # Add student with department and section
    user_id = add_user("Test Student", "teststudent", "pwd123", "student", TEST_DB_PATH, "Computer Science", "Section A")
    
    # Ensure folders do not exist yet
    test_classrooms_dir = "data/test_classrooms"
    if os.path.exists(test_classrooms_dir):
        shutil.rmtree(test_classrooms_dir)
        
    # Log attendance
    log_id = log_attendance(user_id, "Blink Only", TEST_DB_PATH)
    assert log_id > 0
    
    # Check folder creation
    expected_folder = os.path.join(test_classrooms_dir, "Computer Science_Section A")
    assert os.path.exists(expected_folder)
    
    # Check cumulative CSV
    cum_csv_path = os.path.join(expected_folder, "attendance.csv")
    assert os.path.exists(cum_csv_path)
    
    # Verify content of cumulative CSV
    with open(cum_csv_path, mode="r", newline="", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        assert len(reader) == 2 # Header + 1 row
        assert reader[0] == ["Timestamp", "Student ID", "Name", "Department", "Section", "Liveness Method"]
        assert reader[1][1] == "teststudent"
        assert reader[1][2] == "Test Student"
        assert reader[1][3] == "Computer Science"
        assert reader[1][4] == "Section A"
        assert reader[1][5] == "Blink Only"
        
    # Check daily CSV
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    daily_csv_path = os.path.join(expected_folder, f"attendance_{date_str}.csv")
    assert os.path.exists(daily_csv_path)

def test_password_reset_flow():
    """Tests the password reset request, rate limiting, approval, OTP expiration, and one-time use functionality."""
    # Register student and admin
    student_id = add_user("Utsav Satane", "001", "oldpwd", "student", TEST_DB_PATH)
    admin_id = add_user("Admin User", "testadmin", "admin123", "admin", TEST_DB_PATH)
    
    # 1. Create reset request
    req_id = create_reset_request("001", TEST_DB_PATH)
    assert req_id > 0
    
    # Verify it exists in pending requests
    requests = get_reset_requests(TEST_DB_PATH)
    assert len(requests) == 1
    assert requests[0]["student_name"] == "Utsav Satane"
    assert requests[0]["status"] == "PENDING"
    assert requests[0]["otp"] is None
    
    # 2. Test Rate Limiting (requesting again within 15 minutes fails)
    with pytest.raises(ValueError, match="once every 15 minutes"):
        create_reset_request("001", TEST_DB_PATH)
        
    # 3. Approve request with an OTP
    otp = "123456"
    update_reset_request_status(req_id, "APPROVED", admin_id, otp, TEST_DB_PATH)
    
    # Verify status changed and OTP is set
    requests = get_reset_requests(TEST_DB_PATH)
    assert requests[0]["status"] == "APPROVED"
    assert requests[0]["otp"] == "123456"
    assert requests[0]["admin_name"] == "Admin User"
    
    # 4. Test verify and reset (wrong OTP fails)
    success, msg = verify_and_reset_password("001", "wrongotp", "newpwd", TEST_DB_PATH)
    assert not success
    assert "Invalid OTP" in msg
    
    # Verify password hasn't changed (still old hash)
    assert authenticate_user("001", "oldpwd", TEST_DB_PATH) is not None
    assert authenticate_user("001", "newpwd", TEST_DB_PATH) is None
    
    # 5. Test verify and reset (correct OTP succeeds)
    success, msg = verify_and_reset_password("001", "123456", "newpwd", TEST_DB_PATH)
    assert success
    assert "successfully reset" in msg
    
    # Verify password updated and authenticates successfully
    assert authenticate_user("001", "oldpwd", TEST_DB_PATH) is None
    assert authenticate_user("001", "newpwd", TEST_DB_PATH) is not None
    
    # 6. Test One-Time Use (attempting to use OTP again fails)
    requests = get_reset_requests(TEST_DB_PATH)
    assert requests[0]["status"] == "COMPLETED"
    assert requests[0]["otp"] is None
    
    success, msg = verify_and_reset_password("001", "123456", "anotherpwd", TEST_DB_PATH)
    assert not success
    assert "Invalid OTP" in msg

def test_password_reset_otp_expiration():
    """Tests that reset OTPs cannot be used after the 15-minute expiration window."""
    student_id = add_user("Utsav Satane", "001", "oldpwd", "student", TEST_DB_PATH)
    admin_id = add_user("Admin User", "testadmin", "admin123", "admin", TEST_DB_PATH)
    
    req_id = create_reset_request("001", TEST_DB_PATH)
    
    # Approve request
    otp = "654321"
    update_reset_request_status(req_id, "APPROVED", admin_id, otp, TEST_DB_PATH)
    
    # Simulate expiration by manually setting approved_at to 20 minutes ago
    import sqlite3
    from datetime import timedelta
    from src.database import get_ist_now
    expired_time = (get_ist_now() - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE password_resets SET approved_at = ? WHERE id = ?", (expired_time, req_id))
    conn.commit()
    conn.close()
    
    # Verify and reset should fail due to expiration
    success, msg = verify_and_reset_password("001", "654321", "newpwd", TEST_DB_PATH)
    assert not success
    assert "expired" in msg.lower()
    
    # Check that status changed to EXPIRED
    requests = get_reset_requests(TEST_DB_PATH)
    assert requests[0]["status"] == "EXPIRED"
    assert requests[0]["otp"] is None


def test_get_all_users_filtered():
    """Tests retrieving a filtered list of users based on department and section."""
    add_user("Alice", "alice", "pwd", "student", TEST_DB_PATH, "CSE", "A")
    add_user("Bob", "bob", "pwd", "student", TEST_DB_PATH, "CSE", "B")
    add_user("Charlie", "charlie", "pwd", "student", TEST_DB_PATH, "ECE", "A")
    
    # 1. Filter by Department CSE
    cse_users = get_all_users(TEST_DB_PATH, department="CSE")
    assert len(cse_users) == 2
    assert cse_users[0]["name"] == "Alice"
    assert cse_users[1]["name"] == "Bob"
    
    # 2. Filter by Section A
    sec_a_users = get_all_users(TEST_DB_PATH, section="A")
    assert len(sec_a_users) == 2
    assert sec_a_users[0]["name"] == "Alice"
    assert sec_a_users[1]["name"] == "Charlie"
    
    # 3. Filter by CSE and Section A
    cse_a_users = get_all_users(TEST_DB_PATH, department="CSE", section="A")
    assert len(cse_a_users) == 1
    assert cse_a_users[0]["name"] == "Alice"
    
    # 4. Filter by CSE and Section B
    cse_b_users = get_all_users(TEST_DB_PATH, department="CSE", section="B")
    assert len(cse_b_users) == 1
    assert cse_b_users[0]["name"] == "Bob"
    
    # 5. Non-existent filter
    none_users = get_all_users(TEST_DB_PATH, department="CE", section="C")
    assert len(none_users) == 0


def test_6_hour_attendance_interval_check():
    """Verifies that the 6-hour interval check correctly determines if a student can check in again."""
    from datetime import timedelta
    from src.database import get_ist_now
    
    user_id = add_user("Frank Castle", "frank", "pwd", "student", TEST_DB_PATH)
    
    # First check-in
    log_attendance(user_id, "Blink Only", TEST_DB_PATH)
    
    # Retrieve last attendance and check if less than 6 hours
    last_log = get_last_attendance(user_id, TEST_DB_PATH)
    assert last_log is not None
    
    now = get_ist_now()
    time_diff = now - last_log
    
    # Since it was logged just now, diff is less than 6 hours
    assert time_diff < timedelta(hours=6)
    
    # Simulate a log from 7 hours ago
    import sqlite3
    seven_hours_ago = (now - timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE attendance SET timestamp = ? WHERE user_id = ?", (seven_hours_ago, user_id))
    conn.commit()
    conn.close()
    
    # Fetch last log again
    last_log = get_last_attendance(user_id, TEST_DB_PATH)
    assert last_log is not None
    time_diff = get_ist_now() - last_log
    
    # Now it is more than 6 hours, so they should be able to log again
    assert time_diff >= timedelta(hours=6)



