-- Schema for Scholarship Management System (SQLite)
-- Implements the 4 core relations with full relational integrity and foreign keys.

CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    aadhaar_no TEXT NOT NULL UNIQUE CHECK(length(aadhaar_no) = 12),
    institute TEXT NOT NULL,
    course TEXT NOT NULL,
    income REAL NOT NULL CHECK(income >= 0)
);

CREATE TABLE IF NOT EXISTS scholarships (
    scholarship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_name TEXT NOT NULL,
    eligibility TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount > 0),
    deadline TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    scholarship_id INTEGER NOT NULL,
    apply_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected')),
    UNIQUE(student_id, scholarship_id),
    FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY(scholarship_id) REFERENCES scholarships(scholarship_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS disbursements (
    disbursement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL UNIQUE,
    payment_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Paid' CHECK(status IN ('Paid', 'Processing', 'Failed')),
    transaction_ref TEXT NOT NULL UNIQUE,
    FOREIGN KEY(application_id) REFERENCES applications(application_id) ON DELETE RESTRICT ON UPDATE CASCADE
);
