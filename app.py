from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.security import check_password_hash

from database import get_db_connection

from services.auth_service import (
    email_exists,
    create_user,
    get_user_by_email
)

from services.behavior_service import save_behavior


from services.recommendation_service import sort_foods_by_behavior





app = Flask(__name__)

app.secret_key = "website-goi-y-mon-an-secret-key"


# ==========================================
# TRANG CHỦ
# ==========================================

@app.route("/")
def home():

    return render_template(
        "user/home.html"
    )


# ==========================================
# KIỂM TRA DATABASE
# ==========================================

@app.route("/test-db")
def test_database():

    conn = get_db_connection()

    if conn is None:

        return """
        <h2>❌ Kết nối Database thất bại</h2>
        """

    try:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT DATABASE()"
        )

        database_name = cursor.fetchone()[0]

        cursor.close()

        conn.close()

        return f"""
        <!DOCTYPE html>

        <html lang="vi">

        <head>
            <meta charset="UTF-8">
            <title>Kiểm tra Database</title>
        </head>

        <body>

            <h1>
                ✅ Kết nối Database thành công
            </h1>

            <p>
                Database hiện tại:
                <strong>{database_name}</strong>
            </p>

            <a href="/">
                ← Trang chủ
            </a>

        </body>

        </html>
        """

    except Exception as e:

        return f"""
        <h2>
            ❌ Lỗi khi kiểm tra Database
        </h2>

        <p>
            {e}
        </p>
        """


# ==========================================
# ĐĂNG KÝ
# ==========================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    # -------------------------------
    # HIỂN THỊ TRANG ĐĂNG KÝ
    # -------------------------------

    if request.method == "GET":

        return render_template(
            "user/register.html"
        )


    # -------------------------------
    # LẤY DỮ LIỆU FORM
    # -------------------------------

    hoten = request.form.get(
        "hoten",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    matkhau = request.form.get(
        "matkhau",
        ""
    )

    xacnhan_matkhau = request.form.get(
        "xacnhan_matkhau",
        ""
    )


    # -------------------------------
    # KIỂM TRA HỌ TÊN
    # -------------------------------

    if not hoten:

        flash(
            "Vui lòng nhập họ và tên.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    # -------------------------------
    # KIỂM TRA EMAIL
    # -------------------------------

    if not email:

        flash(
            "Vui lòng nhập email.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    # -------------------------------
    # KIỂM TRA MẬT KHẨU
    # -------------------------------

    if len(matkhau) < 6:

        flash(
            "Mật khẩu phải có ít nhất 6 ký tự.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    # -------------------------------
    # KIỂM TRA XÁC NHẬN MẬT KHẨU
    # -------------------------------

    if matkhau != xacnhan_matkhau:

        flash(
            "Mật khẩu xác nhận không khớp.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    # -------------------------------
    # KIỂM TRA EMAIL ĐÃ TỒN TẠI
    # -------------------------------

    if email_exists(email):

        flash(
            "Email này đã được đăng ký.",
            "error"
        )

        return redirect(
            url_for("register")
        )


    # -------------------------------
    # TẠO TÀI KHOẢN
    # -------------------------------

    success = create_user(
        hoten,
        email,
        matkhau
    )


    if success:

        flash(
            "Đăng ký tài khoản thành công!",
            "success"
        )

        return redirect(
            url_for("register")
        )


    else:

        flash(
            "Không thể tạo tài khoản. Vui lòng thử lại.",
            "error"
        )

        return redirect(
            url_for("register")
        )

















# ==========================================
# route đăng nhập
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # Hiển thị trang đăng nhập
    if request.method == "GET":
        return render_template("user/login.html")

    # Lấy dữ liệu form
    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    matkhau = request.form.get(
        "matkhau",
        ""
    )

    # Kiểm tra email
    if not email:

        flash(
            "Vui lòng nhập email.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # Kiểm tra mật khẩu
    if not matkhau:

        flash(
            "Vui lòng nhập mật khẩu.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # Tìm người dùng
    user = get_user_by_email(email)

    # Không tìm thấy tài khoản
    if user is None:

        flash(
            "Email hoặc mật khẩu không đúng.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # Kiểm tra mật khẩu
    if not check_password_hash(
        user["matkhau"],
        matkhau
    ):

        flash(
            "Email hoặc mật khẩu không đúng.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    # Lưu thông tin đăng nhập vào session
    session["manguoidung"] = user["manguoidung"]
    session["hoten"] = user["hoten"]
    session["email"] = user["email"]
    session["quyen"] = user["quyen"]

    flash(
        "Đăng nhập thành công!",
        "success"
    )

    return redirect(
        url_for("home")
    )




# ==========================================
# Đăng xuất
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Bạn đã đăng xuất.",
        "success"
    )

    return redirect(
        url_for("home")
    )




# ==========================================
# Tìm kiếm
# ==========================================
@app.route("/search", methods=["GET", "POST"])
def search():

    keyword = ""
    budget = ""
    category = ""
    max_time = ""
    max_kcal = ""
    foods = []
    categories = []

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    # ==========================================
    # LẤY DANH MỤC
    # ==========================================

    cursor.execute("""
        SELECT
            madanhmuc,
            tendanhmuc
        FROM danhmuc
        ORDER BY tendanhmuc
    """)

    categories = cursor.fetchall()

    # ==========================================
    # XỬ LÝ TÌM KIẾM
    # ==========================================

    if request.method == "POST":

        keyword = request.form.get("keyword", "").strip()
        budget = request.form.get("budget", "").strip()
        category = request.form.get("category", "").strip()
        max_time = request.form.get("max_time", "").strip()
        max_kcal = request.form.get("max_kcal", "").strip()

        if "manguoidung" in session:
            behavior_budget = None

            if budget:
                try:
                    behavior_budget = float(budget)
                except ValueError:
                    behavior_budget = None

            save_behavior(
                manguoidung=session["manguoidung"],
                loaihanhvi="tim_kiem",
                tukhoa=keyword,
                ngansach=behavior_budget
            )

        conditions = []
        params = []

        # ==========================================
        # TÌM THEO TÊN MÓN / NGUYÊN LIỆU
        # ==========================================

        if keyword:

            keywords = [
                item.strip()
                for item in keyword.split(",")
                if item.strip()
            ]

            # -------------------------------
            # Một từ khóa
            # -------------------------------

            if len(keywords) == 1:

                search_value = f"%{keywords[0]}%"

                conditions.append("""
                    (
                        m.tenmon LIKE %s

                        OR EXISTS (
                            SELECT 1
                            FROM monan_nguyenlieu mn
                            JOIN nguyenlieu n
                                ON mn.manguyenlieu = n.manguyenlieu
                            WHERE mn.mamon = m.mamon
                            AND n.tennguyenlieu LIKE %s
                        )
                    )
                """)

                params.extend([
                    search_value,
                    search_value
                ])

            # -------------------------------
            # Nhiều nguyên liệu
            # Phải có TẤT CẢ
            # -------------------------------

            else:

                for word in keywords:

                    conditions.append("""
                        EXISTS (
                            SELECT 1
                            FROM monan_nguyenlieu mn2
                            JOIN nguyenlieu n2
                                ON mn2.manguyenlieu = n2.manguyenlieu
                            WHERE mn2.mamon = m.mamon
                            AND n2.tennguyenlieu LIKE %s
                        )
                    """)

                    params.append(f"%{word}%")

        # ==========================================
        # NGÂN SÁCH
        # ==========================================

        if budget:

            try:

                budget_value = float(budget)

                conditions.append("""
                    m.chiphi <= %s
                """)

                params.append(budget_value)

            except ValueError:

                budget = ""

        # ==========================================
        # DANH MỤC
        # ==========================================

        if category:

            try:

                category_value = int(category)

                conditions.append("""
                    m.madanhmuc = %s
                """)

                params.append(category_value)

            except ValueError:

                category = ""

        # ==========================================
        # THỜI GIAN NẤU
        # ==========================================

        if max_time:

            try:

                max_time_value = int(max_time)

                conditions.append("""
                    m.thoigian <= %s
                """)

                params.append(max_time_value)

            except ValueError:

                max_time = ""

        # ==========================================
        # CALO
        # ==========================================

        if max_kcal:

            try:

                max_kcal_value = float(max_kcal)

                conditions.append("""
                    m.kcal <= %s
                """)

                params.append(max_kcal_value)

            except ValueError:

                max_kcal = ""

        # ==========================================
        # CHỈ THỰC HIỆN TÌM KIẾM KHI CÓ ĐIỀU KIỆN
        # ==========================================

        if conditions:

            sql = f"""
                SELECT DISTINCT
                    m.mamon,
                    m.tenmon,
                    m.mota,
                    m.chiphi,
                    m.kcal,
                    m.thoigian,
                    d.tendanhmuc
                FROM monan m
                LEFT JOIN danhmuc d
                    ON m.madanhmuc = d.madanhmuc
                WHERE
                    {" AND ".join(conditions)}
                ORDER BY m.tenmon
            """

            cursor.execute(sql, tuple(params))
            foods = cursor.fetchall()

            if "manguoidung" in session and foods:
                foods = sort_foods_by_behavior(
                    manguoidung=session["manguoidung"],
                    foods=foods
                )
        
        

    cursor.close()
    conn.close()

    return render_template(
        "user/search.html",
        keyword=keyword,
        budget=budget,
        category=category,
        max_time=max_time,
        max_kcal=max_kcal,
        categories=categories,
        foods=foods
    )





# ==========================================
# food detail
# ==========================================
@app.route("/food/<int:mamon>")
def food_detail(mamon):

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    # Lấy thông tin món ăn
    sql_food = """
        SELECT
            m.mamon,
            m.tenmon,
            m.mota,
            m.cachlam,
            m.thoigian,
            m.chiphi,
            m.kcal,
            d.tendanhmuc
        FROM monan m
        LEFT JOIN danhmuc d
            ON m.madanhmuc = d.madanhmuc
        WHERE m.mamon = %s
    """

    cursor.execute(sql_food, (mamon,))
    food = cursor.fetchone()

    if food is None:
        cursor.close()
        conn.close()
        return "Không tìm thấy món ăn", 404


    if "manguoidung" in session:
        save_behavior(
            manguoidung=session["manguoidung"],
            mamon=mamon,
            loaihanhvi="xem_chi_tiet"
        )

    # Lấy danh sách nguyên liệu
    sql_ingredients = """
        SELECT
            n.tennguyenlieu,
            mn.soluong,
            mn.donvi
        FROM monan_nguyenlieu mn
        JOIN nguyenlieu n
            ON mn.manguyenlieu = n.manguyenlieu
        WHERE mn.mamon = %s
        ORDER BY n.tennguyenlieu
    """

    

    cursor.execute(sql_ingredients, (mamon,))
    ingredients = cursor.fetchall()

    cursor.execute("""
    SELECT manguoidung
    FROM yeuthich
    WHERE manguoidung = %s
    AND mamon = %s
""", (
    session.get("manguoidung"),
    mamon
))

    favorite_exists = cursor.fetchone() is not None

    cursor.execute("""
        SELECT
            AVG(diem) AS diem_trung_binh,
            COUNT(*) AS so_luot_danh_gia
        FROM danhgia
        WHERE mamon = %s
    """, (mamon,))

    rating_summary = cursor.fetchone()

    cursor.execute("""
        SELECT
            dg.diem,
            dg.binhluan,
            dg.ngaytao,
            nd.hoten
        FROM danhgia dg
        JOIN nguoidung nd
            ON dg.manguoidung = nd.manguoidung
        WHERE dg.mamon = %s
        ORDER BY dg.ngaytao DESC
    """, (mamon,))

    reviews = cursor.fetchall()
    user_review = None

    if "manguoidung" in session:

        cursor.execute("""
            SELECT
                diem,
                binhluan
            FROM danhgia
            WHERE manguoidung = %s
              AND mamon = %s
            LIMIT 1
        """, (
            session["manguoidung"],
            mamon
        ))

        user_review = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template(
    "user/food_detail.html",
    food=food,
    ingredients=ingredients,
    favorite_exists=favorite_exists,
    rating_summary=rating_summary,
    reviews=reviews,
    user_review=user_review
)



# ==========================================
# Hôm nay ăn gì
# ==========================================
@app.route("/today", methods=["GET", "POST"])
def today():

    food = None
    budget = ""

    if request.method == "POST":

        budget = request.form.get("budget", "").strip()

        if "manguoidung" in session:
            behavior_budget = None

            try:
                behavior_budget = float(budget)
            except ValueError:
                behavior_budget = None

            save_behavior(
                manguoidung=session["manguoidung"],
                loaihanhvi="hom_nay_an_gi",
                ngansach=behavior_budget
            )

        try:
            budget_value = float(budget)

            conn = get_db_connection()

            if conn is None:
                return "Không thể kết nối Database"

            cursor = conn.cursor(dictionary=True)

            sql = """
                SELECT mamon, tenmon, mota, chiphi, kcal
                FROM monan
                WHERE chiphi <= %s
                ORDER BY RAND()
                LIMIT 1
            """

            cursor.execute(sql, (budget_value,))
            food = cursor.fetchone()

            cursor.close()
            conn.close()

        except ValueError:
            flash("Ngân sách phải là số.", "error")

    return render_template(
        "user/today.html",
        food=food,
        budget=budget
    )










# ==========================================
# nút Yêu thích
# ==========================================
@app.route("/favorite/<int:mamon>", methods=["POST"])
def favorite(mamon):

    # Kiểm tra đăng nhập
    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để yêu thích món ăn.", "error")
        return redirect(url_for("login"))

    manguoidung = session["manguoidung"]

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor()

    try:

        # Kiểm tra món đã được yêu thích chưa
        cursor.execute("""
            SELECT manguoidung
            FROM yeuthich
            WHERE manguoidung = %s
            AND mamon = %s
        """, (manguoidung, mamon))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                DELETE FROM yeuthich
                WHERE manguoidung = %s
                AND mamon = %s
                """, (manguoidung, mamon))

            save_behavior(
                manguoidung=manguoidung,
                mamon=mamon,
                loaihanhvi="bo_yeu_thich"
            )

            flash("Đã bỏ món ăn khỏi yêu thích.", "success")

        else:

            # Nếu chưa yêu thích → thêm vào
            cursor.execute("""
                INSERT INTO yeuthich (manguoidung, mamon)
                VALUES (%s, %s)
                """, (manguoidung, mamon))

            save_behavior(
                manguoidung=manguoidung,
                mamon=mamon,
                loaihanhvi="them_yeu_thich"
            )

            flash("Đã thêm món ăn vào yêu thích.", "success")

        conn.commit()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi yêu thích:")
        print(e)

        flash("Không thể thực hiện thao tác.", "error")

    finally:

        cursor.close()
        conn.close()

    return redirect(
        url_for(
            "food_detail",
            mamon=mamon
        )
    )


# TRANG XEM CÁC MON YÊU THÍCH
#
@app.route("/favorites")
def favorites():

    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để xem món ăn yêu thích.", "error")
        return redirect(url_for("login"))

    manguoidung = session["manguoidung"]

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                m.mamon,
                m.tenmon,
                m.mota,
                m.chiphi,
                m.kcal,
                m.thoigian,
                d.tendanhmuc,
                y.ngaytao
            FROM yeuthich y
            JOIN monan m
                ON y.mamon = m.mamon
            LEFT JOIN danhmuc d
                ON m.madanhmuc = d.madanhmuc
            WHERE y.manguoidung = %s
            ORDER BY y.ngaytao DESC
        """, (manguoidung,))

        foods = cursor.fetchall()

    except Exception as e:
        print("❌ Lỗi lấy danh sách yêu thích:")
        print(e)
        foods = []

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "user/favorites.html",
        foods=foods
    )


# ==========================================
# Nút đánh giá
# ==========================================
@app.route("/review/<int:mamon>", methods=["POST"])
def review(mamon):

    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để đánh giá món ăn.", "error")
        return redirect(url_for("login"))

    manguoidung = session["manguoidung"]

    try:
        diem = int(request.form.get("diem", 0))
    except ValueError:
        diem = 0

    binhluan = request.form.get("binhluan", "").strip()

    if diem < 1 or diem > 5:
        flash("Vui lòng chọn từ 1 đến 5 sao.", "error")
        return redirect(url_for("food_detail", mamon=mamon))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor()

    try:

        # Kiểm tra người dùng đã đánh giá món này chưa
        cursor.execute("""
            SELECT madanhgia
            FROM danhgia
            WHERE manguoidung = %s
              AND mamon = %s
            LIMIT 1
        """, (
            manguoidung,
            mamon
        ))

        existing_review = cursor.fetchone()

        if existing_review:

            # Cập nhật đánh giá cũ
            cursor.execute("""
                UPDATE danhgia
                SET diem = %s,
                    binhluan = %s,
                    ngaytao = CURRENT_TIMESTAMP
                WHERE madanhgia = %s
            """, (
                diem,
                binhluan,
                existing_review[0]
            ))

            message = "Đã cập nhật đánh giá của bạn."

        else:

            # Tạo đánh giá mới
            cursor.execute("""
                INSERT INTO danhgia
                (
                    manguoidung,
                    mamon,
                    diem,
                    binhluan
                )
                VALUES (%s, %s, %s, %s)
            """, (
                manguoidung,
                mamon,
                diem,
                binhluan
            ))

            message = "Đánh giá món ăn thành công."

        conn.commit()

        # Lưu hành vi đánh giá
        save_behavior(
            manguoidung=manguoidung,
            mamon=mamon,
            loaihanhvi="danh_gia"
        )

        flash(message, "success")

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi đánh giá món ăn:")
        print(e)

        flash("Không thể lưu đánh giá.", "error")

    finally:

        cursor.close()
        conn.close()

    return redirect(url_for("food_detail", mamon=mamon))












# ==========================================
# ADMIN
# ==========================================

@app.route("/admin")
def admin():
    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    if session.get("quyen") != "admin":
        flash("Bạn không có quyền truy cập trang quản trị.", "error")
        return redirect(url_for("home"))

    return render_template("admin/dashboard.html")




# ==========================================
# quản lý ng dùng
# ==========================================
@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():

    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    if session.get("quyen") != "admin":
        flash("Bạn không có quyền truy cập trang quản trị.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        if request.method == "POST":

            manguoidung = request.form.get("manguoidung")
            quyen = request.form.get("quyen")

            if quyen not in ["user", "admin"]:
                flash("Quyền không hợp lệ.", "error")
                return redirect(url_for("admin_users"))

            # Không cho Admin tự hạ quyền của chính mình
            if int(manguoidung) == session["manguoidung"]:
                flash("Không thể thay đổi quyền của chính tài khoản đang đăng nhập.", "error")
                return redirect(url_for("admin_users"))

            cursor.execute("""
                UPDATE nguoidung
                SET quyen = %s
                WHERE manguoidung = %s
            """, (
                quyen,
                manguoidung
            ))

            conn.commit()

            flash("Đã cập nhật quyền người dùng.", "success")

            return redirect(url_for("admin_users"))

        cursor.execute("""
            SELECT
                manguoidung,
                hoten,
                email,
                quyen,
                ngaytao
            FROM nguoidung
            ORDER BY ngaytao DESC
        """)

        users = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý người dùng:")
        print(e)

        flash("Không thể thực hiện thao tác.", "error")

        users = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/users.html",
        users=users
    )



# ==========================================
# ql món ăn
# ==========================================
@app.route("/admin/foods", methods=["GET", "POST"])
def admin_foods():

    # Kiểm tra đăng nhập
    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    # Kiểm tra quyền admin
    if session.get("quyen") != "admin":
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        # =====================================================
        # XỬ LÝ POST
        # =====================================================
        if request.method == "POST":

            action = request.form.get("action")

            # =================================================
            # THÊM MÓN ĂN
            # =================================================
            if action == "add":

                tenmon = request.form.get("tenmon", "").strip()
                mota = request.form.get("mota", "").strip()
                madanhmuc = request.form.get("madanhmuc")
                cachlam = request.form.get("cachlam", "").strip()
                thoigian = request.form.get("thoigian", 0)

                if not tenmon:
                    flash("Vui lòng nhập tên món ăn.", "error")
                    return redirect(url_for("admin_foods"))

                try:
                    thoigian = int(thoigian or 0)
                except ValueError:
                    thoigian = 0

                # Thêm món trước
                cursor.execute("""
                    INSERT INTO monan
                    (
                        tenmon,
                        mota,
                        madanhmuc,
                        cachlam,
                        thoigian,
                        chiphi,
                        kcal
                    )
                    VALUES (%s, %s, %s, %s, %s, 0, 0)
                """, (
                    tenmon,
                    mota,
                    madanhmuc if madanhmuc else None,
                    cachlam,
                    thoigian
                ))

                mamon = cursor.lastrowid

                # Lấy nguyên liệu
                ingredient_ids = request.form.getlist("manguyenlieu[]")
                quantities = request.form.getlist("soluong[]")

                total_cost = 0
                total_kcal = 0

                for i in range(len(ingredient_ids)):

                    manguyenlieu = ingredient_ids[i]

                    if not manguyenlieu:
                        continue

                    try:
                        soluong = float(quantities[i])
                    except (ValueError, IndexError):
                        continue

                    if soluong <= 0:
                        continue

                    # Lấy thông tin nguyên liệu
                    cursor.execute("""
                        SELECT
                            donvi,
                            giathamkhao,
                            kcal
                        FROM nguyenlieu
                        WHERE manguyenlieu = %s
                    """, (manguyenlieu,))

                    ingredient = cursor.fetchone()

                    if ingredient is None:
                        continue

                    donvi = ingredient["donvi"] or ""
                    gia = float(ingredient["giathamkhao"] or 0)
                    kcal_ref = float(ingredient["kcal"] or 0)

                    # Tính chi phí
                    ingredient_cost = soluong * gia
                    total_cost += ingredient_cost

                    # Tính kcal
                    if donvi.lower() in ("g", "ml"):
                        ingredient_kcal = (soluong / 100) * kcal_ref
                    else:
                        ingredient_kcal = soluong * kcal_ref

                    total_kcal += ingredient_kcal

                    # Lưu nguyên liệu cho món
                    cursor.execute("""
                        INSERT INTO monan_nguyenlieu
                        (
                            mamon,
                            manguyenlieu,
                            soluong,
                            donvi
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        mamon,
                        manguyenlieu,
                        soluong,
                        donvi
                    ))

                # Cập nhật chi phí + kcal
                cursor.execute("""
                    UPDATE monan
                    SET
                        chiphi = %s,
                        kcal = %s
                    WHERE mamon = %s
                """, (
                    total_cost,
                    total_kcal,
                    mamon
                ))

                conn.commit()

                flash(
                    "Đã thêm món ăn và tự tính Chi phí, Kcal.",
                    "success"
                )

                return redirect(url_for("admin_foods"))

            # =================================================
            # XÓA MÓN ĂN
            # =================================================
            elif action == "delete":

                mamon = request.form.get("mamon")

                if not mamon:
                    flash("Không xác định được món ăn cần xóa.", "error")
                    return redirect(url_for("admin_foods"))

                # Xóa món
                # Các bảng liên quan có ON DELETE CASCADE
                cursor.execute("""
                    DELETE FROM monan
                    WHERE mamon = %s
                """, (mamon,))

                conn.commit()

                flash("Đã xóa món ăn thành công.", "success")

                return redirect(url_for("admin_foods"))

            # =================================================
            # SỬA MÓN ĂN
            # =================================================
            elif action == "edit":

                mamon = request.form.get("mamon")
                tenmon = request.form.get("tenmon", "").strip()
                mota = request.form.get("mota", "").strip()
                madanhmuc = request.form.get("madanhmuc")
                cachlam = request.form.get("cachlam", "").strip()
                thoigian = request.form.get("thoigian", 0)

                if not mamon or not tenmon:
                    flash(
                        "Vui lòng nhập đầy đủ thông tin món ăn.",
                        "error"
                    )
                    return redirect(url_for("admin_foods"))

                try:
                    thoigian = int(thoigian or 0)
                except ValueError:
                    thoigian = 0

                # Cập nhật thông tin món
                cursor.execute("""
                    UPDATE monan
                    SET
                        tenmon = %s,
                        mota = %s,
                        madanhmuc = %s,
                        cachlam = %s,
                        thoigian = %s
                    WHERE mamon = %s
                """, (
                    tenmon,
                    mota,
                    madanhmuc if madanhmuc else None,
                    cachlam,
                    thoigian,
                    mamon
                ))

                # Xóa nguyên liệu cũ
                cursor.execute("""
                    DELETE FROM monan_nguyenlieu
                    WHERE mamon = %s
                """, (mamon,))

                ingredient_ids = request.form.getlist(
                    "manguyenlieu[]"
                )

                quantities = request.form.getlist(
                    "soluong[]"
                )

                total_cost = 0
                total_kcal = 0

                for i in range(len(ingredient_ids)):

                    manguyenlieu = ingredient_ids[i]

                    if not manguyenlieu:
                        continue

                    try:
                        soluong = float(quantities[i])
                    except (ValueError, IndexError):
                        continue

                    if soluong <= 0:
                        continue

                    cursor.execute("""
                        SELECT
                            giathamkhao,
                            kcal,
                            donvi
                        FROM nguyenlieu
                        WHERE manguyenlieu = %s
                    """, (manguyenlieu,))

                    ingredient = cursor.fetchone()

                    if ingredient is None:
                        continue

                    gia = float(
                        ingredient["giathamkhao"] or 0
                    )

                    kcal_ref = float(
                        ingredient["kcal"] or 0
                    )

                    donvi = ingredient["donvi"] or ""

                    # Tính chi phí
                    ingredient_cost = soluong * gia
                    total_cost += ingredient_cost

                    # Tính kcal
                    if donvi.lower() in ("g", "ml"):
                        ingredient_kcal = (
                            soluong / 100
                        ) * kcal_ref
                    else:
                        ingredient_kcal = (
                            soluong * kcal_ref
                        )

                    total_kcal += ingredient_kcal

                    # Thêm lại nguyên liệu
                    cursor.execute("""
                        INSERT INTO monan_nguyenlieu
                        (
                            mamon,
                            manguyenlieu,
                            soluong,
                            donvi
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        mamon,
                        manguyenlieu,
                        soluong,
                        donvi
                    ))

                # Cập nhật chi phí + kcal
                cursor.execute("""
                    UPDATE monan
                    SET
                        chiphi = %s,
                        kcal = %s
                    WHERE mamon = %s
                """, (
                    total_cost,
                    total_kcal,
                    mamon
                ))

                conn.commit()

                flash(
                    "Đã cập nhật món ăn và tự tính lại Chi phí, Kcal.",
                    "success"
                )

                return redirect(url_for("admin_foods"))

        # =====================================================
        # LẤY DANH SÁCH MÓN ĂN
        # =====================================================

        cursor.execute("""
            SELECT
                m.mamon,
                m.tenmon,
                m.mota,
                m.madanhmuc,
                d.tendanhmuc,
                m.cachlam,
                m.thoigian,

                COALESCE(
                    SUM(
                        mn.soluong * n.giathamkhao
                    ),
                    0
                ) AS chiphi_tinh,

                COALESCE(
                    SUM(
                        CASE
                            WHEN LOWER(mn.donvi) IN ('g', 'ml')
                            THEN
                                (mn.soluong / 100) * n.kcal
                            ELSE
                                mn.soluong * n.kcal
                        END
                    ),
                    0
                ) AS kcal_tinh,

                GROUP_CONCAT(
                    CONCAT(
                        n.tennguyenlieu,
                        ' ',
                        mn.soluong,
                        ' ',
                        mn.donvi
                    )
                    ORDER BY n.tennguyenlieu
                    SEPARATOR ', '
                ) AS danh_sach_nguyenlieu

            FROM monan m

            LEFT JOIN danhmuc d
                ON m.madanhmuc = d.madanhmuc

            LEFT JOIN monan_nguyenlieu mn
                ON m.mamon = mn.mamon

            LEFT JOIN nguyenlieu n
                ON mn.manguyenlieu = n.manguyenlieu

            GROUP BY
                m.mamon,
                m.tenmon,
                m.mota,
                m.madanhmuc,
                d.tendanhmuc,
                m.cachlam,
                m.thoigian

            ORDER BY m.mamon DESC
        """)

        foods = cursor.fetchall()

        # Danh mục
        cursor.execute("""
            SELECT
                madanhmuc,
                tendanhmuc
            FROM danhmuc
            ORDER BY tendanhmuc
        """)

        categories = cursor.fetchall()

        # Nguyên liệu
        cursor.execute("""
            SELECT
                manguyenlieu,
                tennguyenlieu,
                donvi,
                giathamkhao,
                kcal
            FROM nguyenlieu
            ORDER BY tennguyenlieu
        """)

        ingredients = cursor.fetchall()

        # =====================================================
        # LẤY MÓN ĐANG SỬA
        # =====================================================

        edit_id = request.args.get("edit")

        edit_food = None
        edit_ingredients = []

        if edit_id:

            cursor.execute("""
                SELECT
                    mamon,
                    tenmon,
                    mota,
                    madanhmuc,
                    cachlam,
                    thoigian
                FROM monan
                WHERE mamon = %s
            """, (edit_id,))

            edit_food = cursor.fetchone()

            if edit_food:

                cursor.execute("""
                    SELECT
                        mn.manguyenlieu,
                        mn.soluong,
                        mn.donvi,
                        n.tennguyenlieu
                    FROM monan_nguyenlieu mn
                    JOIN nguyenlieu n
                        ON mn.manguyenlieu = n.manguyenlieu
                    WHERE mn.mamon = %s
                    ORDER BY n.tennguyenlieu
                """, (edit_id,))

                edit_ingredients = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý món ăn:")
        print(e)

        flash(
            "Không thể thực hiện thao tác.",
            "error"
        )

        foods = []
        categories = []
        ingredients = []
        edit_food = None
        edit_ingredients = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/foods.html",
        foods=foods,
        categories=categories,
        ingredients=ingredients,
        edit_food=edit_food,
        edit_ingredients=edit_ingredients
    )



# ==========================================
# Ql nguyên liệu
# ==========================================
@app.route("/admin/ingredients", methods=["GET", "POST"])
def admin_ingredients():

    # Kiểm tra đăng nhập
    if "manguoidung" not in session:
        flash(
            "Vui lòng đăng nhập để truy cập trang quản trị.",
            "error"
        )
        return redirect(url_for("login"))

    # Kiểm tra quyền admin
    if session.get("quyen") != "admin":
        flash(
            "Bạn không có quyền truy cập.",
            "error"
        )
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        # =====================================================
        # XỬ LÝ POST
        # =====================================================

        if request.method == "POST":

            action = request.form.get("action")

            # =================================================
            # THÊM NGUYÊN LIỆU
            # =================================================

            if action == "add":

                tennguyenlieu = request.form.get(
                    "tennguyenlieu",
                    ""
                ).strip()

                donvi = request.form.get(
                    "donvi",
                    ""
                ).strip()

                giathamkhao = request.form.get(
                    "giathamkhao",
                    "0"
                ).strip()

                kcal = request.form.get(
                    "kcal",
                    "0"
                ).strip()

                if not tennguyenlieu:
                    flash(
                        "Vui lòng nhập tên nguyên liệu.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                try:
                    giathamkhao = float(giathamkhao or 0)
                    kcal = float(kcal or 0)
                except ValueError:
                    flash(
                        "Giá tham khảo và kcal phải là số.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                # Kiểm tra trùng tên
                cursor.execute("""
                    SELECT manguyenlieu
                    FROM nguyenlieu
                    WHERE tennguyenlieu = %s
                    LIMIT 1
                """, (tennguyenlieu,))

                existing = cursor.fetchone()

                if existing:
                    flash(
                        "Nguyên liệu này đã tồn tại.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                cursor.execute("""
                    INSERT INTO nguyenlieu
                    (
                        tennguyenlieu,
                        donvi,
                        giathamkhao,
                        kcal
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    tennguyenlieu,
                    donvi,
                    giathamkhao,
                    kcal
                ))

                conn.commit()

                flash(
                    "Đã thêm nguyên liệu thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_ingredients")
                )

            # =================================================
            # SỬA NGUYÊN LIỆU
            # =================================================

            elif action == "edit":

                manguyenlieu = request.form.get(
                    "manguyenlieu"
                )

                tennguyenlieu = request.form.get(
                    "tennguyenlieu",
                    ""
                ).strip()

                donvi = request.form.get(
                    "donvi",
                    ""
                ).strip()

                giathamkhao = request.form.get(
                    "giathamkhao",
                    "0"
                ).strip()

                kcal = request.form.get(
                    "kcal",
                    "0"
                ).strip()

                if not manguyenlieu or not tennguyenlieu:
                    flash(
                        "Vui lòng nhập đầy đủ thông tin.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                try:
                    giathamkhao = float(giathamkhao or 0)
                    kcal = float(kcal or 0)
                except ValueError:
                    flash(
                        "Giá tham khảo và kcal phải là số.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                # Kiểm tra tên có bị trùng với nguyên liệu khác
                cursor.execute("""
                    SELECT manguyenlieu
                    FROM nguyenlieu
                    WHERE tennguyenlieu = %s
                      AND manguyenlieu != %s
                    LIMIT 1
                """, (
                    tennguyenlieu,
                    manguyenlieu
                ))

                existing = cursor.fetchone()

                if existing:
                    flash(
                        "Tên nguyên liệu đã được sử dụng.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                cursor.execute("""
                    UPDATE nguyenlieu
                    SET
                        tennguyenlieu = %s,
                        donvi = %s,
                        giathamkhao = %s,
                        kcal = %s
                    WHERE manguyenlieu = %s
                """, (
                    tennguyenlieu,
                    donvi,
                    giathamkhao,
                    kcal,
                    manguyenlieu
                ))

                conn.commit()

                flash(
                    "Đã cập nhật nguyên liệu thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_ingredients")
                )

            # =================================================
            # XÓA NGUYÊN LIỆU
            # =================================================

            elif action == "delete":

                manguyenlieu = request.form.get(
                    "manguyenlieu"
                )

                if not manguyenlieu:
                    flash(
                        "Không xác định được nguyên liệu cần xóa.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                cursor.execute("""
                    SELECT manguyenlieu
                    FROM monan_nguyenlieu
                    WHERE manguyenlieu = %s
                    LIMIT 1
                """, (manguyenlieu,))

                ingredient_used = cursor.fetchone()

                if ingredient_used:
                    flash(
                        "Không thể xóa nguyên liệu đang được sử dụng trong món ăn.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_ingredients")
                    )

                cursor.execute("""
                    DELETE FROM nguyenlieu
                    WHERE manguyenlieu = %s
                """, (manguyenlieu,))

                conn.commit()

                flash(
                    "Đã xóa nguyên liệu thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_ingredients")
                )

        # =====================================================
        # LẤY DANH SÁCH NGUYÊN LIỆU
        # =====================================================

        cursor.execute("""
            SELECT
                manguyenlieu,
                tennguyenlieu,
                donvi,
                giathamkhao,
                kcal
            FROM nguyenlieu
            ORDER BY manguyenlieu DESC
        """)

        ingredients = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý nguyên liệu:")
        print(e)

        flash(
            "Không thể thực hiện thao tác.",
            "error"
        )

        ingredients = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/ingredients.html",
        ingredients=ingredients
    )




# ==========================================
# ql danh mục
# ==========================================
@app.route("/admin/categories", methods=["GET", "POST"])
def admin_categories():

    # Kiểm tra đăng nhập
    if "manguoidung" not in session:
        flash(
            "Vui lòng đăng nhập để truy cập trang quản trị.",
            "error"
        )
        return redirect(url_for("login"))

    # Kiểm tra quyền admin
    if session.get("quyen") != "admin":
        flash(
            "Bạn không có quyền truy cập.",
            "error"
        )
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        # =====================================================
        # XỬ LÝ POST
        # =====================================================

        if request.method == "POST":

            action = request.form.get("action")

            # =================================================
            # THÊM DANH MỤC
            # =================================================

            if action == "add":

                tendanhmuc = request.form.get(
                    "tendanhmuc",
                    ""
                ).strip()

                if not tendanhmuc:
                    flash(
                        "Vui lòng nhập tên danh mục.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                # Kiểm tra trùng
                cursor.execute("""
                    SELECT madanhmuc
                    FROM danhmuc
                    WHERE tendanhmuc = %s
                    LIMIT 1
                """, (tendanhmuc,))

                existing = cursor.fetchone()

                if existing:
                    flash(
                        "Danh mục này đã tồn tại.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                cursor.execute("""
                    INSERT INTO danhmuc
                    (tendanhmuc)
                    VALUES (%s)
                """, (tendanhmuc,))

                conn.commit()

                flash(
                    "Đã thêm danh mục thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_categories")
                )

            # =================================================
            # SỬA DANH MỤC
            # =================================================

            elif action == "edit":

                madanhmuc = request.form.get(
                    "madanhmuc"
                )

                tendanhmuc = request.form.get(
                    "tendanhmuc",
                    ""
                ).strip()

                if not madanhmuc or not tendanhmuc:
                    flash(
                        "Vui lòng nhập đầy đủ thông tin.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                # Kiểm tra trùng với danh mục khác
                cursor.execute("""
                    SELECT madanhmuc
                    FROM danhmuc
                    WHERE tendanhmuc = %s
                      AND madanhmuc != %s
                    LIMIT 1
                """, (
                    tendanhmuc,
                    madanhmuc
                ))

                existing = cursor.fetchone()

                if existing:
                    flash(
                        "Tên danh mục đã được sử dụng.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                cursor.execute("""
                    UPDATE danhmuc
                    SET tendanhmuc = %s
                    WHERE madanhmuc = %s
                """, (
                    tendanhmuc,
                    madanhmuc
                ))

                conn.commit()

                flash(
                    "Đã cập nhật danh mục thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_categories")
                )

            # =================================================
            # XÓA DANH MỤC
            # =================================================

            elif action == "delete":

                madanhmuc = request.form.get(
                    "madanhmuc"
                )

                if not madanhmuc:
                    flash(
                        "Không xác định được danh mục cần xóa.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                # Kiểm tra danh mục đang được món ăn sử dụng
                cursor.execute("""
                    SELECT mamon
                    FROM monan
                    WHERE madanhmuc = %s
                    LIMIT 1
                """, (madanhmuc,))

                category_used = cursor.fetchone()

                if category_used:
                    flash(
                        "Không thể xóa danh mục đang được sử dụng trong món ăn.",
                        "error"
                    )
                    return redirect(
                        url_for("admin_categories")
                    )

                cursor.execute("""
                    DELETE FROM danhmuc
                    WHERE madanhmuc = %s
                """, (madanhmuc,))

                conn.commit()

                flash(
                    "Đã xóa danh mục thành công.",
                    "success"
                )

                return redirect(
                    url_for("admin_categories")
                )

        # =====================================================
        # LẤY DANH SÁCH DANH MỤC
        # =====================================================

        cursor.execute("""
            SELECT
                d.madanhmuc,
                d.tendanhmuc,
                COUNT(m.mamon) AS so_mon
            FROM danhmuc d
            LEFT JOIN monan m
                ON d.madanhmuc = m.madanhmuc
            GROUP BY
                d.madanhmuc,
                d.tendanhmuc
            ORDER BY d.madanhmuc DESC
        """)

        categories = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý danh mục:")
        print(e)

        flash(
            "Không thể thực hiện thao tác.",
            "error"
        )

        categories = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/categories.html",
        categories=categories
    )



# ==========================================
# ql  đánh giá
# ==========================================
@app.route("/admin/reviews", methods=["GET", "POST"])
def admin_reviews():

    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    if session.get("quyen") != "admin":
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        # =========================
        # XÓA ĐÁNH GIÁ
        # =========================
        if request.method == "POST":

            action = request.form.get("action")

            if action == "delete":

                madanhgia = request.form.get("madanhgia")

                if not madanhgia:
                    flash("Không xác định được đánh giá cần xóa.", "error")
                    return redirect(url_for("admin_reviews"))

                cursor.execute("""
                    DELETE FROM danhgia
                    WHERE madanhgia = %s
                """, (madanhgia,))

                conn.commit()

                flash("Đã xóa đánh giá thành công.", "success")

                return redirect(url_for("admin_reviews"))

        # =========================
        # LẤY DANH SÁCH ĐÁNH GIÁ
        # =========================
        cursor.execute("""
            SELECT
                dg.madanhgia,
                dg.diem,
                dg.binhluan,
                dg.ngaytao,
                nd.hoten,
                nd.email,
                m.mamon,
                m.tenmon
            FROM danhgia dg

            JOIN nguoidung nd
                ON dg.manguoidung = nd.manguoidung

            JOIN monan m
                ON dg.mamon = m.mamon

            ORDER BY dg.ngaytao DESC
        """)

        reviews = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý đánh giá:")
        print(e)

        flash("Không thể thực hiện thao tác.", "error")

        reviews = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/reviews.html",
        reviews=reviews
    )

# ==========================================
# ql liên kết
# ==========================================
@app.route("/admin/related-data", methods=["GET", "POST"])
def admin_related_data():

    if "manguoidung" not in session:
        flash("Vui lòng đăng nhập để truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    if session.get("quyen") != "admin":
        flash("Bạn không có quyền truy cập.", "error")
        return redirect(url_for("home"))

    conn = get_db_connection()

    if conn is None:
        return "Không thể kết nối Database"

    cursor = conn.cursor(dictionary=True)

    try:

        # =========================
        # THÊM LIÊN KẾT
        # =========================
        if request.method == "POST":

            action = request.form.get("action")

            if action == "add":

                mamon = request.form.get("mamon")
                manguyenlieu = request.form.get("manguyenlieu")
                soluong = request.form.get("soluong", "").strip()
                donvi = request.form.get("donvi", "").strip()

                if not mamon or not manguyenlieu or not soluong:
                    flash("Vui lòng nhập đầy đủ thông tin.", "error")
                    return redirect(url_for("admin_related_data"))

                try:
                    soluong = float(soluong)

                    if soluong <= 0:
                        raise ValueError

                except ValueError:
                    flash("Số lượng phải là số lớn hơn 0.", "error")
                    return redirect(url_for("admin_related_data"))

                # Kiểm tra liên kết đã tồn tại
                cursor.execute("""
                    SELECT mamon
                    FROM monan_nguyenlieu
                    WHERE mamon = %s
                      AND manguyenlieu = %s
                    LIMIT 1
                """, (mamon, manguyenlieu))

                existing = cursor.fetchone()

                if existing:
                    flash(
                        "Liên kết món ăn và nguyên liệu này đã tồn tại.",
                        "error"
                    )
                    return redirect(url_for("admin_related_data"))

                # Nếu không nhập đơn vị thì lấy đơn vị của nguyên liệu
                if not donvi:
                    cursor.execute("""
                        SELECT donvi
                        FROM nguyenlieu
                        WHERE manguyenlieu = %s
                    """, (manguyenlieu,))

                    ingredient = cursor.fetchone()

                    if ingredient:
                        donvi = ingredient["donvi"]

                cursor.execute("""
                    INSERT INTO monan_nguyenlieu
                    (
                        mamon,
                        manguyenlieu,
                        soluong,
                        donvi
                    )
                    VALUES (%s, %s, %s, %s)
                """, (
                    mamon,
                    manguyenlieu,
                    soluong,
                    donvi
                ))

                conn.commit()

                flash(
                    "Đã thêm liên kết món ăn - nguyên liệu.",
                    "success"
                )

                return redirect(url_for("admin_related_data"))

            # =========================
            # SỬA LIÊN KẾT
            # =========================
            elif action == "edit":

                mamon = request.form.get("mamon")
                manguyenlieu = request.form.get("manguyenlieu")
                soluong = request.form.get("soluong", "").strip()
                donvi = request.form.get("donvi", "").strip()

                if not mamon or not manguyenlieu or not soluong:
                    flash("Vui lòng nhập đầy đủ thông tin.", "error")
                    return redirect(url_for("admin_related_data"))

                try:
                    soluong = float(soluong)

                    if soluong <= 0:
                        raise ValueError

                except ValueError:
                    flash("Số lượng phải là số lớn hơn 0.", "error")
                    return redirect(url_for("admin_related_data"))

                if not donvi:
                    cursor.execute("""
                        SELECT donvi
                        FROM nguyenlieu
                        WHERE manguyenlieu = %s
                    """, (manguyenlieu,))

                    ingredient = cursor.fetchone()

                    if ingredient:
                        donvi = ingredient["donvi"]

                cursor.execute("""
                    UPDATE monan_nguyenlieu
                    SET soluong = %s,
                        donvi = %s
                    WHERE mamon = %s
                      AND manguyenlieu = %s
                """, (
                    soluong,
                    donvi,
                    mamon,
                    manguyenlieu
                ))

                conn.commit()

                flash(
                    "Đã cập nhật dữ liệu liên quan.",
                    "success"
                )

                return redirect(url_for("admin_related_data"))

            # =========================
            # XÓA LIÊN KẾT
            # =========================
            elif action == "delete":

                mamon = request.form.get("mamon")
                manguyenlieu = request.form.get("manguyenlieu")

                if not mamon or not manguyenlieu:
                    flash(
                        "Không xác định được dữ liệu cần xóa.",
                        "error"
                    )
                    return redirect(url_for("admin_related_data"))

                cursor.execute("""
                    DELETE FROM monan_nguyenlieu
                    WHERE mamon = %s
                      AND manguyenlieu = %s
                """, (
                    mamon,
                    manguyenlieu
                ))

                conn.commit()

                flash(
                    "Đã xóa liên kết món ăn - nguyên liệu.",
                    "success"
                )

                return redirect(url_for("admin_related_data"))

        # =========================
        # DANH SÁCH LIÊN KẾT
        # =========================

        cursor.execute("""
            SELECT
                mn.mamon,
                mn.manguyenlieu,
                m.tenmon,
                n.tennguyenlieu,
                mn.soluong,
                mn.donvi,
                n.giathamkhao,
                n.kcal,

                (
                    mn.soluong * n.giathamkhao
                ) AS chiphi,

                CASE
                    WHEN mn.donvi IN ('g', 'ml')
                    THEN (mn.soluong / 100) * n.kcal
                    ELSE mn.soluong * n.kcal
                END AS nangluong

            FROM monan_nguyenlieu mn

            JOIN monan m
                ON mn.mamon = m.mamon

            JOIN nguyenlieu n
                ON mn.manguyenlieu = n.manguyenlieu

            ORDER BY
                m.tenmon,
                n.tennguyenlieu
        """)

        related_data = cursor.fetchall()

        # Danh sách món ăn
        cursor.execute("""
            SELECT
                mamon,
                tenmon
            FROM monan
            ORDER BY tenmon
        """)

        foods = cursor.fetchall()

        # Danh sách nguyên liệu
        cursor.execute("""
            SELECT
                manguyenlieu,
                tennguyenlieu,
                donvi
            FROM nguyenlieu
            ORDER BY tennguyenlieu
        """)

        ingredients = cursor.fetchall()

    except Exception as e:

        conn.rollback()

        print("❌ Lỗi quản lý dữ liệu liên quan:")
        print(e)

        flash(
            "Không thể thực hiện thao tác.",
            "error"
        )

        related_data = []
        foods = []
        ingredients = []

    finally:

        cursor.close()
        conn.close()

    return render_template(
        "admin/related_data.html",
        related_data=related_data,
        foods=foods,
        ingredients=ingredients
    )


















if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
