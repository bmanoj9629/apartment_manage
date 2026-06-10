from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from extensions import mysql
import bcrypt

auth_bp = Blueprint('auth', __name__)

def log_activity(user_id, action, details='', ip=''):
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO activity_log (user_id, action, details, ip_address) VALUES (%s,%s,%s,%s)",
                    (user_id, action, details, ip))
        mysql.connection.commit()
        cur.close()
    except Exception:
        pass

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(f'{current_user.role}.dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/login.html')

        row = User.get_by_email(email)
        if not row:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        if not bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        if not row['is_active']:
            flash('Your account has been deactivated. Contact admin.', 'warning')
            return render_template('auth/login.html')

        user = User(row['id'], row['name'], row['email'], row['role'],
                    row['phone'], row['avatar'], row['is_active'])
        login_user(user, remember=request.form.get('remember'))
        log_activity(user.id, 'LOGIN', f'User {user.email} logged in', request.remote_addr)

        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for(f'{user.role}.dashboard'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'LOGOUT', f'User {current_user.email} logged out', request.remote_addr)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
