"""MySQL database utilities shared by the FastAPI routes."""
import decimal
import os
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote, urlparse

import pymysql
from pymysql.err import (
    DatabaseError,
    DataError,
    IntegrityError,
    InterfaceError,
    InternalError,
    MySQLError,
    NotSupportedError,
    OperationalError,
    ProgrammingError,
)

# Load environment variables from .env if python-dotenv is available
ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

SCHEMA_PATH = ROOT / "db" / "schema.sql"
SEED_PATH = ROOT / "db" / "seed.sql"


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


def _normalize_sql(sql: str) -> str:
    """Convert '?' parameter placeholders to '%s' for MySQL compatibility, respecting string literals."""
    in_single = False
    in_double = False
    result = []
    for ch in sql:
        if ch == "'" and not in_double:
            in_single = not in_single
            result.append(ch)
        elif ch == '"' and not in_single:
            in_double = not in_double
            result.append(ch)
        elif ch == "?" and not in_single and not in_double:
            result.append("%s")
        else:
            result.append(ch)
    return "".join(result)


class CursorWrapper:
    """Wraps a PyMySQL cursor to return Row objects and provide lastrowid/rowcount."""

    def __init__(self, cursor: pymysql.cursors.Cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query: str, params: Optional[Union[tuple, list, dict]] = None):
        norm_query = _normalize_sql(query)
        self._cursor.execute(norm_query, params)
        self.lastrowid = self._cursor.lastrowid
        self.rowcount = self._cursor.rowcount
        return self

    def fetchone(self) -> Optional[Row]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        col_names = [desc[0] for desc in self._cursor.description]
        return Row(col_names, row)

    def fetchall(self) -> List[Row]:
        rows = self._cursor.fetchall()
        if not rows:
            return []
        col_names = [desc[0] for desc in self._cursor.description]
        return [Row(col_names, r) for r in rows]

    def close(self):
        self._cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DatabaseConnection:
    """High-level MySQL connection supporting execute(), commit(), executescript(), and close()."""

    def __init__(self, raw_conn: pymysql.Connection):
        self._conn = raw_conn

    def execute(self, query: str, params: Optional[Union[tuple, list, dict]] = None) -> CursorWrapper:
        cursor = self._conn.cursor()
        wrapper = CursorWrapper(cursor)
        wrapper.execute(query, params)
        return wrapper

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def executescript(self, script_text: str) -> None:
        """Execute multiple SQL statements separated by semicolons."""
        statements = []
        stmt_buf = []
        in_single = False
        in_double = False

        for line in script_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("--") or line_str.startswith("#"):
                continue
            for ch in line:
                if ch == "'" and not in_double:
                    in_single = not in_single
                elif ch == '"' and not in_single:
                    in_double = not in_double
                elif ch == ";" and not in_single and not in_double:
                    statements.append("".join(stmt_buf).strip())
                    stmt_buf = []
                    continue
                stmt_buf.append(ch)
            stmt_buf.append("\n")

        remainder = "".join(stmt_buf).strip()
        if remainder:
            statements.append(remainder)

        with self._conn.cursor() as cur:
            for stmt in statements:
                if stmt:
                    cur.execute(stmt)
        self._conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_db_config(include_db: bool = True) -> Dict[str, Any]:
    """Parse connection configuration from environment variables or DATABASE_URL."""
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if db_url and db_url.startswith(("mysql://", "mysql+pymysql://")):
        url = urlparse(db_url)
        config = {
            "host": url.hostname or "localhost",
            "port": url.port or 3306,
            "user": unquote(url.username or "root"),
            "password": unquote(url.password or ""),
            "charset": "utf8mb4",
            "autocommit": False,
        }
        if include_db:
            db_name = url.path.lstrip("/") or "scholarship_db"
            config["database"] = db_name
        return config

    config = {
        "host": os.environ.get("MYSQL_HOST", "localhost"),
        "port": int(os.environ.get("MYSQL_PORT", 3306)),
        "user": os.environ.get("MYSQL_USER", "root"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": False,
    }
    if include_db:
        config["database"] = os.environ.get("MYSQL_DATABASE", "scholarship_db")
    return config


def get_db() -> DatabaseConnection:
    """Open a short-lived MySQL connection."""
    config = get_db_config(include_db=True)
    try:
        raw_conn = pymysql.connect(**config)
        return DatabaseConnection(raw_conn)
    except pymysql.err.OperationalError as err:
        # If database doesn't exist (error 1049: Unknown database), attempt initialization
        if err.args and err.args[0] == 1049:
            initialise_database()
            raw_conn = pymysql.connect(**config)
            return DatabaseConnection(raw_conn)
        raise RuntimeError(
            f"Failed to connect to MySQL database '{config.get('database')}' at "
            f"{config.get('host')}:{config.get('port')} with user '{config.get('user')}'.\n"
            f"Error: {err}\n"
            f"Please verify your credentials in your .env file or environment variables."
        ) from err


def initialise_database() -> None:
    """Create database if not exists, create schema and demonstration records."""
    db_name = os.environ.get("MYSQL_DATABASE", "scholarship_db")
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("MYSQL_URL")
    if db_url and db_url.startswith(("mysql://", "mysql+pymysql://")):
        parsed = urlparse(db_url).path.lstrip("/")
        if parsed:
            db_name = parsed

    # Step 1: Connect to server without specifying database to create database if not exists
    server_config = get_db_config(include_db=False)
    try:
        with pymysql.connect(**server_config) as s_conn:
            with s_conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
            s_conn.commit()
    except Exception:
        # If user does not have CREATE DATABASE permissions (e.g. cloud host), continue
        pass

    # Step 2: Connect to the database and initialize tables
    db_config = get_db_config(include_db=True)
    with pymysql.connect(**db_config) as conn:
        db = DatabaseConnection(conn)
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        count_cursor = db.execute("SELECT COUNT(*) FROM students")
        row = count_cursor.fetchone()
        if row and row[0] == 0:
            db.executescript(SEED_PATH.read_text(encoding="utf-8"))
        db.commit()


def reset_database() -> None:
    """Drop tables and recreate schema with seed data."""
    with closing(get_db()) as db:
        db.execute("SET FOREIGN_KEY_CHECKS = 0;")
        db.execute("DROP TABLE IF EXISTS disbursements;")
        db.execute("DROP TABLE IF EXISTS applications;")
        db.execute("DROP TABLE IF EXISTS scholarships;")
        db.execute("DROP TABLE IF EXISTS students;")
        db.execute("SET FOREIGN_KEY_CHECKS = 1;")
        db.commit()
    initialise_database()
