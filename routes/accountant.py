from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from functools import wraps
from extensions import mysql

accountant_bp = Blueprint('accountant', __name__)

def accountant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'accountant':
            flash('Accountant access required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def get_cursor():
    return mysql.connection.cursor()

# ── Dashboard ─────────────────────────────────────────────
@accountant_bp.route('/dashboard')
@login_required
@accountant_required
def dashboard():
    cur = get_cursor()
    cur.execute("SELECT COALESCE(SUM(total),0) AS c FROM invoices WHERE status='unpaid'"); unpaid = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total),0) AS c FROM invoices WHERE status='paid' AND MONTH(paid_at)=MONTH(NOW()) AND YEAR(paid_at)=YEAR(NOW())"); monthly_collected = cur.fetchone()['c']
    cur.execute("SELECT COALESCE(SUM(total),0) AS c FROM invoices WHERE status='overdue'"); overdue = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM invoices WHERE status='unpaid'"); unpaid_count = cur.fetchone()['c']

    cur.execute("""SELECT i.*, u.name AS resident_name, f.flat_no
                   FROM invoices i JOIN users u ON i.resident_id=u.id
                   JOIN flats f ON i.flat_id=f.id
                   WHERE i.status IN ('unpaid','overdue')
                   ORDER BY i.due_date ASC LIMIT 10""")
    pending_invoices = cur.fetchall()

    cur.execute("""SELECT month, COALESCE(SUM(total),0) AS total,
                          COALESCE(SUM(CASE WHEN status='paid' THEN total ELSE 0 END),0) AS collected
                   FROM invoices WHERE year=YEAR(NOW())
                   GROUP BY month ORDER BY month""")
    monthly_data = cur.fetchall()

    cur.close()
    return render_template('accountant/dashboard.html', unpaid=unpaid,
                           monthly_collected=monthly_collected, overdue=overdue,
                           unpaid_count=unpaid_count, pending_invoices=pending_invoices,
                           monthly_data=monthly_data)

# ── Billing ───────────────────────────────────────────────
@accountant_bp.route('/billing')
@login_required
@accountant_required
def billing():
    cur = get_cursor()
    status_filter = request.args.get('status', 'all')
    month_filter  = request.args.get('month', '')
    sql = """SELECT i.*, u.name AS resident_name, f.flat_no
             FROM invoices i JOIN users u ON i.resident_id=u.id
             JOIN flats f ON i.flat_id=f.id WHERE 1=1"""
    params = []
    if status_filter != 'all':
        sql += " AND i.status=%s"; params.append(status_filter)
    if month_filter:
        sql += " AND i.month=%s"; params.append(month_filter)
    sql += " ORDER BY i.year DESC, i.month DESC, i.due_date ASC"
    cur.execute(sql, params)
    invoices = cur.fetchall()

    cur.execute("SELECT id, name FROM users WHERE role='resident' AND is_active=1 ORDER BY name")
    residents = cur.fetchall()
    cur.execute("SELECT id, flat_no FROM flats WHERE status='occupied' ORDER BY flat_no")
    occupied_flats = cur.fetchall()
    cur.close()
    return render_template('accountant/billing.html', invoices=invoices,
                           residents=residents, occupied_flats=occupied_flats,
                           status_filter=status_filter, month_filter=month_filter)

@accountant_bp.route('/billing/generate', methods=['POST'])
@login_required
@accountant_required
def generate_invoice():
    try:
        cur = get_cursor()
        cur.execute("""INSERT INTO invoices (resident_id,flat_id,month,year,rent,maintenance,electricity,water,parking,other,due_date,status)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'unpaid')""",
                    (request.form['resident_id'], request.form['flat_id'],
                     request.form['month'], request.form['year'],
                     request.form.get('rent',0), request.form.get('maintenance',0),
                     request.form.get('electricity',0), request.form.get('water',0),
                     request.form.get('parking',0), request.form.get('other',0),
                     request.form['due_date']))
        mysql.connection.commit()
        flash('Invoice generated successfully.', 'success')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('accountant.billing'))

@accountant_bp.route('/billing/mark-paid/<int:iid>')
@login_required
@accountant_required
def mark_paid(iid):
    cur = get_cursor()
    cur.execute("UPDATE invoices SET status='paid', paid_at=NOW() WHERE id=%s", (iid,))
    mysql.connection.commit()
    flash('Invoice marked as paid.', 'success')
    return redirect(url_for('accountant.billing'))

@accountant_bp.route('/billing/mark-overdue/<int:iid>')
@login_required
@accountant_required
def mark_overdue(iid):
    cur = get_cursor()
    cur.execute("UPDATE invoices SET status='overdue' WHERE id=%s AND status='unpaid'", (iid,))
    mysql.connection.commit()
    flash('Invoice marked as overdue.', 'warning')
    return redirect(url_for('accountant.billing'))

# ── Reports ───────────────────────────────────────────────
@accountant_bp.route('/reports')
@login_required
@accountant_required
def reports():
    cur = get_cursor()
    cur.execute("""SELECT month, year, COUNT(*) AS count,
                          COALESCE(SUM(total),0) AS total_billed,
                          COALESCE(SUM(CASE WHEN status='paid' THEN total ELSE 0 END),0) AS collected,
                          COALESCE(SUM(CASE WHEN status IN ('unpaid','overdue') THEN total ELSE 0 END),0) AS outstanding
                   FROM invoices GROUP BY year, month ORDER BY year DESC, month DESC LIMIT 12""")
    monthly = cur.fetchall()

    cur.execute("""SELECT u.name AS resident, f.flat_no,
                          COUNT(i.id) AS invoice_count,
                          COALESCE(SUM(i.total),0) AS total_billed,
                          COALESCE(SUM(CASE WHEN i.status='paid' THEN i.total ELSE 0 END),0) AS paid_amount
                   FROM invoices i JOIN users u ON i.resident_id=u.id JOIN flats f ON i.flat_id=f.id
                   GROUP BY i.resident_id ORDER BY total_billed DESC""")
    by_resident = cur.fetchall()

    cur.execute("""SELECT COALESCE(SUM(CASE WHEN status='paid' THEN total ELSE 0 END),0) AS paid,
                          COALESCE(SUM(CASE WHEN status='unpaid' THEN total ELSE 0 END),0) AS unpaid,
                          COALESCE(SUM(CASE WHEN status='overdue' THEN total ELSE 0 END),0) AS overdue,
                          COALESCE(SUM(total),0) AS grand_total FROM invoices""")
    totals = cur.fetchone()
    cur.close()
    return render_template('accountant/reports.html', monthly=monthly,
                           by_resident=by_resident, totals=totals)
