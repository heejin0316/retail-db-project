# Retail DB Project

## 팀 정보
- 수업명: DataBase
- 팀명: 널값없는 사이
- 팀원
  - 정희진
  - 이윤주

## 프로젝트 소개

본 프로젝트는 유통업체의 매장, 제품, 고객 주문, 재고, 발주 데이터를 관리하기 위한 데이터베이스 시스템입니다.

SQLite 기반으로 데이터베이스 스키마와 초기 데이터를 구성했으며, Flask 웹 인터페이스를 통해 주요 기능을 실행할 수 있도록 구현했습니다. 배포 환경에서는 Turso/libSQL 원격 데이터베이스를 사용합니다.

## 배포 사이트

아래 주소에서 웹 인터페이스를 확인할 수 있습니다.

```text
https://retail-db-project.vercel.app/
```

## 주요 기능

1. 고객 주문 등록
   - 고객ID, 제품ID, 수량을 입력하여 주문을 생성합니다.
   - 주문 성공 시 주문 데이터가 추가되고 제품 재고가 감소합니다.

2. 매장 재고 조회
   - 매장별 제품 재고를 조회합니다.
   - 재고량, 재주문기준수량, 판매가격, 재주문 필요 여부를 확인할 수 있습니다.

3. 자동 재주문 발주 생성
   - 재고량이 재주문기준수량 이하인 제품을 대상으로 자동 발주를 생성합니다.
   - 진행 중인 발주가 있는 제품은 중복 발주하지 않습니다.

4. 공급업체 발주 처리
   - 발주 상태를 단계별로 변경합니다.
   - `COMPLETED` 처리 시 제품 재고가 발주수량만큼 증가합니다.

5. Sample Query 실행
   - 데이터베이스 분석용 sample query 5개를 실행하고 결과를 확인합니다.

## 프로젝트 구조

```text
dbprojext/
  README.md
  requirements.txt
  web_app.py
  database.py
  seed_data.py
  seed_remote.py
  sample_query_runner.py

  db/
    schema.sql

  docs/
    er_diagram.png
    erd_description.md
    relation_schema.md
    query_description.md

  queries/
    sample_queries.sql
    query_results.md

  templates/
    base.html
    index.html
    order.html
    inventory.html
    reorder.html
    purchase_orders.html
    analysis.html
```

## Relation Schema

주요 relation은 다음과 같습니다.

```text
retailer(retailer_id, retailer_name, website_url, phone_number)

store(store_id, retailer_id, store_name, address, business_hours)

customer(customer_id, customer_name, phone_number, privacy_agreed)

brand(brand_id, brand_name)

product_category(category_id, category_name, parent_category_id)

supplier(supplier_id, supplier_name)

product(product_id, brand_id, store_id, category_id, product_name,
        stock_quantity, sale_price, reorder_threshold, barcode_number)

orders(order_id, customer_id, store_id, product_id,
       order_datetime, quantity, unit_price)

purchase_order(purchase_order_id, store_id, supplier_id, product_id,
               order_datetime, status, order_quantity)

supplier_brand(supplier_id, brand_id)
```

자세한 내용은 `docs/relation_schema.md`와 `db/schema.sql`에 정리되어 있습니다.

## Sample Query

`queries/sample_queries.sql`에는 다음 5개 query가 포함되어 있습니다.

1. 각 매장별 가장 많이 판매된 상위 20개 제품 조회
2. 캠퍼스 구역별 가장 많이 판매된 상위 20개 제품 조회
3. 판매 실적이 우수한 상위 5개 매장 조회
4. 코카콜라 제품보다 노브랜드 콜라가 더 많이 판매된 매장의 수 조회
5. 우유 제품을 가장 많이 판매한 상위 5개 매장 조회

쿼리 설명은 `docs/query_description.md`, 실행 결과 예시는 `queries/query_results.md`에 있습니다.

## 로컬 실행 방법

### 1. 패키지 설치

```bash
python -m pip install -r requirements.txt
```

### 2. 로컬 SQLite DB 생성

```bash
python seed_data.py --reset --db market.db
```

### 3. Flask 웹앱 실행

```bash
python web_app.py
```

실행 후 브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:5000
```

## Sample Query 실행

```bash
python queries/query_test.py
```

실행 결과는 아래 파일에 저장됩니다.

```text
queries/query_results.md
```

## 데이터 파일 안내

과제 제출 기준에 따라 실제 데이터베이스 파일(`market.db`)은 GitHub 및 제출 ZIP에 포함하지 않았습니다.

로컬에서 아래 명령어를 실행하면 동일한 구조의 DB를 다시 생성할 수 있습니다.

```bash
python seed_data.py --reset --db market.db
```

## 기술 스택

- Python
- Flask
- SQLite
- Turso/libSQL
- HTML/CSS
- Vercel

## 배포 환경

- 로컬 실행: SQLite 파일 DB 사용
- 배포 실행: Turso/libSQL 원격 DB 사용
- 웹 배포: Vercel
