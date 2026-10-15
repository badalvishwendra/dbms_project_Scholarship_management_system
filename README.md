# Scholarship Management System

A simple, explainable **DBMS college project** that manages students, scholarships, applications and scholarship payments. It includes a polished admin dashboard and demonstrates essential DBMS concepts through a usable web application.

## Features

- Dashboard with live table counts and application status chart
- Add and view students (unique Aadhaar number)
- Create scholarship programmes with eligibility and deadlines
- Submit, approve or reject applications
- Record payments for approved applications
- Foreign keys, uniqueness rules and `CHECK` constraints in SQLite

## Project structure

```
backend/    FastAPI routes and database helper
db/         SQL schema and demo data
frontend/   HTML templates and dashboard styling
scripts/    Utility scripts
storage/    SQLite database created at runtime
```

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Open http://127.0.0.1:8000. The database is created and populated with safe demo data automatically on first run.

## Database schema

| Table | Purpose |
| --- | --- |
| `students` | Student identity, institute, course and income |
| `scholarships` | Scholarship programme and award amount |
| `applications` | Student applications for scholarships |
| `disbursements` | Payment records for approved applications |

See [Architecture.md](Architecture.md) for the relationship explanation and DBMS viva notes.
