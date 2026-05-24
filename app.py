import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "market.db"
QUERY_TEST_PATH = BASE_DIR / "queries" / "query_test.py"

ALLOWED_TRANSITIONS = {
    "REQUESTED": ["APPROVED", "CANCELLED"],
    "APPROVED": ["SHIPPED", "CANCELLED"],
    "SHIPPED": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
}


def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "market.db 파일이 없습니다. 먼저 `python seed_data.py --reset --db market.db`를 실행하세요."
        )
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def input_int(prompt):
    value = input(prompt).strip()
    try:
        return int(value)
    except ValueError:
        print("숫자를 입력해야 합니다.")
        return None


def pause():
    input("\nEnter 키를 누르면 메뉴로 돌아갑니다.")


def print_rows(headers, rows):
    if not rows:
        print("조회 결과가 없습니다.")
        return

    string_rows = [[str(value) if value is not None else "" for value in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in string_rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    header_line = " | ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    divider = "-+-".join("-" * width for width in widths)
    print(header_line)
    print(divider)
    for row in string_rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def list_customers(conn, limit=10):
    rows = conn.execute(
        """
        SELECT customer_id, customer_name, phone_number
        FROM customer
        ORDER BY customer_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    print("\n[고객 목록 일부]")
    print_rows(["고객ID", "이름", "전화번호"], rows)


def list_products(conn, limit=20):
    rows = conn.execute(
        """
        SELECT
            p.product_id,
            p.product_name,
            s.store_name,
            p.stock_quantity,
            p.sale_price
        FROM product p
        JOIN store s
            ON p.store_id = s.store_id
        ORDER BY p.product_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    print("\n[제품 목록 일부]")
    print_rows(["제품ID", "제품명", "매장명", "재고량", "판매가격"], rows)


def list_stores(conn):
    rows = conn.execute(
        """
        SELECT store_id, store_name
        FROM store
        ORDER BY store_id
        """
    ).fetchall()
    print("\n[매장 목록]")
    print_rows(["매장ID", "매장명"], rows)


def register_order():
    print("\n=== 고객 주문 등록 ===")
    try:
        with get_connection() as conn:
            list_customers(conn)
            list_products(conn)

            customer_id = input_int("\n고객ID 입력: ")
            if customer_id is None:
                return
            product_id = input_int("제품ID 입력: ")
            if product_id is None:
                return
            quantity = input_int("수량 입력: ")
            if quantity is None:
                return
            if quantity < 1:
                print("수량은 1개 이상이어야 합니다.")
                return

            customer = conn.execute(
                """
                SELECT customer_id, customer_name
                FROM customer
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()
            if customer is None:
                print("존재하지 않는 고객입니다.")
                return

            product = conn.execute(
                """
                SELECT
                    product_id,
                    store_id,
                    product_name,
                    sale_price,
                    stock_quantity
                FROM product
                WHERE product_id = ?
                """,
                (product_id,),
            ).fetchone()
            if product is None:
                print("존재하지 않는 제품입니다.")
                return

            _, store_id, product_name, sale_price, stock_quantity = product
            if stock_quantity < quantity:
                print("재고가 부족하여 주문할 수 없습니다.")
                print(f"현재 재고: {stock_quantity}")
                return

            try:
                conn.execute("BEGIN")
                conn.execute(
                    """
                    INSERT INTO orders (
                        customer_id,
                        store_id,
                        product_id,
                        order_datetime,
                        quantity,
                        unit_price
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        customer_id,
                        store_id,
                        product_id,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        quantity,
                        sale_price,
                    ),
                )
                conn.execute(
                    """
                    UPDATE product
                    SET stock_quantity = stock_quantity - ?
                    WHERE product_id = ?
                      AND stock_quantity >= ?
                    """,
                    (quantity, product_id, quantity),
                )
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                print(f"주문 처리 중 오류가 발생했습니다: {exc}")
                return

            print("주문이 완료되었습니다.")
            print(f"고객: {customer[1]}")
            print(f"제품: {product_name}")
            print(f"수량: {quantity}")
            print(f"판매단가: {sale_price}")

    except FileNotFoundError as exc:
        print(exc)


def view_store_inventory():
    print("\n=== 매장 재고 조회 ===")
    try:
        with get_connection() as conn:
            list_stores(conn)
            store_id = input_int("\n조회할 매장ID 입력: ")
            if store_id is None:
                return

            store = conn.execute(
                """
                SELECT store_id, store_name
                FROM store
                WHERE store_id = ?
                """,
                (store_id,),
            ).fetchone()
            if store is None:
                print("존재하지 않는 매장입니다.")
                return

            rows = conn.execute(
                """
                SELECT
                    product_id,
                    product_name,
                    stock_quantity,
                    reorder_threshold,
                    sale_price,
                    CASE
                        WHEN stock_quantity <= reorder_threshold THEN '필요'
                        ELSE '정상'
                    END AS reorder_needed
                FROM product
                WHERE store_id = ?
                ORDER BY
                    stock_quantity ASC,
                    product_id ASC
                """,
                (store_id,),
            ).fetchall()

            if not rows:
                print("해당 매장에 등록된 제품이 없습니다.")
                return

            print(f"\n[{store[1]} 재고 목록]")
            print_rows(
                ["제품ID", "제품명", "재고량", "재주문기준", "판매가격", "재주문"],
                rows,
            )

    except FileNotFoundError as exc:
        print(exc)


def create_auto_reorder():
    print("\n=== 자동 재주문 발주 생성 ===")
    try:
        with get_connection() as conn:
            targets = conn.execute(
                """
                SELECT
                    p.product_id,
                    p.store_id,
                    p.brand_id,
                    p.product_name,
                    p.stock_quantity,
                    p.reorder_threshold,
                    MIN(sb.supplier_id) AS supplier_id,
                    MAX(p.reorder_threshold * 3, 10) AS order_quantity
                FROM product p
                JOIN supplier_brand sb
                    ON p.brand_id = sb.brand_id
                WHERE p.stock_quantity <= p.reorder_threshold
                  AND NOT EXISTS (
                      SELECT 1
                      FROM purchase_order po
                      WHERE po.product_id = p.product_id
                        AND po.store_id = p.store_id
                        AND po.status IN ('REQUESTED', 'APPROVED')
                  )
                GROUP BY
                    p.product_id,
                    p.store_id,
                    p.brand_id,
                    p.product_name,
                    p.stock_quantity,
                    p.reorder_threshold
                ORDER BY
                    p.stock_quantity ASC,
                    p.product_id ASC
                """
            ).fetchall()

            if not targets:
                print("자동 재주문이 필요한 제품이 없습니다.")
                return

            created_rows = []
            try:
                conn.execute("BEGIN")
                for product_id, store_id, _, product_name, stock_quantity, reorder_threshold, supplier_id, order_quantity in targets:
                    cursor = conn.execute(
                        """
                        INSERT INTO purchase_order (
                            store_id,
                            supplier_id,
                            product_id,
                            order_datetime,
                            status,
                            order_quantity
                        )
                        VALUES (?, ?, ?, ?, 'REQUESTED', ?)
                        """,
                        (
                            store_id,
                            supplier_id,
                            product_id,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            order_quantity,
                        ),
                    )
                    created_rows.append(
                        (
                            cursor.lastrowid,
                            product_id,
                            product_name,
                            stock_quantity,
                            reorder_threshold,
                            supplier_id,
                            order_quantity,
                        )
                    )
                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                print(f"자동 재주문 발주 생성 중 오류가 발생했습니다: {exc}")
                return

            print("자동 재주문 발주가 생성되었습니다.")
            print_rows(
                ["발주ID", "제품ID", "제품명", "재고량", "재주문기준", "공급업체ID", "발주수량"],
                created_rows,
            )

    except FileNotFoundError as exc:
        print(exc)


def list_processable_purchase_orders(conn):
    rows = conn.execute(
        """
        SELECT
            po.purchase_order_id,
            po.status,
            po.order_quantity,
            po.order_datetime,
            s.store_name,
            p.product_name,
            su.supplier_name
        FROM purchase_order po
        JOIN store s
            ON po.store_id = s.store_id
        JOIN product p
            ON po.product_id = p.product_id
        JOIN supplier su
            ON po.supplier_id = su.supplier_id
        WHERE po.status NOT IN ('COMPLETED', 'CANCELLED')
        ORDER BY
            po.purchase_order_id
        LIMIT 30
        """
    ).fetchall()
    print("\n[처리 가능한 발주 목록 일부]")
    print_rows(["발주ID", "상태", "수량", "발주일시", "매장", "제품", "공급업체"], rows)


def process_purchase_order():
    print("\n=== 공급업체 발주 처리 ===")
    try:
        with get_connection() as conn:
            list_processable_purchase_orders(conn)

            purchase_order_id = input_int("\n처리할 발주ID 입력: ")
            if purchase_order_id is None:
                return

            purchase_order = conn.execute(
                """
                SELECT
                    purchase_order_id,
                    store_id,
                    product_id,
                    status,
                    order_quantity
                FROM purchase_order
                WHERE purchase_order_id = ?
                """,
                (purchase_order_id,),
            ).fetchone()
            if purchase_order is None:
                print("존재하지 않는 발주입니다.")
                return

            _, store_id, product_id, current_status, order_quantity = purchase_order
            next_statuses = ALLOWED_TRANSITIONS[current_status]

            if current_status == "COMPLETED":
                print("이미 완료된 발주는 변경할 수 없습니다.")
                return
            if current_status == "CANCELLED":
                print("이미 취소된 발주는 변경할 수 없습니다.")
                return

            print(f"현재 상태: {current_status}")
            print(f"변경 가능 상태: {', '.join(next_statuses)}")
            new_status = input("변경할 상태 입력: ").strip().upper()

            if new_status not in next_statuses:
                print("허용되지 않는 상태 변경입니다.")
                return

            try:
                conn.execute("BEGIN")
                conn.execute(
                    """
                    UPDATE purchase_order
                    SET status = ?
                    WHERE purchase_order_id = ?
                    """,
                    (new_status, purchase_order_id),
                )

                if new_status == "COMPLETED":
                    conn.execute(
                        """
                        UPDATE product
                        SET stock_quantity = stock_quantity + ?
                        WHERE product_id = ?
                          AND store_id = ?
                        """,
                        (order_quantity, product_id, store_id),
                    )

                conn.commit()
            except sqlite3.Error as exc:
                conn.rollback()
                print(f"발주 처리 중 오류가 발생했습니다: {exc}")
                return

            if new_status == "COMPLETED":
                print("발주가 완료 처리되었고 재고가 증가했습니다.")
            elif new_status == "CANCELLED":
                print("발주가 취소되었습니다.")
            else:
                print("발주 상태가 변경되었습니다.")

    except FileNotFoundError as exc:
        print(exc)


def run_sample_queries():
    print("\n=== Sample Query 실행 및 결과 저장 ===")
    if not QUERY_TEST_PATH.exists():
        print("queries/query_test.py 파일이 없습니다.")
        return

    result = subprocess.run(
        [sys.executable, str(QUERY_TEST_PATH)],
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr)

    if result.returncode == 0:
        print("Sample Query 실행 및 결과 저장이 완료되었습니다.")
    else:
        print("Sample Query 실행 중 오류가 발생했습니다.")


def customer_menu():
    while True:
        print("\n=== 고객 기능 ===")
        print("1. 고객 주문 등록")
        print("0. 뒤로가기")
        choice = input("메뉴 선택: ").strip()
        if choice == "1":
            register_order()
            pause()
        elif choice == "0":
            return
        else:
            print("잘못된 메뉴입니다.")


def admin_menu():
    while True:
        print("\n=== 관리자 기능 ===")
        print("1. 매장 재고 조회")
        print("2. 자동 재주문 발주 생성")
        print("3. 공급업체 발주 처리")
        print("0. 뒤로가기")
        choice = input("메뉴 선택: ").strip()
        if choice == "1":
            view_store_inventory()
            pause()
        elif choice == "2":
            create_auto_reorder()
            pause()
        elif choice == "3":
            process_purchase_order()
            pause()
        elif choice == "0":
            return
        else:
            print("잘못된 메뉴입니다.")


def analysis_menu():
    while True:
        print("\n=== 분석 기능 ===")
        print("1. Sample Query 실행 및 결과 저장")
        print("0. 뒤로가기")
        choice = input("메뉴 선택: ").strip()
        if choice == "1":
            run_sample_queries()
            pause()
        elif choice == "0":
            return
        else:
            print("잘못된 메뉴입니다.")


def main():
    while True:
        print("\n=== Retail DB CLI ===")
        print("1. 고객 기능")
        print("2. 관리자 기능")
        print("3. 분석 기능")
        print("0. 종료")
        choice = input("메뉴 선택: ").strip()

        if choice == "1":
            customer_menu()
        elif choice == "2":
            admin_menu()
        elif choice == "3":
            analysis_menu()
        elif choice == "0":
            print("프로그램을 종료합니다.")
            break
        else:
            print("잘못된 메뉴입니다.")


if __name__ == "__main__":
    main()
