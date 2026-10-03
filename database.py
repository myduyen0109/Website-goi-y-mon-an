import mysql.connector
from mysql.connector import Error


def get_db_connection():
    """
    Tạo kết nối đến database MySQL 'monan'.
    """

    try:
        conn = mysql.connector.connect(
            host="127.0.0.1",
            port=3306,
            user="duyen",
            password="",
            database="monan",
            charset="utf8mb4",
            use_pure=True   
        )

        if conn.is_connected():
            print("✅ KẾT NỐI MYSQL THÀNH CÔNG")
            return conn

        print("❌ Không thể kết nối MySQL")
        return None

    except Error as e:
        print("❌ LỖI KẾT NỐI MYSQL")
        print("Chi tiết:", e)
        return None