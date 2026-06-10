# extensions.py — shared Flask extensions (avoids circular imports)
from flask_mysqldb import MySQL
from flask_login import LoginManager

mysql = MySQL()
login_manager = LoginManager()
