"""Unit tests for MySQL database module and wrappers."""
import decimal
from datetime import date
from unittest.mock import MagicMock

import pytest

from backend.database import (
    CursorWrapper,
    DatabaseConnection,
    IntegrityError,
    MySQLError,
    Row,
    _convert_val,
    _normalize_sql,
    get_db_config,
)


def test_convert_val():
    assert _convert_val(decimal.Decimal("100.00")) == 100
    assert _convert_val(decimal.Decimal("100.50")) == 100.5
    assert _convert_val(date(2026, 10, 15)) == "2026-10-15"
    assert _convert_val("text") == "text"
    assert _convert_val(42) == 42


def test_row_indexing_and_attribute_access():
    keys = ["student_id", "student_name", "income"]
    values = [1, "Aarav Sharma", decimal.Decimal("180000.00")]
    row = Row(keys, values)

    # Dictionary access
    assert row["student_id"] == 1
    assert row["student_name"] == "Aarav Sharma"
    assert row["income"] == 180000

    # Index access
    assert row[0] == 1
    assert row[1] == "Aarav Sharma"
    assert row[2] == 180000

    # Attribute access
    assert row.student_id == 1
    assert row.student_name == "Aarav Sharma"

    # dict() conversion
    d = dict(row)
    assert d == {"student_id": 1, "student_name": "Aarav Sharma", "income": 180000}

    # keys, values, items
    assert list(row.keys()) == ["student_id", "student_name", "income"]
    assert list(row.values()) == [1, "Aarav Sharma", 180000]


def test_normalize_sql():
    sql = "SELECT * FROM students WHERE institute = ? AND course = ?"
    expected = "SELECT * FROM students WHERE institute = %s AND course = %s"
    assert _normalize_sql(sql) == expected

    # Question mark inside quotes should NOT be replaced
    sql_quoted = "SELECT * FROM students WHERE name = 'What?' AND id = ?"
    expected_quoted = "SELECT * FROM students WHERE name = 'What?' AND id = %s"
    assert _normalize_sql(sql_quoted) == expected_quoted


def test_get_db_config(monkeypatch):
    monkeypatch.setenv("MYSQL_HOST", "db.example.com")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "admin")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret123")
    monkeypatch.setenv("MYSQL_DATABASE", "custom_scholarship_db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MYSQL_URL", raising=False)

    config = get_db_config()
    assert config["host"] == "db.example.com"
    assert config["port"] == 3307
    assert config["user"] == "admin"
    assert config["password"] == "secret123"
    assert config["database"] == "custom_scholarship_db"


def test_get_db_config_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://myuser:mypass@dbhost:3308/prod_db")
    config = get_db_config()
    assert config["host"] == "dbhost"
    assert config["port"] == 3308
    assert config["user"] == "myuser"
    assert config["password"] == "mypass"
    assert config["database"] == "prod_db"


def test_cursor_wrapper_and_db_connection():
    mock_cursor = MagicMock()
    mock_cursor.description = [("id",), ("name",)]
    mock_cursor.fetchone.return_value = (10, "Scholarship A")
    mock_cursor.fetchall.return_value = [(10, "Scholarship A"), (20, "Scholarship B")]
    mock_cursor.lastrowid = 10
    mock_cursor.rowcount = 1

    wrapper = CursorWrapper(mock_cursor)
    res = wrapper.execute("SELECT * FROM scholarships WHERE id = ?", (10,))
    assert res is wrapper
    assert wrapper.lastrowid == 10

    single = wrapper.fetchone()
    assert single["id"] == 10
    assert single["name"] == "Scholarship A"

    multiple = wrapper.fetchall()
    assert len(multiple) == 2
    assert multiple[1]["id"] == 20


def test_executescript_parsing():
    mock_raw_conn = MagicMock()
    mock_cur = MagicMock()
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cur

    conn = DatabaseConnection(mock_raw_conn)
    script = """
    -- Comment line
    CREATE TABLE t1 (id INT PRIMARY KEY);
    # Another comment
    INSERT INTO t1 VALUES (1);
    """
    conn.executescript(script)
    assert mock_cur.execute.call_count == 2
