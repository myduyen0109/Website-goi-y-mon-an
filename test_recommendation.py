from services.recommendation_service import sort_foods_by_behavior


foods = [
    {
        "mamon": 1,
        "tenmon": "Cơm gà"
    },
    {
        "mamon": 2,
        "tenmon": "Phở bò"
    },
    {
        "mamon": 3,
        "tenmon": "Mì xào bò"
    }
]


result = sort_foods_by_behavior(
    manguoidung=1,
    foods=foods
)


print("Kết quả sau khi sắp xếp:")

for food in result:
    print(
        food["mamon"],
        "-",
        food["tenmon"]
    )