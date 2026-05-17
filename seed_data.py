import argparse
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


SEED = 20260517
ORDER_COUNT = 1500
PURCHASE_ORDER_COUNT = 150


# Values in these master lists come from "데이터 목록.pdf".
# Product stock/price/reorder/barcode values are generated because they are
# required by the final relation schema but are not listed in the PDF.

RETAILERS = [
    (1, "이마트24", None, None),
]

STORES = [
    (1, 1, "이대기숙사점", None, None),
    (2, 1, "이대과학관점", None, None),
    (3, 1, "이대아산공학관점", None, None),
    (4, 1, "이대도서관점", None, None),
    (5, 1, "이대경영관점", None, None),
    (6, 1, "이대아산공학관부속점", None, None),
    (7, 1, "이대음악관점", None, None),
    (8, 1, "이대조형관점", None, None),
    (9, 1, "이대조형관위성점", None, None),
    (10, 1, "이대학관점", None, None),
]

BRANDS = [
    (1, "농심"),
    (2, "삼양"),
    (3, "오뚜기"),
    (4, "팔도"),
    (5, "롯데웰푸드"),
    (6, "오리온"),
    (7, "해태"),
    (8, "크라운"),
    (9, "칠성"),
    (10, "코카콜라"),
    (11, "동원"),
    (12, "CJ 제일제당"),
    (13, "하림"),
    (14, "매일유업"),
    (15, "노브랜드"),
]

PRODUCT_CATEGORIES = [
    (1, "면 / 간편식", None),
    (2, "음료", None),
    (3, "과자 / 디저트", None),
    (4, "냉장 / 냉동식품", None),
    (5, "생활용품", None),
    (6, "컵라면", 1),
    (7, "즉석밥 / 간편식", 1),
    (8, "탄산음료", 2),
    (9, "커피 / 차 / 생수", 2),
    (10, "스낵과자", 3),
    (11, "초콜릿 / 비스킷 / 파이", 3),
    (12, "유제품", 4),
    (13, "냉장 / 냉동간편식", 4),
    (14, "위생용품", 5),
    (15, "생활잡화", 5),
]

SUPPLIERS = [
    (1, "서울식품유통"),
    (2, "한강음료유통"),
    (3, "이화스낵물류"),
    (4, "프레시냉장물류"),
    (5, "생활잡화공급"),
]

PRODUCT_SOURCE = [
    (1, "농심 신라면컵", "농심", "컵라면", "이대기숙사점"),
    (2, "농심 육개장사발면", "농심", "컵라면", "이대기숙사점"),
    (3, "농심 튀김우동컵", "농심", "컵라면", "이대기숙사점"),
    (4, "삼양 불닭볶음면컵", "삼양", "컵라면", "이대기숙사점"),
    (5, "삼양 까르보불닭볶음면컵", "삼양", "컵라면", "이대기숙사점"),
    (6, "오뚜기 진라면매운맛컵", "오뚜기", "컵라면", "이대기숙사점"),
    (7, "팔도 왕뚜껑", "팔도", "컵라면", "이대기숙사점"),
    (8, "팔도 도시락컵라면", "팔도", "컵라면", "이대기숙사점"),
    (9, "CJ 제일제당 햇반", "CJ 제일제당", "즉석밥 / 간편식", "이대과학관점"),
    (10, "CJ 제일제당 햇반컵반 미역국밥", "CJ 제일제당", "즉석밥 / 간편식", "이대과학관점"),
    (11, "CJ 제일제당 햇반컵반 제육덮밥", "CJ 제일제당", "즉석밥 / 간편식", "이대과학관점"),
    (12, "CJ 제일제당 비비고 육개장", "CJ 제일제당", "즉석밥 / 간편식", "이대과학관점"),
    (13, "오뚜기 3분카레", "오뚜기", "즉석밥 / 간편식", "이대과학관점"),
    (14, "오뚜기 컵밥 김치참치덮밥", "오뚜기", "즉석밥 / 간편식", "이대과학관점"),
    (15, "동원 양반 전복죽", "동원", "즉석밥 / 간편식", "이대과학관점"),
    (16, "노브랜드 즉석밥", "노브랜드", "즉석밥 / 간편식", "이대과학관점"),
    (17, "코카콜라 오리지널", "코카콜라", "탄산음료", "이대아산공학관점"),
    (18, "코카콜라 제로", "코카콜라", "탄산음료", "이대아산공학관점"),
    (19, "코카콜라 스프라이트", "코카콜라", "탄산음료", "이대아산공학관점"),
    (20, "코카콜라 환타 오렌지", "코카콜라", "탄산음료", "이대아산공학관점"),
    (21, "칠성 칠성사이다", "칠성", "탄산음료", "이대아산공학관점"),
    (22, "칠성 칠성사이다제로", "칠성", "탄산음료", "이대아산공학관점"),
    (23, "칠성 밀키스", "칠성", "탄산음료", "이대아산공학관점"),
    (24, "노브랜드 콜라", "노브랜드", "탄산음료", "이대아산공학관점"),
    (25, "매일유업 바리스타룰스 아메리카노", "매일유업", "커피 / 차 / 생수", "이대도서관점"),
    (26, "매일유업 바리스타룰스 라떼", "매일유업", "커피 / 차 / 생수", "이대도서관점"),
    (27, "매일유업 피크닉 사과", "매일유업", "커피 / 차 / 생수", "이대도서관점"),
    (28, "동원 보성홍차 아이스티", "동원", "커피 / 차 / 생수", "이대도서관점"),
    (29, "농심 백산수", "농심", "커피 / 차 / 생수", "이대도서관점"),
    (30, "칠성 아이시스 8.0", "칠성", "커피 / 차 / 생수", "이대도서관점"),
    (31, "코카콜라 조지아 오리지널", "코카콜라", "커피 / 차 / 생수", "이대도서관점"),
    (32, "노브랜드 생수", "노브랜드", "커피 / 차 / 생수", "이대도서관점"),
    (33, "농심 새우깡", "농심", "스낵과자", "이대경영관점"),
    (34, "농심 양파링", "농심", "스낵과자", "이대경영관점"),
    (35, "농심 포테토칩 오리지널", "농심", "스낵과자", "이대경영관점"),
    (36, "오리온 포카칩 오리지널", "오리온", "스낵과자", "이대경영관점"),
    (37, "오리온 오감자", "오리온", "스낵과자", "이대경영관점"),
    (38, "해태 맛동산", "해태", "스낵과자", "이대경영관점"),
    (39, "크라운 콘칩", "크라운", "스낵과자", "이대경영관점"),
    (40, "노브랜드 감자칩 오리지널", "노브랜드", "스낵과자", "이대경영관점"),
    (41, "롯데웰푸드 가나초콜릿", "롯데웰푸드", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (42, "롯데웰푸드 빼빼로 초코", "롯데웰푸드", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (43, "롯데웰푸드 칸쵸", "롯데웰푸드", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (44, "오리온 초코파이", "오리온", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (45, "오리온 다이제 초코", "오리온", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (46, "해태 에이스", "해태", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (47, "해태 자유시간", "해태", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (48, "크라운 쿠크다스", "크라운", "초콜릿 / 비스킷 / 파이", "이대아산공학관부속점"),
    (49, "매일유업 매일우유 오리지널", "매일유업", "유제품", "이대음악관점"),
    (50, "매일유업 소화가잘되는우유", "매일유업", "유제품", "이대음악관점"),
    (51, "매일유업 바이오 플레인요거트", "매일유업", "유제품", "이대음악관점"),
    (52, "매일유업 상하목장 유기농우유", "매일유업", "유제품", "이대음악관점"),
    (53, "노브랜드 굿밀크", "노브랜드", "유제품", "이대음악관점"),
    (54, "롯데웰푸드 월드콘", "롯데웰푸드", "유제품", "이대음악관점"),
    (55, "해태 부라보콘", "해태", "유제품", "이대음악관점"),
    (56, "오리온 닥터유 단백질바", "오리온", "유제품", "이대음악관점"),
    (57, "하림 닭가슴살 오리지널", "하림", "냉장 / 냉동간편식", "이대조형관점"),
    (58, "하림 닭가슴살 블랙페퍼", "하림", "냉장 / 냉동간편식", "이대조형관점"),
    (59, "하림 치킨너겟", "하림", "냉장 / 냉동간편식", "이대조형관점"),
    (60, "CJ 제일제당 비비고 왕교자", "CJ 제일제당", "냉장 / 냉동간편식", "이대조형관점"),
    (61, "CJ 제일제당 비비고 김치왕교자", "CJ 제일제당", "냉장 / 냉동간편식", "이대조형관점"),
    (62, "동원 리챔", "동원", "냉장 / 냉동간편식", "이대조형관점"),
    (63, "동원 동원참치 라이트스탠다드", "동원", "냉장 / 냉동간편식", "이대조형관점"),
    (64, "노브랜드 냉동피자", "노브랜드", "냉장 / 냉동간편식", "이대조형관점"),
    (65, "노브랜드 물티슈", "노브랜드", "위생용품", "이대조형관위성점"),
    (66, "노브랜드 미용티슈", "노브랜드", "위생용품", "이대조형관위성점"),
    (67, "노브랜드 화장지", "노브랜드", "위생용품", "이대조형관위성점"),
    (68, "노브랜드 키친타월", "노브랜드", "위생용품", "이대조형관위성점"),
    (69, "노브랜드 마스크", "노브랜드", "위생용품", "이대조형관위성점"),
    (70, "노브랜드 위생장갑", "노브랜드", "위생용품", "이대조형관위성점"),
    (71, "노브랜드 지퍼백", "노브랜드", "위생용품", "이대조형관위성점"),
    (72, "노브랜드 핸드워시", "노브랜드", "위생용품", "이대조형관위성점"),
    (73, "노브랜드 건전지 AA", "노브랜드", "생활잡화", "이대학관점"),
    (74, "노브랜드 건전지 AAA", "노브랜드", "생활잡화", "이대학관점"),
    (75, "노브랜드 종이컵", "노브랜드", "생활잡화", "이대학관점"),
    (76, "노브랜드 빨대", "노브랜드", "생활잡화", "이대학관점"),
    (77, "노브랜드 일회용접시", "노브랜드", "생활잡화", "이대학관점"),
    (78, "노브랜드 비닐봉투", "노브랜드", "생활잡화", "이대학관점"),
    (79, "노브랜드 다용도테이프", "노브랜드", "생활잡화", "이대학관점"),
    (80, "노브랜드 우산", "노브랜드", "생활잡화", "이대학관점"),
]

CUSTOMERS = [
    (1, "강시연", "010-1111-2222", 1),
    (2, "김연수", "010-1212-2121", 1),
    (3, "김채영", "010-3432-2343", 1),
    (4, "박선영", "010-1234-4321", 1),
    (5, "박시원", "010-4567-7654", 1),
    (6, "신우림", "010-4321-1234", 1),
    (7, "양승혜", "010-0987-7890", 1),
    (8, "정희진", "010-6543-3456", 0),
    (9, "진웨이", "010-9898-9898", 1),
    (10, "김수민", "010-3333-4444", 1),
    (11, "김서영", "010-3322-3322", 1),
    (12, "김민주", "010-0099-0099", 1),
    (13, "김연수", "010-4433-2233", 0),
    (14, "민지인", "010-1234-1234", 1),
    (15, "안례진", "010-2222-1111", 1),
    (16, "한승연", "010-6666-5555", 1),
    (17, "이윤주", "010-1234-5432", 0),
    (18, "윤수연", "010-8282-8282", 1),
    (19, "오수진", "010-5555-4321", 1),
    (20, "김윤지", "010-6655-7788", 1),
    (21, "정지혜", "010-8888-4433", 1),
    (22, "김지선", "010-1010-0101", 1),
    (23, "김하빈", "010-1234-0987", 0),
    (24, "이승호", "010-7656-8767", 1),
    (25, "김은숙", "010-1209-0912", 1),
]

SUPPLIER_BRANDS_BY_NAME = {
    "서울식품유통": ["농심", "삼양", "오뚜기", "팔도", "CJ 제일제당", "동원"],
    "한강음료유통": ["코카콜라", "칠성", "매일유업", "농심", "동원"],
    "이화스낵물류": ["롯데웰푸드", "오리온", "해태", "크라운", "농심"],
    "프레시냉장물류": ["하림", "CJ 제일제당", "동원", "매일유업", "롯데웰푸드"],
    "생활잡화공급": ["노브랜드"],
}

CATEGORY_PRICE_RANGES = {
    "컵라면": (1200, 2200),
    "즉석밥 / 간편식": (1500, 6500),
    "탄산음료": (1200, 2500),
    "커피 / 차 / 생수": (900, 3200),
    "스낵과자": (1200, 3000),
    "초콜릿 / 비스킷 / 파이": (1000, 4500),
    "유제품": (1200, 7000),
    "냉장 / 냉동간편식": (2500, 9500),
    "위생용품": (1500, 8000),
    "생활잡화": (1000, 12000),
}


def build_lookup(rows):
    return {name: row_id for row_id, name, *_ in rows}


def random_datetime(rng, start, end):
    seconds = int((end - start).total_seconds())
    value = start + timedelta(seconds=rng.randint(0, seconds))
    value = value.replace(
        minute=rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]),
        second=0,
        microsecond=0,
    )
    return value.strftime("%Y-%m-%d %H:%M:%S")


def build_supplier_brand_rows():
    supplier_id_by_name = build_lookup(SUPPLIERS)
    brand_id_by_name = build_lookup(BRANDS)
    rows = []
    for supplier_name, brand_names in SUPPLIER_BRANDS_BY_NAME.items():
        for brand_name in brand_names:
            rows.append((supplier_id_by_name[supplier_name], brand_id_by_name[brand_name]))
    return sorted(set(rows))


def generated_product_values(rng, product_id, category_name):
    low, high = CATEGORY_PRICE_RANGES[category_name]
    stock_quantity = rng.randint(15, 120)
    sale_price = rng.randrange(low, high + 1, 100)
    reorder_threshold = rng.randint(5, min(30, stock_quantity))
    barcode_number = f"880{product_id:010d}"
    return stock_quantity, sale_price, reorder_threshold, barcode_number


def build_product_rows(rng):
    brand_id_by_name = build_lookup(BRANDS)
    category_id_by_name = build_lookup(PRODUCT_CATEGORIES)
    store_id_by_name = {store_name: store_id for store_id, _, store_name, _, _ in STORES}
    rows = []
    for product_id, product_name, brand_name, category_name, store_name in PRODUCT_SOURCE:
        stock_quantity, sale_price, reorder_threshold, barcode_number = generated_product_values(
            rng, product_id, category_name
        )
        rows.append(
            (
                product_id,
                brand_id_by_name[brand_name],
                store_id_by_name[store_name],
                category_id_by_name[category_name],
                product_name,
                stock_quantity,
                sale_price,
                reorder_threshold,
                barcode_number,
            )
        )
    return rows


def weighted_choice(rng, rows, weight_fn):
    total = sum(weight_fn(row) for row in rows)
    pick = rng.uniform(0, total)
    current = 0
    for row in rows:
        current += weight_fn(row)
        if current >= pick:
            return row
    return rows[-1]


def build_order_rows(rng, products):
    start = datetime(2025, 5, 17, 0, 0, 0)
    end = datetime(2026, 5, 17, 23, 55, 0)
    rows = []
    popular_categories = {6, 7, 8, 9, 10}
    for order_id in range(1, ORDER_COUNT + 1):
        product = weighted_choice(
            rng,
            products,
            lambda row: 3.0 if row[3] in popular_categories else 1.4 if row[3] in {11, 12, 13} else 0.8,
        )
        rows.append(
            (
                order_id,
                rng.randint(1, len(CUSTOMERS)),
                product[2],
                product[0],
                random_datetime(rng, start, end),
                rng.choices([1, 2, 3, 4, 5], weights=[58, 24, 11, 5, 2], k=1)[0],
                product[6],
            )
        )
    return rows


def build_purchase_order_rows(rng, products, supplier_brand_rows):
    start = datetime(2025, 3, 1, 9, 0, 0)
    end = datetime(2026, 2, 28, 18, 0, 0)
    suppliers_by_brand = {}
    for supplier_id, brand_id in supplier_brand_rows:
        suppliers_by_brand.setdefault(brand_id, []).append(supplier_id)
    statuses = ["REQUESTED", "APPROVED", "SHIPPED", "COMPLETED", "CANCELLED"]
    rows = []
    for purchase_order_id in range(1, PURCHASE_ORDER_COUNT + 1):
        product = weighted_choice(rng, products, lambda row: 2.5 if row[5] <= row[7] + 20 else 1.0)
        rows.append(
            (
                purchase_order_id,
                product[2],
                rng.choice(suppliers_by_brand[product[1]]),
                product[0],
                random_datetime(rng, start, end),
                rng.choices(statuses, weights=[18, 22, 24, 30, 6], k=1)[0],
                rng.randrange(10, 121, 5),
            )
        )
    return rows


def insert_rows(conn, table, columns, rows):
    placeholders = ", ".join("?" for _ in columns)
    col_sql = ", ".join(columns)
    conn.executemany(f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})", rows)


def seed_database(schema_path, db_path, reset):
    rng = random.Random(SEED)
    if reset and db_path.exists():
        db_path.unlink()

    schema_sql = schema_path.read_text(encoding="utf-8")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)

        supplier_brand_rows = build_supplier_brand_rows()
        product_rows = build_product_rows(rng)

        insert_rows(conn, "retailer", ["retailer_id", "retailer_name", "website_url", "phone_number"], RETAILERS)
        insert_rows(conn, "store", ["store_id", "retailer_id", "store_name", "address", "business_hours"], STORES)
        insert_rows(conn, "brand", ["brand_id", "brand_name"], BRANDS)
        insert_rows(conn, "product_category", ["category_id", "category_name", "parent_category_id"], PRODUCT_CATEGORIES)
        insert_rows(conn, "supplier", ["supplier_id", "supplier_name"], SUPPLIERS)
        insert_rows(conn, "supplier_brand", ["supplier_id", "brand_id"], supplier_brand_rows)
        insert_rows(
            conn,
            "product",
            [
                "product_id",
                "brand_id",
                "store_id",
                "category_id",
                "product_name",
                "stock_quantity",
                "sale_price",
                "reorder_threshold",
                "barcode_number",
            ],
            product_rows,
        )
        insert_rows(conn, "customer", ["customer_id", "customer_name", "phone_number", "privacy_agreed"], CUSTOMERS)
        insert_rows(
            conn,
            "orders",
            ["order_id", "customer_id", "store_id", "product_id", "order_datetime", "quantity", "unit_price"],
            build_order_rows(rng, product_rows),
        )
        insert_rows(
            conn,
            "purchase_order",
            ["purchase_order_id", "store_id", "supplier_id", "product_id", "order_datetime", "status", "order_quantity"],
            build_purchase_order_rows(rng, product_rows, supplier_brand_rows),
        )

        conn.commit()
        return validate(conn)


def validate(conn):
    expected_counts = {
        "retailer": 1,
        "store": 10,
        "brand": 15,
        "product_category": 15,
        "supplier": 5,
        "supplier_brand": len(build_supplier_brand_rows()),
        "product": 80,
        "customer": 25,
        "orders": ORDER_COUNT,
        "purchase_order": PURCHASE_ORDER_COUNT,
    }
    counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in expected_counts}
    if counts != expected_counts:
        raise RuntimeError(f"count mismatch: expected={expected_counts}, actual={counts}")

    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        raise RuntimeError(f"foreign key errors: {fk_errors}")

    product_columns = [row[1] for row in conn.execute("PRAGMA table_info(product)").fetchall()]
    expected_product_columns = [
        "product_id",
        "brand_id",
        "store_id",
        "category_id",
        "product_name",
        "stock_quantity",
        "sale_price",
        "reorder_threshold",
        "barcode_number",
    ]
    if product_columns != expected_product_columns:
        raise RuntimeError(f"unexpected product columns: {product_columns}")

    return counts


def main():
    parser = argparse.ArgumentParser(description="Seed SQLite database from 데이터 목록.pdf based data.")
    parser.add_argument("--schema", default="db/schema.sql")
    parser.add_argument("--db", default="market.db")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    counts = seed_database(Path(args.schema), Path(args.db), args.reset)
    print(f"[OK] seeded database: {args.db}")
    for table, count in counts.items():
        print(f"[OK] {table}: {count}")


if __name__ == "__main__":
    main()
