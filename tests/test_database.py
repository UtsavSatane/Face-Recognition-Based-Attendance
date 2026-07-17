import os
import pytest
import sqlite3
from datetime import datetime
from src.database import (
    init_db, add_user, get_user_by_name, log_attendance,
    get_attendance_today, get_all_users, delete_user,
    authenticate_user, get_user_by_login_id, get_last_attendance,
    get_setting, update_setting, get_student_attendance_history
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


