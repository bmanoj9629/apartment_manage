from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import mysql

security_bp = Blueprint('security', __name__)

def security_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'security':
            flash('Security access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_cursor():
    return mysql.connection.cursor()

# ── Dashboard ─────────────────────────────────────────────
@security_bp.route('/dashboard')
@login_required
@security_required
def dashboard():
    cur = get_cursor()
    cur.execute("SELECT COUNT(*) AS c FROM visitors WHERE status='checked_in'"); active_visitors = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM visitors WHERE status='pending'"); pending_visitors = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM parking_slots WHERE status='available'"); avail_parking = cur.fetchone()['c']
    cur.execute("SELECT * FROM emergency_alerts WHERE status='active' ORDER BY created_at DESC")
    alerts = cur.fetchall()

    cur.execute("""SELECT v.*, u.name AS resident_name, f.flat_no
                   FROM visitors v JOIN users u ON v.resident_id=u.id
                   LEFT JOIN flat_allocations fa ON u.id=fa.resident_id AND fa.is_current=1
                   LEFT JOIN flats f ON fa.flat_id=f.id
                   WHERE v.status IN ('pending','checked_in')
                   ORDER BY v.check_in DESC LIMIT 10""")
    recent_visitors = cur.fetchall()

    cur.execute("""SELECT vl.*, v.visitor_name, u.name AS security_name
                   FROM visitor_log vl JOIN visitors v ON vl.visitor_id=v.id
                   JOIN users u ON vl.security_id=u.id
                   ORDER BY vl.timestamp DESC LIMIT 10""")
    recent_log = cur.fetchall()

    cur.close()
    return render_template('security/dashboard.html',
                           active_visitors=active_visitors, pending_visitors=pending_visitors,
                           avail_parking=avail_parking, alerts=alerts,
                           recent_visitors=recent_visitors, recent_log=recent_log)

# ── Visitors ──────────────────────────────────────────────
@security_bp.route('/visitors')
@login_required
@security_required
def visitors():
    status_filter = request.args.get('status', 'all')
    cur = get_cursor()
    sql = """SELECT v.*, u.name AS resident_name, f.flat_no
             FROM visitors v JOIN users u ON v.resident_id=u.id
             LEFT JOIN flat_allocations fa ON u.id=fa.resident_id AND fa.is_current=1
             LEFT JOIN flats f ON fa.flat_id=f.id"""
    if status_filter != 'all':
        sql += f" WHERE v.status='{status_filter}'"
    sql += " ORDER BY v.check_in DESC"
    cur.execute(sql)
    visitors = cur.fetchall()
    cur.close()
    return render_template('security/visitors.html', visitors=visitors, status_filter=status_filter)

@security_bp.route('/visitors/action/<int:vid>', methods=['POST'])
@login_required
@security_required
def visitor_action(vid):
    action = request.form['action']
    remarks = request.form.get('remarks', '')
    cur = get_cursor()

    status_map = {'approve': 'approved', 'check_in': 'checked_in',
                  'check_out': 'checked_out', 'deny': 'denied'}
    new_status = status_map.get(action, 'pending')

    if action == 'check_out':
        cur.execute("UPDATE visitors SET status=%s, check_out=NOW(), approved_by=%s WHERE id=%s",
                    (new_status, current_user.id, vid))
    else:
        cur.execute("UPDATE visitors SET status=%s, approved_by=%s WHERE id=%s",
                    (new_status, current_user.id, vid))

    log_action = 'check_in' if action == 'check_in' else ('check_out' if action == 'check_out' else 'denied')
    cur.execute("""INSERT INTO visitor_log (visitor_id, security_id, action, remarks)
                   VALUES (%s,%s,%s,%s)""", (vid, current_user.id, log_action, remarks))
    mysql.connection.commit()
    flash(f'Visitor {action.replace("_"," ")} recorded.', 'success')
    return redirect(url_for('security.visitors'))

# ── Log Visitor (walk-in) ─────────────────────────────────
@security_bp.route('/log-visitor', methods=['GET', 'POST'])
@login_required
@security_required
def log_visitor():
    cur = get_cursor()
    cur.execute("SELECT u.id, u.name, f.flat_no FROM users u LEFT JOIN flat_allocations fa ON u.id=fa.resident_id AND fa.is_current=1 LEFT JOIN flats f ON fa.flat_id=f.id WHERE u.role='resident' AND u.is_active=1 ORDER BY u.name")
    residents = cur.fetchall()
    if request.method == 'POST':
        cur.execute("""INSERT INTO visitors (resident_id,visitor_name,phone,purpose,vehicle_no,status,approved_by)
                       VALUES (%s,%s,%s,%s,%s,'checked_in',%s)""",
                    (request.form['resident_id'], request.form['visitor_name'],
                     request.form.get('phone',''), request.form.get('purpose',''),
                     request.form.get('vehicle_no',''), current_user.id))
        vid = cur.lastrowid
        cur.execute("INSERT INTO visitor_log (visitor_id,security_id,action) VALUES (%s,%s,'check_in')", (vid, current_user.id))
        mysql.connection.commit()
        flash('Walk-in visitor logged and checked in.', 'success')
        return redirect(url_for('security.visitors'))
    cur.close()
    return render_template('security/log_visitor.html', residents=residents)

# ── Parking ───────────────────────────────────────────────
@security_bp.route('/parking')
@login_required
@security_required
def parking():
    cur = get_cursor()
    cur.execute("""SELECT ps.*, u.name AS resident_name
                   FROM parking_slots ps LEFT JOIN users u ON ps.resident_id=u.id
                   ORDER BY ps.block, ps.level, ps.slot_no""")
    slots = cur.fetchall()
    cur.close()
    return render_template('security/parking.html', slots=slots)

# ── Emergency ─────────────────────────────────────────────
@security_bp.route('/emergency')
@login_required
@security_required
def emergency():
    cur = get_cursor()
    cur.execute("""SELECT ea.*, u.name AS created_by_name
                   FROM emergency_alerts ea JOIN users u ON ea.created_by=u.id
                   ORDER BY ea.created_at DESC""")
    alerts = cur.fetchall()
    cur.close()
    return render_template('security/emergency.html', alerts=alerts)

@security_bp.route('/emergency/report', methods=['POST'])
@login_required
@security_required
def report_emergency():
    cur = get_cursor()
    cur.execute("""INSERT INTO emergency_alerts (created_by,type,title,description,severity)
                   VALUES (%s,%s,%s,%s,%s)""",
                (current_user.id, request.form['type'], request.form['title'],
                 request.form.get('description',''), request.form['severity']))
    mysql.connection.commit()
    flash('Emergency alert reported!', 'danger')
    return redirect(url_for('security.emergency'))
