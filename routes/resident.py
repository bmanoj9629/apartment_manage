from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import mysql

resident_bp = Blueprint('resident', __name__)

def resident_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'resident':
            flash('Resident access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_cursor():
    return mysql.connection.cursor()

def get_resident_flat(resident_id):
    cur = get_cursor()
    cur.execute("""SELECT f.* FROM flats f
                   JOIN flat_allocations fa ON f.id=fa.flat_id
                   WHERE fa.resident_id=%s AND fa.is_current=1""", (resident_id,))
    flat = cur.fetchone()
    cur.close()
    return flat

# ── Dashboard ─────────────────────────────────────────────
@resident_bp.route('/dashboard')
@login_required
@resident_required
def dashboard():
    cur = get_cursor()
    flat = get_resident_flat(current_user.id)

    cur.execute("SELECT COUNT(*) AS c FROM maintenance_requests WHERE resident_id=%s AND status='pending'", (current_user.id,))
    pending_maintenance = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM complaints WHERE resident_id=%s AND status='open'", (current_user.id,))
    open_complaints = cur.fetchone()['c']

    cur.execute("SELECT COUNT(*) AS c FROM visitors WHERE resident_id=%s AND status='checked_in'", (current_user.id,))
    active_visitors = cur.fetchone()['c']

    cur.execute("SELECT * FROM invoices WHERE resident_id=%s AND status IN ('unpaid','overdue') ORDER BY year DESC, month DESC LIMIT 3", (current_user.id,))
    pending_bills = cur.fetchall()

    cur.execute("SELECT * FROM notices WHERE (target_role='all' OR target_role='resident') AND (expires_at IS NULL OR expires_at > NOW()) ORDER BY is_pinned DESC, published_at DESC LIMIT 5")
    notices = cur.fetchall()

    cur.execute("SELECT * FROM emergency_alerts WHERE status='active' ORDER BY created_at DESC")
    alerts = cur.fetchall()

    cur.execute("SELECT * FROM maintenance_requests WHERE resident_id=%s ORDER BY requested_at DESC LIMIT 3", (current_user.id,))
    recent_requests = cur.fetchall()

    cur.close()
    return render_template('resident/dashboard.html', flat=flat,
                           pending_maintenance=pending_maintenance,
                           open_complaints=open_complaints,
                           active_visitors=active_visitors,
                           pending_bills=pending_bills, notices=notices,
                           alerts=alerts, recent_requests=recent_requests)

# ── Maintenance ───────────────────────────────────────────
@resident_bp.route('/maintenance')
@login_required
@resident_required
def maintenance():
    cur = get_cursor()
    cur.execute("""SELECT mr.*, s.name AS staff_name FROM maintenance_requests mr
                   LEFT JOIN users s ON mr.assigned_to=s.id
                   WHERE mr.resident_id=%s ORDER BY mr.requested_at DESC""", (current_user.id,))
    requests = cur.fetchall()
    flat = get_resident_flat(current_user.id)
    cur.close()
    return render_template('resident/maintenance.html', requests=requests, flat=flat)

@resident_bp.route('/maintenance/submit', methods=['POST'])
@login_required
@resident_required
def submit_maintenance():
    flat = get_resident_flat(current_user.id)
    if not flat:
        flash('No flat allocated to your account.', 'danger')
        return redirect(url_for('resident.maintenance'))
    cur = get_cursor()
    cur.execute("""INSERT INTO maintenance_requests (resident_id,flat_id,category,title,description,priority)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (current_user.id, flat['id'], request.form['category'],
                 request.form['title'], request.form.get('description',''),
                 request.form['priority']))
    mysql.connection.commit()
    flash('Maintenance request submitted.', 'success')
    return redirect(url_for('resident.maintenance'))

# ── Complaints ────────────────────────────────────────────
@resident_bp.route('/complaints')
@login_required
@resident_required
def complaints():
    cur = get_cursor()
    cur.execute("SELECT * FROM complaints WHERE resident_id=%s ORDER BY submitted_at DESC", (current_user.id,))
    complaints = cur.fetchall()
    cur.close()
    return render_template('resident/complaints.html', complaints=complaints)

@resident_bp.route('/complaints/submit', methods=['POST'])
@login_required
@resident_required
def submit_complaint():
    cur = get_cursor()
    cur.execute("""INSERT INTO complaints (resident_id,category,title,description,priority)
                   VALUES (%s,%s,%s,%s,%s)""",
                (current_user.id, request.form['category'], request.form['title'],
                 request.form.get('description',''), request.form['priority']))
    mysql.connection.commit()
    flash('Complaint submitted.', 'success')
    return redirect(url_for('resident.complaints'))

# ── Visitors ──────────────────────────────────────────────
@resident_bp.route('/visitors')
@login_required
@resident_required
def visitors():
    cur = get_cursor()
    cur.execute("SELECT * FROM visitors WHERE resident_id=%s ORDER BY check_in DESC", (current_user.id,))
    visitors = cur.fetchall()
    cur.close()
    return render_template('resident/visitors.html', visitors=visitors)

@resident_bp.route('/visitors/add', methods=['POST'])
@login_required
@resident_required
def add_visitor():
    cur = get_cursor()
    cur.execute("""INSERT INTO visitors (resident_id,visitor_name,phone,purpose,vehicle_no,status)
                   VALUES (%s,%s,%s,%s,%s,'pending')""",
                (current_user.id, request.form['visitor_name'], request.form.get('phone',''),
                 request.form.get('purpose',''), request.form.get('vehicle_no','')))
    mysql.connection.commit()
    flash('Visitor registered. Security will verify at gate.', 'success')
    return redirect(url_for('resident.visitors'))

# ── Parking ───────────────────────────────────────────────
@resident_bp.route('/parking')
@login_required
@resident_required
def parking():
    cur = get_cursor()
    cur.execute("SELECT * FROM parking_slots WHERE resident_id=%s", (current_user.id,))
    my_slot = cur.fetchone()
    cur.execute("SELECT * FROM parking_slots WHERE status='available' ORDER BY block, slot_no")
    available = cur.fetchall()
    cur.close()
    return render_template('resident/parking.html', my_slot=my_slot, available=available)

@resident_bp.route('/parking/request', methods=['POST'])
@login_required
@resident_required
def request_parking():
    slot_id    = request.form['slot_id']
    vehicle_no = request.form['vehicle_no']
    cur = get_cursor()
    cur.execute("""UPDATE parking_slots SET resident_id=%s, vehicle_no=%s,
                   status='occupied', assigned_at=NOW() WHERE id=%s AND status='available'""",
                (current_user.id, vehicle_no, slot_id))
    mysql.connection.commit()
    flash('Parking slot assigned!', 'success')
    return redirect(url_for('resident.parking'))

# ── Amenities ─────────────────────────────────────────────
@resident_bp.route('/amenities')
@login_required
@resident_required
def amenities():
    cur = get_cursor()
    cur.execute("SELECT * FROM amenities WHERE status='available' ORDER BY name")
    amenities = cur.fetchall()
    cur.execute("SELECT ab.*, a.name AS amenity_name FROM amenity_bookings ab JOIN amenities a ON ab.amenity_id=a.id WHERE ab.resident_id=%s ORDER BY ab.booking_date DESC", (current_user.id,))
    my_bookings = cur.fetchall()
    cur.close()
    return render_template('resident/amenities.html', amenities=amenities, my_bookings=my_bookings)

@resident_bp.route('/amenities/book', methods=['POST'])
@login_required
@resident_required
def book_amenity():
    cur = get_cursor()
    cur.execute("""INSERT INTO amenity_bookings (amenity_id,resident_id,booking_date,start_time,end_time,notes)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (request.form['amenity_id'], current_user.id, request.form['booking_date'],
                 request.form['start_time'], request.form['end_time'], request.form.get('notes','')))
    mysql.connection.commit()
    flash('Amenity booking requested!', 'success')
    return redirect(url_for('resident.amenities'))

# ── Bills ─────────────────────────────────────────────────
@resident_bp.route('/bills')
@login_required
@resident_required
def bills():
    cur = get_cursor()
    cur.execute("""SELECT i.*, f.flat_no FROM invoices i JOIN flats f ON i.flat_id=f.id
                   WHERE i.resident_id=%s ORDER BY i.year DESC, i.month DESC""", (current_user.id,))
    invoices = cur.fetchall()
    cur.close()
    return render_template('resident/bills.html', invoices=invoices)

# ── Profile ───────────────────────────────────────────────
@resident_bp.route('/profile')
@login_required
@resident_required
def profile():
    cur = get_cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (current_user.id,))
    user = cur.fetchone()
    flat = get_resident_flat(current_user.id)
    cur.close()
    return render_template('resident/profile.html', user=user, flat=flat)

@resident_bp.route('/profile/update', methods=['POST'])
@login_required
@resident_required
def update_profile():
    import bcrypt as _bcrypt
    cur = get_cursor()
    phone = request.form.get('phone','')
    cur.execute("UPDATE users SET phone=%s WHERE id=%s", (phone, current_user.id))
    if request.form.get('new_password'):
        pwd = _bcrypt.hashpw(request.form['new_password'].encode(), _bcrypt.gensalt()).decode()
        cur.execute("UPDATE users SET password=%s WHERE id=%s", (pwd, current_user.id))
    mysql.connection.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('resident.profile'))

# ── Notices ───────────────────────────────────────────────
@resident_bp.route('/notices')
@login_required
@resident_required
def notices():
    cur = get_cursor()
    cur.execute("""SELECT n.*, u.name AS author FROM notices n JOIN users u ON n.created_by=u.id
                   WHERE (n.target_role='all' OR n.target_role='resident')
                   AND (n.expires_at IS NULL OR n.expires_at > NOW())
                   ORDER BY n.is_pinned DESC, n.published_at DESC""")
    notices = cur.fetchall()
    cur.close()
    return render_template('resident/notices.html', notices=notices)
