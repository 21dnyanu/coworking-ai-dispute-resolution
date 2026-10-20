-- Database Schema for AI-Powered Coworking Space Booking & Complaint Resolution System
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS USERS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'CUSTOMER')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS SPACES (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Meeting Room', 'Private Cabin', 'Dedicated Desk', 'Studio', 'Day Pass')),
    location TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    capacity INTEGER NOT NULL,
    amenities TEXT NOT NULL,
    image_path TEXT NOT NULL,
    availability_status TEXT DEFAULT 'AVAILABLE' CHECK(availability_status IN ('AVAILABLE', 'MAINTENANCE', 'OCCUPIED'))
);

CREATE TABLE IF NOT EXISTS BOOKINGS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_reference TEXT UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES USERS(id) ON DELETE CASCADE,
    space_id INTEGER NOT NULL REFERENCES SPACES(id) ON DELETE CASCADE,
    booking_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    booking_amount REAL NOT NULL,
    status TEXT DEFAULT 'CONFIRMED' CHECK(status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS COMPLAINTS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_reference TEXT UNIQUE NOT NULL,
    booking_id INTEGER NOT NULL REFERENCES BOOKINGS(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES USERS(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    expected_resolution TEXT NOT NULL,
    status TEXT DEFAULT 'SUBMITTED' CHECK(status IN ('SUBMITTED', 'UNDER REVIEW', 'AWAITING EVIDENCE', 'MANUAL INVESTIGATION', 'RESOLVED', 'CLOSED')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS EVIDENCE (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES COMPLAINTS(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    validation_status TEXT DEFAULT 'PENDING' CHECK(validation_status IN ('PENDING', 'RELEVANT', 'PARTIALLY_RELEVANT', 'UNRELATED', 'UNCERTAIN', 'IMAGE_UNREADABLE')),
    validation_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS OWNER_STATEMENTS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES COMPLAINTS(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS POLICY_DOCUMENTS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_name TEXT NOT NULL,
    document_path TEXT NOT NULL,
    version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS AI_INVESTIGATIONS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER UNIQUE NOT NULL REFERENCES COMPLAINTS(id) ON DELETE CASCADE,
    verified_facts_json TEXT NOT NULL,
    customer_allegations_json TEXT NOT NULL,
    owner_allegations_json TEXT NOT NULL,
    unknown_information_json TEXT NOT NULL,
    evidence_analysis_json TEXT NOT NULL,
    policy_references_json TEXT NOT NULL,
    proposed_resolution TEXT NOT NULL CHECK(proposed_resolution IN ('FULL_REFUND', 'PARTIAL_REFUND', 'NO_REFUND', 'MANUAL_INVESTIGATION')),
    explanation TEXT NOT NULL,
    requires_manual_review INTEGER DEFAULT 0,
    suggested_refund_amount REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ADMIN_DECISIONS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES COMPLAINTS(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES USERS(id),
    proposed_resolution TEXT NOT NULL,
    final_resolution TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT NOT NULL,
    final_amount REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS AUDIT_LOGS (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES USERS(id),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON USERS(email);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON BOOKINGS(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_space_date ON BOOKINGS(space_id, booking_date);
CREATE INDEX IF NOT EXISTS idx_complaints_booking ON COMPLAINTS(booking_id);
CREATE INDEX IF NOT EXISTS idx_complaints_customer ON COMPLAINTS(customer_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON COMPLAINTS(status);
CREATE INDEX IF NOT EXISTS idx_evidence_complaint ON EVIDENCE(complaint_id);
CREATE INDEX IF NOT EXISTS idx_ai_inv_complaint ON AI_INVESTIGATIONS(complaint_id);
CREATE INDEX IF NOT EXISTS idx_admin_dec_complaint ON ADMIN_DECISIONS(complaint_id);
