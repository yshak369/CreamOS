-- CreamOS database schema (fresh install).
-- For an existing database created from an older schema, run the files in
-- database/migrations/ instead of this file.

CREATE TABLE products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    selling_price NUMERIC(10,2) NOT NULL CHECK (selling_price >= 0),
    cost_price NUMERIC(10,2) NOT NULL CHECK (cost_price >= 0)
);

CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    pincode VARCHAR(10) NOT NULL
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(30) NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    shipping_cost NUMERIC(10,2) DEFAULT 50 CHECK (shipping_cost >= 0),

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) CHECK (unit_price >= 0),
    unit_cost NUMERIC(10,2) CHECK (unit_cost >= 0),
    discount_amount NUMERIC(10,2) DEFAULT 0 CHECK (discount_amount >= 0),

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

CREATE TABLE payments (
    payment_id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(30) NOT NULL,
    gateway VARCHAR(50),
    transaction_id VARCHAR(100),
    gateway_fee NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (gateway_fee >= 0),

    FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
);

CREATE TABLE expenses (
    expense_id SERIAL PRIMARY KEY,
    expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10,2) NOT NULL CHECK (amount >= 0),
    description TEXT
);

-- Indexes for the joins and filters used by the analytics endpoints.
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_orders_order_date ON orders (order_date);
CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);
CREATE INDEX idx_payments_order_id ON payments (order_id);
CREATE INDEX idx_expenses_expense_date ON expenses (expense_date);
