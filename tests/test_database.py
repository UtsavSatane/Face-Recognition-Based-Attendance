import os
import pytest
import sqlite3
from datetime import datetime
from src.database import (
    init_db, add_user, get_user_by_name, log_attendance,
    get_attendance_today, get_all_users, delete_user
)

TEST_DB_PATH = "data/test_attendance.db"

@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Sets up a clean test database before each test and tears it down afterwards."""
    # Ensure any previous test database is removed
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
        
    # Initialize the test schema
    init_db(TEST_DB_PATH)
    
    yield
    
    # Clean up test database
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass # Handle Windows file locking during teardown if necessary

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
    
    conn.close()

def test_add_and_get_user():
    """Tests registering new users and retrieving their records."""
    # Register user
    user_id = add_user("Alice Smith", TEST_DB_PATH)
    assert user_id > 0
    
    # Retrieve user
    user = get_user_by_name("Alice Smith", TEST_DB_PATH)
    assert user is not None
    assert user["name"] == "Alice Smith"
    assert user["id"] == user_id

    # Test duplicate username restriction
    with pytest.raises(ValueError, match="already registered"):
        add_user("Alice Smith", TEST_DB_PATH)

def test_get_nonexistent_user():
    """Tests retrieval of an unregistered user returns None."""
    user = get_user_by_name("Bob Jones", TEST_DB_PATH)
    assert user is None

def test_log_and_fetch_attendance():
    """Tests logging attendance entries and querying them."""
    user_id = add_user("Charlie Brown", TEST_DB_PATH)
    
    # Log attendance
    log_id = log_attendance(user_id, "Blink Only", TEST_DB_PATH)
    assert log_id > 0
    
    # Fetch today's logs
    logs = get_attendance_today(TEST_DB_PATH)
    assert len(logs) == 1
    assert logs[0]["name"] == "Charlie Brown"
    assert logs[0]["liveness_method"] == "Blink Only"

def test_get_all_users():
    """Tests retrieving a list of all enrolled users in alphabetical order."""
    add_user("Zack", TEST_DB_PATH)
    add_user("Aaron", TEST_DB_PATH)
    
    users = get_all_users(TEST_DB_PATH)
    assert len(users) == 2
    assert users[0]["name"] == "Aaron"
    assert users[1]["name"] == "Zack"

def test_delete_user():
    """Tests deleting users and cascading delete verification."""
    user_id = add_user("David Miller", TEST_DB_PATH)
    log_attendance(user_id, "None", TEST_DB_PATH)
    
    # Verify user exists
    assert get_user_by_name("David Miller", TEST_DB_PATH) is not None
    assert len(get_attendance_today(TEST_DB_PATH)) == 1
    
    # Delete user
    delete_user(user_id, TEST_DB_PATH)
    
    # Verify user and cascade logs are removed
    assert get_user_by_name("David Miller", TEST_DB_PATH) is None
    assert len(get_attendance_today(TEST_DB_PATH)) == 0
