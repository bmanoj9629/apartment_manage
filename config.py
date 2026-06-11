import os

class Config:
    SECRET_KEY = "your-secret-key"

    # ADD THIS (IMPORTANT)
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")

    # if you use MySQL
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_DB = os.getenv("MYSQL_DB")