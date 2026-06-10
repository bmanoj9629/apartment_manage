from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import mysql

staff_bp = Blueprint('staff', __name__)

def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'staff':
            flash('Staff access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_cursor():
    return mysql.connection.cursor()

# ── Dashboard ─────────────────────────────────────────────
@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    cur = get_cursor()
    cur.execute("SELECT COUNT(*) AS c FROM staff_tasks WHERE assigned_to=%s AND status='pending'", (current_user.id,)); pending = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM staff_tasks WHERE assigned_to=%s AND status='in_progress'", (current_user.id,)); in_progress = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM staff_tasks WHERE assigned_to=%s AND status='completed'", (current_user.id,)); completed = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM maintenance_requests WHERE assigned_to=%s AND status='in_progress'", (current_user.id,)); active_maintenance = cur.fetchone()['c']

    cur.execute("""SELECT st.*, u.name AS assigned_by_name FROM staff_tasks st
                   JOIN users u ON st.assigned_by=u.id
                   WHERE st.assigned_to=%s AND st.status != 'completed'
                   ORDER BY FIELD(st.priority,'urgent','high','medium','low'), st.due_date""",
                (current_user.id,))
    tasks = cur.fetchall()

    cur.execute("""SELECT mr.*, f.flat_no, u.name AS resident_name FROM maintenance_requests mr
                   JOIN flats f ON mr.flat_id=f.id JOIN users u ON mr.resident_id=u.id
                   WHERE mr.assigned_to=%s ORDER BY mr.requested_at DESC""", (current_user.id,))
    maintenance = cur.fetchall()

    cur.execute("SELECT * FROM notices WHERE (target_role='all' OR target_role='staff') AND (expires_at IS NULL OR expires_at > NOW()) ORDER BY is_pinned DESC, published_at DESC LIMIT 5")
    notices = cur.fetchall()
    cur.close()
    return render_template('staff/dashboard.html', pending=pending, in_progress=in_progress,
                           completed=completed, active_maintenance=active_maintenance,
                           tasks=tasks, maintenance=maintenance, notices=notices)

# ── Tasks ─────────────────────────────────────────────────
@staff_bp.route('/tasks')
@login_required
@staff_required
def tasks():
    status_filter = request.args.get('status', 'all')
    cur = get_cursor()
    sql = """SELECT st.*, u.name AS assigned_by_name FROM staff_tasks st
             JOIN users u ON st.assigned_by=u.id WHERE st.assigned_to=%s"""
    params = [current_user.id]
    if status_filter != 'all':
        sql += " AND st.status=%s"
        params.append(status_filter)
    sql += " ORDER BY st.created_at DESC"
    cur.execute(sql, params)
    tasks = cur.fetchall()
    cur.close()
    return render_template('staff/tasks.html', tasks=tasks, status_filter=status_filter)

@staff_bp.route('/tasks/update/<int:tid>', methods=['POST'])
@login_required
@staff_required
def update_task(tid):
    status = request.form['status']
    notes  = request.form.get('notes','')
    cur = get_cursor()
    if status == 'completed':
        cur.execute("UPDATE staff_tasks SET status=%s, notes=%s, completed_at=NOW() WHERE id=%s AND assigned_to=%s",
                    (status, notes, tid, current_user.id))
    else:
        cur.execute("UPDATE staff_tasks SET status=%s, notes=%s WHERE id=%s AND assigned_to=%s",
                    (status, notes, tid, current_user.id))
    mysql.connection.commit()
    flash('Task status updated.', 'success')
    return redirect(url_for('staff.tasks'))

# ── Maintenance ───────────────────────────────────────────
@staff_bp.route('/maintenance')
@login_required
@staff_required
def maintenance():
    cur = get_cursor()
    cur.execute("""SELECT mr.*, f.flat_no, u.name AS resident_name FROM maintenance_requests mr
                   JOIN flats f ON mr.flat_id=f.id JOIN users u ON mr.resident_id=u.id
                   WHERE mr.assigned_to=%s ORDER BY mr.requested_at DESC""", (current_user.id,))
    requests = cur.fetchall()
    cur.close()
    return render_template('staff/maintenance.html', requests=requests)

@staff_bp.route('/maintenance/update/<int:rid>', methods=['POST'])
@login_required
@staff_required
def update_maintenance(rid):
    status = request.form['status']
    notes  = request.form.get('notes','')
    cur = get_cursor()
    if status == 'completed':
        cur.execute("UPDATE maintenance_requests SET status=%s, notes=%s, completed_at=NOW() WHERE id=%s AND assigned_to=%s",
                    (status, notes, rid, current_user.id))
    else:
        cur.execute("UPDATE maintenance_requests SET status=%s, notes=%s WHERE id=%s AND assigned_to=%s",
                    (status, notes, rid, current_user.id))
    mysql.connection.commit()
    flash('Maintenance request updated.', 'success')
    return redirect(url_for('staff.maintenance'))

# ── Work History ──────────────────────────────────────────
@staff_bp.route('/history')
@login_required
@staff_required
def history():
    cur = get_cursor()
    cur.execute("""SELECT st.*, u.name AS assigned_by_name FROM staff_tasks st
                   JOIN users u ON st.assigned_by=u.id
                   WHERE st.assigned_to=%s AND st.status='completed'
                   ORDER BY st.completed_at DESC""", (current_user.id,))
    completed_tasks = cur.fetchall()
    cur.execute("""SELECT mr.*, f.flat_no FROM maintenance_requests mr
                   JOIN flats f ON mr.flat_id=f.id
                   WHERE mr.assigned_to=%s AND mr.status='completed'
                   ORDER BY mr.completed_at DESC""", (current_user.id,))
    completed_maintenance = cur.fetchall()
    cur.close()
    return render_template('staff/history.html', completed_tasks=completed_tasks,
                           completed_maintenance=completed_maintenance)
