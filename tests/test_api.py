from tests.conftest import MIGRATION, SCHEMA


def paid_order(client, quantity=1, source="Website", fee=10, **extra):
    total = 499 * quantity
    return client.post("/orders", json={
        "customer_id": 1,
        "source": source,
        "payment_method": "UPI",
        "payment_status": "Paid",
        "order_status": "Delivered",
        "shipping_cost": 50,
        "items": [{"product_id": 1, "quantity": quantity}],
        "payment": {
            "amount": total, "payment_method": "UPI",
            "payment_status": "Paid", "gateway": "Razorpay",
            "gateway_fee": fee,
        },
        **extra,
    })


def cod_order(client, order_status="Placed", source="WhatsApp"):
    return client.post("/orders", json={
        "customer_id": 1,
        "source": source,
        "payment_method": "COD",
        "payment_status": "Pending",
        "order_status": order_status,
        "shipping_cost": 60,
        "items": [{"product_id": 1, "quantity": 1}],
    })


# --- Schema -----------------------------------------------------------------

def test_payment_endpoints_work_on_fresh_schema(seed):
    assert paid_order(seed).status_code == 200
    payments = seed.get("/payments")
    assert payments.status_code == 200
    assert payments.json()[0]["gateway_fee"] == 10.0


def test_migration_upgrades_old_schema_and_is_rerunnable(db):
    old_schema = SCHEMA.replace(
        """    gateway VARCHAR(50),
    transaction_id VARCHAR(100),
    gateway_fee NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (gateway_fee >= 0),
""", "")
    assert "gateway_fee" not in old_schema
    db("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    db(old_schema)
    db("""
        INSERT INTO customers (name, phone, address, pincode)
            VALUES ('A', '1', 'x', '1');
        INSERT INTO orders (customer_id, source, payment_method,
                            payment_status, order_status)
            VALUES (1, 'Website', 'UPI', 'pending', 'delivered');
        INSERT INTO payments (order_id, amount, payment_method, payment_status)
            VALUES (1, 499, 'UPI', 'paid');
    """)
    db(MIGRATION)
    db(MIGRATION)  # second run must not fail

    from backend.database import get_connection
    connection = get_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT payment_status, gateway_fee FROM payments")
        assert cursor.fetchone() == ("Paid", 0)
        cursor.execute("SELECT payment_status, order_status FROM orders")
        assert cursor.fetchone() == ("Paid", "Delivered")
    connection.close()


# --- Validation ---------------------------------------------------------------

def test_status_is_case_insensitive_and_stored_canonically(seed):
    response = seed.post("/orders", json={
        "customer_id": 1, "source": "Website", "payment_method": "UPI",
        "payment_status": "paid", "order_status": "DELIVERED",
        "items": [{"product_id": 1, "quantity": 1}],
        "payment": {"amount": 499, "payment_method": "UPI",
                    "payment_status": "paid"},
    })
    assert response.status_code == 200
    assert seed.get("/analytics/orders").json()["total_orders"] == 1


def test_unknown_status_is_rejected(seed):
    response = cod_order(seed, order_status="Teleported")
    assert response.status_code == 422


def test_wrong_payment_amount_is_rejected_even_lowercase(seed):
    response = seed.post("/orders", json={
        "customer_id": 1, "source": "Website", "payment_method": "UPI",
        "payment_status": "paid", "order_status": "Delivered",
        "items": [{"product_id": 1, "quantity": 1}],
        "payment": {"amount": 1, "payment_method": "UPI",
                    "payment_status": "paid"},
    })
    assert response.status_code == 400
    assert "Expected ₹499.00" in response.json()["detail"]


def test_negative_quantity_is_rejected(seed):
    response = seed.post("/orders", json={
        "customer_id": 1, "source": "x", "payment_method": "COD",
        "payment_status": "Pending", "order_status": "Placed",
        "items": [{"product_id": 1, "quantity": -5}],
    })
    assert response.status_code == 422


def test_unknown_customer_and_product_give_400(seed):
    bad_customer = seed.post("/orders", json={
        "customer_id": 999, "source": "x", "payment_method": "COD",
        "payment_status": "Pending", "order_status": "Placed",
        "items": [{"product_id": 1, "quantity": 1}],
    })
    bad_product = seed.post("/orders", json={
        "customer_id": 1, "source": "x", "payment_method": "COD",
        "payment_status": "Pending", "order_status": "Placed",
        "items": [{"product_id": 42, "quantity": 1}],
    })
    assert bad_customer.status_code == 400
    assert bad_product.status_code == 400


def test_payment_for_unknown_order_gives_404(seed):
    response = seed.post("/payments", json={
        "order_id": 999, "amount": 10, "payment_method": "COD",
        "payment_status": "Paid",
    })
    assert response.status_code == 404


def test_prices_default_to_catalogue(seed):
    response = seed.post("/orders", json={
        "customer_id": 1, "source": "x", "payment_method": "COD",
        "payment_status": "Pending", "order_status": "Placed",
        "items": [{"product_id": 1, "quantity": 2, "discount_amount": 98}],
    })
    assert response.status_code == 200
    assert response.json()["order_total"] == 900.0


# --- Payment status sync ----------------------------------------------------

def test_cod_payment_marks_order_paid_and_counts_revenue(seed):
    order_id = cod_order(seed).json()["order_id"]
    assert seed.get("/analytics/summary").json()["revenue"] == 0

    seed.post("/payments", json={
        "order_id": order_id, "amount": 499, "payment_method": "COD",
        "payment_status": "Paid",
    })

    orders = seed.get("/orders").json()["orders"]
    assert orders[0]["payment_status"] == "Paid"
    assert seed.get("/analytics/summary").json()["revenue"] == 499.0


# --- Profit -------------------------------------------------------------------

def test_net_profit_includes_every_cost(seed):
    paid_order(seed, quantity=2)                 # 998 revenue, 240 cost, 50 ship, 10 fee
    cod_order(seed, order_status="RTO")          # 60 shipping lost
    seed.post("/expenses", json={"category": "Meta Ads", "amount": 300})
    seed.post("/expenses", json={"category": "Packaging", "amount": 200})

    summary = seed.get("/analytics/summary").json()
    assert summary["revenue"] == 998.0
    assert summary["ads"] == 300.0
    assert summary["other_expenses"] == 200.0
    assert summary["return_shipping_loss"] == 60.0
    assert summary["payment_fees"] == 10.0
    assert summary["net_profit"] == 998 - 240 - 50 - 10 - 300 - 200 - 60


def test_daily_monthly_and_summary_agree(seed):
    paid_order(seed)
    seed.post("/expenses", json={"category": "Meta Ads", "amount": 100})
    seed.post("/expenses", json={"category": "Courier bags", "amount": 25})

    summary = seed.get("/analytics/summary").json()
    daily = seed.get("/analytics/daily").json()["daily"]
    monthly = seed.get("/analytics/monthly").json()["monthly"]

    assert sum(day["net_profit"] for day in daily) == summary["net_profit"]
    assert sum(m["net_profit"] for m in monthly) == summary["net_profit"]
    assert daily[0]["payment_fees"] == 10.0


def test_channel_profit_charges_returns_to_their_channel(seed):
    paid_order(seed, source="Website")
    cod_order(seed, order_status="RTO", source="WhatsApp")

    channels = {
        c["source"]: c for c in seed.get("/analytics/channel-profit").json()["channels"]
    }
    assert channels["Website"]["profit_before_ads"] == 499 - 120 - 50 - 10
    assert channels["WhatsApp"]["return_shipping_loss"] == 60.0
    assert channels["WhatsApp"]["return_rate_percentage"] == 100.0


def test_date_filters(seed):
    paid_order(seed)
    assert seed.get(
        "/analytics/summary", params={"end_date": "2000-01-01"}
    ).json()["revenue"] == 0
    assert seed.get(
        "/analytics/summary", params={"start_date": "2000-01-01"}
    ).json()["revenue"] == 499.0


def test_empty_database_returns_zeros(client):
    summary = client.get("/analytics/summary").json()
    assert summary["net_profit"] == 0
    for endpoint in [
        "/analytics/monthly", "/analytics/daily", "/analytics/channels",
        "/analytics/channel-profit", "/analytics/orders", "/analytics/products",
        "/analytics/customers", "/analytics/customer-retention",
        "/customers", "/products", "/payments", "/expenses", "/orders",
    ]:
        assert client.get(endpoint).status_code == 200, endpoint
