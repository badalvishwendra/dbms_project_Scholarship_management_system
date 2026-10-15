"""Small SQLite helper functions used by the Flask routes."""
from pathlib import Path
import sqlite3
from flask import g

ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT / "storage" / "scholarships.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


def get_db():
    """Return one database connection per request."""
    if "db" not in g:
        DATABASE_PATH.parent.mkdir(exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialise_database():
    """Create the database and add readable demo records on first run."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA_PATH.read_text())
    has_data = connection.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    if has_data == 0:
        connection.executescript(SEED_PATH.read_text())
    connection.commit()
    connection.close()
