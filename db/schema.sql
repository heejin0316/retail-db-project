PRAGMA foreign_keys = ON;

CREATE TABLE retailer (
    retailer_id INTEGER PRIMARY KEY,
    retailer_name TEXT NOT NULL UNIQUE,
    website_url TEXT,
    phone_number TEXT
);

CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    phone_number TEXT,
    privacy_agreed INTEGER NOT NULL CHECK (privacy_agreed IN (0, 1))
);

CREATE TABLE brand (
    brand_id INTEGER PRIMARY KEY,
    brand_name TEXT NOT NULL UNIQUE
);

CREATE TABLE product_category (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT NOT NULL,
    parent_category_id INTEGER,
    FOREIGN KEY (parent_category_id) REFERENCES product_category(category_id)
);

CREATE TABLE supplier (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE
);

CREATE TABLE store (
    store_id INTEGER PRIMARY KEY,
    retailer_id INTEGER NOT NULL,
    store_name TEXT NOT NULL,
    address TEXT,
    business_hours TEXT,
    FOREIGN KEY (retailer_id) REFERENCES retailer(retailer_id)
);

CREATE TABLE product (
    product_id INTEGER PRIMARY KEY,
    brand_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    stock_quantity INTEGER NOT NULL CHECK (stock_quantity >= 0),
    sale_price INTEGER NOT NULL CHECK (sale_price >= 0),
    reorder_threshold INTEGER NOT NULL CHECK (reorder_threshold >= 0),
    barcode_number TEXT NOT NULL UNIQUE,
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (category_id) REFERENCES product_category(category_id)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    order_datetime TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);

CREATE TABLE purchase_order (
    purchase_order_id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    order_datetime TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('REQUESTED', 'APPROVED', 'SHIPPED', 'COMPLETED', 'CANCELLED')
    ),
    order_quantity INTEGER NOT NULL CHECK (order_quantity > 0),
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);

CREATE TABLE supplier_brand (
    supplier_id INTEGER NOT NULL,
    brand_id INTEGER NOT NULL,
    PRIMARY KEY (supplier_id, brand_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id)
);

CREATE INDEX idx_orders_store_id
ON orders(store_id);

CREATE INDEX idx_orders_product_id
ON orders(product_id);

CREATE INDEX idx_orders_customer_id
ON orders(customer_id);

CREATE INDEX idx_product_store_id
ON product(store_id);

CREATE INDEX idx_product_brand_id
ON product(brand_id);

CREATE INDEX idx_product_category_id
ON product(category_id);

CREATE INDEX idx_purchase_order_store_id
ON purchase_order(store_id);

CREATE INDEX idx_purchase_order_supplier_id
ON purchase_order(supplier_id);
