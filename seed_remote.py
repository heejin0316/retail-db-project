import argparse
import random
from pathlib import Path

from database import execute_schema, get_connection, using_remote_database
from seed_data import (
    BRANDS,
    CUSTOMERS,
    ORDER_COUNT,
    PRODUCT_CATEGORIES,
    PURCHASE_ORDER_COUNT,
    RETAILERS,
    SEED,
    STORES,
    SUPPLIERS,
    build_order_rows,
    build_product_rows,
    build_purchase_order_rows,
    build_supplier_brand_rows,
    validate,
)


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

DROP_TABLES = [
    "supplier_brand",
    "purchase_order",
    "orders",
    "product",
    "store",
    "supplier",
    "product_category",
    "brand",
    "customer",
    "retailer",
]


def insert_rows(conn, table, columns, rows):
    placeholders = ", ".join("?" for _ in columns)
    col_sql = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
    for row in rows:
        conn.execute(sql, row)


def reset_schema(conn):
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in DROP_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table}")
    conn.commit()
    execute_schema(conn, SCHEMA_PATH)
    conn.execute("PRAGMA foreign_keys = ON")


def seed_remote_database(reset):
    rng = random.Random(SEED)
    product_rows = build_product_rows(rng)
    supplier_brand_rows = build_supplier_brand_rows()
    order_rows = build_order_rows(rng, product_rows)
    purchase_order_rows = build_purchase_order_rows(rng, product_rows, supplier_brand_rows)

    conn = get_connection(create_local=True)
    try:
        if reset:
            reset_schema(conn)

        insert_rows(conn, "retailer", ["retailer_id", "retailer_name", "website_url", "phone_number"], RETAILERS)
        insert_rows(conn, "store", ["store_id", "retailer_id", "store_name", "address", "business_hours"], STORES)
        insert_rows(conn, "customer", ["customer_id", "customer_name", "phone_number", "privacy_agreed"], CUSTOMERS)
        insert_rows(conn, "brand", ["brand_id", "brand_name"], BRANDS)
        insert_rows(
            conn,
            "product_category",
            ["category_id", "category_name", "parent_category_id"],
            PRODUCT_CATEGORIES,
        )
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
        insert_rows(
            conn,
            "orders",
            ["order_id", "customer_id", "store_id", "product_id", "order_datetime", "quantity", "unit_price"],
            order_rows,
        )
        insert_rows(
            conn,
            "purchase_order",
            ["purchase_order_id", "store_id", "supplier_id", "product_id", "order_datetime", "status", "order_quantity"],
            purchase_order_rows,
        )
        conn.commit()
        validate(conn)
        print("[OK] remote database seeded")
        print(f"[OK] orders: {ORDER_COUNT}")
        print(f"[OK] purchase_order: {PURCHASE_ORDER_COUNT}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Seed a Turso/libSQL remote database.")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all project tables before seeding")
    parser.add_argument(
        "--allow-local",
        action="store_true",
        help="Allow seeding the local SQLite database when TURSO_DATABASE_URL is not set",
    )
    args = parser.parse_args()

    if not using_remote_database() and not args.allow_local:
        raise RuntimeError(
            "TURSO_DATABASE_URL이 설정되어 있지 않습니다. 원격 DB를 seed하려면 환경변수를 설정하세요. "
            "로컬 DB에 테스트하려면 --allow-local을 추가하세요."
        )

    seed_remote_database(reset=args.reset)


if __name__ == "__main__":
    main()
