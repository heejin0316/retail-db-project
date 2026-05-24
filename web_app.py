import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import markdown as md_lib
from flask import Flask, render_template, request, redirect, url_for, flash

from database import LOCAL_DB_PATH, get_connection, using_remote_database
from sample_query_runner import results_to_markdown, run_sample_queries

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = LOCAL_DB_PATH
QUERY_TEST_PATH = BASE_DIR / "queries" / "query_test.py"
QUERY_RESULTS_PATH = BASE_DIR / "queries" / "query_results.md"

ALLOWED_TRANSITIONS = {
    "REQUESTED": ["APPROVED", "CANCELLED"],
    "APPROVED": ["SHIPPED", "CANCELLED"],
    "SHIPPED": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "retail_db_secret_key_2026")


# ──────────────────────────────────────────
# DB 연결 헬퍼
# ──────────────────────────────────────────

# ──────────────────────────────────────────
# 메인 화면
# ──────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ──────────────────────────────────────────
# 1. 고객 주문 등록
# ──────────────────────────────────────────

@app.route("/order", methods=["GET", "POST"])
def order():
    conn = get_connection()
    customers = conn.execute(
        "SELECT customer_id, customer_name, phone_number FROM customer ORDER BY customer_id"
    ).fetchall()
    products = conn.execute(
        """
        SELECT p.product_id, p.product_name, s.store_name, p.stock_quantity, p.sale_price
        FROM product p
        JOIN store s ON p.store_id = s.store_id
        ORDER BY p.product_id
        """
    ).fetchall()

    result = None

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        product_id = request.form.get("product_id", "").strip()
        quantity = request.form.get("quantity", "").strip()

        # 유효성 검사
        error = None
        if not customer_id.isdigit():
            error = "고객ID는 숫자여야 합니다."
        elif not product_id.isdigit():
            error = "제품ID는 숫자여야 합니다."
        elif not quantity.isdigit() or int(quantity) < 1:
            error = "수량은 1 이상의 숫자여야 합니다."

        if error:
            conn.close()
            return render_template("order.html", customers=customers, products=products,
                                   error=error)

        customer_id = int(customer_id)
        product_id = int(product_id)
        quantity = int(quantity)

        # 고객 존재 확인
        customer = conn.execute(
            "SELECT customer_id, customer_name FROM customer WHERE customer_id = ?",
            (customer_id,)
        ).fetchone()
        if customer is None:
            conn.close()
            return render_template("order.html", customers=customers, products=products,
                                   error=f"고객ID {customer_id}는 존재하지 않습니다.")

        # 제품 존재 확인
        product = conn.execute(
            "SELECT product_id, store_id, product_name, sale_price, stock_quantity FROM product WHERE product_id = ?",
            (product_id,)
        ).fetchone()
        if product is None:
            conn.close()
            return render_template("order.html", customers=customers, products=products,
                                   error=f"제품ID {product_id}는 존재하지 않습니다.")

        store_id = product["store_id"]
        product_name = product["product_name"]
        sale_price = product["sale_price"]
        stock_quantity = product["stock_quantity"]

        if stock_quantity < quantity:
            conn.close()
            return render_template("order.html", customers=customers, products=products,
                                   error=f"재고가 부족합니다. 현재 재고: {stock_quantity}개")

        # 트랜잭션 처리
        try:
            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO orders (customer_id, store_id, product_id, order_datetime, quantity, unit_price)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    customer_id, store_id, product_id,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    quantity, sale_price,
                ),
            )
            conn.execute(
                """
                UPDATE product
                SET stock_quantity = stock_quantity - ?
                WHERE product_id = ? AND stock_quantity >= ?
                """,
                (quantity, product_id, quantity),
            )
            conn.commit()
            result = {
                "success": True,
                "customer_name": customer["customer_name"],
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": sale_price,
                "total": quantity * sale_price,
            }
        except sqlite3.Error as exc:
            conn.rollback()
            conn.close()
            return render_template("order.html", customers=customers, products=products,
                                   error=f"주문 처리 중 오류: {exc}")

    conn.close()
    return render_template("order.html", customers=customers, products=products, result=result)


# ──────────────────────────────────────────
# 2. 매장 재고 조회
# ──────────────────────────────────────────

@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    conn = get_connection()
    stores = conn.execute(
        "SELECT store_id, store_name FROM store ORDER BY store_id"
    ).fetchall()

    inventory_rows = None
    selected_store = None
    error = None

    store_id_param = request.form.get("store_id") if request.method == "POST" else request.args.get("store_id")

    if store_id_param is not None:
        if not str(store_id_param).strip().isdigit():
            error = "매장ID는 숫자여야 합니다."
        else:
            store_id = int(store_id_param)
            selected_store = conn.execute(
                "SELECT store_id, store_name FROM store WHERE store_id = ?", (store_id,)
            ).fetchone()
            if selected_store is None:
                error = f"매장ID {store_id}는 존재하지 않습니다."
            else:
                inventory_rows = conn.execute(
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
                    ORDER BY stock_quantity ASC, product_id ASC
                    """,
                    (store_id,),
                ).fetchall()

    conn.close()
    return render_template("inventory.html", stores=stores, inventory_rows=inventory_rows,
                           selected_store=selected_store, error=error)


# ──────────────────────────────────────────
# 3. 자동 재주문 발주 생성
# ──────────────────────────────────────────

@app.route("/reorder", methods=["GET", "POST"])
def reorder():
    created_rows = None
    message = None
    error = None

    if request.method == "POST":
        try:
            conn = get_connection()
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
                JOIN supplier_brand sb ON p.brand_id = sb.brand_id
                WHERE p.stock_quantity <= p.reorder_threshold
                  AND NOT EXISTS (
                      SELECT 1 FROM purchase_order po
                      WHERE po.product_id = p.product_id
                        AND po.store_id = p.store_id
                        AND po.status IN ('REQUESTED', 'APPROVED')
                  )
                GROUP BY p.product_id, p.store_id, p.brand_id,
                         p.product_name, p.stock_quantity, p.reorder_threshold
                ORDER BY p.stock_quantity ASC, p.product_id ASC
                """
            ).fetchall()

            if not targets:
                message = "자동 재주문이 필요한 제품이 없습니다."
                conn.close()
            else:
                created_list = []
                try:
                    conn.execute("BEGIN")
                    for row in targets:
                        product_id = row["product_id"]
                        store_id = row["store_id"]
                        product_name = row["product_name"]
                        stock_quantity = row["stock_quantity"]
                        reorder_threshold = row["reorder_threshold"]
                        supplier_id = row["supplier_id"]
                        order_quantity = row["order_quantity"]

                        cursor = conn.execute(
                            """
                            INSERT INTO purchase_order
                                (store_id, supplier_id, product_id, order_datetime, status, order_quantity)
                            VALUES (?, ?, ?, ?, 'REQUESTED', ?)
                            """,
                            (
                                store_id, supplier_id, product_id,
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                order_quantity,
                            ),
                        )
                        created_list.append({
                            "purchase_order_id": cursor.lastrowid,
                            "product_id": product_id,
                            "product_name": product_name,
                            "stock_quantity": stock_quantity,
                            "reorder_threshold": reorder_threshold,
                            "supplier_id": supplier_id,
                            "order_quantity": order_quantity,
                        })
                    conn.commit()
                    created_rows = created_list
                except sqlite3.Error as exc:
                    conn.rollback()
                    error = f"자동 재주문 발주 생성 중 오류: {exc}"
                finally:
                    conn.close()

        except FileNotFoundError as exc:
            error = str(exc)

    return render_template("reorder.html", created_rows=created_rows,
                           message=message, error=error)


# ──────────────────────────────────────────
# 4. 공급업체 발주 처리
# ──────────────────────────────────────────

@app.route("/purchase_orders", methods=["GET", "POST"])
def purchase_orders():
    conn = get_connection()

    result_msg = None
    error = None

    if request.method == "POST":
        po_id = request.form.get("purchase_order_id", "").strip()
        new_status = request.form.get("new_status", "").strip().upper()

        if not po_id.isdigit():
            error = "발주ID는 숫자여야 합니다."
        else:
            po_id = int(po_id)
            po = conn.execute(
                """
                SELECT purchase_order_id, store_id, product_id, status, order_quantity
                FROM purchase_order
                WHERE purchase_order_id = ?
                """,
                (po_id,)
            ).fetchone()

            if po is None:
                error = f"발주ID {po_id}는 존재하지 않습니다."
            else:
                current_status = po["status"]
                if current_status == "COMPLETED":
                    error = "이미 완료된 발주는 변경할 수 없습니다."
                elif current_status == "CANCELLED":
                    error = "이미 취소된 발주는 변경할 수 없습니다."
                elif new_status not in ALLOWED_TRANSITIONS.get(current_status, []):
                    error = f"허용되지 않는 상태 변경입니다. ({current_status} → {new_status})"
                else:
                    try:
                        conn.execute("BEGIN")
                        conn.execute(
                            "UPDATE purchase_order SET status = ? WHERE purchase_order_id = ?",
                            (new_status, po_id),
                        )
                        if new_status == "COMPLETED":
                            conn.execute(
                                """
                                UPDATE product
                                SET stock_quantity = stock_quantity + ?
                                WHERE product_id = ? AND store_id = ?
                                """,
                                (po["order_quantity"], po["product_id"], po["store_id"]),
                            )
                        conn.commit()
                        if new_status == "COMPLETED":
                            result_msg = f"발주 #{po_id}가 완료 처리되었고 재고가 증가했습니다."
                        elif new_status == "CANCELLED":
                            result_msg = f"발주 #{po_id}가 취소되었습니다."
                        else:
                            result_msg = f"발주 #{po_id} 상태가 {current_status} → {new_status}(으)로 변경되었습니다."
                    except sqlite3.Error as exc:
                        conn.rollback()
                        error = f"발주 처리 중 오류: {exc}"

    # 전체 발주 목록 조회 (COMPLETED/CANCELLED 포함 모두 표시, 처리 가능한 항목 우선)
    all_orders = conn.execute(
        """
        SELECT
            po.purchase_order_id,
            p.product_name,
            su.supplier_name,
            s.store_name,
            po.order_datetime,
            po.status,
            po.order_quantity
        FROM purchase_order po
        JOIN store s      ON po.store_id = s.store_id
        JOIN product p    ON po.product_id = p.product_id
        JOIN supplier su  ON po.supplier_id = su.supplier_id
        ORDER BY
            CASE po.status
                WHEN 'REQUESTED' THEN 1
                WHEN 'APPROVED'  THEN 2
                WHEN 'SHIPPED'   THEN 3
                WHEN 'COMPLETED' THEN 4
                WHEN 'CANCELLED' THEN 5
            END,
            po.purchase_order_id
        """
    ).fetchall()

    conn.close()
    return render_template("purchase_orders.html", all_orders=all_orders,
                           allowed_transitions=ALLOWED_TRANSITIONS,
                           result_msg=result_msg, error=error)


# ──────────────────────────────────────────
# 5. Sample Query 실행 및 결과 확인
# ──────────────────────────────────────────

@app.route("/analysis", methods=["GET", "POST"])
def analysis():
    run_result = None
    error = None
    query_results_html = ""

    if request.method == "POST":
        if using_remote_database():
            conn = None
            try:
                conn = get_connection()
                results = run_sample_queries(conn, BASE_DIR / "queries" / "sample_queries.sql")
                raw = results_to_markdown(results, "Turso/libSQL remote database", "queries/sample_queries.sql")
                query_results_html = md_lib.markdown(raw, extensions=["tables"])
                run_result = "\n".join(
                    f"[{'PASS' if result['passed'] else 'FAIL'}] {result['title']} "
                    f"rows={result['row_count']} time={result['elapsed_ms']:.3f}ms"
                    for result in results
                )
            except Exception as exc:
                error = f"쿼리 실행 중 오류가 발생했습니다: {exc}"
            finally:
                if conn is not None:
                    conn.close()
        else:
            if not QUERY_TEST_PATH.exists():
                error = "queries/query_test.py 파일이 없습니다."
            else:
                proc = subprocess.run(
                    [sys.executable, str(QUERY_TEST_PATH)],
                    cwd=BASE_DIR,
                    text=True,
                    capture_output=True,
                )
                if proc.returncode == 0:
                    run_result = proc.stdout.strip()
                else:
                    error = proc.stderr.strip() or "쿼리 실행 중 오류가 발생했습니다."

    # query_results.md → HTML 변환 (tables 확장으로 정확한 테이블 렌더링)
    if not query_results_html and QUERY_RESULTS_PATH.exists():
        raw = QUERY_RESULTS_PATH.read_text(encoding="utf-8")
        query_results_html = md_lib.markdown(raw, extensions=["tables"])

    return render_template("analysis.html", run_result=run_result,
                           query_results_html=query_results_html, error=error)


# ──────────────────────────────────────────
# 실행 진입점
# ──────────────────────────────────────────

if __name__ == "__main__":
    if not using_remote_database() and not DB_PATH.exists():
        print("오류: market.db 파일이 없습니다.")
        print("먼저 `python seed_data.py --reset --db market.db`를 실행하세요.")
        sys.exit(1)
    print("Flask 웹앱 시작 중...")
    if using_remote_database():
        print("DB 연결: Turso/libSQL remote database")
    else:
        print(f"DB 경로: {DB_PATH}")
    print("접속 주소: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
