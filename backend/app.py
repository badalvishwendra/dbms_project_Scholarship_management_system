"""FastAPI backend for the Scholarship Management System."""
from contextlib import closing
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from backend.database import get_db, initialise_database

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Scholarship Management System", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=ROOT / "frontend" / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "frontend" / "templates")
templates.env.globals["get_flashed_messages"] = lambda **_kwargs: []


@app.on_event("startup")
def startup() -> None:
    initialise_database()


def page(request: Request, name: str, **context):
    return templates.TemplateResponse(request, name, context)


def dashboard_data():
    """Return dashboard data for both the HTML page and JSON API."""
    with closing(get_db()) as db:
        totals = db.execute("""SELECT (SELECT COUNT(*) FROM students) AS students,
            (SELECT COUNT(*) FROM scholarships) AS scholarships,
            (SELECT COUNT(*) FROM applications) AS applications,
            (SELECT COUNT(*) FROM disbursements WHERE status='Paid') AS paid""").fetchone()
        recent = db.execute("""SELECT a.application_id,s.student_name,sc.scholarship_name,sc.amount,a.status,a.apply_date
            FROM applications a JOIN students s ON s.student_id=a.student_id
            JOIN scholarships sc ON sc.scholarship_id=a.scholarship_id
            ORDER BY a.apply_date DESC,a.application_id DESC LIMIT 6""").fetchall()
        status_counts = db.execute("SELECT status,COUNT(*) AS total FROM applications GROUP BY status").fetchall()
    return totals, recent, status_counts


@app.get("/")
def dashboard(request: Request):
    totals, recent, status_counts = dashboard_data()
    return page(request, "dashboard.html", totals=totals, recent=recent, status_counts=status_counts)


@app.get("/api/dashboard")
def dashboard_api():
    """JSON data used by the separately hosted Vercel frontend."""
    totals, recent, status_counts = dashboard_data()
    return {"totals": dict(totals), "recent": [dict(row) for row in recent], "status_counts": [dict(row) for row in status_counts]}


@app.get("/students")
def students(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("SELECT * FROM students ORDER BY student_id DESC").fetchall()
    return page(request, "students.html", students=rows)


@app.post("/students")
def add_student(student_name: str = Form(), aadhaar_no: str = Form(), institute: str = Form(), course: str = Form(), income: float = Form()):
    with closing(get_db()) as db:
        db.execute("INSERT INTO students (student_name,aadhaar_no,institute,course,income) VALUES (?,?,?,?,?)", (student_name, aadhaar_no, institute, course, income))
        db.commit()
    return RedirectResponse("/students", status_code=303)


@app.get("/scholarships")
def scholarships(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("SELECT * FROM scholarships ORDER BY deadline").fetchall()
    return page(request, "scholarships.html", scholarships=rows)


@app.post("/scholarships")
def add_scholarship(scholarship_name: str = Form(), eligibility: str = Form(), amount: float = Form(), deadline: str = Form()):
    with closing(get_db()) as db:
        db.execute("INSERT INTO scholarships (scholarship_name,eligibility,amount,deadline) VALUES (?,?,?,?)", (scholarship_name, eligibility, amount, deadline))
        db.commit()
    return RedirectResponse("/scholarships", status_code=303)


@app.get("/applications")
def applications(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("""SELECT a.*,s.student_name,sc.scholarship_name,sc.amount FROM applications a
            JOIN students s USING(student_id) JOIN scholarships sc USING(scholarship_id) ORDER BY a.application_id DESC""").fetchall()
        student_rows = db.execute("SELECT * FROM students ORDER BY student_name").fetchall()
        scholarship_rows = db.execute("SELECT * FROM scholarships ORDER BY scholarship_name").fetchall()
    return page(request, "applications.html", applications=rows, students=student_rows, scholarships=scholarship_rows)


@app.post("/applications")
def add_application(student_id: int = Form(), scholarship_id: int = Form(), apply_date: str = Form()):
    with closing(get_db()) as db:
        db.execute("INSERT INTO applications (student_id,scholarship_id,apply_date,status) VALUES (?,?,?,'Pending')", (student_id, scholarship_id, apply_date))
        db.commit()
    return RedirectResponse("/applications", status_code=303)


@app.post("/applications/{application_id}/status", name="change_status")
def change_status(application_id: int, status: str = Form()):
    with closing(get_db()) as db:
        db.execute("UPDATE applications SET status=? WHERE application_id=?", (status, application_id))
        db.commit()
    return RedirectResponse("/applications", status_code=303)


@app.get("/disbursements")
def disbursements(request: Request):
    with closing(get_db()) as db:
        rows = db.execute("""SELECT d.*,s.student_name,sc.scholarship_name,sc.amount FROM disbursements d
            JOIN applications a USING(application_id) JOIN students s ON s.student_id=a.student_id
            JOIN scholarships sc ON sc.scholarship_id=a.scholarship_id ORDER BY d.disbursement_id DESC""").fetchall()
        approved = db.execute("""SELECT a.application_id,s.student_name,sc.scholarship_name,sc.amount FROM applications a
            JOIN students s USING(student_id) JOIN scholarships sc USING(scholarship_id)
            WHERE a.status='Approved' AND a.application_id NOT IN (SELECT application_id FROM disbursements)""").fetchall()
    return page(request, "disbursements.html", disbursements=rows, approved=approved)


@app.post("/disbursements")
def add_disbursement(application_id: int = Form(), payment_date: str = Form(), transaction_ref: str = Form()):
    with closing(get_db()) as db:
        db.execute("INSERT INTO disbursements (application_id,payment_date,status,transaction_ref) VALUES (?,?,'Paid',?)", (application_id, payment_date, transaction_ref))
        db.execute("UPDATE applications SET status='Approved' WHERE application_id=?", (application_id,))
        db.commit()
    return RedirectResponse("/disbursements", status_code=303)


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


fastapi_app = app
app = UniversalApp(fastapi_app)

