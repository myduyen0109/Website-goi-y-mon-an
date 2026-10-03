from database import get_db_connection


def save_behavior(
    manguoidung,
    mamon=None,
    loaihanhvi=None,
    tukhoa=None,
    ngansach=None
):
    conn = get_db_connection()

    if conn is None:
        return False

    cursor = conn.cursor()

    try:
        sql = """
            INSERT INTO hanhvi
            (
                manguoidung,
                mamon,
                loaihanhvi,
                tukhoa,
                ngansach
            )
            VALUES (%s, %s, %s, %s, %s)
        """

        cursor.execute(
            sql,
            (
                manguoidung,
                mamon,
                loaihanhvi,
                tukhoa,
                ngansach
            )
        )

        conn.commit()

        print("✅ Đã lưu hành vi người dùng")

        return True

    except Exception as e:
        conn.rollback()

        print("❌ Lỗi lưu hành vi:")
        print(e)

        return False

    finally:
        cursor.close()
        conn.close()