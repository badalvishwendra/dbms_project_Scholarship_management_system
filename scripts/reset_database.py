"""Reset MySQL database tables and re-populate demonstration records."""
import sys
from pathlib import Path

# Add project root to sys.path so backend imports work
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database import reset_database

if __name__ == "__main__":
    print("Resetting Scholarship Management System MySQL database...")
    try:
        reset_database()
        print("Database reset successfully with fresh demo records.")
    except Exception as exc:
        print(f"Error resetting database: {exc}")
        sys.exit(1)
