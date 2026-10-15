"""Integration and route tests for FastAPI backend."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app import fastapi_app
from backend.database import Row

client = TestClient(fastapi_app)


def test_api_dashboard():
    mock_db = MagicMock()
    # Mock totals
    totals_row = Row(["students", "scholarships", "applications", "paid"], [3, 3, 3, 1])
    recent_row = Row(
        ["application_id", "student_name", "institute", "scholarship_name", "amount", "status", "apply_date"],
        [1, "Aarav Sharma", "Delhi Technical University", "Merit Excellence", 50000, "Approved", "2026-09-15"],
    )
    status_row = Row(["status", "total"], ["Approved", 1])

    # totals fetchone, recent fetchall, status_counts fetchall
    mock_db.execute.side_effect = [
        MagicMock(fetchone=MagicMock(return_value=totals_row)),
        MagicMock(fetchall=MagicMock(return_value=[recent_row])),
        MagicMock(fetchall=MagicMock(return_value=[status_row])),
    ]

    with patch("backend.app.get_db", return_value=mock_db):
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "totals" in data
        assert data["totals"]["students"] == 3
        assert len(data["recent"]) == 1
        assert data["recent"][0]["student_name"] == "Aarav Sharma"


def test_api_students():
    mock_db = MagicMock()
    student_row = Row(
        ["student_id", "student_name", "aadhaar_no", "institute", "course", "income"],
        [1, "Aarav Sharma", "123456789012", "Delhi Technical University", "B.Tech", 180000],
    )
    inst_row = Row(["institute"], ["Delhi Technical University"])

    mock_db.execute.side_effect = [
        MagicMock(fetchall=MagicMock(return_value=[student_row])),
        MagicMock(fetchall=MagicMock(return_value=[inst_row])),
    ]

    with patch("backend.app.get_db", return_value=mock_db):
        response = client.get("/api/students")
        assert response.status_code == 200
        data = response.json()
        assert len(data["students"]) == 1
        assert data["students"][0]["aadhaar_no"] == "123456789012"
        assert "Delhi Technical University" in data["institutes"]


def test_api_add_student_validation():
    # Test invalid aadhaar
    response = client.post(
        "/api/students",
        json={
            "student_name": "Test",
            "aadhaar_no": "123",  # Invalid: not 12 digits
            "institute": "Test Inst",
            "course": "B.Tech",
            "income": 100000,
        },
    )
    assert response.status_code == 400
    assert "Aadhaar number must be exactly 12 numeric digits" in response.json()["detail"]


def test_api_scholarships():
    mock_db = MagicMock()
    sch_row = Row(
        ["scholarship_id", "scholarship_name", "eligibility", "amount", "deadline", "applications_count", "approved_count"],
        [1, "Merit Excellence", "80%+", 50000, "2026-12-31", 2, 1],
    )
    mock_db.execute.return_value = MagicMock(fetchall=MagicMock(return_value=[sch_row]))

    with patch("backend.app.get_db", return_value=mock_db):
        response = client.get("/api/scholarships")
        assert response.status_code == 200
        data = response.json()
        assert len(data["scholarships"]) == 1
        assert data["scholarships"][0]["scholarship_name"] == "Merit Excellence"
