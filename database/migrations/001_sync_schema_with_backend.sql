-- Migration 001: bring a database created from the original schema.sql in
-- line with what the backend expects. Safe to run more than once.
--
--   psql -d creamos -f database/migrations/001_sync_schema_with_backend.sql

BEGIN;

-- 1. Payment columns the backend reads and writes (missing from the
--    original schema.sql, which made payment and summary endpoints fail).
ALTER TABLE payments ADD COLUMN IF NOT EXISTS gateway VARCHAR(50);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100);
ALTER TABLE payments ADD COLUMN IF NOT EXISTS gateway_fee NUMERIC(10,2) DEFAULT 0;
UPDATE payments SET gateway_fee = 0 WHERE gateway_fee IS NULL;
ALTER TABLE payments ALTER COLUMN gateway_fee SET DEFAULT 0;
ALTER TABLE payments ALTER COLUMN gateway_fee SET NOT NULL;

-- 2. Normalise the capitalisation of known status values, so rows such as
--    'paid' are no longer silently ignored by the analytics.
UPDATE payments
SET payment_status = INITCAP(payment_status)
WHERE LOWER(payment_status) IN ('paid', 'pending', 'failed', 'refunded')
  AND payment_status <> INITCAP(payment_status);

UPDATE orders
SET payment_status = INITCAP(payment_status)
WHERE LOWER(payment_status) IN ('paid', 'pending', 'failed', 'refunded')
  AND payment_status <> INITCAP(payment_status);

UPDATE orders
SET order_status = CASE
        WHEN LOWER(order_status) = 'rto' THEN 'RTO'
        ELSE INITCAP(order_status)
    END
WHERE LOWER(order_status) IN (
        'placed', 'confirmed', 'shipped', 'delivered',
        'cancelled', 'returned', 'rto', 'refunded'
    )
  AND order_status <> CASE
        WHEN LOWER(order_status) = 'rto' THEN 'RTO'
        ELSE INITCAP(order_status)
    END;

-- 3. Keep orders.payment_status in step with recorded payments: an order
--    with a Paid payment is Paid.
UPDATE orders o
SET payment_status = 'Paid'
WHERE o.payment_status <> 'Paid'
  AND EXISTS (
      SELECT 1 FROM payments p
      WHERE p.order_id = o.order_id
        AND p.payment_status = 'Paid'
  );

-- 4. Sanity constraints. Added NOT VALID so existing rows are not checked
--    (run "ALTER TABLE ... VALIDATE CONSTRAINT ..." later if you want that);
--    every new or updated row is checked.
DO $$
DECLARE
    c RECORD;
BEGIN
    FOR c IN
        SELECT * FROM (VALUES
            ('products',    'products_selling_price_check',      'selling_price >= 0'),
            ('products',    'products_cost_price_check',         'cost_price >= 0'),
            ('orders',      'orders_shipping_cost_check',        'shipping_cost >= 0'),
            ('order_items', 'order_items_quantity_check',        'quantity > 0'),
            ('order_items', 'order_items_unit_price_check',      'unit_price >= 0'),
            ('order_items', 'order_items_unit_cost_check',       'unit_cost >= 0'),
            ('order_items', 'order_items_discount_amount_check', 'discount_amount >= 0'),
            ('payments',    'payments_amount_check',             'amount >= 0'),
            ('payments',    'payments_gateway_fee_check',        'gateway_fee >= 0'),
            ('expenses',    'expenses_amount_check',             'amount >= 0')
        ) AS t(tbl, name, expr)
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = c.name
        ) THEN
            EXECUTE format(
                'ALTER TABLE %I ADD CONSTRAINT %I CHECK (%s) NOT VALID',
                c.tbl, c.name, c.expr
            );
        END IF;
    END LOOP;
END $$;

-- 5. Indexes for the analytics joins and date filters.
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments (order_id);
CREATE INDEX IF NOT EXISTS idx_expenses_expense_date ON expenses (expense_date);

COMMIT;
