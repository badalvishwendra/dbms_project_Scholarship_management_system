"""Unit tests for SQLite database module, Row abstraction, and relational constraints."""
import decimal
from datetime import date
from pathlib import Path
import pytest

from backend.database import (
    IntegrityError,
    Row,
    _convert_val,
    get_db,
    get_db_config,
    get_db_path,
    initialise_database,
    reset_database,
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
    assert ("student_name", "Aarav Sharma") in list(row.items())


def test_get_db_path_and_config(monkeypatch, tmp_path):
    # Test custom DATABASE_PATH
    custom_db = tmp_path / "test_custom.db"
    monkeypatch.setenv("DATABASE_PATH", str(custom_db))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    assert get_db_path() == custom_db

    # Test custom DATABASE_URL
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{custom_db}")
    assert get_db_path() == custom_db

    # Test get_db_config
    config = get_db_config()
    assert config["engine"] == "sqlite"
    assert config["database"] == str(custom_db)
    assert config["is_memory"] is False


def test_sqlite_in_memory_connection():
    conn = get_db(":memory:")
    # Check that foreign keys are enabled
    fk_status = conn.execute("PRAGMA foreign_keys;").fetchone()
    assert fk_status[0] == 1

    # Check row factory produces Row objects
    conn.execute("CREATE TABLE test_tbl (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO test_tbl (name) VALUES ('Test Item');")
    row = conn.execute("SELECT id, name FROM test_tbl;").fetchone()
    assert isinstance(row, Row)
    assert row["name"] == "Test Item"
    assert row.name == "Test Item"
    assert row[1] == "Test Item"
    conn.close()


def test_initialise_database_and_seed(tmp_path):
    test_db = tmp_path / "test_scholarships.db"
    initialise_database(test_db)

    conn = get_db(test_db)
    try:
        # Check student records seeded
        students = conn.execute("SELECT * FROM students;").fetchall()
        assert len(students) >= 3

        # Check scholarships seeded
        scholarships = conn.execute("SELECT * FROM scholarships;").fetchall()
        assert len(scholarships) >= 3

        # Check applications seeded
        applications = conn.execute("SELECT * FROM applications;").fetchall()
        assert len(applications) >= 3

        # Check disbursements seeded
        disbursements = conn.execute("SELECT * FROM disbursements;").fetchall()
        assert len(disbursements) >= 1
    finally:
        conn.close()


def test_relational_constraints_in_sqlite(tmp_path):
    test_db = tmp_path / "test_constraints.db"
    initialise_database(test_db)

    conn = get_db(test_db)
    try:
        # 1. Foreign key constraint: inserting application with non-existent student_id
        with pytest.raises(IntegrityError):
            conn.execute(
                "INSERT INTO applications (student_id, scholarship_id, apply_date, status) VALUES (?, ?, ?, ?)",
                (999999, 1, "2026-10-22", "Pending"),
            )

        # 2. Domain check constraint: Aadhaar number must be exactly 12 characters
        with pytest.raises(IntegrityError):
            conn.execute(
                "INSERT INTO students (student_name, aadhaar_no, institute, course, income) VALUES (?, ?, ?, ?, ?)",
                ("Invalid Student", "123", "Test Inst", "B.Tech", 100000),
            )

        # 3. Domain check constraint: Family income cannot be negative
        with pytest.raises(IntegrityError):
            conn.execute(
                "INSERT INTO students (student_name, aadhaar_no, institute, course, income) VALUES (?, ?, ?, ?, ?)",
                ("Negative Income", "999999999999", "Test Inst", "B.Tech", -500),
            )

        # 4. Composite unique constraint: (student_id, scholarship_id) uniqueness
        with pytest.raises(IntegrityError):
            # Student 1 already applied for Scholarship 1 in seed data
            conn.execute(
                "INSERT INTO applications (student_id, scholarship_id, apply_date, status) VALUES (?, ?, ?, ?)",
                (1, 1, "2026-10-22", "Pending"),
            )
    finally:
        conn.close()


def test_reset_database(tmp_path):
    test_db = tmp_path / "test_reset.db"
    initialise_database(test_db)

    # Insert a non-seed student
    conn = get_db(test_db)
    conn.execute(
        "INSERT INTO students (student_name, aadhaar_no, institute, course, income) VALUES (?, ?, ?, ?, ?)",
        ("Temporary Student", "987654321098", "Temp Uni", "B.Sc", 120000),
    )
    conn.commit()
    count_before = conn.execute("SELECT COUNT(*) FROM students;").fetchone()[0]
    assert count_before == 4
    conn.close()

    # Reset database
    reset_database(test_db)

    conn2 = get_db(test_db)
    try:
        count_after = conn2.execute("SELECT COUNT(*) FROM students;").fetchone()[0]
        # Restored to 3 original demo students
        assert count_after == 3
        temp_student = conn2.execute("SELECT * FROM students WHERE aadhaar_no = '987654321098';").fetchone()
        assert temp_student is None
    finally:
        conn2.close()
