# Architecture and DBMS Concepts

## Technology

- **Frontend:** HTML/CSS templates rendered by Flask.
- **Backend:** Python Flask routes handle forms and use parameterized SQL queries.
- **Database:** SQLite, stored locally at `storage/scholarships.db` after the first run.

## Entity relationships

`Students (1) → (many) Applications (many) ← (1) Scholarships`

`Applications (1) → (0 or 1) Disbursements`

An application connects a student to a scholarship. A disbursement is created only when an application has been approved.

## Constraints shown in the project

- Primary keys uniquely identify each row.
- `aadhaar_no` is `UNIQUE`, preventing duplicate student profiles.
- Foreign keys prevent applications or payments pointing to non-existent records.
- `CHECK` constraints restrict valid payment and application status values.
- A composite `UNIQUE(student_id, scholarship_id)` prevents a duplicate application.
- Parameterized `?` SQL values are used in Python to protect against SQL injection.

## Suggested viva explanation

“The system is normalized into four tables. Student details and scholarship details are stored only once. Applications form the many-to-many relationship, while disbursement records payments. This avoids duplicate data and enforces referential integrity using foreign keys.”
