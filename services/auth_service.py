from database import get_db_connection
from werkzeug.security import generate_password_hash


def email_exists(email):
    conn = get_db_connection()

    if conn is None:
        return False

    cursor = conn.cursor()

    try:
        sql = """
            SELECT manguoidung
            FROM nguoidung
            WHERE email = %s
            LIMIT 1
        """

        cursor.execute(sql, (email,))

        return cursor.fetchone() is not None

    except Exception as e:
        print("❌ Lỗi kiểm tra email:")
        print(e)
        return False

    finally:
        cursor.close()
        conn.close()


def create_user(hoten, email, matkhau):
    conn = get_db_connection()

    if conn is None:
        return False

    cursor = conn.cursor()

    try:
        password_hash = generate_password_hash(matkhau)

        sql = """
            INSERT INTO nguoidung
            (
                hoten,
                email,
                matkhau,
                quyen
            )
            VALUES
            (
                %s,
                %s,
                %s,
                'user'
            )
        """

        cursor.execute(
            sql,
            (
                hoten,
                email,
                password_hash
            )
        )

        conn.commit()

        print("✅ Tạo tài khoản thành công")

        return True

    except Exception as e:
        conn.rollback()

        print("❌ Lỗi tạo tài khoản:")
        print(e)

        return False

    finally:
        cursor.close()
        conn.close()


def get_user_by_email(email):
    conn = get_db_connection()

    if conn is None:
        return None

    cursor = conn.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                manguoidung,
                hoten,
                email,
                matkhau,
                quyen
            FROM nguoidung
            WHERE email = %s
            LIMIT 1
        """

        cursor.execute(sql, (email,))

        return cursor.fetchone()

    except Exception as e:
        print("❌ Lỗi lấy thông tin người dùng:")
        print(e)

        return None

    finally:
        cursor.close()
        conn.close()