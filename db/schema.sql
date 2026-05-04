PRAGMA foreign_keys = ON;

CREATE TABLE retailer (
    retailer_id INTEGER PRIMARY KEY,
    retailer_name TEXT,
    website_url TEXT,
    phone_number TEXT
);

CREATE TABLE store (
    store_id INTEGER PRIMARY KEY,
    retailer_id INTEGER,
    store_name TEXT,
    address TEXT,
    business_hours TEXT,
    FOREIGN KEY (retailer_id) REFERENCES retailer(retailer_id)
);

CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    phone_number TEXT,
    privacy_agreed INTEGER
);

CREATE TABLE brand (
    brand_id INTEGER PRIMARY KEY,
    brand_name TEXT
);

CREATE TABLE product_category (
    category_id INTEGER PRIMARY KEY,
    category_name TEXT,
    parent_category_id INTEGER,
    FOREIGN KEY (parent_category_id) REFERENCES product_category(category_id)
);

CREATE TABLE product (
    product_id INTEGER PRIMARY KEY,
    brand_id INTEGER,
    store_id INTEGER,
    category_id INTEGER,
    product_name TEXT,
    stock_quantity INTEGER,
    sale_price INTEGER,
    reorder_threshold INTEGER,
    specification TEXT,
    package_type TEXT,
    barcode_number TEXT,
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (category_id) REFERENCES product_category(category_id)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    store_id INTEGER,
    product_id INTEGER,
    order_datetime TEXT,
    quantity INTEGER,
    unit_price INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);

CREATE TABLE supplier (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT
);

CREATE TABLE purchase_order (
    purchase_order_id INTEGER PRIMARY KEY,
    store_id INTEGER,
    supplier_id INTEGER,
    product_id INTEGER,
    order_datetime TEXT,
    status TEXT,
    order_quantity INTEGER,
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (product_id) REFERENCES product(product_id)
);

CREATE TABLE supplier_brand (
    supplier_id INTEGER,
    brand_id INTEGER,
    PRIMARY KEY (supplier_id, brand_id),
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id),
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id)
);
