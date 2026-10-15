"""FastAPI backend for the Scholarship Management System."""
from contextlib import closing
from pathlib import Path
import sqlite3
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from backend.database import get_db, initialise_database

ROOT = Path(__file__).resolve().parent.parent
fastapi_app = FastAPI(title="Scholarship Management System", version="1.0.0")

# Enable CORS for all origins so Vercel and local frontends can access all API endpoints
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.mount("/static", StaticFiles(directory=ROOT / "frontend" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "frontend" / "templates")
templates.env.globals["get_flashed_messages"] = lambda **_kwargs: []


@fastapi_app.on_event("startup")
def startup() -> None:
    initialise_database()


def page(request: Request, name: str, **context):
    return templates.TemplateResponse(request, name, context)


async def get_payload(request: Request) -> dict:
    """Extract parameters from either JSON body or HTML Form."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            return await request.json()
        except Exception:
            return {}
    form = await request.form()
    return dict(form)


def dashboard_data():
    """Return dashboard summary data for both the HTML page and JSON API."""
    with closing(get_db()) as db:
        totals = db.execute("""SELECT (SELECT COUNT(*) FROM students) AS students,
            (SELECT COUNT(*) FROM scholarships) AS scholarships,
            (SELECT COUNT(*) FROM applications) AS applications,
            (SELECT COUNT(*) FROM disbursements WHERE status='Paid') AS paid""").fetchone()
        recent = db.execute("""SELECT a.application_id, s.student_name, s.institute, sc.scholarship_name, sc.amount, a.status, a.apply_date
            FROM applications a JOIN students s ON s.student_id=a.student_id
            JOIN scholarships sc ON sc.scholarship_id=a.scholarship_id
            ORDER BY a.apply_date DESC, a.application_id DESC LIMIT 6""").fetchall()
        status_counts = db.execute("SELECT status, COUNT(*) AS total FROM applications GROUP BY status").fetchall()
    return totals, recent, status_counts


# -----------------------------------------------------------------------------
# HTML Template Routes (Local / Direct Administrative Interface)
# -----------------------------------------------------------------------------

@fastapi_app.get("/")
def dashboard(request: Request):
    totals, recent, status_counts = dashboard_data()
    return page(request, "dashboard.html", active_page="dashboard", totals=totals, recent=recent, status_counts=status_counts)


@fastapi_app.get("/students")
def students(request: Request, institute: str | None = None):
    with closing(get_db()) as db:
        if institute and institute != "all":
            rows = db.execute("SELECT * FROM students WHERE institute = ? ORDER BY student_id DESC", (institute,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM students ORDER BY student_id DESC").fetchall()
        institutes = [r[0] for r in db.execute("SELECT DISTINCT institute FROM students ORDER BY institute").fetchall()]
    return page(request, "students.html", active_page="students", students=rows, institutes=institutes, selected_institute=institute)


@fastapi_app.post("/students")
def add_student(student_name: str = Form(), aadhaar_no: str = Form(), institute: str = Form(), course: str = Form(), income: float = Form()):
    with closing(get_db()) as db:
        try:
            db.execute("INSERT INTO students (student_name,aadhaar_no,institute,course,income) VALUES (?,?,?,?,?)",
                       (student_name.strip(), aadhaar_no.strip(), institute.strip(), course.strip(), income))
            db.commit()
        except sqlite3.IntegrityError:
            pass
    return RedirectResponse("/students", status_code=303)


@fastapi_app.get("/scholarships")
def scholarships(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("SELECT * FROM scholarships ORDER BY deadline").fetchall()
    return page(request, "scholarships.html", active_page="scholarships", scholarships=rows)


@fastapi_app.post("/scholarships")
def add_scholarship(scholarship_name: str = Form(), eligibility: str = Form(), amount: float = Form(), deadline: str = Form()):
    with closing(get_db()) as db:
        db.execute("INSERT INTO scholarships (scholarship_name,eligibility,amount,deadline) VALUES (?,?,?,?)",
                   (scholarship_name.strip(), eligibility.strip(), amount, deadline.strip()))
        db.commit()
    return RedirectResponse("/scholarships", status_code=303)


@fastapi_app.get("/applications")
def applications(request: Request, status: str | None = None, institute: str | None = None):
    with closing(get_db()) as db:
        query = """SELECT a.*, s.student_name, s.institute, sc.scholarship_name, sc.amount FROM applications a
            JOIN students s USING(student_id) JOIN scholarships sc USING(scholarship_id) WHERE 1=1"""
        params = []
        if status and status != "all":
            query += " AND a.status = ?"
            params.append(status)
        if institute and institute != "all":
            query += " AND s.institute = ?"
            params.append(institute)
        query += " ORDER BY a.application_id DESC"
        rows = db.execute(query, params).fetchall()
        student_rows = db.execute("SELECT * FROM students ORDER BY student_name").fetchall()
        scholarship_rows = db.execute("SELECT * FROM scholarships ORDER BY scholarship_name").fetchall()
        institutes = [r[0] for r in db.execute("SELECT DISTINCT institute FROM students ORDER BY institute").fetchall()]
    return page(request, "applications.html", active_page="applications", applications=rows, students=student_rows,
                scholarships=scholarship_rows, institutes=institutes, selected_status=status, selected_institute=institute)


@fastapi_app.post("/applications")
def add_application(student_id: int = Form(), scholarship_id: int = Form(), apply_date: str = Form()):
    with closing(get_db()) as db:
        try:
            db.execute("INSERT INTO applications (student_id,scholarship_id,apply_date,status) VALUES (?,?,?,'Pending')",
                       (student_id, scholarship_id, apply_date.strip()))
            db.commit()
        except sqlite3.IntegrityError:
            pass
    return RedirectResponse("/applications", status_code=303)


@fastapi_app.post("/applications/{application_id}/status", name="change_status")
def change_status(application_id: int, status: str = Form()):
    with closing(get_db()) as db:
        db.execute("UPDATE applications SET status=? WHERE application_id=?", (status.strip(), application_id))
        db.commit()
    return RedirectResponse("/applications", status_code=303)


@fastapi_app.get("/disbursements")
def disbursements(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("""SELECT d.*, s.student_name, s.institute, sc.scholarship_name, sc.amount FROM disbursements d
            JOIN applications a USING(application_id) JOIN students s ON s.student_id=a.student_id
            JOIN scholarships sc ON sc.scholarship_id=a.scholarship_id ORDER BY d.disbursement_id DESC""").fetchall()
        approved = db.execute("""SELECT a.application_id, s.student_name, s.institute, sc.scholarship_name, sc.amount FROM applications a
            JOIN students s USING(student_id) JOIN scholarships sc USING(scholarship_id)
            WHERE a.status='Approved' AND a.application_id NOT IN (SELECT application_id FROM disbursements)""").fetchall()
    return page(request, "disbursements.html", active_page="disbursements", disbursements=rows, approved=approved)


@fastapi_app.post("/disbursements")
def add_disbursement(application_id: int = Form(), payment_date: str = Form(), transaction_ref: str = Form()):
    with closing(get_db()) as db:
        try:
            db.execute("INSERT INTO disbursements (application_id,payment_date,status,transaction_ref) VALUES (?,?,'Paid',?)",
                       (application_id, payment_date.strip(), transaction_ref.strip()))
            db.execute("UPDATE applications SET status='Approved' WHERE application_id=?", (application_id,))
            db.commit()
        except sqlite3.IntegrityError:
            pass
    return RedirectResponse("/disbursements", status_code=303)


# -----------------------------------------------------------------------------
# REST API Endpoints (Consumed by Vercel Frontend and API Clients)
# -----------------------------------------------------------------------------

@fastapi_app.get("/api/dashboard")
def dashboard_api():
    """JSON dashboard summary used by the frontend."""
    totals, recent, status_counts = dashboard_data()
    return {
        "totals": dict(totals),
        "recent": [dict(row) for row in recent],
        "status_counts": [dict(row) for row in status_counts]
    }


@fastapi_app.get("/api/students")
def api_get_students(institute: str | None = None, search: str | None = None):
    with closing(get_db()) as db:
        query = "SELECT * FROM students WHERE 1=1"
        params = []
        if institute and institute != "all":
            query += " AND institute = ?"
            params.append(institute)
        if search:
            query += " AND (student_name LIKE ? OR aadhaar_no LIKE ? OR institute LIKE ? OR course LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term, term])
        query += " ORDER BY student_id DESC"
        rows = db.execute(query, params).fetchall()
        institutes = [r[0] for r in db.execute("SELECT DISTINCT institute FROM students ORDER BY institute").fetchall()]
    return {"students": [dict(r) for r in rows], "institutes": institutes}


@fastapi_app.post("/api/students")
async def api_add_student(request: Request):
    data = await get_payload(request)
    student_name = str(data.get("student_name", "")).strip()
    aadhaar_no = str(data.get("aadhaar_no", "")).strip()
    institute = str(data.get("institute", "")).strip()
    course = str(data.get("course", "")).strip()
    try:
        income = float(data.get("income", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Annual family income must be a valid number.")

    if not student_name or not institute or not course:
        raise HTTPException(status_code=400, detail="Student name, institute, and course are required.")
    if len(aadhaar_no) != 12 or not aadhaar_no.isdigit():
        raise HTTPException(status_code=400, detail="Aadhaar number must be exactly 12 numeric digits.")
    if income < 0:
        raise HTTPException(status_code=400, detail="Annual income cannot be negative.")

    with closing(get_db()) as db:
        existing = db.execute("SELECT student_id FROM students WHERE aadhaar_no = ?", (aadhaar_no,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"A student with Aadhaar number {aadhaar_no} already exists.")
        try:
            cursor = db.execute(
                "INSERT INTO students (student_name,aadhaar_no,institute,course,income) VALUES (?,?,?,?,?)",
                (student_name, aadhaar_no, institute, course, income)
            )
            db.commit()
            new_id = cursor.lastrowid
        except sqlite3.IntegrityError as err:
            raise HTTPException(status_code=400, detail=f"Database constraint error: {err}")

    return {"success": True, "message": "Student registered successfully", "student_id": new_id}


@fastapi_app.delete("/api/students/{student_id}")
def api_delete_student(student_id: int):
    with closing(get_db()) as db:
        app_count = db.execute("SELECT COUNT(*) FROM applications WHERE student_id = ?", (student_id,)).fetchone()[0]
        if app_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete a student who has active scholarship applications.")
        db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
        db.commit()
    return {"success": True, "message": "Student record removed successfully"}


@fastapi_app.get("/api/scholarships")
def api_get_scholarships():
    with closing(get_db()) as db:
        rows = db.execute("""
            SELECT sc.*,
                   (SELECT COUNT(*) FROM applications a WHERE a.scholarship_id = sc.scholarship_id) AS applications_count,
                   (SELECT COUNT(*) FROM applications a WHERE a.scholarship_id = sc.scholarship_id AND a.status = 'Approved') AS approved_count
            FROM scholarships sc ORDER BY sc.deadline
        """).fetchall()
    return {"scholarships": [dict(r) for r in rows]}


@fastapi_app.post("/api/scholarships")
async def api_add_scholarship(request: Request):
    data = await get_payload(request)
    scholarship_name = str(data.get("scholarship_name", "")).strip()
    eligibility = str(data.get("eligibility", "")).strip()
    deadline = str(data.get("deadline", "")).strip()
    try:
        amount = float(data.get("amount", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Scholarship award amount must be a number.")

    if not scholarship_name or not eligibility or not deadline:
        raise HTTPException(status_code=400, detail="Scholarship name, eligibility, and deadline are required.")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Award amount must be greater than zero.")

    with closing(get_db()) as db:
        cursor = db.execute(
            "INSERT INTO scholarships (scholarship_name,eligibility,amount,deadline) VALUES (?,?,?,?)",
            (scholarship_name, eligibility, amount, deadline)
        )
        db.commit()
        new_id = cursor.lastrowid
    return {"success": True, "message": "Scholarship programme added successfully", "scholarship_id": new_id}


@fastapi_app.get("/api/applications")
def api_get_applications(status: str | None = None, institute: str | None = None):
    with closing(get_db()) as db:
        query = """
            SELECT a.application_id, a.student_id, a.scholarship_id, a.apply_date, a.status,
                   s.student_name, s.aadhaar_no, s.institute, s.course,
                   sc.scholarship_name, sc.amount,
                   d.disbursement_id, d.status AS payment_status, d.payment_date, d.transaction_ref
            FROM applications a
            JOIN students s ON s.student_id = a.student_id
            JOIN scholarships sc ON sc.scholarship_id = a.scholarship_id
            LEFT JOIN disbursements d ON d.application_id = a.application_id
            WHERE 1=1
        """
        params = []
        if status and status != "all":
            query += " AND a.status = ?"
            params.append(status)
        if institute and institute != "all":
            query += " AND s.institute = ?"
            params.append(institute)
        query += " ORDER BY a.application_id DESC"
        rows = db.execute(query, params).fetchall()
        institutes = [r[0] for r in db.execute("SELECT DISTINCT institute FROM students ORDER BY institute").fetchall()]
    return {"applications": [dict(r) for r in rows], "institutes": institutes}


@fastapi_app.post("/api/applications")
async def api_add_application(request: Request):
    data = await get_payload(request)
    try:
        student_id = int(data.get("student_id", 0))
        scholarship_id = int(data.get("scholarship_id", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid student or scholarship selection.")
    apply_date = str(data.get("apply_date", "")).strip()

    if not student_id or not scholarship_id or not apply_date:
        raise HTTPException(status_code=400, detail="Student, scholarship, and apply date are required.")

    with closing(get_db()) as db:
        existing = db.execute(
            "SELECT application_id FROM applications WHERE student_id = ? AND scholarship_id = ?",
            (student_id, scholarship_id)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="This student has already submitted an application for this scholarship.")
        cursor = db.execute(
            "INSERT INTO applications (student_id,scholarship_id,apply_date,status) VALUES (?,?,?,'Pending')",
            (student_id, scholarship_id, apply_date)
        )
        db.commit()
        new_id = cursor.lastrowid
    return {"success": True, "message": "Application submitted successfully", "application_id": new_id}


@fastapi_app.post("/api/applications/{application_id}/status")
async def api_change_status(application_id: int, request: Request):
    data = await get_payload(request)
    new_status = str(data.get("status", "")).strip()
    if new_status not in ("Pending", "Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="Status must be Pending, Approved, or Rejected.")

    with closing(get_db()) as db:
        db.execute("UPDATE applications SET status = ? WHERE application_id = ?", (new_status, application_id))
        db.commit()
    return {"success": True, "message": f"Application status changed to {new_status}", "application_id": application_id, "status": new_status}


@fastapi_app.get("/api/disbursements")
def api_get_disbursements(institute: str | None = None):
    with closing(get_db()) as db:
        query = """
            SELECT d.disbursement_id, d.application_id, d.payment_date, d.status, d.transaction_ref,
                   s.student_name, s.aadhaar_no, s.institute,
                   sc.scholarship_name, sc.amount
            FROM disbursements d
            JOIN applications a USING(application_id)
            JOIN students s ON s.student_id = a.student_id
            JOIN scholarships sc ON sc.scholarship_id = a.scholarship_id
            WHERE 1=1
        """
        params = []
        if institute and institute != "all":
            query += " AND s.institute = ?"
            params.append(institute)
        query += " ORDER BY d.disbursement_id DESC"
        rows = db.execute(query, params).fetchall()

        unpaid_query = """
            SELECT a.application_id, s.student_name, s.aadhaar_no, s.institute,
                   sc.scholarship_name, sc.amount
            FROM applications a
            JOIN students s USING(student_id)
            JOIN scholarships sc USING(scholarship_id)
            WHERE a.status = 'Approved' AND a.application_id NOT IN (SELECT application_id FROM disbursements)
            ORDER BY a.application_id DESC
        """
        unpaid_rows = db.execute(unpaid_query).fetchall()

        total_paid = db.execute("""
            SELECT COALESCE(SUM(sc.amount), 0)
            FROM disbursements d
            JOIN applications a USING(application_id)
            JOIN scholarships sc USING(scholarship_id)
            WHERE d.status='Paid'
        """).fetchone()[0]

        institutes = [r[0] for r in db.execute("SELECT DISTINCT institute FROM students ORDER BY institute").fetchall()]

    return {
        "disbursements": [dict(r) for r in rows],
        "approved_unpaid": [dict(r) for r in unpaid_rows],
        "total_disbursed_amount": total_paid,
        "institutes": institutes
    }


@fastapi_app.post("/api/disbursements")
async def api_add_disbursement(request: Request):
    data = await get_payload(request)
    try:
        application_id = int(data.get("application_id", 0))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid application ID.")
    payment_date = str(data.get("payment_date", "")).strip()
    status = str(data.get("status", "Paid")).strip()
    transaction_ref = str(data.get("transaction_ref", "")).strip()

    if not application_id or not payment_date or not transaction_ref:
        raise HTTPException(status_code=400, detail="Application, payment date, and transaction reference are required.")

    with closing(get_db()) as db:
        app_row = db.execute("SELECT status FROM applications WHERE application_id = ?", (application_id,)).fetchone()
        if not app_row:
            raise HTTPException(status_code=404, detail="Selected application does not exist.")
        existing_disb = db.execute("SELECT disbursement_id FROM disbursements WHERE application_id = ?", (application_id,)).fetchone()
        if existing_disb:
            raise HTTPException(status_code=400, detail="A disbursement payment has already been recorded for this application.")
        existing_ref = db.execute("SELECT disbursement_id FROM disbursements WHERE transaction_ref = ?", (transaction_ref,)).fetchone()
        if existing_ref:
            raise HTTPException(status_code=400, detail=f"Transaction reference '{transaction_ref}' is already in use.")

        cursor = db.execute(
            "INSERT INTO disbursements (application_id,payment_date,status,transaction_ref) VALUES (?,?,?,?)",
            (application_id, payment_date, status, transaction_ref)
        )
        db.execute("UPDATE applications SET status='Approved' WHERE application_id=?", (application_id,))
        db.commit()
        new_id = cursor.lastrowid
    return {"success": True, "message": "Disbursement payment recorded successfully", "disbursement_id": new_id}


@fastapi_app.get("/api/institutes")
def api_get_institutes():
    """Aggregate statistics per institute for the institute portal."""
    with closing(get_db()) as db:
        rows = db.execute("""
            SELECT s.institute,
                   COUNT(DISTINCT s.student_id) AS total_students,
                   COUNT(DISTINCT a.application_id) AS total_applications,
                   COUNT(DISTINCT CASE WHEN a.status = 'Approved' THEN a.application_id END) AS approved_applications,
                   COUNT(DISTINCT CASE WHEN a.status = 'Pending' THEN a.application_id END) AS pending_applications,
                   COUNT(DISTINCT CASE WHEN a.status = 'Rejected' THEN a.application_id END) AS rejected_applications,
                   COALESCE(SUM(CASE WHEN d.status = 'Paid' THEN sc.amount ELSE 0 END), 0) AS total_disbursed
            FROM students s
            LEFT JOIN applications a ON a.student_id = s.student_id
            LEFT JOIN scholarships sc ON sc.scholarship_id = a.scholarship_id
            LEFT JOIN disbursements d ON d.application_id = a.application_id
            GROUP BY s.institute
            ORDER BY total_students DESC, s.institute ASC
        """).fetchall()
    return {"institutes": [dict(r) for r in rows]}


# -----------------------------------------------------------------------------
# Dual ASGI / WSGI Compatibility Layer
# -----------------------------------------------------------------------------

class ASGI2Adapter:
    def __init__(self, asgi_app, scope):
        self.asgi_app = asgi_app
        self.scope = scope

    async def __call__(self, receive, send):
        await self.asgi_app(self.scope, receive, send)


class UniversalApp:
    """Universal callable supporting ASGI3 (Uvicorn), ASGI2, and WSGI (Gunicorn sync worker)."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app
        self._wsgi_app = None
        initialise_database()

    @property
    def wsgi_app(self):
        if self._wsgi_app is None:
            from a2wsgi import ASGIMiddleware
            self._wsgi_app = ASGIMiddleware(self.asgi_app)
        return self._wsgi_app

    def __call__(self, *args, **kwargs):
        if len(args) == 1:
            return ASGI2Adapter(self.asgi_app, args[0])
        elif len(args) == 2:
            return self.wsgi_app(*args, **kwargs)
        elif len(args) == 3:
            return self.asgi_app(*args, **kwargs)
        raise TypeError(f"UniversalApp expected 1, 2, or 3 arguments, got {len(args)}")

    def __getattr__(self, name):
        return getattr(self.asgi_app, name)


app = UniversalApp(fastapi_app)
