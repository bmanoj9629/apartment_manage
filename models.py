from flask_login import UserMixin
from extensions import mysql
from MySQLdb.cursors import DictCursor

class User(UserMixin):
    def __init__(self, id, name, email, role, phone=None, avatar=None, is_active=True):
        self.id      = id
        self.name    = name
        self.email   = email
        self.role    = role
        self.phone   = phone
        self.avatar  = avatar or 'default_avatar.png'
        self._active = is_active

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return bool(self._active)

    @staticmethod
    def get_by_id(user_id):
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            return User(row['id'], row['name'], row['email'], row['role'],
                        row['phone'], row['avatar'], row['is_active'])
        return None

    @staticmethod
    def get_by_email(email):
        cur = mysql.connection.cursor(DictCursor)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        cur.close()
        return row
