from database import get_db_connection

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def sort_foods_by_behavior(manguoidung, foods):
    """
    Xếp hạng kết quả tìm kiếm dựa trên:
    1. Hành vi người dùng
    2. Độ tương đồng nguyên liệu bằng TF-IDF + Cosine Similarity
    3. Mức ngân sách phù hợp

    Nếu người dùng chưa có lịch sử:
    - Không tính similarity cá nhân.
    - Giữ nguyên kết quả tìm kiếm.
    """

    if not foods:
        return []

    conn = get_db_connection()

    if conn is None:
        return foods

    cursor = conn.cursor(dictionary=True)

    try:

        # ==========================================
        # 1. Lấy lịch sử món ăn của người dùng
        # ==========================================

        cursor.execute("""
            SELECT DISTINCT mamon
            FROM hanhvi
            WHERE manguoidung = %s
              AND mamon IS NOT NULL
              AND loaihanhvi IN (
                  'xem_chi_tiet',
                  'them_yeu_thich'
              )
        """, (manguoidung,))

        behavior_rows = cursor.fetchall()

        behavior_mamon = [
            row["mamon"]
            for row in behavior_rows
        ]

        # ==========================================
        # 2. Lấy nguyên liệu của tất cả món ăn
        # ==========================================

        cursor.execute("""
            SELECT
                mn.mamon,
                n.tennguyenlieu
            FROM monan_nguyenlieu mn
            JOIN nguyenlieu n
                ON mn.manguyenlieu = n.manguyenlieu
        """)

        ingredient_rows = cursor.fetchall()

        ingredients_by_food = {}

        for row in ingredient_rows:

            mamon = row["mamon"]
            ingredient = row["tennguyenlieu"]

            if mamon not in ingredients_by_food:
                ingredients_by_food[mamon] = []

            ingredients_by_food[mamon].append(ingredient)

        # ==========================================
        # 3. Tạo danh sách món ăn
        # ==========================================

        all_food_ids = set(ingredients_by_food.keys())

        all_food_ids.update(
            food["mamon"]
            for food in foods
        )

        food_ids = list(all_food_ids)

        if not food_ids:
            return foods

        # ==========================================
        # 4. Tạo văn bản nguyên liệu
        # ==========================================

        ingredient_documents = []

        for mamon in food_ids:

            ingredients = ingredients_by_food.get(
                mamon,
                []
            )

            document = " ".join(ingredients)

            # Nếu món không có nguyên liệu
            # thì dùng một giá trị mặc định
            if not document:
                document = "khong_co_nguyen_lieu"

            ingredient_documents.append(document)

        # ==========================================
        # 5. TF-IDF
        # ==========================================

        vectorizer = TfidfVectorizer()

        tfidf_matrix = vectorizer.fit_transform(
            ingredient_documents
        )

        food_index = {
            mamon: index
            for index, mamon in enumerate(food_ids)
        }

        # ==========================================
        # 6. Tạo hồ sơ sở thích người dùng
        # ==========================================

        user_food_indexes = [
            food_index[mamon]
            for mamon in behavior_mamon
            if mamon in food_index
        ]

        if user_food_indexes:

            user_profile = tfidf_matrix[
                user_food_indexes
            ].mean(axis=0)

        else:

            # Người dùng mới
            user_profile = None

        # ==========================================
        # 7. Ngân sách trung bình
        # ==========================================

        cursor.execute("""
            SELECT AVG(ngansach) AS ngan_sach_trung_binh
            FROM hanhvi
            WHERE manguoidung = %s
              AND ngansach IS NOT NULL
        """, (manguoidung,))

        budget_row = cursor.fetchone()

        average_budget = budget_row[
            "ngan_sach_trung_binh"
        ]

        # ==========================================
        # 8. Tính điểm cho từng món
        # ==========================================

        for food in foods:

            mamon = food["mamon"]

            score = 0

            # --------------------------------------
            # 8.1. Điểm hành vi
            # --------------------------------------

            cursor.execute("""
                SELECT COUNT(*) AS solan
                FROM hanhvi
                WHERE manguoidung = %s
                  AND mamon = %s
                  AND loaihanhvi IN (
                      'xem_chi_tiet',
                      'them_yeu_thich'
                  )
            """, (
                manguoidung,
                mamon
            ))

            behavior_row = cursor.fetchone()

            behavior_count = behavior_row["solan"]

            score += behavior_count * 3

            # --------------------------------------
            # 8.2. Điểm Cosine Similarity
            # --------------------------------------

            similarity_score = 0

            if user_profile is not None:

                index = food_index.get(mamon)

                if index is not None:

                    food_vector = tfidf_matrix[index]

                    similarity = cosine_similarity(
                        user_profile,
                        food_vector
                    )[0][0]

                    similarity_score = float(
                        similarity
                    )

                    score += similarity_score * 10

            # --------------------------------------
            # 8.3. Điểm ngân sách
            # --------------------------------------

            if average_budget is not None:

                food_cost = float(
                    food["chiphi"] or 0
                )

                average_budget_value = float(
                    average_budget
                )

                if average_budget_value > 0:

                    difference = abs(
                        food_cost -
                        average_budget_value
                    )

                    if difference == 0:

                        score += 3

                    elif difference <= (
                        average_budget_value * 0.2
                    ):

                        score += 2

                    elif difference <= (
                        average_budget_value * 0.4
                    ):

                        score += 1

            # --------------------------------------
            # 8.4. Lưu điểm
            # --------------------------------------

            food["_similarity_score"] = round(
                similarity_score,
                4
            )

            food["_recommendation_score"] = round(
                score,
                4
            )

        # ==========================================
        # 9. Sắp xếp kết quả
        # ==========================================

        # Người dùng mới:
        # score của các món đều = 0 nếu không có
        # hành vi và ngân sách.
        #
        # Khi đó thứ tự sẽ giữ gần với kết quả
        # tìm kiếm ban đầu.

        foods = sorted(
            foods,
            key=lambda food: food.get(
                "_recommendation_score",
                0
            ),
            reverse=True
        )

        return foods

    except Exception as e:

        print("❌ Lỗi tính điểm gợi ý:")
        print(e)

        return foods

    finally:

        cursor.close()
        conn.close()