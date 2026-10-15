# Scholarship Management System

A comprehensive, explainable **DBMS College Project** implementing a multi-institution Scholarship Management System. The project manages students, scholarship programmes, application workflows, and financial disbursements while strictly enforcing relational integrity, normalization (3NF/BCNF), and parameterized queries.

Built with **FastAPI**, **MySQL (InnoDB)**, and dual client support: a Single Page Application for **Vercel** and server-rendered administration templates for **Render** / local hosting.

---

## Features

- **Dashboard**: Live metric cards, application distribution progress, recent activity, and participating academic institutes snapshot.
- **Students Directory**: Enforce unique 12-digit Aadhaar identification, track affiliated institute, course, and annual income with real-time search & filters.
- **Scholarship Catalogue**: Define scheme awards (₹), eligibility standards, application deadlines, and monitor applicant counts.
- **Application Workflow**: Submit student applications, review submissions, and make decisions with inline **Approve**, **Reject**, or **Reset** actions.
- **Disbursements Register**: Track financial grants, verify bank transaction references (`TXN-...`), and ensure payments are only processed for approved awards.
- **Institute Portal**: Institutional performance tracking with enrollment counts, application success rates, and total grant funds awarded per academic institute.
- **DBMS Constraints**: Primary keys with `AUTO_INCREMENT`, InnoDB foreign keys with cascade rules, composite uniqueness (`UNIQUE(student_id, scholarship_id)`), and domain `CHECK` rules.

---

## Project Structure

```
backend/
├── app.py             # FastAPI REST endpoints & Jinja route handlers
└── database.py        # MySQL connection wrapper, auto-initializer & schema manager
db/
├── schema.sql         # MySQL DDL tables, InnoDB foreign keys, CHECK constraints
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
└── reset_database.py  # Reset MySQL database tables & reload demo seed data
.env.example           # MySQL credentials & environment configuration template
```

---

## Run Locally

### 1. Configure MySQL Database
Ensure MySQL is running on your machine or cloud provider. Create your local environment configuration:
```bash
cp .env.example .env
```
Edit `.env` with your MySQL credentials:
```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=scholarship_db
```
*(The system automatically creates `scholarship_db`, executes the schema, and populates initial demo seed records on first launch).*

### 2. Start the FastAPI Backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```
Backend runs at: **http://127.0.0.1:8000** (interactive API docs available at `http://127.0.0.1:8000/docs`).

### 3. View the Vercel Frontend Locally
```bash
python3 -m http.server 3000 --directory frontend-vercel
```
Open **http://localhost:3000** in your browser. It automatically detects localhost and communicates with your local FastAPI server.

---

## Database Relations

| Relation | Primary Key | Key Attributes & Foreign Keys |
|---|---|---|
| `students` | `student_id` | `student_name`, `aadhaar_no` (UNIQUE, 12 digits), `institute`, `course`, `income` |
| `scholarships` | `scholarship_id` | `scholarship_name`, `eligibility`, `amount` (CHECK > 0), `deadline` |
| `applications` | `application_id` | `student_id` (FK), `scholarship_id` (FK), `apply_date`, `status` (Pending/Approved/Rejected) |
| `disbursements` | `disbursement_id` | `application_id` (FK, UNIQUE), `payment_date`, `status`, `transaction_ref` (UNIQUE) |

For complete ER diagrams, normalization proofs (1NF to BCNF), and examiner viva answers, see [Architecture.md](Architecture.md).
