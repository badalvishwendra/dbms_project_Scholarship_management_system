"""SQLite database utilities shared by the FastAPI routes."""
import decimal
import os
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

# Re-export standard SQLite exceptions
from sqlite3 import (
    DatabaseError,
    DataError,
    Error,
    IntegrityError,
    InterfaceError,
    InternalError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
)

# Backward-compatibility alias
MySQLError = DatabaseError

# Load environment variables from .env if python-dotenv is available
ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DEFAULT_DATABASE_PATH = ROOT / "storage" / "scholarships.db"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


def get_db_path() -> Path:
    """Resolve the SQLite database file path from environment variables or default."""
    raw_path = os.environ.get("DATABASE_PATH") or os.environ.get("SQLITE_PATH")
    if not raw_path:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            if db_url.startswith("sqlite:////"):
                raw_path = "/" + db_url[11:]
            elif db_url.startswith("sqlite:///"):
                raw_path = db_url[10:]
            elif db_url.startswith("sqlite://"):
                raw_path = db_url[9:]

    if raw_path:
        if raw_path == ":memory:":
            return Path(":memory:")
        custom_path = Path(raw_path)
        return custom_path if custom_path.is_absolute() else (ROOT / custom_path)

    return DEFAULT_DATABASE_PATH


def get_db_config() -> Dict[str, Any]:
    """Return database configuration details for introspection and diagnostics."""
    path = get_db_path()
    return {
        "engine": "sqlite",
        "database": str(path),
        "is_memory": str(path) == ":memory:",
    }


def _convert_val(val: Any) -> Any:
    """Normalize types (Decimal -> float/int, date/datetime -> str) to match API conventions."""
    if isinstance(val, decimal.Decimal):
        return float(val) if val % 1 != 0 else int(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val


class Row(dict):
    """A dictionary subclass that also allows integer indexing and attribute access.

    Compatible with sqlite3.Row, tuple indexing, and dict() conversion.
    """

    def __init__(self, keys: List[str], values: Union[Tuple, List]):
        self._keys = list(keys)
        self._values = [_convert_val(v) for v in values]
        super().__init__(zip(self._keys, self._values))

    def __getitem__(self, item: Union[int, str, slice]) -> Any:
        if isinstance(item, (int, slice)):
            return self._values[item]
        return super().__getitem__(item)

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        raise AttributeError(f"'Row' object has no attribute '{name}'")

    def keys(self):
        return self._keys

    def values(self):
        return self._values

    def items(self):
        return [(k, self[k]) for k in self._keys]


def row_factory(cursor: sqlite3.Cursor, row: Tuple) -> Row:
    """SQLite row factory producing dictionary-like Row objects with attribute access."""
    col_names = [desc[0] for desc in cursor.description]
    return Row(col_names, row)


def get_db(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Open a short-lived SQLite connection with foreign keys enabled."""
    if db_path is None:
        target_path = get_db_path()
    elif isinstance(db_path, str) and db_path != ":memory:":
        target_path = Path(db_path) if Path(db_path).is_absolute() else (ROOT / db_path)
    else:
        target_path = db_path

    is_memory = str(target_path) == ":memory:"

    if not is_memory and isinstance(target_path, Path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(target_path), timeout=30.0, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.Error:
            pass
    else:
        conn = sqlite3.connect(":memory:", timeout=30.0, check_same_thread=False)

    conn.row_factory = row_factory
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialise_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Create schema and demonstration records on first startup if tables are empty."""
    conn = get_db(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        count_cursor = conn.execute("SELECT COUNT(*) FROM students")
        row = count_cursor.fetchone()
        if row and row[0] == 0:
            conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def reset_database(db_path: Optional[Union[str, Path]] = None) -> None:
    """Drop tables or reset the database file and recreate schema with seed data."""
    if db_path is None:
        target = get_db_path()
    elif isinstance(db_path, str) and db_path != ":memory:":
        target = Path(db_path) if Path(db_path).is_absolute() else (ROOT / db_path)
    else:
        target = db_path

    is_memory = str(target) == ":memory:"

    if not is_memory and isinstance(target, Path) and target.exists():
        try:
            target.unlink()
            wal = Path(str(target) + "-wal")
            shm = Path(str(target) + "-shm")
            if wal.exists():
                wal.unlink(missing_ok=True)
            if shm.exists():
                shm.unlink(missing_ok=True)
        except Exception:
            pass

    conn = get_db(target)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("DROP TABLE IF EXISTS disbursements;")
        conn.execute("DROP TABLE IF EXISTS applications;")
        conn.execute("DROP TABLE IF EXISTS scholarships;")
        conn.execute("DROP TABLE IF EXISTS students;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
    finally:
        conn.close()

    initialise_database(target)
