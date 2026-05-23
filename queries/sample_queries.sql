-- Query 1. 각 매장별 가장 많이 판매된 상위 20개 제품 조회
SELECT
    store_id,
    store_name,
    product_id,
    product_name,
    total_quantity
FROM (
    SELECT
        s.store_id,
        s.store_name,
        p.product_id,
        p.product_name,
        SUM(o.quantity) AS total_quantity,
        ROW_NUMBER() OVER (
            PARTITION BY s.store_id
            ORDER BY SUM(o.quantity) DESC
        ) AS ranking
    FROM orders o
    JOIN store s
        ON o.store_id = s.store_id
    JOIN product p
        ON o.product_id = p.product_id
    GROUP BY
        s.store_id,
        s.store_name,
        p.product_id,
        p.product_name
)
WHERE ranking <= 20
ORDER BY
    store_name,
    total_quantity DESC;

-- Query 2. 캠퍼스 구역별로 가장 많이 판매된 상위 20개 제품 조회
WITH store_area AS (
    SELECT
        store_id,
        CASE
            WHEN store_name LIKE '%기숙사%' THEN '기숙사 구역'
            WHEN store_name LIKE '%과학관%' THEN '과학관 구역'
            WHEN store_name LIKE '%아산공학관%' THEN '아산공학관 구역'
            WHEN store_name LIKE '%도서관%' THEN '도서관 구역'
            WHEN store_name LIKE '%경영관%' THEN '경영관 구역'
            WHEN store_name LIKE '%음악관%' THEN '음악관 구역'
            WHEN store_name LIKE '%조형관%' THEN '조형관 구역'
            WHEN store_name LIKE '%학관%' THEN '학관 구역'
            ELSE '기타 구역'
        END AS campus_area
    FROM store
)
SELECT
    campus_area,
    product_id,
    product_name,
    total_quantity
FROM (
    SELECT
        sa.campus_area,
        p.product_id,
        p.product_name,
        SUM(o.quantity) AS total_quantity,
        ROW_NUMBER() OVER (
            PARTITION BY sa.campus_area
            ORDER BY SUM(o.quantity) DESC
        ) AS ranking
    FROM orders o
    JOIN store_area sa
        ON o.store_id = sa.store_id
    JOIN product p
        ON o.product_id = p.product_id
    GROUP BY
        sa.campus_area,
        p.product_id,
        p.product_name
)
WHERE ranking <= 20
ORDER BY
    campus_area,
    total_quantity DESC;

-- Query 3. 판매 실적이 우수한 상위 5개 매장 조회
SELECT
    s.store_id,
    s.store_name,
    SUM(o.quantity * o.unit_price) AS total_sales_amount
FROM orders o
JOIN store s
    ON o.store_id = s.store_id
GROUP BY
    s.store_id,
    s.store_name
ORDER BY
    total_sales_amount DESC
LIMIT 5;

-- Query 4. 코카콜라 제품보다 노브랜드 콜라가 더 많이 판매된 매장의 수 조회
SELECT
    COUNT(*) AS store_count
FROM (
    SELECT
        s.store_id,
        s.store_name,
        SUM(
            CASE
                WHEN p.product_name IN ('코카콜라 오리지널', '코카콜라 제로')
                THEN o.quantity
                ELSE 0
            END
        ) AS coca_cola_quantity,
        SUM(
            CASE
                WHEN p.product_name = '노브랜드 콜라'
                THEN o.quantity
                ELSE 0
            END
        ) AS no_brand_cola_quantity
    FROM orders o
    JOIN store s
        ON o.store_id = s.store_id
    JOIN product p
        ON o.product_id = p.product_id
    WHERE p.product_name IN (
        '코카콜라 오리지널',
        '코카콜라 제로',
        '노브랜드 콜라'
    )
    GROUP BY
        s.store_id,
        s.store_name
)
WHERE no_brand_cola_quantity > coca_cola_quantity;

-- Query 5. 우유 제품 판매량이 있는 매장 중 판매량 상위 5개 조회
SELECT
    s.store_id,
    s.store_name,
    SUM(o.quantity) AS milk_total_quantity,
    SUM(o.quantity * o.unit_price) AS milk_total_sales_amount
FROM orders o
JOIN store s
    ON o.store_id = s.store_id
JOIN product p
    ON o.product_id = p.product_id
WHERE p.product_name IN (
    '매일유업 매일우유 오리지널',
    '매일유업 소화가잘되는우유',
    '매일유업 상하목장 유기농우유',
    '노브랜드 굿밀크'
)
GROUP BY
    s.store_id,
    s.store_name
ORDER BY
    milk_total_quantity DESC,
    milk_total_sales_amount DESC
LIMIT 5;
