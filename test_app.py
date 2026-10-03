import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as app_module

app_module.app.config["TESTING"] = True


# ---------------------------------------------------------------------------
# Đối tượng giả cho kết nối MySQL
# ---------------------------------------------------------------------------
class FakeCursor:
    def __init__(self, fetchone=None, fetchall=None, lastrowid=1, raise_on=None):
        self.one = list(fetchone or [])
        self.all = list(fetchall or [])
        self.lastrowid = lastrowid
        self.raise_on = raise_on
        self.executed = []

    def execute(self, sql, params=None):
        sql = " ".join(sql.split())
        self.executed.append((sql, params))
        if self.raise_on and self.raise_on in sql:
            raise RuntimeError("Lỗi DB giả lập")

    def fetchone(self):
        return self.one.pop(0) if self.one else None

    def fetchall(self):
        return self.all.pop(0) if self.all else []

    def close(self):
        pass

    def sqls(self, keyword):
        return [(s, p) for s, p in self.executed if keyword in s]


class FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, *args, **kwargs):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


class Base(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.rendered = []
        self.behaviors = []

        def fake_render(name, **kwargs):
            self.rendered.append((name, kwargs))
            return "RENDER:" + name

        def fake_save_behavior(**kwargs):
            self.behaviors.append(kwargs)
            return True

        self.patches = [
            patch.object(app_module, "render_template", fake_render),
            patch.object(app_module, "save_behavior", fake_save_behavior),
            patch.object(app_module, "sort_foods_by_behavior",
                         lambda manguoidung, foods: list(reversed(foods))),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    # ---- tiện ích ----
    def use_db(self, **cursor_kwargs):
        cur = FakeCursor(**cursor_kwargs)
        conn = FakeConn(cur)
        p = patch.object(app_module, "get_db_connection", lambda: conn)
        p.start()
        self.addCleanup(p.stop)
        return conn, cur

    def login_as(self, quyen="user", uid=1):
        with self.client.session_transaction() as s:
            s["manguoidung"] = uid
            s["hoten"] = "Người Test"
            s["email"] = "test@example.com"
            s["quyen"] = quyen

    def flashes(self):
        with self.client.session_transaction() as s:
            return [m for _, m in s.get("_flashes", [])]

    def assertFlash(self, text):
        msgs = self.flashes()
        self.assertTrue(any(text in m for m in msgs), f"Không thấy thông báo '{text}', thực tế: {msgs}")

    def assertRedirect(self, resp, path):
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.headers["Location"].endswith(path),
                        f"Chuyển hướng tới {resp.headers['Location']} (mong đợi {path})")


# ===========================================================================
# 1. ĐĂNG KÝ
# ===========================================================================
class TestRegister(Base):
    VALID = {"hoten": "Nguyễn Văn A", "email": "a@gmail.com",
             "matkhau": "123456", "xacnhan_matkhau": "123456"}

    def post(self, **over):
        data = dict(self.VALID, **over)
        return self.client.post("/register", data=data)

    def test_auth_01_mo_trang_dang_ky(self):
        """Module: Đăng ký
        Tiêu đề: Mở trang đăng ký
        Đầu vào: GET /register
        Kỳ vọng: HTTP 200, hiển thị template user/register.html"""
        r = self.client.get("/register")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rendered[-1][0], "user/register.html")

    def test_auth_02_ho_ten_rong(self):
        """Module: Đăng ký
        Tiêu đề: Để trống họ tên
        Đầu vào: hoten = '' (các trường khác hợp lệ)
        Kỳ vọng: Chuyển về /register, báo 'Vui lòng nhập họ và tên.'"""
        with patch.object(app_module, "create_user") as cu:
            r = self.post(hoten="   ")
            self.assertRedirect(r, "/register")
            self.assertFlash("Vui lòng nhập họ và tên.")
            cu.assert_not_called()

    def test_auth_03_email_rong(self):
        """Module: Đăng ký
        Tiêu đề: Để trống email
        Đầu vào: email = ''
        Kỳ vọng: Báo 'Vui lòng nhập email.', không tạo tài khoản"""
        with patch.object(app_module, "create_user") as cu:
            r = self.post(email="")
            self.assertRedirect(r, "/register")
            self.assertFlash("Vui lòng nhập email.")
            cu.assert_not_called()

    def test_auth_04_mat_khau_ngan(self):
        """Module: Đăng ký
        Tiêu đề: Mật khẩu ngắn hơn 6 ký tự (biên 5 ký tự)
        Đầu vào: matkhau = '12345'
        Kỳ vọng: Báo 'Mật khẩu phải có ít nhất 6 ký tự.'"""
        with patch.object(app_module, "create_user") as cu:
            r = self.post(matkhau="12345", xacnhan_matkhau="12345")
            self.assertRedirect(r, "/register")
            self.assertFlash("ít nhất 6 ký tự")
            cu.assert_not_called()

    def test_auth_05_mat_khau_dung_6_ky_tu(self):
        """Module: Đăng ký
        Tiêu đề: Mật khẩu đúng 6 ký tự (biên hợp lệ)
        Đầu vào: matkhau = '123456'
        Kỳ vọng: Tạo tài khoản thành công"""
        with patch.object(app_module, "email_exists", return_value=False), \
             patch.object(app_module, "create_user", return_value=True) as cu:
            self.post()
            cu.assert_called_once()
            self.assertFlash("Đăng ký tài khoản thành công!")

    def test_auth_06_xac_nhan_khong_khop(self):
        """Module: Đăng ký
        Tiêu đề: Xác nhận mật khẩu không khớp
        Đầu vào: matkhau = '123456', xacnhan_matkhau = '654321'
        Kỳ vọng: Báo 'Mật khẩu xác nhận không khớp.'"""
        with patch.object(app_module, "create_user") as cu:
            r = self.post(xacnhan_matkhau="654321")
            self.assertRedirect(r, "/register")
            self.assertFlash("xác nhận không khớp")
            cu.assert_not_called()

    def test_auth_07_email_da_ton_tai(self):
        """Module: Đăng ký
        Tiêu đề: Đăng ký bằng email đã tồn tại
        Đầu vào: email đã có trong CSDL
        Kỳ vọng: Báo 'Email này đã được đăng ký.', không tạo tài khoản"""
        with patch.object(app_module, "email_exists", return_value=True), \
             patch.object(app_module, "create_user") as cu:
            r = self.post()
            self.assertRedirect(r, "/register")
            self.assertFlash("Email này đã được đăng ký.")
            cu.assert_not_called()

    def test_auth_08_dang_ky_thanh_cong_chuan_hoa_email(self):
        """Module: Đăng ký
        Tiêu đề: Đăng ký thành công, email được chuẩn hóa
        Đầu vào: email = '  A@Gmail.COM  '
        Kỳ vọng: create_user nhận email 'a@gmail.com' (bỏ khoảng trắng, chữ thường); báo thành công"""
        with patch.object(app_module, "email_exists", return_value=False), \
             patch.object(app_module, "create_user", return_value=True) as cu:
            self.post(email="  A@Gmail.COM  ")
            cu.assert_called_once_with("Nguyễn Văn A", "a@gmail.com", "123456")
            self.assertFlash("Đăng ký tài khoản thành công!")

    def test_auth_09_tao_tai_khoan_that_bai(self):
        """Module: Đăng ký
        Tiêu đề: Lỗi khi lưu tài khoản vào CSDL
        Đầu vào: create_user trả về False
        Kỳ vọng: Báo 'Không thể tạo tài khoản. Vui lòng thử lại.'"""
        with patch.object(app_module, "email_exists", return_value=False), \
             patch.object(app_module, "create_user", return_value=False):
            self.post()
            self.assertFlash("Không thể tạo tài khoản")

    @unittest.expectedFailure
    def test_auth_10_email_sai_dinh_dang(self):
        """Module: Đăng ký
        Tiêu đề: Email sai định dạng (LỖI PHÁT HIỆN)
        Đầu vào: email = 'abc' (không có @ và tên miền)
        Kỳ vọng: Từ chối, báo email không hợp lệ, không tạo tài khoản.
        Ghi chú lỗi: Server chỉ kiểm tra email không rỗng nên vẫn tạo tài khoản."""
        with patch.object(app_module, "email_exists", return_value=False), \
             patch.object(app_module, "create_user", return_value=True) as cu:
            self.post(email="abc")
            cu.assert_not_called()


# ===========================================================================
# 2. ĐĂNG NHẬP / ĐĂNG XUẤT
# ===========================================================================
class TestLogin(Base):
    USER = {"manguoidung": 7, "hoten": "Lan", "email": "lan@gmail.com",
            "quyen": "user", "matkhau": generate_password_hash("123456")}

    def test_login_01_mo_trang(self):
        """Module: Đăng nhập
        Tiêu đề: Mở trang đăng nhập
        Đầu vào: GET /login
        Kỳ vọng: HTTP 200, template user/login.html"""
        r = self.client.get("/login")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rendered[-1][0], "user/login.html")

    def test_login_02_email_rong(self):
        """Module: Đăng nhập
        Tiêu đề: Để trống email
        Đầu vào: email = '', matkhau = '123456'
        Kỳ vọng: Báo 'Vui lòng nhập email.'"""
        r = self.client.post("/login", data={"email": "", "matkhau": "123456"})
        self.assertRedirect(r, "/login")
        self.assertFlash("Vui lòng nhập email.")

    def test_login_03_mat_khau_rong(self):
        """Module: Đăng nhập
        Tiêu đề: Để trống mật khẩu
        Đầu vào: email hợp lệ, matkhau = ''
        Kỳ vọng: Báo 'Vui lòng nhập mật khẩu.'"""
        r = self.client.post("/login", data={"email": "lan@gmail.com", "matkhau": ""})
        self.assertRedirect(r, "/login")
        self.assertFlash("Vui lòng nhập mật khẩu.")

    def test_login_04_email_khong_ton_tai(self):
        """Module: Đăng nhập
        Tiêu đề: Email chưa đăng ký
        Đầu vào: email không có trong CSDL
        Kỳ vọng: Báo 'Email hoặc mật khẩu không đúng.' (không tiết lộ email có tồn tại hay không)"""
        with patch.object(app_module, "get_user_by_email", return_value=None):
            r = self.client.post("/login", data={"email": "x@gmail.com", "matkhau": "123456"})
        self.assertRedirect(r, "/login")
        self.assertFlash("Email hoặc mật khẩu không đúng.")

    def test_login_05_sai_mat_khau(self):
        """Module: Đăng nhập
        Tiêu đề: Sai mật khẩu
        Đầu vào: email đúng, matkhau = 'saimatkhau'
        Kỳ vọng: Cùng thông báo 'Email hoặc mật khẩu không đúng.', không tạo session"""
        with patch.object(app_module, "get_user_by_email", return_value=self.USER):
            r = self.client.post("/login", data={"email": "lan@gmail.com", "matkhau": "saimatkhau"})
        self.assertRedirect(r, "/login")
        self.assertFlash("Email hoặc mật khẩu không đúng.")
        with self.client.session_transaction() as s:
            self.assertNotIn("manguoidung", s)

    def test_login_06_thanh_cong(self):
        """Module: Đăng nhập
        Tiêu đề: Đăng nhập thành công
        Đầu vào: email '  LAN@Gmail.com ' + mật khẩu đúng
        Kỳ vọng: Session lưu manguoidung/hoten/email/quyen, chuyển về trang chủ"""
        with patch.object(app_module, "get_user_by_email", return_value=self.USER) as g:
            r = self.client.post("/login", data={"email": "  LAN@Gmail.com ", "matkhau": "123456"})
            g.assert_called_once_with("lan@gmail.com")
        self.assertRedirect(r, "/")
        with self.client.session_transaction() as s:
            self.assertEqual(s["manguoidung"], 7)
            self.assertEqual(s["quyen"], "user")
            self.assertEqual(s["hoten"], "Lan")
        self.assertFlash("Đăng nhập thành công!")

    def test_login_07_dang_xuat(self):
        """Module: Đăng nhập
        Tiêu đề: Đăng xuất
        Đầu vào: GET /logout khi đã đăng nhập
        Kỳ vọng: Xóa session, chuyển về trang chủ"""
        self.login_as()
        r = self.client.get("/logout")
        self.assertRedirect(r, "/")
        with self.client.session_transaction() as s:
            self.assertNotIn("manguoidung", s)
            self.assertNotIn("quyen", s)


# ===========================================================================
# 3. TÌM KIẾM
# ===========================================================================
class TestSearch(Base):
    CATS = [{"madanhmuc": 1, "tendanhmuc": "Món chính"}]
    FOODS = [{"mamon": 1, "tenmon": "Gà rang"}, {"mamon": 2, "tenmon": "Gà luộc"}]

    def search(self, **form):
        return self.client.post("/search", data=form)

    def test_search_01_mo_trang(self):
        """Module: Tìm kiếm
        Tiêu đề: Mở trang tìm kiếm (GET)
        Đầu vào: GET /search
        Kỳ vọng: HTTP 200, có danh sách danh mục, chưa có kết quả món ăn"""
        self.use_db(fetchall=[self.CATS])
        r = self.client.get("/search")
        self.assertEqual(r.status_code, 200)
        kw = self.rendered[-1][1]
        self.assertEqual(kw["categories"], self.CATS)
        self.assertEqual(kw["foods"], [])

    def test_search_02_mot_tu_khoa(self):
        """Module: Tìm kiếm
        Tiêu đề: Tìm theo một từ khóa
        Đầu vào: keyword = 'gà'
        Kỳ vọng: Truy vấn dùng LIKE '%gà%' cho cả tên món và tên nguyên liệu; trả danh sách món"""
        _, cur = self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(keyword="gà")
        sql, params = cur.executed[-1]
        self.assertIn("m.tenmon LIKE", sql)
        self.assertIn("n.tennguyenlieu LIKE", sql)
        self.assertEqual(params, ("%gà%", "%gà%"))
        self.assertEqual(len(self.rendered[-1][1]["foods"]), 2)

    def test_search_03_nhieu_nguyen_lieu(self):
        """Module: Tìm kiếm
        Tiêu đề: Tìm nhiều nguyên liệu (phải có TẤT CẢ)
        Đầu vào: keyword = 'gà, hành, tỏi'
        Kỳ vọng: Sinh 3 điều kiện EXISTS nối bằng AND, tham số lần lượt %gà%, %hành%, %tỏi%"""
        _, cur = self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(keyword="gà, hành, tỏi")
        sql, params = cur.executed[-1]
        self.assertEqual(sql.count("EXISTS"), 3)
        self.assertEqual(params, ("%gà%", "%hành%", "%tỏi%"))

    def test_search_04_loc_ngan_sach(self):
        """Module: Tìm kiếm
        Tiêu đề: Lọc theo ngân sách
        Đầu vào: budget = '50000'
        Kỳ vọng: Điều kiện m.chiphi <= 50000.0"""
        _, cur = self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(budget="50000")
        sql, params = cur.executed[-1]
        self.assertIn("m.chiphi <=", sql)
        self.assertEqual(params, (50000.0,))

    def test_search_05_ket_hop_bo_loc(self):
        """Module: Tìm kiếm
        Tiêu đề: Kết hợp từ khóa + ngân sách + danh mục + thời gian + kcal
        Đầu vào: keyword='gà', budget=80000, category=1, max_time=30, max_kcal=600
        Kỳ vọng: Tất cả điều kiện được nối bằng AND, đúng thứ tự tham số"""
        _, cur = self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(keyword="gà", budget="80000", category="1", max_time="30", max_kcal="600")
        sql, params = cur.executed[-1]
        self.assertEqual(params, ("%gà%", "%gà%", 80000.0, 1, 30, 600.0))
        for cond in ("m.chiphi <=", "m.madanhmuc =", "m.thoigian <=", "m.kcal <="):
            self.assertIn(cond, sql)

    def test_search_06_ngan_sach_khong_phai_so(self):
        """Module: Tìm kiếm
        Tiêu đề: Ngân sách không phải số
        Đầu vào: budget = 'abc'
        Kỳ vọng: Bỏ qua điều kiện ngân sách, không gây lỗi 500"""
        self.use_db(fetchall=[self.CATS])
        r = self.search(budget="abc")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rendered[-1][1]["budget"], "")

    def test_search_07_form_rong(self):
        """Module: Tìm kiếm
        Tiêu đề: Gửi form rỗng
        Đầu vào: POST /search, mọi trường để trống
        Kỳ vọng: Không chạy truy vấn món ăn, danh sách kết quả rỗng, không lỗi"""
        _, cur = self.use_db(fetchall=[self.CATS])
        r = self.search(keyword="", budget="")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(cur.executed), 1)  # chỉ truy vấn danh mục
        self.assertEqual(self.rendered[-1][1]["foods"], [])

    def test_search_08_khach_khong_ghi_hanh_vi(self):
        """Module: Tìm kiếm
        Tiêu đề: Khách (chưa đăng nhập) tìm kiếm
        Đầu vào: keyword = 'gà', không có session
        Kỳ vọng: Không ghi hành vi, không gọi sắp xếp cá nhân hóa"""
        self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(keyword="gà")
        self.assertEqual(self.behaviors, [])
        kw = self.rendered[-1][1]
        self.assertEqual([f["mamon"] for f in kw["foods"]], [1, 2])  # giữ nguyên thứ tự

    def test_search_09_nguoi_dung_ghi_hanh_vi_va_sap_xep(self):
        """Module: Tìm kiếm
        Tiêu đề: Người dùng đã đăng nhập tìm kiếm
        Đầu vào: keyword='gà', budget='50000', đã đăng nhập
        Kỳ vọng: Ghi hành vi 'tim_kiem' (kèm từ khóa, ngân sách) và kết quả đi qua sort_foods_by_behavior"""
        self.login_as(uid=5)
        self.use_db(fetchall=[self.CATS, self.FOODS])
        self.search(keyword="gà", budget="50000")
        self.assertEqual(self.behaviors[0], {"manguoidung": 5, "loaihanhvi": "tim_kiem",
                                             "tukhoa": "gà", "ngansach": 50000.0})
        kw = self.rendered[-1][1]
        self.assertEqual([f["mamon"] for f in kw["foods"]], [2, 1])  # mock đảo thứ tự

    def test_search_10_mat_ket_noi_db(self):
        """Module: Tìm kiếm
        Tiêu đề: Mất kết nối cơ sở dữ liệu
        Đầu vào: get_db_connection() trả về None
        Kỳ vọng: Trả thông báo 'Không thể kết nối Database', không crash"""
        with patch.object(app_module, "get_db_connection", lambda: None):
            r = self.client.get("/search")
        self.assertIn("Không thể kết nối Database", r.get_data(as_text=True))


# ===========================================================================
# 4. CHI TIẾT MÓN ĂN
# ===========================================================================
class TestFoodDetail(Base):
    FOOD = {"mamon": 3, "tenmon": "Canh chua", "chiphi": 40000, "kcal": 250}

    def prime(self, logged=False):
        # fetchone: món, yêu thích, tổng hợp đánh giá, [đánh giá của user]
        ones = [self.FOOD, None, {"diem_trung_binh": 4.5, "so_luot_danh_gia": 2}]
        if logged:
            ones.append({"diem": 5, "binhluan": "Ngon"})
        return self.use_db(fetchone=ones, fetchall=[[{"tennguyenlieu": "Cà chua"}], []])

    def test_detail_01_mon_khong_ton_tai(self):
        """Module: Chi tiết món
        Tiêu đề: Truy cập món không tồn tại
        Đầu vào: GET /food/9999
        Kỳ vọng: HTTP 404 'Không tìm thấy món ăn'"""
        self.use_db(fetchone=[None])
        r = self.client.get("/food/9999")
        self.assertEqual(r.status_code, 404)

    def test_detail_02_khach_xem_chi_tiet(self):
        """Module: Chi tiết món
        Tiêu đề: Khách xem chi tiết món
        Đầu vào: GET /food/3, chưa đăng nhập
        Kỳ vọng: HTTP 200, có nguyên liệu và tổng hợp đánh giá; KHÔNG ghi hành vi"""
        self.prime()
        r = self.client.get("/food/3")
        self.assertEqual(r.status_code, 200)
        kw = self.rendered[-1][1]
        self.assertEqual(kw["food"]["tenmon"], "Canh chua")
        self.assertEqual(kw["ingredients"][0]["tennguyenlieu"], "Cà chua")
        self.assertEqual(kw["rating_summary"]["so_luot_danh_gia"], 2)
        self.assertFalse(kw["favorite_exists"] is True)
        self.assertEqual(self.behaviors, [])

    def test_detail_03_nguoi_dung_ghi_hanh_vi_xem(self):
        """Module: Chi tiết món
        Tiêu đề: Người dùng đăng nhập xem chi tiết món
        Đầu vào: GET /food/3, đã đăng nhập
        Kỳ vọng: Ghi hành vi 'xem_chi_tiet' với mamon=3; trả về đánh giá cũ của người dùng"""
        self.login_as(uid=4)
        self.prime(logged=True)
        self.client.get("/food/3")
        self.assertEqual(self.behaviors, [{"manguoidung": 4, "mamon": 3, "loaihanhvi": "xem_chi_tiet"}])
        self.assertEqual(self.rendered[-1][1]["user_review"]["diem"], 5)

    def test_detail_04_duong_dan_khong_hop_le(self):
        """Module: Chi tiết món
        Tiêu đề: Mã món không phải số nguyên
        Đầu vào: GET /food/abc
        Kỳ vọng: HTTP 404 (Flask từ chối do ràng buộc <int:mamon>)"""
        r = self.client.get("/food/abc")
        self.assertEqual(r.status_code, 404)


# ===========================================================================
# 5. HÔM NAY ĂN GÌ
# ===========================================================================
class TestToday(Base):
    def test_today_01_mo_trang(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Mở trang
        Đầu vào: GET /today
        Kỳ vọng: HTTP 200, chưa có món được đề xuất"""
        r = self.client.get("/today")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(self.rendered[-1][1]["food"])

    def test_today_02_ngan_sach_hop_le(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Chọn ngân sách hợp lệ
        Đầu vào: budget = '100000'
        Kỳ vọng: Truy vấn chiphi <= 100000.0, ORDER BY RAND() LIMIT 1, trả đúng 1 món"""
        food = {"mamon": 2, "tenmon": "Cá kho", "chiphi": 90000}
        _, cur = self.use_db(fetchone=[food])
        self.client.post("/today", data={"budget": "100000"})
        sql, params = cur.executed[-1]
        self.assertIn("chiphi <=", sql)
        self.assertIn("RAND()", sql)
        self.assertIn("LIMIT 1", sql)
        self.assertEqual(params, (100000.0,))
        self.assertEqual(self.rendered[-1][1]["food"]["tenmon"], "Cá kho")

    def test_today_03_khong_co_mon_phu_hop(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Không có món nào trong ngân sách
        Đầu vào: budget = '1000' (quá thấp)
        Kỳ vọng: food = None, không lỗi"""
        self.use_db(fetchone=[None])
        r = self.client.post("/today", data={"budget": "1000"})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(self.rendered[-1][1]["food"])

    def test_today_04_ngan_sach_khong_phai_so(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Ngân sách không phải số
        Đầu vào: budget = 'abc'
        Kỳ vọng: Báo 'Ngân sách phải là số.', không truy vấn DB"""
        r = self.client.post("/today", data={"budget": "abc"})
        self.assertEqual(r.status_code, 200)
        self.assertFlash("Ngân sách phải là số.")
        self.assertIsNone(self.rendered[-1][1]["food"])

    def test_today_05_ngan_sach_rong(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Để trống ngân sách
        Đầu vào: budget = ''
        Kỳ vọng: Báo 'Ngân sách phải là số.'"""
        self.client.post("/today", data={"budget": ""})
        self.assertFlash("Ngân sách phải là số.")

    def test_today_06_ghi_hanh_vi(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Người dùng đăng nhập dùng chức năng
        Đầu vào: budget = '60000', đã đăng nhập
        Kỳ vọng: Ghi hành vi 'hom_nay_an_gi' kèm ngân sách 60000.0"""
        self.login_as(uid=2)
        self.use_db(fetchone=[None])
        self.client.post("/today", data={"budget": "60000"})
        self.assertEqual(self.behaviors[0], {"manguoidung": 2, "loaihanhvi": "hom_nay_an_gi",
                                             "ngansach": 60000.0})

    @unittest.expectedFailure
    def test_today_07_ngan_sach_am(self):
        """Module: Hôm nay ăn gì?
        Tiêu đề: Ngân sách âm (LỖI PHÁT HIỆN)
        Đầu vào: budget = '-5000'
        Kỳ vọng: Từ chối giá trị âm, báo lỗi, không truy vấn DB.
        Ghi chú lỗi: Server chỉ bắt ValueError nên chấp nhận số âm và vẫn truy vấn."""
        _, cur = self.use_db(fetchone=[None])
        self.client.post("/today", data={"budget": "-5000"})
        self.assertEqual(cur.executed, [])


# ===========================================================================
# 6. YÊU THÍCH
# ===========================================================================
class TestFavorite(Base):
    def test_fav_01_chua_dang_nhap(self):
        """Module: Yêu thích
        Tiêu đề: Khách bấm yêu thích
        Đầu vào: POST /favorite/5, chưa đăng nhập
        Kỳ vọng: Chuyển tới /login, báo cần đăng nhập, không ghi DB"""
        r = self.client.post("/favorite/5")
        self.assertRedirect(r, "/login")
        self.assertFlash("Vui lòng đăng nhập để yêu thích món ăn.")

    def test_fav_02_them_yeu_thich(self):
        """Module: Yêu thích
        Tiêu đề: Thêm món vào yêu thích
        Đầu vào: POST /favorite/5, món chưa có trong yêu thích
        Kỳ vọng: INSERT vào yeuthich, commit, ghi hành vi 'them_yeu_thich', quay về /food/5"""
        self.login_as(uid=3)
        conn, cur = self.use_db(fetchone=[None])
        r = self.client.post("/favorite/5")
        self.assertRedirect(r, "/food/5")
        self.assertTrue(cur.sqls("INSERT INTO yeuthich"))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(self.behaviors[0]["loaihanhvi"], "them_yeu_thich")
        self.assertFlash("Đã thêm món ăn vào yêu thích.")

    def test_fav_03_bo_yeu_thich(self):
        """Module: Yêu thích
        Tiêu đề: Bỏ món khỏi yêu thích (bấm lần 2)
        Đầu vào: POST /favorite/5, món đã có trong yêu thích
        Kỳ vọng: DELETE khỏi yeuthich, commit, ghi hành vi 'bo_yeu_thich'"""
        self.login_as(uid=3)
        conn, cur = self.use_db(fetchone=[(3,)])
        self.client.post("/favorite/5")
        self.assertTrue(cur.sqls("DELETE FROM yeuthich"))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(self.behaviors[0]["loaihanhvi"], "bo_yeu_thich")
        self.assertFlash("Đã bỏ món ăn khỏi yêu thích.")

    def test_fav_04_loi_db_rollback(self):
        """Module: Yêu thích
        Tiêu đề: Lỗi CSDL khi thêm yêu thích
        Đầu vào: INSERT ném lỗi
        Kỳ vọng: rollback, báo 'Không thể thực hiện thao tác.', không ghi hành vi"""
        self.login_as()
        conn, _ = self.use_db(fetchone=[None], raise_on="INSERT INTO yeuthich")
        self.client.post("/favorite/5")
        self.assertEqual(conn.rollbacks, 1)
        self.assertEqual(conn.commits, 0)
        self.assertFlash("Không thể thực hiện thao tác.")
        self.assertEqual(self.behaviors, [])

    def test_fav_05_danh_sach_chua_dang_nhap(self):
        """Module: Yêu thích
        Tiêu đề: Xem danh sách yêu thích khi chưa đăng nhập
        Đầu vào: GET /favorites
        Kỳ vọng: Chuyển tới /login"""
        r = self.client.get("/favorites")
        self.assertRedirect(r, "/login")

    def test_fav_06_danh_sach_cua_toi(self):
        """Module: Yêu thích
        Tiêu đề: Xem danh sách yêu thích của mình
        Đầu vào: GET /favorites, đã đăng nhập
        Kỳ vọng: HTTP 200; truy vấn lọc theo đúng manguoidung của session"""
        self.login_as(uid=8)
        _, cur = self.use_db(fetchall=[[{"mamon": 1, "tenmon": "Phở"}]])
        r = self.client.get("/favorites")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(cur.executed[-1][1], (8,))
        self.assertEqual(len(self.rendered[-1][1]["foods"]), 1)


# ===========================================================================
# 7. ĐÁNH GIÁ
# ===========================================================================
class TestReview(Base):
    def test_rev_01_chua_dang_nhap(self):
        """Module: Đánh giá
        Tiêu đề: Khách gửi đánh giá
        Đầu vào: POST /review/5, chưa đăng nhập
        Kỳ vọng: Chuyển tới /login"""
        r = self.client.post("/review/5", data={"diem": "5"})
        self.assertRedirect(r, "/login")
        self.assertFlash("Vui lòng đăng nhập để đánh giá món ăn.")

    def test_rev_02_diem_ngoai_khoang(self):
        """Module: Đánh giá
        Tiêu đề: Điểm ngoài khoảng 1-5 (biên 0 và 6)
        Đầu vào: diem = 0, sau đó diem = 6
        Kỳ vọng: Cả hai đều báo 'Vui lòng chọn từ 1 đến 5 sao.', không ghi DB"""
        self.login_as()
        for d in ("0", "6", "-1"):
            self.client.post("/review/5", data={"diem": d})
        self.assertEqual(self.flashes().count("Vui lòng chọn từ 1 đến 5 sao."), 3)

    def test_rev_03_diem_khong_phai_so(self):
        """Module: Đánh giá
        Tiêu đề: Điểm không phải số nguyên
        Đầu vào: diem = 'abc' và diem = '3.5'
        Kỳ vọng: Báo 'Vui lòng chọn từ 1 đến 5 sao.', không lỗi 500"""
        self.login_as()
        for d in ("abc", "3.5"):
            r = self.client.post("/review/5", data={"diem": d})
            self.assertEqual(r.status_code, 302)
        self.assertEqual(self.flashes().count("Vui lòng chọn từ 1 đến 5 sao."), 2)

    def test_rev_04_thieu_diem(self):
        """Module: Đánh giá
        Tiêu đề: Không gửi trường điểm
        Đầu vào: POST không có 'diem'
        Kỳ vọng: Báo 'Vui lòng chọn từ 1 đến 5 sao.'"""
        self.login_as()
        self.client.post("/review/5", data={})
        self.assertFlash("Vui lòng chọn từ 1 đến 5 sao.")

    def test_rev_05_them_moi(self):
        """Module: Đánh giá
        Tiêu đề: Gửi đánh giá lần đầu (biên 1 và 5 sao)
        Đầu vào: diem = 5, binhluan = '  Rất ngon  '
        Kỳ vọng: INSERT danhgia (bình luận đã bỏ khoảng trắng), commit, ghi hành vi 'danh_gia'"""
        self.login_as(uid=6)
        conn, cur = self.use_db(fetchone=[None])
        r = self.client.post("/review/5", data={"diem": "5", "binhluan": "  Rất ngon  "})
        self.assertRedirect(r, "/food/5")
        ins = cur.sqls("INSERT INTO danhgia")
        self.assertEqual(ins[0][1], (6, 5, 5, "Rất ngon"))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(self.behaviors[0]["loaihanhvi"], "danh_gia")
        self.assertFlash("Đánh giá món ăn thành công.")

    def test_rev_06_cap_nhat_danh_gia_cu(self):
        """Module: Đánh giá
        Tiêu đề: Đánh giá lại món đã đánh giá
        Đầu vào: diem = 3; người dùng đã có đánh giá (mã 12)
        Kỳ vọng: UPDATE đánh giá cũ (không tạo bản ghi trùng), báo 'Đã cập nhật đánh giá của bạn.'"""
        self.login_as(uid=6)
        conn, cur = self.use_db(fetchone=[(12,)])
        self.client.post("/review/5", data={"diem": "3", "binhluan": ""})
        self.assertTrue(cur.sqls("UPDATE danhgia"))
        self.assertFalse(cur.sqls("INSERT INTO danhgia"))
        self.assertEqual(cur.sqls("UPDATE danhgia")[0][1], (3, "", 12))
        self.assertFlash("Đã cập nhật đánh giá của bạn.")

    def test_rev_07_loi_db_rollback(self):
        """Module: Đánh giá
        Tiêu đề: Lỗi CSDL khi lưu đánh giá
        Đầu vào: INSERT ném lỗi (ví dụ món không tồn tại)
        Kỳ vọng: rollback, báo 'Không thể lưu đánh giá.', không ghi hành vi"""
        self.login_as()
        conn, _ = self.use_db(fetchone=[None], raise_on="INSERT INTO danhgia")
        self.client.post("/review/5", data={"diem": "4"})
        self.assertEqual(conn.rollbacks, 1)
        self.assertFlash("Không thể lưu đánh giá.")
        self.assertEqual(self.behaviors, [])


# ===========================================================================
# 8. PHÂN QUYỀN QUẢN TRỊ
# ===========================================================================
ADMIN_ROUTES = ["/admin", "/admin/users", "/admin/foods", "/admin/ingredients",
                "/admin/categories", "/admin/reviews", "/admin/related-data"]


class TestAdminAccess(Base):
    def test_acl_01_khach_bi_chan(self):
        """Module: Phân quyền
        Tiêu đề: Khách truy cập 7 trang quản trị
        Đầu vào: GET từng URL /admin, /admin/users, /admin/foods, /admin/ingredients, /admin/categories, /admin/reviews, /admin/related-data (chưa đăng nhập)
        Kỳ vọng: Cả 7 trang đều chuyển tới /login"""
        for url in ADMIN_ROUTES:
            r = self.client.get(url)
            self.assertRedirect(r, "/login")

    def test_acl_02_user_thuong_bi_chan(self):
        """Module: Phân quyền
        Tiêu đề: Tài khoản quyền 'user' truy cập 7 trang quản trị
        Đầu vào: Như trên nhưng đăng nhập với quyen='user'
        Kỳ vọng: Cả 7 trang đều chuyển về trang chủ, báo không có quyền"""
        self.login_as("user")
        for url in ADMIN_ROUTES:
            r = self.client.get(url)
            self.assertRedirect(r, "/")

    def test_acl_03_user_thuong_khong_the_post(self):
        """Module: Phân quyền
        Tiêu đề: User thường gửi POST trực tiếp để xóa/sửa dữ liệu
        Đầu vào: POST action=delete tới /admin/foods, /admin/ingredients, /admin/categories, /admin/reviews, /admin/users (quyen='user')
        Kỳ vọng: Bị chặn, không truy vấn DB, không commit"""
        self.login_as("user")
        conn, cur = self.use_db()
        for url in ["/admin/foods", "/admin/ingredients", "/admin/categories",
                    "/admin/reviews", "/admin/users"]:
            r = self.client.post(url, data={"action": "delete", "mamon": "1", "manguyenlieu": "1",
                                            "madanhmuc": "1", "madanhgia": "1",
                                            "manguoidung": "2", "quyen": "admin"})
            self.assertRedirect(r, "/")
        self.assertEqual(cur.executed, [])
        self.assertEqual(conn.commits, 0)

    def test_acl_04_admin_vao_duoc_dashboard(self):
        """Module: Phân quyền
        Tiêu đề: Admin truy cập trang quản trị
        Đầu vào: GET /admin với quyen='admin'
        Kỳ vọng: HTTP 200, template admin/dashboard.html"""
        self.login_as("admin")
        r = self.client.get("/admin")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.rendered[-1][0], "admin/dashboard.html")

    def test_acl_05_admin_doi_quyen_nguoi_khac(self):
        """Module: Phân quyền
        Tiêu đề: Admin đổi quyền người dùng khác
        Đầu vào: manguoidung=2, quyen='admin' (admin đang đăng nhập có mã 1)
        Kỳ vọng: UPDATE nguoidung với ('admin','2'), commit, báo thành công"""
        self.login_as("admin", uid=1)
        conn, cur = self.use_db()
        self.client.post("/admin/users", data={"manguoidung": "2", "quyen": "admin"})
        self.assertEqual(cur.sqls("UPDATE nguoidung")[0][1], ("admin", "2"))
        self.assertEqual(conn.commits, 1)
        self.assertFlash("Đã cập nhật quyền người dùng.")

    def test_acl_06_admin_khong_doi_quyen_chinh_minh(self):
        """Module: Phân quyền
        Tiêu đề: Admin tự hạ quyền của chính mình
        Đầu vào: manguoidung = mã của admin đang đăng nhập, quyen='user'
        Kỳ vọng: Từ chối, báo 'Không thể thay đổi quyền của chính tài khoản đang đăng nhập.'"""
        self.login_as("admin", uid=1)
        conn, cur = self.use_db()
        self.client.post("/admin/users", data={"manguoidung": "1", "quyen": "user"})
        self.assertFlash("Không thể thay đổi quyền của chính tài khoản")
        self.assertFalse(cur.sqls("UPDATE nguoidung"))

    def test_acl_07_quyen_khong_hop_le(self):
        """Module: Phân quyền
        Tiêu đề: Gán quyền không hợp lệ
        Đầu vào: quyen = 'superadmin'
        Kỳ vọng: Từ chối, báo 'Quyền không hợp lệ.'"""
        self.login_as("admin", uid=1)
        _, cur = self.use_db()
        self.client.post("/admin/users", data={"manguoidung": "2", "quyen": "superadmin"})
        self.assertFlash("Quyền không hợp lệ.")
        self.assertFalse(cur.sqls("UPDATE nguoidung"))


# ===========================================================================
# 9. QUẢN LÝ MÓN ĂN
# ===========================================================================
class TestAdminFoods(Base):
    def setUp(self):
        super().setUp()
        self.login_as("admin", uid=1)

    def test_food_01_thieu_ten_mon(self):
        """Module: Quản lý món ăn
        Tiêu đề: Thêm món không có tên
        Đầu vào: action=add, tenmon=''
        Kỳ vọng: Báo 'Vui lòng nhập tên món ăn.', không INSERT"""
        _, cur = self.use_db()
        self.client.post("/admin/foods", data={"action": "add", "tenmon": "  "})
        self.assertFlash("Vui lòng nhập tên món ăn.")
        self.assertFalse(cur.sqls("INSERT INTO monan"))

    def test_food_02_tu_tinh_chi_phi_kcal(self):
        """Module: Quản lý món ăn
        Tiêu đề: Tự tính chi phí và kcal khi thêm món
        Đầu vào: Gà 200 g (giá 10/g, 165 kcal/100g) + Trứng 2 quả (giá 3000/quả, 70 kcal/quả)
        Kỳ vọng: chi phí = 200*10 + 2*3000 = 8000; kcal = 200/100*165 + 2*70 = 470; lưu 2 dòng monan_nguyenlieu"""
        conn, cur = self.use_db(
            lastrowid=9,
            fetchone=[{"donvi": "g", "giathamkhao": 10, "kcal": 165},
                      {"donvi": "quả", "giathamkhao": 3000, "kcal": 70}])
        self.client.post("/admin/foods", data={
            "action": "add", "tenmon": "Gà hấp trứng", "thoigian": "30",
            "manguyenlieu[]": ["1", "2"], "soluong[]": ["200", "2"]})
        self.assertEqual(cur.sqls("UPDATE monan SET")[-1][1], (8000.0, 470.0, 9))
        self.assertEqual(len(cur.sqls("INSERT INTO monan_nguyenlieu")), 2)
        self.assertEqual(conn.commits, 1)

    def test_food_03_bo_qua_dong_khong_hop_le(self):
        """Module: Quản lý món ăn
        Tiêu đề: Bỏ qua dòng nguyên liệu không hợp lệ
        Đầu vào: số lượng 0, số lượng 'abc', nguyên liệu rỗng, nguyên liệu không tồn tại, và 1 dòng hợp lệ (100 g, giá 5, 100 kcal)
        Kỳ vọng: Chỉ dòng hợp lệ được lưu: chi phí 500, kcal 100"""
        _, cur = self.use_db(
            lastrowid=4,
            fetchone=[None, {"donvi": "g", "giathamkhao": 5, "kcal": 100}])
        # thứ tự dòng: (rỗng) | soluong=0 | soluong='abc' | id=99 không tồn tại | id=1 hợp lệ
        self.client.post("/admin/foods", data={
            "action": "add", "tenmon": "Món thử",
            "manguyenlieu[]": ["", "1", "1", "99", "1"],
            "soluong[]": ["10", "0", "abc", "50", "100"]})
        self.assertEqual(len(cur.sqls("INSERT INTO monan_nguyenlieu")), 1)
        self.assertEqual(cur.sqls("UPDATE monan SET")[-1][1], (500.0, 100.0, 4))

    def test_food_04_xoa_thieu_ma(self):
        """Module: Quản lý món ăn
        Tiêu đề: Xóa món nhưng thiếu mã món
        Đầu vào: action=delete, không có mamon
        Kỳ vọng: Báo 'Không xác định được món ăn cần xóa.', không DELETE"""
        _, cur = self.use_db()
        self.client.post("/admin/foods", data={"action": "delete"})
        self.assertFlash("Không xác định được món ăn cần xóa.")
        self.assertFalse(cur.sqls("DELETE FROM monan"))

    def test_food_05_xoa_thanh_cong(self):
        """Module: Quản lý món ăn
        Tiêu đề: Xóa món ăn
        Đầu vào: action=delete, mamon=7
        Kỳ vọng: DELETE FROM monan WHERE mamon=7, commit, báo thành công"""
        conn, cur = self.use_db()
        self.client.post("/admin/foods", data={"action": "delete", "mamon": "7"})
        self.assertEqual(cur.sqls("DELETE FROM monan")[0][1], ("7",))
        self.assertEqual(conn.commits, 1)
        self.assertFlash("Đã xóa món ăn thành công.")

    @unittest.expectedFailure
    def test_food_06_mon_khong_nguyen_lieu(self):
        """Module: Quản lý món ăn
        Tiêu đề: Thêm món không có nguyên liệu nào (LỖI PHÁT HIỆN)
        Đầu vào: action=add, tenmon='Món rỗng', không chọn nguyên liệu
        Kỳ vọng: Từ chối vì không tính được chi phí/kcal hợp lệ.
        Ghi chú lỗi: Món vẫn được lưu với chiphi=0, kcal=0 nên xuất hiện ở mọi mức ngân sách trong 'Hôm nay ăn gì?'."""
        conn, cur = self.use_db(lastrowid=3)
        self.client.post("/admin/foods", data={"action": "add", "tenmon": "Món rỗng"})
        self.assertEqual(conn.commits, 0)


# ===========================================================================
# 10. QUẢN LÝ NGUYÊN LIỆU
# ===========================================================================
class TestAdminIngredients(Base):
    def setUp(self):
        super().setUp()
        self.login_as("admin", uid=1)

    FORM = {"action": "add", "tennguyenlieu": "Thịt gà", "donvi": "g",
            "giathamkhao": "120", "kcal": "165"}

    def test_ing_01_thieu_ten(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Thêm nguyên liệu không có tên
        Đầu vào: tennguyenlieu=''
        Kỳ vọng: Báo 'Vui lòng nhập tên nguyên liệu.'"""
        _, cur = self.use_db()
        self.client.post("/admin/ingredients", data=dict(self.FORM, tennguyenlieu=" "))
        self.assertFlash("Vui lòng nhập tên nguyên liệu.")
        self.assertFalse(cur.sqls("INSERT INTO nguyenlieu"))

    def test_ing_02_gia_khong_phai_so(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Giá hoặc kcal không phải số
        Đầu vào: giathamkhao='abc'
        Kỳ vọng: Báo 'Giá tham khảo và kcal phải là số.'"""
        _, cur = self.use_db()
        self.client.post("/admin/ingredients", data=dict(self.FORM, giathamkhao="abc"))
        self.assertFlash("Giá tham khảo và kcal phải là số.")
        self.assertFalse(cur.sqls("INSERT INTO nguyenlieu"))

    def test_ing_03_trung_ten(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Thêm nguyên liệu trùng tên
        Đầu vào: tên đã tồn tại
        Kỳ vọng: Báo 'Nguyên liệu này đã tồn tại.'"""
        _, cur = self.use_db(fetchone=[{"manguyenlieu": 1}])
        self.client.post("/admin/ingredients", data=self.FORM)
        self.assertFlash("Nguyên liệu này đã tồn tại.")
        self.assertFalse(cur.sqls("INSERT INTO nguyenlieu"))

    def test_ing_04_them_thanh_cong(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Thêm nguyên liệu hợp lệ
        Đầu vào: Thịt gà, g, 120, 165
        Kỳ vọng: INSERT với ('Thịt gà','g',120.0,165.0), commit"""
        conn, cur = self.use_db(fetchone=[None])
        self.client.post("/admin/ingredients", data=self.FORM)
        self.assertEqual(cur.sqls("INSERT INTO nguyenlieu")[0][1], ("Thịt gà", "g", 120.0, 165.0))
        self.assertEqual(conn.commits, 1)
        self.assertFlash("Đã thêm nguyên liệu thành công.")

    def test_ing_05_xoa_dang_duoc_dung(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Xóa nguyên liệu đang được dùng trong món ăn
        Đầu vào: nguyên liệu có trong monan_nguyenlieu
        Kỳ vọng: Từ chối, báo 'Không thể xóa nguyên liệu đang được sử dụng trong món ăn.'"""
        _, cur = self.use_db(fetchone=[(1,)])
        self.client.post("/admin/ingredients", data={"action": "delete", "manguyenlieu": "1"})
        self.assertFlash("Không thể xóa nguyên liệu đang được sử dụng")
        self.assertFalse(cur.sqls("DELETE FROM nguyenlieu"))

    def test_ing_06_xoa_thanh_cong(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Xóa nguyên liệu không dùng
        Đầu vào: nguyên liệu chưa gắn món nào
        Kỳ vọng: DELETE + commit, báo thành công"""
        conn, cur = self.use_db(fetchone=[None])
        self.client.post("/admin/ingredients", data={"action": "delete", "manguyenlieu": "1"})
        self.assertTrue(cur.sqls("DELETE FROM nguyenlieu"))
        self.assertEqual(conn.commits, 1)
        self.assertFlash("Đã xóa nguyên liệu thành công.")

    @unittest.expectedFailure
    def test_ing_07_gia_am(self):
        """Module: Quản lý nguyên liệu
        Tiêu đề: Giá và kcal âm khi gửi trực tiếp (LỖI PHÁT HIỆN)
        Đầu vào: giathamkhao='-100', kcal='-50' (vượt qua min=0 của HTML bằng cách gửi request trực tiếp)
        Kỳ vọng: Server từ chối giá trị âm.
        Ghi chú lỗi: Chỉ kiểm tra min=0 ở trình duyệt; server vẫn INSERT, làm sai chi phí/kcal của mọi món dùng nguyên liệu này."""
        conn, cur = self.use_db(fetchone=[None])
        self.client.post("/admin/ingredients",
                         data=dict(self.FORM, giathamkhao="-100", kcal="-50"))
        self.assertFalse(cur.sqls("INSERT INTO nguyenlieu"))


# ===========================================================================
# 11. QUẢN LÝ DANH MỤC
# ===========================================================================
class TestAdminCategories(Base):
    def setUp(self):
        super().setUp()
        self.login_as("admin", uid=1)

    def test_cat_01_thieu_ten(self):
        """Module: Quản lý danh mục
        Tiêu đề: Thêm danh mục không có tên
        Đầu vào: tendanhmuc=''
        Kỳ vọng: Báo 'Vui lòng nhập tên danh mục.'"""
        self.use_db()
        self.client.post("/admin/categories", data={"action": "add", "tendanhmuc": ""})
        self.assertFlash("Vui lòng nhập tên danh mục.")

    def test_cat_02_trung_ten(self):
        """Module: Quản lý danh mục
        Tiêu đề: Thêm danh mục trùng tên
        Đầu vào: tên đã tồn tại
        Kỳ vọng: Báo 'Danh mục này đã tồn tại.'"""
        _, cur = self.use_db(fetchone=[{"madanhmuc": 1}])
        self.client.post("/admin/categories", data={"action": "add", "tendanhmuc": "Món chính"})
        self.assertFlash("Danh mục này đã tồn tại.")
        self.assertFalse(cur.sqls("INSERT INTO danhmuc"))

    def test_cat_03_them_thanh_cong(self):
        """Module: Quản lý danh mục
        Tiêu đề: Thêm danh mục hợp lệ
        Đầu vào: tendanhmuc='Món canh'
        Kỳ vọng: INSERT + commit, báo thành công"""
        conn, cur = self.use_db(fetchone=[None])
        self.client.post("/admin/categories", data={"action": "add", "tendanhmuc": "Món canh"})
        self.assertEqual(cur.sqls("INSERT INTO danhmuc")[0][1], ("Món canh",))
        self.assertEqual(conn.commits, 1)

    def test_cat_04_sua_trung_ten(self):
        """Module: Quản lý danh mục
        Tiêu đề: Đổi tên trùng với danh mục khác
        Đầu vào: action=edit, tên đã thuộc danh mục khác
        Kỳ vọng: Báo 'Tên danh mục đã được sử dụng.', không UPDATE"""
        _, cur = self.use_db(fetchone=[{"madanhmuc": 2}])
        self.client.post("/admin/categories",
                         data={"action": "edit", "madanhmuc": "1", "tendanhmuc": "Món canh"})
        self.assertFlash("Tên danh mục đã được sử dụng.")
        self.assertFalse(cur.sqls("UPDATE danhmuc"))

    def test_cat_05_xoa_dang_duoc_dung(self):
        """Module: Quản lý danh mục
        Tiêu đề: Xóa danh mục đang có món ăn
        Đầu vào: danh mục có món thuộc về
        Kỳ vọng: Từ chối, báo 'Không thể xóa danh mục đang được sử dụng trong món ăn.'"""
        _, cur = self.use_db(fetchone=[(1,)])
        self.client.post("/admin/categories", data={"action": "delete", "madanhmuc": "1"})
        self.assertFlash("Không thể xóa danh mục đang được sử dụng")
        self.assertFalse(cur.sqls("DELETE FROM danhmuc"))

    def test_cat_06_xoa_thanh_cong(self):
        """Module: Quản lý danh mục
        Tiêu đề: Xóa danh mục rỗng
        Đầu vào: danh mục chưa có món
        Kỳ vọng: DELETE + commit"""
        conn, cur = self.use_db(fetchone=[None])
        self.client.post("/admin/categories", data={"action": "delete", "madanhmuc": "1"})
        self.assertTrue(cur.sqls("DELETE FROM danhmuc"))
        self.assertEqual(conn.commits, 1)


# ===========================================================================
# 12. QUẢN LÝ ĐÁNH GIÁ
# ===========================================================================
class TestAdminReviews(Base):
    def setUp(self):
        super().setUp()
        self.login_as("admin", uid=1)

    def test_arev_01_xoa_thieu_ma(self):
        """Module: Quản lý đánh giá
        Tiêu đề: Xóa đánh giá thiếu mã
        Đầu vào: action=delete, không có madanhgia
        Kỳ vọng: Báo 'Không xác định được đánh giá cần xóa.'"""
        _, cur = self.use_db()
        self.client.post("/admin/reviews", data={"action": "delete"})
        self.assertFlash("Không xác định được đánh giá cần xóa.")
        self.assertFalse(cur.sqls("DELETE FROM danhgia"))

    def test_arev_02_xoa_thanh_cong(self):
        """Module: Quản lý đánh giá
        Tiêu đề: Xóa đánh giá
        Đầu vào: madanhgia=5
        Kỳ vọng: DELETE + commit, báo 'Đã xóa đánh giá thành công.'"""
        conn, cur = self.use_db()
        self.client.post("/admin/reviews", data={"action": "delete", "madanhgia": "5"})
        self.assertEqual(cur.sqls("DELETE FROM danhgia")[0][1], ("5",))
        self.assertEqual(conn.commits, 1)
        self.assertFlash("Đã xóa đánh giá thành công.")


# ===========================================================================
# 13. QUẢN LÝ DỮ LIỆU LIÊN QUAN (món - nguyên liệu)
# ===========================================================================
class TestAdminRelated(Base):
    def setUp(self):
        super().setUp()
        self.login_as("admin", uid=1)

    def test_rel_01_thieu_truong(self):
        """Module: Dữ liệu liên quan
        Tiêu đề: Thêm liên kết thiếu thông tin
        Đầu vào: không chọn nguyên liệu
        Kỳ vọng: Báo 'Vui lòng nhập đầy đủ thông tin.'"""
        self.use_db()
        self.client.post("/admin/related-data",
                         data={"action": "add", "mamon": "1", "manguyenlieu": "", "soluong": "10"})
        self.assertFlash("Vui lòng nhập đầy đủ thông tin.")

    def test_rel_02_so_luong_khong_hop_le(self):
        """Module: Dữ liệu liên quan
        Tiêu đề: Số lượng 0, âm hoặc không phải số
        Đầu vào: soluong = '0', '-5', 'abc'
        Kỳ vọng: Cả 3 lần đều báo 'Số lượng phải là số lớn hơn 0.'"""
        self.use_db()
        for q in ("0", "-5", "abc"):
            self.client.post("/admin/related-data",
                             data={"action": "add", "mamon": "1", "manguyenlieu": "1", "soluong": q})
        self.assertEqual(self.flashes().count("Số lượng phải là số lớn hơn 0."), 3)

    def test_rel_03_trung_lien_ket(self):
        """Module: Dữ liệu liên quan
        Tiêu đề: Thêm liên kết món - nguyên liệu đã tồn tại
        Đầu vào: cặp (mamon, manguyenlieu) đã có
        Kỳ vọng: Báo 'Liên kết món ăn và nguyên liệu này đã tồn tại.'"""
        _, cur = self.use_db(fetchone=[(1,)])
        self.client.post("/admin/related-data",
                         data={"action": "add", "mamon": "1", "manguyenlieu": "1", "soluong": "10"})
        self.assertFlash("đã tồn tại")
        self.assertFalse(cur.sqls("INSERT INTO monan_nguyenlieu"))

    def test_rel_04_tu_lay_don_vi(self):
        """Module: Dữ liệu liên quan
        Tiêu đề: Để trống đơn vị, hệ thống lấy theo nguyên liệu
        Đầu vào: soluong=150, donvi=''; nguyên liệu có đơn vị 'g'
        Kỳ vọng: INSERT với đơn vị 'g', commit"""
        conn, cur = self.use_db(fetchone=[None, {"donvi": "g"}])
        self.client.post("/admin/related-data",
                         data={"action": "add", "mamon": "2", "manguyenlieu": "3",
                               "soluong": "150", "donvi": ""})
        ins = cur.sqls("INSERT INTO monan_nguyenlieu")
        self.assertEqual(ins[0][1], ("2", "3", 150.0, "g"))
        self.assertEqual(conn.commits, 1)

    @unittest.expectedFailure
    def test_rel_05_dong_bo_chi_phi_kcal(self):
        """Module: Dữ liệu liên quan
        Tiêu đề: Thêm liên kết nhưng chi phí/kcal của món không cập nhật (LỖI PHÁT HIỆN)
        Đầu vào: thêm nguyên liệu mới vào một món có sẵn qua trang Dữ liệu liên quan
        Kỳ vọng: monan.chiphi và monan.kcal được tính lại.
        Ghi chú lỗi: Chỉ trang Quản lý món ăn tính lại chi phí; trang này không UPDATE monan nên /today và /search lọc theo chi phí cũ (mất tính nhất quán)."""
        conn, cur = self.use_db(fetchone=[None, {"donvi": "g"}])
        self.client.post("/admin/related-data",
                         data={"action": "add", "mamon": "2", "manguyenlieu": "3",
                               "soluong": "150", "donvi": "g"})
        self.assertTrue(cur.sqls("UPDATE monan SET"))


# ===========================================================================
# 14. BẢO MẬT CẤU HÌNH
# ===========================================================================
class TestSecurity(Base):
    @unittest.expectedFailure
    def test_sec_01_khoa_bi_mat_trong_ma_nguon(self):
        """Module: Bảo mật
        Tiêu đề: secret_key không được viết cứng trong mã nguồn (LỖI PHÁT HIỆN)
        Đầu vào: kiểm tra app.secret_key
        Kỳ vọng: Lấy từ biến môi trường, không phải chuỗi cố định trong app.py.
        Ghi chú lỗi: Ai có mã nguồn đều có thể tự ký cookie session, giả mạo quyền 'admin'."""
        with open(app_module.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn('app.secret_key = "', src)

    @unittest.expectedFailure
    def test_sec_02_test_db_cong_khai(self):
        """Module: Bảo mật
        Tiêu đề: Đường dẫn /test-db mở công khai (LỖI PHÁT HIỆN)
        Đầu vào: GET /test-db khi chưa đăng nhập
        Kỳ vọng: Bị chặn hoặc chỉ dành cho admin.
        Ghi chú lỗi: Khách xem được tên cơ sở dữ liệu và nội dung lỗi kết nối."""
        self.use_db(fetchone=[("goiymonan",)])
        r = self.client.get("/test-db")
        self.assertNotEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)