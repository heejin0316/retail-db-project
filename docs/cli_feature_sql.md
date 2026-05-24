# CLI Feature SQL

이 문서는 CLI 인터페이스에서 사용할 기능별 SQL과 처리 기준을 정리한다.

## 1. 고객 주문 등록

### 입력값

- 고객ID
- 제품ID
- 수량

### 고객 존재 확인

```sql
SELECT
    customer_id,
    customer_name
FROM customer
WHERE customer_id = ?;
```

### 제품 정보 조회

제품ID를 기준으로 매장ID, 판매단가, 현재 재고량을 조회한다.

```sql
SELECT
    product_id,
    store_id,
    product_name,
    sale_price,
    stock_quantity
FROM product
WHERE product_id = ?;
```

### 주문 추가

`order_id`는 SQLite `INTEGER PRIMARY KEY` 특성에 따라 자동 생성되도록 직접 넣지 않는다.

```sql
INSERT INTO orders (
    customer_id,
    store_id,
    product_id,
    order_datetime,
    quantity,
    unit_price
)
VALUES (?, ?, ?, ?, ?, ?);
```

### 제품 재고 감소

```sql
UPDATE product
SET stock_quantity = stock_quantity - ?
WHERE product_id = ?
  AND stock_quantity >= ?;
```

### 처리 순서

1. 고객ID, 제품ID, 수량을 입력받는다.
2. 수량이 1 이상인지 확인한다.
3. 고객이 존재하는지 확인한다.
4. 제품이 존재하는지 확인한다.
5. 제품의 `store_id`, `sale_price`, `stock_quantity`를 조회한다.
6. 재고가 주문 수량보다 적으면 주문을 실패 처리한다.
7. `orders`에 새 주문을 추가한다.
8. `product.stock_quantity`를 주문 수량만큼 감소시킨다.
9. 정상 처리 시 commit한다.
10. 중간 오류 발생 시 rollback한다.

## 2. 매장 재고 조회

### 입력값

- 매장ID

### 전체 매장 목록 조회

```sql
SELECT
    store_id,
    store_name
FROM store
ORDER BY store_id;
```

### 매장 존재 확인

```sql
SELECT
    store_id,
    store_name
FROM store
WHERE store_id = ?;
```

### 매장별 제품 재고 조회

```sql
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
    product_id ASC;
```

### 처리 순서

1. 전체 매장 목록을 출력한다.
2. 사용자가 매장ID를 입력한다.
3. 매장 존재 여부를 확인한다.
4. 해당 매장의 제품 재고 목록을 조회한다.
5. 재고량 낮은 순서로 출력한다.

## 3. 자동 재주문 발주 생성

### 자동 재주문 대상 제품 조회

재고량이 재주문기준수량 이하이고, 같은 제품에 대해 `REQUESTED` 또는 `APPROVED` 상태의 진행 중 발주가 없는 제품을 조회한다.

```sql
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
    p.product_id ASC;
```

### 발주 생성

`purchase_order_id`는 SQLite `INTEGER PRIMARY KEY` 특성에 따라 자동 생성되도록 직접 넣지 않는다.

```sql
INSERT INTO purchase_order (
    store_id,
    supplier_id,
    product_id,
    order_datetime,
    status,
    order_quantity
)
VALUES (?, ?, ?, ?, 'REQUESTED', ?);
```

### 처리 순서

1. 자동 재주문 대상 제품을 조회한다.
2. 대상 제품이 없으면 "자동 재주문이 필요한 제품이 없습니다."를 출력한다.
3. 각 대상 제품의 `brand_id`를 기준으로 `supplier_brand`에서 공급업체를 찾는다.
4. 가능한 공급업체가 여러 개면 `supplier_id`가 가장 작은 공급업체를 선택한다.
5. 발주수량은 `max(reorder_threshold * 3, 10)`으로 계산한다.
6. `purchase_order`에 `REQUESTED` 상태로 새 발주를 추가한다.
7. 생성된 발주 목록을 출력한다.

## 4. 공급업체 발주 처리

### 처리 가능한 발주 목록 조회

```sql
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
    po.purchase_order_id;
```

### 특정 발주 조회

```sql
SELECT
    purchase_order_id,
    store_id,
    product_id,
    status,
    order_quantity
FROM purchase_order
WHERE purchase_order_id = ?;
```

### 발주 상태 변경

```sql
UPDATE purchase_order
SET status = ?
WHERE purchase_order_id = ?;
```

### COMPLETED 처리 시 재고 증가

```sql
UPDATE product
SET stock_quantity = stock_quantity + ?
WHERE product_id = ?
  AND store_id = ?;
```

### 상태 변경 규칙

```text
REQUESTED -> APPROVED, CANCELLED
APPROVED  -> SHIPPED, CANCELLED
SHIPPED   -> COMPLETED
COMPLETED -> 변경 불가
CANCELLED -> 변경 불가
```

### 처리 순서

1. 처리 가능한 발주 목록을 출력한다.
2. 사용자가 발주ID를 입력한다.
3. 발주 존재 여부를 확인한다.
4. 현재 상태를 확인한다.
5. 변경 가능한 다음 상태 목록을 출력한다.
6. 사용자가 변경할 상태를 입력한다.
7. 상태 변경 가능 여부를 확인한다.
8. `purchase_order.status`를 변경한다.
9. 변경 상태가 `COMPLETED`이면 `product.stock_quantity`를 발주수량만큼 증가시킨다.
10. 정상 처리 시 commit한다.
11. 중간 오류 발생 시 rollback한다.

## 5. 분석 기능

분석 기능은 기존 `queries/query_test.py`를 실행하여 sample query 5개를 검증하고 `queries/query_results.md`를 갱신한다.

```text
python queries/query_test.py
```
