INSERT INTO students (student_name, aadhaar_no, institute, course, income) VALUES
 ('Aarav Sharma', '123456789012', 'Delhi Technical University', 'B.Tech Computer Science', 180000),
 ('Priya Patel', '234567890123', 'Mumbai University', 'B.Com', 220000),
 ('Kabir Singh', '345678901234', 'Pune Institute of Technology', 'B.Tech Mechanical', 150000);
INSERT INTO scholarships (scholarship_name, eligibility, amount, deadline) VALUES
 ('Merit Excellence Scholarship', 'Marks above 80%', 50000, '2026-12-31'),
 ('Need-Based Support Grant', 'Family income below ₹2.5 lakh', 40000, '2026-11-30'),
 ('Women in STEM Award', 'Female students in STEM courses', 60000, '2026-10-31');
INSERT INTO applications (student_id, scholarship_id, apply_date, status) VALUES
 (1, 1, '2026-09-15', 'Approved'), (2, 2, '2026-09-22', 'Pending'), (3, 1, '2026-10-02', 'Rejected');
INSERT INTO disbursements (application_id, payment_date, status, transaction_ref) VALUES
 (1, '2026-10-01', 'Paid', 'TXN-2026-0001');
