# Scholarship Management System

A comprehensive, explainable **DBMS College Project** implementing a multi-institution Scholarship Management System. The project manages students, scholarship programmes, application workflows, and financial disbursements while strictly enforcing relational integrity, normalization (3NF/BCNF), and parameterized queries.

Built with **FastAPI**, **SQLite**, and dual client support: a Single Page Application for **Vercel** and server-rendered administration templates for **Render** / local hosting.

---

## Features

- **Dashboard**: Live metric cards, application distribution progress, recent activity, and participating academic institutes snapshot.
- **Students Directory**: Enforce unique 12-digit Aadhaar identification, track affiliated institute, course, and annual income with real-time search & filters.
- **Scholarship Catalogue**: Define scheme awards (₹), eligibility standards, application deadlines, and monitor applicant counts.
- **Application Workflow**: Submit student applications, review submissions, and make decisions with inline **Approve**, **Reject**, or **Reset** actions.
- **Disbursements Register**: Track financial grants, verify bank transaction references (`TXN-...`), and ensure payments are only processed for approved awards.
- **Institute Portal**: Institutional performance tracking with enrollment counts, application success rates, and total grant funds awarded per academic institute.
- **DBMS Constraints**: Primary keys with `AUTOINCREMENT`, SQLite foreign keys with cascade rules (`PRAGMA foreign_keys = ON`), composite uniqueness (`UNIQUE(student_id, scholarship_id)`), and domain `CHECK` rules.

---

## Project Structure

```
backend/
├── app.py             # FastAPI REST endpoints & Jinja route handlers
└── database.py        # SQLite connection helper, auto-initializer & schema manager
db/
├── schema.sql         # SQLite DDL tables, foreign keys, CHECK constraints
└── seed.sql           # Safe initial demonstration data
frontend/              # Server-rendered administrative interface
├── static/style.css   # Clean stylesheet for local admin
└── templates/         # Jinja2 templates (dashboard, students, etc.)
frontend-vercel/       # Client-side SPA for Vercel deployment
├── index.html         # Tabbed single-page application
├── app.js             # Client routing, API fetchers, form handlers
├── style.css          # Responsive design & corporate academic theme
└── config.js          # API URL configuration (local / production)
scripts/
└── reset_database.py  # Reset storage/scholarships.db & reload demo seed data
storage/
└── scholarships.db    # SQLite database generated automatically
.env.example           # Server & database environment configuration template
```

---

## Run Locally

### 1. Start the FastAPI Backend
No external database server installation required. SQLite is built into Python and automatically creates `storage/scholarships.db`, executes the schema, and populates initial demo seed records on first launch.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```
Backend runs at: **http://127.0.0.1:8000** (interactive API docs available at `http://127.0.0.1:8000/docs`).

### 2. View the Vercel Frontend Locally
```bash
python3 -m http.server 3000 --directory frontend-vercel
```
Open **http://localhost:3000** in your browser. It automatically detects localhost and communicates with your local FastAPI server.

### 3. Reset Database (Optional)
To clear any added test records and restore fresh demonstration seed data:
```bash
python scripts/reset_database.py
```

---

## Database Relations

| Relation | Primary Key | Key Attributes & Foreign Keys |
|---|---|---|
| `students` | `student_id` | `student_name`, `aadhaar_no` (UNIQUE, 12 digits), `income` (CHECK >= 0), `institute`, `course` |
| `scholarships` | `scholarship_id` | `scholarship_name`, `eligibility`, `amount` (CHECK > 0), `deadline` |
| `applications` | `application_id` | `student_id` (FK), `scholarship_id` (FK), `apply_date`, `status` (Pending/Approved/Rejected) |
| `disbursements` | `disbursement_id` | `application_id` (FK, UNIQUE), `payment_date`, `status`, `transaction_ref` (UNIQUE) |

For complete ER diagrams, normalization proofs (1NF to BCNF), and examiner viva answers, see [Architecture.md](Architecture.md).
