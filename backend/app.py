"""Flask application for the Scholarship Management System.

The routes intentionally use straightforward SQL so the project is easy to
demonstrate in a DBMS viva.
"""
from pathlib import Path
from flask import Flask, flash, redirect, render_template, request, url_for
from backend.database import close_db, get_db, initialise_database

ROOT = Path(__file__).resolve().parent.parent


def create_app():
    app = Flask(
        __name__,
        template_folder=str(ROOT / "frontend" / "templates"),
        static_folder=str(ROOT / "frontend" / "static"),
    )
    app.config["SECRET_KEY"] = "college-project-demo-key"
    app.teardown_appcontext(close_db)
    with app.app_context():
        initialise_database()

    @app.get("/")
    def dashboard():
        db = get_db()
        totals = db.execute("""
            SELECT
              (SELECT COUNT(*) FROM students) AS students,
              (SELECT COUNT(*) FROM scholarships) AS scholarships,
              (SELECT COUNT(*) FROM applications) AS applications,
              (SELECT COUNT(*) FROM disbursements WHERE status = 'Paid') AS paid
        """).fetchone()
        recent = db.execute("""
            SELECT a.application_id, s.student_name, sc.scholarship_name,
                   sc.amount, a.status, a.apply_date
            FROM applications a
            JOIN students s ON s.student_id = a.student_id
            JOIN scholarships sc ON sc.scholarship_id = a.scholarship_id
            ORDER BY a.apply_date DESC, a.application_id DESC LIMIT 6
        """).fetchall()
        status_counts = db.execute("SELECT status, COUNT(*) AS total FROM applications GROUP BY status").fetchall()
        return render_template("dashboard.html", totals=totals, recent=recent, status_counts=status_counts)

    @app.route("/students", methods=["GET", "POST"])
    def students():
        db = get_db()
        if request.method == "POST":
            try:
                db.execute("INSERT INTO students (student_name, aadhaar_no, institute, course, income) VALUES (?, ?, ?, ?, ?)",
                           (request.form["student_name"], request.form["aadhaar_no"], request.form["institute"], request.form["course"], request.form["income"]))
                db.commit(); flash("Student added successfully.", "success")
            except Exception as error:
                flash(f"Could not add student: {error}", "error")
            return redirect(url_for("students"))
        return render_template("students.html", students=db.execute("SELECT * FROM students ORDER BY student_id DESC").fetchall())

    @app.route("/scholarships", methods=["GET", "POST"])
    def scholarships():
        db = get_db()
        if request.method == "POST":
            db.execute("INSERT INTO scholarships (scholarship_name, eligibility, amount, deadline) VALUES (?, ?, ?, ?)",
                       (request.form["scholarship_name"], request.form["eligibility"], request.form["amount"], request.form["deadline"]))
            db.commit(); flash("Scholarship added successfully.", "success")
            return redirect(url_for("scholarships"))
        return render_template("scholarships.html", scholarships=db.execute("SELECT * FROM scholarships ORDER BY deadline").fetchall())

    @app.route("/applications", methods=["GET", "POST"])
    def applications():
        db = get_db()
        if request.method == "POST":
            db.execute("INSERT INTO applications (student_id, scholarship_id, apply_date, status) VALUES (?, ?, ?, 'Pending')",
                       (request.form["student_id"], request.form["scholarship_id"], request.form["apply_date"]))
            db.commit(); flash("Application submitted. Status is Pending.", "success")
            return redirect(url_for("applications"))
        rows = db.execute("""SELECT a.*, s.student_name, sc.scholarship_name, sc.amount
                             FROM applications a JOIN students s USING(student_id)
                             JOIN scholarships sc USING(scholarship_id)
                             ORDER BY a.application_id DESC""").fetchall()
        return render_template("applications.html", applications=rows,
                               students=db.execute("SELECT * FROM students ORDER BY student_name").fetchall(),
                               scholarships=db.execute("SELECT * FROM scholarships ORDER BY scholarship_name").fetchall())

    @app.post("/applications/<int:application_id>/status")
    def change_status(application_id):
        status = request.form["status"]
        db = get_db(); db.execute("UPDATE applications SET status = ? WHERE application_id = ?", (status, application_id))
        db.commit(); flash("Application status updated.", "success")
        return redirect(url_for("applications"))

    @app.route("/disbursements", methods=["GET", "POST"])
    def disbursements():
        db = get_db()
        if request.method == "POST":
            application_id = request.form["application_id"]
            db.execute("INSERT INTO disbursements (application_id, payment_date, status, transaction_ref) VALUES (?, ?, 'Paid', ?)",
                       (application_id, request.form["payment_date"], request.form["transaction_ref"]))
            db.execute("UPDATE applications SET status = 'Approved' WHERE application_id = ?", (application_id,))
            db.commit(); flash("Payment recorded successfully.", "success")
            return redirect(url_for("disbursements"))
        rows = db.execute("""SELECT d.*, s.student_name, sc.scholarship_name, sc.amount
                             FROM disbursements d JOIN applications a USING(application_id)
                             JOIN students s ON s.student_id = a.student_id
                             JOIN scholarships sc ON sc.scholarship_id = a.scholarship_id
                             ORDER BY d.disbursement_id DESC""").fetchall()
        approved = db.execute("""SELECT a.application_id, s.student_name, sc.scholarship_name, sc.amount
                                FROM applications a JOIN students s USING(student_id)
                                JOIN scholarships sc USING(scholarship_id)
                                WHERE a.status='Approved' AND a.application_id NOT IN (SELECT application_id FROM disbursements)""").fetchall()
        return render_template("disbursements.html", disbursements=rows, approved=approved)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
