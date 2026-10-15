-- Schema for Scholarship Management System (MySQL / MariaDB)
-- Implements the 4 core relations with full relational integrity and InnoDB engine.

CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    student_name VARCHAR(255) NOT NULL,
    aadhaar_no VARCHAR(12) NOT NULL UNIQUE,
    institute VARCHAR(255) NOT NULL,
    course VARCHAR(255) NOT NULL,
    income DECIMAL(12, 2) NOT NULL,
    CONSTRAINT chk_aadhaar_length CHECK (CHAR_LENGTH(aadhaar_no) = 12),
    CONSTRAINT chk_income_nonneg CHECK (income >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scholarships (
    scholarship_id INT AUTO_INCREMENT PRIMARY KEY,
    scholarship_name VARCHAR(255) NOT NULL,
    eligibility TEXT NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    deadline VARCHAR(50) NOT NULL,
    CONSTRAINT chk_amount_pos CHECK (amount > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    scholarship_id INT NOT NULL,
    apply_date VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    CONSTRAINT uq_student_scholarship UNIQUE (student_id, scholarship_id),
    CONSTRAINT chk_app_status CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    CONSTRAINT fk_app_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_app_scholarship FOREIGN KEY (scholarship_id) REFERENCES scholarships(scholarship_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS disbursements (
    disbursement_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL UNIQUE,
    payment_date VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Paid',
    transaction_ref VARCHAR(100) NOT NULL UNIQUE,
    CONSTRAINT chk_disb_status CHECK (status IN ('Paid', 'Processing', 'Failed')),
    CONSTRAINT fk_disb_application FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
