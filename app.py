from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from functools import wraps
import random

app = Flask(__name__)

# Khóa bí mật dùng cho session
app.secret_key = "website-goi-y-mon-an-secret-key"


# =========================
# KẾT NỐI MYSQL
# =========================

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="monan"
    )


# =========================
# TRANG ĐĂNG NHẬP
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Nếu người dùng truy cập trang login
    if request.method == "GET":

        return render_template("login.html")


    # =========================
    # LẤY DỮ LIỆU FORM
    # =========================

    email = request.form.get("email", "").strip()
    matkhau = request.form.get("matkhau", "")


    # =========================
    # KIỂM TRA DỮ LIỆU
    # =========================

    if not email:

        flash("Vui lòng nhập email.", "error")

        return redirect(url_for("login"))


    if not matkhau:

        flash("Vui lòng nhập mật khẩu.", "error")

        return redirect(url_for("login"))


    # =========================
    # KẾT NỐI DATABASE
    # =========================

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)


        # =========================
        # TÌM NGƯỜI DÙNG
        # =========================

        sql = """
            SELECT
                manguoidung,
                hoten,
                email,
                matkhau
            FROM nguoidung
            WHERE email = %s
            LIMIT 1
        """

        cursor.execute(sql, (email,))

        user = cursor.fetchone()


        # =========================
        # KIỂM TRA TÀI KHOẢN
        # =========================

        if user is None:

            flash(
                "Email hoặc mật khẩu không chính xác.",
                "error"
            )

            return redirect(url_for("login"))


        # =========================
        # KIỂM TRA MẬT KHẨU
        # =========================

        if user["matkhau"] != matkhau:

            flash(
                "Email hoặc mật khẩu không chính xác.",
                "error"
            )

            return redirect(url_for("login"))


        # =========================
        # LƯU SESSION
        # =========================

        session["manguoidung"] = user["manguoidung"]

        session["hoten"] = user["hoten"]

        session["email"] = user["email"]


        # =========================
        # THÔNG BÁO
        # =========================

        flash(
            f"Đăng nhập thành công. Xin chào {user['hoten']}!",
            "success"
        )


        # =========================
        # CHUYỂN VỀ TRANG CHỦ
        # =========================

        return redirect(url_for("home"))


    except mysql.connector.Error as e:

        print("Lỗi MySQL:", e)

        flash(
            "Không thể kết nối đến cơ sở dữ liệu.",
            "error"
        )

        return redirect(url_for("login"))


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================
# TRANG CHỦ
# =========================

# =========================
# TRANG CHỦ
# =========================

@app.route("/")
def home():

    conn = None
    cursor = None

    try:

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)


        # =========================
        # LẤY DANH SÁCH MÓN ĂN
        # =========================

        sql = """
            SELECT
                m.mamon,
                m.tenmon,
                m.mota,
                m.thoigian,
                m.chiphi,
                m.kcal,
                m.madanhmuc,
                d.tendanhmuc
            FROM monan m
            LEFT JOIN danhmuc d
                ON m.madanhmuc = d.madanhmuc
            ORDER BY m.mamon DESC
            LIMIT 8
        """

        cursor.execute(sql)

        foods = cursor.fetchall()


        return render_template(
            "user/home.html",
            foods=foods
        )


    except mysql.connector.Error as e:

        print("Lỗi MySQL:", e)

        flash(
            "Không thể tải danh sách món ăn.",
            "error"
        )

        return render_template(
            "user/home.html",
            foods=[]
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()
# =========================
# ĐĂNG XUẤT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Bạn đã đăng xuất.",
        "success"
    )

    return redirect(url_for("login"))





    # =========================
# ĐĂNG KÝ TÀI KHOẢN
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    # Khi mở trang đăng ký
    if request.method == "GET":

        return render_template("user/register.html")


    # =========================
    # LẤY DỮ LIỆU TỪ FORM
    # =========================

    hoten = request.form.get("hoten", "").strip()

    email = request.form.get("email", "").strip()

    matkhau = request.form.get("matkhau", "")

    xacnhanmatkhau = request.form.get(
        "xacnhanmatkhau",
        ""
    )


    # =========================
    # KIỂM TRA HỌ TÊN
    # =========================

    if not hoten:

        flash(
            "Vui lòng nhập họ và tên.",
            "error"
        )

        return redirect(url_for("register"))


    # =========================
    # KIỂM TRA EMAIL
    # =========================

    if not email:

        flash(
            "Vui lòng nhập email.",
            "error"
        )

        return redirect(url_for("register"))


    # =========================
    # KIỂM TRA MẬT KHẨU
    # =========================

    if not matkhau:

        flash(
            "Vui lòng nhập mật khẩu.",
            "error"
        )

        return redirect(url_for("register"))


    if len(matkhau) < 6:

        flash(
            "Mật khẩu phải có ít nhất 6 ký tự.",
            "error"
        )

        return redirect(url_for("register"))


    # =========================
    # KIỂM TRA XÁC NHẬN
    # =========================

    if matkhau != xacnhanmatkhau:

        flash(
            "Mật khẩu xác nhận không khớp.",
            "error"
        )

        return redirect(url_for("register"))


    conn = None
    cursor = None

    try:

        # =========================
        # KẾT NỐI MYSQL
        # =========================

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)


        # =========================
        # KIỂM TRA EMAIL ĐÃ TỒN TẠI
        # =========================

        sql_check = """
            SELECT manguoidung
            FROM nguoidung
            WHERE email = %s
            LIMIT 1
        """

        cursor.execute(
            sql_check,
            (email,)
        )

        existing_user = cursor.fetchone()


        if existing_user:

            flash(
                "Email này đã được đăng ký.",
                "error"
            )

            return redirect(
                url_for("register")
            )


        # =========================
        # THÊM NGƯỜI DÙNG
        # =========================

        sql_insert = """
            INSERT INTO nguoidung
                (hoten, email, matkhau)
            VALUES
                (%s, %s, %s)
        """

        cursor.execute(
            sql_insert,
            (
                hoten,
                email,
                matkhau
            )
        )


        # =========================
        # LƯU THAY ĐỔI
        # =========================

        conn.commit()


        # =========================
        # THÔNG BÁO
        # =========================

        flash(
            "Đăng ký tài khoản thành công. Vui lòng đăng nhập.",
            "success"
        )


        # =========================
        # CHUYỂN SANG LOGIN
        # =========================

        return redirect(
            url_for("login")
        )


    except mysql.connector.Error as e:

        print("Lỗi MySQL:", e)

        if conn:

            conn.rollback()

        flash(
            "Có lỗi xảy ra khi đăng ký tài khoản.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    finally:

        if cursor:

            cursor.close()

        if conn:

            conn.close()




# =========================
# TÌM KIẾM MÓN ĂN
# =========================

@app.route("/search", methods=["GET"])
def search():

    # Lấy từ khóa từ URL
    keyword = request.args.get(
        "q",
        ""
    ).strip()


    conn = None
    cursor = None

    try:

        # =========================
        # KẾT NỐI MYSQL
        # =========================

        conn = get_db_connection()

        cursor = conn.cursor(
            dictionary=True
        )


        # =========================
        # NẾU KHÔNG NHẬP TỪ KHÓA
        # =========================

        if keyword == "":

            sql = """
                SELECT
                    m.mamon,
                    m.tenmon,
                    m.mota,
                    m.thoigian,
                    m.chiphi,
                    m.kcal,
                    m.madanhmuc,
                    d.tendanhmuc
                FROM monan m
                LEFT JOIN danhmuc d
                    ON m.madanhmuc = d.madanhmuc
                ORDER BY m.mamon DESC
            """

            cursor.execute(sql)


        # =========================
        # CÓ TỪ KHÓA
        # =========================

        else:

            search_keyword = f"%{keyword}%"

            sql = """
                SELECT
                    m.mamon,
                    m.tenmon,
                    m.mota,
                    m.thoigian,
                    m.chiphi,
                    m.kcal,
                    m.madanhmuc,
                    d.tendanhmuc
                FROM monan m
                LEFT JOIN danhmuc d
                    ON m.madanhmuc = d.madanhmuc
                WHERE
                    m.tenmon LIKE %s
                    OR m.mota LIKE %s
                    OR m.nguyenlieu LIKE %s
                ORDER BY m.mamon DESC
            """

            cursor.execute(
                sql,
                (
                    search_keyword,
                    search_keyword,
                    search_keyword
                )
            )


        # =========================
        # LẤY KẾT QUẢ
        # =========================

        foods = cursor.fetchall()


        # =========================
        # HIỂN THỊ SEARCH.HTML
        # =========================

        return render_template(
            "user/search.html",
            foods=foods,
            keyword=keyword
        )


    except mysql.connector.Error as e:

        print("Lỗi MySQL:", e)

        flash(
            "Không thể tìm kiếm món ăn.",
            "error"
        )

        return render_template(
            "user/search.html",
            foods=[],
            keyword=keyword
        )


    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()



@app.route("/today")
def today():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT
                m.mamon,
                m.tenmon,
                m.mota,
                m.thoigian,
                m.chiphi,
                m.kcal,
                m.madanhmuc,
                d.tendanhmuc
            FROM monan m
            LEFT JOIN danhmuc d
                ON m.madanhmuc = d.madanhmuc
            ORDER BY RAND()
            LIMIT 6
        """

        cursor.execute(sql)
        foods = cursor.fetchall()

        return render_template(
            "user/today.html",
            foods=foods
        )

    except mysql.connector.Error as e:
        print("Lỗi MySQL:", e)

        flash(
            "Không thể tải danh sách món ăn.",
            "error"
        )

        return render_template(
            "user/today.html",
            foods=[]
        )

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()





@app.route("/food/<int:mamon>")
def food_detail(mamon):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT
                m.mamon,
                m.tenmon,
                m.mota,
                m.madanhmuc,
                m.nguyenlieu,
                m.soluong,
                m.thoigian,
                m.chiphi,
                m.kcal,
                d.tendanhmuc
            FROM monan m
            LEFT JOIN danhmuc d
                ON m.madanhmuc = d.madanhmuc
            WHERE m.mamon = %s
        """

        cursor.execute(sql, (mamon,))
        food = cursor.fetchone()

        if food is None:
            flash("Không tìm thấy món ăn.", "error")
            return redirect(url_for("home"))

        return render_template(
            "user/food_detail.html",
            food=food
        )

    except mysql.connector.Error as e:
        print("Lỗi MySQL:", e)

        flash(
            "Không thể tải thông tin món ăn.",
            "error"
        )

        return redirect(url_for("home"))

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()




# =========================
# CHẠY ỨNG DỤNG
# =========================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=3000,
        debug=True
    )