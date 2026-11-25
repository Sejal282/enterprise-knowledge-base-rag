
from app.database import test_database_connection as run_database_check


def test_database_connection():
    """Verify that the database connection works."""
    result = run_database_check()
    assert result is not None


if __name__ == "__main__":
    try:
        result = run_database_check()
        print("Database connection successful!")
        print(f"Test query result: {result}")
    except Exception as e:
        print("Database connection failed!")
        print(f"Error: {e}")
