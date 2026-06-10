-- ============================================================
-- Apartment Management System — Full Schema
-- Database: apartment_manage
-- ============================================================

CREATE DATABASE IF NOT EXISTS apartment_manage CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE apartment_manage;

-- ============================================================
-- 1. USERS (all roles)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,
    role        ENUM('admin','resident','security','staff','accountant') NOT NULL DEFAULT 'resident',
    phone       VARCHAR(20),
    avatar      VARCHAR(255) DEFAULT 'default_avatar.png',
    is_active   TINYINT(1) DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. FLATS
-- ============================================================
CREATE TABLE IF NOT EXISTS flats (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    flat_no     VARCHAR(20) UNIQUE NOT NULL,
    floor       INT NOT NULL,
    block       VARCHAR(10) NOT NULL,
    type        ENUM('1BHK','2BHK','3BHK','4BHK','Studio') NOT NULL DEFAULT '2BHK',
    area_sqft   INT,
    rent        DECIMAL(10,2) DEFAULT 0.00,
    status      ENUM('occupied','vacant','maintenance') DEFAULT 'vacant',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 3. FLAT ALLOCATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS flat_allocations (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    flat_id     INT NOT NULL,
    resident_id INT NOT NULL,
    start_date  DATE NOT NULL,
    end_date    DATE,
    is_current  TINYINT(1) DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (flat_id)     REFERENCES flats(id) ON DELETE CASCADE,
    FOREIGN KEY (resident_id) REFERENCES users(id)  ON DELETE CASCADE
);

-- ============================================================
-- 4. MAINTENANCE REQUESTS
-- ============================================================
CREATE TABLE IF NOT EXISTS maintenance_requests (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    resident_id  INT NOT NULL,
    flat_id      INT NOT NULL,
    category     ENUM('electrical','plumbing','carpentry','cleaning','painting','other') DEFAULT 'other',
    title        VARCHAR(200) NOT NULL,
    description  TEXT,
    priority     ENUM('low','medium','high','urgent') DEFAULT 'medium',
    status       ENUM('pending','in_progress','completed','cancelled') DEFAULT 'pending',
    assigned_to  INT,
    amount       DECIMAL(10,2) DEFAULT 0.00,
    notes        TEXT,
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    FOREIGN KEY (resident_id)  REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (flat_id)      REFERENCES flats(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to)  REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 5. COMPLAINTS
-- ============================================================
CREATE TABLE IF NOT EXISTS complaints (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    resident_id INT NOT NULL,
    category    ENUM('noise','cleanliness','security','parking','amenities','neighbor','staff','other') DEFAULT 'other',
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      ENUM('open','under_review','resolved','closed') DEFAULT 'open',
    priority    ENUM('low','medium','high') DEFAULT 'medium',
    response    TEXT,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at  DATETIME,
    FOREIGN KEY (resident_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 6. VISITORS
-- ============================================================
CREATE TABLE IF NOT EXISTS visitors (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    resident_id  INT NOT NULL,
    visitor_name VARCHAR(100) NOT NULL,
    phone        VARCHAR(20),
    purpose      VARCHAR(200),
    vehicle_no   VARCHAR(30),
    check_in     DATETIME DEFAULT CURRENT_TIMESTAMP,
    check_out    DATETIME,
    approved_by  INT,
    status       ENUM('pending','approved','checked_in','checked_out','denied') DEFAULT 'pending',
    FOREIGN KEY (resident_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 7. PARKING SLOTS
-- ============================================================
CREATE TABLE IF NOT EXISTS parking_slots (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    slot_no     VARCHAR(20) UNIQUE NOT NULL,
    block       VARCHAR(10),
    level       INT DEFAULT 1,
    type        ENUM('car','bike','both') DEFAULT 'car',
    status      ENUM('available','occupied','reserved','maintenance') DEFAULT 'available',
    resident_id INT,
    vehicle_no  VARCHAR(30),
    assigned_at DATETIME,
    FOREIGN KEY (resident_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- 8. AMENITIES
-- ============================================================
CREATE TABLE IF NOT EXISTS amenities (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    capacity    INT DEFAULT 1,
    location    VARCHAR(100),
    status      ENUM('available','maintenance','closed') DEFAULT 'available',
    open_time   TIME,
    close_time  TIME,
    image       VARCHAR(255)
);

-- ============================================================
-- 9. AMENITY BOOKINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS amenity_bookings (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    amenity_id  INT NOT NULL,
    resident_id INT NOT NULL,
    booking_date DATE NOT NULL,
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    status      ENUM('pending','confirmed','cancelled','completed') DEFAULT 'pending',
    notes       TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (amenity_id)  REFERENCES amenities(id) ON DELETE CASCADE,
    FOREIGN KEY (resident_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 10. INVOICES / BILLING
-- ============================================================
CREATE TABLE IF NOT EXISTS invoices (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    resident_id  INT NOT NULL,
    flat_id      INT NOT NULL,
    month        INT NOT NULL,
    year         INT NOT NULL,
    rent         DECIMAL(10,2) DEFAULT 0.00,
    maintenance  DECIMAL(10,2) DEFAULT 0.00,
    electricity  DECIMAL(10,2) DEFAULT 0.00,
    water        DECIMAL(10,2) DEFAULT 0.00,
    parking      DECIMAL(10,2) DEFAULT 0.00,
    other        DECIMAL(10,2) DEFAULT 0.00,
    total        DECIMAL(10,2) GENERATED ALWAYS AS (rent+maintenance+electricity+water+parking+other) STORED,
    status       ENUM('unpaid','paid','overdue','waived') DEFAULT 'unpaid',
    due_date     DATE,
    paid_at      DATETIME,
    notes        TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resident_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (flat_id)     REFERENCES flats(id) ON DELETE CASCADE
);

-- ============================================================
-- 11. NOTICES / ANNOUNCEMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS notices (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    created_by  INT NOT NULL,
    title       VARCHAR(200) NOT NULL,
    content     TEXT NOT NULL,
    category    ENUM('general','maintenance','event','emergency','billing','security') DEFAULT 'general',
    target_role ENUM('all','resident','security','staff','accountant') DEFAULT 'all',
    is_pinned   TINYINT(1) DEFAULT 0,
    published_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 12. EMERGENCY ALERTS
-- ============================================================
CREATE TABLE IF NOT EXISTS emergency_alerts (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    created_by  INT NOT NULL,
    type        ENUM('fire','flood','medical','security','evacuation','power','other') DEFAULT 'other',
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    severity    ENUM('low','medium','high','critical') DEFAULT 'high',
    status      ENUM('active','resolved','false_alarm') DEFAULT 'active',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 13. STAFF TASKS
-- ============================================================
CREATE TABLE IF NOT EXISTS staff_tasks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    assigned_to INT NOT NULL,
    assigned_by INT NOT NULL,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    category    ENUM('cleaning','repair','security','delivery','general') DEFAULT 'general',
    priority    ENUM('low','medium','high','urgent') DEFAULT 'medium',
    status      ENUM('pending','in_progress','completed','cancelled') DEFAULT 'pending',
    due_date    DATE,
    completed_at DATETIME,
    notes       TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 14. VISITOR LOG (security gate log)
-- ============================================================
CREATE TABLE IF NOT EXISTS visitor_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    visitor_id   INT NOT NULL,
    security_id  INT NOT NULL,
    action       ENUM('check_in','check_out','denied') NOT NULL,
    timestamp    DATETIME DEFAULT CURRENT_TIMESTAMP,
    remarks      VARCHAR(255),
    FOREIGN KEY (visitor_id)  REFERENCES visitors(id) ON DELETE CASCADE,
    FOREIGN KEY (security_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ============================================================
-- 15. ACTIVITY LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT,
    action     VARCHAR(255) NOT NULL,
    details    TEXT,
    ip_address VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- SEED DATA
-- ============================================================

-- Admin user (password: admin123)
INSERT INTO users (name, email, password, role, phone) VALUES
('Super Admin',    'admin@apartment.com',     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'admin',     '9876543210'),
('John Resident',  'resident@apartment.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'resident',   '9876543211'),
('Mike Security',  'security@apartment.com',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'security',   '9876543212'),
('Sam Staff',      'staff@apartment.com',     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'staff',      '9876543213'),
('Lisa Accounts',  'accountant@apartment.com','$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'accountant', '9876543214'),
('Alice Resident', 'alice@apartment.com',     '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'resident',   '9876543215'),
('Bob Resident',   'bob@apartment.com',       '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBpj2rKX4J3X9i', 'resident',   '9876543216');

-- Flats
INSERT INTO flats (flat_no, floor, block, type, area_sqft, rent, status) VALUES
('A-101', 1, 'A', '2BHK', 1200, 25000.00, 'occupied'),
('A-102', 1, 'A', '1BHK', 800,  18000.00, 'occupied'),
('A-201', 2, 'A', '3BHK', 1600, 35000.00, 'vacant'),
('A-202', 2, 'A', '2BHK', 1200, 25000.00, 'occupied'),
('B-101', 1, 'B', '2BHK', 1200, 26000.00, 'vacant'),
('B-102', 1, 'B', '4BHK', 2000, 45000.00, 'occupied'),
('B-201', 2, 'B', 'Studio',600, 12000.00, 'maintenance'),
('C-101', 1, 'C', '2BHK', 1200, 25000.00, 'vacant'),
('C-102', 1, 'C', '3BHK', 1600, 35000.00, 'occupied'),
('C-201', 2, 'C', '2BHK', 1200, 25000.00, 'vacant');

-- Flat Allocations
INSERT INTO flat_allocations (flat_id, resident_id, start_date, is_current) VALUES
(1, 2, '2024-01-01', 1),
(2, 6, '2024-03-01', 1),
(4, 7, '2024-06-01', 1),
(6, 2, '2023-01-01', 0);

-- Parking Slots
INSERT INTO parking_slots (slot_no, block, level, type, status, resident_id, vehicle_no, assigned_at) VALUES
('P-A01', 'A', 1, 'car',  'occupied',  2, 'MH01AB1234', NOW()),
('P-A02', 'A', 1, 'car',  'available', NULL, NULL, NULL),
('P-A03', 'A', 1, 'bike', 'available', NULL, NULL, NULL),
('P-B01', 'B', 1, 'car',  'occupied',  6, 'MH02CD5678', NOW()),
('P-B02', 'B', 1, 'car',  'available', NULL, NULL, NULL),
('P-C01', 'C', 1, 'both', 'occupied',  7, 'MH03EF9012', NOW()),
('P-C02', 'C', 1, 'car',  'maintenance',NULL,NULL,NULL);

-- Amenities
INSERT INTO amenities (name, description, capacity, location, status, open_time, close_time) VALUES
('Swimming Pool',  'Olympic size swimming pool with lifeguard', 30, 'Ground Floor', 'available', '06:00:00', '22:00:00'),
('Gym',            'Fully equipped modern gymnasium',           20, 'Block A-GF',   'available', '05:00:00', '23:00:00'),
('Clubhouse',      'Multipurpose hall for events and meetings', 100,'Central Area',  'available', '08:00:00', '22:00:00'),
('Badminton Court','Professional badminton court',              4,  'Block B',       'available', '06:00:00', '21:00:00'),
('Kids Play Area', 'Safe and fun play area for children',       15, 'Garden Area',   'available', '08:00:00', '20:00:00'),
('Library',        'Quiet reading room with books & wifi',      10, 'Block C-1F',   'available', '09:00:00', '21:00:00');

-- Notices
INSERT INTO notices (created_by, title, content, category, target_role, is_pinned) VALUES
(1, 'Welcome to ApartaSmart Portal', 'Welcome residents! This portal gives you access to all services.', 'general', 'all', 1),
(1, 'Water Supply Maintenance', 'Water supply will be interrupted on Apr 10 from 10AM-2PM for maintenance.', 'maintenance', 'all', 0),
(1, 'Annual Society Meeting', 'Annual general meeting scheduled for Apr 20 at 6 PM in Clubhouse.', 'event', 'resident', 0),
(1, 'April Maintenance Bills Due', 'April maintenance bills are now generated. Please pay by Apr 30.', 'billing', 'resident', 1);

-- Sample Maintenance Requests
INSERT INTO maintenance_requests (resident_id, flat_id, category, title, description, priority, status, amount) VALUES
(2, 1, 'plumbing', 'Leaking bathroom tap', 'The bathroom tap has been leaking for 2 days.', 'high', 'in_progress', 500.00),
(2, 1, 'electrical', 'Fan not working', 'Bedroom ceiling fan stopped working.', 'medium', 'pending', 0.00),
(6, 2, 'carpentry', 'Wardrobe door broken', 'Master bedroom wardrobe door hinge is broken.', 'low', 'completed', 800.00),
(7, 4, 'cleaning', 'Deep cleaning request', 'Need deep cleaning for entire flat.', 'medium', 'pending', 2000.00);

-- Sample Complaints
INSERT INTO complaints (resident_id, category, title, description, status) VALUES
(2, 'noise',    'Loud music from A-201', 'Neighbours play loud music after midnight.', 'open'),
(6, 'parking',  'Unauthorized parking', 'Someone parks in visitor slot P-A02 daily.', 'under_review'),
(7, 'cleanliness','Common area not clean','Lobby floor not being cleaned regularly.', 'open');

-- Sample Visitors
INSERT INTO visitors (resident_id, visitor_name, phone, purpose, status, check_in) VALUES
(2, 'Raj Kumar',    '9111111111', 'Family visit', 'checked_in', NOW()),
(2, 'Delivery Guy', '9222222222', 'Package delivery', 'checked_out', DATE_SUB(NOW(), INTERVAL 1 HOUR)),
(6, 'Priya Sharma', '9333333333', 'Friend visit', 'pending', NOW());

-- Sample Invoices
INSERT INTO invoices (resident_id, flat_id, month, year, rent, maintenance, electricity, water, parking, due_date, status) VALUES
(2, 1, 4, 2026, 25000.00, 3000.00, 1500.00, 500.00, 500.00, '2026-04-30', 'unpaid'),
(2, 1, 3, 2026, 25000.00, 3000.00, 1200.00, 450.00, 500.00, '2026-03-31', 'paid'),
(6, 2, 4, 2026, 18000.00, 3000.00, 900.00,  300.00, 0.00,   '2026-04-30', 'unpaid'),
(7, 4, 4, 2026, 25000.00, 3000.00, 1100.00, 400.00, 500.00, '2026-04-30', 'overdue');

-- Staff Tasks
INSERT INTO staff_tasks (assigned_to, assigned_by, title, description, category, priority, status, due_date) VALUES
(4, 1, 'Clean lobby Area A', 'Deep clean the Block A lobby and stairs.', 'cleaning', 'medium', 'in_progress', '2026-04-08'),
(4, 1, 'Fix light in corridor B', 'Replace blown bulb in B-block corridor.', 'repair', 'high', 'pending', '2026-04-07'),
(4, 1, 'Garden maintenance', 'Trim hedges and water plants in garden area.', 'general', 'low', 'completed', '2026-04-05');

-- Emergency Alerts
INSERT INTO emergency_alerts (created_by, type, title, description, severity, status) VALUES
(1, 'power', 'Scheduled Power Outage', 'Power will be off on Apr 9 from 2PM-4PM for transformer maintenance.', 'medium', 'active');
