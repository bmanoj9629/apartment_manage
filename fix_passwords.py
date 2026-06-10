import bcrypt
import mysql.connector

# Connect directly to the DB and update all user passwords to the proper bcrypt hash for 'admin123'
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="apartment_manage"
    )
    cursor = conn.cursor()
    
    # Generate proper hash
    hashed = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8')
    
    # Update all
    cursor.execute("UPDATE users SET password = %s", (hashed,))
    conn.commit()
    print("Passwords fixed! Rows affected:", cursor.rowcount)
    
except Exception as e:
    print("Error:", e)
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()
