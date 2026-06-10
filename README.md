# ApartaSmart — Apartment Management System

A full-stack web application built with **Python Flask + MySQL (XAMPP) + premium dark UI**.

## 👥 Roles & Login Credentials

| Role        | Email                       | Password   |
|-------------|-----------------------------|------------|
| Admin       | admin@apartment.com         | admin123   |
| Resident    | resident@apartment.com      | admin123   |
| Security    | security@apartment.com      | admin123   |
| Staff       | staff@apartment.com         | admin123   |
| Accountant  | accountant@apartment.com    | admin123   |

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.9+
- XAMPP (Apache + MySQL running)
- pip

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Database
1. Open **phpMyAdmin** at http://localhost/phpmyadmin
2. Create a database named `apartment_manage`
3. Import `database/schema.sql`

### 4. Run the App
```bash
python app.py
```

Open http://localhost:5000

---

## 🗂️ Project Structure

```
apartment_manage/
├── app.py                  # App factory
├── config.py               # XAMPP MySQL config
├── models.py               # User model
├── requirements.txt
├── database/
│   └── schema.sql          # Full DB schema + seed data
├── routes/
│   ├── auth.py             # Login / Logout
│   ├── admin.py            # Admin module
│   ├── resident.py         # Resident module
│   ├── security.py         # Security module
│   ├── staff.py            # Staff module
│   └── accountant.py       # Accountant module
├── static/
│   ├── css/style.css       # Premium dark theme
│   ├── js/main.js          # Shared JS + Chart.js helpers
│   └── uploads/            # File uploads
└── templates/
    ├── base.html           # Master layout
    ├── auth/login.html
    ├── admin/              # 11 admin templates
    ├── resident/           # 8 resident templates
    ├── security/           # 5 security templates
    ├── staff/              # 4 staff templates
    ├── accountant/         # 3 accountant templates
    └── errors/             # 403, 404, 500
```

---

## ✨ Features

### Admin
- Dashboard with charts & stats
- Resident management (add/toggle)
- Flat management & allocation
- Maintenance assignment
- Complaint responses
- Visitor log overview
- Parking slot management
- Amenity status control
- Emergency alert system
- Staff management & task assignment
- Notices & announcements
- Revenue reports & analytics

### Resident
- Personal dashboard with flat info
- Submit maintenance requests
- File & track complaints
- Register & track visitors
- Parking slot request
- Amenity booking
- Bill history
- Profile management
- Notice board

### Security
- Gate visitor queue (approve/deny/check-in/out)
- Walk-in visitor logging
- Parking overview
- Emergency reporting

### Staff
- Assigned task management
- Maintenance job updates
- Work history

### Accountant
- Financial dashboard (KPIs)
- Invoice generation & management
- Mark paid / overdue
- Monthly revenue reports
- Per-resident billing summary
