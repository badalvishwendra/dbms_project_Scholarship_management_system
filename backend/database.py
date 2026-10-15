"""SQLite utilities shared by the FastAPI routes."""
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "storage" / "scholarships.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


def get_db() -> sqlite3.Connection:
    """Open a short-lived SQLite connection with foreign keys enabled."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_database() -> None:
    """Create schema and demonstration records on the first startup."""
    connection = get_db()
    connection.executescript(SCHEMA_PATH.read_text())
    if connection.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        connection.executescript(SEED_PATH.read_text())
    connection.commit()
    connection.close()
