from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import mysql
import bcrypt

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_cursor():
    return mysql.connection.cursor()

# ── Dashboard ────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    cur = get_cursor()
    stats = {}
    cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='resident' AND is_active=1"); stats['residents'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM flats"); stats['total_flats'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM flats WHERE status='occupied'"); stats['occupied'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM flats WHERE status='vacant'"); stats['vacant'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='pending'"); stats['pending_maintenance'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM complaints WHERE status='open'"); stats['open_complaints'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM visitors WHERE status='checked_in'"); stats['active_visitors'] = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total),0) AS c FROM invoices WHERE status='unpaid'"); stats['unpaid_amount'] = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM emergency_alerts WHERE status='active'"); stats['active_alerts'] = cur.fetchone()['c']

    cur.execute("""SELECT u.name, u.email, u.role, u.created_at FROM users u
                   ORDER BY u.created_at DESC LIMIT 5""")
    recent_users = cur.fetchall()

    cur.execute("""SELECT mr.title, mr.status, mr.priority, u.name AS resident
                   FROM maintenance_requests mr JOIN users u ON mr.resident_id=u.id
                   ORDER BY mr.requested_at DESC LIMIT 5""")
    recent_maintenance = cur.fetchall()

    cur.execute("""SELECT c.title, c.status, c.category, u.name AS resident
                   FROM complaints c JOIN users u ON c.resident_id=u.id
                   ORDER BY c.submitted_at DESC LIMIT 5""")
    recent_complaints = cur.fetchall()

    cur.execute("SELECT * FROM emergency_alerts WHERE status='active' ORDER BY created_at DESC")
    alerts = cur.fetchall()

    # Chart data — monthly revenue
    cur.execute("""SELECT month, COALESCE(SUM(total),0) AS revenue
                   FROM invoices WHERE year=YEAR(NOW()) AND status='paid'
                   GROUP BY month ORDER BY month""")
    revenue_data = cur.fetchall()

    cur.close()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_users=recent_users, recent_maintenance=recent_maintenance,
                           recent_complaints=recent_complaints, alerts=alerts,
                           revenue_data=revenue_data)

# ── Residents ────────────────────────────────────────────────
@admin_bp.route('/residents')
@login_required
@admin_required
def residents():
    cur = get_cursor()
    cur.execute("""SELECT u.*, f.flat_no, f.block FROM users u
                   LEFT JOIN flat_allocations fa ON u.id=fa.resident_id AND fa.is_current=1
                   LEFT JOIN flats f ON fa.flat_id=f.id
                   WHERE u.role='resident' ORDER BY u.name""")
    residents = cur.fetchall()
    cur.close()
    return render_template('admin/residents.html', residents=residents)

@admin_bp.route('/residents/add', methods=['POST'])
@login_required
@admin_required
def add_resident():
    name  = request.form['name']
    email = request.form['email'].lower()
    phone = request.form.get('phone','')
    pwd   = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()
    try:
        cur = get_cursor()
        cur.execute("INSERT INTO users (name,email,password,role,phone) VALUES (%s,%s,%s,'resident',%s)",
                    (name, email, pwd, phone))
        mysql.connection.commit()
        flash('Resident added successfully.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.residents'))

@admin_bp.route('/residents/toggle/<int:uid>')
@login_required
@admin_required
def toggle_resident(uid):
    cur = get_cursor()
    cur.execute("UPDATE users SET is_active = NOT is_active WHERE id=%s", (uid,))
    mysql.connection.commit()
    flash('Resident status updated.', 'success')
    return redirect(url_for('admin.residents'))

# ── Flats ────────────────────────────────────────────────────
@admin_bp.route('/flats')
@login_required
@admin_required
def flats():
    cur = get_cursor()
    cur.execute("""SELECT f.*, u.name AS resident_name
                   FROM flats f
                   LEFT JOIN flat_allocations fa ON f.id=fa.flat_id AND fa.is_current=1
                   LEFT JOIN users u ON fa.resident_id=u.id
                   ORDER BY f.block, f.floor, f.flat_no""")
    flats = cur.fetchall()
    cur.execute("SELECT id, name FROM users WHERE role='resident' AND is_active=1 ORDER BY name")
    residents = cur.fetchall()
    cur.close()
    return render_template('admin/flats.html', flats=flats, residents=residents)

@admin_bp.route('/flats/add', methods=['POST'])
@login_required
@admin_required
def add_flat():
    try:
        cur = get_cursor()
        cur.execute("""INSERT INTO flats (flat_no,floor,block,type,area_sqft,rent)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (request.form['flat_no'], request.form['floor'], request.form['block'],
                     request.form['type'], request.form.get('area','0'), request.form.get('rent','0')))
        mysql.connection.commit()
        flash('Flat added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.flats'))

@admin_bp.route('/flats/allocate', methods=['POST'])
@login_required
@admin_required
def allocate_flat():
    flat_id     = request.form['flat_id']
    resident_id = request.form['resident_id']
    start_date  = request.form['start_date']
    try:
        cur = get_cursor()
        cur.execute("UPDATE flat_allocations SET is_current=0 WHERE flat_id=%s", (flat_id,))
        cur.execute("""INSERT INTO flat_allocations (flat_id,resident_id,start_date,is_current)
                       VALUES (%s,%s,%s,1)""", (flat_id, resident_id, start_date))
        cur.execute("UPDATE flats SET status='occupied' WHERE id=%s", (flat_id,))
        mysql.connection.commit()
        flash('Flat allocated successfully.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.flats'))

# ── Maintenance ──────────────────────────────────────────────
@admin_bp.route('/maintenance')
@login_required
@admin_required
def maintenance():
    cur = get_cursor()
    cur.execute("""SELECT mr.*, u.name AS resident_name, f.flat_no,
                          s.name AS staff_name
                   FROM maintenance_requests mr
                   JOIN users u ON mr.resident_id=u.id
                   JOIN flats f ON mr.flat_id=f.id
                   LEFT JOIN users s ON mr.assigned_to=s.id
                   ORDER BY mr.requested_at DESC""")
    requests = cur.fetchall()
    cur.execute("SELECT id, name FROM users WHERE role='staff' AND is_active=1")
    staff = cur.fetchall()
    cur.close()
    return render_template('admin/maintenance.html', requests=requests, staff=staff)

@admin_bp.route('/maintenance/assign/<int:rid>', methods=['POST'])
@login_required
@admin_required
def assign_maintenance(rid):
    # staff_id can be empty string when admin selects “Unassigned”
    raw_staff_id = request.form.get('staff_id', '').strip()
    staff_id = int(raw_staff_id) if raw_staff_id else None

    status = request.form.get('status', 'in_progress')
    amount_raw = request.form.get('amount', 0)
    try:
        amount = float(amount_raw) if amount_raw not in (None, '') else 0.0
    except ValueError:
        amount = 0.0

    cur = get_cursor()
    cur.execute(
        """UPDATE maintenance_requests
           SET assigned_to=%s, status=%s, amount=%s
           WHERE id=%s""",
        (staff_id, status, amount, rid)
    )
    mysql.connection.commit()
    flash('Maintenance request updated.', 'success')
    return redirect(url_for('admin.maintenance'))


# ── Complaints ───────────────────────────────────────────────
@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    cur = get_cursor()
    cur.execute("""SELECT c.*, u.name AS resident_name
                   FROM complaints c JOIN users u ON c.resident_id=u.id
                   ORDER BY c.submitted_at DESC""")
    complaints = cur.fetchall()
    cur.close()
    return render_template('admin/complaints.html', complaints=complaints)

@admin_bp.route('/complaints/respond/<int:cid>', methods=['POST'])
@login_required
@admin_required
def respond_complaint(cid):
    response = request.form['response']
    status   = request.form['status']
    cur = get_cursor()
    resolved = "NOW()" if status == 'resolved' else "NULL"
    cur.execute(f"""UPDATE complaints SET response=%s, status=%s,
                    resolved_at=IF(%s='resolved', NOW(), NULL) WHERE id=%s""",
                (response, status, status, cid))
    mysql.connection.commit()
    flash('Complaint updated.', 'success')
    return redirect(url_for('admin.complaints'))

# ── Visitors ─────────────────────────────────────────────────
@admin_bp.route('/visitors')
@login_required
@admin_required
def visitors():
    cur = get_cursor()
    cur.execute("""SELECT v.*, u.name AS resident_name, f.flat_no
                   FROM visitors v JOIN users u ON v.resident_id=u.id
                   LEFT JOIN flat_allocations fa ON u.id=fa.resident_id AND fa.is_current=1
                   LEFT JOIN flats f ON fa.flat_id=f.id
                   ORDER BY v.check_in DESC""")
    visitors = cur.fetchall()
    cur.close()
    return render_template('admin/visitors.html', visitors=visitors)

# ── Parking ──────────────────────────────────────────────────
@admin_bp.route('/parking')
@login_required
@admin_required
def parking():
    cur = get_cursor()
    cur.execute("""SELECT ps.*, u.name AS resident_name
                   FROM parking_slots ps LEFT JOIN users u ON ps.resident_id=u.id
                   ORDER BY ps.block, ps.slot_no""")
    slots = cur.fetchall()
    cur.execute("SELECT id,name FROM users WHERE role='resident' AND is_active=1 ORDER BY name")
    residents = cur.fetchall()
    cur.close()
    return render_template('admin/parking.html', slots=slots, residents=residents)

@admin_bp.route('/parking/assign', methods=['POST'])
@login_required
@admin_required
def assign_parking():
    try:
        cur = get_cursor()
        cur.execute("""UPDATE parking_slots SET resident_id=%s, vehicle_no=%s,
                       status='occupied', assigned_at=NOW() WHERE id=%s""",
                    (request.form['resident_id'], request.form['vehicle_no'], request.form['slot_id']))
        mysql.connection.commit()
        flash('Parking slot assigned.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.parking'))

@admin_bp.route('/parking/release/<int:sid>')
@login_required
@admin_required
def release_parking(sid):
    cur = get_cursor()
    cur.execute("UPDATE parking_slots SET resident_id=NULL, vehicle_no=NULL, status='available', assigned_at=NULL WHERE id=%s", (sid,))
    mysql.connection.commit()
    flash('Parking slot released.', 'success')
    return redirect(url_for('admin.parking'))

# ── Amenities ────────────────────────────────────────────────
@admin_bp.route('/amenities')
@login_required
@admin_required
def amenities():
    cur = get_cursor()
    cur.execute("SELECT * FROM amenities ORDER BY name")
    amenities = cur.fetchall()
    cur.execute("""SELECT ab.*, a.name AS amenity_name, u.name AS resident_name
                   FROM amenity_bookings ab JOIN amenities a ON ab.amenity_id=a.id
                   JOIN users u ON ab.resident_id=u.id
                   ORDER BY ab.booking_date DESC LIMIT 20""")
    bookings = cur.fetchall()
    cur.close()
    return render_template('admin/amenities.html', amenities=amenities, bookings=bookings)

@admin_bp.route('/amenities/update/<int:aid>', methods=['POST'])
@login_required
@admin_required
def update_amenity(aid):
    cur = get_cursor()
    cur.execute("UPDATE amenities SET status=%s WHERE id=%s",
                (request.form['status'], aid))
    mysql.connection.commit()
    flash('Amenity updated.', 'success')
    return redirect(url_for('admin.amenities'))

# ── Emergency ────────────────────────────────────────────────
@admin_bp.route('/emergency')
@login_required
@admin_required
def emergency():
    cur = get_cursor()
    cur.execute("""SELECT ea.*, u.name AS created_by_name
                   FROM emergency_alerts ea JOIN users u ON ea.created_by=u.id
                   ORDER BY ea.created_at DESC""")
    alerts = cur.fetchall()
    cur.close()
    return render_template('admin/emergency.html', alerts=alerts)

@admin_bp.route('/emergency/create', methods=['POST'])
@login_required
@admin_required
def create_alert():
    cur = get_cursor()
    cur.execute("""INSERT INTO emergency_alerts (created_by,type,title,description,severity)
                   VALUES (%s,%s,%s,%s,%s)""",
                (current_user.id, request.form['type'], request.form['title'],
                 request.form['description'], request.form['severity']))
    mysql.connection.commit()
    flash('Emergency alert created!', 'danger')
    return redirect(url_for('admin.emergency'))

@admin_bp.route('/emergency/resolve/<int:aid>')
@login_required
@admin_required
def resolve_alert(aid):
    cur = get_cursor()
    cur.execute("UPDATE emergency_alerts SET status='resolved', resolved_at=NOW() WHERE id=%s", (aid,))
    mysql.connection.commit()
    flash('Alert resolved.', 'success')
    return redirect(url_for('admin.emergency'))

# ── Staff Management ─────────────────────────────────────────
@admin_bp.route('/staff')
@login_required
@admin_required
def staff():
    cur = get_cursor()
    cur.execute("""SELECT u.*, COUNT(st.id) AS task_count
                   FROM users u LEFT JOIN staff_tasks st ON u.id=st.assigned_to
                   WHERE u.role IN ('staff','security','accountant')
                   GROUP BY u.id ORDER BY u.role, u.name""")
    staff_members = cur.fetchall()
    cur.close()
    return render_template('admin/staff.html', staff_members=staff_members)

@admin_bp.route('/staff/add', methods=['POST'])
@login_required
@admin_required
def add_staff():
    name  = request.form['name']
    email = request.form['email'].lower()
    role  = request.form['role']
    phone = request.form.get('phone','')
    pwd   = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt()).decode()
    try:
        cur = get_cursor()
        cur.execute("INSERT INTO users (name,email,password,role,phone) VALUES (%s,%s,%s,%s,%s)",
                    (name, email, pwd, role, phone))
        mysql.connection.commit()
        flash('Staff member added.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin.staff'))

@admin_bp.route('/staff/task/assign', methods=['POST'])
@login_required
@admin_required
def assign_task():
    cur = get_cursor()
    cur.execute("""INSERT INTO staff_tasks (assigned_to,assigned_by,title,description,category,priority,due_date)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (request.form['staff_id'], current_user.id, request.form['title'],
                 request.form.get('description',''), request.form['category'],
                 request.form['priority'], request.form['due_date']))
    mysql.connection.commit()
    flash('Task assigned.', 'success')
    return redirect(url_for('admin.staff'))

# ── Notices ──────────────────────────────────────────────────
@admin_bp.route('/notices')
@login_required
@admin_required
def notices():
    cur = get_cursor()
    cur.execute("SELECT n.*, u.name AS author FROM notices n JOIN users u ON n.created_by=u.id ORDER BY n.published_at DESC")
    notices = cur.fetchall()
    cur.close()
    return render_template('admin/notices.html', notices=notices)

@admin_bp.route('/notices/add', methods=['POST'])
@login_required
@admin_required
def add_notice():
    cur = get_cursor()
    cur.execute("""INSERT INTO notices (created_by,title,content,category,target_role,is_pinned)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (current_user.id, request.form['title'], request.form['content'],
                 request.form['category'], request.form['target_role'],
                 1 if request.form.get('is_pinned') else 0))
    mysql.connection.commit()
    flash('Notice published.', 'success')
    return redirect(url_for('admin.notices'))

@admin_bp.route('/notices/delete/<int:nid>')
@login_required
@admin_required
def delete_notice(nid):
    cur = get_cursor()
    cur.execute("DELETE FROM notices WHERE id=%s", (nid,))
    mysql.connection.commit()
    flash('Notice deleted.', 'success')
    return redirect(url_for('admin.notices'))

# ── Reports ──────────────────────────────────────────────────
@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    cur = get_cursor()
    cur.execute("""SELECT month, year, SUM(total) AS total, SUM(rent) AS rent,
                          SUM(maintenance) AS maintenance, COUNT(*) AS count,
                          SUM(CASE WHEN status='paid' THEN total ELSE 0 END) AS collected
                   FROM invoices GROUP BY year, month ORDER BY year DESC, month DESC LIMIT 12""")
    monthly = cur.fetchall()

    cur.execute("""SELECT f.block, COUNT(*) AS total,
                          SUM(f.status='occupied') AS occupied,
                          SUM(f.status='vacant') AS vacant
                   FROM flats f GROUP BY f.block""")
    flat_stats = cur.fetchall()

    cur.execute("""SELECT category, COUNT(*) AS count FROM maintenance_requests GROUP BY category""")
    maint_by_cat = cur.fetchall()

    cur.execute("""SELECT status, COUNT(*) AS count FROM complaints GROUP BY status""")
    complaint_stats = cur.fetchall()

    cur.close()
    return render_template('admin/reports.html', monthly=monthly,
                           flat_stats=flat_stats, maint_by_cat=maint_by_cat,
                           complaint_stats=complaint_stats)
